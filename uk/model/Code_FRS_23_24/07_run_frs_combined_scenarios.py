# LICENCE: AGPL-3.0, because this file imports policyengine-uk, which together with
# policyengine-core is published under the GNU Affero General Public License v3. That
# licence is reciprocal, so it reaches this file through the import. The licence is
# confirmed from both packages' installed metadata rather than from the project's own
# notes. The text is in uk/model/Code_FRS_23_24/LICENSE.

"""
07 — Run the full scenario matrix, the baseline plus 15, on FRS 2023-24.

Combines shock + reform logic from steps 04–06 to run every scenario.
For each scenario:

1.  Resolve the unemployment shock (direct or via Okun's Law).
2.  Apply the shock to the person table.
3.  Apply the reform modifier (if any) via a Scenario object.
4.  Run the simulation.

After all scenarios, produces a comparison table against the reference
implementation's archetype-based results.

Input
-----
- data/frs_2023_24/intermediate/pe_persons.parquet
- data/frs_2023_24/intermediate/pe_benunits.parquet
- data/frs_2023_24/intermediate/pe_households.parquet

Output
------
- data/frs_2023_24/output/frs_all_scenarios.parquet
- data/frs_2023_24/output/frs_scenario_aggregates.xlsx
- data/frs_2023_24/output/frs_vs_archetypes_comparison.xlsx
- data/frs_2023_24/output/per_unit_export.parquet  (valuation layer input)

Usage
-----
    python model/Code_FRS_23_24/07_run_frs_combined_scenarios.py
"""

import importlib.util
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Code_FRS_23_24.utils.frs_config import (
    DATA_INTERMEDIATE,
    DATA_OUTPUT,
    FRS_FISCAL_YEAR,
    OPTIONAL_VARIABLES,
    OUTPUT_VARIABLES,
    PE_PERIOD,
    add_ref_impl_to_path,
)

# Import from numerically-prefixed module using importlib
_shock_spec = importlib.util.spec_from_file_location(
    "frs_shocks",
    Path(__file__).resolve().parent / "06_run_frs_shocks.py",
)
_shock_mod = importlib.util.module_from_spec(_shock_spec)
_shock_spec.loader.exec_module(_shock_mod)
_apply_shock_to_persons = _shock_mod._apply_shock_to_persons

# Per-unit export covers working-age benefit units only.
# FRS 2023-24 wave is 16,754 households (vs 25,050 in 2022-23).
EXPORT_WORKING_AGE_ONLY = True
# Schema-seam keys for the per-unit export consumed by the country-agnostic WEVM
# layer (wevm.py). country is the literal ISO code; year is the FRS survey-start
# year, set explicitly here and deliberately NOT read from FRS_FISCAL_YEAR (which
# is the PolicyEngine calc period -- 2023 in both pipelines -- not the survey year).
EXPORT_COUNTRY = "GB"
EXPORT_SURVEY_YEAR = 2023  # FRS 2023-24 survey-start year
# ------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)
SCENARIOS = {
    "baseline": {"description": "Current UK tax-benefit system (2024 parameters)", "shock_pp": 0.0},
    "shock_3pp": {"description": "Unemployment +3 percentage points (direct)", "shock_pp": 0.03},
    "shock_5pp": {"description": "Unemployment +5 percentage points (direct)", "shock_pp": 0.05},
    "gdp_minus_1": {"description": "GDP -1% -> unemployment via Okun's Law (B=0.4)", "gdp_change_pct": -1.0},
    "gdp_minus_3": {"description": "GDP -3% -> unemployment via Okun's Law (B=0.4)", "gdp_change_pct": -3.0},
    "gdp_minus_5": {"description": "GDP -5% (severe recession) -> Okun's Law", "gdp_change_pct": -5.0},
    "uc_taper_45": {"description": "UC taper rate reduced to 45% (from 55%)", "reform_name": "uc_taper_45", "shock_pp": 0.0},
    "uc_taper_65": {"description": "UC taper rate increased to 65% (cost saving)", "reform_name": "uc_taper_65", "shock_pp": 0.0},
    "uc_work_allowance_up_20": {"description": "UC work allowance raised by 20%", "reform_name": "uc_work_allowance_up_20", "shock_pp": 0.0},
    "uc_standard_up_10": {"description": "UC standard allowance +10%", "reform_name": "uc_standard_up_10", "shock_pp": 0.0},
    "uc_standard_down_10": {"description": "UC standard allowance -10%", "reform_name": "uc_standard_down_10", "shock_pp": 0.0},
    "raise_personal_allowance": {"description": "Personal allowance raised to 15,000 (from 12,570)", "reform_name": "raise_personal_allowance", "shock_pp": 0.0},
    "cb_remove_hicbc": {"description": "Remove High Income Child Benefit Charge", "reform_name": "cb_remove_hicbc", "shock_pp": 0.0},
    "cb_increase_10pct": {"description": "Child benefit rates +10%", "reform_name": "cb_increase_10pct", "shock_pp": 0.0},
    "gdp_minus_3_plus_uc_boost": {"description": "GDP -3% + UC +25/week (COVID-style response)", "reform_name": "gdp_minus_3_plus_uc_boost", "gdp_change_pct": -3.0},
    "gdp_minus_3_plus_tax_cut": {"description": "GDP -3% + personal allowance to 15k", "reform_name": "gdp_minus_3_plus_tax_cut", "gdp_change_pct": -3.0},
}

