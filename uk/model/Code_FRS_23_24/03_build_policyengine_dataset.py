# LICENCE: AGPL-3.0, because this file imports policyengine-uk, which together with
# policyengine-core is published under the GNU Affero General Public License v3. That
# licence is reciprocal, so it reaches this file through the import. The licence is
# confirmed from both packages' installed metadata rather than from the project's own
# notes. The text is in uk/model/Code_FRS_23_24/LICENSE.

"""
03 — Build PolicyEngine UK dataset from the FRS 2023-24 benefit-unit table.

Transforms the BU-level parquet into PolicyEngine's three-table format
(person / benunit / household) and writes a ``UKSingleYearDataset``
HDF5 file ready for ``Simulation(dataset=...)``.

Each benefit unit is treated as a *separate household* for PE purposes
(1:1 BU–household mapping).  Adults and children within each BU are
exploded into individual person rows.

Input
-----
- data/frs_2023_24/intermediate/frs_benefit_units.parquet

Output
------
- data/frs_2023_24/intermediate/pe_dataset.h5            (UKSingleYearDataset)
- data/frs_2023_24/intermediate/pe_persons.parquet        (person table)
- data/frs_2023_24/intermediate/pe_benunits.parquet       (benunit table)
- data/frs_2023_24/intermediate/pe_households.parquet     (household table)
- data/frs_2023_24/intermediate/pe_id_mapping.parquet     (BU key ↔ PE ids)

Usage
-----
    python model/Code_FRS_23_24/03_build_policyengine_dataset.py
"""

import logging
import os
import sys
from pathlib import Path
from typing import List

_DEMO_MODE = bool(os.getenv("FRS_DEMO_MODE"))

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Code_FRS_23_24.utils.frs_config import (
    CT_ANNUAL_BY_BAND,
    CT_BAND_MAP,
    DATA_INTERMEDIATE,
    FRS_FISCAL_YEAR,
    GENDER_MAP,
    REGION_MAP,
    TENURE_MAP,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)

WEEKS_PER_YEAR: float = 52.0

# ------------------------------------------------------------------
# Toggle — must match setting in 02_build_benefit_unit_table.py
# ------------------------------------------------------------------
WORKING_AGE_ONLY = True   # Restrict to working-age population
# ------------------------------------------------------------------
# ======================================================================
# Person-row explosion
# ======================================================================


def _safe_list(val: object) -> list:
    """Ensure *val* is a list (handles numpy arrays and scalars)."""
    if isinstance(val, (list, np.ndarray)):
        return list(val)
    return []

