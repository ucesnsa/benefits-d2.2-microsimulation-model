#!/usr/bin/env python3
"""Negative tests: every assertion here must fail on a page that breaks it.

Each mutation breaks exactly the thing one assertion claims to protect. The test
passes when that assertion FAILS on the mutated page, which is what proves the
assertion is load-bearing rather than decorative.

Covers star propagation across the whole provider panel (three separate mutations,
because a mark can be dropped from a single row while the headline still carries one),
deep-link tab restore, and the decile chart summing to the headline as displayed.

The provider-panel claims carry two mutations each, because each has two halves that
can break independently. Two of them require the assertion to re-derive rather than
read:

  * the catchment conversion is asserted by re-deriving the central extra demand from
    the surface and comparing it, not by reading the factor off the page: a page can
    print the right factor and still do the arithmetic wrong.
  * the entered unit cost is asserted on the raw money, which must move in proportion
    to the price, not on the rendered cell: the cell carries the marks, so a page that
    accepts a price and then ignores it can still show the dagger.
"""
import importlib.util, sys, tempfile, shutil
from pathlib import Path

# Resolve from this file, never from an absolute path. It used to hard-code the
# working tree, so running it from anywhere else silently tested the working tree
# instead of the copy in front of you, and reported a pass for it. In an exported
# tree on another machine that path does not exist at all.
ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cb", ROOT / "check_browser.py")
cb = importlib.util.module_from_spec(spec)
# Keep our own arguments: loading check_browser.py replaces sys.argv, so read the
# filter first or it is gone by the time the cases are selected.
_ARGS = [a for a in sys.argv[1:] if not a.startswith("-")]
sys.argv = ["check_browser.py"]
spec.loader.exec_module(cb)
CHROME = cb.find_chrome()

UK = ROOT / "uk/tools/dial_tool_uk.html"
ES = ROOT / "europe/Spain/tools/dial_tool_spain.html"
IT = ROOT / "europe/Italy/tools/dial_tool_italy.html"

