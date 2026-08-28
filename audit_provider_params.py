#!/usr/bin/env python3
"""Provider-block parameter audit: every numeric key, its readers, its cross-country values.

One question per parameter: do the registry entry, the formula in `template.html`
that reads it, and the documentation carried beside it agree on what the parameter
is and what unit it carries. A value can be correctly sourced, correctly classified
and still be plugged in backwards.

The four response surfaces were audited field-by-field in G2. The
provider block never was. This enumerates it so the judgement pass reads a table
rather than the codebase.

For every numeric leaf in every one of the four `country_*.json` blocks outside
`grid` (the grid is the response surface, audited separately) it records:

  * the key, its canonical path, and its value in each of the four countries
  * every site in `europe/tool_machinery/template.html` that reads it, with the
    surrounding expression
  * the registry counterpart in `uk/model/parameters.py`, where one exists, with the
    registry's own `unit` and `source` strings
  * whether the key has no reader at all
  * whether the value is identical across all four countries

Indirection is resolved rather than reported as absent. Keys reached through
`COUNTRY.fiscal_rows`, `COUNTRY.fiscal_field`, `DATA.services.find(...)`,
`DATA.outcomes[s.name]`, `PROFILES[prof]`, `DATA.wevm[sScen]` and friends are never
named literally in the template. Each route is declared with the exact template text
that performs the lookup, and that text is re-checked against the live template on
every run, so a dead parameter is distinguishable from a dynamically read one and a
route that stops existing is caught rather than silently assumed.

Section 7 holds the arithmetic checks a name-by-name table cannot express: the
affected-fraction identity, the per-unit welfare denominator, the staffing-throughput
identity, the elasticity band multipliers, the outcome band ordering, and the
profile-key match against the page's hard-coded option list.

Cross-country alignment: services are matched by position, not by name, because the
four blocks name the same slot differently. `outcomes` is a dict keyed by service
name, so it is re-keyed onto the service index before comparison.

Usage:  py -3 audit_provider_params.py            (writes PROVIDER_PARAM_AUDIT.md)
        py -3 audit_provider_params.py --stdout   (prints instead)

Read-only. Touches nothing but its own report.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

# Prints an arrow in its own output, which a Windows cp1252 console cannot encode, so
# the script died in print() with a UnicodeEncodeError and exited non-zero even though
# it had done its work. Same defect as check_browser.py had; handled here rather than
# by asking the caller to set PYTHONIOENCODING.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError, OSError):
    pass


ROOT = Path(__file__).resolve().parent
MACH = ROOT / "europe" / "tool_machinery"
TEMPLATE = MACH / "template.html"
REGISTRY_PY = ROOT / "uk" / "model" / "parameters.py"
REPORT = ROOT / "PROVIDER_PARAM_AUDIT.md"

COUNTRIES = [("UK", "country_uk.json"), ("ES", "country_es.json"),
             ("IT", "country_it.json"), ("EL", "country_el.json")]
CCS = [c for c, _ in COUNTRIES]

# The shipped tools, to confirm the blocks audited here are the blocks that ship.
TOOLS = {
    "UK": ROOT / "uk" / "tools" / "dial_tool_uk.html",
    "ES": ROOT / "europe" / "Spain" / "tools" / "dial_tool_spain.html",
    "IT": ROOT / "europe" / "Italy" / "tools" / "dial_tool_italy.html",
    "EL": ROOT / "europe" / "Greece" / "tools" / "dial_tool_greece.html",
}

# Keys whose name collides with something else in the page. A hit only counts when
# the receiver in front of the dot is one of these. `value` is the DOM property on
# every <input> and <select> in the tool, so an unfiltered scan reports
# `wellby_spine.value` as read seventeen times when nothing reads it at all.
RECEIVER_HINT = {
    "value": ("SPINE", "wellby_spine", "COUNTRY.wellby_spine", "ws", "spine"),
}

# Blocks of `data` holding the provider/operational layer, versus bulk re-emits of
# the response surface (one number per scenario per epsilon per decile). Both are
# enumerated; they are reported separately because the second is thousands of numbers
# sharing a single provenance and a single builder.
PROVIDER_BLOCKS = {"services", "outcomes", "shockInterp", "bu"}
STRIP_BLOCKS = {"wevm", "deciles", "fiscal", "winlose", "cost", "shock",
                "epsGrid", "sc15", "scenarios", "poverty", "reforms"}
TOPLEVEL_PROVIDER_ROOTS = {"profiles", "wellby_spine", "scenario_extra", "deflator"}

# UK service name -> registry key in parameters.py. Taken from
# europe/tool_machinery/classify_provenance.py, which is the script that wrote the
# provenance notes now on disk.
UK_TO_REG = {
    "Jobcentre Plus / DWP work coaches": "jobcentre_plus",
    "UC claim processing (DWP)": "uc_processing",
    "Food banks (Trussell Trust + independent)": "food_banks",
    "Debt advice (Citizens Advice, StepChange)": "debt_advice",
    "NHS Talking Therapies (IAPT)": "mental_health_iapt",
    "Housing / homelessness services": "housing_support",
    "Children's social care": "childrens_services",
    "Domestic abuse services": "domestic_abuse",
    "Drug & alcohol treatment": "substance_misuse",
    "Additional GP consultations": "gp_additional_visits",
}
# EU service slot -> the UK slot its operational values were transferred from.
EU_SOURCE_SLOT = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 8]
# tool field -> registry field inside a service_demand value dict
FIELD_TO_REG = {
    "elastCentral": "demand_elasticity",
    "unitCost": "unit_cost_per_case",
    "staffRatio": "staff_ratio",
}

# ---------------------------------------------------------------------------
# Indirection map: (path regex, route label, template text that performs the lookup)
# ---------------------------------------------------------------------------
INDIRECTION = [
    (r"^data\.services\[\d+\]\.(elastLow|elastCentral|elastHigh|unitCost|staffRatio)$",
     "s = DATA.services.find(s=>s.name===#p-serv), then s.<key>",
     'function svc(){return DATA.services.find(s=>s.name===$("#p-serv").value);}'),
    (r"^data\.services\[\d+\]\.provenance\.",
     "svcClasses(s) iterates every key of s.provenance",
     "function svcClasses(s){var p=(s&&s.provenance)||{},o=[];"),
    (r"^data\.outcomes\[\d+\]\.(convL|convC|convH|wbL|wbC|wbH|sensC)$",
     "o = DATA.outcomes[s.name], then o.<key>",
     "const o=DATA.outcomes[s.name]||{convL:0"),
    (r"^data\.outcomes\[\d+\]\.rows\[\d+\]\.valC$",
     "o.rows.forEach(rw=>... rw.valC ...)",
     "o.rows.forEach(rw=>{ev+="),
    (r"^data\.shockInterp\.(du3|du5|aff3|aff5)$",
     "I = DATA.shockInterp, then I.du3/I.aff3/I.du5/I.aff5",
     "const I=DATA.shockInterp;"),
    (r"^data\.shockInterp\.(dpov3|dpov5)$",
     "read at line 332 into a local that is never rendered (dead)",
     "const dpov=shockVal(raw,I.dpov3,I.dpov5);"),
    (r"^profiles\.",
     "PROFILES[#p-prof value]; the option list is hard-coded in the page",
     "const band=PROFILES[prof],k=band.length"),
    (r"^data\.fiscal\.[^.]+\.",
     "DATA.fiscal[sScen][r.field] via COUNTRY.fiscal_rows / fiscal_field",
     "(COUNTRY.fiscal_rows||[]).map(function(r){return rowHTML(r.label,f[r.field]-b[r.field]"),
    (r"^data\.(wevm|deciles)\.",
     "DATA.wevm[sScen][ei] / DATA.deciles[ref][ei]; keys come from sc15 and scenarios",
     "var w=(DATA.wevm[sScen]||[])[ei]||0;"),
    (r"^data\.winlose\.",
     "wl = DATA.winlose[sScen], then wl.gain/.lose/.gainDec/.loseDec",
     "var wl=DATA.winlose?DATA.winlose[sScen]:null;"),
    (r"^data\.cost\.[^.]+\.welfarePerBn$",
     "DATA.cost[sScen].welfarePerBn",
     "DATA.cost[s].welfarePerBn"),
    (r"^data\.shock\.[^.]+\.(affected|dpov)$",
     "sh = DATA.shock[sScen], then sh.affected / sh.dpov",
     "var sh=(DATA.shock&&DATA.shock[sScen])||{};"),
    (r"^scenario_extra\.(imv_cost_m|irpf_cost_m)$",
     "ex.imv_cost_m / ex.irpf_cost_m in the spine table header",
     "money_m(ex.imv_cost_m)"),
    (r"^data\.epsGrid\[\d+\]$",
     "EPS = DATA.epsGrid; the provider and scenario epsilon selectors index into it",
     "const EPS=DATA.epsGrid, BU=DATA.bu;"),
]


# ---------------------------------------------------------------------------
# Section 0 is the only hand-written part of this report. Everything below it is
# generated. Each finding names the table underneath it that carries the evidence.
# ---------------------------------------------------------------------------
FINDINGS = """\
## 0. Findings