def _run_single_scenario(
    person_df: pd.DataFrame,
    benunit_df: pd.DataFrame,
    household_df: pd.DataFrame,
    scenario_name: str,
    shock_pp: float,
    modifier=None,
) -> pd.DataFrame:
    """Run one scenario: apply shock + optional reform, return results.

    Args:
        person_df: Base person DataFrame.
        benunit_df: Benunit DataFrame.
        household_df: Household DataFrame.
        scenario_name: Identifier for the scenario.
        shock_pp: Unemployment shock as a fraction (0.0 = no shock).
        modifier: Optional reform modifier callable.

    Returns:
        Household-level results DataFrame.
    """
    from policyengine_uk.data.dataset_schema import UKSingleYearDataset
    from policyengine_uk.utils.scenario import Scenario

    from Code_FRS_23_24.utils.pe_runner import run_simulation

    # Apply shock if needed
    if shock_pp > 0:
        persons = _apply_shock_to_persons(person_df, household_df, shock_pp)
    else:
        persons = person_df

    dataset = UKSingleYearDataset(
        person=persons,
        benunit=benunit_df,
        household=household_df,
        fiscal_year=FRS_FISCAL_YEAR,
    )

    scenario = None
    if modifier is not None:
        scenario = Scenario(simulation_modifier=modifier)

    return run_simulation(dataset, scenario=scenario, scenario_label=scenario_name)