def _explode_persons(bu: pd.DataFrame) -> pd.DataFrame:
    """Explode each BU row into individual person rows.

    Adults come from the list columns (ages, sexes, employment_incomes,
    etc.).  Children come from child_ages / child_sexes.

    Returns a DataFrame with one row per person and columns matching
    PolicyEngine variable names.
    """
    persons: List[dict] = []
    person_id = 0

    for idx, row in bu.iterrows():
        bu_id = int(idx)

        # --- Adults ---
        ages = _safe_list(row["ages"])
        sexes = _safe_list(row["sexes"])
        emp_incomes = _safe_list(row["employment_incomes"])
        se_incomes = _safe_list(row["self_employment_incomes"])
        occ_pensions = _safe_list(row["occupational_pensions"])
        savings = _safe_list(row["savings_interests"])
        inv_incomes = _safe_list(row.get("investment_incomes", []))
        dividends = _safe_list(row.get("dividend_incomes", []))
        hours = _safe_list(row.get("hours_worked", []))

        # Childcare cost (weekly, BU-level — split equally across children)
        weekly_cc = float(row.get("weekly_childcare_cost", 0.0))
        n_children = len(_safe_list(row.get("child_ages", [])))
        annual_cc_per_child = (weekly_cc * WEEKS_PER_YEAR / n_children) if n_children > 0 else 0.0

        # Employment-relevant benefits (per person, weekly)
        housing_benefit = _safe_list(row.get("housing_benefit", []))
        jsa_contrib_wk = _safe_list(row.get("jsa_contrib", []))
        jsa_income_wk = _safe_list(row.get("jsa_income", []))

        # empstati per-person — FRS adult employment status (used for ESA/JSA proxies).
        # empstati mapping (from policyengine-uk-data `create_frs`):
        #   10 = LONG_TERM_DISABLED, 11 = SHORT_TERM_DISABLED, 6 = UNEMPLOYED
        empstatis = _safe_list(row.get("empstatis", []))
        maritals = _safe_list(row.get("maritals", []))
        hrpids = _safe_list(row.get("hrpids", []))
        upersons = _safe_list(row.get("upersons", []))
        bu_has_children = int(row.get("num_children", 0)) > 0
        educfts = _safe_list(row.get("educfts", []))
        typeed2s = _safe_list(row.get("typeed2s", []))
        educquals = _safe_list(row.get("educquals", []))
        maintenance_in_wk = _safe_list(row.get("maintenance_incomes", []))
        maintenance_out_wk = _safe_list(row.get("maintenance_expenses", []))

        # Phase 2 — disability / carer / pensioner / tax credit benefits (per person, weekly)
        state_pension_wk = _safe_list(row.get("state_pension", []))
        pension_credit_wk = _safe_list(row.get("pension_credit", []))
        attendance_allowance_wk = _safe_list(row.get("attendance_allowance", []))
        carers_allowance_wk = _safe_list(row.get("carers_allowance", []))
        dla_sc_wk = _safe_list(row.get("dla_sc", []))
        dla_m_wk = _safe_list(row.get("dla_m", []))
        pip_dl_wk = _safe_list(row.get("pip_dl", []))
        pip_m_wk = _safe_list(row.get("pip_m", []))
        esa_contrib_wk = _safe_list(row.get("esa_contrib", []))
        esa_income_wk = _safe_list(row.get("esa_income", []))
        income_support_wk = _safe_list(row.get("income_support", []))
        wtc_wk = _safe_list(row.get("working_tax_credit", []))
        ctc_wk = _safe_list(row.get("child_tax_credit", []))

        def _annual(series, i):
            return float(series[i]) * WEEKS_PER_YEAR if i < len(series) else 0.0

        # State Pension age (simplified — 66 in 2023-24 for everyone)
        STATE_PENSION_AGE = 66

        # --- Phase 3 categorical mappers (per policyengine-uk-data) ---
        # FRS marital code → PE marital_status category
        MARITAL_MAP = {
            1: "MARRIED",       # married / civil partnership
            2: "SINGLE",        # cohabiting
            3: "SINGLE",        # single, never married
            4: "WIDOWED",
            5: "SEPARATED",
            6: "DIVORCED",
        }
        # FRS empstati → PE employment_status category (reference EMPLOYMENTS list)
        EMPLOYMENT_MAP = {
            1: "CHILD",
            2: "FT_EMPLOYED",
            3: "PT_EMPLOYED",
            4: "FT_SELF_EMPLOYED",
            5: "PT_SELF_EMPLOYED",
            6: "UNEMPLOYED",
            7: "RETIRED",
            8: "STUDENT",
            9: "CARER",
            10: "LONG_TERM_DISABLED",
            11: "SHORT_TERM_DISABLED",
        }
        # EDUCQUAL → highest_education (simplified mapping)
        HIGHEST_EDU_MAP = {
            1: "TERTIARY", 2: "TERTIARY",          # degree
            3: "UPPER_SECONDARY", 4: "UPPER_SECONDARY",
            5: "LOWER_SECONDARY", 6: "LOWER_SECONDARY",
            7: "LOWER_SECONDARY", 8: "NOT_IN_EDUCATION",
        }

        def _current_education(fted, typeed2, age):
            """Approx mapping of FTED + TYPEED2 → PE current_education category."""
            if fted in (2, -1, 0):
                return "NOT_IN_EDUCATION"
            if typeed2 == 1:
                return "PRE_PRIMARY"
            if typeed2 in (2, 4) or (typeed2 in (3, 8) and age < 11):
                return "PRIMARY"
            if typeed2 in (5, 6) or (typeed2 in (3, 8) and age <= 16):
                return "LOWER_SECONDARY"
            if typeed2 == 7 or (typeed2 in (3, 8) and age > 16):
                return "UPPER_SECONDARY"
            if typeed2 in (7, 8) and age >= 19:
                return "POST_SECONDARY"
            return "NOT_IN_EDUCATION"

        # Household-level CTR amount — attach to head of BU (i==0) only.
        weekly_ctr = float(row.get("weekly_council_tax_rebate", 0.0))

        n_adults = len(ages)
        for i in range(n_adults):
            a_age = float(ages[i]) if i < len(ages) else 40.0
            a_hours_annual = _annual(hours, i)
            a_empstati = int(empstatis[i]) if i < len(empstatis) else 0

            # Phase 2b — disability / JSA proxies
            reported = a_empstati > 0
            is_health_related = a_empstati in (10, 11)    # 10=long-term, 11=short-term disabled
            is_long_term_disabled = a_empstati == 10
            in_wa_range = (a_age >= 16) and (a_age < STATE_PENSION_AGE)

            esa_health_proxy = reported and in_wa_range and is_health_related
            esa_support_proxy = esa_health_proxy and is_long_term_disabled and a_hours_annual <= 0

            # Disability flag for UC LCW/LCWRA, disabled child element, etc.
            # Derived from reported DLA/PIP claims (per policyengine-uk-data).
            dla_sc_ann = _annual(_safe_list(row.get("dla_sc", [])), i)
            dla_m_ann  = _annual(_safe_list(row.get("dla_m", [])), i)
            pip_dl_ann = _annual(_safe_list(row.get("pip_dl", [])), i)
            pip_m_ann  = _annual(_safe_list(row.get("pip_m", [])), i)
            is_disabled = (dla_sc_ann + dla_m_ann + pip_dl_ann + pip_m_ann) > 0

            # Phase 3 — categorical per-adult fields
            a_marital = int(maritals[i]) if i < len(maritals) else 3
            a_educft = int(educfts[i]) if i < len(educfts) else 2
            a_typeed2 = int(typeed2s[i]) if i < len(typeed2s) else 0
            a_educqual = int(educquals[i]) if i < len(educquals) else 8
            a_is_hh_head = (int(hrpids[i]) == 1) if i < len(hrpids) else (i == 0)
            a_is_bu_head = (int(upersons[i]) == 1) if i < len(upersons) else (i == 0)

            persons.append({
                "person_id": person_id,
                "person_benunit_id": bu_id,
                "person_household_id": bu_id,
                "age": a_age,
                "gender": GENDER_MAP.get(sexes[i], "MALE") if i < len(sexes) else "MALE",
                # Phase 3 — demographics (used by PE for various eligibility rules)
                "marital_status": MARITAL_MAP.get(a_marital, "SINGLE"),
                "employment_status": EMPLOYMENT_MAP.get(a_empstati, "UNEMPLOYED"),
                # Phase 3b — head-of-household / parent flags
                "is_household_head": a_is_hh_head,
                "is_benunit_head": a_is_bu_head,
                "is_parent": bu_has_children,   # any adult in a BU with dependent children
                "current_education": _current_education(a_educft, a_typeed2, a_age),
                "highest_education": HIGHEST_EDU_MAP.get(a_educqual, "NOT_IN_EDUCATION"),
                # Phase 3 — maintenance income / expenses
                "maintenance_income": _annual(maintenance_in_wk, i),
                "maintenance_expenses": _annual(maintenance_out_wk, i),
                # Phase 3 — Council Tax Reduction (attached to BU head only)
                "council_tax_benefit_reported": (weekly_ctr * WEEKS_PER_YEAR) if i == 0 else 0.0,
                # Phase 2b — disability flags (for UC LCW/LCWRA element, disabled child element)
                "esa_health_condition_proxy": bool(esa_health_proxy),
                "esa_support_group_proxy": bool(esa_support_proxy),
                "is_disabled_for_benefits": bool(is_disabled),
                # Income — weekly → annual
                "employment_income": _annual(emp_incomes, i),
                "self_employment_income": _annual(se_incomes, i),
                "private_pension_income": _annual(occ_pensions, i),
                "savings_interest_income": _annual(savings, i),
                "property_income": _annual(inv_incomes, i),
                "dividend_income": _annual(dividends, i),
                # Hours worked — FRS tothours is weekly; PE hours_worked is annual
                "hours_worked": _annual(hours, i),
                "weekly_hours": float(hours[i]) if i < len(hours) else 0.0,
                "childcare_expenses": 0.0,
                # Reported benefits — weekly → annual
                "housing_benefit_reported": _annual(housing_benefit, i),
                "jsa_contrib_reported": _annual(jsa_contrib_wk, i),
                "jsa_income_reported": _annual(jsa_income_wk, i),
                # Phase 2 — reported benefits passed directly to PolicyEngine
                "state_pension_reported": _annual(state_pension_wk, i),
                "pension_credit_reported": _annual(pension_credit_wk, i),
                "attendance_allowance_reported": _annual(attendance_allowance_wk, i),
                "carers_allowance_reported": _annual(carers_allowance_wk, i),
                "dla_sc_reported": _annual(dla_sc_wk, i),
                "dla_m_reported": _annual(dla_m_wk, i),
                "pip_dl_reported": _annual(pip_dl_wk, i),
                "pip_m_reported": _annual(pip_m_wk, i),
                "esa_contrib_reported": _annual(esa_contrib_wk, i),
                "esa_income_reported": _annual(esa_income_wk, i),
                "income_support_reported": _annual(income_support_wk, i),
                "working_tax_credit_reported": _annual(wtc_wk, i),
                "child_tax_credit_reported": _annual(ctc_wk, i),
            })
            person_id += 1

        # --- Children ---
        child_ages = _safe_list(row.get("child_ages", []))
        child_sexes = _safe_list(row.get("child_sexes", []))

        # Children in our pipeline don't carry disability benefit receipts individually.
        # Known limitation — FRS child table doesn't break benefits out per child.
        for j in range(len(child_ages)):
            c_age = float(child_ages[j])
            persons.append({
                "person_id": person_id,
                "person_benunit_id": bu_id,
                "person_household_id": bu_id,
                "age": c_age,
                "gender": GENDER_MAP.get(child_sexes[j], "MALE") if j < len(child_sexes) else "MALE",
                "marital_status": "SINGLE",
                "employment_status": "CHILD",
                "current_education": "PRIMARY" if c_age < 11 else ("LOWER_SECONDARY" if c_age <= 16 else "NOT_IN_EDUCATION"),
                "highest_education": "NOT_IN_EDUCATION",
                "is_household_head": False,
                "is_benunit_head": False,
                "is_parent": False,
                "maintenance_income": 0.0,
                "maintenance_expenses": 0.0,
                "council_tax_benefit_reported": 0.0,
                "esa_health_condition_proxy": False,
                "esa_support_group_proxy": False,
                "is_disabled_for_benefits": False,
                "employment_income": 0.0,
                "self_employment_income": 0.0,
                "private_pension_income": 0.0,
                "savings_interest_income": 0.0,
                "property_income": 0.0,
                "dividend_income": 0.0,
                "hours_worked": 0.0,
                "weekly_hours": 0.0,
                "childcare_expenses": annual_cc_per_child,
                "housing_benefit_reported": 0.0,
                "jsa_contrib_reported": 0.0,
                "jsa_income_reported": 0.0,
                "state_pension_reported": 0.0,
                "pension_credit_reported": 0.0,
                "attendance_allowance_reported": 0.0,
                "carers_allowance_reported": 0.0,
                "dla_sc_reported": 0.0,
                "dla_m_reported": 0.0,
                "pip_dl_reported": 0.0,
                "pip_m_reported": 0.0,
                "esa_contrib_reported": 0.0,
                "esa_income_reported": 0.0,
                "income_support_reported": 0.0,
                "working_tax_credit_reported": 0.0,
                "child_tax_credit_reported": 0.0,
            })
            person_id += 1

    return pd.DataFrame(persons)