Restamped 2026-08-02 against the tree as it stands. This section is the only
hand-written part of the report; sections 1 to 8 regenerate from disk on every run, so
they were always current while this one was not. Between the first pass and this one,
thirteen of the fifteen findings were fixed and re-verified, and for a while section 0
still read as though none of them had been, which is a worse failure than the findings
it described: a reviewer reads section 0 and believes it.

Each finding below carries its state. Where a fix is claimed, the claim is checked
against the code as it ships rather than against a commit message.

### F1. FIXED. `bu` meant benefit units in the UK and working-age population in the EU

`data.bu` divided two panels that need different denominators. The per-unit welfare
figure now divides by `UNITS_M`, taken from `GRID.meta.population_basis`, which is the
count of units the deciles actually cover in the country in question; the affected
fraction is units over units on both sides. Verify by grepping the template for
`UNITS_M`: `data.bu` appears in neither formula.

### F2. FIXED. The per-unit welfare denominator was wrong in all three EU tools

The consequence recorded in the first pass was an EU cash floor at 0.633x (ES),
0.699x (IT) and 0.682x (EL) of a per-household reading. That is gone with F1: the
divisor is now each surface's own unit count. The headline, the cash floor, the engine
income and the benefit-cost ratio all moved accordingly and were re-verified live.

### F3. FIXED. The EU `aff` values were the UK's, scaled by a ratio that mixed people
and units

The scaling is units to units, so the affected fraction is not identical in all four
tools by construction.

### F4. NOT REACHED, and now moot for the panel. What UK `affected` counts

The first pass could bound it but not reproduce it. It has since been derived: the
weighted count of working-age units whose employment income falls under the shock,
466,700.4 at 3pp and 782,549.2 at 5pp from the run that fed the surface. the project audit
section 8 item 15. The EU tools do not carry the figure at all and now say so on the
face rather than showing a scaled UK number.

### F4b. FIXED. `dpov` in the UK Scenarios tab was a share of benefit units, labelled
as something else

Labelled by its own unit.

### F5. FIXED. The staffing recommendation contradicted the capacity model beside it

`addStaff` divided unmet demand by the registry `staffRatio` while `capacity` used the
provider's own entry, so the panel measured the gap on one throughput and the fix on
another. It now uses the provider's own `casesPer` for both.

### F6. DEFUSED. `staffRatio` was used as a flow and read as a stock

The unit was never stated by the registry and the formula needed the other one.
`staffRatio` is read nowhere in the template; it survives in the country blocks as one
of the unread paths in F14. The ambiguity is therefore not load-bearing on anything the
tools compute. It is not resolved, and a future use of the field would have to resolve
it first.

### F7. FIXED. Four rows on the provider panel rested on `**` inputs and rendered
unmarked

`mk()` now grades twelve rows, including the monetised total, the headline, the
benefit-cost ratio, extra and unmet demand, the extra caseworkers and the extra running
cost. The browser suite asserts propagation on every provider row and three separate
mutations of it are negatively tested.

### F8. FIXED. EU `aff3`/`aff5` were classed `national_derived` and rendered unmarked

Regraded with the same pass as F7.

### F9. FIXED. `data.bu` carried no provenance key

All four blocks now carry `data.bu_provenance` = `national_derived` and a
`bu_provenance_note` stating what the count is.

### F10. RESOLVED IN FAVOUR OF THE DATA. The spine on disk is the uprated GBP 16,300

The first pass found the data and the standing rule in flat contradiction and declined
to say which was stale. It was the rule. The project's standing rules now sanction the applied figure
of GBP 16,300 at 2024 prices, records that the earlier "never use 16,300" wording was
wrong and forbade the right answer, and requires the figure never to be cited without
its derivation.

### F11. FIXED. The UK spine label printed a different number from the one used

The UK label now reads "GBP 16,300 at 2024 prices (HM Treasury's GBP 13,000 at 2019
prices, uprated)". The browser suite asserts that every mention carries its base.

### F12. FIXED. `dpov` was computed unconditionally and read nowhere

Guarded, so there is no path that prints NaN in three tools.

### F13. FIXED. The UK carried no capacity caveat

The UK block now carries one, as the three EU blocks did.

### F14. OPEN, DELIBERATELY. Forty-six numeric paths have no reader

They stay. Removing them this late would mean regenerating four blocks and
re-instantiating four tools for no change to anything the tools compute, and each
regeneration is a chance to ship a stale grid. They are documented in table 7.12 and
this note is the record that they are known and left in place on purpose. `staffRatio`
joined them when F5 was fixed.

### F15. FIXED. Price years differed inside the `unitCost` column while the export
claimed one base for all of them

Two halves. Every unit cost now states its own price base in its own note, and the
three sourced UK figures were uprated to 2024-25 with the deflator series named. The
citable export prints no blanket claim over the top of those notes: it quotes the
price-base sentence of the service being exported, so the export and the note
cannot disagree. Exactly one service in each EU tool, the opioid substitution or SERT
figure, is recorded at 2004 and deliberately not uprated, and the export now says so
when that service is the one on screen. Browser assertion
`export_price_base_quotes_the_service_note`, negatively tested.

### Still open after this pass

Two things, both recorded rather than fixed:

* **F14**, above, by decision.
* **What a provider case is.** The panel multiplies a catchment given in people by a
  share of units and a per-unit money figure. F1 and F2 fixed the arithmetic so that
  each side uses its own denominator consistently, but the modelling question of
  whether a provider case is a household or a person is not settled by that, and the
  capacity panel still reads "people served". `DATA_ISSUES_FOR_TECHNICAL_REPORT.md`
  section 9 carries it.

### Checked and found sound


* `addStaff = ceil(unmetC / s.staffRatio)` divides in the correct direction; the
  previous session's judgement holds, verified independently against the units on
  both sides.
