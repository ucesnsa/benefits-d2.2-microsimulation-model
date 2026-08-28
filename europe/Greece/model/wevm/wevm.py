"""
wevm.py -- Weighted Equivalent-Variation Measure (WEVM) aggregation layer.

BENEFITS D2.2 microsimulation deliverable.

Consumes the per-unit export emitted by the tax-benefit engine (PolicyEngine UK
for the UK beta; EUROMOD or OpenFisca for the European extension) and produces a
distributionally-weighted monetary welfare change for each reform or shock
scenario.

The layer is engine-agnostic and country-agnostic by construction. It depends
only on the export schema, not on how the export was produced. Standing up a new
country is a matter of emitting the same schema from a different engine, with no
change to this file.

Required export schema (long format, one row per unit per scenario):

    country        ISO-3166 alpha-2, canonical (GB, GR, ...); Eurostat variants
                   UK and EL are remapped on ingest by load_per_unit_export
    year           fiscal-year start as an integer, e.g. 2022 for 2022-23
    scenario       scenario id; the no-reform run must be labelled BASELINE
    unit_id        unique unit identifier within (country, year, scenario);
                   the engine column household_id is aliased to this on ingest
    net_income     disposable income under the scenario (welfare-relevant resource)
    income         market income (retained for reference)
    survey_weight  grossing weight
    household_type category, coarse equivalisation proxy (optional)
    n_adults       optional; enables exact OECD-modified equivalisation
    n_children     optional; enables exact OECD-modified equivalisation

UNIT OF ANALYSIS (confirmed for the UK build):
    Each FRS benefit unit is modelled as a singleton PolicyEngine household
    (1:1, enforced in the build). net_income, income and survey_weight are
    therefore all at benefit-unit level and mutually coherent. Two limitations
    follow and must be stated in the methods, not implied:
      (i)  policies whose incidence runs through the real dwelling rather than
           the claim (council-tax single-person discount, shared housing) are
           mis-stated, so council-tax-touching scenarios carry a caveat;
      (ii) the distributional weight is only as good as its income concept, so
           equivalisation (below) matters for the headline.
"""

from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

BASELINE = "baseline"  # scenario label for the no-reform run
EPS_GRID = (0.0, 0.5, 1.0, 1.5, 2.0)  # inequality-aversion grid
REQUIRED_COLUMNS = (
    "country", "year", "scenario", "unit_id",
    "net_income", "income", "survey_weight",
)

# Eurostat / EU-SILC code variants remapped to canonical ISO 3166-1 alpha-2,
# so one country key spans PolicyEngine (UK) and EUROMOD (EU-SILC) cleanly.
_COUNTRY_CANON = {"UK": "GB", "EL": "GR"}

# OECD-modified equivalence scale, applied only when n_adults / n_children are
# present. First adult 1.0, each further adult 0.5, each child 0.3.
def _oecd_modified(n_adults: np.ndarray, n_children: np.ndarray) -> np.ndarray:
    n_adults = np.asarray(n_adults, float)
    n_children = np.asarray(n_children, float)
    return 1.0 + 0.5 * np.maximum(n_adults - 1.0, 0.0) + 0.3 * n_children


# ----------------------------------------------------------------------------
# Ingest
# ----------------------------------------------------------------------------
def load_per_unit_export(source, id_column: str = "household_id") -> pd.DataFrame:
    """Read one or more per-unit export parquet files into a single frame.

    `source` may be a parquet path, a directory (globbed for
    **/per_unit_export.parquet), or a list of paths. The schema is harmonised:
    the engine id column is aliased to unit_id, and country codes are
    canonicalised to ISO 3166-1 alpha-2.
    """
    if isinstance(source, (list, tuple)):
        paths = list(source)
    elif isinstance(source, str) and os.path.isdir(source):
        paths = sorted(glob.glob(
            os.path.join(source, "**", "per_unit_export.parquet"), recursive=True))
    else:
        paths = [source]
    if not paths:
        raise FileNotFoundError(f"No per_unit_export.parquet found under {source!r}")

    df = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    if "unit_id" not in df.columns and id_column in df.columns:
        df = df.rename(columns={id_column: "unit_id"})
    if "country" in df.columns:
        df["country"] = df["country"].replace(_COUNTRY_CANON)
    validate_schema(df)
    return df


