# LICENCE: AGPL-3.0, because this file imports policyengine-uk, which together with
# policyengine-core is published under the GNU Affero General Public License v3. That
# licence is reciprocal, so it reaches this file through the import. The licence is
# confirmed from both packages' installed metadata rather than from the project's own
# notes. The text is in uk/model/Code_FRS_23_24/LICENSE.

"""
09 - Build the magnitude-grid response surface for the Level 2 dial tool.

For each reform family (a "dial"), this stage runs the calibrated UK
microsimulation at an eleven-point magnitude grid, passes every point through
the WEVM welfare layer, and stores the welfare and distributional response
surface. The grids are single-reform: exactly one lever moves per point, the
baseline sits at the zero point of each dial, and the High Income Child Benefit
Charge removal is carried as a binary toggle rather than a slider.

The five policy dials vary a policy parameter at each point; the two shocks are
seeded employment-income transforms applied to the dataset at each magnitude
(the GDP shock is routed through the GDP-to-unemployment transmission, matching
step 06). Every point shares the canonical UC take-up calibration (0.731), so
the surface is consistent with the shipped baseline and reproduces the fixed
scenarios where they coincide with a grid point.

Output (git-ignored, regenerated deterministically):
    outputs/frs_2023_24/dial_grid.json

Usage:
    python model/Code_FRS_23_24/09_build_dial_grid.py
"""

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))          # model/

from Code_FRS_23_24.utils.frs_config import (
    DATA_INTERMEDIATE,
    DATA_OUTPUT,
    FRS_FISCAL_YEAR,
    SURFACE_PATH,
    add_ref_impl_to_path,
)
from Code_FRS_23_24.utils.frs_reforms import (
    make_uc_takeup_modifier,
    compose_modifiers,
    _make_uc_standard_allowance_modifier,
    _make_cb_rate_modifier,
    _make_personal_allowance_modifier,
    _make_uc_taper_modifier,
    _make_uc_work_allowance_modifier,
    _make_cb_remove_hicbc_modifier,
)
from Code_FRS_23_24.utils.pe_runner import run_simulation

add_ref_impl_to_path()
from shock_transmission import gdp_shock_to_unemployment  # noqa: E402

import wevm.wevm as W  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)

_PA_BASE = 12570.0       # 2023-24 income tax personal allowance (frozen)
_UC_TAPER_BASE = 55      # baseline UC taper, per cent
SEED = 42                # matches step 06 so shock selection is identical

# Every point already calculates the full output-variable set; these are the
# columns kept alongside net income so a point can report its fiscal cost and its
# poverty effect without a second run. Emitting them into the surface is a schema
# change, batched separately; `_point_aggregates` computes them from what is kept.
FISCAL_COLUMNS = (
    "income_tax", "national_insurance", "ni_employer", "total_national_insurance",
    "universal_credit", "child_benefit", "housing_benefit", "household_benefits",
    "council_tax",
)
POVERTY_COLUMNS = (
    "in_relative_poverty_bhc", "in_relative_poverty_ahc",
    "in_poverty_bhc", "in_poverty_ahc",
    "poverty_gap_bhc", "poverty_gap_ahc",
)
RETAINED_COLUMNS = ("household_net_income", "household_net_income_ahc") \
    + FISCAL_COLUMNS + POVERTY_COLUMNS


class _GridScenario:
    """Minimal scenario object accepted by pe_runner.run_simulation."""

    def __init__(self, modifier):
        self.parameter_changes = {}
        self.simulation_modifier = modifier