def _compute_scenario_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-scenario weighted aggregates."""
    rows = []
    for scenario_name in df["scenario"].unique():
        sdf = df[df["scenario"] == scenario_name]
        total_weight = sdf["household_weight"].sum()

        agg = {
            "scenario": scenario_name,
            "total_bu_weighted": total_weight,
        }

        numeric_vars = [
            v for v in OUTPUT_VARIABLES
            if v in sdf.columns and pd.api.types.is_numeric_dtype(sdf[v])
        ]

        for var in numeric_vars:
            total = (sdf[var] * sdf["household_weight"]).sum()
            agg[f"{var}_bn"] = total / 1e9
            agg[f"{var}_avg"] = total / total_weight if total_weight > 0 else 0.0

        rows.append(agg)

    return pd.DataFrame(rows)


def run_all_scenarios() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run all SCENARIOS, the baseline plus 15, and produce comparison output.

    Returns:
        (stacked_detail, aggregates)
    """
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)

    # Import from reference implementation
    add_ref_impl_to_path()
    from Code_FRS_23_24.utils.frs_reforms import (
        get_reform, REFORM_CATALOGUE, make_uc_takeup_modifier, compose_modifiers,
    )
    from shock_transmission import gdp_shock_to_unemployment, full_fiscal_impact

    # Load base tables
    person_df = pd.read_parquet(DATA_INTERMEDIATE / "pe_persons.parquet")
    benunit_df = pd.read_parquet(DATA_INTERMEDIATE / "pe_benunits.parquet")
    household_df = pd.read_parquet(DATA_INTERMEDIATE / "pe_households.parquet")

    all_results = []
    transmission_reports = {}

    for name, config in SCENARIOS.items():
        log.info("\n%s", "=" * 60)
        log.info("Scenario: %s", name)
        log.info("  %s", config.get("description", ""))
        log.info("%s", "=" * 60)

        # Resolve shock
        shock_pp = 0.0
        transmission = None

        if "gdp_change_pct" in config:
            gdp = config["gdp_change_pct"]
            macro = gdp_shock_to_unemployment(gdp)
            shock_pp = macro["unemployment_change_pp"] / 100
            transmission = full_fiscal_impact(gdp)
            transmission_reports[name] = transmission
            log.info(
                "  GDP %.1f%% → unemployment +%.2fpp",
                gdp,
                macro["unemployment_change_pp"],
            )
        elif config.get("shock_pp", 0) > 0:
            shock_pp = config["shock_pp"]

        # Resolve reform
        modifier = None
        if "reform_name" in config:
            reform = get_reform(config["reform_name"])
            modifier = reform["modifier"]
            log.info("  Reform: %s", reform["name"])
        elif config.get("reform") is not None:
            # Direct Scenario object (not used in current SCENARIOS but supported)
            modifier = None  # scenario is passed directly

        # Canonical UC take-up calibration (0.731, aligned to the DWP UC outturn)
        # applied to EVERY scenario including baseline, so the whole grid shares
        # one calibrated take-up assumption. See frs_reforms.CANONICAL_UC_TAKEUP_RATE.
        modifier = compose_modifiers(make_uc_takeup_modifier(), modifier)

        # Run
        t0 = time.time()
        results = _run_single_scenario(
            person_df, benunit_df, household_df,
            name, shock_pp, modifier,
        )
        elapsed = time.time() - t0
        log.info("  Completed in %.1fs (%s households)", elapsed, f"{len(results):,}")

        all_results.append(results)

    # Combine
    stacked = pd.concat(all_results, ignore_index=True)

    # Attach BU attributes (household_type, composition, working-age, region)
    # from the step-03 id-map. region is the RWI join key wired through here.
    id_map_path = DATA_INTERMEDIATE / "pe_id_mapping.parquet"
    stacked = _merge_unit_attributes(stacked, id_map_path)

    # Save full detail (all BUs)
    stacked_path = DATA_OUTPUT / "frs_all_scenarios.parquet"
    stacked.to_parquet(stacked_path, index=False)
    log.info("All scenarios saved to %s", stacked_path)

    # Filter to working-age for aggregates (comparable with transmission model)
    if "is_working_age" in stacked.columns:
        stacked_wa = stacked[stacked["is_working_age"] == True]
        n_wa = stacked_wa["household_id"].nunique()
        n_all = stacked["household_id"].nunique()
        log.info(
            "Working-age filter: %s of %s BUs (%s pensioner-only excluded)",
            f"{n_wa:,}", f"{n_all:,}", f"{n_all - n_wa:,}",
        )
    else:
        stacked_wa = stacked
        log.warning("is_working_age not available — using all BUs")

    # Aggregates — working-age national totals
    aggregates = _compute_scenario_aggregates(stacked_wa)

    # Aggregates — by household type (working-age only)
    agg_path = DATA_OUTPUT / "frs_scenario_aggregates.xlsx"
    with pd.ExcelWriter(agg_path, engine="openpyxl") as writer:
        aggregates.to_excel(writer, sheet_name="National", index=False)
        if "household_type" in stacked_wa.columns:
            hh_type_rows = []
            for scenario_name in stacked_wa["scenario"].unique():
                sdf = stacked_wa[stacked_wa["scenario"] == scenario_name]
                for hh_type in sorted(sdf["household_type"].dropna().unique()):
                    tdf = sdf[sdf["household_type"] == hh_type]
                    tw = tdf["household_weight"].sum()
                    row = {
                        "scenario": scenario_name,
                        "household_type": hh_type,
                        "total_bu_weighted": tw,
                    }
                    for var in OUTPUT_VARIABLES:
                        if var in tdf.columns and pd.api.types.is_numeric_dtype(tdf[var]):
                            total = (tdf[var] * tdf["household_weight"]).sum()
                            row[f"{var}_bn"] = total / 1e9
                            row[f"{var}_avg"] = total / tw if tw > 0 else 0.0
                    hh_type_rows.append(row)
            hh_type_agg = pd.DataFrame(hh_type_rows)
            hh_type_agg.to_excel(writer, sheet_name="By Household Type", index=False)
            log.info("Household type aggregates: %d rows", len(hh_type_agg))
    log.info("Aggregates saved to %s", agg_path)

    # Print summary
    log.info("\n%s", "=" * 70)
    log.info("SCENARIO AGGREGATES (£ billions)")
    log.info("%s", "=" * 70)
    summary_cols = [
        c for c in aggregates.columns
        if c.endswith("_bn") and any(
            k in c for k in ["universal_credit", "household_benefits", "income_tax"]
        )
    ]
    for _, row in aggregates.iterrows():
        parts = [f"  {row['scenario']:<30s}"]
        for col in summary_cols[:3]:
            parts.append(f"{col.replace('_bn', '')}: £{row[col]:,.2f}bn")
        log.info("  ".join(parts))

    # Transmission reports
    if transmission_reports:
        trans_rows = []
        for tname, treport in transmission_reports.items():
            t_row = {"scenario": tname}
            t_row.update({f"macro_{k}": v for k, v in treport["macro"].items()})
            t_row.update({
                f"fiscal_{k}": v
                for k, v in treport["fiscal"].items()
                if not isinstance(v, dict)
            })
            if "cost_by_level" in treport["fiscal"]:
                for level, cost in treport["fiscal"]["cost_by_level"].items():
                    t_row[f"fiscal_cost_{level}"] = cost
            trans_rows.append(t_row)

        trans_df = pd.DataFrame(trans_rows)
        trans_path = DATA_OUTPUT / "frs_transmission_reports.xlsx"
        trans_df.to_excel(trans_path, index=False)
        log.info("Transmission reports saved to %s", trans_path)

    # --- Cross-validation: FRS vs archetypes ---
    _cross_validate(aggregates)

    # --- Per-unit export for valuation layer ---
    _export_per_unit(stacked)

    return stacked, aggregates


