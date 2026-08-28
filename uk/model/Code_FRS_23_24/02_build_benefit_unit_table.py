"""
02 — Build benefit-unit-level table from raw FRS 2023-24 extracts.

Joins adults, children, childcare costs, and disability/carer benefits
into a single benefit-unit (BU) table with one row per BU.  Adult-level
data is stored as lists (ages, earnings, employment statuses) ready for
person-level explosion in step 03.

Input
-----
- data/frs_2023_24/input/frs_raw_adults.parquet
- data/frs_2023_24/input/frs_raw_children.parquet
- data/frs_2023_24/input/frs_raw_childcare.parquet
- data/frs_2023_24/input/frs_raw_benefits.parquet

Output
------
- data/frs_2023_24/intermediate/frs_benefit_units.parquet

Usage
-----
    python model/Code_FRS_23_24/02_build_benefit_unit_table.py
"""

import logging
import os
import sys
from pathlib import Path

import pandas as pd

_DEMO_MODE = bool(os.getenv("FRS_DEMO_MODE"))

# ------------------------------------------------------------------
# Toggle to restrict to working-age population (JSA, UC, housing, CTR)
# ------------------------------------------------------------------
WORKING_AGE_ONLY = True    # Restrict to working-age population
WORKING_AGE_MAX = 66      # State Pension age in 2023-24
# ------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from Code_FRS_23_24.utils.frs_config import DATA_INPUT, DATA_INTERMEDIATE, REGION_NAMES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)

_REQUIRED_INPUTS = [
    DATA_INPUT / "frs_raw_adults.parquet",
    DATA_INPUT / "frs_raw_children.parquet",
    DATA_INPUT / "frs_raw_childcare.parquet",
    DATA_INPUT / "frs_raw_benefits.parquet",
]
_missing = [p for p in _REQUIRED_INPUTS if not p.exists()]
if _missing:
    log.error(
        "Missing required FRS input files in %s:\n%s\n\n"
        "FRS microdata is safeguarded by the UK Data Service (UKDS).\n"
        "Apply for access at https://ukdataservice.ac.uk, download the\n"
        "FRS 2023-24 parquet extracts, and place them in that directory.",
        DATA_INPUT,
        "\n".join(f"  {p.name}" for p in _missing),
    )
    sys.exit(1)

# Columns needing integer coercion
_INT_COLS_ADULT = [
    "sernum", "gvtregn", "benunit", "person", "age80", "sex",
    "empstat", "empstatb", "empstati", "tenure_code", "ctband",
    "marital", "educft", "typeed2", "educqual",
    "hrpid", "uperson",
]

# Income / continuous columns needing float coercion
_FLOAT_COLS_ADULT = [
    "inearns", "seincam2", "inpeninc", "inrinc", "totint",
    "burent", "rentfull", "mortpay", "mortint",   # ← added
    "careah", "tothours", "gross4", "ctrebamt",
]
_BENEFIT_COLS = [
    "housing_benefit_weekly",
    "jsa_contrib_weekly",          # Phase 3b: split from jsa_weekly
    "jsa_income_weekly",           # Phase 3b: income-based JSA
    # Phase 2 — disability / carer / pensioner / tax credits
    "state_pension_weekly",
    "pension_credit_weekly",
    "attendance_allowance_weekly",
    "carers_allowance_weekly",
    "dla_sc_weekly",
    "dla_m_weekly",
    "pip_dl_weekly",
    "pip_m_weekly",
    "esa_contrib_weekly",          # Phase 3b: split from esa_weekly
    "esa_income_weekly",           # Phase 3b: income-based ESA
    "income_support_weekly",
    "working_tax_credit_weekly",
    "child_tax_credit_weekly",
]