# ----------------------------------------------------------------------------
# Employment shock (mirrors step 06's seeded transform, kept here so the grid
# stage does not modify the verified shock script).
# ----------------------------------------------------------------------------
def _apply_shock_to_persons(person_df, household_df, shock_pp, seed=SEED):
    persons = person_df.copy()
    employed_mask = persons["employment_income"] > 0
    if employed_mask.sum() == 0 or shock_pp <= 0:
        return persons
    hh_weights = household_df.set_index("household_id")["household_weight"]
    persons["_hh_weight"] = persons["person_household_id"].map(hh_weights).fillna(0)
    bu_employed = (
        persons[employed_mask]
        .groupby("person_benunit_id")
        .agg(hh_weight=("_hh_weight", "first"))
    )
    target_weight = shock_pp * bu_employed["hh_weight"].sum()
    bu_employed = bu_employed.sample(frac=1, random_state=seed)
    bu_employed["cum_weight"] = bu_employed["hh_weight"].cumsum()
    selected_bus = bu_employed[bu_employed["cum_weight"] <= target_weight].index
    for bu_id in selected_bus:
        bu_persons = persons[
            (persons["person_benunit_id"] == bu_id) & (persons["employment_income"] > 0)
        ]
        if len(bu_persons) == 0:
            continue
        if len(bu_persons) == 1:
            persons.loc[bu_persons.index, "employment_income"] = 0.0
        else:
            persons.loc[bu_persons["employment_income"].idxmax(), "employment_income"] = 0.0
    persons.drop(columns=["_hh_weight"], inplace=True)
    return persons


# ----------------------------------------------------------------------------
# Dial definitions. magnitude -> modifier for the policy dials; the two shocks
# are dataset transforms handled separately.
# ----------------------------------------------------------------------------
PCT_UP = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]

DIALS = {
    "min_income": dict(
        label="Minimum income (UC standard allowance)", lever="uc_standard_allowance",
        unit="% change", baseline_magnitude=0, magnitudes=PCT_UP, kind="policy",
        modifier=lambda m: _make_uc_standard_allowance_modifier(1.0 + m / 100.0),
    ),
    "child_benefit": dict(
        label="Child or family element (Child Benefit)", lever="child_benefit_rate",
        unit="% change", baseline_magnitude=0, magnitudes=PCT_UP, kind="policy",
        modifier=lambda m: _make_cb_rate_modifier(1.0 + m / 100.0),
    ),
    "personal_allowance": dict(
        label="Personal income tax (personal allowance)", lever="personal_allowance",
        unit="% change", baseline_magnitude=0,
        magnitudes=[-20, -16, -12, -8, -4, 0, 4, 8, 12, 16, 20], kind="policy",
        modifier=lambda m: _make_personal_allowance_modifier(round(_PA_BASE * (1.0 + m / 100.0), 2)),
    ),
    "gdp_shock": dict(
        label="GDP shock (market income)", lever="gdp_change_pct",
        unit="% GDP", baseline_magnitude=0,
        magnitudes=[-10, -9, -8, -7, -6, -5, -4, -3, -2, -1, 0], kind="gdp_shock",
    ),
    "unemployment_shock": dict(
        label="Unemployment shock", lever="unemployment_pp",
        unit="pp", baseline_magnitude=0,
        magnitudes=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], kind="unemployment_shock",
    ),
    "uc_taper": dict(
        label="UC taper rate", lever="uc_taper_rate", unit="% rate",
        baseline_magnitude=_UC_TAPER_BASE,
        magnitudes=[45, 47, 49, 51, 53, 55, 57, 59, 61, 63, 65], kind="policy",
        modifier=lambda m: _make_uc_taper_modifier(m / 100.0),
    ),
    "uc_work_allowance": dict(
        label="UC work allowance", lever="uc_work_allowance",
        unit="% change", baseline_magnitude=0, magnitudes=PCT_UP, kind="policy",
        modifier=lambda m: _make_uc_work_allowance_modifier(1.0 + m / 100.0),
    ),
}


