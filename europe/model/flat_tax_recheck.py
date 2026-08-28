"""flat_tax_recheck.py -- the Italian tax dial's flat-tax caveat, recomputed on the
completed conversion.

The caveat on Italy's `pit_give` dial says the dial reaches more people than the real
schedule does, because `lse01`, the variable that selects the *regime forfetario*, is a
national imputation the public EU-SILC user database does not carry and is therefore zero
for everyone. It sizes the overstatement by taking everyone statutorily eligible into the
regime and re-measuring the dial. Property tax does not enter the IRPEF base, so populating
the second-property component (`aobiv`) should not move this arithmetic. This script
measures it on the final input, so that it is measured rather than assumed.

Method, deliberately the same as the original.
  * `tinyse_it` reads `lse01` and nothing else: at 0 the person's `yse` goes into the
    progressive base (`yse00_s`); at 1 the person is charged 15 per cent (`$FlatRate`) on
    `yse - ils_sicse` through `tin00_s` and leaves the progressive base. Both branches are
    read from the live IT_2023 system rather than recalled.
  * The dial is the committed lever: -2pp on the first IRPEF bracket rate
    (`$tintsna_rate1` group 9), built by `reforms.build_const_overwrites` from the live
    constant, exactly as `build_grid.py` builds it.
  * The dial's income tax effect is `ils_tax` aggregated the way the surface aggregates it:
    summed within `idhh`, times twelve, times the household weight, in EUR millions,
    differenced against that configuration's own baseline.
  * Three configurations. SHIPPED is the surface as it stands, `lse01 = 0` for everyone.
    The two CEILINGS put every statutorily eligible self-employed person into the regime,
    at the EUR 65,000 revenue threshold the EUROMOD input data codebook records and at the
    EUR 85,000 threshold that applies to the 2023 income year. Eligibility is annual
    self-employment income, `yseev * 12`, at or below the threshold, for anyone with
    positive self-employment income.

Six engine runs: a baseline and a -2pp reform for each configuration. Aggregates only;
nothing is populated, no surface is touched, and no microdata is written.
"""
import argparse
import importlib
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EUROPE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EUROPE, "common"))
sys.path.insert(0, os.path.join(EUROPE, "Italy", "model", "pipeline"))
sys.path.insert(0, os.path.join(EUROPE, "Italy", "model", "it_real"))

import engine       # noqa: E402
import config       # noqa: E402
import reforms      # noqa: E402

MONTHS, MILLION = 12, 1e6
SYSTEM, DATASET, TRAIN = "IT_2023", "IT_2024_a1_2015_03_e2", "IT_training_data"

# The two revenue ceilings for the regime. 65,000 is what the EUROMOD input data codebook
# records; 85,000 is the figure in force for the 2023 income year, raised by the 2023
# budget law. Both are carried because the codebook and the policy year disagree.
THRESHOLDS = [65000.0, 85000.0]

# Italy recorded about 1.9 million taxpayers in the regime for 2023. The locator is that
# count as a share of the eligible population this build produces, applied to the
# overstatement, which is linear in the number of electors.
ELECTORS = 1.9e6

# The lines the country report publishes, read at each configuration's baseline as the
# external control on the mechanism.
CONTROL_COLS = ["tinna_s", "tin00_s", "tinrg_s", "il_taxabley", "ils_tax", "ils_sicse"]


