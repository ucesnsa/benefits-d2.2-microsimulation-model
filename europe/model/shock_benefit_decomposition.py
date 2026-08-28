"""shock_benefit_decomposition.py -- which benefit instrument moves under a shock, per country.

Why this exists. Spain's benefit system barely moves under a shock: a 10 percentage point
unemployment rise raises benefit spending by EUR 27m against Italy's EUR 4,633m and the UK's
EUR 6,001m. `DATA_ISSUES` 9.2 records it as the last wholly unexplained item and says what is
understood: `les` is read by no live Spanish policy, and contributory unemployment eligibility
runs off `lunmy`, the months-unemployed count, which the shock does not change. But that
mechanism is shared with Greece and Italy, which do respond, so it cannot be the whole of it.

Two hypotheses were checked against the model's own structure before this was written, and
both were disposed of:

  * A PRIOR-YEAR MEANS TEST would explain it: a test on last year's income cannot see a
    current-year shock. It is not what the model does. Spain's `il_bsa00`, the IMV means
    test's income list, expands to leaves including `+yem` and `+yse`, which are exactly the
    two variables the Spanish shock levers touch.
  * A FIXED CASELOAD CAP would explain it. All three countries carry one, and in all three it
    is `$X_target_count = $sum_i_X_elig * $X_rate`, proportional to the eligible count rather
    than fixed, so it scales with eligibility and cannot pin spending against a shock.

So the answer is not structural in either of those ways, and the remaining question is
empirical: WHICH instruments move, and by how much. That is what this measures. It runs one
baseline and one shocked point per country and differences every simulated benefit instrument
the country's `ils_ben` list contains, so the near-zero total can be attributed to named
instruments rather than left as an aggregate.

Aggregates only. Nothing is populated, no surface is touched, no microdata is written.
"""
import argparse
import importlib
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EUROPE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EUROPE, "common"))

import build_grid   # noqa: E402
import config       # noqa: E402
import engine       # noqa: E402
from incomelist_members import defined_lists, expand  # noqa: E402

MONTHS, MILLION = 12, 1e6
CONVERTER_DIR = {
    "ES": os.path.join(EUROPE, "Spain", "model", "es_real"),
    "IT": os.path.join(EUROPE, "Italy", "model", "it_real"),
    "EL": os.path.join(EUROPE, "Greece", "model", "el_real"),
}
SYSTEMS = {"ES": "ES_2023", "IT": "IT_2023", "EL": "EL_2023"}


def agg(out, col):
    if col not in out.columns:
        return None
    per_hh = out.groupby("idhh")[col].sum() * MONTHS
    wt = out.groupby("idhh")["dwt"].first()
    return float((per_hh * wt).sum()) / MILLION


def measure(cc, dial, mag):
    cfg = build_grid.CC_CFG[cc]
    sys.path.insert(0, CONVERTER_DIR[cc])
    mod = engine.load_model()
    cobj = mod.countries[cc]
    sysname, dataset = cfg["system"], cfg["dataset"]
    sysobj = engine.get_system(cobj, sysname)
    template = list(cobj.load_data(cfg["train"]).columns)
    conv = importlib.import_module(cfg["mod"])
    real = getattr(conv, cfg["fn"])(template)[0]
    earn = [v for v in cfg["earn"] if v in real.columns]
    perm, lf = build_grid.nested_employed(real)

    base = engine.run(cobj, sysname, real, dataset).outputs[0]
    reform = build_grid.magnitude_to_reform(config.PROFILES[cc]["reforms"][dial], mag)
    ref = build_grid.run_point(cobj, sysobj, sysname, dataset, real, earn, perm, lf, reform)

    lists = defined_lists(sysobj)
    members = [m.lstrip("+-").replace("(off)", "") for m in expand("ils_ben", lists)]
    seen, rows = set(), []
    for v in members:
        if v in seen:
            continue
        seen.add(v)
        b, r = agg(base, v), agg(ref, v)
        if b is None or r is None:
            continue
        rows.append({"var": v, "baseline_eur_m": round(b, 3),
                     "shocked_eur_m": round(r, 3), "delta_eur_m": round(r - b, 3)})
    tot_b, tot_r = agg(base, "ils_ben"), agg(ref, "ils_ben")
    sys.path.remove(CONVERTER_DIR[cc])
    return {"country": cc, "system": sysname, "dial": dial, "magnitude": mag,
            "labour_force": lf,
            "ils_ben_baseline_eur_m": round(tot_b, 3),
            "ils_ben_shocked_eur_m": round(tot_r, 3),
            "ils_ben_delta_eur_m": round(tot_r - tot_b, 3),
            "components": sorted(rows, key=lambda r: -abs(r["delta_eur_m"]))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", default="ES,IT,EL")
    ap.add_argument("--dial", default="unemployment_shock")
    ap.add_argument("--magnitude", type=float, default=10.0)
    ap.add_argument("--out", default=os.path.join(EUROPE, "docs", "shock_benefit_decomposition.json"))
    args = ap.parse_args(argv)

    engine.assert_matched_engine()
    out = {}
    for cc in [c.strip() for c in args.countries.split(",") if c.strip()]:
        r = measure(cc, args.dial, args.magnitude)
        out[cc] = r
        print("=" * 96)
        print("%s  %s %+g:  ils_ben %.1f -> %.1f, delta %+.1f m"
              % (cc, r["dial"], r["magnitude"], r["ils_ben_baseline_eur_m"],
                 r["ils_ben_shocked_eur_m"], r["ils_ben_delta_eur_m"]))
        for c in r["components"][:12]:
            if abs(c["delta_eur_m"]) < 0.05:
                continue
            print("     %-14s %12.1f -> %12.1f   %+10.1f" %
                  (c["var"], c["baseline_eur_m"], c["shocked_eur_m"], c["delta_eur_m"]))
        moved = [c for c in r["components"] if abs(c["delta_eur_m"]) >= 0.05]
        print("     %d of %d simulated benefit components move at all"
              % (len(moved), len(r["components"])))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\nwritten", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