# ======================================================================
# Household-level table
# ======================================================================


def _build_household_table(bu: pd.DataFrame) -> pd.DataFrame:
    """Build the household-level DataFrame from the BU table.

    Each benefit unit maps 1:1 to a PE household.
    """
    rows = []
    for idx, row in bu.iterrows():
        bu_id = int(idx)

        # Map FRS codes to PE enum keys with fallbacks
        tenure_code = int(row.get("tenure", 5))
        tenure_str = TENURE_MAP.get(tenure_code, "RENT_PRIVATELY")

        region_code = int(row.get("gvtregn", 112000007))
        region_str = REGION_MAP.get(region_code, "LONDON")

        ctband_code = int(row.get("ctband", 4))
        ctband_str = CT_BAND_MAP.get(ctband_code, "D")

        weekly_rent = float(row.get("weekly_rent", 0.0))
        # Phase 2 — rent cap removed. PolicyEngine applies LHA / social-rent
        # caps internally based on region and BU composition, so truncating
        # the input understates UC housing element for high-rent (London) BUs.
        annual_rent = max(weekly_rent * WEEKS_PER_YEAR, 0.0)

        # Phase 3 — mortgage interest/capital split (PE uses both for HBAI AHC income)
        weekly_mortgage_total = float(row.get("weekly_mortgage", 0.0))
        weekly_mortgage_interest = float(row.get("weekly_mortgage_interest", 0.0))
        weekly_mortgage_capital = max(weekly_mortgage_total - weekly_mortgage_interest, 0.0)
        annual_mortgage_interest = weekly_mortgage_interest * WEEKS_PER_YEAR
        annual_mortgage_capital = weekly_mortgage_capital * WEEKS_PER_YEAR

        # Estimate annual council tax from band
        annual_ct = CT_ANNUAL_BY_BAND.get(ctband_str, CT_ANNUAL_BY_BAND["D"])

        rows.append({
            "household_id": bu_id,
            "household_weight": float(row.get("hh_weight", 1.0)),
            "rent": annual_rent,
            "mortgage_interest_repayment": annual_mortgage_interest,
            "mortgage_capital_repayment": annual_mortgage_capital,
            "council_tax": annual_ct,
            "council_tax_band": ctband_str,
            "tenure_type": tenure_str,
            "region": region_str,
        })

    return pd.DataFrame(rows)


