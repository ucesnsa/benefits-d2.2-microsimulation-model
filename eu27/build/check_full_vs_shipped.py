"""Positive control for the full view: filled with a SHIPPED country block, its provider panel
must render exactly what the shipped tool's Provider tab renders, for many input configurations.

For each of ES, IT, EL: instantiate full_template.html with the shipped country_<cc>.json, load
it and the shipped tool in headless Chrome, drive both through the same configurations (every
service x three profiles x three eps x two references x two shocks), and compare the innerHTML of
#p-value, #p-shockout and #p-evidence. Run: py check_full_vs_shipped.py
"""
import html, io, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import DELIV, chrome, short_workdir, file_url  # noqa: E402
CHROME = chrome()
TOOLS = {"es": os.path.join("europe", "Spain", "tools", "dial_tool_spain.html"),
         "it": os.path.join("europe", "Italy", "tools", "dial_tool_italy.html"),
         "el": os.path.join("europe", "Greece", "tools", "dial_tool_greece.html")}

PROBE = r"""<pre id="__X" style="display:none"></pre><script>
window.addEventListener("load",function(){setTimeout(function(){
 var out=[],set=function(i,v){var e=document.getElementById(i);e.value=v;e.dispatchEvent(new Event("change"));};
 var svs=[].map.call(document.querySelectorAll("#p-serv option"),function(o){return o.value;});
 var refs=[].map.call(document.querySelectorAll("#p-ref option"),function(o){return o.value;});
 var profs=["Lowest incomes (deciles 1-3)","Low-to-middle (deciles 4-6)","Broad mix (all deciles)"];
 /* The input labels too: a label left unfilled (for example an empty currency symbol) is a defect
    the result panels alone would not show. */
 out.push(["__labels__","","","","",JSON.stringify([].map.call(document.querySelectorAll("#provider label"),function(l){return l.textContent;})),"",""]);
 svs.forEach(function(sv){profs.forEach(function(pr){["0","1","2"].forEach(function(ep){[refs[0],refs[refs.length-1]].forEach(function(rf){["2","7"].forEach(function(sh){
   set("p-serv",sv);set("p-prof",pr);set("p-eps",ep);set("p-ref",rf);set("p-shock",sh);
   out.push([sv,pr,ep,rf,sh,document.getElementById("p-value").innerHTML,document.getElementById("p-shockout").innerHTML,
             document.getElementById("p-evidence").innerHTML]);});});});});});
 document.getElementById("__X").textContent=JSON.stringify(out);
},800);});
</script>"""


def run(page_html, tag):
    i = page_html.rfind("</body>")
    with short_workdir() as wd:
        fn = os.path.join(wd, "probe_%s.html" % tag)
        io.open(fn, "w", encoding="utf-8").write(page_html[:i] + PROBE + page_html[i:])
        dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=60000",
                              "--user-data-dir=" + os.path.join(wd, "prof"), "--dump-dom", file_url(fn)],
                             capture_output=True, text=True, encoding="utf-8", timeout=300).stdout
    m = re.search(r'<pre id="__X"[^>]*>(.*?)</pre>', dom, re.S)
    if not m or not m.group(1).strip():
        sys.exit("probe returned nothing for " + tag)
    return json.loads(html.unescape(m.group(1)))


def main():
    tpl = io.open(os.path.join(HERE, "full_template.html"), encoding="utf-8").read()
    bad = 0
    global RESULT
    RESULT = {}
    for cc, rel in TOOLS.items():
        block = io.open(os.path.join(DELIV, "europe", "tool_machinery", "country_%s.json" % cc), encoding="utf-8").read()
        mine = run(tpl.replace("__COUNTRY_JSON__", block), "full_" + cc)
        ship = run(io.open(os.path.join(DELIV, rel), encoding="utf-8").read(), "ship_" + cc)
        assert len(mine) == len(ship) and len(mine) > 0, (cc, len(mine), len(ship))
        diffs = [(a[:5], k) for a, b in zip(mine, ship) for k in (5, 6, 7) if a[k] != b[k]]
        bad += len(diffs)
        RESULT[cc.upper()] = len(mine)
        print("%s: %d configurations x 3 panels compared, %d differ" % (cc.upper(), len(mine), len(diffs)))
        for d in diffs[:5]:
            print("   ", d)
    os.makedirs(os.path.join(HERE, "checks"), exist_ok=True)
    json.dump({"configurations_per_country": RESULT, "differences": bad},
              io.open(os.path.join(HERE, "checks", "full_vs_shipped.json"), "w", encoding="utf-8"), indent=1)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
