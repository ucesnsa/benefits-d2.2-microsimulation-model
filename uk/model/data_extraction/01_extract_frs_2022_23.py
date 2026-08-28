"""
01 — Extract FRS 2022-23 microdata from PostgreSQL.

Reads tables from the ``frs_2022_23`` schema and writes raw
parquet files plus an extraction metadata JSON to
``data/frs_2022_23/input/``.

Mirrors the FRS 2023-24 extraction so that downstream pipeline steps
(02_build_benefit_unit_table, 03_build_policyengine_dataset, …) see the
same input schema regardless of which fiscal year is being processed.

Two structural differences from the 23-24 version:
  * the 22-23 schema is all-lowercase, so no ``quote_col()`` wrapping is
    needed — bare identifiers are valid SQL;
  * the schema name is ``frs_2022_23`` (provided by ``FRS_SCHEMA``).

Outputs
-------
- frs_raw_adults.parquet
- frs_raw_children.parquet
- frs_raw_benefits.parquet
- frs_raw_childcare.parquet
- frs_raw_accounts.parquet      (dividend income from accounts table)
- frs_raw_maintenance.parquet   (paid / received maintenance from maint table)
- frs_extraction_metadata.json  (row counts, timestamp)

Usage
-----
    python uk/model/data_extraction/01_extract_frs_2022_23.py
"""
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from Code_FRS_22_23.utils.frs_config import (
    DATA_INPUT,
    FRS_SCHEMA,
    get_db_engine,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)

# ======================================================================
# SQL queries  (FRS 2022-23 column names are all lowercase — no quoting)
# ======================================================================

SQL_ADULTS = f"""
SELECT
    -- Household level
    h.sernum,
    h.gvtregn,
    h.tenure   AS tenure_code,
    h.adulth,
    h.depchldh,
    h.gross4,
    h.ctband,
    h.hdhhinc,

    -- Council Tax Rebate (for council_tax_benefit_reported)
    h.ctrebamt,
    h.ctrebpd,

    -- Benefit unit level
    b.benunit,
    b.burent,

    -- Housing costs
    r.rentfull,
    h.mortpay,
    h.mortint,

    -- Adult demographics
    a.person,
    a.hrpid,
    a.uperson,
    a.hdage,
    a.age80,
    a.sex,
    a.marital,

    -- Education
    a.educft,
    a.typeed2,
    a.educqual,
    a.empstat,
    a.empstatb,
    a.empstati,
    a.tothours,
    a.ftwk,
    a.sic,
    a.soc2020,
    a.numjob,

    -- Income (all weekly £)
    a.inearns,
    a.seincam2,
    a.inpeninc,
    a.inrinc,
    a.totint,

    -- Ethnicity & socioeconomic classification
    a.ethgrps,
    a.nssec20,

    -- Care & disability
    a.careah,
    a.health1,
    a.limitl

FROM {FRS_SCHEMA}.househol h
LEFT JOIN {FRS_SCHEMA}.benunit b
    ON h.sernum = b.sernum
LEFT JOIN {FRS_SCHEMA}.renter r
    ON h.sernum = r.sernum
LEFT JOIN {FRS_SCHEMA}.adult a
    ON h.sernum = a.sernum AND b.benunit = a.benunit
ORDER BY h.sernum, b.benunit, a.person;
"""

SQL_CHILDREN = f"""
SELECT
    sernum,
    benunit,
    person,
    age,
    sex
FROM {FRS_SCHEMA}.child
ORDER BY sernum, benunit, person;
"""

