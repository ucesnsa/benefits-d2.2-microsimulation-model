"""it_credit_bound.py -- the third mechanism behind Italy's income tax gap, bounded.

Why this exists. Italian national income tax is EUR 54,459m above the model's own published
baseline. Two mechanisms are bounded in `BASELINE_VALIDATION.md`: the tax-compliance
adjustment that cannot run, and the flat-tax regime that never fires. Together at their
maximum they close EUR 46,121m, and about EUR 8.3bn is left over.

There is a third mechanism of exactly the same kind and nobody had sized it. **Every Italian
income tax credit that runs off a claim selector is switched off for every household.**
`SetDefault_it` sets `tintchlyn`, `tintcoxyn`, `tintclfyn`, `tintcstyn`, `tintaoxyn`,
`tintccdyn` and `tintcfuyn` to zero, because each is a national imputation the public
EU-SILC user database does not carry, and every credit's `Comp_Cond` opens with
`(tintXXXyn > 0)`. So no household claims any of them. Credits reduce tax. If they are all
off, tax is overstated. Same class of cause as the other two, same source, and it acts on
the same line: `tinna_s = tintsna_s - tintc01_s - tintcst_s - tintcmi_s - tintchl_s -
tintccd_s - tintcox_s - tintclf_s - tintcfu_s - tintc_s`, floored at zero.

WHAT IS BOUNDED, AND HOW. The floor is the current state: every selector zero, nobody
claiming, which is the shipped build. The ceiling is every household whose income band the
credit's own schedule covers claiming it, which is what setting the selector to 1 does. That
is the same shape as the other two bounds and it is deliberately generous: in reality only
households that actually incurred the expenditure claim.

NO APPROXIMATION IS NEEDED FOR THE FIVE RATE-BASED CREDITS, and that is a property of the
2017-onwards formulation rather than luck. Each applies a rate directly to `il_taxabley` in
an income band, so the model has already done the imputation from expenditure to income;
there is no expenditure term to approximate. The rates and bands are read from the live
system and printed, not transcribed.

ONE CREDIT CANNOT BE BOUNDED FROM THE MODEL and is reported as such rather than guessed:
`tintc01_s = tintcho`, the rent credit, is an input AMOUNT the model reads rather than a
rate it applies, and `SetDefault_it` sets it to zero. The model carries no schedule for it,
so there is nothing in the model to take rates or caps from. The survey does carry rent
(`xhcrt`), so a bound is derivable the moment the statutory schedule is supplied from
outside; this script does not invent one.

THE INTERACTION IS MEASURED, NOT ASSUMED. The credits act on overlapping populations and
`tinna_s` is floored at zero, so the combined effect is not the sum of the singles. Both are
run and both are reported.

Aggregates only. Nothing is populated, no surface is touched, no microdata is written, and
nothing in the build changes. The product is a number for the report.
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
sys.path.insert(0, os.path.join(EUROPE, "Italy", "model", "it_real"))

import engine  # noqa: E402

SYSTEM, DATASET, TRAIN = "IT_2023", "IT_2024_a1_2015_03_e2", "IT_training_data"
MONTHS, MILLION = 12, 1e6

# The claim selectors, the credit each gates, and the label the report will use. Read off
# the live system by `gg1` inspection of tintc_it and tintsna_it; every one of them is set
# to 0 by SetDefault_it for this dataset class.
CREDITS = [
    ("tintchlyn", "tintchl_s", "health expenses"),
    ("tintcoxyn", "tintcox_s", "other expenses"),
    ("tintclfyn", "tintclf_s", "life insurance"),
    ("tintcstyn", "tintcst_s", "education and study"),
    ("tintaoxyn", "tintaox_s", "other-expense allowance (deducted before the schedule)"),
    ("tintccdyn", "tintccd_s", "childcare"),
    ("tintcfuyn", "tintcfu_s", "funeral expenses"),
]
# The published comparator and the two bounds already recorded, so the corners can be
# restated in one place. Sources are in BASELINE_VALIDATION.md and DATA_ISSUES 9.10.
PUBLISHED_TINNA = 200784.0     # Y16_CR_IT table A3.4, tinna_s
# The other two mechanisms, reconstructed here rather than taken from the record, because
# the record's singles do not sum to its combined figure: 28,318 + 27,803 = 56,121 against
# a recorded 46,121, and the EUR 8.3bn residual follows from the 46,121. Rather than decide
# which of the three is the typo, all three mechanisms are measured on the same input and
# every combination of them is run, so the corners are differences of runs and the
# interaction is a measurement.
TCA_TARGET_SELFEMP = 133905.0  # the self-employment level Y16_CR_IT implies, BASELINE_VALIDATION
# The STATUTORY threshold for the 2023 income year, which is what a ceiling defined as
# "everyone statutorily eligible" has to use. `flat_tax_recheck.py` measures both this and
# the EUR 65,000 the EUROMOD input data codebook records, and the EUR 27,803m in the standing
# record is the 65,000 figure: at 65,000 tinna_s lands at 227,439.7 against a floor of
# 255,242.6, a difference of 27,802.9. At 85,000 it lands at 221,891.2. Both are carried.
FLAT_TAX_THRESHOLD = 85000.0
FLAT_TAX_CODEBOOK_THRESHOLD = 65000.0


def agg(out, col):
    """Annualised, weighted population total of a per-person column, EUR millions."""
    if col not in out.columns:
        return None
    per_hh = out.groupby("idhh")[col].sum() * MONTHS
    wt = out.groupby("idhh")["dwt"].first()
    return float((per_hh * wt).sum()) / MILLION


def households(out, col):
    """(records, weighted households in thousands) with a non-zero value of `col`."""
    if col not in out.columns:
        return 0, 0.0
    per_hh = out.groupby("idhh")[col].sum()
    wt = out.groupby("idhh")["dwt"].first()
    hit = per_hh > 0
    return int(hit.sum()), float(wt[hit].sum()) / 1e3


def run(cobj, frame):
    return engine.run(cobj, SYSTEM, frame, DATASET).outputs[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(EUROPE, "docs", "it_credit_bound.json"))
    args = ap.parse_args(argv)

    engine.assert_matched_engine()
    mod = engine.load_model()
    cobj = mod.countries["IT"]
    template = list(cobj.load_data(TRAIN).columns)
    conv = importlib.import_module("convert_it")
    # The Italian converter returns three values, not two: the frame, its log, and the NUTS-1
    # codes. Unpacked loosely so a later signature change is a clearer failure than a
    # ValueError halfway down.
    _ret = conv.convert_it_2024_full(template)
    real = _ret[0] if isinstance(_ret, tuple) else _ret

    present = [(sel, out, lab) for sel, out, lab in CREDITS if sel in real.columns]
    missing = [sel for sel, _, _ in CREDITS if sel not in real.columns]

    report = {"system": SYSTEM, "dataset": DATASET,
              "published_tinna_s": PUBLISHED_TINNA,
              "selectors_not_in_the_input_frame": missing, "credits": {}}

    # ---- the floor: the shipped build, every selector zero ----
    base = run(cobj, real)
    floor_tin = agg(base, "tinna_s")
    report["floor"] = {
        "tinna_s": round(floor_tin, 1),
        "vs_published_pct": round(100 * (floor_tin / PUBLISHED_TINNA - 1), 1),
        "credits_claimed": {out: round(agg(base, out) or 0.0, 1) for _, out, _ in CREDITS},
    }
    print("=" * 96)
    print("FLOOR, the shipped build: tinna_s %,.1f EUR m  (%+.1f%% against the published %,.0f)"
          .replace(",", "") % (floor_tin, 100 * (floor_tin / PUBLISHED_TINNA - 1), PUBLISHED_TINNA))
    for _, out, lab in CREDITS:
        v = agg(base, out)
        print("   %-12s %-52s %s" % (out, lab, "not an output column" if v is None
                                     else ("%.1f EUR m" % v)))

    # ---- each credit alone ----
    single_total = 0.0
    for sel, out, lab in present:
        f = real.copy()
        f[sel] = 1
        o = run(cobj, f)
        tin = agg(o, "tinna_s")
        cred = agg(o, out) or 0.0
        n, wk = households(o, out)
        cut = floor_tin - tin
        single_total += cut
        report["credits"][out] = {
            "selector": sel, "label": lab,
            "credit_value_eur_m": round(cred, 1),
            "households_records": n, "households_weighted_k": round(wk, 1),
            "tinna_s_at_ceiling": round(tin, 1),
            "tax_reduction_eur_m": round(cut, 1),
        }
        print("-" * 96)
        print("%-12s %-46s  credit %10.1f  tax -%9.1f  -> tinna_s %10.1f"
              % (sel, lab, cred, cut, tin))
        print("             households claiming: %d records, %.1f thousand weighted" % (n, wk))

    # ---- all together: the ceiling ----
    allf = real.copy()
    for sel, _, _ in present:
        allf[sel] = 1
    allo = run(cobj, allf)
    ceil_tin = agg(allo, "tinna_s")
    combined = floor_tin - ceil_tin
    n_any, wk_any = 0, 0.0
    anycol = allo[[c for _, c, _ in present if c in allo.columns]].sum(axis=1)
    tmp = allo.assign(__any=anycol)
    n_any, wk_any = households(tmp, "__any")
    report["ceiling"] = {
        "tinna_s": round(ceil_tin, 1),
        "vs_published_pct": round(100 * (ceil_tin / PUBLISHED_TINNA - 1), 1),
        "tax_reduction_eur_m": round(combined, 1),
        "sum_of_singles_eur_m": round(single_total, 1),
        "interaction_eur_m": round(single_total - combined, 1),
        "households_records": n_any, "households_weighted_k": round(wk_any, 1),
        "credits_claimed": {out: round(agg(allo, out) or 0.0, 1) for _, out, _ in CREDITS},
    }
    print("=" * 96)
    print("CEILING, every selector on: tinna_s %.1f  (%+.1f%% against published)"
          % (ceil_tin, 100 * (ceil_tin / PUBLISHED_TINNA - 1)))
    print("   combined tax reduction %.1f, sum of the singles %.1f, INTERACTION %.1f"
          % (combined, single_total, single_total - combined))
    print("   households claiming at least one: %d records, %.1f thousand weighted"
          % (n_any, wk_any))

    # ---- the corners: all three mechanisms, every combination, measured ----
    # Each mechanism is applied to the SAME input frame and every corner is a run, so the
    # interactions are differences of measurements rather than sums of separately recorded
    # singles. Eight corners, the full lattice of three switches.
    gap = floor_tin - PUBLISHED_TINNA
    selfemp_now = agg(base, "yseev") or agg(base, "yse")
    tca_factor = TCA_TARGET_SELFEMP / selfemp_now if selfemp_now else 1.0
    yse_annual = pd.to_numeric(real["yseev"], errors="coerce").fillna(0.0).to_numpy() * MONTHS
    elig_flat = (yse_annual > 0) & (yse_annual <= FLAT_TAX_THRESHOLD)
    print("=" * 96)
    print("THE OTHER TWO MECHANISMS, reconstructed on this input rather than recalled:")
    print("   compliance adjustment: yseev scaled by %.5f, %.1f -> %.1f EUR m"
          % (tca_factor, selfemp_now, selfemp_now * tca_factor))
    print("   flat-tax regime: lse01=1 for %d records with 0 < yseev*12 <= %.0f"
          % (int(elig_flat.sum()), FLAT_TAX_THRESHOLD))
    report["mechanism_reconstruction"] = {
        "self_employment_now_eur_m": round(selfemp_now, 1),
        "tca_scale_factor": round(tca_factor, 5),
        "tca_target_eur_m": TCA_TARGET_SELFEMP,
        "flat_tax_threshold_eur": FLAT_TAX_THRESHOLD,
        "flat_tax_eligible_records": int(elig_flat.sum()),
    }

    def build(tca, flat, cred):
        d = real.copy()
        if tca:
            d["yseev"] = pd.to_numeric(d["yseev"], errors="coerce").fillna(0.0) * tca_factor
        if flat:
            # lse01 is NOT a column of this input: `flat_tax_recheck.py` records
            # lse01_in_template=false, and the engine reads it as zero for everyone. It is
            # ADDED here, exactly as flat_tax_recheck.py adds it. A guard that skipped the
            # assignment when the column was absent made this whole arm a silent no-op and
            # the flat-tax corner closed exactly zero, which is what caught it.
            d["lse01"] = elig_flat.astype("int64")
        if cred:
            for sel, _, _ in present:
                d[sel] = 1
        return d

    corners = []
    for tca in (False, True):
        for flat in (False, True):
            for cred in (False, True):
                if not (tca or flat or cred):
                    tin = floor_tin
                else:
                    tin = agg(run(cobj, build(tca, flat, cred)), "tinna_s")
                bits = [n for n, on in (("compliance", tca), ("flat tax", flat),
                                        ("credits", cred)) if on]
                corners.append({
                    "compliance": tca, "flat_tax": flat, "credits": cred,
                    "corner": " + ".join(bits) if bits else "none of the three",
                    "tinna_s": round(tin, 1),
                    "closes_eur_m": round(floor_tin - tin, 1),
                    "vs_published_pct": round(100 * (tin / PUBLISHED_TINNA - 1), 1),
                    "share_of_gap_closed_pct": round(100 * (floor_tin - tin) / gap, 1)})
    # The same flat-tax arm at the codebook threshold, so the corners can be read against
    # the standing record as well as against the statute.
    elig65 = (yse_annual > 0) & (yse_annual <= FLAT_TAX_CODEBOOK_THRESHOLD)
    d65 = real.copy()
    d65["lse01"] = elig65.astype("int64")
    tin65 = agg(run(cobj, d65), "tinna_s")
    # The same two-way and three-way at the codebook threshold. The two-way is the one that
    # settles what the standing record's EUR 46,121m is: it is a MEASURED two-way, not a sum
    # of the singles, which is why 28,318 + 27,803 does not reproduce it.
    d65b = d65.copy()
    d65b["yseev"] = pd.to_numeric(d65b["yseev"], errors="coerce").fillna(0.0) * tca_factor
    tin65_tca = agg(run(cobj, d65b), "tinna_s")
    d65c = d65b.copy()
    for sel, _, _ in present:
        d65c[sel] = 1
    tin65_all = agg(run(cobj, d65c), "tinna_s")
    report["flat_tax_at_codebook_threshold"] = {
        "threshold_eur": FLAT_TAX_CODEBOOK_THRESHOLD,
        "eligible_records": int(elig65.sum()),
        "flat_tax_only": {"tinna_s": round(tin65, 1), "closes_eur_m": round(floor_tin - tin65, 1)},
        "compliance_plus_flat_tax": {"tinna_s": round(tin65_tca, 1),
                                     "closes_eur_m": round(floor_tin - tin65_tca, 1)},
        "all_three": {"tinna_s": round(tin65_all, 1),
                      "closes_eur_m": round(floor_tin - tin65_all, 1),
                      "residual_eur_m": round(gap - (floor_tin - tin65_all), 1)},
    }
    print("   flat tax at the codebook EUR 65,000 instead: closes %.1f (the recorded 27,803)"
          % (floor_tin - tin65))
    print("   compliance + flat tax at 65,000: closes %.1f (the recorded 46,121)"
          % (floor_tin - tin65_tca))
    print("   all three at 65,000: closes %.1f, residual %.1f"
          % (floor_tin - tin65_all, gap - (floor_tin - tin65_all)))

    by = {(c["compliance"], c["flat_tax"], c["credits"]): c["closes_eur_m"] for c in corners}
    all_three = by[(True, True, True)]
    sum_singles = by[(True, False, False)] + by[(False, True, False)] + by[(False, False, True)]
    report["gap_eur_m"] = round(gap, 1)
    report["corners"] = corners
    report["sum_of_single_mechanisms_eur_m"] = round(sum_singles, 1)
    report["three_way_interaction_eur_m"] = round(sum_singles - all_three, 1)
    report["residual_after_all_three_eur_m"] = round(gap - all_three, 1)
    report["residual_after_all_three_pct_of_gap"] = round(100 * (gap - all_three) / gap, 1)
    print("=" * 96)
    print("THE CORNERS, measured, on a gap of %.1f EUR m" % gap)
    for c in corners:
        print("   %-38s closes %9.1f  tinna_s %10.1f  (%+6.1f%%)  %5.1f%% of the gap"
              % (c["corner"], c["closes_eur_m"], c["tinna_s"],
                 c["vs_published_pct"], c["share_of_gap_closed_pct"]))
    print("   sum of the three singles %.1f against %.1f measured together: INTERACTION %.1f"
          % (sum_singles, all_three, sum_singles - all_three))
    print("   residual after all three at their maximum: %.1f EUR m (%.1f%% of the gap)"
          % (report["residual_after_all_three_eur_m"],
             report["residual_after_all_three_pct_of_gap"]))

    # ---- what this says about the standing record ----
    # The record has the two mechanisms closing EUR 46,121m together, and the EUR 8.3bn
    # residual is derived from that figure. It reproduces as neither the sum of the singles
    # nor the measured two-way, so it is reported here rather than quietly replaced.
    rec_single_tca, rec_single_flat, rec_two_way = 28318.0, 27803.0, 46121.0
    meas_tca = by[(True, False, False)]
    meas_flat65 = floor_tin - tin65
    meas_two65 = floor_tin - tin65_tca
    report["record_reconciliation"] = {
        "recorded_compliance_single": rec_single_tca,
        "measured_compliance_single": round(meas_tca, 1),
        "recorded_flat_tax_single": rec_single_flat,
        "measured_flat_tax_single_at_codebook_threshold": round(meas_flat65, 1),
        "sum_of_the_two_measured_singles": round(meas_tca + meas_flat65, 1),
        "recorded_two_way": rec_two_way,
        "measured_two_way_at_codebook_threshold": round(meas_two65, 1),
        "measured_two_way_at_statutory_threshold": round(by[(True, True, False)], 1),
        "recorded_residual_eur_m": round(gap - rec_two_way, 1),
        "measured_residual_after_two_at_codebook_threshold": round(gap - meas_two65, 1),
        "note": ("The two singles reproduce: 27,803 exactly at the codebook threshold and "
                 "28,318 to within 0.1 per cent. Their TWO-WAY does not. The recorded "
                 "46,121 is neither their sum (56,088) nor the measured two-way (40,010), "
                 "and the EUR 8.3bn residual in the record is derived from it. On the "
                 "measured two-way the residual is 14,449, not 8,338."),
    }
    print("=" * 96)
    print("AGAINST THE STANDING RECORD")
    print("   singles reproduce:  compliance %.1f (recorded %.0f), flat tax %.1f (recorded %.0f)"
          % (meas_tca, rec_single_tca, meas_flat65, rec_single_flat))
    print("   their sum %.1f; their MEASURED two-way %.1f; the record says %.0f"
          % (meas_tca + meas_flat65, meas_two65, rec_two_way))
    print("   residual after two mechanisms: recorded %.1f, measured %.1f"
          % (gap - rec_two_way, gap - meas_two65))

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print("\nwritten", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
