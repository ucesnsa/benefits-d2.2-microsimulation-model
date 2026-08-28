#!/usr/bin/env python3
"""Negative tests for the 7.10d valuation-layer reproduction check.

Same principle as tests_negative_drift.py and tests_negative_browser.py: break
exactly the thing the check claims to protect, and require the check to FAIL. A
check that passes on broken data is decoration.

7.10d is the check that did not exist when the Greek gender-based-violence transfer
applied its PPP factor twice. Mutation 1 reconstructs that defect: the
transfer with its PPP factor applied twice.

Runs against in-memory copies of the real blocks. Nothing on disk is touched.
"""
import copy
import re
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("apap", ROOT / "audit_provider_params.py")
apap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apap)

BLOCKS = ROOT / "europe" / "tool_machinery"


def load(cc):
    return json.loads((BLOCKS / ("country_%s.json" % cc)).read_text(encoding="utf-8"))


def outcome(block, name):
    return block["data"]["outcomes"][name]


def verdicts(cc, name, o):
    rows, fails = apap.outcome_conversion_rows(cc, name, o)
    return fails, [r["verdict"] for r in rows]


# ---- the mutations -------------------------------------------------------------
def _undocument_band(o):
    """Remove a row's BAND ORIGIN so its two ends have no origin to recompute from.

    Rewritten 2026-08-05. These two tests used to run against the European housing rows,
    which carried a NOT DERIVED declaration because nothing derived their band ends. The
    stages pass documented those band origins, so the declaration is gone from the tree
    and the tests had no target: both silently started passing on unmutated data. The
    declaration path still exists in 7.10d and still has to be load-bearing, so the
    condition is now synthesised here rather than borrowed from whichever row happens to
    be undocumented this month."""
    o["provenance_note"] = re.sub(r"BAND ORIGIN\s+[0-9.]+\s+AND\s+[0-9.]+;?\s*", "",
                                  o["provenance_note"])
    return o


def m_declaration_stripped(o):
    """A band nobody derives loses its NOT DERIVED declaration. It must go back to
    being a failure: the declaration is the only thing standing between an undocumented
    band end and an unreported one."""
    o = _undocument_band(o)
    o["provenance_note"] += " NOT DERIVED: a reason that is about to be removed."
    o["provenance_note"] = re.sub(r"NOT DERIVED:.*", "", o["provenance_note"])
    return o


def m_declaration_without_reason(o):
    """The declaration kept but emptied. A bare marker is not a reason, and the check
    must not accept one, or the clause becomes a way of silencing the row."""
    o = _undocument_band(o)
    o["provenance_note"] += " NOT DERIVED: a reason that is about to be emptied."
    o["provenance_note"] = re.sub(r"NOT DERIVED:.*", "NOT DERIVED:", o["provenance_note"])
    return o


def m_declaration_masks_wrong_value(o):
    """The declaration must never excuse a value that IS recomputable and lands wrong.
    Greek children's social care carries a real band origin, so breaking a band end and
    appending a declaration has to stay caught by the arithmetic."""
    o["convH"] = o["convH"] * 2
    o["provenance_note"] += " NOT DERIVED: an excuse that must not work."
    return o


def m_gbv_double_ppp(o):
    """The real defect: apply 0.881460 a second time to an already-transferred value.
    These are the exact figures the Greek block shipped from the 2026-07-04 baseline
    until B2, and no check in the suite noticed them."""
    o["convL"], o["convC"], o["convH"] = 1945, 13797, 66831
    return o


def m_gbv_central_only(o):
    """Move only the central value, by one part in fifty. A band that still verifies
    beside a central that does not is the shape a transcription slip takes."""
    o["convC"] = 15651 - 313
    return o


def m_gbv_band_low(o):
    """Move one band end only. The check must read all three points, not just the
    central: a band end is a published figure too."""
    o["convL"] = 2209 - 40
    return o


def m_gbv_factor_dropped(o):
    """Strip the machine-readable clause but leave the prose that names the factor.
    This is the pre-B2 note exactly: readable by a person, unparseable by a check,
    and the condition under which the double application survived."""
    o["provenance_note"] = o["provenance_note"].replace(
        "ORIGIN 15651 FACTOR 1.0; BAND ORIGIN 15651 AND 15651; ", "")
    return o