* `addBudget = unmetC * s.unitCost` is cases per year times currency per case.
* Every proportion in the block is stored and used on the same scale. The
  elasticities are ratios used as ratios; `winlose.gain`/`.lose` are stored as
  fractions and multiplied by 100 at render; `winners_pct`/`losers_pct` come off the
  surface already as percentages and are not multiplied again.
* `elastLow`/`elastHigh` are the registry's own stated `range.demand_elasticity` for
  every service, taken directly, and the notes on disk say so. The earlier uniform
  0.67x / 1.5x multiplier is gone. Table 7.4.
* Periods agree: `unitCost` is per case and multiplies a cases-per-year quantity;
  `staffRatio` is per year on the formula's reading; the shock magnitudes are
  percentage points on both sides of `shockVal`.
* Outcome bands are ordered low <= central <= high in all 43 service-country cells.
* `profiles` keys match the page's hard-coded option list in all four; `epsGrid`
  matches the page's epsilon options in all four. Tables 7.7, 7.7b.
* No orphan outcome entries and no service without one. Table 7.9.
* The blocks audited here are byte-identical to the blocks embedded in the four
  shipped tools. Table 7.11.
* Two `rows[].valC` cells differ from the central figure they sit beside: UK
  domestic abuse 2,608 against 5,588.24, and UK talking therapies 7,500 against
  3,471.90. Both are the SENSITIVITY row, which is defined as an alternative
  valuation and is correctly excluded from the headline. Not a defect. The Spanish
  GBV row shows 2,305 against a central 2,305.5, a rounding difference in the
  display only.

### Not reached

* The exact computation behind UK `affected`. See F4: bounded, not reproduced. The
  three UK unit costs that differ from the registry (children's social care 8,640
  against 8,000, drug and alcohol 4,488 against 3,000, GP 196 against 160) are each
  explained by a sourced note on disk and are deliberate, not drift.
* Whether each unit cost matches the publication it cites. This pass compared the
  tool against the registry and against the note; it did not open the sources.
* Whether the EU outcome values are the correct PPP conversions of their UK or
  national originals. The conversion factors are stated in the notes and were not
  recomputed.
* The 3,104 numbers in the scenario strips and the 4,631 to 6,334 in each `grid`.
  Those are the response surface, audited in G2 (FIELD_AUDIT.md), and the strips are
  re-emits of it.
* `data.services[*].flag` and every `provenance_note` were read for the services
  quoted above and skimmed elsewhere; they were not audited line by line against
  their sources.

"""


# ---------------------------------------------------------------------------
def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def walk(node, path, out):
    if isinstance(node, dict):
        for k, v in node.items():
            walk(v, "%s.%s" % (path, k) if path else str(k), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, "%s[%d]" % (path, i), out)
    elif is_num(node):
        out[path] = node


def canonical_block(block):
    """A copy of the country block with `data.outcomes` re-keyed from service name to
    service index, so the same slot lines up across the four countries."""
    b = json.loads(json.dumps(block))
    names = [s["name"] for s in b["data"]["services"]]
    oc = b["data"].get("outcomes") or {}
    b["data"]["outcomes"] = [oc.get(n, {}) for n in names]
    b["_orphan_outcomes"] = sorted(set(oc) - set(names))
    return b


def numeric_inventory(block):
    out = {}
    for k, v in block.items():
        if k in ("grid", "_orphan_outcomes"):
            continue
        walk(v, k, out)
    return out


def grid_count(block):
    out = {}
    walk(block.get("grid", {}), "grid", out)
    return len(out)


# ---------------------------------------------------------------------------
def load_template():
    txt = TEMPLATE.read_text(encoding="utf-8")
    return txt, txt.split("\n")


def scan_readers(lines, key):
    """Every site naming `key` as a property access or a quoted key. Returns
    (hits, rejected); a hit is (line_no, snippet) with the surrounding expression.
    A key listed in RECEIVER_HINT only counts when the receiver in front of the dot
    is one of the declared ones; everything else is returned as rejected."""
    esc = re.escape(key)
    pat = re.compile(r"(?:\.\s*%s\b)|(?:\[\s*[\"']%s[\"']\s*\])|(?:[\"']%s[\"']\s*:)"
                     % (esc, esc, esc))
    hint = RECEIVER_HINT.get(key)
    hits, rejected = [], []
    for i, line in enumerate(lines, 1):
        for m in pat.finditer(line):
            a, b = max(0, m.start() - 55), min(len(line), m.end() + 65)
            snip = line[a:b].strip().replace("|", "\\|")
            entry = (i, ("..." if a > 0 else "") + snip + ("..." if b < len(line) else ""))
            if hint is not None:
                recv = re.search(r"([\w$.]+)\s*$", line[:m.start()])
                recv = recv.group(1) if recv else ""
                if not any(recv == h or recv.endswith("." + h) for h in hint):
                    rejected.append(entry)
                    continue
            hits.append(entry)
    return hits, rejected


def leaf_key(path):
    return re.sub(r"\[\d+\]$", "", path.split(".")[-1])


def route_for(path):
    for pat, label, anchor in INDIRECTION:
        if re.search(pat, path):
            return label, anchor
    return None, None


# ---------------------------------------------------------------------------
def load_registry():
    spec = importlib.util.spec_from_file_location("params", REGISTRY_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PARAMETER_REGISTRY["service_demand"]


def registry_for(path, uk_names):
    """The registry value, unit string and source string behind a service field."""
    m = re.match(r"^data\.services\[(\d+)\]\.(\w+)$", path)
    if not m:
        return None
    slot, field = int(m.group(1)), m.group(2)
    if field not in FIELD_TO_REG:
        return None
    if slot >= len(uk_names):
        return None
    rk = UK_TO_REG.get(uk_names[slot])
    if not rk:
        return None
    return rk, FIELD_TO_REG[field]


# ---------------------------------------------------------------------------
def _ordered(a, b, c):
    if a is None or b is None or c is None:
        return None
    return a <= b <= c


ORIGIN_RE = re.compile(r"ORIGIN\s+([0-9][0-9.]*)\s+FACTOR\s+([0-9][0-9.]*)")
BAND_RE = re.compile(r"BAND ORIGIN\s+([0-9][0-9.]*)\s+AND\s+([0-9][0-9.]*)")
# The chain is origin x factor x effect share x attribution, so a check that stopped at the
# factor would fail every staged row, and one that ignored the tail would pass a row
# whose multipliers had been swapped for anything at all. Both clauses are optional: a note
# without STAGE is read as effect 1 and attribution 1, which is what the unstaged rows meant.
# BAND FACTOR exists because three United Kingdom rows carry a different WELLBY coefficient
# at each band end, so one factor cannot serve all three points.
NUM = r"([0-9]+(?:\.[0-9]+)?)"      # deliberately not [0-9][0-9.]* : that swallows a
                                    # sentence-ending full stop and float() then dies on "0.27."
BANDFAC_RE = re.compile(r"BAND FACTOR\s+%s\s+AND\s+%s" % (NUM, NUM))
STAGE_RE = re.compile(
    r"STAGE EFFECT\s+%s\s+%s\s+%s\s+ATTRIBUTION\s+%s\s+%s\s+%s" % ((NUM,) * 6))
# A band end nobody derives can be DECLARED so, in the tool's own excluded-route spirit:
# the row stays on the face with its value and its reason, exactly as an
# UNEVIDENCED-EXCLUDED outcome stays visible at zero rather than being deleted. The
# declaration must carry a reason after the colon, so "NOT DERIVED:" on its own does not
# satisfy it, and it applies ONLY where no origin is stated. It can never mask a value
# that IS recomputable and lands wrong: that path is untouched below and still fails.
NOT_DERIVED_RE = re.compile(r"NOT DERIVED:\s*\S")


def outcome_conversion_rows(cc, name, o):
    """7.10d for one outcome: recompute all three points from the note's own stated
    origin and factor. Returns (rows, n_failing). Module-level so the negative test
    can drive exactly the code the audit runs."""
    note = o.get("provenance_note") or ""
    conv = [o.get("convL") or 0, o.get("convC") or 0, o.get("convH") or 0]
    wb = [o.get("wbL") or 0, o.get("wbC") or 0, o.get("wbH") or 0]
    live, trip = ("conv", conv) if any(conv) else ("wb", wb)
    if not any(trip):
        return ([{"cc": cc, "outcome": name, "field": "-", "shipped": "-", "origin": "-",
                  "factor": "-", "recomputed": "-",
                  "verdict": "no value (all three points zero)"}], 0)
    mo = ORIGIN_RE.search(note)
    if not mo:
        return ([{"cc": cc, "outcome": name, "field": live, "shipped": trip[1],
                  "origin": "-", "factor": "-", "recomputed": "-",
                  "verdict": "**NO ORIGIN CLAUSE - FAIL**"}], 1)
    origin, factor = float(mo.group(1)), float(mo.group(2))
    mb = BAND_RE.search(note)
    band_missing = "BAND ORIGIN NOT DOCUMENTED" in note
    origins = [float(mb.group(1)), origin, float(mb.group(2))] if mb else [None, origin, None]
    mf = BANDFAC_RE.search(note)
    factors = [float(mf.group(1)), factor, float(mf.group(2))] if mf else [factor] * 3
    ms = STAGE_RE.search(note)
    if ms:
        eff = [float(ms.group(i)) for i in (1, 2, 3)]
        att = [float(ms.group(i)) for i in (4, 5, 6)]
    else:
        eff = att = [1.0, 1.0, 1.0]
    rows, fails = [], 0
    for i, (lbl, org, got) in enumerate(zip(("L", "C", "H"), origins, trip)):
        factor = factors[i]
        if org is None:
            declared = NOT_DERIVED_RE.search(note) is not None
            if not declared:
                fails += 1
            rows.append({"cc": cc, "outcome": name, "field": live + lbl, "shipped": got,
                         "origin": "-", "factor": factor, "recomputed": "-",
                         "verdict": ("not derived (declared)" if declared
                                     else "**BAND ORIGIN NOT DOCUMENTED - FAIL**" if band_missing
                                     else "**NO BAND ORIGIN CLAUSE - FAIL**")})
            continue
        rec = org * factor * eff[i] * att[i]
        tol = max(1.0, abs(rec) * 0.0005)
        ok = abs(rec - got) <= tol
        if not ok:
            fails += 1
        rows.append({"cc": cc, "outcome": name, "field": live + lbl, "shipped": got,
                     "origin": org, "factor": factor,
                     "effect": eff[i], "attribution": att[i], "recomputed": round(rec, 3),
                     "verdict": ok if ok else "**off by %.3f - FAIL**" % (got - rec)})
    return rows, fails


def outcome_rows_scoped(cc, name, o):
    """outcome_conversion_rows plus the scope rule, in one place.

    A transferred row must state an origin or fail; a national row without one is
    reported and not counted, because some national rows are a single published figure
    with no conversion. Module-level and shared, because the audit and
    europe/model/write_valuation_chains.py both need it and a second copy of the rule is
    how the two would come to disagree about what counts as a failure.
    """
    rows, fails = outcome_conversion_rows(cc, name, o)
    if o.get("provenance") in ("borrowed_adjusted", "borrowed_unadjusted"):
        return rows, fails
    for row in rows:
        if "NO ORIGIN CLAUSE" in str(row.get("verdict")):
            row["verdict"] = "national, no conversion stated (not counted)"
            fails -= 1
    return rows, fails


def derived_checks(blocks, reg, raw_for_compare):
    out = []

    out.append(("7.1 Affected fraction: the denominator under the whole capacity panel", [], """\
