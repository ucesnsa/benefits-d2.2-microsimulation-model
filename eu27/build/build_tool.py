"""Assemble the all-country provider tool: ONE self-contained HTML file with a country picker
and a switch between the full view (the D2.2 Provider tab) and the plain-language view (the
plain-language provider tool). Each view runs in its own frame, built on demand from its template and the selected
country's block, so the two tools' scripts never share a scope.

Inputs:  data/<CC>.json (one country block each; see views.py), full_template.html,
         lite_template.html.
Output:  ../BENEFITS_Provider_Tool_EU27_v2.html (test builds: out/)
Run:     py build_tool.py [--blocks-from-shipped]   (the flag builds a test file from the three
         shipped EU blocks only, before data/ exists)
"""
import io, json, os, sys, glob, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import views
from paths import MACH, ROOT

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
EU27 = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "EL", "HU", "IE", "IT", "LV", "LT",
        "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"]

SHELL = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BENEFITS Provider Tool v2 · EU</title>
<style>
:root{--ink:#10243e;--mut:#475569;--line:#d6dde8;--bg:#f6f8fb;--accent:#1f4e8c;--card:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
.bar{position:sticky;top:0;z-index:5;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px}
.bar .in{max-width:1180px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center}
.brand{font-weight:700;font-size:16px;margin-right:auto}
.brand small{display:block;font-weight:400;color:var(--mut);font-size:12px}
label.pick{display:flex;align-items:center;gap:8px;font-size:14px}
select{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:#fff;min-width:190px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.seg button{font:inherit;font-size:14px;padding:6px 12px;border:0;background:#fff;color:var(--ink);cursor:pointer}
.seg button[aria-pressed="true"]{background:var(--accent);color:#fff}
.seg button:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.scopewrap{max-width:1180px;margin:10px auto 0;padding:0 16px}
.scope{margin:0;padding:8px 12px;border:1px solid #9db4d6;border-radius:8px;background:#eef4fb;font-size:13px;color:var(--ink)}
.status{max-width:1180px;margin:10px auto 0;padding:0 16px;font-size:13px;color:var(--mut)}
.status b{color:var(--ink)}
.status .derived{display:inline-block;margin-left:4px;padding:1px 7px;border-radius:10px;background:#fff3cd;border:1px solid #e0b400;color:#5b4300;font-size:12px}
.status .model{display:inline-block;margin-left:4px;padding:1px 7px;border-radius:10px;background:#e7f5ec;border:1px solid #6fbf8e;color:#14532d;font-size:12px}
iframe{display:block;width:100%;max-width:1180px;margin:8px auto 24px;border:0;background:#fff;min-height:600px}
@media (max-width:640px){.brand{width:100%}select{min-width:0;flex:1}label.pick{flex:1}}
</style>
</head>
<body>
<div class="bar"><div class="in">
  <div class="brand">BENEFITS provider tool, version 2<small>27 EU countries · Horizon Europe grant agreement 101179032</small></div>
  <label class="pick" for="cc">Country <select id="cc"></select></label>
  <div class="seg" role="group" aria-label="View">
    <button type="button" id="v-lite" aria-pressed="true">Plain language</button>
    <button type="button" id="v-full" aria-pressed="false">Full detail</button>
  </div>
</div></div>
<div class="scopewrap"><p class="scope" id="scope"><b>Version 2 is the Provider tab only.</b> It covers the 27 EU member states. The Analyst and Scenarios tabs, and the United Kingdom, are in the four country tools of BENEFITS Deliverable 2.2 (Spain, Italy, Greece and the United Kingdom), which carry the same provider figures.</p></div>
<p class="status" id="status" aria-live="polite"></p>
<iframe id="view" title="Provider tool"></iframe>
<script>
"use strict";
var BLOCKS=@@BLOCKS@@;
var LITE_D=@@LITE_D@@;
var TPL_FULL=@@TPL_FULL@@;
var TPL_LITE=@@TPL_LITE@@;
var ORDER=@@ORDER@@;
var BUILT=@@BUILT@@;
var cur={cc:null,view:"lite"};
var $=function(i){return document.getElementById(i);};
var esc=function(s){return String(s).replace(/<\//g,"<\\/");};
function page(cc,view){
  var C=BLOCKS[cc];
  if(view==="full")return TPL_FULL.replace("__COUNTRY_JSON__",esc(JSON.stringify(C)));
  return TPL_LITE.split("@@COUNTRY_NAME@@").join(C.name).replace("@@DATA@@",esc(JSON.stringify(LITE_D[cc])));}
/* The two views name the same ten inputs differently. Carry them across a switch so that
   changing view never loses what the user entered. */
var MAP=[["p-serv","f-svc"],["p-people","f-people"],["p-prof","f-prof"],["p-cost","f-cost"],["p-eps","f-eps"],
         ["p-ref","f-ref"],["p-shock","f-shock"],["p-staff","f-staff"],["p-casesper","f-casesper"],["p-unitcost","f-unitcost"]];
function readInputs(){
  var f=$("view"),d;try{d=f.contentDocument;}catch(e){return null;}if(!d)return null;
  var k=(cur.view==="full")?0:1,o={};
  MAP.forEach(function(m,i){var e=d.getElementById(m[k]);if(e)o[i]=e.value;});return o;}
function writeInputs(o){
  if(!o)return;var f=$("view"),d=f.contentDocument,w=f.contentWindow,k=(cur.view==="full")?0:1;
  MAP.forEach(function(m,i){var e=d.getElementById(m[k]);if(!e||o[i]==null)return;
    if(e.tagName==="SELECT"&&![].some.call(e.options,function(x){return x.value===o[i];}))return;
    if(e.value===o[i])return;e.value=o[i];
    e.dispatchEvent(new w.Event("input",{bubbles:true}));e.dispatchEvent(new w.Event("change",{bubbles:true}));});}
function fit(){var f=$("view");try{var h=f.contentDocument.documentElement.scrollHeight;if(h)f.style.height=(h+8)+"px";}catch(e){}}
function status(){
  var C=BLOCKS[cur.cc],der=(C.income_basis==="derived");
  $("status").innerHTML="<b>"+C.name+".</b> "+(der
    ?'<span class="derived">Income effect estimated</span> There is no microsimulation for '+C.name+': the extra income a service brings is estimated from national minimum-income data. Every other figure carries its own source and grade.'
    :'<span class="model">Income effect modelled</span> Income effects come from EUROMOD run on EU-SILC data for '+C.name+'. Every other figure carries its own source and grade.')
    +" Built "+BUILT+".";}
function show(cc,view,keep){
  var carry=keep?readInputs():null;
  cur.cc=cc;cur.view=view;
  $("v-lite").setAttribute("aria-pressed",view==="lite");$("v-full").setAttribute("aria-pressed",view==="full");
  $("cc").value=cc;status();
  var f=$("view");
  f.onload=function(){writeInputs(carry);fit();
    try{var ro=new f.contentWindow.ResizeObserver(fit);ro.observe(f.contentDocument.documentElement);}catch(e){}};
  f.srcdoc=page(cc,view);
  try{history.replaceState(null,"","#"+cc+"-"+view);}catch(e){}}
(function(){
  var sel=$("cc");ORDER.forEach(function(cc){var o=document.createElement("option");o.value=cc;o.textContent=BLOCKS[cc].name;sel.appendChild(o);});
  sel.addEventListener("change",function(){show(sel.value,cur.view,true);});
  $("v-lite").addEventListener("click",function(){if(cur.view!=="lite")show(cur.cc,"lite",true);});
  $("v-full").addEventListener("click",function(){if(cur.view!=="full")show(cur.cc,"full",true);});
  var m=/^#([A-Z]{2})-(lite|full)$/.exec(location.hash||"");
  show((m&&BLOCKS[m[1]])?m[1]:ORDER[0],m?m[2]:"lite",false);
  window.addEventListener("resize",fit);
})();
</script>
</body>
</html>
"""


def js(v):
    return json.dumps(v, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def load_blocks(from_shipped):
    blocks = {}
    if from_shipped:
        for cc, f in (("ES", "es"), ("IT", "it"), ("EL", "el")):
            p = os.path.join(MACH, "country_%s.json" % f)
            blocks[cc] = json.load(io.open(p, encoding="utf-8"))
    else:
        for cc in EU27:
            p = os.path.join(HERE, "data", cc + ".json")
            if os.path.exists(p):
                blocks[cc] = json.load(io.open(p, encoding="utf-8"))
        missing = [c for c in EU27 if c not in blocks]
        assert not missing or "--partial" in sys.argv, "no data block for: %s" % " ".join(missing)
    return blocks


def main():
    from_shipped = "--blocks-from-shipped" in sys.argv
    blocks = load_blocks(from_shipped)
    full = io.open(os.path.join(HERE, "full_template.html"), encoding="utf-8").read()
    lite = io.open(os.path.join(HERE, "lite_template.html"), encoding="utf-8").read()
    svg, emblem = views.footer_parts(views.shipped_footer())
    lite = lite.replace("@@LOGO_SVG@@", svg).replace("@@EMBLEM_IMG@@", emblem)
    lite_d = {cc: views.lite_data(views.extract_static(C)) for cc, C in blocks.items()}
    order = sorted(blocks, key=lambda c: blocks[c]["name"])
    page = (SHELL.replace("@@BLOCKS@@", js(blocks)).replace("@@LITE_D@@", js(lite_d))
            .replace("@@TPL_FULL@@", js(full)).replace("@@TPL_LITE@@", js(lite))
            .replace("@@ORDER@@", js(order)).replace("@@BUILT@@", js(datetime.date.today().isoformat())))
    assert "@@" not in page.replace("@@COUNTRY_NAME@@", "").replace("@@DATA@@", ""), "unfilled shell placeholder"
    os.makedirs(OUT, exist_ok=True)
    name = ("TEST_3_shipped_countries.html" if from_shipped else
            ("TEST_partial.html" if "--partial" in sys.argv else "BENEFITS_Provider_Tool_EU27_v2.html"))
    fn = os.path.join(ROOT if name.startswith("BENEFITS_") else OUT, name)
    io.open(fn, "w", encoding="utf-8", newline="\n").write(page)
    print(fn, len(page.encode("utf-8")) // 1024, "KB,", len(blocks), "countries")


if __name__ == "__main__":
    main()
