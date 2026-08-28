"""One-off migration: add provenance and provenance_note to the operational layer.

Splices compact JSON back into the existing compact `data` line so the authoring
files keep their formatting. Values are never touched, only annotated.

================================================================================
RE-RUNNING THIS REVERTS DELIBERATE DECISIONS. IT IS KEPT AS A RECORD, NOT A TOOL.
================================================================================

This script did its job once and is retained because it documents how the
provenance layer was built. Running it again would undo the following, and no
check would catch it, because the blocks and the pages would still agree with
each other:

  * dpov3 / dpov5 provenance would come back to the three EU blocks. Those fields
    were WITHDRAWN on 2026-07-31 because the poverty response to an unemployment
    shock is the United Kingdom's own modelled benefit-system behaviour and does
    not transfer: how far a job loss pushes a household under the line depends on
    the national system. The `else` branch below still writes provenance for both.
    It would annotate fields that no longer exist.

  * staffRatio notes would be rewritten to assert "cases per caseworker per year".
    That unit is NOT established: the registry states no unit for the field, and
    none of its ten source strings mentions staffing. It was corrected on
    2026-08-01, and this script would put the unsupported claim back.

  * unitCost and aff notes would lose the 2024-equivalent price base and the
    borrowed_adjusted reclassification added on 2026-08-01. check_drift.py would then
    fail on the price-base assertion, which is the one part of this that WOULD be
    caught.

If you need to re-annotate, update this script to the current decisions first.

Guarded: it refuses to run without --i-know-this-reverts.
"""
import importlib.util, json, sys
from pathlib import Path

if "--i-know-this-reverts" not in sys.argv:
    sys.exit(
        "classify_provenance.py is a RECORD of a completed migration, not a tool.\n"
        "Re-running it reverts the dpov withdrawal, the staffRatio unit correction\n"
        "and the 2024-equivalent price base.\n"
        "Read the module docstring. If you still mean it, pass --i-know-this-reverts."
    )

# Resolve from this file. It used to hard-code a macOS home directory that does not
# exist on the machine this project runs on, so the script was doubly inert: guarded,
# and pointed at nothing. Inert is not the same as harmless in a shipped tree.
MACH = Path(__file__).resolve().parent          # europe/tool_machinery
ROOT = MACH.parent.parent                       # the Deliverable root

spec = importlib.util.spec_from_file_location("params", ROOT / "uk/model/parameters.py")
P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
REG = P.PARAMETER_REGISTRY["service_demand"]

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
UK_ORDER = list(UK_TO_REG)
# EU service position -> the UK service its values came from
EU_SOURCE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 8]

# unit costs whose registry attribution is a volume or prevalence publication
VOLUME_ATTRIB = {"food_banks", "debt_advice", "mental_health_iapt", "housing_support",
                 "childrens_services", "domestic_abuse", "substance_misuse"}
NO_ATTRIB = {"jobcentre_plus", "uc_processing"}

CLASSIFIED = ("elastLow", "elastCentral", "elastHigh", "staffRatio", "unitCost")


def uk_notes(name):
    """provenance class and note for each classified field of one UK service."""
    key = REG[UK_TO_REG[name]]
    src, val = key["source"], key["value"]
    cen = val["demand_elasticity"]
    rng = key.get("range", {}).get("demand_elasticity")
    cls, note = {}, {}

    cls["elastCentral"] = "national_source"
    note["elastCentral"] = f"Registry demand_elasticity = {cen}, taken directly. Source: {src}"
    for f, mult, word in (("elastLow", 0.67, "low"), ("elastHigh", 1.5, "high")):
        cls[f] = "national_derived"
        note[f] = (f"Central {cen} x {mult}, a uniform band multiplier applied to every service. "
                   f"The registry's own stated range for this elasticity is {rng}, which this "
                   f"{word} bound does not match; the multiplier itself carries no source.")

    cls["staffRatio"] = "assumption"
    note["staffRatio"] = (
        f"Registry staff_ratio = {val['staff_ratio']} cases per caseworker per year"
        + ("" if val["staff_ratio"] == CURRENT_STAFF[name]
           else f", but the tool carries {CURRENT_STAFF[name]}, which the registry does not support")
        + f". No source string covers staffing; the service attribution is: {src}")

    rk = UK_TO_REG[name]
    cls["unitCost"] = "assumption"
    if rk in NO_ATTRIB:
        note["unitCost"] = (f"No cost attribution and no price year. The service attribution, "
                            f"'{src}', covers the demand relationship, not the cost per case.")
    elif rk == "gp_additional_visits":
        note["unitCost"] = (f"Stated as approximately four additional visits at GBP 39 each "
                            f"(156, rounded to 160). The GBP 39 rate carries no source and no "
                            f"price year. Service attribution: {src}")
    else:
        note["unitCost"] = (f"Attribution is a volume or prevalence publication, which counts "
                            f"people and does not carry a cost per case: '{src}'. No price year "
                            f"is stated and no evidence was found that the cost was checked "
                            f"against the named source.")
    return cls, note


