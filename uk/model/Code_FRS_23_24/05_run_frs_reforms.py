# LICENCE: AGPL-3.0, because this file imports policyengine-uk, which together with
# policyengine-core is published under the GNU Affero General Public License v3. That
# licence is reciprocal, so it reaches this file through the import. The licence is
# confirmed from both packages' installed metadata rather than from the project's own
# notes. The text is in uk/model/Code_FRS_23_24/LICENSE.

"""
05 — Run FRS 2023-24 reform scenarios.

For each of the 13+ reforms in ``REFORM_CATALOGUE``, creates a
``Simulation`` with the reform's modifier applied, calculates all
output variables, and compares against the baseline.

Input
-----
- data/frs_2023_24/intermediate/pe_dataset.h5
- data/frs_2023_24/output/frs_baseline_results.parquet  (from step 04)

Output
------
- data/frs_2023_24/output/frs_reform_results.parquet      (all reforms, stacked)
- data/frs_2023_24/output/frs_reform_comparison.xlsx      (summary comparison table)

Usage
-----
    python model/Code_FRS_23_24/05_run_frs_reforms.py
"""

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)


def _load_dataset():
    """Load the UKSingleYearDataset."""
    from policyengine_uk.data.dataset_schema import UKSingleYearDataset

    h5_path = DATA_INTERMEDIATE / "pe_dataset.h5"
    return UKSingleYearDataset(file_path=str(h5_path))


def _run_reform(dataset, reform_name: str, modifier) -> pd.DataFrame:
    """Run a single reform scenario and return household-level results.

    Args:
        dataset: UKSingleYearDataset.
        reform_name: Reform identifier (for the 'scenario' column).
        modifier: Callable that modifies sim parameters.

    Returns:
        DataFrame with one row per household.
    """
    from policyengine_uk.utils.scenario import Scenario

    from Code_FRS_23_24.utils.pe_runner import run_simulation

    scenario = Scenario(simulation_modifier=modifier)
    return run_simulation(dataset, scenario=scenario, scenario_label=reform_name)


def _compute_comparison_row(
    df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    reform_id: str,
    reform_info: dict,
) -> dict:
    """Compute aggregate metrics for a single reform vs baseline."""
    total_weight = df["household_weight"].sum()

    def _weighted_total_bn(frame: pd.DataFrame, col: str) -> float:
        if col in frame.columns:
            return (frame[col] * frame["household_weight"]).sum() / 1e9
        return 0.0

    row = {
        "reform_id": reform_id,
        "reform_name": reform_info.get("name", ""),
        "category": reform_info.get("category", ""),
        "direction": reform_info.get("direction", ""),
        "estimated_cost_bn": reform_info.get("estimated_cost_bn", 0.0),
        "total_uc_bn": _weighted_total_bn(df, "universal_credit"),
        "total_benefits_bn": _weighted_total_bn(df, "household_benefits"),
        "total_tax_bn": _weighted_total_bn(df, "income_tax"),
        "total_ni_bn": _weighted_total_bn(df, "national_insurance"),
        "total_net_income_bn": _weighted_total_bn(df, "household_net_income"),
    }

    # Deltas from baseline
    base_benefits = _weighted_total_bn(baseline_df, "household_benefits")
    base_tax = _weighted_total_bn(baseline_df, "income_tax")
    base_ni = _weighted_total_bn(baseline_df, "national_insurance")
    base_uc = _weighted_total_bn(baseline_df, "universal_credit")

    row["delta_benefits_bn"] = row["total_benefits_bn"] - base_benefits
    row["delta_tax_bn"] = row["total_tax_bn"] - base_tax
    row["delta_uc_bn"] = row["total_uc_bn"] - base_uc
    row["delta_fiscal_bn"] = (
        (row["total_tax_bn"] + row["total_ni_bn"])
        - row["total_benefits_bn"]
        - ((base_tax + base_ni) - base_benefits)
    )

    # Winners / losers (>£1 change in net income)
    if "household_net_income" in df.columns and "household_net_income" in baseline_df.columns:
        merged = pd.merge(
            baseline_df[["household_id", "household_net_income", "household_weight"]],
            df[["household_id", "household_net_income"]],
            on="household_id",
            suffixes=("_base", "_reform"),
        )
        merged["delta"] = merged["household_net_income_reform"] - merged["household_net_income_base"]
        tw = merged["household_weight"].sum()
        row["winners_pct"] = round(
            merged.loc[merged["delta"] > 1, "household_weight"].sum() / tw * 100, 1
        ) if tw > 0 else 0.0
        row["losers_pct"] = round(
            merged.loc[merged["delta"] < -1, "household_weight"].sum() / tw * 100, 1
        ) if tw > 0 else 0.0
    else:
        row["winners_pct"] = 0.0
        row["losers_pct"] = 0.0

    return row