def _cross_validate(frs_agg: pd.DataFrame) -> None:
    """Compare FRS aggregates with reference implementation archetype results.

    Loads archetype results if available, computes the same metrics, and
    produces a side-by-side comparison table.
    """
    import os

    add_ref_impl_to_path()

    # Try to find archetype results
    from Code_FRS_23_24.utils.frs_config import REF_IMPL_DIR

    archetype_path = REF_IMPL_DIR / "scenario_results_aggregates.xlsx"
    if not archetype_path.exists():
        log.info("No archetype results found at %s — skipping cross-validation", archetype_path)
        return

    log.info("Loading archetype aggregates from %s", archetype_path)
    arch_agg = pd.read_excel(archetype_path)

    # Merge on scenario name
    comparison = pd.merge(
        frs_agg,
        arch_agg,
        on="scenario",
        how="outer",
        suffixes=("_frs", "_arch"),
    )

    comp_path = DATA_OUTPUT / "frs_vs_archetypes_comparison.xlsx"
    comparison.to_excel(comp_path, index=False)
    log.info("Cross-validation saved to %s", comp_path)

    # Print key comparisons
    overlap = comparison.dropna(subset=["scenario"])
    if not overlap.empty:
        log.info("\n%s", "=" * 70)
        log.info("FRS vs ARCHETYPE COMPARISON")
        log.info("%s", "=" * 70)

        for col_base in ["universal_credit_bn", "household_benefits_bn", "income_tax_bn"]:
            frs_col = f"{col_base}_frs"
            arch_col = f"{col_base}_arch"
            if frs_col in overlap.columns and arch_col in overlap.columns:
                for _, row in overlap.iterrows():
                    frs_val = row.get(frs_col, float("nan"))
                    arch_val = row.get(arch_col, float("nan"))
                    if pd.notna(frs_val) and pd.notna(arch_val):
                        log.info(
                            "  %-20s  %-25s  FRS: £%.2fbn  Arch: £%.2fbn",
                            row["scenario"],
                            col_base.replace("_bn", ""),
                            frs_val,
                            arch_val,
                        )


