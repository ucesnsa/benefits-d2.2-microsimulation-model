"""selfemp_sic_share.py -- how much of each displayed social-contribution figure is the
self-employed leg, and how much of that leg is the divergence from the published baseline.

Why this exists. The tools display `sic_delta_m` on the Analyst tab and on the Scenarios
tab, and it feeds `net_exchequer_cost_m`, which is the headline fiscal figure on both tabs
and the denominator of the cost-effectiveness ratio. `sic_delta_m` is `ils_sicdy`, which is
employee PLUS self-employed PLUS other contributions. Self-employed contributions diverge
from each country's published EUROMOD baseline by a large margin in two of the three
countries (`europe/docs/BASELINE_VALIDATION.md`): Italy +93.8 per cent, Spain +18.5 per
cent, Greece -25.0 per cent. Nothing had established how much of a displayed figure that
divergence accounts for.

Two of those three published comparators were wrong when this was written and are corrected
in PUBLISHED below. Italy's read 7,093, which is a count of payers in thousands from table
A3.3 rather than an amount; the amount is 20,144 in A3.4. Greece's read 2,418, a hand sum
that dropped one of the list's six live members. Both are `LIKE_FOR_LIKE_SWEEP.md`.

Spain's figure was +41.3 per cent when this was written. It fell to +18.5 on 2026-08-03,
when `ysemy`, the self-employed months-of-receipt count, stopped being an unconditional 12
and started reading the months-worked variable the employee line already read. Re-run after
that rebuild: Spain's exposure roughly halves with it. Re-run again when the Italian and
Greek published comparators were corrected: the SHARE columns do not move at all, because
they are properties of the run, and only the EXCESS column moves, because it is the only
one that reads the published figure.

The divergence is a level error in a contribution base, so it does not follow that it
propagates to a delta in proportion. This measures the propagation rather than assuming it.

Method. Only the two shock dials move `sic_delta_m` at all; the three policy dials leave it
identically zero at every point, which `re_emit.py` already asserts. So the exposure is
measured at the shock points the tool actually ships, replicating `build_grid.run_point`
exactly: `income_scale` over the country's own earnings variables for the earnings downturn,
and `apply_unemployment` over the same nested permutation for the unemployment shock. At
each point the run's `ils_sicee`, `ils_sicse`, `ils_sicot` and `ils_sicdy` are aggregated
the way the surface aggregates them, and differenced against the same baseline.

Two figures come out of it per point:
  * the self-employed SHARE of the displayed contribution change, and
  * the EXCESS, the part of the self-employed change attributable to the divergence, taken
    as the self-employed change scaled by (1 - published/modelled) at baseline. That is a
    proportional attribution, not a re-simulation: it says what the change would have been
    had the self-employed contribution base been at its published level and responded in
    the same proportion. It is stated as such and is not a correction.

Aggregates only; nothing is populated, no surface is touched, and no microdata is written.
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

import engine       # noqa: E402
import config       # noqa: E402
import reforms      # noqa: E402
import build_grid   # noqa: E402

MONTHS, MILLION = 12, 1e6

# The published EUROMOD Country-Report self-employed contribution line for each country,
# with the table it comes from. Held here in one block, exactly as
# write_baseline_validation.py holds its published figures.
PUBLISHED = {
    "ES": (14551.0, "Y16_CR_ES table A3.4, ils_sicse"),
    # CORRECTED 2026-08-03. This read 7093.0, which is the 2023 cell of table A3.3,
    # "Number of payers (THOUSANDS)", not an amount. The annual amount is in A3.4.
    "IT": (20144.0, "Y16_CR_IT table A3.4, ils_sicse, annual amount in EUR millions "
                    "(NOT A3.3, which is a count of payers in thousands)"),
    # CORRECTED 2026-08-03. The 2418.0 hand sum omitted tscseui_s, EUR 71m.
    "EL": (2489.0, "Y16_CR_EL table A3.4, ils_sicse as its six live members, "
                   "1347+478+71+433+151+9"),
}

# The dataset, system, converter and earnings variables come from build_grid.CC_CFG itself,
# so this cannot drift from the configuration the surface was built with. Only the converter
# directory is added here, because build_grid resolves it from its own sys.path.
CONVERTER_DIR = {
    "ES": os.path.join(EUROPE, "Spain", "model", "es_real"),
    "IT": os.path.join(EUROPE, "Italy", "model", "it_real"),
    "EL": os.path.join(EUROPE, "Greece", "model", "el_real"),
}

SIC_COLS = ["ils_sicee", "ils_sicse", "ils_sicot", "ils_sicdy", "ils_sicer",
            "ils_tax", "ils_ben"]

# The points the tool ships. Measuring every one of the eleven per shock dial would be
# twenty-two engine runs a country; these are the three the Scenarios tab names as fixed
# scenarios plus the two ends, which is where a reader meets the figure.
GDP_POINTS = [-1, -3, -5, -10]
UNEMP_POINTS = [3, 5, 10]


def agg(out, col):
    """Annualised, weighted population total of a per-person column, EUR millions.
    build_grid.fiscal_aggregate, reproduced so this script does not depend on module state."""
    if col not in out.columns:
        return None
    per_hh = out.groupby("idhh")[col].sum() * MONTHS
    wt = out.groupby("idhh")["dwt"].first()
    return float((per_hh * wt).sum()) / MILLION


def sics(out):
    return {c: (None if agg(out, c) is None else round(agg(out, c), 3)) for c in SIC_COLS}


def measure(cc):
    cfg = build_grid.CC_CFG[cc]
    sys.path.insert(0, CONVERTER_DIR[cc])
    mod = engine.load_model()
    cobj = mod.countries[cc]
    sysname, dataset = cfg["system"], cfg["dataset"]
    engine.get_system(cobj, sysname)
    template = list(cobj.load_data(cfg["train"]).columns)
    conv = importlib.import_module(cfg["mod"])
    real = getattr(conv, cfg["fn"])(template)[0]
    earn = [v for v in cfg["earn"] if v in real.columns]
    perm, lf = build_grid.nested_employed(real)

    base_out = engine.run(cobj, sysname, real, dataset).outputs[0]
    base = sics(base_out)
    pub, pub_src = PUBLISHED[cc]
    se_excess_frac = (base["ils_sicse"] - pub) / base["ils_sicse"] if base["ils_sicse"] else 0.0

    rep = {"country": cc, "system": sysname, "dataset": dataset,
           "converter": os.path.dirname(os.path.abspath(conv.__file__)),
           "earn_vars": earn, "labour_force": lf,
           "published_self_employed_eur_m": pub, "published_source": pub_src,
           "baseline_eur_m": base,
           "baseline_self_employed_share_of_sicdy": round(base["ils_sicse"] / base["ils_sicdy"], 4),
           "baseline_self_employed_vs_published_pct": round(
               100 * (base["ils_sicse"] - pub) / pub, 1),
           "self_employed_excess_fraction_of_own_leg": round(se_excess_frac, 4),
           "points": []}

    todo = ([("gdp_shock", m) for m in GDP_POINTS]
            + [("unemployment_shock", m) for m in UNEMP_POINTS])
    for dial, mag in todo:
        reform = build_grid.magnitude_to_reform(config.PROFILES[cc]["reforms"][dial], mag)
        out = build_grid.run_point(cobj, engine.get_system(cobj, sysname), sysname,
                                   dataset, real, earn, perm, lf, reform)
        cur = sics(out)
        d = {c: round(cur[c] - base[c], 3) for c in SIC_COLS if cur[c] is not None}
        sicdy, sicse = d["ils_sicdy"], d["ils_sicse"]
        net = round(d["ils_ben"] - d["ils_tax"] - d["ils_sicdy"] - d["ils_sicer"], 3)
        rep["points"].append({
            "dial": dial, "magnitude": mag,
            "delta_eur_m": d,
            "net_exchequer_cost_m": net,
            "self_employed_share_of_sic_delta_pct": (
                round(100 * sicse / sicdy, 1) if sicdy else None),
            "self_employed_share_of_net_cost_pct": (
                round(100 * abs(sicse) / abs(net), 2) if net else None),
            "divergence_attributable_eur_m": round(sicse * se_excess_frac, 3),
            "divergence_share_of_net_cost_pct": (
                round(100 * abs(sicse * se_excess_frac) / abs(net), 2) if net else None),
        })
        p = rep["points"][-1]
        print("   %-20s %+5s  sicdy %10.1f  sicse %10.1f (%5.1f%% of it)  net %10.1f  "
              "self-emp = %5.2f%% of net, divergence = %5.2f%% of net"
              % (dial, mag, sicdy, sicse,
                 p["self_employed_share_of_sic_delta_pct"] or 0.0, net,
                 p["self_employed_share_of_net_cost_pct"] or 0.0,
                 p["divergence_share_of_net_cost_pct"] or 0.0))
    sys.path.remove(CONVERTER_DIR[cc])
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", default="ES,IT,EL")
    ap.add_argument("--out", default=os.path.join(EUROPE, "docs", "selfemp_sic_share.json"))
    args = ap.parse_args(argv)

    engine.assert_matched_engine()
    out = {}
    for cc in [c.strip() for c in args.countries.split(",") if c.strip()]:
        print("=" * 78)
        print(cc)
        r = measure(cc)
        print("   baseline: sicdy %.1f, of which self-employed %.1f (%.1f%%); published %.1f (%+.1f%%)"
              % (r["baseline_eur_m"]["ils_sicdy"], r["baseline_eur_m"]["ils_sicse"],
                 100 * r["baseline_self_employed_share_of_sicdy"],
                 r["published_self_employed_eur_m"],
                 r["baseline_self_employed_vs_published_pct"]))
        out[cc] = r
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("\nwritten", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