`affFrac = aff / (BU*1000)` at template.html:334, commented "share of the population
affected". `aff` is interpolated from `shockInterp.aff3/aff5`; `BU` is `data.bu`.
`units_k` and `population_k` are the surface's own weighted counts at the baseline
point, from `grid.meta.population_basis`."""))
    rows = out[-1][1]
    uk_si, uk_bu = blocks["UK"]["data"]["shockInterp"], blocks["UK"]["data"]["bu"]
    for cc in CCS:
        d = blocks[cc]["data"]
        si, bu = d["shockInterp"], d["bu"]
        pb = blocks[cc]["grid"]["meta"].get("population_basis") or {}
        rows.append({
            "cc": cc, "data.bu": bu, "denominator BU*1000 (k)": bu * 1000,
            "aff3": si.get("aff3"), "aff5": si.get("aff5"),
            "affFrac @3pp": si["aff3"] / (bu * 1000) if si.get("aff3") else None,
            "affFrac @5pp": si["aff5"] / (bu * 1000) if si.get("aff5") else None,
            "aff3 predicted by UK aff3 x bu/uk_bu": round(uk_si["aff3"] * bu / uk_bu, 1),
            "surface units_k": pb.get("units_k"), "surface population_k": pb.get("population_k"),
            "BU*1000 / units_k": (bu * 1000) / pb["units_k"] if pb.get("units_k") else None,
            "BU*1000 / population_k": (bu * 1000) / pb["population_k"] if pb.get("population_k") else None,
            "affFrac if denom were units_k": si["aff3"] / pb["units_k"] if pb.get("units_k") else None,
            "affFrac if denom were population_k": si["aff3"] / pb["population_k"] if pb.get("population_k") else None,
        })

    out.append(("7.2 Per-unit welfare denominator", [], """\
`pbW = bandWt*10/(k*BU)` and `pbU = bandUnwt*10/(k*BU)` at template.html:303. The
decile array is a split of the whole modelled population into ten equal groups of
units, so the divisor must be the count of units the surface covers, in millions.
`cashfloor = people*pbW` and `engineInc = people*pbU` feed the headline and the BCR."""))
    rows = out[-1][1]
    for cc in CCS:
        pb = blocks[cc]["grid"]["meta"].get("population_basis") or {}
        bu = blocks[cc]["data"]["bu"]
        uk_m = (pb.get("units_k") or 0) / 1000 or None
        pk_m = (pb.get("population_k") or 0) / 1000 or None
        rows.append({
            "cc": cc, "BU used as divisor (m)": bu,
            "units the deciles cover (m)": uk_m, "people they cover (m)": pk_m,
            "correct-if-per-unit factor": (uk_m / bu) if uk_m else None,
            "correct-if-per-person factor": (pk_m / bu) if pk_m else None,
        })

    out.append(("7.3 Staffing throughput: two statements of the same quantity", [], """\