def _merge_unit_attributes(stacked: pd.DataFrame, id_map_path: Path) -> pd.DataFrame:
    """Attach benefit-unit attributes from the step-03 id-map onto `stacked`.

    Brings across household_type, num_adults, num_children, the working-age flag
    and region (the RWI join key), keyed on household_id. Returns `stacked`
    unchanged when the id-map is absent. is_working_age and region are attached
    only when present, so an older id-map without them still merges cleanly.
    """
    if not id_map_path.exists():
        return stacked
    id_map = pd.read_parquet(id_map_path)
    id_map["household_id"] = id_map["pe_household_id"].astype(
        stacked["household_id"].dtype
    )
    merge_cols = ["household_id", "household_type", "num_adults", "num_children"]
    for opt in ("is_working_age", "region"):
        if opt in id_map.columns:
            merge_cols.append(opt)
    return stacked.merge(id_map[merge_cols], on="household_id", how="left")


def _export_per_unit(stacked: pd.DataFrame) -> None:
    """Write the per-unit export required by the valuation (WEVM) layer.

    Reads from the full stacked results and writes a clean parquet matching the
    country-agnostic schema enforced by wevm.py: the required seam keys
    (country, year, unit_id, scenario, net_income, income, survey_weight) plus
    the optional composition fields used for OECD-modified equivalisation.
    Working-age benefit units only.

    Emitted columns:
        country, year, unit_id, scenario, net_income, income, survey_weight,
        household_type, is_working_age, n_adults, n_children

    region note: region is NOT currently carried onto `stacked`. The id-map
    merge in run_all_scenarios() selects only household_id / household_type /
    num_adults / num_children / is_working_age, and step 03 writes
    pe_id_mapping.parquet without a region column (it derives region_str only for
    the PolicyEngine household dataset). The source exists -- FRS gvtregn mapped
    through REGION_MAP in frs_config -- so wiring region in means adding it to the
    id-map in step 03 and to merge_cols here. Until then region is omitted rather
    than fabricated; the optional pass-through below emits it automatically once
    it is present on `stacked`.
    """
    # household_id -> unit_id (engine id becomes the schema unit id);
    # num_adults / num_children -> n_adults / n_children (equivalisation inputs).
    COLUMN_MAP = {
        "household_id": "unit_id",
        "household_net_income": "net_income",
        "total_income": "income",
        "household_weight": "survey_weight",
        "num_adults": "n_adults",
        "num_children": "n_children",
    }

    keep = ["household_id", "scenario",
            "household_net_income", "total_income", "household_weight"]
    # Optional pass-through columns, emitted iff present on `stacked`.
    for opt in ("household_type", "is_working_age",
                "num_adults", "num_children", "region"):
        if opt in stacked.columns:
            keep.append(opt)

    export = stacked[[c for c in keep if c in stacked.columns]].copy()

    if EXPORT_WORKING_AGE_ONLY and "is_working_age" in export.columns:
        export = export[export["is_working_age"] == True]

    export = export.rename(columns=COLUMN_MAP)

    # Schema-seam keys: country is the literal ISO code, year is the explicit
    # survey-start year (NOT FRS_FISCAL_YEAR). Placed first for readability.
    export.insert(0, "country", EXPORT_COUNTRY)
    export.insert(1, "year", EXPORT_SURVEY_YEAR)

    out_path = DATA_OUTPUT / "per_unit_export.parquet"
    export.to_parquet(out_path, index=False)

    n_bu_sample = export["unit_id"].nunique()
    n_scenarios = export["scenario"].nunique()
    weighted_sum = export.loc[export["scenario"] == "baseline", "survey_weight"].sum()
    log.info(
        "Per-unit export saved to %s  (%s BUs × %s scenarios, weighted sum %.0f)",
        out_path, f"{n_bu_sample:,}", n_scenarios, weighted_sum,
    )


if __name__ == "__main__":
    run_all_scenarios()