def _welfare_result(base, point_net_income):
    """WEVM and distributional incidence of a point against the baseline.

    `base` is the working-age baseline frame (unit_id, net_income_baseline,
    survey_weight, n_adults, n_children); `point_net_income` is aligned to it.
    Method matches wevm.py: OECD-modified equivalisation, weighted-median anchor,
    AROP floor at 60% of the median, Atkinson weights over the eps grid. Values
    are returned in GBP millions.
    """
    ev = point_net_income - base["net_income_baseline"].to_numpy(float)
    scale = 1.0 + 0.5 * np.maximum(base["n_adults"].to_numpy(float) - 1.0, 0.0) \
        + 0.3 * base["n_children"].to_numpy(float)
    y = base["net_income_baseline"].to_numpy(float) / np.maximum(scale, 1e-6)
    w = base["survey_weight"].to_numpy(float)
    y_ref = W._weighted_median(y, w)
    floor = 0.6 * y_ref
    # Stable sort: units tied on equivalised income must fall in a fixed order, or
    # the decile boundary between two tied units resolves differently on different
    # platforms and the decile split moves while the total stays put.
    order = np.argsort(y, kind="stable")
    cum = np.empty_like(y)
    cum[order] = np.cumsum(w[order]) / w.sum()
    dec = np.clip((cum * 10).astype(int), 0, 9) + 1
    wevm, deciles = [], []
    for eps in W.EPS_GRID:
        kappa = (np.maximum(y, floor) / y_ref) ** (-eps)
        contrib = w * kappa * ev
        wevm.append(round(float(contrib.sum()) / 1e6, 3))
        deciles.append([round(float(contrib[dec == d].sum()) / 1e6, 3) for d in range(1, 11)])
    wsum = w.sum()
    return dict(
        wevm=wevm,
        deciles=deciles,
        winners_pct=round(float(w[ev > 0].sum()) / wsum * 100, 1),
        losers_pct=round(float(w[ev < 0].sum()) / wsum * 100, 1),
    )


def _run_point(person_df, benunit_df, household_df, id_map, modifier, shock_pp):
    """Run one calibrated point and return the working-age per-unit results.

    Returns a frame indexed by unit_id carrying net income and, alongside it, the
    fiscal and poverty columns the run already computed (RETAINED_COLUMNS). The
    engine calculates these whether or not they are kept, so retaining them costs
    nothing; discarding them was what made a per-point fiscal or poverty lens
    require a second pass over the whole grid.
    """
    from policyengine_uk.data.dataset_schema import UKSingleYearDataset

    persons = person_df
    if shock_pp is not None:
        persons = _apply_shock_to_persons(person_df, household_df, shock_pp)
    dataset = UKSingleYearDataset(
        person=persons, benunit=benunit_df, household=household_df, fiscal_year=FRS_FISCAL_YEAR,
    )
    res = run_simulation(dataset, scenario=_GridScenario(modifier), scenario_label="point")
    kept = [c for c in RETAINED_COLUMNS if c in res.columns]
    missing = [c for c in RETAINED_COLUMNS if c not in res.columns]
    if missing:
        log.warning("  point is missing retained columns: %s", ", ".join(missing))
    merged = res[["household_id"] + kept].merge(
        id_map[["pe_household_id", "is_working_age"]],
        left_on="household_id", right_on="pe_household_id", how="left",
    )
    merged = merged[merged["is_working_age"] == True]
    return merged.set_index("household_id")[kept]


def _point_fiscal(base, point_df, base_df):
    """Weighted fiscal deltas for one point, against the baseline, in GBP millions.

    The first five fields carry the names the EU surfaces use, so the four tools
    present one fiscal object: `sic_delta_m` is employee and self-employed National
    Insurance, matching EUROMOD's `ils_sicdy`, and employer NI is reported
    separately because it sits outside that concept. The exchequer identity is the
    EU one, `benefit - tax - sic`, positive meaning a cost to the exchequer.
    """
    w = base["survey_weight"].to_numpy(float)
    idx = base["unit_id"]

    def delta_m(col):
        if col not in point_df.columns or col not in base_df.columns:
            return None
        p = point_df[col].reindex(idx).to_numpy(float)
        b = base_df[col].reindex(idx).to_numpy(float)
        return round(float(((p - b) * w).sum()) / 1e6, 3)

    tax, sic = delta_m("income_tax"), delta_m("national_insurance")
    ben, net = delta_m("household_benefits"), delta_m("household_net_income")
    nier = delta_m("ni_employer")
    out = {
        "income_tax_delta_m": tax,
        "benefit_delta_m": ben,
        "sic_delta_m": sic,
        "net_income_delta_m": net,
        # Employer NI is exchequer revenue, so it belongs in the net cost. Before
        # 2026-08-01 the identity was ben - tax - sic and employer NI was reported
        # beside it but left out, so summing the components did not reproduce the
        # headline. It is exactly zero for every policy dial and the toggle, because
        # none of them changes employment; it is the two shocks, which destroy jobs
        # and so destroy employer contributions, where it matters.
        "net_exchequer_cost_m": round(ben - tax - sic - nier, 3),
    }
    for col, key in (("universal_credit", "uc_delta_m"),
                     ("child_benefit", "child_benefit_delta_m"),
                     ("housing_benefit", "housing_benefit_delta_m"),
                     ("council_tax", "council_tax_delta_m"),
                     ("ni_employer", "ni_employer_delta_m")):
        out[key] = delta_m(col)
    return out