# ----------------------------------------------------------------------------
# Schema validation
# ----------------------------------------------------------------------------
def validate_schema(df: pd.DataFrame) -> None:
    """Fail loudly if the export cannot support a defensible WEVM computation."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Per-unit export missing required columns: {missing}")

    panels = df.groupby(["country", "year"])["scenario"].apply(set)
    for (country, year), scenarios in panels.items():
        if BASELINE not in scenarios:
            raise ValueError(f"No '{BASELINE}' scenario for {country} {year}.")

    dup = int(df.duplicated(["country", "year", "scenario", "unit_id"]).sum())
    if dup:
        raise ValueError(
            f"{dup} duplicate (country, year, scenario, unit_id) rows. "
            "Grain is not one row per unit per scenario."
        )


# ----------------------------------------------------------------------------
# Equivalent variation
# ----------------------------------------------------------------------------
def compute_ev(df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-unit equivalent variation for every non-baseline scenario.

    EV_i = net_income_i(scenario) - net_income_i(baseline).

    This is the quasilinear approximation appropriate for cash reforms, where the
    change in disposable income approximates the equivalent variation. The
    assumption is stated plainly here so it can be cited in the methods section.
    """
    validate_schema(df)

    base = (
        df.loc[df["scenario"] == BASELINE,
               ["country", "year", "unit_id", "net_income"]]
        .rename(columns={"net_income": "net_income_baseline"})
    )
    merged = df.merge(base, on=["country", "year", "unit_id"], how="inner")

    merged["ev"] = merged["net_income"] - merged["net_income_baseline"]
    merged["y_baseline"] = merged["net_income_baseline"]
    return merged.loc[merged["scenario"] != BASELINE].copy()


# ----------------------------------------------------------------------------
# Living standard for the distributional weight
# ----------------------------------------------------------------------------
def living_standard(g: pd.DataFrame, equivalise: bool) -> np.ndarray:
    """Baseline income used in the social weight, equivalised if possible.

    Equivalisation needs n_adults and n_children. If `equivalise` is True and
    those columns are present, apply the OECD-modified scale; otherwise return
    raw baseline income and (when equivalise was requested) leave the caller to
    note that the headline is unequivalised.
    """
    y = g["y_baseline"].to_numpy(float)
    if equivalise and {"n_adults", "n_children"}.issubset(g.columns):
        scale = _oecd_modified(g["n_adults"].to_numpy(), g["n_children"].to_numpy())
        return y / np.maximum(scale, 1e-6)
    return y


# ----------------------------------------------------------------------------
# Distributional weighting
# ----------------------------------------------------------------------------
def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    """Weighted median, used as the reference living standard for the social weight.

    The Green Book convention anchors the distributional weight to one at the
    median equivalised living standard, not the mean. Linear interpolation on the
    weighted cumulative distribution gives a continuous estimate.
    """
    values = np.asarray(values, float)
    weights = np.asarray(weights, float)
    order = np.argsort(values, kind="stable")
    v, w = values[order], weights[order]
    cum = (np.cumsum(w) - 0.5 * w) / w.sum()
    return float(np.interp(0.5, cum, v))


def _income_floor(y: np.ndarray, w: np.ndarray, floor: float | None,
                  y_ref: float) -> float:
    """Positive income floor for the Atkinson social weight.

    Default: 60% of the median equivalised living standard (`y_ref`) -- the
    Eurostat at-risk-of-poverty / UK HBAI relative low-income line. This bounds the
    maximum social weight to (0.6)**(-eps). An explicit `floor` overrides the
    default (used by the sensitivity sweep to pass other values).

    The floor has to sit clear of the bottom of the distribution. On real FRS ~4.5%
    of units have zero or negative baseline income, so a floor read off the low tail
    -- the weighted first percentile, for instance -- lands at ~1 currency unit, and
    those units carry near-unbounded weight and dominate the eps>=1 aggregate. The
    AROP anchor is the project's own documented choice (see README section 8 / PLAN),
    independent of any external axiomatic characterisation.
    """
    if floor is not None:
        return float(floor)
    return float(0.6 * y_ref)


def social_weight(y: np.ndarray, eps: float, y_ref: float, floor: float) -> np.ndarray:
    """
    Normalised social marginal value of income (Atkinson form):

        kappa(y; eps) = (max(y, floor) / y_ref) ** (-eps)

    eps = 0 : utilitarian; kappa == 1 and WEVM reduces to the weighted EV sum.
    eps > 0 : gains to low-income units are up-weighted; the result stays in
              money terms because kappa is normalised to 1 at the reference income.

    Reference and floor are the project's own documented choices: kappa is
    normalised to one at the weighted-median equivalised living standard (y_ref),
    and the living standard is floored at the AROP line (0.6 * y_ref) before the
    power is taken, so kappa is bounded by (0.6)**(-eps) (about 2.78 at eps = 2).
    This convention is AROP-anchored and the EU/UK standard (see README section 8 /
    PLAN); it is independent of the GM/DX axiomatic characterisation, which is a
    separate partner paper and not binding on this deliverable. Nothing downstream
    depends on the internal form of this function.
    """
    y_floored = np.maximum(y, floor)
    return (y_floored / y_ref) ** (-eps)