def splice(raw, key, value):
    """Replace the JSON value of `key` in the compact line, preserving formatting."""
    marker = f'"{key}":'
    i = raw.find(marker)
    assert i >= 0, key
    start = i + len(marker)
    opener = raw[start]
    closer = {"[": "]", "{": "}"}[opener]
    depth, j, in_str, esc = 0, start, False, False
    while j < len(raw):
        c = raw[j]
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
        elif c == '"': in_str = True
        elif c == opener: depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                break
        j += 1
    return raw[:start] + json.dumps(value, separators=(",", ":"), ensure_ascii=False) + raw[j + 1:]


counts, report = {}, []
uk_block = json.loads((MACH / "country_uk.json").read_text(encoding="utf-8"))
CURRENT_STAFF = {s["name"]: s["staffRatio"] for s in uk_block["data"]["services"]}

for cc, fn in (("UK", "country_uk.json"), ("ES", "country_es.json"),
               ("IT", "country_it.json"), ("EL", "country_el.json")):
    raw = (MACH / fn).read_text(encoding="utf-8")
    block = json.loads(raw)
    services = block["data"]["services"]
    tally = {}

    for i, s in enumerate(services):
        if cc == "UK":
            cls, note = uk_notes(s["name"])
        else:
            uk_name = UK_ORDER[EU_SOURCE[i]]
            ucls, unote = uk_notes(uk_name)
            cls = {f: "borrowed_unadjusted" for f in CLASSIFIED}
            note = {f: (f"UK value transferred unadjusted from '{uk_name}' ({f} = {s[f]}). "
                        + ("The UK figure is itself an assumption: " + unote[f]
                           if ucls[f] == "assumption" else
                           "UK basis: " + unote[f]))
                    for f in CLASSIFIED}
        s["provenance"] = {f: cls[f] for f in CLASSIFIED}
        s["provenance_note"] = {f: note[f] for f in CLASSIFIED}
        for f in CLASSIFIED:
            tally[cls[f]] = tally.get(cls[f], 0) + 1

    si = block["data"]["shockInterp"]
    if cc == "UK":
        sp = {"du3": "national_derived", "du5": "national_derived",
              "aff3": "national_derived", "aff5": "national_derived",
              "dpov3": "national_derived", "dpov5": "national_derived"}
        sn = {
            "du3": "The modelled shock magnitude, 3pp, a computed point on this country's surface.",
            "du5": "The modelled shock magnitude, 5pp, a computed point on this country's surface.",
            "aff3": "People affected nationally at 3pp, from this country's own shock scenario.",
            "aff5": "People affected nationally at 5pp, from this country's own shock scenario.",
            "dpov3": ("Change in relative poverty after housing costs at 3pp, from this country's "
                      "own scenario aggregates: 28.428 per cent at baseline to 29.083 per cent at "
                      "shock_3pp, a rise of 0.654pp."),
            "dpov5": ("Change in relative poverty after housing costs at 5pp, from this country's "
                      "own scenario aggregates: 28.428 per cent at baseline to 29.429 per cent at "
                      "shock_5pp, a rise of 1.001pp."),
        }
    else:
        sp = {"du3": "national_derived", "du5": "national_derived",
              "aff3": "national_derived", "aff5": "national_derived",
              "dpov3": "borrowed_unadjusted", "dpov5": "borrowed_unadjusted"}
        sn = {
            "du3": "The modelled shock magnitude, 3pp, a computed point on this country's surface.",
            "du5": "The modelled shock magnitude, 5pp, a computed point on this country's surface.",
            "aff3": "People affected nationally at 3pp, scaled to this country's own population.",
            "aff5": "People affected nationally at 5pp, scaled to this country's own population.",
            "dpov3": ("UK modelled poverty response transferred unchanged and NOT country-scaled, "
                      "unlike aff3 beside it: the UK's relative poverty after housing costs rises "
                      "0.654pp at 3pp. How far a job loss pushes a household under the poverty "
                      "line depends on the national benefit system, so this is institutional "
                      "rather than a delivery technology."),
            "dpov5": ("UK modelled poverty response transferred unchanged and NOT country-scaled, "
                      "unlike aff5 beside it: the UK's relative poverty after housing costs rises "
                      "1.001pp at 5pp. How far a job loss pushes a household under the poverty "
                      "line depends on the national benefit system, so this is institutional "
                      "rather than a delivery technology."),
        }
    si["provenance"], si["provenance_note"] = sp, sn
    for v in sp.values():
        tally[v] = tally.get(v, 0) + 1

    raw = splice(raw, "services", services)
    raw = splice(raw, "shockInterp", si)
    json.loads(raw)                                  # must stay valid
    (MACH / fn).write_bytes(raw.encode("utf-8"))   # bytes: see instantiate.py
    counts[cc] = tally
    print(f"{cc}: {sum(tally.values())} parameters classified -> {tally}")

print("\nby class across all four blocks:")
allc = {}
for c in counts.values():
    for k, v in c.items():
        allc[k] = allc.get(k, 0) + v
for k in sorted(allc):
    print(f"   {k:<24}{allc[k]:>5}")
print(f"   {'TOTAL':<24}{sum(allc.values()):>5}")