def _point_poverty(base, point_df):
    """Weighted poverty counts for one point, with the denominator beside them.

    PolicyEngine's poverty flags are HOUSEHOLD-entity booleans, so each flag is
    multiplied by that household's person count before weighting: these are
    headcounts of people, not rates and not household counts. Before 2026-08-01
    the flag was summed on its own, which counted households under people names
    and beside a people denominator. The denominator a rate needs is emitted alongside
    (`population_k`, the people living in the modelled working-age units, and
    `units_k`, the units themselves), so the tool layer can form whichever rate it
    decides on without re-running the grid. Levels, not deltas: the change is the
    difference from the zero-magnitude point. Counts are thousands; the two
    poverty gaps are depth measures in GBP millions, not counts.
    """
    w = base["survey_weight"].to_numpy(float)
    idx = base["unit_id"]
    people = (base["n_adults"].to_numpy(float) + base["n_children"].to_numpy(float))

    def headcount(col):
        """People in thousands. PolicyEngine's poverty flags are HOUSEHOLD-entity
        booleans, so the flag must be multiplied by that household's person count
        before weighting. Summing the flag alone counts households, which would
        put household counts under people names, beside population_k as their
        denominator."""
        if col not in point_df.columns:
            return None
        v = point_df[col].reindex(idx).to_numpy(float)
        return round(float((v * people * w).sum()) / 1e3, 3)

    def amount(col):
        """A household-level money total in millions. The gaps are amounts, not
        counts, so they are weighted but not multiplied by the person count."""
        if col not in point_df.columns:
            return None
        v = point_df[col].reindex(idx).to_numpy(float)
        return round(float((v * w).sum()) / 1e6, 3)

    def anchored(col, held):
        """Headcount below a threshold held at the baseline, on the project's own
        OECD-modified equivalisation, matching the EU builder exactly."""
        if held is None or col not in point_df.columns:
            return None
        y = point_df[col].reindex(idx).to_numpy(float) / _equiv_scale(base)
        return round(float((people * w)[y < held].sum()) / 1e3, 3)

    return {
        "relative_bhc_headcount_k": headcount("in_relative_poverty_bhc"),
        "relative_ahc_headcount_k": headcount("in_relative_poverty_ahc"),
        "absolute_bhc_headcount_k": headcount("in_poverty_bhc"),
        "absolute_ahc_headcount_k": headcount("in_poverty_ahc"),
        "anchored_bhc_headcount_k": anchored("household_net_income", _ANCHOR.get("bhc")),
        "anchored_ahc_headcount_k": anchored("household_net_income_ahc", _ANCHOR.get("ahc")),
        "anchored_bhc_threshold_cur": (None if _ANCHOR.get("bhc") is None
                                   else round(float(_ANCHOR["bhc"]), 3)),
        "poverty_gap_bhc_m": amount("poverty_gap_bhc"),
        "poverty_gap_ahc_m": amount("poverty_gap_ahc"),
        "population_k": round(float((people * w).sum()) / 1e3, 3),
        "units_k": round(float(w.sum()) / 1e3, 3),
    }


