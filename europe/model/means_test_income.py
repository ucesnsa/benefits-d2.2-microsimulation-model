"""means_test_income.py -- which income concept each country's minimum-income means test
reads, and whether a current-year shock can reach it.

Why this exists. Spain's benefit system barely moves under a shock: a 10 percentage point
unemployment rise raises benefit spending by EUR 27m against Italy's EUR 4,633m and the UK's
EUR 6,001m, on a benefit system of broadly comparable size. `DATA_ISSUES` 9.2 records that as
the last wholly unexplained item, and says explicitly that the `les` mechanism it half-blames
is shared with Greece and Italy, which do respond.

There is a candidate explanation and it is checkable rather than arguable. If the Spanish
minimum income is means-tested on the PREVIOUS year's income, a current-year shock cannot
reach the entitlement and the near-zero response is correct behaviour rather than a defect.
The IMV is in fact assessed on the prior fiscal year in law. What matters here is not the law
but what THIS MODEL implements, and that is on disk.

Method. For each country, take the minimum-income policy, walk its functions, and print
every eligibility condition and every income list or variable the test reads, from the live
2023 system. Then classify each income variable the test depends on by whether the two shock
levers touch it: the earnings downturn scales the country's own earnings variables, and the
unemployment shock zeroes them for the people it flips. A test that reads only variables the
shock does not touch cannot respond to the shock, and that is a sufficient explanation.

Aggregates and model structure only. Nothing is run, no data is read, no surface is touched.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EUROPE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EUROPE, "common"))

import config   # noqa: E402
import engine   # noqa: E402

SYSTEMS = {"ES": "ES_2023", "IT": "IT_2023", "EL": "EL_2023"}

# The minimum-income policy in each country, and the instrument the dial moves.
MININC_POLICY = {"ES": "bsa00_es", "IT": "bsamm_it", "EL": "bsa00_el"}

# What each country's shock levers actually touch, from build_grid.CC_CFG.
SHOCK_TOUCHES = {
    "ES": ["yem", "yse"],
    "IT": ["yem", "yse", "yseev"],
    "EL": ["yem", "yse", "yemre", "ysere"],
}


def policies_matching(system_obj, stem):
    out = []
    for p in system_obj.policies:
        nm = (getattr(p, "name", "") or "")
        if nm.lower().startswith(stem.lower()) or stem.lower() in nm.lower():
            out.append(p)
    return out


def dump_policy(p):
    """Every function in the policy, with the parameters that name an income concept."""
    rows = []
    for f in (getattr(p, "functions", None) or []):
        fname = getattr(f, "name", "")
        pars = [((getattr(x, "name", "") or ""), (getattr(x, "value", "") or ""),
                 str(getattr(x, "group", "") or ""))
                for x in (getattr(f, "parameters", None) or [])]
        rows.append((fname, pars))
    return rows


INCOME_HINT = ("il_", "ils_", "y", "b", "p")


def looks_like_income(tok):
    t = tok.strip().lower()
    return (t.startswith(("il_", "ils_")) or
            t[:1] in ("y", "b", "p") and len(t) >= 3 and t.replace("_", "").isalnum())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", default="ES,IT,EL")
    ap.add_argument("--out", default=os.path.join(EUROPE, "docs", "means_test_income.json"))
    args = ap.parse_args(argv)

    engine.assert_matched_engine()
    mod = engine.load_model()
    report = {}
    for cc in [c.strip() for c in args.countries.split(",") if c.strip()]:
        sysname = SYSTEMS[cc]
        sysobj = engine.get_system(mod.countries[cc], sysname)
        stem = MININC_POLICY[cc]
        pols = policies_matching(sysobj, stem)
        print("=" * 100)
        print("%s (%s): minimum income policy stem %r -> %d matching polic(ies): %s"
              % (cc, sysname, stem, len(pols), [getattr(p, "name", "") for p in pols]))
        entry = {"system": sysname, "policy_stem": stem, "shock_touches": SHOCK_TOUCHES[cc],
                 "policies": {}}
        for p in pols:
            pname = getattr(p, "name", "")
            rows = dump_policy(p)
            entry["policies"][pname] = [{"function": f, "parameters": pars} for f, pars in rows]
            print("  --- policy %s: %d functions" % (pname, len(rows)))
            for f, pars in rows:
                interesting = [(k, v) for k, v in [(a, b) for a, b, _ in pars]
                               if k.lower() in ("incomelist", "income_list", "il", "base",
                                                "elig_cond", "cond", "run_cond", "output_var",
                                                "who_must_be_elig", "tu_name", "comp_cond",
                                                "elig_1", "elig_2", "amount", "result_var")
                               or "il_" in str(v).lower() or "ils_" in str(v).lower()]
                if interesting:
                    print("      %-14s %s" % (f, "; ".join("%s=%s" % (k, v) for k, v in interesting)[:200]))
        report[cc] = entry
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print("\nwritten", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