def m_children_origin_swapped(o):
    """Point the Greek children's transfer at Spain's factor instead of its own.
    Both are real factors in this tree, which is why a check that only looks for
    'a factor' rather than recomputing would pass this."""
    o["provenance_note"] = o["provenance_note"].replace("FACTOR 0.881460", "FACTOR 0.932084")
    return o


def m_employment_spine_tier(o):
    """Put the employment band on the central spine tier at both ends, which is what
    a band copied rather than derived looks like."""
    o["provenance_note"] = o["provenance_note"].replace(
        "BAND ORIGIN 12540 AND 20064", "BAND ORIGIN 16300 AND 16300")
    return o


def m_attribution_reinstated(o):
    """Put the double counterfactual back into children's social care.

    Added 2026-08-05 with the valuation stages. The 8.6 percentage points are the
    difference between two arms of a randomised trial, so the counterfactual is already
    inside them and the attribution is 1.0. This restores the 0.5 that halved the value
    until fix run three, in the note only, leaving the shipped figure alone. It is the
    mutation the whole stage grammar exists for: nothing about the origin, the factor or
    the band changes, and a check that stopped at the factor would pass it.
    """
    o["provenance_note"] = o["provenance_note"].replace(
        "ATTRIBUTION 1.0 1.0 1.0", "ATTRIBUTION 0.5 0.5 0.5")
    return o


def m_attribution_reinstated_housing(o):
    """The same break in a transferred row, where the multiplier is carried rather than
    native: European housing takes the United Kingdom attribution band unchanged, so a
    change to it must fail there too."""
    o["provenance_note"] = o["provenance_note"].replace(
        "ATTRIBUTION 0.500 0.562 0.575", "ATTRIBUTION 0.4 0.5 0.7")
    return o


CASES = [
    ("el", "Domestic abuse / GBV", m_gbv_double_ppp,
     "0.881460 applied twice, the shipped state until B2"),
    ("el", "Domestic abuse / GBV", m_gbv_central_only,
     "central moved 2 per cent, band untouched"),
    ("el", "Domestic abuse / GBV", m_gbv_band_low,
     "one band end moved"),
    ("el", "Domestic abuse / GBV", m_gbv_factor_dropped,
     "note made unparseable, prose kept"),
    ("el", "Children's social care", m_children_origin_swapped,
     "Greek transfer given Spain's factor"),
    ("es", "Employment support", m_employment_spine_tier,
     "band origins collapsed onto the central spine tier"),
    ("es", "Housing / homelessness", m_declaration_stripped,
     "the NOT DERIVED declaration removed from an underived band"),
    ("es", "Housing / homelessness", m_declaration_without_reason,
     "declaration left with no reason after the colon"),
    ("el", "Children's social care", m_declaration_masks_wrong_value,
     "a declaration added to a band that IS derived, over a wrong value"),
    ("uk", "Children's social care", m_attribution_reinstated,
     "a carried multiplier changed: the double counterfactual put back"),
    ("es", "Housing / homelessness", m_attribution_reinstated_housing,
     "a carried multiplier changed in a transferred row"),
]


def main():
    allgood = True
    for cc, name, mutate, why in CASES:
        block = load(cc)
        o = outcome(block, name)
        clean_fails, _ = verdicts(cc, name, o)
        if clean_fails:
            print("[SETUP FAIL] %s %s: unmutated data already fails (%d)"
                  % (cc.upper(), name, clean_fails))
            allgood = False
            continue
        broken = mutate(copy.deepcopy(o))
        fails, vs = verdicts(cc, name, broken)
        caught = fails > 0
        allgood &= caught
        print("[%s] %s %-24s %s" % ("CAUGHT" if caught else "MISSED", cc.upper(),
                                    name[:24], why))
        if not caught:
            print("        verdicts: %s" % vs)
    print()
    print("ALL %d MUTATIONS CAUGHT; 7.10d IS LOAD-BEARING" % len(CASES) if allgood
          else "SOME MUTATIONS SURVIVED; 7.10d IS NOT LOAD-BEARING")
    return 0 if allgood else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