# The anchored thresholds, computed once at the zero-magnitude baseline point and held
# across every point of every dial. Empty until _set_anchor runs, so a point computed
# before it emits null rather than a wrong number.
_ANCHOR = {}


def _equiv_scale(base):
    """OECD-modified equivalence scale, the same one _welfare_result uses."""
    return np.maximum(
        1.0 + 0.5 * np.maximum(base["n_adults"].to_numpy(float) - 1.0, 0.0)
        + 0.3 * base["n_children"].to_numpy(float), 1e-6)


def _set_anchor(base, base_df):
    """Fix the anchored thresholds at the baseline: 60% of the weighted median
    equivalised household income, before and after housing costs.

    This is the project's own AROP construction, identical to the EU builder's
    arop_line, so the anchored series is the same measure in all four countries.
    It is NOT PolicyEngine's relative line, which is what the relative_* fields
    carry, so the two do not coincide at the baseline; the surface records both
    and meta.poverty_basis says which is which."""
    w = base["survey_weight"].to_numpy(float)
    scale = _equiv_scale(base)
    for key, col in (("bhc", "household_net_income"), ("ahc", "household_net_income_ahc")):
        if col not in base_df.columns:
            continue
        y = base_df[col].reindex(base["unit_id"]).to_numpy(float) / scale
        _ANCHOR[key] = W._income_floor(y, w, None, W._weighted_median(y, w))


def _check_against_reference(reference, dial_id, index, result, mismatches):
    """Compare a rebuilt point's WEVM against a stored surface, if one was given.

    The surface must not move when the run is extended. A single mismatch is
    reported and the build continues; more than one aborts, because at that point
    the rebuild is not reproducing the shipped result and nothing downstream of it
    can be trusted.
    """
    if reference is None:
        return
    try:
        if dial_id == "__toggle__":
            stored = reference["toggles"]["hicbc_removal"]["on"]["wevm"]
        else:
            stored = reference["dials"][dial_id]["points"][index]["wevm"]
    except (KeyError, IndexError):
        return
    if list(stored) != list(result["wevm"]):
        where = dial_id if dial_id == "__toggle__" else f"{dial_id}[{index}]"
        mismatches.append((where, list(stored), list(result["wevm"])))
        log.error("  WEVM MISMATCH at %s: stored %s, rebuilt %s",
                  where, stored, result["wevm"])
        if len(mismatches) > 1:
            raise SystemExit(
                f"aborting: {len(mismatches)} points differ from the stored surface; "
                "the rebuild is not reproducing the shipped result")