CASES = [
    ("ticks_drawn_in_every_browser", UK,
     '\'<div class="ticks" id="tk-\'', '\'<div class="ticks" id="NOTk-\'',
     "the drawn tick container is renamed, so the explicit marks cannot be found"),
    ("poverty_anchored_leads_relative_beside", UK,
     '<div class="row" data-pov="anchored">', '<div class="row" data-pov="relative">',
     "the anchored row is mislabelled, so the anchored figure no longer leads"),
    ("poverty_nulls_skipped_no_false_zero", UK,
     'var povFmt=function(v){return (v>=0?"+":"")', 'var povFmt=function(v){return "NaN"+(v>=0?"+":"")',
     "a value renders as NaN"),
    ("poverty_scope_sentence_is_country_specific", UK,
     '<b class="pov-scope">Scope:</b>', '<b class="pov-scope">Coverage:</b>',
     "the scope sentence loses its marker"),
    ("poverty_uk_baseline_note_gated_to_uk", UK,
     'COUNTRY.code==="GB"?\' <span id="pov-uk-baseline">', 'COUNTRY.code==="ZZ"?\' <span id="pov-uk-baseline">',
     "the UK-only sentence is suppressed in the UK"),
    ("poverty_uk_baseline_note_gated_to_uk", ES,
     'COUNTRY.code==="GB"?\' <span id="pov-uk-baseline">', 'COUNTRY.code!=="ZZ"?\' <span id="pov-uk-baseline">',
     "the UK-only sentence leaks into Spain"),
    # L6: the state the tools were actually in. Four capacity rows rested on borrowed
    # elasticities and a borrowed shock anchor and rendered with no mark at all, and
    # the old propagation assertion looked only at the headline, so it passed.
    ("stars_propagate_on_every_provider_row", ES,
     "+n0(addL)+' / '+n0(addC)+' / '+n0(addH)+''+oorMk+mk(gDem)+",
     "+n0(addL)+' / '+n0(addC)+' / '+n0(addH)+''+oorMk+",
     "the extra-demand row loses its mark while still resting on borrowed elasticities"),
    ("stars_propagate_on_every_provider_row", ES,
     "'+addStaff.toLocaleString(LOC)+oorMk+mk(gDem)+'",
     "'+addStaff.toLocaleString(LOC)+oorMk+'",
     "the extra-caseworkers row loses its mark"),
    ("stars_propagate_on_every_provider_row", ES,
     "<b>Benefit-cost ratio (BCR)</b>'+mk(gHead)+'",
     "<b>Benefit-cost ratio (BCR)</b>'+'",
     "the BCR loses the grade it inherits from the headline"),
    # L8: a deep link must come back to the tab it was shared from.
    ("deep_link_restores_its_tab", ES,
     'if(st.t){var b=document.getElementById("tab-"+st.t);if(b)b.click();}',
     'if(st.t){var b=document.getElementById("tab-NOPE-"+st.t);if(b)b.click();}',
     "the tab restore is broken, as renderScenario() used to break it by throwing"),
    # L12: the decile chart must sum to the headline the user reads above it. The
    # mutation has to break ONE side only: changing fmtM itself moves both together
    # and the two still agree, which is the whole point of comparing through the
    # formatter. So take the bar caption off the formatter instead.
    ("decile_chart_sums_to_headline_as_displayed", ES,
     'Sum = "+fmtM(dec.reduce((a,b)=>a+b,0))+" "',
     'Sum = "+(dec.reduce((a,b)=>a+b,0)).toFixed(1)+" "',
     "the bar caption stops going through the deflating formatter while the headline still does"),
    ("decile_chart_states_its_price_base", ES,
     '), in "+PRICE_BASE+".";',
     ').";',
     "the bar caption stops stating which year the money is in"),
    # R2: the state the UK tool was actually in. Freezing the cost-effectiveness row at
    # one epsilon is invisible unless something moves the selector and looks.
    ("cost_effectiveness_responds_to_epsilon", UK,
     'var cev=exchDelta(sScen)==null?null:w/exchDelta(sScen);',
     'var cev=exchDelta(sScen)==null?null:((DATA.wevm[sScen]||[])[2]||0)/exchDelta(sScen);',
     "the row is pinned to eps=1 again, as it was, while the headline above it still moves"),
    # R3: a ratio rendered through the money formatter, which applies the deflator.
    # Harmless while the UK deflator is 1, so mutate a country where it is not.
    ("cost_effectiveness_is_one_at_eps_zero_for_a_pure_transfer", ES,
     'var ceFmt=fmtRatio;',
     'var ceFmt=function(v){return fmtBn(v);};',
     "the ratio goes back through the deflating money formatter"),
    # A ratio rendered in the country locale. es-ES and it-IT write one point zero
    # zero zero as "1,000", which an English-reading reviewer reads as one thousand. The
    # tools are in English; money takes the locale and a dimensionless figure does not.
    ("cost_effectiveness_is_one_at_eps_zero_for_a_pure_transfer", ES,
     'const fmtRatio=v=>(v<0?"-":"")+Math.abs(v).toFixed(3);',
     'const fmtRatio=v=>v.toLocaleString(LOC,{minimumFractionDigits:3,maximumFractionDigits:3});',
     "a ratio goes back into the country locale, printing 1.000 as 1,000"),
    # Put one price-base sentence into the state that produces a truncated
    # export line. The old assertion passed on "price base." because a fragment of the
    # note is still in the note; this requires the line to open a sentence and name a year.
    # Mutate the DEFAULT service's note: the export reports whichever service is selected,
    # and the default is the one a reader exports without touching anything.
    ("export_price_base_quotes_the_service_note", UK,
     "'Citizens Advice annual stats; StepChange data'. No price year is stated and no evidence was found that the cost was checked against the named source. PRICE BASE:",
     "'Citizens Advice annual stats; StepChange data'. No price year is stated and no evidence was found that the cost was checked against the named source. Its target price base is:",
     "the default service loses its explicit price-base sentence, so the export truncates mid-sentence"),
    # ---- V: the caveats, the service-load card and the export ----
    ("service_load_poverty_from_own_surface", ES,
     'sPovA=sDelta("anchored_bhc_headcount_k");sPovR=sDelta("relative_bhc_headcount_k");',
     'sPovA=sDelta("relative_bhc_headcount_k");sPovR=sDelta("anchored_bhc_headcount_k");',
     "the card shows the relative figure where the anchored one belongs"),
    ("service_load_affected_dash_is_labelled", ES,
     'if(!sAffOn)sAffRow+=', 'if(false)sAffRow+=',
     "the dash loses the sentence saying why it is a dash"),
    ("dial_caveat_on_its_own_dial_only", ES,
     'var m=COUNTRY.dial_caveats;\n  if(!id||!m||!m[id])return "";',
     'var m=COUNTRY.dial_caveats;\n  if(!m)return "";id=Object.keys(m)[0];if(!m[id])return "";',
     "the caveat is pinned to one dial and shows under every dial"),
    ("employer_zero_states_it_is_an_input_limit", IT,
     "derives by proxy, and the proxy is ours rather than EUROMOD's",
     "derives by proxy, and the proxy is the model author's",
     "the row presents a class this build invents as the model's own rule"),
    ("export_price_base_quotes_the_service_note", ES,
     '+"Price base: analyst money shown in 2024 terms. Provider figure: "+priceBaseOf(s)+"\\n"',
     '+"Price base: provider figures 2024-equivalent; analyst money shown in 2024 terms\\n"',
     "the export goes back to one blanket claim over notes that disagree with it"),
    # ---- W1: Horizon Europe Article 17 visibility ----
    ("eu_emblem_displayed", ES,
     '<img class="emblem"', '<img class="emblem-was"',
     "the emblem is dropped from the footer"),
    ("eu_emblem_at_least_as_prominent", ES,
     '.fbrand img.emblem{height:50px', '.fbrand img.emblem{height:30px',
     "the emblem is shrunk below the project logo beside it"),
    ("eu_disclaimer_verbatim", ES,
     'Views and opinions expressed are however those of the author(s) only',
     'Views and opinions are those of the authors only',
     "the Article 17.3 disclaimer is paraphrased instead of quoted"),
    ("eu_grant_number_stated", ES,
     'Project number: 101179032.', 'Project number: withheld.',
     "the grant agreement number is removed"),
    # ---- The catchment conversion. The dangerous failure is not a wrong factor,
    # which is loud, but the silent fallback to 1, which restores the incoherent
    # arithmetic and looks exactly like a page that was never converted.
    ("catchment_converted_at_the_surface_household_size", ES,
     'return (pb&&pb.population_k!=null&&pb.units_k)?(pb.population_k/pb.units_k):1;})();',
     'return 1;})();',
     "the household-size factor falls back to 1, silently restoring the per-unit arithmetic"),
    ("catchment_converted_at_the_surface_household_size", UK,
     'const affFrac=aff/(unitsK*HH_SIZE);',
     'const affFrac=aff/unitsK;',
     "the affected share goes back to a share of units against a catchment in people"),
    # ---- The defaults must be in force with nothing entered ----
    ("unit_cost_defaults_to_the_shipped_value", ES,
     'el.value=String(unitCostOf(s));',
     'el.value=String(unitCostOf(s)*2);',
     "the field opens on something other than the shipped value, so a reader who touches "
     "nothing is not seeing the default"),
    ("unit_cost_defaults_to_the_shipped_value", UK,
     'var COST_OVERRIDE={};',
     'var COST_OVERRIDE={"Debt advice (Citizens Advice, StepChange)":9};',
     "an override is present before the user has entered anything"),
    # ---- An entered value must reach the figures ----
    ("user_unit_cost_changes_the_downstream_figure", ES,
     'const addBudget=unmetC*uCost;',
     'const addBudget=unmetC*s.unitCost;',
     "the entered cost is accepted and then ignored downstream, which is the worst of both"),
    ("user_unit_cost_changes_the_downstream_figure", UK,
     'else COST_OVERRIDE[s.name]=v;',
     'else COST_OVERRIDE[s.name]=s.unitCost;',
     "typing a value stores the default instead of what was typed"),
    # ---- The marks. Two mutations, because the assertion has two halves: our star
    # must go, and the dagger must appear. Breaking one at a time proves both are read.
    ("user_unit_cost_drops_our_mark_and_carries_its_own", ES,
     'function unitCostClasses(s){return costOverridden(s)?["user_supplied"]:fieldClasses(s,["unitCost"]);}',
     'function unitCostClasses(s){return fieldClasses(s,["unitCost"]);}',
     "a figure resting on the user's own cost keeps carrying OUR mark for it"),
    ("user_unit_cost_drops_our_mark_and_carries_its_own", UK,
     "?'<sup class=\"mark usermark\" title=\"rests on a unit cost you entered, not on ours\">&dagger;</sup>':\"\";}",
     "?'':\"\";}",
     "the user-supplied dagger is not rendered, so an entered value is indistinguishable "
     "from one of our national sources"),
    # ---- The export. A copied figure that does not say whose cost it used claims a
    # provenance it does not have, so both halves are mutated: the status and the ledger.
    ("export_records_the_unit_cost_override", ES,
     '+(costOverridden(s)?("ENTERED BY THE USER (our shipped default was "+fmtGBP(s.unitCost)+")")',
     '+(false?("ENTERED BY THE USER (our shipped default was "+fmtGBP(s.unitCost)+")")',
     "the export calls a value the user entered the shipped default"),
    ("export_records_the_unit_cost_override", UK,
     '+"All unit costs in this configuration: "+costLedger()+"\\n"',
     '+""',
     "the per-service ledger is dropped, so an override on an unselected service is invisible"),
    # ---- URL state. A shared configuration that drops the overrides shows the
    # recipient different numbers from the ones the sharer was looking at.
    ("url_state_round_trips_a_unit_cost_override", ES,
     'uc:COST_OVERRIDE},',
     'uc:{}},',
     "the fragment stops carrying the overrides, so a shared link shows our costs, not theirs"),
    ("url_state_round_trips_a_unit_cost_override", UK,
     'if(v!=null&&isFinite(+v)&&+v>=0)COST_OVERRIDE[x.name]=+v;});}',
     '});}',
     "the fragment carries the overrides and the restore drops them on the floor"),
    # ---- Reset ----
    ("reset_restores_the_shipped_unit_cost", ES,
     'function resetCost(all){if(all)COST_OVERRIDE={};else{var s=svc();if(s)delete COST_OVERRIDE[s.name];}',
     'function resetCost(all){if(all)COST_OVERRIDE={};else{var s=svc();if(s&&false)delete COST_OVERRIDE[s.name];}',
     "the per-service reset does not clear the override it claims to clear"),
    ("reset_restores_the_shipped_unit_cost", UK,
     'setCostField();renderProvider();\n  if(window.__encodeState)window.__encodeState();}',
     'setCostField();\n  if(window.__encodeState)window.__encodeState();}',
     "reset restores the field but not the figures under it, so the panel shows the "
     "default price against a total still computed from the override"),
    # ---- The BCR at a zero running cost. Two mutations, because the row and the
    # funding-case sentence read the same variable and either could lose the guard on its
    # own. The second is the worse of the two: the panel reads n/a while the sentence a
    # provider pastes into a bid claims a benefit-cost ratio of Infinity.
    ("provider_bcr_finite_at_a_zero_running_cost", UK,
     'const bcr=(bcrRaw!=null&&isFinite(bcrRaw))?bcrRaw:null,sens=people*o.sensC;',
     'const bcr=bcrRaw,sens=people*o.sensC;',
     "the finite guard is dropped, so a zero running cost divides through to Infinity"),
    ("provider_bcr_finite_at_a_zero_running_cost", ES,
     '+(bcr==null?"":", a benefit-cost ratio of "+bcr.toFixed(2)',
     '+(bcrRaw==null?"":", a benefit-cost ratio of "+bcrRaw.toFixed(2)',
     "the row is guarded but the funding-case sentence is not, so the panel reads n/a "
     "while the text quotes a ratio of Infinity"),
    # ---- The mean-gain row. Two mutations: the gate that keeps it off a loss, and
    # the sign of the figure inside it. Removing the gate has to be mutated on an EU tool,
    # because the UK's loss dials report a gaining share of zero and are held off the row
    # by the older winners>0 gate regardless.
    ("mean_gain_row_only_where_the_total_is_a_gain", ES,
     'if(uK&&winners>0&&full&&full[0]!=null&&full[0]>0){',
     'if(uK&&winners>0&&full&&full[0]!=null){',
     "the gate goes, so a downturn prints an aggregate loss per gaining household under "
     "a label saying gain"),
    ("mean_gain_row_only_where_the_total_is_a_gain", UK,
     'var winnersN=(winners/100)*uK*1e3, mg=(full[0]*DEF*1e6)/winnersN;',
     'var winnersN=(winners/100)*uK*1e3, mg=-(full[0]*DEF*1e6)/winnersN;',
     "the gate holds but the figure inside it is negated, so a gain is shown as a loss"),
]

