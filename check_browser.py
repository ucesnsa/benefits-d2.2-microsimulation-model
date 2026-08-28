#!/usr/bin/env python3
"""Browser check: load each tool page in a real browser engine and assert its contract.

`check_drift.py` proves the embedded grid matches the canonical surface. This
script proves the page built from that grid behaves: it loads the tool in
headless Chrome, drives the controls, and asserts the invariants the tools are
supposed to hold (four tabs render, zero page errors, one tick per computed point
and those ticks drawn rather than left to the browser, sliders bounded by the grid,
interpolation clamped, one reform control active at a time, the baseline reads zero,
the fiscal card appears only where the surface carries fiscal, the poverty panel leads
with the anchored figure and skips null fields without a false zero, and the spine and
currency on the face come from the country block).

Expectations are derived from each country's own data, not hardcoded, so the
same suite runs unchanged against all four tools.

Usage:
    python3 check_browser.py                 # all four countries
    python3 check_browser.py greece          # one country
    python3 check_browser.py uk spain        # several
"""

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# This script prints epsilon, the euro sign and the pound sign, in test details it takes
# straight off the page. On a Windows console the default encoding is cp1252, which has
# no epsilon, so the run died in print() partway through the UK block with a
# UnicodeEncodeError and reported nothing further. It was survivable only by setting
# PYTHONIOENCODING before calling, and a check that needs a wrapper to run is a check
# someone will eventually run without one. Handled here instead: UTF-8 where the stream
# supports it, and a replacing encoder where it does not, so the worst case is a question
# mark in one detail string rather than a dead run and a blank matrix.
def _make_stdio_total():
    for stream in ("stdout", "stderr"):
        s = getattr(sys, stream, None)
        if s is None:
            continue
        try:
            s.reconfigure(encoding="utf-8", errors="replace")      # Python 3.7+
        except (AttributeError, ValueError, OSError):
            try:
                import io as _io
                buf = getattr(s, "buffer", None)
                if buf is not None:
                    setattr(sys, stream, _io.TextIOWrapper(
                        buf, encoding="utf-8", errors="replace", line_buffering=True))
            except Exception:                                       # noqa: BLE001
                pass


_make_stdio_total()

ROOT = Path(__file__).resolve().parent

TOOLS = {
    "uk": ("UK", ROOT / "uk" / "tools" / "dial_tool_uk.html"),
    "spain": ("Spain", ROOT / "europe" / "Spain" / "tools" / "dial_tool_spain.html"),
    "italy": ("Italy", ROOT / "europe" / "Italy" / "tools" / "dial_tool_italy.html"),
    "greece": ("Greece", ROOT / "europe" / "Greece" / "tools" / "dial_tool_greece.html"),
}