`capacity = staffN * casesPer` at template.html:339 uses the provider's own entry for
cases each caseworker handles per year (page default 50). `addStaff =
ceil(unmetC / s.staffRatio)` at template.html:344 uses the registry value instead.
If the two disagree, the recommended headcount does not close the gap the same panel
just reported. `implied gap` is how many times too few staff are recommended when
the provider leaves the page default in place."""))
    rows = out[-1][1]
    for cc in CCS:
        for i, s in enumerate(blocks[cc]["data"]["services"]):
            sr = s.get("staffRatio")
            rows.append({"cc": cc, "slot": i, "service": s["name"],
                         "staffRatio (addStaff divisor)": sr,
                         "page default casesPer (capacity multiplier)": 50,
                         "implied gap (staffRatio/casesPer)": (sr / 50) if sr else None})

    out.append(("7.4 Elasticity bands against the registry's own stated range", [], """\
`elastLow`/`elastHigh` are multiplied by the caseload to give the low and high demand
bands. The provenance notes on disk say each bound is the registry's stated
`range.demand_elasticity`, taken directly, replacing an earlier uniform multiplier
with no source. Checked here against the registry rather than against the note."""))
    rows = out[-1][1]
    uk_names_l = [s["name"] for s in blocks["UK"]["data"]["services"]]
    for cc in CCS:
        for i, s in enumerate(blocks[cc]["data"]["services"]):
            c = s.get("elastCentral")
            src = i if cc == "UK" else (EU_SOURCE_SLOT[i] if i < len(EU_SOURCE_SLOT) else None)
            rng = None
            if src is not None and src < len(uk_names_l):
                rk = UK_TO_REG.get(uk_names_l[src])
                if rk:
                    rng = (reg[rk].get("range") or {}).get("demand_elasticity")
            rows.append({"cc": cc, "slot": i, "service": s["name"],
                         "low": s.get("elastLow"), "central": c, "high": s.get("elastHigh"),
                         "registry range": rng,
                         "bounds match range": (rng is not None
                                                and [s.get("elastLow"), s.get("elastHigh")] == list(rng)),
                         "low/central": (s["elastLow"] / c) if c else None,
                         "high/central": (s["elastHigh"] / c) if c else None})

    out.append(("7.5 Registry versus tool, service by service", [], """\
`registry` is `service_demand.<key>.value.<field>` in uk/model/parameters.py. The
registry's `unit` field for every service is the string "service params"; it states
no unit for any individual number inside the dict. The `unit stated` column is
therefore what the registry actually says, not what the tool assumes."""))
    rows = out[-1][1]
    uk_names = [s["name"] for s in blocks["UK"]["data"]["services"]]
    for i, s in enumerate(blocks["UK"]["data"]["services"]):
        rk = UK_TO_REG.get(s["name"])
        if not rk:
            continue
        rv = reg[rk]["value"]
        for field, rfield in FIELD_TO_REG.items():
            rows.append({
                "slot": i, "UK service": s["name"], "field": field,
                "tool UK": s.get(field), "registry": rv.get(rfield),
                "agree": s.get(field) == rv.get(rfield),
                "registry unit stated": reg[rk].get("unit"),
                "registry source": (reg[rk].get("source") or "")[:70],
            })

    out.append(("7.6 Outcome bands: ordering, and agreement with the evidence row", [], """\
`conv L/C/H` and `wb L/C/H` are multiplied by the provider's caseload and shown as a
low/central/high band, so they must be ordered. `rows[].valC` is shown in the
evidence table as the value per person helped, so it should equal the central figure
of whichever route that row declares."""))
    rows = out[-1][1]
    for cc in CCS:
        for i, o in enumerate(blocks[cc]["data"]["outcomes"]):
            name = blocks[cc]["data"]["services"][i]["name"]
            vals = [r.get("valC") for r in o.get("rows", [])]
            meths = [r.get("method") for r in o.get("rows", [])]
            rows.append({
                "cc": cc, "slot": i, "service": name,
                "conv L/C/H": "%s/%s/%s" % (o.get("convL"), o.get("convC"), o.get("convH")),
                "wb L/C/H": "%s/%s/%s" % (o.get("wbL"), o.get("wbC"), o.get("wbH")),
                "conv ordered": _ordered(o.get("convL"), o.get("convC"), o.get("convH")),
                "wb ordered": _ordered(o.get("wbL"), o.get("wbC"), o.get("wbH")),
                "rows valC": vals, "rows method": meths,
                "every valC equals a central or 0": all(
                    v in (o.get("convC"), o.get("wbC"), 0) for v in vals),
                "sensC": o.get("sensC"),
            })

    out.append(("7.7 Profile keys against the page's hard-coded option list", [], """\
`PROFILES[prof]` at template.html:300 is indexed by the literal text of the selected
<option>. The options are hard-coded in the page, so a profile key that does not
match one of them is unreachable, and an option with no matching key throws."""))
    rows = out[-1][1]
    txt, _ = load_template()
    m = re.search(r'<select id="p-prof">(.*?)</select>', txt, re.S)
    page_opts = re.findall(r"<option>(.*?)</option>", m.group(1)) if m else []
    for cc in CCS:
        keys = list(blocks[cc]["profiles"].keys())
        rows.append({"cc": cc, "profile keys": " | ".join(keys),
                     "match page options": keys == page_opts})
    rows.append({"cc": "page", "profile keys": " | ".join(page_opts), "match page options": "-"})

    out.append(("7.7b Epsilon grid against the page's hard-coded option list", [], """\
`epsIdx(e)` is `EPS.indexOf(e)` where `EPS = DATA.epsGrid` and `e` is parsed from the
selected `#p-eps` option. An option with no matching grid entry returns -1 and
`DATA.deciles[ref][-1]` is undefined, which would take down the whole value panel."""))
    rows = out[-1][1]
    m2 = re.search(r'<select id="p-eps">(.*?)</select>', txt, re.S)
    page_eps = [float(x) for x in re.findall(r"<option[^>]*>(.*?)</option>", m2.group(1))] if m2 else []
    for cc in CCS:
        eg = blocks[cc]["data"].get("epsGrid") or []
        rows.append({"cc": cc, "data.epsGrid": eg, "page #p-eps options": page_eps,
                     "every option resolvable": all(e in eg for e in page_eps)})

    out.append(("7.8 Deflator and spine", [], """\
`DEF = COUNTRY.deflator` multiplies money at display time through fmtM, fmtBn,
money_m and anchorLine. It is NOT applied by `fmtGBP`, which formats every figure on
the Provider tab, so provider money is shown at whatever price base its parameters
carry. `wellby_spine.value` is the number the WELLBY outcome bands were built from;
`wellby_spine.label` is what the page prints. Neither the UK base of GBP 13,000 at
2019 prices nor the uprated GBP 16,300 is read by any formula; the spine enters only
through the already-multiplied `wb*` values."""))
    rows = out[-1][1]
    uk_spine = (blocks["UK"].get("wellby_spine") or {}).get("value")
    for cc in CCS:
        ws = blocks[cc].get("wellby_spine") or {}
        v = ws.get("value")
        rows.append({"cc": cc, "deflator": blocks[cc].get("deflator"),
                     "wellby_spine.value": v,
                     "value / UK value": (v / uk_spine) if (v and uk_spine) else None,
                     "value / 13000 base": (v / 13000) if v else None,
                     "wellby_spine.label (printed)": ws.get("label"),
                     "spine provenance": ws.get("provenance")})

    out.append(("7.9 Orphan outcome entries", [], """\
`DATA.outcomes` is keyed by service name. An entry whose key matches no service is
unreachable; a service with no entry silently falls back to the all-zero default
object at template.html:304."""))
    rows = out[-1][1]
    for cc in CCS:
        b = blocks[cc]
        names = [s["name"] for s in b["data"]["services"]]
        empty = [names[i] for i, o in enumerate(b["data"]["outcomes"]) if not o]
        rows.append({"cc": cc, "orphan outcome keys": b.get("_orphan_outcomes") or "-",
                     "services with no outcome entry": empty or "-"})

    out.append(("7.10 Scenario-key coverage of the strip dictionaries", [], """\