# ======================================================================
# Main
# ======================================================================


def build_policyengine_dataset() -> None:
    """Build the PE dataset and save to HDF5 + parquets."""
    from policyengine_uk.data.dataset_schema import UKSingleYearDataset

    bu_path = DATA_INTERMEDIATE / "frs_benefit_units.parquet"
    log.info("Loading benefit-unit table from %s ...", bu_path)
    bu = pd.read_parquet(bu_path).reset_index(drop=True)
    log.info("  BU rows: %s", f"{len(bu):,}")

    # --- Person table ---
    log.info("Exploding persons...")
    person_df = _explode_persons(bu)
    log.info("  Person rows: %s", f"{len(person_df):,}")

    # --- Benunit table ---
    benunit_df = pd.DataFrame({
        "benunit_id": list(range(len(bu))),
    })
    log.info("  Benunit rows: %s", f"{len(benunit_df):,}")

    # --- Household table ---
    log.info("Building household table...")
    household_df = _build_household_table(bu)
    log.info("  Household rows: %s", f"{len(household_df):,}")

    # --- Validation ---
    weight_sum = household_df["household_weight"].sum()
    log.info("  Total weight: %s", f"{weight_sum:,.0f}")
    if not _DEMO_MODE:
        assert len(person_df) > 15_000, f"Too few persons: {len(person_df)}"
    assert len(household_df) == len(bu), "Household count must equal BU count"
    if not _DEMO_MODE:
        if WORKING_AGE_ONLY:
            assert weight_sum > 18_000_000, f"Weight sum too low: {weight_sum:,.0f}"
        else:
            assert weight_sum > 25_000_000, f"Weight sum too low: {weight_sum:,.0f}"

    # Ensure no negative incomes from data issues
    income_cols = [
        "employment_income", "self_employment_income",
        "private_pension_income", "savings_interest_income",
        "property_income",
    ]
    for col in income_cols:
        neg_count = (person_df[col] < 0).sum()
        if neg_count > 0:
            log.warning(
                "  %s negative values in %s — clipping to zero",
                neg_count, col,
            )
            person_df[col] = person_df[col].clip(lower=0)

    # --- Save individual parquets for inspection ---
    person_df.to_parquet(DATA_INTERMEDIATE / "pe_persons.parquet", index=False)
    benunit_df.to_parquet(DATA_INTERMEDIATE / "pe_benunits.parquet", index=False)
    household_df.to_parquet(DATA_INTERMEDIATE / "pe_households.parquet", index=False)

    # --- ID mapping (for traceability) ---
    id_map = bu[["sernum", "benunit"]].copy()
    id_map["pe_benunit_id"] = list(range(len(bu)))
    id_map["pe_household_id"] = list(range(len(bu)))

    # Derive household type from num_adults and num_children
    num_adults = bu["num_adults"].values
    num_children = bu["num_children"].values
    hh_types = []
    for na, nc in zip(num_adults, num_children):
        if na == 1 and nc == 0:
            hh_types.append("Single, no children")
        elif na == 1 and nc > 0:
            hh_types.append("Single, with children")
        elif na >= 2 and nc == 0:
            hh_types.append("Couple, no children")
        else:
            hh_types.append("Couple with children")
    id_map["household_type"] = hh_types
    id_map["num_adults"] = num_adults
    id_map["num_children"] = num_children

    # Region (RWI join key). Re-derived from FRS gvtregn through the same
    # REGION_MAP the PE household dataset uses (region_str above), so the id-map
    # region is identical to the engine's; missing/unknown codes fall back to
    # LONDON, matching that builder. Stored as the PE region enum key.
    id_map["region"] = (
        bu["gvtregn"].fillna(112000007).astype(int)
        .map(REGION_MAP).fillna("LONDON").to_numpy()
    )

    # Working-age flag: True if at least one adult aged 18-64
    # Derived from person_df (has age per person, linked by person_household_id)
    adult_ages = person_df[person_df["age"] >= 18].groupby("person_household_id")["age"].min()
    is_wa = (adult_ages < 65).reindex(id_map["pe_household_id"]).fillna(False).values
    id_map["is_working_age"] = is_wa

    id_map.to_parquet(DATA_INTERMEDIATE / "pe_id_mapping.parquet", index=False)

    n_wa = is_wa.sum()
    n_pen = len(is_wa) - n_wa
    log.info(
        "\nHousehold types in ID mapping:\n%s\n\n"
        "Working-age BUs: %s  |  Pensioner-only BUs: %s",
        id_map["household_type"].value_counts().to_string(),
        f"{n_wa:,}", f"{n_pen:,}",
    )

    # --- Build UKSingleYearDataset ---
    log.info("Constructing UKSingleYearDataset (fiscal_year=%s)...", FRS_FISCAL_YEAR)
    dataset = UKSingleYearDataset(
        person=person_df,
        benunit=benunit_df,
        household=household_df,
        fiscal_year=FRS_FISCAL_YEAR,
    )

    h5_path = DATA_INTERMEDIATE / "pe_dataset.h5"
    dataset.save(str(h5_path))
    log.info("Dataset saved to %s", h5_path)

    # --- Summary ---
    log.info(
        "\nDataset summary:\n"
        "  Persons:    %s\n"
        "  Benunits:   %s\n"
        "  Households: %s\n"
        "  Weight sum: %s\n"
        "  Fiscal yr:  %s",
        f"{len(person_df):,}",
        f"{len(benunit_df):,}",
        f"{len(household_df):,}",
        f"{weight_sum:,.0f}",
        FRS_FISCAL_YEAR,
    )


if __name__ == "__main__":
    build_policyengine_dataset()