# Chrome or Chromium, found the same way on either machine. CHROME_BINARY overrides
# everything if set. The Windows entries are built from the environment rather than
# hard-coded drive letters, so a machine that puts Program Files elsewhere still works.
def _chrome_candidates():
    env = os.environ.get("CHROME_BINARY")
    out = [env] if env else []
    if sys.platform == "win32":
        for base in filter(None, (os.environ.get("ProgramFiles"),
                                  os.environ.get("ProgramFiles(x86)"),
                                  os.environ.get("LOCALAPPDATA"))):
            out.append(os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"))
            out.append(os.path.join(base, "Chromium", "Application", "chrome.exe"))
    out += [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "google-chrome",
        "chromium",
        "chrome",
    ]
    return out


CHROME_CANDIDATES = _chrome_candidates()

RESULT_ID = "BENEFITS_TEST_RESULT"

# Installed before the page's own scripts so it sees every error they raise.
CAPTURE = """<script>
window.__errs=[];
window.addEventListener("error",function(e){window.__errs.push("error: "+(e.message||e.type));});
window.addEventListener("unhandledrejection",function(e){window.__errs.push("unhandledrejection: "+e.reason);});
(function(){var ce=console.error;console.error=function(){window.__errs.push("console.error: "+
  Array.prototype.join.call(arguments," "));return ce.apply(console,arguments);};})();
</script>"""

# Runs after the page has initialised. Writes base64 JSON into the result node.
HARNESS = """<div id="__RESULT_ID__" style="display:none"></div>
<script>
window.addEventListener("load",function(){setTimeout(function(){
  var T=[], A=function(name,ok,detail){T.push({test:name,ok:!!ok,detail:detail===undefined?"":String(detail)});};
  try{
    var dialIds=Object.keys(GRID.dials), hasFiscal=!!(GRID.dials[dialIds[0]].points[0]||{}).fiscal;
    var tabs=["home","analyst","provider","scenarios"], rendered=[];
    tabs.forEach(function(t){
      var b=document.getElementById("tab-"+t); if(b)b.click();
      var p=document.getElementById(t);
      rendered.push(t+"="+(p?p.textContent.replace(/\\s+/g," ").trim().length:0));
    });
    A("tabs_render", rendered.every(function(r){return +r.split("=")[1]>200;}), rendered.join(" "));

    document.getElementById("tab-analyst").click();

    // one slider per dial, bounded by the grid, one tick per computed point
    // (the count comes from the dial's own magnitudes; nothing assumes eleven)
    var bounds=[], ticks=[], built=0;
    dialIds.forEach(function(id){
      var s=document.getElementById("dl-"+id); if(!s)return; built++;
      var M=GRID.dials[id].magnitudes, mn=Math.min.apply(null,M), mx=Math.max.apply(null,M);
      if(+s.min!==mn||+s.max!==mx) bounds.push(id+" slider["+s.min+","+s.max+"] grid["+mn+","+mx+"]");
      var dl=document.getElementById("ticks-"+id);
      var n=dl?dl.querySelectorAll("option").length:0;
      if(n!==M.length) ticks.push(id+" ticks="+n+" points="+M.length);
    });
    A("dials_built", built===dialIds.length, built+" of "+dialIds.length);
    A("slider_bounds_are_grid_ends", bounds.length===0, bounds.join("; "));
    A("ticks_match_computed_points", ticks.length===0, ticks.join("; "));

    // interpolation is clamped: far outside the grid equals the end point
    var clampFails=[];
    dialIds.forEach(function(id){
      var M=GRID.dials[id].magnitudes, mn=Math.min.apply(null,M), mx=Math.max.apply(null,M);
      var loEnd=interpDial(id,mn,2).wevm, hiEnd=interpDial(id,mx,2).wevm;
      if(interpDial(id,mn-1000,2).wevm!==loEnd||interpDial(id,mx+1000,2).wevm!==hiEnd) clampFails.push(id);
    });
    A("interpolation_clamped_no_extrapolation", clampFails.length===0, clampFails.join(", "));

    // baseline magnitude reads exactly zero welfare
    var zeroFails=[];
    dialIds.forEach(function(id){
      var b=GRID.dials[id].baseline_magnitude;
      GRID.meta.eps_grid.forEach(function(e,i){ if(interpDial(id,b,i).wevm!==0) zeroFails.push(id+"@eps"+e); });
    });
    A("baseline_point_is_zero", zeroFails.length===0, zeroFails.join(", "));

    // exactly one reform control active: moving one dial returns the others to baseline
    var exclusive=[];
    if(dialIds.length>1){
      var a=dialIds[0], b=dialIds[1];
      var sa=document.getElementById("dl-"+a), sb=document.getElementById("dl-"+b);
      sb.value=GRID.dials[b].magnitudes[GRID.dials[b].magnitudes.length-1];
      sb.dispatchEvent(new Event("input"));
      sa.value=GRID.dials[a].magnitudes[GRID.dials[a].magnitudes.length-1];
      sa.dispatchEvent(new Event("input"));
      if(+sb.value!==GRID.dials[b].baseline_magnitude) exclusive.push(b+" left at "+sb.value);
    }
    A("one_control_at_a_time", exclusive.length===0, exclusive.join("; "));

    // the toggle, where the country has one, resets the dials and vice versa
    if(COUNTRY.toggle){
      var tg=document.getElementById("tg-"+COUNTRY.toggle.id)||document.querySelector('input[type="checkbox"]');
      var d0=document.getElementById("dl-"+dialIds[0]);
      d0.value=GRID.dials[dialIds[0]].magnitudes[10]; d0.dispatchEvent(new Event("input"));
      if(tg){ tg.checked=true; tg.dispatchEvent(new Event("change")); }
      A("toggle_resets_dials", +document.getElementById("dl-"+dialIds[0]).value===GRID.dials[dialIds[0]].baseline_magnitude,
        tg?"":"toggle input not found");
      if(tg){ tg.checked=false; tg.dispatchEvent(new Event("change")); }
    } else {
      A("toggle_absent_as_expected", !document.querySelector('input[type="checkbox"]'), "country carries no toggle");
    }

    // the epsilon lens moves the headline and does not reset the active dial
    var dTest=dialIds[0], sT=document.getElementById("dl-"+dTest);
    sT.value=GRID.dials[dTest].magnitudes[GRID.dials[dTest].magnitudes.length-1];
    sT.dispatchEvent(new Event("input"));
    var epsBtns=document.getElementById("a-eps").children;
    var before=document.getElementById("a-welfare").textContent;
    epsBtns[epsBtns.length-1].click();
    var after=document.getElementById("a-welfare").textContent;
    A("epsilon_lens_responds", before!==after, "eps0 vs eps"+GRID.meta.eps_grid.slice(-1)[0]);
    A("epsilon_lens_keeps_dial", +document.getElementById("dl-"+dTest).value!==GRID.dials[dTest].baseline_magnitude);
    epsBtns[2].click();

    // the analyst fiscal card is data-gated on the surface carrying fiscal
    var card=document.getElementById("a-fiscal-card");
    A("fiscal_card_matches_surface", hasFiscal?!!card:!card,
      hasFiscal?("surface has fiscal, card "+(card?"present":"MISSING")):("no fiscal on surface, card "+(card?"PRESENT":"absent")));

    // the face reads its spine and currency from the country block
    document.getElementById("tab-provider").click();
    var ev=document.getElementById("p-evidence"), evTxt=ev?ev.textContent:"";
    var plain=SPINE.label.replace(/&pound;/g,"\\u00a3").replace(/&euro;/g,"\\u20ac");
    A("spine_label_from_country_block", evTxt.indexOf(plain)>=0, "block label: "+plain);
    // The applied figure of 16,300 is the number the WELLBY bands were built from, so
    // it belongs on the face. What must never happen is citing it bare, because on its
    // own it reads as an HM Treasury figure and it is not one. So this assertion requires
    // that wherever the figure appears, its derivation appears with it. Requiring its
    // absence instead would enforce a rule that forbids the right answer.
    // Scoped to the rendered panels: document.body.textContent would include this script's own source.
    var faceTxt="";
    ["home","analyst","provider","scenarios"].forEach(function(t){
      var b=document.getElementById("tab-"+t); if(b)b.click();
      var pnl=document.getElementById(t); if(pnl)faceTxt+=" "+pnl.textContent;});
    var ft=document.getElementById("foot-note"); if(ft)faceTxt+=" "+ft.textContent;
    var fund2=document.getElementById("p-funding"); if(fund2)faceTxt+=" "+fund2.value;
    var bare=false, at=faceTxt.indexOf("16,300");
    while(at>=0){
      var ctx=faceTxt.slice(Math.max(0,at-160),at+160);
      if(!(/13,000/.test(ctx)&&/2019/.test(ctx)))bare=true;
      at=faceTxt.indexOf("16,300",at+1);
    }
    A("uprated_spine_cited_with_its_derivation", !bare,
      bare?"16,300 appears without 13,000 and 2019 nearby":"every mention carries its base");
    // Scoped to elements that display this tool's OWN computed money. Prose may
    // legitimately cite a foreign figure (the UK source behind a transferred
    // value) or an engine parameter name containing "$".
    var foreign=["£","€","$"].filter(function(s){return s!==CUR;});
    var moneyTxt="";
    ["#a-welfare","#a-epsstrip","#a-fiscal-card","#s-fiscal","#p-value","#p-headline"].forEach(function(sel){
      var e=document.querySelector(sel); if(e)moneyTxt+=" "+e.textContent;});
    [].forEach.call(document.querySelectorAll(".headline, .row .v, #p-evidence table"),function(e){moneyTxt+=" "+e.textContent;});
    var fund=document.getElementById("p-funding"); if(fund)moneyTxt+=" "+fund.value;
    // The spine label is the one legitimate foreign-currency citation on an EU face:
    // it names the GBP base and the GBP applied figure the local spine derives from.
    // Remove it before scanning, so the assertion stays strict about every other
    // figure rather than being loosened wholesale.
    moneyTxt=moneyTxt.split(plain).join(" ");
    var found=foreign.filter(function(s){return moneyTxt.indexOf(s)>=0;});
    A("computed_money_uses_country_currency", found.length===0, found.join(" "));

    // the footer states this country's own provenance
    var foot=document.getElementById("foot-note");
    A("footer_states_country_provenance",
      !!foot&&COUNTRY.provenance&&foot.textContent.indexOf(COUNTRY.provenance.replace(/&times;/g,"\\u00d7").slice(0,40))>=0,
      foot?foot.textContent.slice(0,60):"foot-note missing");

    // ---- assertions for the render pass ----
    var dialIds2=Object.keys(GRID.dials);
    // ticks: one per computed magnitude, and native painting not disabled
    var tickBad=[];
    dialIds2.forEach(function(id){
      var dl=document.getElementById("ticks-"+id), s2=document.getElementById("dl-"+id);
      var n=dl?dl.querySelectorAll("option").length:0;
      if(n!==GRID.dials[id].magnitudes.length) tickBad.push(id+" ticks="+n);
      var ap=getComputedStyle(s2).appearance||getComputedStyle(s2).webkitAppearance;
      if(ap&&ap!=="auto") tickBad.push(id+" appearance="+ap+" (native ticks suppressed)");
    });
    A("ticks_one_per_computed_point", tickBad.length===0, tickBad.join("; "));

    // Drawn ticks. The assertion above passes on Chrome whether or not the marks are
    // drawn, because Chrome paints datalist ticks natively; Firefox paints none. So
    // assert the DRAWN marks: one <i class="tick"> per magnitude, inside the dial, each
    // with a real position and non-zero box. Remove the explicit rendering and this fails.
    var drawnBad=[];
    // measure on the visible tab: a hidden panel reports every box as zero
    document.getElementById("tab-analyst").click();
    dialIds2.forEach(function(id){
      var box=document.getElementById("tk-"+id);
      if(!box){drawnBad.push(id+" no drawn tick container");return;}
      var marks=box.querySelectorAll("i.tick");
      var M=GRID.dials[id].magnitudes;
      if(marks.length!==M.length){drawnBad.push(id+" drawn="+marks.length+" points="+M.length);return;}
      var r0=marks[0].getBoundingClientRect();
      if(!(r0.height>0)) drawnBad.push(id+" drawn ticks have no height");
      var lefts=[].map.call(marks,function(m){return m.style.left;});
      if(lefts.some(function(L){return !L||L.indexOf("%")<0;})) drawnBad.push(id+" tick without a % position");
      var uniq={};lefts.forEach(function(L){uniq[L]=1;});
      if(Object.keys(uniq).length!==M.length) drawnBad.push(id+" ticks overlap: "+Object.keys(uniq).length+" distinct of "+M.length);
    });
    A("ticks_drawn_in_every_browser", drawnBad.length===0, drawnBad.join("; "));

    document.getElementById("tab-analyst").click();
    var dA=dialIds2[0], sA=document.getElementById("dl-"+dA);
    sA.value=GRID.dials[dA].magnitudes[GRID.dials[dA].magnitudes.length-1]; sA.dispatchEvent(new Event("input"));

    // "per household" in the UK was wrong: the UK models benefit units. The noun now
    // comes from the block, so the assertion expects the block's own noun.
    var anch=document.querySelector("#a-welfare .anchor");
    var unitOne=COUNTRY.unit_noun_singular||"household";
    A("anchoring_rendered", !!anch && anch.textContent.indexOf("per "+unitOne)>=0,
      anch?anch.textContent.slice(0,70):"no .anchor beside the headline");

    var card=document.getElementById("a-fiscal-card");
    var ceTxt=card?card.textContent:"";
    A("cost_effectiveness_present", !card || /Welfare per unit of fiscal cost/.test(ceTxt),
      card?"":"no fiscal card on this surface");
    // sweep every stored magnitude of every dial: the card must never print a
    // non-finite value. The zero-cost branch itself is unreachable through the UI,
    // because the card is removed whenever no dial is off baseline.
    var nonFinite=[];
    dialIds2.forEach(function(id){
      var s3=document.getElementById("dl-"+id); if(!s3)return;
      GRID.dials[id].magnitudes.forEach(function(mg){
        s3.value=mg; s3.dispatchEvent(new Event("input"));
        var c3=document.getElementById("a-fiscal-card");
        if(c3&&/Infinity|NaN|\u221e/.test(c3.textContent)) nonFinite.push(id+"@"+mg);
      });
      s3.value=GRID.dials[id].baseline_magnitude; s3.dispatchEvent(new Event("input"));
    });
    A("cost_effectiveness_finite_at_every_point", nonFinite.length===0, nonFinite.slice(0,4).join(", "));
    sA.value=GRID.dials[dA].magnitudes[GRID.dials[dA].magnitudes.length-1]; sA.dispatchEvent(new Event("input"));

    var pts=document.querySelectorAll("#a-epscurve circle.epspt");
    A("epsilon_curve_marks_computed_points", pts.length===GRID.meta.eps_grid.length,
      pts.length+" of "+GRID.meta.eps_grid.length);

    // stars: worst grade wins, computed not stored
    var RANK={national_source:0,national_derived:0,borrowed_adjusted:1,borrowed_unadjusted:2,assumption:2};
    document.getElementById("tab-provider").click();
    var svcName=document.getElementById("p-serv").value;
    var svcObj=DATA.services.filter(function(x){return x.name===svcName;})[0];
    // the value headline depends on the outcome valuation and the spine it rides,
    // not on the operational parameters, so the expected grade is built from those
    var cls=[]; var svcObj2=svcObj;
    var oo=DATA.outcomes&&DATA.outcomes[svcName]; if(oo&&oo.provenance)cls.push(oo.provenance);
    if(COUNTRY.wellby_spine&&COUNTRY.wellby_spine.provenance)cls.push(COUNTRY.wellby_spine.provenance);
    var worst=0; cls.forEach(function(c){var r=RANK[c]; if(r==null)r=2; if(r>worst)worst=r;});
    var expect=worst===0?"":(worst===1?"*":"**");
    var headRow=[].slice.call(document.querySelectorAll("#p-value .row")).filter(function(r){return /HEADLINE/.test(r.textContent);})[0];
    var shown=headRow?(headRow.querySelector(".mark")||{}).textContent||"":"";
    A("stars_propagate_worst_grade", shown===expect, "shown '"+shown+"' expected '"+expect+"' from "+cls.join(","));
    A("no_stored_propagated_field", !(oo&&("grade" in oo||"mark" in oo)), "outcomes entry must not store a grade");

    // Every provider row that rests on a graded input must carry the worst grade of
    // the inputs IT uses. The assertion above only ever looked at the headline, so
    // four rows resting on borrowed elasticities and a borrowed shock anchor rendered
    // unmarked and it passed. Grade each row from the block and compare what is shown.
    var gradeFrom=function(list){var w=0;list.forEach(function(c){if(c==null)return;
      var r=RANK[c];if(r==null)r=2;if(r>w)w=r;});return w===0?"":(w===1?"*":"**");};
    var sp=(DATA.shockInterp&&DATA.shockInterp.provenance)||{};
    var pv=(svcObj&&svcObj.provenance)||{};
    var shockCls=[sp.aff3,sp.aff5];
    var demandCls=[pv.elastLow,pv.elastCentral,pv.elastHigh].concat(shockCls);
    var budgetCls=demandCls.concat([pv.unitCost]);
    var ROWS=[
      ["losing an earner",              gradeFrom(shockCls)],
      ["Extra demand on you",           gradeFrom(demandCls)],
      ["Unmet demand",                  gradeFrom(demandCls)],
      ["Extra caseworkers",             gradeFrom(demandCls)],
      ["Extra running cost",            gradeFrom(budgetCls)],
      ["Benefit-cost ratio",            expect],
      ["Monetised total",               expect]
    ];
    var rowMark=function(needle){
      var all=[].slice.call(document.querySelectorAll("#p-value .row, #p-shockout .row"));
      var row=all.filter(function(r){return r.textContent.indexOf(needle)>=0;})[0];
      if(!row)return null;
      var marks=[].slice.call(row.querySelectorAll(".mark"))
        .map(function(m){return m.textContent;})
        .filter(function(x){return x==="*"||x==="**";});
      return marks.length?marks.sort(function(a,b){return b.length-a.length;})[0]:"";
    };
    var badRows=[];
    ROWS.forEach(function(pair){
      var got=rowMark(pair[0]);
      if(got===null){badRows.push(pair[0]+" ROW MISSING");return;}
      if(got!==pair[1])badRows.push(pair[0]+" shows '"+got+"' expected '"+pair[1]+"'");
    });
    A("stars_propagate_on_every_provider_row", badRows.length===0, badRows.join(" | "));

    // A deep link must come back to the tab it was shared from. applyState called
    // renderScenario(), which does not exist, so it threw into its own catch and
    // skipped the tab restore that follows it. currentState always writes a scenario
    // key, so this failed on every link, silently. Drive the real path: capture state
    // from a non-default tab, move away, apply it back, and check the tab returned.
    document.getElementById("tab-scenarios").click();
    var wantScen=(COUNTRY.scenarios_list||DATA.scenarios||[])[1]||null;
    if(wantScen){var ssel=document.getElementById("s-scen");if(ssel){ssel.value=wantScen;
      ssel.dispatchEvent(new Event("change",{bubbles:true}));}}
    var shared=window.__getState().state;
    document.getElementById("tab-home").click();
    var beforeTab=[].slice.call(document.querySelectorAll('[id^="tab-"]'))
      .filter(function(b){return b.getAttribute("aria-selected")==="true";})[0];
    window.__setState(shared);
    var afterTab=[].slice.call(document.querySelectorAll('[id^="tab-"]'))
      .filter(function(b){return b.getAttribute("aria-selected")==="true";})[0];
    var afterId=afterTab?afterTab.id:"(none)";
    A("deep_link_restores_its_tab", afterId==="tab-"+shared.t,
      "shared from "+shared.t+", landed on "+afterId+" (was "+(beforeTab?beforeTab.id:"?")+" before applying)");
    A("deep_link_restores_its_scenario", !wantScen||document.getElementById("s-scen").value===wantScen,
      "wanted "+wantScen+", got "+(document.getElementById("s-scen")||{}).value);

    /* The cost-effectiveness row must move when the epsilon selector moves, because it
       is welfare at that epsilon over a cost that does not depend on epsilon. On the UK
       tool it was a stored constant computed once at epsilon=1 and shown unchanged at
       every epsilon, while the welfare headline in the same panel moved. Nothing was
       looking, so it sat there for a month contradicting the panel's own sentence.
       Also asserted: at epsilon=0 a pure transfer reads exactly 1.000, which is that
       sentence, and the row is a ratio so it must not carry a currency symbol. */
    document.getElementById("tab-scenarios").click();
    var sEpsBtns=document.getElementById("s-eps").children;
    var ceAt=function(i){sEpsBtns[i].click();
      var el=document.getElementById("s-ce");return el?el.textContent.trim():"";};
    var ce0=ceAt(0), ceTop=ceAt(sEpsBtns.length-1);
    A("cost_effectiveness_responds_to_epsilon", ce0!==ceTop && ce0!=="" && ceTop!=="",
      "eps"+GRID.meta.eps_grid[0]+" '"+ce0+"' vs eps"+GRID.meta.eps_grid.slice(-1)[0]+" '"+ceTop+"'");
    /* Pick a scenario whose exchequer cost is a pure transfer: no income tax and no
       contribution response on its grid point, so at epsilon=0 welfare IS the cost. */
    var pureScen=null;
    (DATA.sc15||[]).forEach(function(s){
      if(pureScen)return;
      var f=DATA.fiscal&&DATA.fiscal[s], b0=DATA.fiscal&&DATA.fiscal.baseline;
      if(!f||!b0)return;
      var it=(f.income_tax_delta_m!=null)?f.income_tax_delta_m-b0.income_tax_delta_m:(f.it!=null?f.it-b0.it:null);
      var si=(f.sic_delta_m!=null)?f.sic_delta_m-b0.sic_delta_m:(f.ni!=null?f.ni-b0.ni:null);
      if(it!=null&&si!=null&&Math.abs(it)<1e-6&&Math.abs(si)<1e-6)pureScen=s;});
    if(pureScen){
      var ssel2=document.getElementById("s-scen");ssel2.value=pureScen;
      ssel2.dispatchEvent(new Event("change",{bubbles:true}));
      var pure0=ceAt(0);
      /* Exactly the four characters "1.000", with a decimal POINT, in every country.
         Comparing against the locale's own rendering of one would be the assertion
         encoding the defect: through toLocaleString(LOC), es-ES and it-IT write one as
         "1,000", and these tools are in English, a ratio has no country, and "1,000"
         reads as one thousand. The ratio goes through fmtRatio, and this assertion is
         what holds it there. */
      A("cost_effectiveness_is_one_at_eps_zero_for_a_pure_transfer", pure0==="1.000",
        pureScen+" reads "+pure0+" at eps=0; a ratio must render as 1.000 with a decimal "
        +"point in every locale (this locale writes one as "
        +(1).toLocaleString(LOC,{minimumFractionDigits:3,maximumFractionDigits:3})+")");
    } else {
      A("cost_effectiveness_is_one_at_eps_zero_for_a_pure_transfer", true,
        "no pure-transfer scenario on this tool");
    }
    A("cost_effectiveness_is_a_ratio_not_an_amount",
      (document.getElementById("s-ce")||{textContent:""}).textContent.indexOf(CUR)<0,
      "row carries no currency symbol: it is welfare per unit of cost");

    /* ---- service-load card ----
       The poverty rows must be this country's own, read from its own surface at the
       grid point the scenario sits on, on the same basis as the Provider tab. The
       expectation is recomputed here from the surface rather than hardcoded, so the
       assertion fails if the card ever starts showing a different measure. */
    var sSelP=document.getElementById("s-scen");
    var sOnPoint=null;
    (COUNTRY.scenarios||[]).forEach(function(s){
      if(sOnPoint||!s.dial||s.mag==null)return;
      var gg=GRID.dials[s.dial];
      if(gg&&gg.magnitudes&&gg.magnitudes.indexOf(s.mag)>=0)sOnPoint=s;});
    if(sOnPoint){
      sSelP.value=sOnPoint.id; sSelP.dispatchEvent(new Event("change",{bubbles:true}));
      var svcTxt=(document.getElementById("s-service")||{textContent:""}).textContent;
      var pN=interpPoverty(sOnPoint.dial,sOnPoint.mag),
          pB=interpPoverty(sOnPoint.dial,baselineMag(sOnPoint.dial)),
          wantPov=null;
      if(pN&&pB&&pN.anchored_bhc_headcount_k!=null&&pB.anchored_bhc_headcount_k!=null){
        var dv=pN.anchored_bhc_headcount_k-pB.anchored_bhc_headcount_k;
        wantPov=(dv>=0?"+":"")+dv.toLocaleString(LOC,{minimumFractionDigits:1,maximumFractionDigits:1});}
      var sRows=[].slice.call(document.querySelectorAll("[data-spov]"));
      var sKinds=sRows.map(function(r){return r.getAttribute("data-spov");});
      var sVals=sRows.map(function(r){return ((r.querySelector(".v")||{}).textContent||"").trim();});
      A("service_load_poverty_from_own_surface",
        sKinds.length===2 && sKinds[0]==="anchored" && sKinds[1]==="relative"
        && (wantPov===null || sVals[0]===wantPov),
        sOnPoint.id+" expects anchored '"+wantPov+"' first; rows "+sKinds.join(",")
        +" values "+sVals.join(" / "));
      /* The affected count is a dash where it is not modelled, and says why. A dash with
         no explanation, or an explanation with a number beside it, are both wrong. */
      var affRow=document.querySelector("[data-affected]");
      var affState=affRow?affRow.getAttribute("data-affected"):"missing";
      var affNote=document.getElementById("s-affected-note");
      A("service_load_affected_dash_is_labelled",
        (affState==="modelled" && !affNote)
        || (affState==="none" && !!affNote && /does not transfer/.test(affNote.textContent)),
        "affected="+affState+", note "+(affNote?"present":"absent"));
    } else {
      A("service_load_poverty_from_own_surface", true, "no scenario sits on a stored grid point");
      A("service_load_affected_dash_is_labelled", true, "not applicable");
    }
    sEpsBtns[2].click();
    document.getElementById("tab-provider").click();

    // Counts and nouns in prose are generated from the block through {{TOKEN}}
    // placeholders. If a string carrying one is rendered without going through the
    // filler, the token shows on the face; that happened to the capacity caveat while
    // this was being written. Scoped to the rendered panels, not document.body, which
    // would match the filler's own source in the script.
    var rendered="";
    ["home","analyst","provider","scenarios"].forEach(function(t){
      var b2=document.getElementById("tab-"+t); if(b2)b2.click();
      var pnl=document.getElementById(t); if(pnl)rendered+=" "+pnl.textContent;});
    var fn2=document.getElementById("foot-note"); if(fn2)rendered+=" "+fn2.textContent;
    var fx=document.getElementById("p-funding"); if(fx)rendered+=" "+fx.value;
    var leaked=rendered.match(/\\{\\{[A-Z_]+\\}\\}/g)||[];
    A("no_unfilled_text_tokens", leaked.length===0, leaked.join(", "));

    /* ---- per-dial caveats ----
       A caveat belongs to one dial. It must show when that dial is the active reform and
       must not show under any other, or a reader moving between dials carries a
       qualification that does not apply to what is on screen. */
    document.getElementById("tab-analyst").click();
    var dcKeys=Object.keys(COUNTRY.dial_caveats||{}).filter(function(k){return !!GRID.dials[k];});
    var dcBad=[];
    dcKeys.forEach(function(id){
      /* A caveat may be a plain string or {short, detail}. The visible part is what has
         to be on the face beside the figure, so take the stub from that; a stub taken
         from the object would be "[object Object]" and the assertion would pass on a
         caveat that renders nothing. Tags stripped, because the face carries text. */
      var _cv=COUNTRY.dial_caveats[id];
      var stub=String((typeof _cv==="string")?_cv:(_cv&&_cv.short)||"").replace(/<[^>]+>/g,"").slice(0,45);
      var mg=GRID.dials[id].magnitudes;
      onDial(id, mg[mg.length-1]);
      var own=(document.getElementById("a-fiscal-card")||{textContent:""}).textContent;
      if(own.indexOf(stub)<0)dcBad.push(id+": missing on its own dial");
      /* "Leaks" means the caveat appears under a dial that does not declare it. Two
         dials may legitimately declare the SAME caveat -- Italy's self-employed
         contribution note applies to both shock dials and to neither policy dial -- so
         the comparison is against what each dial declares, not against dial identity. */
      var stubOf=function(k){var c=COUNTRY.dial_caveats[k];
        return String((typeof c==="string")?c:(c&&c.short)||"").replace(/<[^>]+>/g,"").slice(0,45);};
      var other=dialIds2.filter(function(x){return x!==id&&stubOf(x)!==stub;})[0];
      if(other){
        var mo=GRID.dials[other].magnitudes;
        onDial(other, mo[mo.length-1]);
        var oth=(document.getElementById("a-fiscal-card")||{textContent:""}).textContent;
        if(oth.indexOf(stub)>=0)dcBad.push(id+": leaks onto "+other);}});
    A("dial_caveat_on_its_own_dial_only", dcBad.length===0,
      dcKeys.length?("dials "+dcKeys.join(", ")+(dcBad.length?" | "+dcBad.join("; "):"")) :
                    "no dial on this tool carries a caveat");

    /* ---- a fiscal row must say where its figure comes from ----
       A field that is zero at every point must carry a gloss, and that gloss must not
       blame the model. EUROMOD does simulate Italy's employer contributions, so calling a
       zero there "not a modelled result" states the opposite of the truth: a zero is our
       input conversion, not a limit of the model.
       Where the figure instead comes from a contract class this build proxies, the gloss
       must say whose rule the proxy is, because a reader has no other way to tell a model
       construction from ours. */
    var empRow=(COUNTRY.analyst_fiscal_rows||[]).filter(
      function(r){return r.field==="sic_employer_delta_m";})[0];
    var empOK=true, empDet="no employer row on this tool";
    if(empRow){
      var fk=Object.keys(DATA.fiscal||{});
      var allZero=fk.length>0 && fk.every(function(k){
        var v=(DATA.fiscal[k]||{}).sic_employer_delta_m;
        return v==null||Math.abs(v)<1e-9;});
      var blob=empRow.label+" "+(empRow.gloss||"");
      empOK=!/not a modelled result/i.test(blob);
      if(allZero)empOK=empOK && !!empRow.gloss && /this build/i.test(empRow.gloss);
      if(empRow.gloss && /proxy/i.test(empRow.gloss))
        empOK=empOK && /proxy is ours/i.test(empRow.gloss)
                    && !/proxy is (the )?(model author|EUROMOD)/i.test(empRow.gloss);
      empDet="zero at every point="+allZero+", gloss "+(empRow.gloss?"present":"absent")
             +(empRow.gloss&&/proxy/i.test(empRow.gloss)?", declares a proxy":"");}
    A("employer_zero_states_it_is_an_input_limit", empOK, empDet);
    document.getElementById("tab-provider").click();

    /* ---- the citable export must not overrule the notes ----
       The line it prints must be a quotation from the note of the very service being
       exported. One price base printed over every service contradicts the per-service
       notes wherever they differ. */
    var expTxt=(document.getElementById("p-export")||{value:""}).value;
    var sNow=svc();
    var sNote=String((sNow&&sNow.provenance_note&&sNow.provenance_note.unitCost)||"");
    var pbLine=(expTxt.split("\\n").filter(function(l){return l.indexOf("Price base:")===0;})[0]||"");
    var pbClaim=(pbLine.split("Provider figure: ")[1]||"").trim();
    /* Quoting the note is necessary and was not sufficient: a truncation is a quotation
       too. priceBaseOf takes the first case-insensitive "PRICE BASE ... ." and on two of
       the ten UK services no such sentence existed, so it landed mid-sentence inside
       "...the provider tab's own price base, confirmed from PROVIDER_TOOLREADY_2024
       rather than assumed." and the export told a reader the price base was "price base."
       This assertion passed on that, because the fragment is in the note. It now also
       requires the line to BEGIN a sentence -- either the explicit PRICE BASE opener or
       the "at <year> prices" form -- and to name a year, which is the thing a price base
       actually is. Every service now carries the explicit sentence. */
    var pbAt=sNote.indexOf(pbClaim);
    var pbInNote=pbAt>=0;
    /* The quotation must begin where a SENTENCE begins in the note. That is the test that
       catches a truncation, and quoting alone was not: priceBaseOf takes the first
       case-insensitive "PRICE BASE ... ." and where the note carried no such sentence it
       landed inside one, so the export told a reader the price base was "price base." and
       this assertion passed, because a fragment of the note is still in the note. */
    var pbStartsSentence=pbInNote&&(pbAt===0||/[.!?]\\s$/.test(sNote.slice(Math.max(0,pbAt-2),pbAt)));
    var pbNamesAYear=/20[0-9][0-9]/.test(pbClaim);
    A("export_price_base_quotes_the_service_note",
      pbClaim.length>0 && pbInNote && pbStartsSentence && pbNamesAYear,
      "claim '"+pbClaim.slice(0,70)+"' | in the note: "+pbInNote
      +" | begins a sentence in it: "+pbStartsSentence
      +(pbInNote&&!pbStartsSentence?(" (preceded by '"+sNote.slice(Math.max(0,pbAt-24),pbAt)+"')"):"")
      +" | names a year: "+pbNamesAYear);

    /* ---- Horizon Europe Article 17 visibility ----
       These are grant obligations, not house style, and a breach can reduce the grant
       (Article 17.5). Four separate requirements, asserted separately so a failure says
       which one broke:
         17.2  the emblem is displayed
         17.2  the funding statement accompanies it
         17.2  it is at least as prominent as any other logo shown with it
         17.3  the disclaimer appears, in the agreement's own words
       Plus the grant number, so the project can be identified. The disclaimer string is
       compared verbatim against Article 17.3 with the granting authority named; a
       paraphrase fails, which is the point. */
    var FUND_TXT="Funded by the European Union";
    var DISC_TXT="Views and opinions expressed are however those of the author(s) only and do not "
      +"necessarily reflect those of the European Union or the European Research Executive Agency. "
      +"Neither the European Union nor the granting authority can be held responsible for them.";
    var emb=document.querySelector("img.emblem");
    A("eu_emblem_displayed", !!emb && /^data:image\\/(png|jpe?g)/.test(emb.getAttribute("src")||""),
      emb?("alt='"+(emb.getAttribute("alt")||"")+"'"):"no img.emblem in the page");
    var footTxt=(document.querySelector("footer")||{textContent:""}).textContent;
    A("eu_funding_statement_present",
      (footTxt.indexOf(FUND_TXT)>=0) || (!!emb && (emb.getAttribute("alt")||"").indexOf(FUND_TXT)>=0),
      "in the footer text: "+(footTxt.indexOf(FUND_TXT)>=0)
      +", in the emblem alt: "+(!!emb&&(emb.getAttribute("alt")||"").indexOf(FUND_TXT)>=0));
    A("eu_disclaimer_verbatim", footTxt.indexOf(DISC_TXT)>=0,
      footTxt.indexOf(DISC_TXT)>=0?"":"footer does not carry Article 17.3 word for word");
    A("eu_grant_number_stated", footTxt.indexOf("101179032")>=0, "");
    /* Measured off the rendered page, not off the stylesheet, so a change anywhere in
       the cascade is caught. Every other logo in the footer counts, whatever it is. */
    var embH=emb?emb.getBoundingClientRect().height:0;
    var others=[].slice.call(document.querySelectorAll("footer img, footer svg"))
      .filter(function(n){return n!==emb;})
      .map(function(n){return {tag:n.tagName.toLowerCase(), h:n.getBoundingClientRect().height};});
    var tallest=others.reduce(function(a,b){return b.h>a?b.h:a;},0);
    A("eu_emblem_at_least_as_prominent", embH>0 && embH>=tallest,
      "emblem "+embH.toFixed(1)+"px against the tallest other logo "+tallest.toFixed(1)+"px"
      +" ("+others.map(function(o){return o.tag+" "+o.h.toFixed(0);}).join(", ")+")");

    // The decile chart must sum to the headline the reader sees above it. Both go
    // through fmtM, which applies the country deflator; if one stopped doing so the
    // chart would silently stop adding up to the figure it explains. Compared through
    // the formatter rather than by parsing localised numerals back out of the DOM.
    document.getElementById("tab-analyst").click();
    var dD=dialIds2[0];
    onDial(dD, GRID.dials[dD].magnitudes[GRID.dials[dD].magnitudes.length-1]);
    var eiD=GRID.meta.eps_grid.indexOf(aEps);
    var rD=interpDial(dD, mags[dD], eiD);
    var sumD=rD.deciles.reduce(function(a,b){return a+b;},0);
    var headTxt=(document.querySelector("#a-welfare .headline")||{textContent:""}).textContent.trim();
    var barTxt=(document.getElementById("a-barsum")||{textContent:""}).textContent;
    var sameFmt=fmtM(rD.wevm)===fmtM(sumD);
    A("decile_chart_sums_to_headline_as_displayed",
      sameFmt && headTxt.indexOf(fmtM(rD.wevm))>=0 && barTxt.indexOf(fmtM(sumD))>=0,
      "headline '"+headTxt+"' fmtM(wevm)='"+fmtM(rD.wevm)+"' fmtM(decile sum)='"+fmtM(sumD)
      +"' deflator="+DEF);
    A("decile_chart_states_its_price_base",
      /price|prices|20\\d\\d/.test(barTxt), "bar caption: "+barTxt.slice(0,120));
    document.getElementById("tab-provider").click();

    // legend on every panel that can be screenshotted alone
    var panelsNeedingLegend=["a-welfare","p-value","p-evidence","p-shockout"];
    var noLeg=panelsNeedingLegend.filter(function(id){var e=document.getElementById(id);
      return e && !(e.querySelector(".legend")||(e.parentNode&&e.parentNode.querySelector(".legend")));});
    A("legend_on_every_panel", noLeg.length===0, noLeg.join(", "));

    // extrapolation marker: only above the modelled point
    var sh=document.getElementById("p-shock"), du5=DATA.shockInterp.du5;
    sh.value=du5-1; sh.dispatchEvent(new Event("input"));
    var below=document.querySelectorAll("#p-shockout .oor").length;
    sh.value=du5+3; sh.dispatchEvent(new Event("input"));
    var above=document.querySelectorAll("#p-shockout .oor").length;
    A("extrapolation_marker_only_above_modelled", below===0&&above>0, "below="+below+" above="+above);

    // ---- poverty panel: anchored leads, relative beside it, nulls skipped ----
    var povRows=[].slice.call(document.querySelectorAll("[data-pov]"));
    var povKinds=povRows.map(function(r){return r.getAttribute("data-pov");});
    var povVals=povRows.map(function(r){return ((r.querySelector(".v")||{}).textContent||"").trim();});
    A("poverty_anchored_leads_relative_beside",
      povKinds.length===2 && povKinds[0]==="anchored" && povKinds[1]==="relative",
      povKinds.join(",")+" values "+povVals.join(" / "));
    // A null field must skip its row entirely. It must never arrive as NaN, as the word
    // undefined, or as a zero standing in for "not carried": four of the eight EU poverty
    // fields are legitimately null and a missing measure is not a measure of zero.
    var povBad=povVals.filter(function(v){return !v||/NaN|undefined/.test(v);});
    var povNote=document.getElementById("pov-note");
    var paneTxt=(document.getElementById("p-shockout")||{textContent:""}).textContent;
    A("poverty_nulls_skipped_no_false_zero",
      povBad.length===0 && !/NaN|undefined/.test(paneTxt),
      povBad.length?("bad values "+povBad.join(",")):"");
    // scope sentence present, and carrying THIS country's own population
    var popK=null, pvp=(GRID.dials[dialIds2[0]].points[0]||{}).poverty;
    if(pvp&&pvp.population_k!=null)popK=pvp.population_k/1000;
    var scopeOK=!!povNote&&/Scope:/.test(povNote.textContent);
    var scopeNum=scopeOK&&popK!=null&&povNote.textContent.indexOf(popK.toFixed(1).replace(".",(1.1).toLocaleString(LOC).indexOf(",")>0?",":"."))>=0;
    A("poverty_scope_sentence_is_country_specific", scopeOK&&scopeNum,
      scopeOK?("expected "+(popK==null?"?":popK.toFixed(1))+"m in: "+povNote.textContent.slice(-150)):"no scope sentence");
    // the UK-only baseline sentence, present in the UK and absent everywhere else
    var ukNote=document.getElementById("pov-uk-baseline");
    A("poverty_uk_baseline_note_gated_to_uk",
      (COUNTRY.code==="GB")===!!ukNote,
      "code="+COUNTRY.code+" sentence="+(ukNote?"present":"absent"));

    // citable export: carries its marks and its citation
    var ex=document.getElementById("p-export"), xv=ex?ex.value:"";
    A("export_present_with_copy_button", !!ex && !!document.getElementById("p-copy"), "");
    A("export_carries_marks_and_citation",
      /Cite as:/.test(xv) && /Provenance marks:/.test(xv) && (expect===""||xv.indexOf(expect)>=0),
      expect?("expected mark '"+expect+"' in the copied text"):"no mark expected for this service");

    // URL state round trip
    var wBefore=document.getElementById("a-welfare").textContent;
    if(window.__encodeState)window.__encodeState();   // the writer is debounced; flush it
    var frag=location.hash;
    document.getElementById("a-reset").click();
    var wReset=document.getElementById("a-welfare").textContent;
    var st=null; try{st=JSON.parse(decodeURIComponent(escape(atob(frag.replace(/^#/,"")))));}catch(e){}
    if(st)window.__setState(st);
    var wAfter=document.getElementById("a-welfare").textContent;
    A("url_state_round_trip", frag.length>1 && wReset!==wBefore && wAfter===wBefore,
      "fragment "+frag.length+" chars; before/reset/after differ correctly: "+(wAfter===wBefore));

    /* ==== The provider panel counts people, and accepts the user's own price.
       Everything below drives the real controls and reads the rendered page. ========= */

    // ---- The catchment conversion is applied, and its factor IS the surface's ----
    // The fallback when a surface carries no population_basis is 1, which silently
    // restores the incoherent arithmetic. This is the assertion that stops that shipping.
    var pb=(GRID.meta&&GRID.meta.population_basis)||null;
    var expHH=(pb&&pb.population_k!=null&&pb.units_k)?(pb.population_k/pb.units_k):null;
    var hhRow=document.querySelector("#p-shockout .row[data-hhsize]");
    var pageHH=hhRow?parseFloat(hhRow.getAttribute("data-hhsize")):null;
    // Stating the factor is not applying it. This RE-DERIVES the central extra demand
    // from the surface and the page's own inputs and compares it to what the page
    // rendered, so reverting affFrac to a share of units is caught even though the
    // factor is still printed correctly beside it. The first version of this assertion
    // read the attribute alone and missed exactly that mutation.
    var svcSel=DATA.services.filter(function(x){return x.name===document.getElementById("p-serv").value;})[0];
    var pplNow=+document.getElementById("p-people").value||0;
    var shk=+document.getElementById("p-shock").value, II=DATA.shockInterp;
    var affExp=shk<=0?0:(shk<=II.du3 ? II.aff3*(shk/II.du3)
                                     : II.aff3+(shk-II.du3)/(II.du5-II.du3)*(II.aff5-II.aff3));
    var unitsKExp=(pb&&pb.units_k!=null)?pb.units_k:null;
    var expAddC=(expHH!=null&&unitsKExp)&&svcSel
      ? svcSel.elastCentral*pplNow*(affExp/(unitsKExp*expHH)) : null;
    var demRow=document.querySelector("#p-shockout .row[data-extrac]");
    var pageAddC=demRow?parseFloat(demRow.getAttribute("data-extrac")):null;
    A("catchment_converted_at_the_surface_household_size",
      expHH!=null && pageHH!=null && Math.abs(pageHH-expHH)<1e-6 && pageHH>1
      && expAddC!=null && pageAddC!=null && Math.abs(pageAddC-expAddC)<1e-6,
      "factor: surface "+(expHH==null?"?":expHH.toFixed(6))+" vs page "
      +(pageHH==null?"missing":pageHH.toFixed(6))+"; applied: re-derived central extra demand "
      +(expAddC==null?"?":expAddC.toFixed(4))+" vs page "+(pageAddC==null?"missing":pageAddC.toFixed(4)));

    // ---- The shipped default is in force before anything is entered ----
    var ucEl=document.getElementById("p-unitcost");
    var costRow=function(){return document.querySelector("#p-shockout .row[data-unitcost]");};
    // The RAW money, not the rendered cell. The cell also carries the marks, so comparing
    // its text sees a dagger appearing as a figure changing: that let through a mutation
    // in which the entered cost was accepted and then ignored downstream.
    var budget=function(){var r=costRow();return r?parseFloat(r.getAttribute("data-budget")):null;};
    var svcNow=DATA.services.filter(function(x){return x.name===document.getElementById("p-serv").value;})[0];
    var dflt=svcNow?svcNow.unitCost:null;
    var budDefault=budget(), rowSrcDefault=costRow()?costRow().getAttribute("data-unitcost-source"):null;
    var dagDefault=costRow()?costRow().querySelectorAll(".v .usermark").length:0;
    var starDefault=costRow()?costRow().querySelectorAll(".v .mark:not(.usermark)").length:0;
    A("unit_cost_defaults_to_the_shipped_value",
      !!ucEl && dflt!=null && parseFloat(ucEl.value)===dflt
      && rowSrcDefault==="default" && dagDefault===0,
      "field "+(ucEl?ucEl.value:"missing")+" vs shipped "+dflt+", row source "+rowSrcDefault
      +", daggers "+dagDefault);

    // ---- An entered value changes the downstream figure ----
    var entered=Math.round(dflt*3)+7;   // never equal to the default, never a round number
    ucEl.value=String(entered);
    ucEl.dispatchEvent(new Event("input",{bubbles:true}));
    var budUser=budget(), rowSrcUser=costRow().getAttribute("data-unitcost-source");
    // The money must move IN PROPORTION to the price. Same gap, same demand, three times
    // the unit cost, so three times the budget: an assertion that only asked whether the
    // number changed would pass on a page that applied the new price to the wrong term.
    var budRatio=(budDefault>0&&budUser!=null)?(budUser/budDefault):null;
    var priceRatio=entered/dflt;
    A("user_unit_cost_changes_the_downstream_figure",
      rowSrcUser==="user" && costRow().getAttribute("data-unitcost")===String(entered)
      && budUser!=null && budDefault!=null && budUser!==budDefault
      && budRatio!=null && Math.abs(budRatio-priceRatio)<1e-9,
      "entered "+entered+" against our "+dflt+": extra running cost "+budDefault.toFixed(2)
      +" -> "+budUser.toFixed(2)+", ratio "+(budRatio==null?"?":budRatio.toFixed(6))
      +" against a price ratio of "+priceRatio.toFixed(6));

    // ---- The override loses OUR mark and gains its own ----
    // Not "has no mark": the row still carries whatever its other inputs earn. What must
    // go is the star the unit cost itself contributed, and what must appear is the dagger.
    var starUser=costRow().querySelectorAll(".v .mark:not(.usermark)").length;
    var dagUser=costRow().querySelectorAll(".v .usermark").length;
    var ourCostGrade=gradeOf(fieldClasses(svcNow,["unitCost"]));
    var otherGrade=gradeOf(demandClasses(svcNow));
    A("user_unit_cost_drops_our_mark_and_carries_its_own",
      dagUser===1 && dagDefault===0
      && gradeOf(budgetClasses(svcNow))===otherGrade
      && (ourCostGrade===""||starUser<=starDefault),
      "our cost grade '"+ourCostGrade+"', other inputs '"+otherGrade+"'; stars "
      +starDefault+" -> "+starUser+", daggers "+dagDefault+" -> "+dagUser);

    // ---- The export records which cost was used, and the entered value ----
    // The value is compared AS FORMATTED, not as a raw number. The first version of this
    // assertion looked for String(entered) and failed on the UK and Greece and passed on
    // Spain and Italy, because 1507 prints as "£1,507" and 3247 prints as "3247" in a
    // locale that does not group four digits. That tested the formatter, not the export.
    var xu=document.getElementById("p-export").value, enteredFmt=fmtGBP(entered);
    A("export_records_the_unit_cost_override",
      /ENTERED BY THE USER/.test(xu) && xu.indexOf(enteredFmt)>=0
      && /All unit costs in this configuration:/.test(xu) && /\\[entered\\]/.test(xu)
      && /\\[default\\]/.test(xu),
      "export names the entered value as "+enteredFmt+" and ledgers every service");

    // ---- URL state round-trips the override ----
    if(window.__encodeState)window.__encodeState();
    var ucFrag=location.hash, ucSt=null;
    try{ucSt=JSON.parse(decodeURIComponent(escape(atob(ucFrag.replace(/^#/,"")))));}catch(e){}
    document.getElementById("p-costresetall").click();     // wipe it locally
    var wipedSrc=costRow().getAttribute("data-unitcost-source");
    if(ucSt)window.__setState(ucSt);                       // and bring it back from the URL
    var backSrc=costRow().getAttribute("data-unitcost-source");
    var backVal=document.getElementById("p-unitcost").value;
    A("url_state_round_trips_a_unit_cost_override",
      !!ucSt && ucSt.p && ucSt.p.uc && ucSt.p.uc[svcNow.name]===entered
      && wipedSrc==="default" && backSrc==="user" && parseFloat(backVal)===entered,
      "fragment carries "+JSON.stringify(ucSt&&ucSt.p?ucSt.p.uc:null)
      +"; wiped->"+wipedSrc+", restored->"+backSrc+" at "+backVal);

    // ---- Reset restores the default ----
    document.getElementById("p-costreset").click();
    var budReset=budget(), rowSrcReset=costRow().getAttribute("data-unitcost-source");
    A("reset_restores_the_shipped_unit_cost",
      parseFloat(document.getElementById("p-unitcost").value)===dflt
      && rowSrcReset==="default"
      && budReset!=null && budDefault!=null && Math.abs(budReset-budDefault)<1e-9
      && costRow().querySelectorAll(".v .usermark").length===0,
      "back to "+dflt+", extra running cost "+(budReset==null?"?":budReset.toFixed(2))
      +" (was "+(budDefault==null?"?":budDefault.toFixed(2))+" before the override)");

    /* ---- The BCR is a number at every cost a reader can enter ----
       A running cost of zero is legal, the field's own minimum being zero, and an
       unguarded divide reaches the row and the funding-case sentence as the literal
       string "Infinity". Guarding only the BLANK field leaves that open. The analyst
       card already holds this rule as cost_effectiveness_finite_at_every_point, and its
       own comment says the zero-cost branch is unreachable there; this is the card
       where it is reachable.
       Both halves are asserted, because the row and the sentence read the same variable
       and either could be reverted on its own. */
    var costFld=document.getElementById("p-cost"), costWas=costFld.value;
    function bcrCell(){var out="";
      document.querySelectorAll("#p-value .row").forEach(function(r){
        if(/Benefit-cost ratio/.test(r.textContent)){var v=r.querySelector(".v");if(v)out=v.textContent.trim();}});
      return out;}
    costFld.value="0"; costFld.dispatchEvent(new Event("input"));
    var bcrZero=bcrCell(), fundZero=document.getElementById("p-funding").value||"";
    costFld.value=""; costFld.dispatchEvent(new Event("input"));
    var bcrBlank=bcrCell();
    costFld.value=costWas; costFld.dispatchEvent(new Event("input"));
    var bcrBack=bcrCell();
    var nonFin=/Infinity|NaN|\\u221e/;
    A("provider_bcr_finite_at_a_zero_running_cost",
      !nonFin.test(bcrZero) && !nonFin.test(fundZero) && bcrZero===bcrBlank
      && /[0-9]/.test(bcrBack),
      "zero cost reads '"+bcrZero+"', blank reads '"+bcrBlank+"', restored reads '"
      +bcrBack+"'; funding sentence non-finite: "+nonFin.test(fundZero));

    /* ---- The mean-gain row is a gain ----
       It is the unweighted total at epsilon zero over the number gaining, so on a loss
       dial the quotient is a loss and it was printed under a label saying gain, as far
       as minus 1.5 million a household on the Spanish unemployment dial. The UK escaped
       only because its loss dials report a gaining share of zero. Swept over every
       stored point of every dial: present exactly where the total is a gain, absent
       everywhere else, and never negative where it is present. */
    document.getElementById("tab-analyst").click();
    var mgBad=[], mgShown=0;
    Object.keys(GRID.dials).forEach(function(idG){
      var sG=document.getElementById("dl-"+idG); if(!sG)return;
      GRID.dials[idG].magnitudes.forEach(function(mgv){
        sG.value=mgv; sG.dispatchEvent(new Event("input"));
        var mgRow=null;
        document.querySelectorAll("#a-winlose .row").forEach(function(r){
          if(/Mean gain among those gaining/.test(r.textContent))mgRow=r;});
        var totG=interpDial(idG,mgv,0).wevm, winG=interpDial(idG,mgv,0).winners;
        if(mgRow){
          mgShown++;
          var cell=mgRow.querySelector(".v"), shown=cell?cell.textContent:"";
          if(!(totG>0))mgBad.push(idG+"@"+mgv+" shown on a total of "+totG.toFixed(1));
          else if(/[-\\u2212]/.test(shown))mgBad.push(idG+"@"+mgv+" reads "+shown);
        } else if(totG>0&&winG>0){mgBad.push(idG+"@"+mgv+" missing on a gain of "+totG.toFixed(1));}
      });
      sG.value=GRID.dials[idG].baseline_magnitude; sG.dispatchEvent(new Event("input"));
    });
    A("mean_gain_row_only_where_the_total_is_a_gain", mgBad.length===0,
      (mgBad.slice(0,3).join("; ")||"row shown at "+mgShown+" of the stored settings"));

    A("no_page_errors", window.__errs.length===0, window.__errs.join(" | "));
  }catch(err){ A("harness_completed", false, err&&err.stack?err.stack.split("\\n")[0]:String(err)); }
  var node=document.getElementById("__RESULT_ID__");
  node.textContent=btoa(unescape(encodeURIComponent(JSON.stringify(T))));
},400);});
</script>"""


def find_chrome():
    for c in CHROME_CANDIDATES:
        if Path(c).exists():
            return c
        found = shutil.which(c)
        if found:
            return found
    return None


def run_one(chrome, label, tool_path, workdir):
    html = tool_path.read_text(encoding="utf-8")
    if "<head>" not in html:
        return None, "page has no <head> to instrument"
    html = html.replace("<head>", "<head>" + CAPTURE, 1)
    harness = HARNESS.replace("__RESULT_ID__", RESULT_ID)
    if "</body>" in html:
        html = html.replace("</body>", harness + "</body>", 1)
    else:
        html += harness
    # Run from a copy so the shipped file is never modified.
    tmp = workdir / f"{tool_path.stem}__instrumented.html"
    tmp.write_text(html, encoding="utf-8")
    # --dump-dom emits UTF-8. Decode it as UTF-8 explicitly rather than letting
    # text=True pick the locale codec: on this Windows machine that is cp1252, which
    # raises UnicodeDecodeError the moment a page carries a character outside it, and
    # every one of these pages carries a currency symbol. Errors are replaced rather
    # than raised, because the harness result is base64 and survives a mangled byte
    # elsewhere in the DOM.
    proc = subprocess.run(
        [chrome, "--headless", "--disable-gpu", "--no-sandbox", "--no-first-run",
         "--virtual-time-budget=8000", "--dump-dom", tmp.as_uri()],
        capture_output=True, timeout=180,
    )
    stdout = proc.stdout.decode("utf-8", "replace")
    m = re.search(rf'id="{RESULT_ID}"[^>]*>([A-Za-z0-9+/=]*)<', stdout)
    if not m or not m.group(1):
        return None, "harness produced no result (page failed to load or script never ran)"
    return json.loads(base64.b64decode(m.group(1)).decode("utf-8")), None


COUNTS_FILE = Path(__file__).resolve().parent / ".suite_counts.json"


def write_counts(counted, failures, wanted):
    """Record how many assertions ran, so the published README cannot misstate it.

    A count nothing computes is a count that goes stale. The three mutation counts can be
    read straight out of the suites' CASES lists, but this one cannot: assertions
    register at run time inside the page, and several are country-conditional, so a
    static count of the source over-reads. The only figure that is true is the one a run
    produces, so a run writes it down.

    Only a clean full-set run writes. A partial or failing run leaves the previous file
    alone rather than replacing a good count with a partial one; the export stamper then
    warns that the count it holds is not from this build, which is the honest failure.
    """
    if failures or set(wanted) != set(TOOLS) or not counted:
        return
    per = sorted(set(counted.values()))
    blob = {
        "browser_per_country": per[0] if len(per) == 1 else None,
        "browser_per_country_by_tool": counted,
        "browser_total": sum(counted.values()),
        "countries": len(counted),
    }
    COUNTS_FILE.write_text(json.dumps(blob, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {COUNTS_FILE.name}: {blob['browser_total']} assertions over "
          f"{blob['countries']} tools")


def main(argv):
    wanted = [a.lower() for a in argv[1:]] or list(TOOLS)
    if "all" in wanted:
        wanted = list(TOOLS)
    unknown = [w for w in wanted if w not in TOOLS]
    if unknown:
        raise SystemExit(f"unknown country: {', '.join(unknown)}. "
                         f"Choose from: {', '.join(TOOLS)}, or all.")
    chrome = find_chrome()
    if not chrome:
        raise SystemExit("no Chrome or Chromium found; install one or set a path in "
                         "CHROME_CANDIDATES")
    failures = 0
    counted = {}
    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        for key in wanted:
            label, path = TOOLS[key]
            print(f"\n===== {label} =====")
            if not path.exists():
                print(f"  ERROR: {path} not found")
                failures += 1
                continue
            results, err = run_one(chrome, label, path, workdir)
            if err:
                print(f"  ERROR: {err}")
                failures += 1
                continue
            for r in results:
                status = "PASS" if r["ok"] else "FAIL"
                detail = f"  [{r['detail']}]" if r["detail"] else ""
                print(f"  {status}  {r['test']}{detail}")
            bad = [r for r in results if not r["ok"]]
            failures += len(bad)
            counted[label] = len(results)
            print(f"  {len(results) - len(bad)} of {len(results)} passed")
    print(f"\nOVERALL: {'PASS' if failures == 0 else f'FAIL ({failures} failing assertions)'}")
    write_counts(counted, failures, wanted)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