The provider reference selector is filled from `DATA.sc15` and then indexes
`DATA.deciles[ref]`. The scenarios tab is filled from `COUNTRY.scenarios_list ||
DATA.scenarios` and indexes `DATA.wevm`, `DATA.deciles`, `DATA.fiscal`,
`DATA.winlose`. A listed id missing from a strip renders as zero or as a baseline,
with no error."""))
    rows = out[-1][1]
    for cc in CCS:
        d = blocks[cc]["data"]
        sc_list = blocks[cc].get("scenarios_list") or d.get("scenarios") or []
        miss = {}
        for strip in ("wevm", "deciles", "fiscal", "winlose"):
            have = set((d.get(strip) or {}).keys())
            miss[strip] = sorted(set(sc_list) - have)
        rows.append({
            "cc": cc, "sc15 ids": len(d.get("sc15") or []),
            "sc15 missing from deciles": sorted(set(d.get("sc15") or []) - set((d.get("deciles") or {}).keys())) or "-",
            "scenario ids": len(sc_list),
            "missing from wevm": miss["wevm"] or "-",
            "missing from deciles": miss["deciles"] or "-",
            "missing from fiscal": miss["fiscal"] or "-",
            "missing from winlose": miss["winlose"] or "-",
        })

    out.append(("7.10b Provenance marks against the rows they should mark", [], """\
the project's standing rules: marks propagate by worst grade, and a headline computed from a starred
component is itself starred. `marked in template` is whether the row's HTML calls
`mk(...)` at all; `worst grade of inputs` is what `gradeOf` would return for the
inputs that row actually uses, computed here from the provenance keys on disk for
the default service in each country."""))
    rows = out[-1][1]
    RANK = {"national_source": 0, "national_derived": 0, "borrowed_adjusted": 1,
            "borrowed_unadjusted": 2, "assumption": 2}

    def grade(classes):
        w = max([RANK.get(c, 2) for c in classes] or [0])
        return "" if w == 0 else ("*" if w == 1 else "**")

    # The inputs each row uses, and whether the template marks it, as of the per-row
    # grading change. staffRatio is absent from every list because no formula reads it
    # any more, and data.bu because the per-unit figures now divide by the surface's
    # own units_k.
    DEC = ["surface deciles"]
    OUT = ["outcome", "spine"]
    DEM = ["elastLow", "elastCentral", "elastHigh", "aff3", "aff5"]
    ROWS = [
        ("Cash-equivalent floor", DEC, False),
        ("Engine income (unweighted)", DEC, False),
        ("Conventional outcomes L/C/H", OUT, True),
        ("WELLBY outcomes L/C/H", OUT, True),
        ("Monetised total L/C/H", DEC + OUT, True),
        ("Welfare-weighted HEADLINE", DEC + OUT, True),
        ("Benefit-cost ratio (BCR)", DEC + OUT, True),
        ("Units losing an earner, nationally", ["aff3", "aff5"], True),
        ("Extra demand on you", DEM, True),
        ("Unmet demand", DEM, True),
        ("Extra caseworkers to close the gap", DEM, True),
        ("Extra running cost to close the gap", DEM + ["unitCost"], True),
    ]
    for cc in CCS:
        b = blocks[cc]
        default_svc = b.get("provider_default") or b["data"]["services"][0]["name"]
        s = [x for x in b["data"]["services"] if x["name"] == default_svc][0]
        oc = b["data"]["outcomes"][b["data"]["services"].index(s)]
        cls = dict(s.get("provenance") or {})
        cls["outcome"] = oc.get("provenance")
        cls["spine"] = (b.get("wellby_spine") or {}).get("provenance")
        sip = b["data"]["shockInterp"].get("provenance") or {}
        cls["aff3"], cls["aff5"] = sip.get("aff3"), sip.get("aff5")
        cls["surface deciles"] = "national_derived"
        for label, inputs, marked in ROWS:
            g = grade([cls.get(i) for i in inputs if cls.get(i) is not None])
            rows.append({"cc": cc, "row on the panel": label,
                         "inputs": ", ".join(inputs),
                         "worst grade of inputs": g or "(none)",
                         "marked in template": marked,
                         "mark shown matches grade": (marked or g == "")})

    out.append(("7.9b Classified-parameter count, by group", [], """\
The count of parameters carrying one of the five provenance classes. Reported here
because it has been quoted from memory rather than recomputed, and two of the
figures in circulation cannot be reproduced from anything in the tree. Every value
is also checked against the five permitted classes."""))
    rows = out[-1][1]
    VALID = {"national_source", "national_derived", "borrowed_adjusted",
             "borrowed_unadjusted", "assumption"}
    grand, bad = 0, []
    for cc in CCS:
        b, D = blocks[cc], blocks[cc]["data"]
        sv = sum(len(s.get("provenance") or {}) for s in D["services"])
        si = len((D.get("shockInterp") or {}).get("provenance") or {})
        oc = sum(1 for o in D["outcomes"] if isinstance(o, dict) and o.get("provenance"))
        sp = 1 if (b.get("wellby_spine") or {}).get("provenance") else 0
        pf = 1 if b.get("profiles_provenance") else 0
        bu = 1 if D.get("bu_provenance") else 0
        for s in D["services"]:
            for k, v in (s.get("provenance") or {}).items():
                if v not in VALID:
                    bad.append("%s services[%s].%s = %r" % (cc, s["name"], k, v))
        for k, v in ((D.get("shockInterp") or {}).get("provenance") or {}).items():
            if v not in VALID:
                bad.append("%s shockInterp.%s = %r" % (cc, k, v))
        t = sv + si + oc + sp + pf + bu
        grand += t
        rows.append({"cc": cc, "services (5 fields each)": sv, "shockInterp": si,
                     "outcomes": oc, "wellby_spine": sp, "profiles": pf,
                     "data.bu": bu, "total": t})
    rows.append({"cc": "TOTAL", "services (5 fields each)": "", "shockInterp": "",
                 "outcomes": "", "wellby_spine": "", "profiles": "", "data.bu": "",
                 "total": grand})
    rows.append({"cc": "values outside the five permitted classes", "total": bad or "none"})

    out.append(("7.10c EU unit costs recomputed from the UK source and the stated ratio", [], """\
Every EU unitCost that is a conversion carries, in its own note, the UK value it was
converted from and the ratio applied. Recomputed here: tool value against
UK value x ratio, rounded. A row reading "national figure" is not a conversion and
has no ratio to check. This is the arithmetic the provider audit did not reach."""))
    rows = out[-1][1]
    uk_svc = blocks["UK"]["data"]["services"]
    for cc in CCS:
        if cc == "UK":
            continue
        for i, s in enumerate(blocks[cc]["data"]["services"]):
            note = (s.get("provenance_note") or {}).get("unitCost", "")
            mr = re.search(r"Ratio applied:\s*([0-9]+\.[0-9]+)", note)
            mu = re.search(r"converted from the UK value of GBP\s*([0-9.,]+)", note)
            if not (mr and mu):
                rows.append({"cc": cc, "slot": i, "service": s["name"],
                             "tool value": s.get("unitCost"), "UK source": "-", "ratio": "-",
                             "recomputed": "-", "matches": "national figure, not a conversion"})
                continue
            ratio, uk_val = float(mr.group(1)), float(mu.group(1).replace(",", ""))
            src = EU_SOURCE_SLOT[i] if i < len(EU_SOURCE_SLOT) else None
            in_block = uk_svc[src]["unitCost"] if src is not None and src < len(uk_svc) else None
            rec = uk_val * ratio
            rows.append({
                "cc": cc, "slot": i, "service": s["name"], "tool value": s.get("unitCost"),
                "UK source": uk_val, "ratio": ratio, "recomputed": round(rec, 3),
                "matches": (round(rec) == s.get("unitCost")
                            and (in_block is None or abs(in_block - uk_val) < 1e-9)),
            })

    out.append(("7.10d data.outcomes recomputed from the stated chain", [], """\
