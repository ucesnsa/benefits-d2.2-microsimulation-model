# LICENCE: AGPL-3.0, because this file imports policyengine-uk, which together with
# policyengine-core is published under the GNU Affero General Public License v3. That
# licence is reciprocal, so it reaches this file through the import. The licence is
# confirmed from both packages' installed metadata rather than from the project's own
# notes. The text is in uk/model/Code_FRS_23_24/LICENSE.

"""
Shared simulation runner — calculates PE output variables and
aggregates to the household level.

Used by steps 04–07 to avoid duplicating the entity-level
aggregation logic.
"""

import logging
import time

import numpy as np
import pandas as pd

from Code_FRS_23_24.utils.frs_config import (
    OPTIONAL_VARIABLES,
    OUTPUT_VARIABLES,
    PE_PERIOD,
)

log = logging.getLogger(__name__)


def run_simulation(
    dataset,
    scenario=None,
    scenario_label: str = "",
) -> pd.DataFrame:
    """Run a PE Simulation and return household-level results.

    Variables live at different entity levels (person / benunit /
    household).  Person- and benunit-level values are summed within
    each household to produce a single household-level row.

    Args:
        dataset: UKSingleYearDataset (or compatible).
        scenario: Optional ``Scenario`` object (for reforms).
        scenario_label: Value written to the ``scenario`` column.

    Returns:
        DataFrame with one row per household.
    """
    from policyengine_uk import Simulation

    log.info("Building simulation (period=%s)...", PE_PERIOD)
    t0 = time.time()

    sim = Simulation(dataset=dataset)

    if scenario is not None:
        if scenario.parameter_changes:
            for path, value in scenario.parameter_changes.items():
                sim.tax_benefit_system.parameters.get_child(path).update(value=value)
        if scenario.simulation_modifier is not None:
            scenario.simulation_modifier(sim)

    log.info("  Simulation built in %.1fs", time.time() - t0)

    # Entity dimensions
    hh_ids = np.array(sim.calculate("household_id", PE_PERIOD))
    hh_weights = np.array(sim.calculate("household_weight", PE_PERIOD))
    n_hh = len(hh_ids)

    # Person→household mapping for aggregation
    person_hh_ids = np.array(sim.calculate("person_household_id", PE_PERIOD))
    benunit_ids = np.array(sim.calculate("benunit_id", PE_PERIOD))

    results: dict = {
        "household_id": hh_ids,
        "household_weight": hh_weights,
    }
    if scenario_label:
        results["scenario"] = scenario_label

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
            results[var] = values
        elif len(values) == len(benunit_ids):
            # Benunit-level — 1:1 with household in our data
            results[var] = values
        elif len(values) == len(person_hh_ids):
            # Person-level — sum within household
            hh_totals = np.zeros(n_hh)
            np.add.at(hh_totals, person_hh_ids.astype(int), values)
            results[var] = hh_totals
        else:
            log.warning(
                "  Variable '%s': unexpected length %d — padding with zeros",
                var, len(values),
            )
            results[var] = np.zeros(n_hh)

    log.info(
        "  Calculated %d variables in %.1fs",
        len(OUTPUT_VARIABLES),
        time.time() - t0,
    )

    # Zero out UC component variables for non-recipients.
    # PE computes these as gross entitlements for ALL BUs; mask to
    # actual recipients so weighted aggregates reflect real spending.
    uc_total = results.get("universal_credit", np.zeros(n_hh))
    non_recipient = uc_total <= 0
    for comp in ("uc_standard_allowance", "uc_child_element",
                 "uc_housing_costs_element"):
        if comp in results:
            results[comp] = np.where(non_recipient, 0.0, results[comp])

    return pd.DataFrame(results)