# Childcare: aggregate to BU level with period→weekly conversion.
# `chpd` is text — guard against non-numeric codes before casting.
SQL_CHILDCARE = f"""
SELECT
    sernum,
    benunit,
    SUM(
        CASE
            WHEN chamt > 0
                 AND chpd IS NOT NULL
                 AND TRIM(CAST(chpd AS TEXT)) ~ '^[0-9]+$'
            THEN
                chamt * CASE CAST(TRIM(CAST(chpd AS TEXT)) AS INTEGER)
                    WHEN 1  THEN 1.0
                    WHEN 2  THEN 1.0/2
                    WHEN 3  THEN 1.0/3
                    WHEN 4  THEN 1.0/4
                    WHEN 5  THEN 12.0/52
                    WHEN 7  THEN 6.0/52
                    WHEN 8  THEN 8.0/52
                    WHEN 9  THEN 9.0/52
                    WHEN 10 THEN 10.0/52
                    WHEN 13 THEN 1.0/13
                    WHEN 26 THEN 1.0/26
                    WHEN 52 THEN 1.0/52
                    WHEN 90 THEN 1.0
                    WHEN 95 THEN 1.0/52
                    ELSE 1.0
                END
            ELSE 0
        END
    ) AS weekly_childcare_cost
FROM {FRS_SCHEMA}.chldcare
WHERE chamt > 0
GROUP BY sernum, benunit
HAVING SUM(chamt) > 0;
"""

# Period conversion: only apply when benpd is a valid numeric code.
# (`benpd` is text in 22-23 too; keep the same guard as 23-24.)
_PERIOD_CONV = """
    CASE WHEN TRIM(CAST(benpd AS TEXT)) ~ '^[0-9]+$' THEN
        benamt * CASE CAST(TRIM(CAST(benpd AS TEXT)) AS INTEGER)
            WHEN 1  THEN 1.0
            WHEN 2  THEN 1.0/2
            WHEN 3  THEN 1.0/3
            WHEN 4  THEN 1.0/4
            WHEN 5  THEN 12.0/52
            WHEN 7  THEN 6.0/52
            WHEN 8  THEN 8.0/52
            WHEN 9  THEN 9.0/52
            WHEN 10 THEN 10.0/52
            WHEN 13 THEN 1.0/13
            WHEN 26 THEN 1.0/26
            WHEN 52 THEN 1.0/52
            WHEN 90 THEN 1.0
            WHEN 95 THEN 1.0/52
            ELSE 1.0
        END
    ELSE 0 END
"""

SQL_BENEFITS = f"""
SELECT
    sernum,
    benunit,
    person,
    SUM(CASE WHEN benefit = 94 THEN {_PERIOD_CONV} ELSE 0 END) AS housing_benefit_weekly,
    SUM(CASE WHEN benefit = 95 THEN {_PERIOD_CONV} ELSE 0 END) AS universal_credit_weekly,
    -- JSA: VAR2 flag distinguishes contribution-based (1, 3) from income-based (2, 4)
    SUM(CASE WHEN benefit = 14 AND CAST(var2 AS TEXT) IN ('1','3') THEN {_PERIOD_CONV} ELSE 0 END) AS jsa_contrib_weekly,
    SUM(CASE WHEN benefit = 14 AND CAST(var2 AS TEXT) IN ('2','4') THEN {_PERIOD_CONV} ELSE 0 END) AS jsa_income_weekly,
    -- ESA: same split
    SUM(CASE WHEN benefit = 16 AND CAST(var2 AS TEXT) IN ('1','3') THEN {_PERIOD_CONV} ELSE 0 END) AS esa_contrib_weekly,
    SUM(CASE WHEN benefit = 16 AND CAST(var2 AS TEXT) IN ('2','4') THEN {_PERIOD_CONV} ELSE 0 END) AS esa_income_weekly,
    SUM(CASE WHEN benefit = 1  THEN {_PERIOD_CONV} ELSE 0 END) AS dla_sc_weekly,
    SUM(CASE WHEN benefit = 2  THEN {_PERIOD_CONV} ELSE 0 END) AS dla_m_weekly,
    SUM(CASE WHEN benefit = 96 THEN {_PERIOD_CONV} ELSE 0 END) AS pip_dl_weekly,
    SUM(CASE WHEN benefit = 97 THEN {_PERIOD_CONV} ELSE 0 END) AS pip_m_weekly,
    SUM(CASE WHEN benefit = 12 THEN {_PERIOD_CONV} ELSE 0 END) AS attendance_allowance_weekly,
    SUM(CASE WHEN benefit = 13 THEN {_PERIOD_CONV} ELSE 0 END) AS carers_allowance_weekly,
    SUM(CASE WHEN benefit = 19 THEN {_PERIOD_CONV} ELSE 0 END) AS income_support_weekly,
    SUM(CASE WHEN benefit = 3  THEN {_PERIOD_CONV} ELSE 0 END) AS child_benefit_weekly,
    SUM(CASE WHEN benefit = 4  THEN {_PERIOD_CONV} ELSE 0 END) AS pension_credit_weekly,
    SUM(CASE WHEN benefit = 5  THEN {_PERIOD_CONV} ELSE 0 END) AS state_pension_weekly,
    SUM(CASE WHEN benefit = 90 THEN {_PERIOD_CONV} ELSE 0 END) AS working_tax_credit_weekly,
    SUM(CASE WHEN benefit = 91 THEN {_PERIOD_CONV} ELSE 0 END) AS child_tax_credit_weekly
FROM {FRS_SCHEMA}.benefits
WHERE benefit IN (1, 2, 3, 4, 5, 12, 13, 14, 16, 19, 90, 91, 94, 95, 96, 97)
  AND benamt > 0
  AND TRIM(CAST(benpd AS TEXT)) ~ '^[0-9]+$'
GROUP BY sernum, benunit, person
HAVING SUM(benamt) > 0;
"""