def run_reforms() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run all reforms and produce comparison table.

    Returns:
        (stacked_results, comparison_table)
    """
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)

    # Import reform catalogue from reference implementation
    add_ref_impl_to_path()
    from Code_FRS_23_24.utils.frs_reforms import REFORM_CATALOGUE, get_reform
    dataset = _load_dataset()

    # Load baseline
    baseline_path = DATA_OUTPUT / "frs_baseline_results.parquet"
    if baseline_path.exists():
        log.info("Loading pre-computed baseline from %s", baseline_path)
        baseline_df = pd.read_parquet(baseline_path)
    else:
        raise FileNotFoundError(
            f"No cached baseline at {baseline_path}. "
            "Run step 04 first:\n"
            "    python model/Code_FRS_23_24/04_run_frs_baseline.py"
        )

    all_results = [baseline_df.assign(scenario="baseline")]
    comparison_rows = []

    # Reforms incompatible with step 05 (single-year, parameter-only sim):
    #   - "Combined" reforms need a GDP shock applied to the dataset (step 07)
    #   - freeze_all_thresholds is a no-op at PE_PERIOD=2023 (fiscal drag
    #     requires a multi-year simulation)
    SKIP_REFORMS = {"freeze_all_thresholds"}

    for reform_id in sorted(REFORM_CATALOGUE.keys()):
        reform = get_reform(reform_id)

        if reform["category"] == "Combined":
            log.info("Skipping %s — combined scenario, handled in step 07", reform_id)
            continue
        if reform_id in SKIP_REFORMS:
            log.info("Skipping %s — no-op for this survey year", reform_id)
            continue

        log.info(
            "\n%s\n  Reform: %s (%s)\n%s",
            "=" * 60,
            reform_id,
            reform["name"],
            "=" * 60,
        )

        t0 = time.time()
        reform_df = _run_reform(dataset, reform_id, reform["modifier"])
        elapsed = time.time() - t0

        log.info("  Completed in %.1fs (%s households)", elapsed, f"{len(reform_df):,}")

        all_results.append(reform_df)
        comparison_rows.append(
            _compute_comparison_row(reform_df, baseline_df, reform_id, reform)
        )

    # Stack all results
    stacked = pd.concat(all_results, ignore_index=True)
    stacked_path = DATA_OUTPUT / "frs_reform_results.parquet"
    stacked.to_parquet(stacked_path, index=False)
    log.info("Stacked results saved to %s", stacked_path)

    # Comparison table
    comparison = pd.DataFrame(comparison_rows)
    comp_path = DATA_OUTPUT / "frs_reform_comparison.xlsx"
    comparison.to_excel(comp_path, index=False)
    log.info("Comparison table saved to %s", comp_path)

    # Print summary
    log.info("\n%s", "=" * 70)
    log.info("REFORM COMPARISON SUMMARY")
    log.info("%s", "=" * 70)
    for _, row in comparison.iterrows():
        log.info(
            "  %-30s  Δ UC: %+.2f bn  Δ fiscal: %+.2f bn  winners: %.1f%%  losers: %.1f%%",
            row["reform_id"],
            row["delta_uc_bn"],
            row["delta_fiscal_bn"],
            row["winners_pct"],
            row["losers_pct"],
        )

    return stacked, comparison


if __name__ == "__main__":
    run_reforms()
