# LICENCE: AGPL-3.0, because this file imports policyengine-uk, which together with
# policyengine-core is published under the GNU Affero General Public License v3. That
# licence is reciprocal, so it reaches this file through the import. The licence is
# confirmed from both packages' installed metadata rather than from the project's own
# notes. The text is in uk/model/Code_FRS_23_24/LICENSE.

"""
04 — Run baseline simulation on FRS 2023-24 dataset.

Loads the PE dataset (HDF5), creates a ``Simulation`` with no reforms,
and calculates all output variables for the 2024 tax-benefit year.
Produces both household-level detail and weighted national aggregates.

Input
-----
- data/frs_2023_24/intermediate/pe_dataset.h5

Output
------
- data/frs_2023_24/output/frs_baseline_results.parquet     (one row per household)
- data/frs_2023_24/output/frs_baseline_aggregates.parquet   (one row — national totals)

Usage
-----
    python model/Code_FRS_23_24/04_run_frs_baseline.py
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
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)

RATE_VARIABLES = {
    "marginal_tax_rate",
    "in_poverty_bhc",
}
def _load_dataset():
    """Load the UKSingleYearDataset from the H5 file."""
    from policyengine_uk.data.dataset_schema import UKSingleYearDataset

    h5_path = DATA_INTERMEDIATE / "pe_dataset.h5"
    log.info("Loading dataset from %s ...", h5_path)
    return UKSingleYearDataset(file_path=str(h5_path))


def _run_simulation(dataset, reform=None) -> pd.DataFrame:
    """Run a simulation and extract results into a household-level DataFrame.

    Args:
        dataset: UKSingleYearDataset to simulate.
        reform: Optional PolicyEngine Reform (for policy changes).

    Returns:
        DataFrame with one row per household, columns for each output
        variable plus household_id and household_weight.
    """
    from policyengine_uk import Simulation

    log.info("Building simulation (period=%s)...", PE_PERIOD)
    t0 = time.time()

    kwargs = {"dataset": dataset}
    if reform is not None:
        kwargs["reform"] = reform

    sim = Simulation(**kwargs)

    elapsed_build = time.time() - t0
    log.info("  Simulation built in %.1fs", elapsed_build)

    # Entity dimensions
    hh_ids = np.array(sim.calculate("household_id", PE_PERIOD))
    hh_weights = np.array(sim.calculate("household_weight", PE_PERIOD))
    n_hh = len(hh_ids)

    # Person→household mapping for aggregation
    person_hh_ids = np.array(sim.calculate("person_household_id", PE_PERIOD))
    benunit_ids = np.array(sim.calculate("benunit_id", PE_PERIOD))

    results = {
        "household_id": hh_ids,
        "household_weight": hh_weights,
    }

    # Calculate each output variable, aggregating to household level
    for var in OUTPUT_VARIABLES:
        try:
            values = np.array(sim.calculate(var, PE_PERIOD), dtype=float)
        except Exception as exc:
            if var in OPTIONAL_VARIABLES:
                log.warning("  Variable '%s' unavailable: %s", var, exc)
                results[var] = np.zeros(n_hh)
                continue
            else:
                raise

        if len(values) == n_hh:
            # Already household-level
            results[var] = values
        elif len(values) == len(benunit_ids):
            # Benunit-level — 1:1 with household, use directly
            results[var] = values
        elif len(values) == len(person_hh_ids):
            # Person-level — sum within household
            hh_totals = np.zeros(n_hh)
            np.add.at(hh_totals, person_hh_ids.astype(int), values)
            results[var] = hh_totals
        else:
            log.warning(
                "  Variable '%s' has unexpected length %d (hh=%d, persons=%d) — padding",
                var, len(values), n_hh, len(person_hh_ids),
            )
            results[var] = np.zeros(n_hh)

    log.info("  Calculated %d variables in %.1fs", len(OUTPUT_VARIABLES), time.time() - t0)

    # Zero out UC component variables for non-recipients.
    uc_total = results.get("universal_credit", np.zeros(n_hh))
    non_recipient = uc_total <= 0
    for comp in ("uc_standard_allowance", "uc_child_element",
                 "uc_housing_costs_element"):
        if comp in results:
            results[comp] = np.where(non_recipient, 0.0, results[comp])

    return pd.DataFrame(results)

def _compute_aggregates(df: pd.DataFrame, label: str = "baseline") -> pd.DataFrame:
    """Compute weighted national aggregates from household-level results.

    FRS weights are household-level gross4 ÷ BUs per household. Sum ≈ 22M (working-age) or 28.6M (full population).
    value × weight gives total in £; we convert to £ billions.
    """
    total_weight = df["household_weight"].sum()
    agg = {"scenario": label, "total_bu_weighted": total_weight}

    numeric_vars = [
        v for v in OUTPUT_VARIABLES
        if v in df.columns and pd.api.types.is_numeric_dtype(df[v])
    ]

    for var in numeric_vars:
        total = (df[var] * df["household_weight"]).sum()
        if var in RATE_VARIABLES:
            agg[f"{var}_mean"] = total / total_weight if total_weight > 0 else 0.0
        else:
            agg[f"{var}_bn"] = total / 1e9
            agg[f"{var}_avg"] = total / total_weight if total_weight > 0 else 0.0

    return pd.DataFrame([agg])

def run_baseline() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run the full baseline and return (detail, aggregates)."""
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)

    dataset = _load_dataset()
    detail = _run_simulation(dataset)

    # Merge household type + working-age flag from ID mapping
    id_map_path = DATA_INTERMEDIATE / "pe_id_mapping.parquet"
    if id_map_path.exists():
        id_map = pd.read_parquet(id_map_path)
        id_map["household_id"] = id_map["pe_household_id"].astype(detail["household_id"].dtype)
        merge_cols = ["household_id", "household_type", "num_adults", "num_children"]
        if "is_working_age" in id_map.columns:
            merge_cols.append("is_working_age")
        detail = detail.merge(
            id_map[merge_cols],
            on="household_id",
            how="left",
        )
        log.info(
            "Household types:\n%s",
            detail["household_type"].value_counts().to_string(),
        )
        if "is_working_age" in detail.columns:
            n_wa = detail["is_working_age"].sum()
            n_pen = len(detail) - n_wa
            log.info("Working-age BUs: %s  |  Pensioner-only: %s", f"{n_wa:,}", f"{n_pen:,}")

    # Save full detail (all BUs including pensioners)
    detail_path = DATA_OUTPUT / "frs_baseline_results.parquet"
    detail.to_parquet(detail_path, index=False)
    log.info("Detail saved to %s (%s rows)", detail_path, f"{len(detail):,}")

    # Aggregates — working-age only (for comparability with transmission model)
    if "is_working_age" in detail.columns:
        detail_wa = detail[detail["is_working_age"] == True]
        log.info("Computing aggregates for working-age BUs only (%s rows)", f"{len(detail_wa):,}")
    else:
        detail_wa = detail
        log.warning("is_working_age not available — using all BUs for aggregates")
    agg = _compute_aggregates(detail_wa)
    agg_path = DATA_OUTPUT / "frs_baseline_aggregates.parquet"
    agg.to_parquet(agg_path, index=False)
    log.info("Aggregates saved to %s", agg_path)

    # Print summary
    log.info("\n%s", "=" * 70)
    log.info("BASELINE AGGREGATES (£ billions, annual)")
    log.info("%s", "=" * 70)
    display_cols_bn = [c for c in agg.columns if c.endswith("_bn")]
    for col in display_cols_bn:
        log.info("  %-40s  £%.2f bn", col.replace("_bn", ""), agg[col].iloc[0])

    display_cols_mean = [c for c in agg.columns if c.endswith("_mean")]
    for col in display_cols_mean:
        log.info("  %-40s  %.3f", col.replace("_mean", ""), agg[col].iloc[0])

    return detail, agg

if __name__ == "__main__":
    run_baseline()