# ----------------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------------
def wevm(ev_df: pd.DataFrame,
         eps_grid: tuple = EPS_GRID,
         income_floor: float | None = None,
         equivalise: bool = False) -> pd.DataFrame:
    """Scenario-level WEVM across the inequality-aversion grid.

    Returns one row per (country, year, scenario) with a WEVM column per eps,
    plus diagnostics: weighted population, units floored, equivalisation flag,
    and the weighted winners and losers populations.
    """
    records = []
    keys = ["country", "year", "scenario"]
    for (country, year, scenario), g in ev_df.groupby(keys, sort=False):
        y = living_standard(g, equivalise)
        equivalised = equivalise and {"n_adults", "n_children"}.issubset(g.columns)
        w = g["survey_weight"].to_numpy(float)
        ev = g["ev"].to_numpy(float)

        # Anchor first: y_ref is the weighted median of the (unfloored) living
        # standard; the floor is then 60% of that median (the AROP line), so kappa
        # is bounded by (0.6)**(-eps). Computing the floor before the median is
        # what let the old first-percentile rule collapse to ~1 on real FRS.
        y_ref = _weighted_median(y, w)
        floor = _income_floor(y, w, income_floor, y_ref)

        rec = {
            "country": country, "year": year, "scenario": scenario,
            "n_units": int(len(g)),
            "weighted_pop": float(w.sum()),
            "equivalised": bool(equivalised),
            "units_floored": int((y < floor).sum()),
            "winners_pop": float(w[ev > 0].sum()),
            "losers_pop": float(w[ev < 0].sum()),
        }
        for eps in eps_grid:
            kappa = social_weight(y, eps, y_ref, floor)
            rec[f"wevm_eps_{eps:g}"] = float(np.sum(w * kappa * ev))
        records.append(rec)

    return pd.DataFrame.from_records(records)


def wevm_by_decile(ev_df: pd.DataFrame, equivalise: bool = False) -> pd.DataFrame:
    """Mean and total EV by weighted decile of baseline (living-standard) income."""
    out = []
    keys = ["country", "year", "scenario"]
    for (country, year, scenario), g in ev_df.groupby(keys, sort=False):
        y = living_standard(g, equivalise)
        w = g["survey_weight"].to_numpy(float)
        ev = g["ev"].to_numpy(float)

        order = np.argsort(y, kind="stable")
        cum = np.empty_like(y, float)
        cum[order] = np.cumsum(w[order]) / w.sum()
        decile = np.clip((cum * 10).astype(int), 0, 9) + 1

        for d in range(1, 11):
            m = decile == d
            if not m.any():
                continue
            out.append({
                "country": country, "year": year, "scenario": scenario,
                "decile": d,
                "weighted_pop": float(w[m].sum()),
                "mean_ev": float(np.average(ev[m], weights=w[m])),
                "total_ev": float(np.sum(w[m] * ev[m])),
            })
    return pd.DataFrame(out)


# ----------------------------------------------------------------------------
# Synthetic demo (runs without FRS, matching the repo --demo philosophy)
# ----------------------------------------------------------------------------
def _synthetic_export(n: int = 4000, seed: int = 0) -> pd.DataFrame:
    """A small synthetic per-unit export with the locked schema, for testing."""
    rng = np.random.default_rng(seed)
    rows = []
    for year in (2022, 2023):
        base_net = rng.lognormal(mean=10.0, sigma=0.6, size=n)
        weight = rng.uniform(800, 1600, size=n)
        market = base_net * rng.uniform(1.05, 1.6, size=n)
        for scenario in ("baseline", "uc_uplift", "ni_cut", "energy_shock"):
            if scenario == "baseline":
                net = base_net
            elif scenario == "uc_uplift":
                net = base_net + np.maximum(0, 18000 - base_net) * 0.04
            elif scenario == "ni_cut":
                net = base_net + base_net * 0.012
            else:
                net = base_net - 450.0
            for uid in range(n):
                rows.append((
                    "GB", year, scenario, f"{year}_{uid}",
                    float(net[uid]), float(market[uid]), float(weight[uid]),
                ))
    return pd.DataFrame(rows, columns=[
        "country", "year", "scenario", "unit_id",
        "net_income", "income", "survey_weight",
    ])


def _demo() -> None:
    df = _synthetic_export()
    ev = compute_ev(df)
    summary = wevm(ev)
    pd.set_option("display.width", 160, "display.max_columns", 20)
    print("WEVM by scenario and inequality aversion (synthetic demo, GBP):\n")
    print(summary.to_string(index=False))
    print("\nEV by baseline-income decile, 2022, uc_uplift:\n")
    dec = wevm_by_decile(ev)
    print(dec[(dec.year == 2022) & (dec.scenario == "uc_uplift")].to_string(index=False))


if __name__ == "__main__":
    _demo()
