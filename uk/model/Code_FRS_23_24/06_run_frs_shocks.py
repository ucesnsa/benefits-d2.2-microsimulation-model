# LICENCE: AGPL-3.0, because this file imports policyengine-uk, which together with
# policyengine-core is published under the GNU Affero General Public License v3. That
# licence is reciprocal, so it reaches this file through the import. The licence is
# confirmed from both packages' installed metadata rather than from the project's own
# notes. The text is in uk/model/Code_FRS_23_24/LICENSE.

"""
06 — Run employment shock scenarios on FRS 2023-24 dataset.

Modifies ``employment_income`` values in the person table for a
fraction of employed households, builds a new ``UKSingleYearDataset``,
and runs the simulation.

Shock logic
-----------
1.  Identify employed persons (employment_income > 0).
2.  Group by household; compute employed-BU weight.
3.  Select BUs totalling ``shock_pp × total_employed_weight``
    (deterministic, seeded).
4.  For selected BUs:
    - Single employed → zero their income.
    - Couple both employed → zero the higher earner.
    - Couple one employed → zero that earner.
5.  Build new ``UKSingleYearDataset`` with modified person table.
6.  Run simulation.

Input
-----
- data/frs_2023_24/intermediate/pe_persons.parquet
- data/frs_2023_24/intermediate/pe_benunits.parquet
- data/frs_2023_24/intermediate/pe_households.parquet

Output
------
- data/frs_2023_24/output/frs_shock_results.parquet
- data/frs_2023_24/output/frs_shock_transmission.xlsx

Usage
-----
    python model/Code_FRS_23_24/06_run_frs_shocks.py
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

# GDP shock scenarios to run
SHOCK_SCENARIOS = {
    "gdp_minus_1": {"gdp_change_pct": -1.0},
    "gdp_minus_3": {"gdp_change_pct": -3.0},
    "gdp_minus_5": {"gdp_change_pct": -5.0},
    "shock_3pp": {"shock_pp": 0.03},
    "shock_5pp": {"shock_pp": 0.05},
}

SEED = 42


def _apply_shock_to_persons(
    person_df: pd.DataFrame,
    household_df: pd.DataFrame,
    shock_pp: float,
    seed: int = SEED,
) -> pd.DataFrame:
    """Apply an employment shock to a copy of the person DataFrame.

    Zeroes ``employment_income`` for a fraction of employed households
    proportional to ``shock_pp``.

    Args:
        person_df: Original person table.
        household_df: Household table (for weights).
        shock_pp: Fraction of employed BU weight to make unemployed.
        seed: Random seed for deterministic selection.

    Returns:
        Modified copy of person_df.
    """
    persons = person_df.copy()

    # Identify employed persons
    employed_mask = persons["employment_income"] > 0
    if employed_mask.sum() == 0:
        log.warning("No employed persons found — shock has no effect")
        return persons

    # Map household weights onto persons
    hh_weights = household_df.set_index("household_id")["household_weight"]
    persons["_hh_weight"] = persons["person_household_id"].map(hh_weights).fillna(0)

    # Identify employed BUs (at least one employed person)
    bu_employed = (
        persons[employed_mask]
        .groupby("person_benunit_id")
        .agg(
            num_employed=("person_id", "count"),
            max_income=("employment_income", "max"),
            hh_weight=("_hh_weight", "first"),
        )
    )

    total_employed_weight = bu_employed["hh_weight"].sum()
    target_weight = shock_pp * total_employed_weight

    log.info(
        "  Shock: pp=%.3f  employed BU weight=%.0f  target weight=%.0f",
        shock_pp,
        total_employed_weight,
        target_weight,
    )

    # Deterministic selection: sort by household_id, accumulate weight

    bu_employed = bu_employed.sample(frac=1, random_state=seed)  # shuffle
    bu_employed["cum_weight"] = bu_employed["hh_weight"].cumsum()
    selected_bus = bu_employed[bu_employed["cum_weight"] <= target_weight].index

    log.info(
        "  Selected %s BUs (weight %.0f) for unemployment",
        f"{len(selected_bus):,}",
        bu_employed.loc[selected_bus, "hh_weight"].sum(),
    )

    # Apply the shock
    for bu_id in selected_bus:
        bu_persons = persons[
            (persons["person_benunit_id"] == bu_id)
            & (persons["employment_income"] > 0)
        ]

        if len(bu_persons) == 0:
            continue

        if len(bu_persons) == 1:
            # Single employed → zero income
            persons.loc[bu_persons.index, "employment_income"] = 0.0
        else:
            # Multiple employed → zero the highest earner
            highest_idx = bu_persons["employment_income"].idxmax()
            persons.loc[highest_idx, "employment_income"] = 0.0

    persons.drop(columns=["_hh_weight"], inplace=True)
    return persons


def _run_shocked_simulation(
    person_df: pd.DataFrame,
    benunit_df: pd.DataFrame,
    household_df: pd.DataFrame,
    scenario_name: str,
    scenario_obj=None,
) -> pd.DataFrame:
    """Build a new dataset from modified persons and run simulation."""
    from policyengine_uk.data.dataset_schema import UKSingleYearDataset

    from Code_FRS_23_24.utils.pe_runner import run_simulation

    dataset = UKSingleYearDataset(
        person=person_df,
        benunit=benunit_df,
        household=household_df,
        fiscal_year=FRS_FISCAL_YEAR,
    )

    return run_simulation(dataset, scenario=scenario_obj, scenario_label=scenario_name)


def run_shocks() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run all shock scenarios and return (detail, transmission reports).

    Returns:
        (stacked_results, transmission_summary)
    """
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)

    # Import shock transmission from reference implementation
    add_ref_impl_to_path()
    from shock_transmission import gdp_shock_to_unemployment, full_fiscal_impact

    # Load base tables
    person_df = pd.read_parquet(DATA_INTERMEDIATE / "pe_persons.parquet")
    benunit_df = pd.read_parquet(DATA_INTERMEDIATE / "pe_benunits.parquet")
    household_df = pd.read_parquet(DATA_INTERMEDIATE / "pe_households.parquet")

    all_results = []
    transmission_rows = []

    for name, config in SHOCK_SCENARIOS.items():
        log.info("\n%s\n  Scenario: %s\n%s", "=" * 60, name, "=" * 60)

        # Resolve shock_pp
        if "gdp_change_pct" in config:
            gdp = config["gdp_change_pct"]
            macro = gdp_shock_to_unemployment(gdp)
            shock_pp = macro["unemployment_change_pp"] / 100
            transmission = full_fiscal_impact(gdp)
            log.info(
                "  GDP %.1f%% → unemployment +%.2fpp → %sk newly unemployed",
                gdp,
                macro["unemployment_change_pp"],
                f"{macro['newly_unemployed_thousands']:.0f}",
            )
        else:
            shock_pp = config["shock_pp"]
            transmission = None

        # Apply shock to person table
        shocked_persons = _apply_shock_to_persons(
            person_df, household_df, shock_pp
        )

        # Run simulation
        t0 = time.time()
        results = _run_shocked_simulation(
            shocked_persons, benunit_df, household_df, name
        )
        elapsed = time.time() - t0
        log.info("  Simulation completed in %.1fs", elapsed)

        all_results.append(results)

        # Transmission report
        if transmission is not None:
            t_row = {"scenario": name, "gdp_change_pct": config["gdp_change_pct"]}
            t_row.update({f"macro_{k}": v for k, v in transmission["macro"].items()})
            t_row.update({f"benefits_{k}": v for k, v in transmission["benefits"].items()})
            t_row.update({
                f"fiscal_{k}": v
                for k, v in transmission["fiscal"].items()
                if not isinstance(v, dict)
            })
            transmission_rows.append(t_row)

    # Combine and save
    stacked = pd.concat(all_results, ignore_index=True)
    stacked_path = DATA_OUTPUT / "frs_shock_results.parquet"
    stacked.to_parquet(stacked_path, index=False)
    log.info("Shock results saved to %s", stacked_path)

    transmission_df = pd.DataFrame(transmission_rows) if transmission_rows else pd.DataFrame()
    if not transmission_df.empty:
        trans_path = DATA_OUTPUT / "frs_shock_transmission.xlsx"
        transmission_df.to_excel(trans_path, index=False)
        log.info("Transmission analysis saved to %s", trans_path)

    return stacked, transmission_df


if __name__ == "__main__":
    run_shocks()