The same arithmetic as 7.10c, one layer up, and since 2026-08-05 it covers **every
outcome carrying a value in all four blocks**, not the European transfers alone. Each
must carry its own chain, in the grammar

    ORIGIN <central> FACTOR <f>  [BAND ORIGIN <low> AND <high>]  [BAND FACTOR <fl> AND <fh>]
    [STAGE EFFECT <l> <c> <h> ATTRIBUTION <l> <c> <h>]

and all three points are recomputed as `origin x factor x effect x attribution`.

Two clauses carry the valuation stages. `STAGE` carries the effect share and the
attribution, because a staged chain is origin x factor x effect x attribution, so a
check that stopped at the factor would fail every staged row, and one that ignored the
tail would pass a row whose multipliers had been swapped for anything at all. `BAND
FACTOR` exists because three United Kingdom rows carry a different WELLBY coefficient at
each band end, so one factor cannot serve all three points. Both are optional: a note
without `STAGE` is read as effect 1 and attribution 1, which is what an unstaged row
means.

**What this check does not prove.** It recomputes the chain, not the labelling. Swapping
the effect share and the attribution leaves every product unchanged and would pass here.
Which quantity is which is protected by the note text and by review, and the reason it
matters is that an attribution applied to a figure that is already net of a comparison
group deducts the counterfactual twice; on children's social care that would halve the
value.

TOLERANCE: 1 currency unit, or 0.05 per cent of the recomputed value, whichever is
larger. The blocks round these conversions to whole units and are not consistent about
which way, so a sub-unit gap is rounding and anything above it is not.

A **transferred** row (`borrowed_adjusted` or `borrowed_unadjusted`) that does not name
an origin and a factor is reported `NO ORIGIN CLAUSE` and counted a FAILURE, not skipped:
an unparseable note is exactly the condition that let the Greek gender-based-violence
transfer apply its factor twice. A **national** row without one is reported and not
counted, because some national rows are a single published figure with no conversion.
`BAND ORIGIN NOT DOCUMENTED` is likewise a failure on the two band ends, and says that
the tree records no derivation for them rather than that they were checked. An all-zero
triple carries no converted figure and is reported `no value` without counting either way.

A band end that nothing derives may instead be **declared** with a `NOT DERIVED: <reason>`
clause in the same note, and is then reported `not derived (declared)` and not counted a
failure. This is the tool's own excluded route applied to the audit: an
UNEVIDENCED-EXCLUDED outcome stays on the face at zero with its reason rather than being
deleted, and a declared band end likewise keeps its shipped value and its reason rather
than being reconstructed on an unsourced multiplier or removed. The declaration needs a
reason after the colon, applies only where no origin is stated, and can never mask a
value that IS recomputable and lands wrong; `tests_negative_provider.py` breaks both of
those on purpose."""))
    rows = out[-1][1]
    fails = 0
    # Covers every outcome carrying a value in all four blocks, which is wider than the
    # borrowed_adjusted outcomes of the three European blocks the valuation stages alone
    # would need. Narrowed to those, the check has two holes: a row that changes
    # provenance class falls silently out of it, and the seven United Kingdom rows every
    # European value is derived from are never recomputed at all. A transferred row must
    # still state an origin or fail; a national row without one is reported and not
    # counted, because some national rows are single published figures with no conversion.
    for cc in CCS:
        svcs = blocks[cc]["data"]["services"]
        for i, o in enumerate(blocks[cc]["data"]["outcomes"]):
            if not isinstance(o, dict):
                continue
            name = svcs[i]["name"] if i < len(svcs) else "slot %d" % i
            r, f = outcome_rows_scoped(cc, name, o)
            rows.extend(r)
            fails += f
    rows.append({"cc": "TOTAL", "outcome": "points failing", "verdict": fails or "none"})

    out.append(("7.11 Does the audited block match the shipped tool", [], """\