# ----------------------------------------------------------------------
# Maintenance (maint table): payments made or received per person.
#   mrus = 1 (received)  → mramt
#   mrus = 2 (paid)      → mruamt
# Both amount columns can be text in 22-23 (mruamt is text), so guard.
# ----------------------------------------------------------------------
SQL_MAINTENANCE = f"""
SELECT
    sernum,
    benunit,
    person,
    SUM(CASE WHEN TRIM(CAST(mrus AS TEXT)) = '1'
             THEN COALESCE(CASE WHEN TRIM(CAST(mramt AS TEXT)) ~ '^-?[0-9]+(\\.[0-9]+)?$'
                               THEN CAST(mramt AS NUMERIC) ELSE 0 END, 0)
             ELSE 0 END) AS maintenance_income_weekly,
    SUM(CASE WHEN TRIM(CAST(mrus AS TEXT)) = '2'
             THEN COALESCE(CASE WHEN TRIM(CAST(mruamt AS TEXT)) ~ '^-?[0-9]+(\\.[0-9]+)?$'
                               THEN CAST(mruamt AS NUMERIC) ELSE 0 END, 0)
             ELSE 0 END) AS maintenance_expense_weekly
FROM {FRS_SCHEMA}.maint
GROUP BY sernum, benunit, person
HAVING SUM(COALESCE(CASE WHEN TRIM(CAST(mramt AS TEXT)) ~ '^-?[0-9]+(\\.[0-9]+)?$'
                         THEN CAST(mramt AS NUMERIC) ELSE 0 END, 0)
         + COALESCE(CASE WHEN TRIM(CAST(mruamt AS TEXT)) ~ '^-?[0-9]+(\\.[0-9]+)?$'
                         THEN CAST(mruamt AS NUMERIC) ELSE 0 END, 0)) > 0;
"""

# ----------------------------------------------------------------------
# Accounts (for dividend income).
# FRS `accounts.account` codes used here (ref: policyengine-uk-data):
#   6 = Government Gilts  (only counts as dividend when invtax=1)
#   7 = Stocks and shares
#   8 = Unit trusts
# `accint` is the interest/dividend amount (weekly). `invtax=1` means basic-rate
# tax was deducted — gross-up by 1.25 to recover pre-tax value.
# ----------------------------------------------------------------------
SQL_ACCOUNTS = f"""
WITH clean AS (
    SELECT
        sernum,
        benunit,
        person,
        CASE WHEN TRIM(CAST(accint AS TEXT)) ~ '^-?[0-9]+(\\.[0-9]+)?$'
             THEN CAST(accint AS NUMERIC) ELSE 0 END AS accint,
        CASE WHEN TRIM(CAST(account AS TEXT)) ~ '^[0-9]+$'
             THEN CAST(account AS INTEGER) ELSE NULL END AS account,
        CASE WHEN TRIM(CAST(invtax AS TEXT)) ~ '^[0-9]+$'
             THEN CAST(invtax AS INTEGER) ELSE 0 END AS invtax
    FROM {FRS_SCHEMA}.accounts
    WHERE accint IS NOT NULL
)
SELECT
    sernum, benunit, person,
    SUM(
        accint
        * CASE WHEN invtax = 1 THEN 1.25 ELSE 1 END
        * CASE
            WHEN account IN (7, 8) THEN 1
            WHEN account = 6 AND invtax = 1 THEN 1
            ELSE 0
          END
    ) AS dividend_weekly
FROM clean
GROUP BY sernum, benunit, person
HAVING SUM(
    CASE
        WHEN account IN (7, 8) THEN 1
        WHEN account = 6 AND invtax = 1 THEN 1
        ELSE 0
    END
) > 0;
"""