def build_grid(reference=None):
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
    mismatches = []
    log.info("Loading dataset tables and id-map ...")
    person_df = pd.read_parquet(DATA_INTERMEDIATE / "pe_persons.parquet")
    benunit_df = pd.read_parquet(DATA_INTERMEDIATE / "pe_benunits.parquet")
    household_df = pd.read_parquet(DATA_INTERMEDIATE / "pe_households.parquet")
    id_map = pd.read_parquet(DATA_INTERMEDIATE / "pe_id_mapping.parquet")

    calib = make_uc_takeup_modifier()

    # Baseline (calibrated), working-age. Reference for every EV.
    log.info("Running calibrated baseline ...")
    base_df = _run_point(person_df, benunit_df, household_df, id_map, calib, None)
    base_ni = base_df["household_net_income"]
    base = (
        id_map[id_map["is_working_age"] == True][["pe_household_id", "num_adults", "num_children"]]
        .rename(columns={"pe_household_id": "unit_id", "num_adults": "n_adults", "num_children": "n_children"})
        .set_index("unit_id")
    )
    base["net_income_baseline"] = base_ni.reindex(base.index).to_numpy()
    # survey weight per working-age household
    hw = household_df.set_index("household_id")["household_weight"]
    base["survey_weight"] = hw.reindex(base.index).to_numpy()
    base = base.reset_index()
    base_net_bn = float((base["net_income_baseline"] * base["survey_weight"]).sum() / 1e9)
    log.info("  baseline working-age net income = GBP %.2fbn over %d units", base_net_bn, len(base))
    # Fix the anchored thresholds here, before any point is computed, so every point
    # of every dial is measured against the same held line.
    _set_anchor(base, base_df)
    log.info("  anchored thresholds held at BHC GBP %.2f, AHC GBP %.2f (equivalised)",
             _ANCHOR.get("bhc", float("nan")), _ANCHOR.get("ahc", float("nan")))

    def aligned(point_ni):
        return point_ni.reindex(base["unit_id"]).to_numpy(float)

    out = {
        "meta": {
            "country": "GB", "year": 2023, "eps_grid": list(W.EPS_GRID),
            "baseline_net_income_bn": round(base_net_bn, 2),
            "n_units_working_age_sample": int(len(base)),
            "uc_takeup_rate": 0.731,
            # What the numbers cover. This builder filters to working-age units before
            # computing anything; the EU builder does not. Same field names, different
            # populations, so the basis travels with the data.
            "population_basis": {
                "scope": "working_age_units",
                "includes": "Benefit units with at least one adult aged 18 to 64.",
                "excludes": "Units in which every adult is 65 or over.",
                "units_k": round(float(base["survey_weight"].sum()) / 1e3, 3),
                "population_k": round(float(((base["n_adults"] + base["n_children"])
                                             * base["survey_weight"]).sum()) / 1e3, 3),
                "summary": ("Working-age units only, meaning benefit units with at least one adult "
                            "aged 18 to 64, excluding units in which every adult is 65 or over."),
            },
            "note": ("Single-reform magnitude grids; one lever per point; the baseline is the "
                     "zero point of each dial; HICBC removal is a binary toggle. WEVM and decile "
                     "contributions are in GBP millions, median-anchored and AROP-floored, equivalised."),
        },
        "dials": {},
        "toggles": {},
    }

    t_start = time.time()
    for dial_id, spec in DIALS.items():
        log.info("\n===== dial: %s (%s) =====", dial_id, spec["label"])
        points = []
        for m in spec["magnitudes"]:
            t0 = time.time()
            if spec["kind"] == "policy":
                # Run every point, including the baseline magnitude: a true no-op
                # modifier returns the baseline net income, so the zero point is a
                # genuine validation that the welfare result is zero there.
                point_df = _run_point(
                    person_df, benunit_df, household_df, id_map,
                    compose_modifiers(calib, spec["modifier"](m)), None,
                )
            else:  # shock dials
                if spec["kind"] == "gdp_shock":
                    shock_pp = gdp_shock_to_unemployment(float(m))["unemployment_change_pp"] / 100.0
                else:
                    shock_pp = m / 100.0
                if shock_pp <= 0:
                    point_df = base_df          # the zero point is the baseline run
                else:
                    point_df = _run_point(person_df, benunit_df, household_df, id_map, calib, shock_pp)
            r = _welfare_result(base, aligned(point_df["household_net_income"]))
            r["magnitude"] = m
            _check_against_reference(reference, dial_id, len(points), r, mismatches)
            r["fiscal"] = _point_fiscal(base, point_df, base_df)
            r["poverty"] = _point_poverty(base, point_df)
            points.append(r)
            log.info("  m=%-4s  WEVM(eps1)=%9.1f  winners=%4.1f%%  losers=%4.1f%%  (%.1fs)",
                     m, r["wevm"][2], r["winners_pct"], r["losers_pct"], time.time() - t0)
        out["dials"][dial_id] = dict(
            label=spec["label"], lever=spec["lever"], unit=spec["unit"],
            baseline_magnitude=spec["baseline_magnitude"], magnitudes=spec["magnitudes"],
            points=points,
        )

    # HICBC removal toggle (off = baseline, on = charge removed).
    log.info("\n===== toggle: hicbc_removal =====")
    off = _welfare_result(base, base["net_income_baseline"].to_numpy(float))
    off["magnitude"] = "off"
    off["fiscal"] = _point_fiscal(base, base_df, base_df)
    off["poverty"] = _point_poverty(base, base_df)
    on_df = _run_point(person_df, benunit_df, household_df, id_map,
                       compose_modifiers(calib, _make_cb_remove_hicbc_modifier()), None)
    on = _welfare_result(base, aligned(on_df["household_net_income"]))
    on["magnitude"] = "on"
    _check_against_reference(reference, "__toggle__", 0, on, mismatches)
    on["fiscal"] = _point_fiscal(base, on_df, base_df)
    on["poverty"] = _point_poverty(base, on_df)
    out["toggles"]["hicbc_removal"] = dict(
        label="Remove the High Income Child Benefit Charge", lever="hicbc",
        off=off, on=on,
    )
    log.info("  HICBC removal: WEVM(eps1)=%.1f  winners=%.1f%%", on["wevm"][2], on["winners_pct"])

    out["meta"]["units"] = {
        "wevm": "GBP millions, welfare-weighted, versus baseline",
        # Must describe the identity the code above actually computes. It said
        # "benefit - tax - sic" for a day after employer NI was folded in, so a
        # rebuild would have re-emitted a string its own numbers contradict.
        "fiscal": "GBP millions versus baseline; net_exchequer_cost_m = benefit_delta_m - "
                  "income_tax_delta_m - sic_delta_m - ni_employer_delta_m, positive is a cost "
                  "to the exchequer. sic_delta_m is the employee contribution and "
                  "ni_employer_delta_m the employer one; both enter the identity.",
        "poverty": "levels, not deltas: headcounts of people in thousands, poverty gaps in GBP "
                   "millions, anchored_bhc_threshold_cur in GBP of equivalised annual income, with "
                   "population_k and units_k as the denominators a rate needs",
        # winners_pct and losers_pct sit on the same panel as poverty rows denominated in
        # people, and a reader who has just read one may take the other the same way. The
        # tool names the base on the face; this says it in the surface too. The UK unit is
        # the benefit unit, which in this build is the same object as the household.
        "winlose": "the weighted count of benefit units with a gain, and with a loss, each "
                   "over the weighted count of all benefit units, times 100. Shares of benefit "
                   "units, not of people, unlike every poverty headcount in the same object, "
                   "which counts people. Both rows are labelled with this base on the tool face.",
    }
    out["meta"]["poverty_basis"] = (
        "Two thresholds, both emitted at every point. RELATIVE (relative_*): PolicyEngine's own "
        "relative low-income line, which moves with the median, so a reform that lowers incomes "
        "generally lowers the line and can cut the measured count without anyone being better "
        "off. ANCHORED (anchored_*): 60% of the weighted median equivalised (OECD-modified) "
        "household income computed once at the zero-magnitude baseline point and held fixed "
        "across every point of every dial, emitted as anchored_bhc_threshold_cur so it is auditable; "
        "the right comparison of a reform against its own baseline. The anchored line is this "
        "project's own AROP construction, identical to the EU builder's, so the anchored series "
        "is the same measure in all four countries; it is NOT PolicyEngine's line, so the "
        "anchored and relative counts do not coincide at the baseline. ANCHORED IS NOT ABSOLUTE: "
        "absolute_* is PolicyEngine's fixed-base-year measure and is unchanged.")
    if mismatches:
        out["meta"]["reference_mismatches"] = [w for w, _, _ in mismatches]

    out_path = SURFACE_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    log.info("\nResponse surface written to %s (%d dials, 1 toggle, %.0fs total)",
             out_path, len(out["dials"]), time.time() - t_start)
    if reference is not None:
        log.info("Reference comparison: %d point(s) differ from the stored surface",
                 len(mismatches))
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", metavar="PATH",
                    help="a stored dial_grid.json; every rebuilt point's WEVM is compared "
                         "against it and the build aborts if more than one differs")
    args = ap.parse_args()
    ref = json.loads(Path(args.reference).read_text(encoding="utf-8")) if args.reference else None
    build_grid(reference=ref)