The blocks audited here live in `europe/tool_machinery/`. Each tool HTML embeds its
own copy in a `const COUNTRY=` literal. If the two have drifted, every finding above
describes the authoring copy rather than what ships."""))
    rows = out[-1][1]
    for cc in CCS:
        path = TOOLS[cc]
        if not path.exists():
            rows.append({"cc": cc, "tool": str(path.name), "embedded block matches": "tool not found"})
            continue
        html = path.read_text(encoding="utf-8")
        m = re.search(r"const COUNTRY=(\{.*?\});\s*\n", html, re.S)
        if not m:
            rows.append({"cc": cc, "tool": path.name, "embedded block matches": "no COUNTRY literal found"})
            continue
        try:
            emb = json.loads(m.group(1))
        except ValueError as exc:
            rows.append({"cc": cc, "tool": path.name, "embedded block matches": "unparseable: %s" % exc})
            continue
        same = emb == raw_for_compare[cc]
        diff = "-" if same else sorted(
            k for k in set(emb) | set(raw_for_compare[cc])
            if emb.get(k) != raw_for_compare[cc].get(k))
        rows.append({"cc": cc, "tool": path.name, "embedded block matches": same,
                     "differing top-level keys": diff})
    return out


# ---------------------------------------------------------------------------
def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "yes" if v else "**no**"
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return ("%.6f" % v).rstrip("0").rstrip(".")
    return str(v).replace("|", "\\|")


def table(w, rows):
    if not rows:
        w("(none)")
        w("")
        return
    cols = list(rows[0].keys())
    w("| " + " | ".join(cols) + " |")
    w("|" + "|".join(["---"] * len(cols)) + "|")
    for r in rows:
        w("| " + " | ".join(fmt(r.get(c)) for c in cols) + " |")
    w("")


def main():
    raw_blocks = {cc: json.loads((MACH / fn).read_text(encoding="utf-8"))
                  for cc, fn in COUNTRIES}
    blocks = {cc: canonical_block(b) for cc, b in raw_blocks.items()}
    reg = load_registry()
    txt, lines = load_template()

    inv = {cc: numeric_inventory(blocks[cc]) for cc in CCS}
    all_paths = sorted(set().union(*[set(v) for v in inv.values()]))
    uk_names = [s["name"] for s in blocks["UK"]["data"]["services"]]
    svc_names = {cc: [s["name"] for s in blocks[cc]["data"]["services"]] for cc in CCS}

    rows = []
    for p in all_paths:
        root = p.split(".")[0]
        if root == "data":
            sub = re.sub(r"\[\d+\]$", "", p.split(".")[1]) if "." in p else root
            kind = ("provider" if sub in PROVIDER_BLOCKS else
                    "strip" if sub in STRIP_BLOCKS else "other")
        else:
            kind = "provider" if root in TOPLEVEL_PROVIDER_ROOTS else "other"
        key = leaf_key(p)
        hits, rejected = scan_readers(lines, key)
        route, _ = route_for(p)
        vals = [inv[cc].get(p) for cc in CCS]
        present = [v for v in vals if v is not None]
        rows.append({
            "path": p, "key": key, "kind": kind, "vals": vals,
            "identical": len(present) == 4 and len(set(present)) == 1,
            "hits": hits, "rejected": rejected, "route": route,
            "reader": "dynamic" if route else ("literal" if hits else "NONE"),
            "reg": registry_for(p, uk_names),
        })

    checks = derived_checks(blocks, reg, raw_blocks)

    out = []
    w = out.append
    w("# Provider-block parameter audit, all four country blocks")
    w("")
    w("Generated by `audit_provider_params.py`. Enumeration only; nothing here is fixed.")
    w("Three references compared for every parameter: the registry entry in")
    w("`uk/model/parameters.py` including its `unit` and `source` strings, the formula in")
    w("`europe/tool_machinery/template.html` that reads it, and the `provenance_note`")
    w("carried beside the value in the country block.")
    w("")
    w("Read the tables, not the codebase. Section 0 is judgement and is written by hand")
    w("in the script; sections 1 to 8 are generated. Section 7 holds the checks that a")
    w("key-by-key table cannot express.")
    w("")
    w(FINDINGS)

    w("## 1. Indirection routes")
    w("")
    w("Keys reached through a variable rather than by name. `anchor` is the exact")
    w("template text that performs the lookup, re-checked against the live template on")
    w("every run, so a route that stops existing is caught here rather than assumed.")
    w("")
    w("| route | anchor present |")
    w("|---|---|")
    for _, label, anchor in INDIRECTION:
        w("| %s | %s |" % (label.replace("|", "\\|"),
                           "yes" if anchor in txt else "**NO - ROUTE BROKEN**"))
    w("")

    nprov = sum(1 for r in rows if r["kind"] == "provider")
    nstrip = sum(1 for r in rows if r["kind"] == "strip")
    noth = sum(1 for r in rows if r["kind"] == "other")
    w("## 2. Inventory")
    w("")
    w("| block | numeric leaves, union of the four countries |")
    w("|---|---:|")
    w("| provider and operational layer | %d |" % nprov)
    w("| response-surface re-emits (scenario strips) | %d |" % nstrip)
    w("| other non-grid numbers | %d |" % noth)
    w("| **total outside `grid`** | **%d** |" % len(rows))
    w("")
    w("| country | numeric leaves outside `grid` | provider layer | inside `grid` |")
    w("|---|---:|---:|---:|")
    for cc in CCS:
        prov = sum(1 for r in rows if r["kind"] == "provider" and inv[cc].get(r["path"]) is not None)
        w("| %s | %d | %d | %d |" % (cc, len(inv[cc]), prov, grid_count(blocks[cc])))
    w("")

    w("## 3. Service slots, by position")
    w("")
    w("The four blocks name the same slot differently, so everything below aligns by")
    w("position. `EU source slot` is the UK slot each EU slot's operational values were")
    w("transferred from, per classify_provenance.py.")
    w("")
    w("| slot | UK | ES | IT | EL | EU source slot |")
    w("|---|---|---|---|---|---|")
    n = max(len(v) for v in svc_names.values())
    for i in range(n):
        cells = [svc_names[cc][i] if i < len(svc_names[cc]) else "-" for cc in CCS]
        src = EU_SOURCE_SLOT[i] if i < len(EU_SOURCE_SLOT) else "-"
        w("| %d | %s | %s | %s | %s | %s |" % (i, cells[0], cells[1], cells[2], cells[3], src))
    w("")

    w("## 4. Provider and operational parameters, key by key")
    w("")
    w("`ident` marks a value identical in all four countries. `reader` is how a formula")
    w("reaches it: `literal` means the key is named in the template, `dynamic` means it")
    w("is reached through one of the routes in section 1, `NONE` means neither.")
    w("`reg` is the registry counterpart where one exists.")
    w("")
    w("| path | UK | ES | IT | EL | ident | reader | lines | registry |")
    w("|---|---:|---:|---:|---:|:---:|---|---|---|")
    for r in rows:
        if r["kind"] != "provider":
            continue
        sites = ",".join(sorted({str(h[0]) for h in r["hits"]}, key=int)) or "-"
        rg = "-"
        if r["reg"]:
            rk, rf = r["reg"]
            rg = "`%s.%s` = %s" % (rk, rf, fmt(reg[rk]["value"].get(rf)))
        w("| `%s` | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["path"], fmt(r["vals"][0]), fmt(r["vals"][1]), fmt(r["vals"][2]),
            fmt(r["vals"][3]), "Y" if r["identical"] else "", r["reader"], sites, rg))
    w("")

    w("## 5. Numeric keys with no reader")
    w("")
    w("The literal scan found no site and no declared indirection route covers them.")
    w("")
    none_rows = [r for r in rows if r["reader"] == "NONE"]
    if not none_rows:
        w("None.")
        w("")
    else:
        w("| path | UK | ES | IT | EL | block |")
        w("|---|---:|---:|---:|---:|---|")
        for r in none_rows:
            w("| `%s` | %s | %s | %s | %s | %s |" % (
                r["path"], fmt(r["vals"][0]), fmt(r["vals"][1]), fmt(r["vals"][2]),
                fmt(r["vals"][3]), r["kind"]))
        w("")

    w("## 6. Provider values identical in all four countries")
    w("")
    w("A provider parameter identical in all four is a transfer that was never")
    w("localised. Legitimate for a delivery technology, not for a price.")
    w("")
    w("| path | value | reader |")
    w("|---|---:|---|")
    for r in rows:
        if r["identical"] and r["kind"] == "provider":
            w("| `%s` | %s | %s |" % (r["path"], fmt(r["vals"][0]), r["reader"]))
    w("")

    w("## 7. Arithmetic checks")
    w("")
    for title, rws, note in checks:
        w("### %s" % title)
        w("")
        w(note)
        w("")
        table(w, rws)

    w("## 8. Read sites, with the surrounding expression")
    w("")
    seen = set()
    for r in rows:
        if r["kind"] != "provider" or not r["hits"] or r["key"] in seen:
            continue
        seen.add(r["key"])
        w("**`%s`**" % r["key"])
        w("")
        for ln, snip in sorted(set(r["hits"]))[:8]:
            w("- `template.html:%d` &mdash; `%s`" % (ln, snip))
        w("")

    rej = [r for r in rows if r["kind"] == "provider" and r["rejected"]]
    if rej:
        w("### Literal matches rejected as name collisions")
        w("")
        w("Sites where the key name appears but the receiver shows it is something")
        w("else. Listed so the rejection is auditable rather than silent.")
        w("")
        seen = set()
        for r in rej:
            if r["key"] in seen:
                continue
            seen.add(r["key"])
            w("**`%s`** (%d rejected)" % (r["key"], len(r["rejected"])))
            w("")
            for ln, snip in sorted(set(r["rejected"]))[:4]:
                w("- `template.html:%d` &mdash; `%s`" % (ln, snip))
            w("")

    text = "\n".join(out) + "\n"
    if "--stdout" in sys.argv:
        sys.stdout.write(text)
    else:
        # bytes, so the generated report does not differ by platform: write_text would
        # emit CRLF on Windows and LF elsewhere for a tracked file.
        REPORT.write_bytes(text.encode("utf-8"))
        print("wrote %s (%d lines)" % (REPORT, len(out)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