def agg(out, col):
    """Annualised, weighted population total of a per-person column, EUR millions.
    The surface's own aggregation, from build_grid.fiscal_aggregate."""
    if col not in out.columns:
        return None
    per_hh = out.groupby("idhh")[col].sum() * MONTHS
    wt = out.groupby("idhh")["dwt"].first()
    return float((per_hh * wt).sum()) / MILLION


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(EUROPE, "docs", "flat_tax_recheck.json"))
    args = ap.parse_args(argv)

    mod = engine.load_model()
    cobj = mod.countries["IT"]
    sysobj = engine.get_system(cobj, SYSTEM)
    template = list(cobj.load_data(TRAIN).columns)
    conv = importlib.import_module("convert_it")
    real = conv.convert_it_2024_full(template)[0]

    # The dial, built from the live constant exactly as the surface builds it.
    reform = dict(config.PROFILES["IT"]["reforms"]["pit_give"])
    reform["delta"] = config.PIT_RATE_DELTA
    consts, skipped = reforms.build_const_overwrites(sysobj, reform)
    if skipped or not consts:
        raise RuntimeError(f"pit_give constant not resolved: skipped={skipped}")
    print(f"dial: {reform['type']} {config.PIT_RATE_DELTA:+} on "
          f"{[n for n, _ in reform['constants']]} -> {consts}")

    yse_annual = pd.to_numeric(real["yseev"], errors="coerce").fillna(0.0).to_numpy() * MONTHS
    dwt = pd.to_numeric(real["dwt"], errors="coerce").fillna(0.0).to_numpy()
    self_employed = yse_annual > 0
    lse01_in_template = "lse01" in template
    print(f"lse01 in the IT input template: {lse01_in_template}; "
          f"{int(self_employed.sum())} people with positive self-employment income "
          f"({float(dwt[self_employed].sum()):,.0f} weighted)")

    configs = [("shipped", None)] + [(f"ceiling_{int(t)}", t) for t in THRESHOLDS]
    rep = {
        "country": "IT", "system": SYSTEM, "dataset": DATASET,
        "converter": os.path.dirname(os.path.abspath(conv.__file__)),
        "dial": {"lever": "$tintsna_rate1 group 9", "delta_pp": 100 * config.PIT_RATE_DELTA,
                 "constants_overwritten": {f"{k[0]}|{k[1]}": v for k, v in consts.items()}},
        "eligibility": ("yseev*12 <= threshold, for anyone with positive self-employment "
                        "income; lse01 set to 1 for exactly that set"),
        "lse01_in_template": lse01_in_template,
        "self_employed_unweighted": int(self_employed.sum()),
        "self_employed_weighted": round(float(dwt[self_employed].sum()), 0),
        "electors_2023": ELECTORS,
        "configurations": {},
    }

    for name, thres in configs:
        d = real.copy()
        if thres is None:
            elig = np.zeros(len(d), dtype=bool)
        else:
            elig = self_employed & (yse_annual <= thres)
        d["lse01"] = elig.astype("int64")

        base = engine.run(cobj, SYSTEM, d, DATASET).outputs[0]
        ref = engine.run(cobj, SYSTEM, d, DATASET, constants=consts).outputs[0]
        b_tax, r_tax = agg(base, "ils_tax"), agg(ref, "ils_tax")
        entry = {
            "threshold_eur": thres,
            "in_regime_unweighted": int(elig.sum()),
            "in_regime_weighted": round(float(dwt[elig].sum()), 0),
            "baseline_eur_m": {c: (None if agg(base, c) is None else round(agg(base, c), 3))
                               for c in CONTROL_COLS},
            "baseline_ils_tax_eur_m": round(b_tax, 3),
            "reform_ils_tax_eur_m": round(r_tax, 3),
            "income_tax_effect_eur_m": round(abs(r_tax - b_tax), 3),
        }
        rep["configurations"][name] = entry
        print(f"\n=== {name} (threshold {thres}) ===")
        print(f"   in regime: {entry['in_regime_unweighted']} people "
              f"({entry['in_regime_weighted']:,.0f} weighted)")
        for c in CONTROL_COLS:
            v = entry["baseline_eur_m"][c]
            print(f"   baseline {c:14} {'n/a' if v is None else f'{v:>14,.1f}'}")
        print(f"   dial income tax effect at -2pp: "
              f"{entry['income_tax_effect_eur_m']:,.3f} EUR m")

    floor = rep["configurations"]["shipped"]["income_tax_effect_eur_m"]
    ship_tinna = rep["configurations"]["shipped"]["baseline_eur_m"]["tinna_s"]
    over = {}
    for name, thres in configs[1:]:
        e = rep["configurations"][name]
        ceil = e["income_tax_effect_eur_m"]
        share = ELECTORS / max(e["in_regime_weighted"], 1.0)
        over[name] = {
            "ceiling_eur_m": ceil,
            "overstatement_vs_ceiling_pct": round(100 * (floor - ceil) / ceil, 2),
            "electors_share_of_eligible": round(share, 4),
            "at_electors_eur_m": round(floor - share * (floor - ceil), 3),
            "overstatement_at_electors_pct": round(
                100 * share * (floor - ceil) / (floor - share * (floor - ceil)), 2),
            "national_irpef_removed_eur_m": round(
                ship_tinna - e["baseline_eur_m"]["tinna_s"], 1),
            "regime_own_revenue_eur_m": e["baseline_eur_m"]["tin00_s"],
        }
    rep["floor_eur_m"] = floor
    rep["overstatement"] = over

    print("\n" + "=" * 78)
    print(f"floor (nobody in the regime): {floor:,.3f} EUR m")
    for name, v in over.items():
        print(f"{name}: ceiling {v['ceiling_eur_m']:,.3f} m, overstated "
              f"{v['overstatement_vs_ceiling_pct']:.2f}%; at {ELECTORS:,.0f} electors "
              f"({v['electors_share_of_eligible']:.1%} of the eligible) "
              f"{v['at_electors_eur_m']:,.0f} m, overstated "
              f"{v['overstatement_at_electors_pct']:.2f}%; national IRPEF removed "
              f"{v['national_irpef_removed_eur_m']:,.0f} m; regime revenue "
              f"{v['regime_own_revenue_eur_m']:,.0f} m")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print("\nwritten", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
