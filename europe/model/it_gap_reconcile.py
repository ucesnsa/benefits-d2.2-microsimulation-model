"""it_gap_reconcile.py -- the three mechanisms behind Italy's income tax gap, on ONE basis,
and separated into a bound and a realistic point.

WHY THIS EXISTS, and it is two distinct problems with the account in `it_credit_bound.py`.

ONE. THE THREE SINGLES WERE NOT ALL ON THE SAME BASIS IN THE RECORD. There are two income
tax quantities in this model and they are not the same:

  * `tinna_s`  national IRPEF alone. This is the line Y16_CR_IT table A3.4 publishes at
               EUR 200,784m, so it is the line the EUR 54,459m gap is defined against, and
               it is the only correct basis for closing that gap.
  * `ils_tax`  the whole income tax list: national IRPEF plus the regional surcharge plus
               the flat-tax regime's own revenue `tin00_s` plus the rest.

For a mechanism that only shrinks the base, the two move together and the whole-list effect
is slightly the larger. For the FLAT-TAX REGIME they diverge violently and in the opposite
direction to intuition, because the regime does not remove revenue, it MOVES it: `tinna_s`
falls by 33,351 while `tin00_s` rises from zero to 19,711, so `ils_tax` falls by only 15,875.
A figure of about 15,875 for the flat tax is therefore a WHOLE-LIST figure and cannot be
added to national-IRPEF figures for the other two. This script reports every mechanism on
both bases so the two can never again be mixed.

TWO. THE HEADLINE CONFLATED A BOUND WITH AN ESTIMATE. The compliance adjustment is what
EUROMOD itself applies, so restoring it estimates an actual effect. The credits and the
flat-tax regime are ceilings: every eligible household claiming, every eligible person
electing. Neither happens. Italy records about 1.9 million forfettario electors against the
7.5 million eligible in this build, and its own tax expenditure report puts the credits at a
fraction of the ceiling. So "three mechanisms close 99.5 per cent" is a statement about an
upper bound and must not be written as an explanation. Both are computed here, separately.

The realistic points are anchored on Italy's own published figures rather than on a rate
chosen here: the Rapporto annuale sulle spese fiscali, whose lines are quoted in ITALY_RSF
below with the page each was read from.

Aggregates only. Nothing is populated, no surface is touched, nothing in the build changes.
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
PUBLISHED_TINNA = 200784.0

SELECTORS = ["tintchlyn", "tintcoxyn", "tintclfyn", "tintcstyn",
             "tintaoxyn", "tintccdyn", "tintcfuyn"]
CREDIT_OUT = {"tintchlyn": "tintchl_s", "tintcoxyn": "tintcox_s", "tintclfyn": "tintclf_s",
              "tintcstyn": "tintcst_s", "tintaoxyn": "tintaox_s", "tintccdyn": "tintccd_s",
              "tintcfuyn": "tintcfu_s"}

TCA_TARGET_SELFEMP = 133905.0
FLAT_TAX_THRESHOLD = 85000.0            # the statutory 2023 revenue threshold
FLAT_TAX_CODEBOOK_THRESHOLD = 65000.0   # the EUROMOD input data codebook's figure
ELECTORS_2023 = 1900000.0               # Italy's own count of forfettario electors, 2023

# Italy's own reported annual cost of each relief, EUR millions of foregone revenue, from
# the Rapporto annuale sulle spese fiscali 2024 (MEF), with the page each was read from and
# the beneficiary count the report states. These are what the reliefs ACTUALLY cost, against
# which a ceiling has to sit comfortably above.
ITALY_RSF = {
    "health (spese sanitarie, 19%)":        (4472.5, 21691291, "summary table 13 p.21 and detail p.55"),
    "education (istruzione)":               (675.7, 3882008, "p.58"),
    "insurance (premi assicurativi)":       (282.7, 5091529, "p.61"),
    "funeral (spese funebri)":              (163.1, 528255, "p.61"),
    "veterinary (spese veterinarie)":       (69.3, 1542443, "p.61"),
    "student rent (canoni, studenti)":      (96.5, None, "p.58"),
    "rent (canoni, abitazione principale)": (353.3, 1755342, "p.51"),
}
ITALY_RSF_FORFETARIO = 3490.8     # "Nuovo regime forfetario", summary table 13 p.21
ITALY_RSF_MORTGAGE = 1040.2       # already live in this build via tintcmi_s; not part of the bound


def agg(out, col):
    if col not in out.columns:
        return None
    per_hh = out.groupby("idhh")[col].sum() * MONTHS
    wt = out.groupby("idhh")["dwt"].first()
    return float((per_hh * wt).sum()) / MILLION


def both(out):
    """The two income tax quantities, and the components that explain their difference."""
    return {k: (None if agg(out, k) is None else round(agg(out, k), 1))
            for k in ("tinna_s", "ils_tax", "tinrg_s", "tin00_s", "il_taxabley")}


def run(cobj, frame):
    return engine.run(cobj, SYSTEM, frame, DATASET).outputs[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(EUROPE, "docs", "it_gap_reconcile.json"))
    args = ap.parse_args(argv)

    engine.assert_matched_engine()
    mod = engine.load_model()
    cobj = mod.countries["IT"]
    template = list(cobj.load_data(TRAIN).columns)
    conv = importlib.import_module("convert_it")
    _r = conv.convert_it_2024_full(template)
    real = _r[0] if isinstance(_r, tuple) else _r

    rep = {"system": SYSTEM, "dataset": DATASET, "published_tinna_s": PUBLISHED_TINNA,
           "italy_rsf": {k: {"cost_eur_m": v[0], "beneficiaries": v[1], "source": v[2]}
                         for k, v in ITALY_RSF.items()},
           "italy_rsf_forfetario_eur_m": ITALY_RSF_FORFETARIO}

    base = run(cobj, real)
    b = both(base)
    floor_tinna, floor_ils = b["tinna_s"], b["ils_tax"]
    gap = floor_tinna - PUBLISHED_TINNA
    rep["floor"] = b
    rep["gap_eur_m"] = round(gap, 1)
    print("=" * 100)
    print("FLOOR  tinna_s %,.1f   ils_tax %,.1f   tinrg_s %,.1f   tin00_s %,.1f"
          .replace(",", "") % (b["tinna_s"], b["ils_tax"], b["tinrg_s"], b["tin00_s"]))
    print("GAP against the published national IRPEF of %.0f: %.1f" % (PUBLISHED_TINNA, gap))

    # ---- mechanism builders -------------------------------------------------------
    selfemp_now = agg(base, "yseev")
    tca_factor = TCA_TARGET_SELFEMP / selfemp_now
    yse_annual = pd.to_numeric(real["yseev"], errors="coerce").fillna(0.0).to_numpy() * MONTHS
    dwt = pd.to_numeric(real["dwt"], errors="coerce").fillna(0.0).to_numpy()

    def elig_flat(thres):
        return (yse_annual > 0) & (yse_annual <= thres)

    def apply_tca(d):
        d["yseev"] = pd.to_numeric(d["yseev"], errors="coerce").fillna(0.0) * tca_factor
        return d

    def apply_flat(d, mask):
        d["lse01"] = mask.astype("int64")     # not a column of this input; added, as flat_tax_recheck does
        return d

    def apply_credits(d, mask=None):
        for s in SELECTORS:
            d[s] = 1 if mask is None else mask.astype("int64")
        return d

    def measure(label, tca=False, flat=None, cred=None):
        d = real.copy()
        if tca:
            d = apply_tca(d)
        if flat is not None:
            d = apply_flat(d, flat)
        if cred is not None:
            d = apply_credits(d, None if cred is True else cred)
        o = run(cobj, d)
        r = both(o)
        r["closes_tinna_s"] = round(floor_tinna - r["tinna_s"], 1)
        r["closes_ils_tax"] = round(floor_ils - r["ils_tax"], 1)
        r["credits"] = {CREDIT_OUT[s]: round(agg(o, CREDIT_OUT[s]) or 0.0, 1) for s in SELECTORS}
        print("-" * 100)
        print("%-44s closes tinna_s %9.1f   closes ils_tax %9.1f"
              % (label, r["closes_tinna_s"], r["closes_ils_tax"]))
        return r

    # ---- HH1: the three singles on BOTH bases ------------------------------------
    print("=" * 100)
    print("THE THREE SINGLES, EACH ON BOTH BASES")
    singles = {
        "compliance adjustment": measure("compliance adjustment", tca=True),
        "flat tax, statutory 85,000": measure("flat tax, statutory 85,000",
                                              flat=elig_flat(FLAT_TAX_THRESHOLD)),
        "flat tax, codebook 65,000": measure("flat tax, codebook 65,000",
                                             flat=elig_flat(FLAT_TAX_CODEBOOK_THRESHOLD)),
        "credits, all seven at ceiling": measure("credits, all seven at ceiling", cred=True),
    }
    rep["singles"] = singles

    # ---- HH2: the bound, all three at maximum -----------------------------------
    print("=" * 100)
    print("THE BOUND: all three at maximum")
    bound85 = measure("all three, flat tax at 85,000", tca=True,
                      flat=elig_flat(FLAT_TAX_THRESHOLD), cred=True)
    bound65 = measure("all three, flat tax at 65,000", tca=True,
                      flat=elig_flat(FLAT_TAX_CODEBOOK_THRESHOLD), cred=True)
    sum85 = (singles["compliance adjustment"]["closes_tinna_s"]
             + singles["flat tax, statutory 85,000"]["closes_tinna_s"]
             + singles["credits, all seven at ceiling"]["closes_tinna_s"])
    rep["bound"] = {
        "at_statutory_threshold": bound85, "at_codebook_threshold": bound65,
        "sum_of_singles_tinna_s": round(sum85, 1),
        "interaction_tinna_s": round(sum85 - bound85["closes_tinna_s"], 1),
        "residual_tinna_s": round(gap - bound85["closes_tinna_s"], 1),
        "residual_at_codebook_tinna_s": round(gap - bound65["closes_tinna_s"], 1),
    }

    # ---- HH2: the realistic point ------------------------------------------------
    # Flat tax at the OBSERVED election rate. Italy records 1.9m electors; this build makes
    # 7.5m statutorily eligible. The electors are drawn at that share from the eligible on a
    # fixed seed, so the draw is reproducible; a proportional attribution is reported beside
    # it because the real electors self-select towards the larger benefit and a random draw
    # does not, which makes this a LOWER bound on the realistic effect.
    print("=" * 100)
    print("THE REALISTIC POINT")
    ef = elig_flat(FLAT_TAX_THRESHOLD)
    elig_w = float(dwt[ef].sum())
    share = ELECTORS_2023 / elig_w
    rng = np.random.default_rng(20240)
    draw = np.zeros(len(real), dtype=bool)
    idx = np.flatnonzero(ef)
    order = rng.permutation(idx)
    cum = np.cumsum(dwt[order])
    draw[order[cum <= ELECTORS_2023]] = True
    print("   eligible %.0f weighted; electors %.0f; share %.4f; drawn %.0f weighted"
          % (elig_w, ELECTORS_2023, share, float(dwt[draw].sum())))
    flat_real = measure("flat tax at the observed election rate", flat=draw)
    rep["realistic_flat_tax"] = {
        "eligible_weighted": round(elig_w, 0), "electors_2023": ELECTORS_2023,
        "share": round(share, 4), "drawn_weighted": round(float(dwt[draw].sum()), 0),
        "measured": flat_real,
        "proportional_attribution_tinna_s":
            round(singles["flat tax, statutory 85,000"]["closes_tinna_s"] * share, 1),
        "italy_rsf_forfetario_cost_eur_m": ITALY_RSF_FORFETARIO,
    }

    # Compliance is NOT a ceiling: it is what EUROMOD applies, so its full effect stands.
    # Credits at Italy's own reported cost: the RSF gives the actual annual cost of each
    # relief, so no claiming rate has to be chosen here. The credits that are switched off
    # in this build are summed; the mortgage credit is excluded because it is already live.
    credits_actual = sum(v[0] for v in ITALY_RSF.values())
    rep["credits_at_italys_reported_cost_eur_m"] = round(credits_actual, 1)
    print("   credits at Italy's own reported cost: %.1f EUR m (sum of the RSF lines)"
          % credits_actual)

    # The realistic three-way, measured where it can be and stated where it cannot.
    real_pair = measure("compliance + flat tax at the election rate", tca=True, flat=draw)
    rep["realistic"] = {
        "compliance_and_flat_tax_measured": real_pair,
        "credits_added_from_italys_reporting": round(credits_actual, 1),
        "combined_tinna_s": round(real_pair["closes_tinna_s"] + credits_actual, 1),
        "residual_tinna_s": round(gap - real_pair["closes_tinna_s"] - credits_actual, 1),
    }
    print("   realistic combined %.1f, residual %.1f"
          % (rep["realistic"]["combined_tinna_s"], rep["realistic"]["residual_tinna_s"]))

    # ---- HH3: the credit ceiling against Italy's own reporting -------------------
    print("=" * 100)
    print("THE CREDIT CEILING AGAINST ITALY'S OWN REPORTING")
    ceil = singles["credits, all seven at ceiling"]
    rep["credit_check"] = {
        "ceiling_tinna_s": ceil["closes_tinna_s"],
        "ceiling_ils_tax": ceil["closes_ils_tax"],
        "italys_reported_total_eur_m": round(credits_actual, 1),
        "ratio_ceiling_to_actual": round(ceil["closes_tinna_s"] / credits_actual, 2),
    }
    print("   ceiling %.1f on tinna_s, %.1f on ils_tax; Italy reports %.1f actually claimed"
          % (ceil["closes_tinna_s"], ceil["closes_ils_tax"], credits_actual))
    print("   ratio ceiling / actual: %.2f" % (ceil["closes_tinna_s"] / credits_actual))
    for k, (v, n, src) in ITALY_RSF.items():
        print("      %-40s Italy %8.1f   (%s)" % (k, v, src))

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print("\nwritten", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