# ======================================================================
# Main
# ======================================================================


def main() -> None:
    """Run all extraction queries and persist outputs."""
    DATA_INPUT.mkdir(parents=True, exist_ok=True)

    engine = get_db_engine()
    metadata: dict = {"timestamp": datetime.now(timezone.utc).isoformat()}

    # --- Adults ---
    log.info("Extracting adults from %s ...", FRS_SCHEMA)
    df_adults = pd.read_sql(SQL_ADULTS, engine)
    log.info(
        "  Adults: %s rows, %s unique households, %s unique BUs",
        f"{len(df_adults):,}",
        f"{df_adults['sernum'].nunique():,}",
        f"{df_adults[['sernum', 'benunit']].drop_duplicates().shape[0]:,}",
    )
    df_adults.to_parquet(DATA_INPUT / "frs_raw_adults.parquet", index=False)
    metadata["adults_rows"] = len(df_adults)

    # --- Children ---
    log.info("Extracting children...")
    df_children = pd.read_sql(SQL_CHILDREN, engine)
    log.info("  Children: %s rows", f"{len(df_children):,}")
    df_children.to_parquet(
        DATA_INPUT / "frs_raw_children.parquet", index=False
    )
    metadata["children_rows"] = len(df_children)

    # --- Childcare costs ---
    log.info("Extracting childcare costs...")
    df_childcare = pd.read_sql(SQL_CHILDCARE, engine)
    log.info("  Childcare: %s BU rows", f"{len(df_childcare):,}")
    df_childcare.to_parquet(
        DATA_INPUT / "frs_raw_childcare.parquet", index=False
    )
    metadata["childcare_rows"] = len(df_childcare)

    # --- Benefits ---
    log.info("Extracting housing/disability/carer benefits...")
    df_benefits = pd.read_sql(SQL_BENEFITS, engine)
    log.info(
        "  Benefits: %s person-rows with at least one benefit",
        f"{len(df_benefits):,}",
    )
    df_benefits.to_parquet(
        DATA_INPUT / "frs_raw_benefits.parquet", index=False
    )
    metadata["benefits_rows"] = len(df_benefits)

    # --- Dividend income (from accounts table) ---
    log.info("Extracting dividend income from accounts table...")
    df_accounts = pd.read_sql(SQL_ACCOUNTS, engine)
    log.info("  Adults with dividend income: %s", f"{len(df_accounts):,}")
    df_accounts.to_parquet(
        DATA_INPUT / "frs_raw_accounts.parquet", index=False
    )
    metadata["accounts_rows"] = len(df_accounts)

    # --- Maintenance payments (maint table) ---
    log.info("Extracting maintenance (paid/received)...")
    df_maint = pd.read_sql(SQL_MAINTENANCE, engine)
    log.info("  Adults with maintenance: %s", f"{len(df_maint):,}")
    df_maint.to_parquet(
        DATA_INPUT / "frs_raw_maintenance.parquet", index=False
    )
    metadata["maintenance_rows"] = len(df_maint)

    # --- Save metadata ---
    meta_path = DATA_INPUT / "frs_extraction_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    log.info("Wrote metadata to %s", meta_path)


if __name__ == "__main__":
    main()
