"""Cross-check the two views of the built all-country tool against each other, country by country.

The full view computes in renderProvider() (the shipped D2.2 code); the lite view computes in
calc() (the plain-language tool's port of it). They are separate code paths over the same country block, so for every
country, service and configuration their headline (low, central, high), benefit-cost ratio, extra
demand and extra budget must agree. Also records any script error in either frame.

Run: py check_views.py [../BENEFITS_Provider_Tool_EU27_v2.html]
"""
import html, io, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import chrome, short_workdir, file_url  # noqa: E402
CHROME = chrome()

PROBE = r"""<pre id="__X" style="display:none"></pre><script>
(async function(){
 const sleep=ms=>new Promise(r=>setTimeout(r,ms));
 const f=document.getElementById("view"); const out={errors:[],rows:[]};
 const num=s=>{const m=String(s).replace(/−/g,"-").match(/-?[0-9][0-9,]*(\.[0-9]+)?/g);return m?m.map(x=>+x.replace(/,/g,"")):[];};
 function load(cc,view){return new Promise(res=>{f.addEventListener("load",function h(){f.removeEventListener("load",h);setTimeout(res,150);});show(cc,view,false);});}
 const profs=["Lowest incomes (deciles 1-3)","Broad mix (all deciles)"], epss=["0","1","2"];
 for(const cc of ORDER){
  await load(cc,"full"); let d=f.contentDocument,w=f.contentWindow;
  w.addEventListener("error",e=>out.errors.push(cc+" full: "+e.message));
  const svs=[...d.querySelectorAll("#p-serv option")].map(o=>o.value);
  const ref=d.getElementById("p-ref").value;
  const full={};
  for(const sv of svs)for(const pr of profs)for(const ep of epss){
    const set=(i,v)=>{const e=d.getElementById(i);e.value=v;e.dispatchEvent(new w.Event("change",{bubbles:true}));};
    set("p-serv",sv);set("p-prof",pr);set("p-eps",ep);
    const rows=[...d.querySelectorAll("#p-value .row")];
    const head=num(rows.find(r=>/HEADLINE/.test(r.textContent)).querySelector(".v").textContent);
    const bcrT=rows.find(r=>/Benefit-cost ratio/.test(r.textContent)).querySelector(".v").textContent;
    const b=d.querySelector("[data-budget]"), x=d.querySelector("[data-extrac]");
    full[sv+"|"+pr+"|"+ep]={head:head,bcr:bcrT==="n/a"?null:+bcrT,addC:+x.getAttribute("data-extrac"),budget:+b.getAttribute("data-budget"),cost:d.getElementById("p-cost").value,staff:d.getElementById("p-staff").value};
  }
  if(!svs.length)out.errors.push(cc+" full: no services");
  await load(cc,"lite"); d=f.contentDocument; w=f.contentWindow;
  if(typeof w.calc!=="function"){out.errors.push(cc+" lite: calc missing");continue;}
  /* The running cost each view fills in by itself, and the staff default, must agree too. */
  for(const sv of svs){const e=d.getElementById("f-svc");e.value=sv;e.dispatchEvent(new w.Event("change",{bubbles:true}));
    const F=full[sv+"|"+profs[0]+"|"+epss[0]], lc=d.getElementById("f-cost").value, ls=d.getElementById("f-staff").value;
    const ok=lc===F.cost&&ls===F.staff&&lc!=="";
    out.rows.push([cc,sv,"auto-cost","",ok?1:0,ok?"":JSON.stringify({full:[F.cost,F.staff],lite:[lc,ls]})]);}
  for(const k in full){const [sv,pr,ep]=k.split("|");
    let r;try{r=w.calc({sv:sv,people:"500",cost:full[k].cost,prof:pr,eps:ep,ref:ref,staff:full[k].staff,casesPer:"50",shock:"4",uc:{}});}
    catch(e){out.errors.push(cc+" lite calc: "+e.message);continue;}
    const F=full[k];
    const same=(a,b,tol)=>(a==null&&b==null)||(a!=null&&b!=null&&Math.abs(a-b)<=tol);
    const ok=[0,1,2].every(i=>same(Math.round(r.head[i]),F.head[i],0.5))&&same(r.bcr==null?null:+r.bcr.toFixed(2),F.bcr,0.005)
             &&same(r.addC,F.addC,1e-6*Math.max(1,Math.abs(F.addC)))&&same(r.addBudget,F.budget,1e-6*Math.max(1,Math.abs(F.budget)));
    out.rows.push([cc,sv,pr,ep,ok?1:0,ok?"":JSON.stringify({full:F,lite:{head:r.head.map(Math.round),bcr:r.bcr,addC:r.addC,budget:r.addBudget}})]);
  }
 }
 document.getElementById("__X").textContent=JSON.stringify(out);
})();
</script>"""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "BENEFITS_Provider_Tool_EU27_v2.html")
    page = io.open(src, encoding="utf-8").read()
    i = page.rfind("</body>")
    with short_workdir() as wd:
        fn = os.path.join(wd, "probe_views.html")
        io.open(fn, "w", encoding="utf-8").write(page[:i] + PROBE + page[i:])
        dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=900000",
                              "--user-data-dir=" + os.path.join(wd, "prof"), "--dump-dom", file_url(fn)],
                             capture_output=True, text=True, encoding="utf-8", timeout=1800).stdout
    m = re.search(r'<pre id="__X"[^>]*>(.*?)</pre>', dom, re.S)
    if not m or not m.group(1).strip():
        sys.exit("probe returned nothing")
    out = json.loads(html.unescape(m.group(1)))
    rows = out["rows"]
    bad = [r for r in rows if not r[4]]
    by = {}
    for r in rows:
        by.setdefault(r[0], [0, 0])
        by[r[0]][0] += 1
        by[r[0]][1] += r[4]
    print("configurations compared: %d, agreeing: %d, differing: %d, script errors: %d"
          % (len(rows), len(rows) - len(bad), len(bad), len(out["errors"])))
    print(" ".join("%s %d/%d" % (cc, v[1], v[0]) for cc, v in sorted(by.items())))
    for e in out["errors"][:10]:
        print("ERROR", e)
    for b in bad[:8]:
        print("DIFF", b[:4], b[5][:300])
    os.makedirs(os.path.join(HERE, "checks"), exist_ok=True)
    if src.endswith("BENEFITS_Provider_Tool_EU27_v2.html"):
        json.dump({"compared": len(rows), "agreeing": len(rows) - len(bad), "script_errors": len(out["errors"]),
                   "countries": len(by)}, io.open(os.path.join(HERE, "checks", "views.json"), "w", encoding="utf-8"), indent=1)
    sys.exit(1 if (bad or out["errors"] or len(by) != 27) else 0)


if __name__ == "__main__":
    main()