print(f"chrome: {CHROME}\n")
# Optional substring filter, so one assertion can be exercised on its own while the
# rest of a change is still in progress. No argument runs everything.
_want = _ARGS
if _want:
    CASES = [c for c in CASES if any(w in c[0] for w in _want)]
    print(f"filtered to {len(CASES)} case(s) matching {_want}\n")
allgood = True
for target, tool, old, new, why in CASES:
    html = tool.read_text(encoding="utf-8")
    if html.count(old) != 1:
        print(f"[SETUP FAIL] {target} ({tool.name}): mutation anchor found {html.count(old)} times")
        allgood = False
        continue
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / tool.name
        p.write_text(html.replace(old, new, 1), encoding="utf-8")
        res, err = cb.run_one(CHROME, tool.stem, p, Path(td))
    if err:
        print(f"[ERROR] {target}: {err}")
        allgood = False
        continue
    by = {r["test"]: r["ok"] for r in res}
    failed = target in by and not by[target]
    others = sorted(t for t, ok in by.items() if not ok and t != target)
    verdict = "CAUGHT" if failed else "MISSED -- assertion is not load-bearing"
    print(f"{'OK ' if failed else 'BAD'}  {target}  ({tool.stem})")
    print(f"        mutation: {why}")
    print(f"        {verdict}" + (f"; also failed: {others}" if others else ""))
    allgood = allgood and failed

print("\nNEGATIVE TESTS:",
      f"ALL {len(CASES)} MUTATIONS CAUGHT; EVERY ASSERTION IS LOAD-BEARING" if allgood
      else "AT LEAST ONE ASSERTION IS NOT LOAD-BEARING")
sys.exit(0 if allgood else 1)