def build_benefit_unit_table() -> pd.DataFrame:
    """Build the benefit-unit table and write to parquet.

    Returns:
        DataFrame with one row per benefit unit.
    """
    log.info("Loading raw parquets...")
    adults = pd.read_parquet(DATA_INPUT / "frs_raw_adults.parquet")
    children = pd.read_parquet(DATA_INPUT / "frs_raw_children.parquet")
    childcare = pd.read_parquet(DATA_INPUT / "frs_raw_childcare.parquet")
    benefits = pd.read_parquet(DATA_INPUT / "frs_raw_benefits.parquet")
    # Dividend income (from accounts table — optional, small file)
    accounts_path = DATA_INPUT / "frs_raw_accounts.parquet"
    accounts = pd.read_parquet(accounts_path) if accounts_path.exists() else pd.DataFrame(
        columns=["sernum", "benunit", "person", "dividend_weekly"]
    )
    # Maintenance (optional, small file)
    maint_path = DATA_INPUT / "frs_raw_maintenance.parquet"
    maintenance = pd.read_parquet(maint_path) if maint_path.exists() else pd.DataFrame(
        columns=["sernum", "benunit", "person", "maintenance_income_weekly", "maintenance_expense_weekly"]
    )

    # ------------------------------------------------------------------
    # Step 0: (Optional) restrict to working-age population
    # ------------------------------------------------------------------
    # The BENEFITS D2.2 shock analysis tool covers working-age households
    # only (JSA, UC, housing, CTR). Set WORKING_AGE_ONLY = False to
    # include pensioners for full-population validation.
    if WORKING_AGE_ONLY:
        log.info("Applying working-age filter (age < %d)...", WORKING_AGE_MAX)
        adults["age80"] = pd.to_numeric(adults["age80"], errors="coerce").fillna(0).astype(int)

        n_adults_before = len(adults)
        adults = adults[adults["age80"] < WORKING_AGE_MAX].copy()
        log.info("  Adults: %s -> %s (%s dropped)",
                 f"{n_adults_before:,}", f"{len(adults):,}",
                 f"{n_adults_before - len(adults):,}")

        valid_bus = adults[["sernum", "benunit"]].drop_duplicates()
        children = children.merge(valid_bus, on=["sernum", "benunit"], how="inner")
        childcare = childcare.merge(valid_bus, on=["sernum", "benunit"], how="inner")
        valid_persons = adults[["sernum", "benunit", "person"]].drop_duplicates()
        benefits = benefits.merge(valid_persons, on=["sernum", "benunit", "person"], how="inner")
    else:
        log.info("Working-age filter OFF — including full FRS population (pensioners retained)")

    # ------------------------------------------------------------------
    # Step 1: Clean adults
    # ------------------------------------------------------------------
    adults = adults.drop_duplicates(subset=["sernum", "benunit", "person"]).copy()

    for col in _INT_COLS_ADULT:
        if col in adults.columns:
            adults[col] = pd.to_numeric(adults[col], errors="coerce").fillna(0).astype(int)

    for col in _FLOAT_COLS_ADULT:
        if col in adults.columns:
            adults[col] = pd.to_numeric(adults[col], errors="coerce").fillna(0.0)

    log.info("  Adults (deduplicated): %s", f"{len(adults):,}")

    # ------------------------------------------------------------------
    # Step 2: Clean children
    # ------------------------------------------------------------------
    for col in ["sernum", "benunit", "person", "age", "sex"]:
        children[col] = pd.to_numeric(children[col], errors="coerce").fillna(0).astype(int)

    log.info("  Children: %s", f"{len(children):,}")

    # ------------------------------------------------------------------
    # Step 3: Merge disability/carer benefits onto adults
    # ------------------------------------------------------------------
    for col in ["sernum", "benunit", "person"]:
        benefits[col] = pd.to_numeric(benefits[col], errors="coerce").fillna(0).astype(int)

    adults = adults.merge(
        benefits[["sernum", "benunit", "person"] + _BENEFIT_COLS],
        on=["sernum", "benunit", "person"],
        how="left",
    )
    for col in _BENEFIT_COLS:
        adults[col] = adults[col].fillna(0.0)

    # Merge dividend income from accounts table
    for c in ["sernum", "benunit", "person"]:
        accounts[c] = pd.to_numeric(accounts[c], errors="coerce").fillna(0).astype(int)
    adults = adults.merge(
        accounts[["sernum", "benunit", "person", "dividend_weekly"]],
        on=["sernum", "benunit", "person"],
        how="left",
    )
    adults["dividend_weekly"] = adults["dividend_weekly"].fillna(0.0)

    # Merge maintenance (received / paid)
    for c in ["sernum", "benunit", "person"]:
        maintenance[c] = pd.to_numeric(maintenance[c], errors="coerce").fillna(0).astype(int)
    adults = adults.merge(
        maintenance[["sernum", "benunit", "person", "maintenance_income_weekly", "maintenance_expense_weekly"]],
        on=["sernum", "benunit", "person"],
        how="left",
    )
    adults["maintenance_income_weekly"] = adults["maintenance_income_weekly"].fillna(0.0)
    adults["maintenance_expense_weekly"] = adults["maintenance_expense_weekly"].fillna(0.0)

    log.info(
        "  Adults with disability/carer benefit: %s",
        f"{(adults[_BENEFIT_COLS].sum(axis=1) > 0).sum():,}",
    )

    # ------------------------------------------------------------------
    # Step 4: Aggregate to benefit-unit level
    # ------------------------------------------------------------------
    households = adults.groupby(["sernum", "benunit"]).agg(
        # Household / BU metadata
        gvtregn=("gvtregn", "first"),
        tenure=("tenure_code", "first"),
        ctband=("ctband", "first"),
        hh_weight=("gross4", "first"),
        num_adults=("person", "count"),

        # Per-person lists
        ages=("age80", list),
        sexes=("sex", list),
        empstatbs=("empstatb", list),
        empstatis=("empstati", list),   # needed for ESA/JSA disability proxies
        maritals=("marital", list),     # for marital_status mapping
        hrpids=("hrpid", list),         # for is_household_head derivation
        upersons=("uperson", list),     # for is_benunit_head derivation
        educfts=("educft", list),       # full-time education flag
        typeed2s=("typeed2", list),     # type of education
        educquals=("educqual", list),   # highest educational qualification
        sic_codes=("sic", list),
        soc_codes=("soc2020", list),
        hours_worked=("tothours", list),

        # Income per person (weekly £)
        employment_incomes=("inearns", list),
        self_employment_incomes=("seincam2", list),
        #pension_incomes=("state_pension_weekly", list),
        occupational_pensions=("inpeninc", list),
        investment_incomes=("inrinc", list),
        savings_interests=("totint", list),
        dividend_incomes=("dividend_weekly", list),

        # Rent — full rent before HB deductions (from renter table)
        weekly_rent=("rentfull", "first"),
        weekly_mortgage=("mortpay", "first"),
        weekly_mortgage_interest=("mortint", "first"),
        # Council Tax Rebate (household-level, weekly £)
        weekly_council_tax_rebate=("ctrebamt", "first"),

        # Maintenance (per person, weekly £)
        maintenance_incomes=("maintenance_income_weekly", list),
        maintenance_expenses=("maintenance_expense_weekly", list),

        # Care hours per person
        care_hours=("careah", list),

        # Employment-related benefits per person (weekly £)
        housing_benefit=("housing_benefit_weekly", list),
        jsa_contrib=("jsa_contrib_weekly", list),
        jsa_income=("jsa_income_weekly", list),

        # Phase 2 — disability / carer / pensioner / tax credits (weekly £, per person)
        state_pension=("state_pension_weekly", list),
        pension_credit=("pension_credit_weekly", list),
        attendance_allowance=("attendance_allowance_weekly", list),
        carers_allowance=("carers_allowance_weekly", list),
        dla_sc=("dla_sc_weekly", list),
        dla_m=("dla_m_weekly", list),
        pip_dl=("pip_dl_weekly", list),
        pip_m=("pip_m_weekly", list),
        esa_contrib=("esa_contrib_weekly", list),
        esa_income=("esa_income_weekly", list),
        income_support=("income_support_weekly", list),
        working_tax_credit=("working_tax_credit_weekly", list),
        child_tax_credit=("child_tax_credit_weekly", list),
    ).reset_index()

    log.info("  Benefit units: %s", f"{len(households):,}")

    # ------------------------------------------------------------------
    # Step 4b: Correct BU-level weight
    # ------------------------------------------------------------------
    # gross4 is a household-level grossing weight.  When a household
    # contains multiple benefit units, simply copying gross4 to each BU
    # inflates the weighted totals (28.6M → 35.4M).  Divide by the
    # number of BUs in the household so that the BU weights within a
    # household sum to the original gross4.
    bus_per_hh = (
        households.groupby("sernum")["benunit"]
        .transform("count")
        .astype(float)
    )
    households["hh_weight"] = households["hh_weight"] / bus_per_hh
    log.info(
        "  Adjusted BU weights (÷ BUs per HH). "
        "National weight total: %s",
        f"{households['hh_weight'].sum():,.0f}",
    )

    # ------------------------------------------------------------------
    # Step 5: Add children count + ages
    # ------------------------------------------------------------------
    child_counts = children.groupby(["sernum", "benunit"]).agg(
        num_children=("person", "count"),
        child_ages=("age", list),
        child_sexes=("sex", list),
    ).reset_index()

    households = households.merge(child_counts, on=["sernum", "benunit"], how="left")
    households["num_children"] = households["num_children"].fillna(0).astype(int)
    households["child_ages"] = households["child_ages"].apply(
        lambda x: x if isinstance(x, list) else []
    )
    households["child_sexes"] = households["child_sexes"].apply(
        lambda x: x if isinstance(x, list) else []
    )

    log.info(
        "  BUs with children: %s",
        f"{(households['num_children'] > 0).sum():,}",
    )

    # ------------------------------------------------------------------
    # Step 5b: Classify benefit-unit type (UC standard allowance bands)
    # ------------------------------------------------------------------
    # Used to validate PolicyEngine's UC standard allowance calculation.
    # UC rates differ by: single vs couple, under-25 vs 25+.
    min_age = households["ages"].apply(min)
    bu_type = pd.Series("unknown", index=households.index)
    bu_type[(households["num_adults"] == 1) & (min_age < 25)] = "single_under_25"
    bu_type[(households["num_adults"] == 1) & (min_age >= 25)] = "single_25_plus"
    bu_type[(households["num_adults"] >= 2) & (min_age < 25)] = "couple_under_25"
    bu_type[(households["num_adults"] >= 2) & (min_age >= 25)] = "couple_25_plus"
    households["bu_type"] = bu_type

    log.info(
        "  BU types:\n"
        "    single_under_25: %s\n"
        "    single_25_plus:  %s\n"
        "    couple_under_25: %s\n"
        "    couple_25_plus:  %s",
        f"{(bu_type == 'single_under_25').sum():,}",
        f"{(bu_type == 'single_25_plus').sum():,}",
        f"{(bu_type == 'couple_under_25').sum():,}",
        f"{(bu_type == 'couple_25_plus').sum():,}",
    )

    # ------------------------------------------------------------------
    # Step 6: Add childcare costs
    # ------------------------------------------------------------------
    childcare["sernum"] = pd.to_numeric(childcare["sernum"], errors="coerce").astype(int)
    childcare["benunit"] = pd.to_numeric(childcare["benunit"], errors="coerce").astype(int)

    households = households.merge(
        childcare[["sernum", "benunit", "weekly_childcare_cost"]],
        on=["sernum", "benunit"],
        how="left",
    )
    households["weekly_childcare_cost"] = households["weekly_childcare_cost"].fillna(0.0)

    log.info(
        "  BUs with childcare costs: %s",
        f"{(households['weekly_childcare_cost'] > 0).sum():,}",
    )

    # ------------------------------------------------------------------
    # Step 6b: Construct unified weekly housing cost by tenure
    # ------------------------------------------------------------------
    # Tenure codes (FRS househol TENURE, 2023-24):
    #   1 = Owns outright             → £0
    #   2 = Buying with mortgage      → mortpay
    #   3 = Part own / part rent      → rentfull + mortpay (shared ownership)
    #   4 = Rents                     → rentfull
    #   5 = Rent-free                 → £0
    #   6 = Squatting                 → £0
    def _housing_cost(row):
        t = row["tenure"]
        if t == 4:
            return row["weekly_rent"] or 0.0
        elif t == 2:
            return row["weekly_mortgage"] or 0.0
        elif t == 3:
            # Shared ownership: pays both part-rent and part-mortgage
            return (row["weekly_rent"] or 0.0) + (row["weekly_mortgage"] or 0.0)
        else:  # 1, 5, 6 → £0
            return 0.0

    households["housing_cost_weekly"] = households.apply(_housing_cost, axis=1)

    log.info(
        "  Housing cost by tenure (mean weekly £):\n%s",
        households.groupby("tenure")["housing_cost_weekly"]
        .agg(["count", "mean"]).to_string()
    )
    # ------------------------------------------------------------------
    # Step 7: Add region name (for display)
    # ------------------------------------------------------------------
    households["region_name"] = households["gvtregn"].map(REGION_NAMES)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    total_weight = households["hh_weight"].sum()
    log.info("  Weighted total: %s", f"{total_weight:,.0f}")

    if not _DEMO_MODE:
        if WORKING_AGE_ONLY:
            assert len(households) > 10_000, f"Expected ~13-15k working-age BUs, got {len(households)}"
            assert total_weight > 18_000_000, f"Expected weight sum ≈ 19-22M, got {total_weight:,.0f}"
        else:
            assert len(households) > 15_000, f"Expected ~19,374 BUs, got {len(households)}"
            assert total_weight > 25_000_000, f"Expected weight sum ≈ 28.8M, got {total_weight:,.0f}"

    assert (households["num_adults"] >= 1).all(), "BUs with zero adults found"

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    out_path = DATA_INTERMEDIATE / "frs_benefit_units.parquet"
    households.to_parquet(out_path, index=False)
    log.info("Saved %s rows to %s", f"{len(households):,}", out_path)

    # Summary
    log.info(
        "\nHousehold composition:\n"
        "  1 adult, no children:  %s\n"
        "  2 adults, no children: %s\n"
        "  1 adult + children:    %s\n"
        "  2 adults + children:   %s\n"
        "  3+ adults:             %s",
        f"{((households['num_adults'] == 1) & (households['num_children'] == 0)).sum():,}",
        f"{((households['num_adults'] == 2) & (households['num_children'] == 0)).sum():,}",
        f"{((households['num_adults'] == 1) & (households['num_children'] > 0)).sum():,}",
        f"{((households['num_adults'] == 2) & (households['num_children'] > 0)).sum():,}",
        f"{(households['num_adults'] >= 3).sum():,}",
    )

    return households


if __name__ == "__main__":
    build_benefit_unit_table()
