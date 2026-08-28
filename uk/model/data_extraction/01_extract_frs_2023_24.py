"""
01 — Extract FRS 2023-24 microdata from PostgreSQL.

Reads tables from the ``frs_2023_24`` schema and writes raw
parquet files plus an extraction metadata JSON to
``data/frs_2023_24/intermediate/``.

Outputs
-------
- frs_raw_adults.parquet
- frs_raw_children.parquet
- frs_raw_benefits.parquet
- frs_raw_childcare.parquet
- frs_extraction_metadata.json (row counts, timestamp)

Usage
-----
    python uk/model/data_extraction/01_extract_frs_2023_24.py
"""
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from Code_FRS_23_24.utils.frs_config import (
    DATA_INPUT,
    FRS_SCHEMA,
    get_db_engine,
    quote_col,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)

# ======================================================================
# SQL queries  (column names quoted for uppercase FRS 2023-24 schema)
# ======================================================================

SQL_ADULTS = f"""
SELECT
    -- Household level
    h.{quote_col('sernum')}   AS sernum,
    h.{quote_col('gvtregn')}  AS gvtregn,
    h.{quote_col('tenure')}   AS tenure_code,
    h.{quote_col('adulth')}   AS adulth,
    h.{quote_col('depchldh')} AS depchldh,
    h.{quote_col('gross4')}   AS gross4,
    h.{quote_col('ctband')}   AS ctband,
    h.{quote_col('hdhhinc')}  AS hdhhinc,

    -- Council Tax Rebate (for council_tax_benefit_reported)
    h.{quote_col('ctrebamt')} AS ctrebamt,
    h.{quote_col('ctrebpd')}  AS ctrebpd,

    -- Benefit unit level
    b.{quote_col('benunit')}  AS benunit,
    b.{quote_col('burent')}   AS burent,

    -- Housing costs
    r.{quote_col('rentfull')} AS rentfull,
    h.{quote_col('mortpay')}  AS mortpay,
    h.{quote_col('mortint')}  AS mortint,

    -- Adult demographics
    a.{quote_col('person')}   AS person,
    a.{quote_col('hrpid')}    AS hrpid,
    a.{quote_col('uperson')}  AS uperson,
    a.{quote_col('hdage')}    AS hdage,
    a.{quote_col('age80')}    AS age80,
    a.{quote_col('sex')}      AS sex,
    a.{quote_col('marital')}  AS marital,

    -- Education
    a.{quote_col('educft')}   AS educft,
    a.{quote_col('typeed2')}  AS typeed2,
    a.{quote_col('educqual')} AS educqual,
    a.{quote_col('empstat')}  AS empstat,
    a.{quote_col('empstatb')} AS empstatb,
    a.{quote_col('empstati')} AS empstati,
    a.{quote_col('tothours')} AS tothours,
    a.{quote_col('ftwk')}     AS ftwk,
    a.{quote_col('sic')}      AS sic,
    a.{quote_col('soc2020')}  AS soc2020,
    a.{quote_col('numjob')}   AS numjob,

    -- Income (all weekly £)
    a.{quote_col('inearns')}  AS inearns,
    a.{quote_col('seincam2')} AS seincam2,
    a.{quote_col('inpeninc')} AS inpeninc,
    a.{quote_col('inrinc')}   AS inrinc,
    a.{quote_col('totint')}   AS totint,

    -- Ethnicity & socioeconomic classification
    a.{quote_col('ethgrps')}  AS ethgrps,
    a.{quote_col('nssec20')}  AS nssec20,

    -- Care & disability
    a.{quote_col('careah')}   AS careah,
    a.{quote_col('health1')}  AS health1,
    a.{quote_col('limitl')}   AS limitl

FROM {FRS_SCHEMA}.househol h
LEFT JOIN {FRS_SCHEMA}.benunit b
    ON h.{quote_col('sernum')} = b.{quote_col('sernum')}
LEFT JOIN {FRS_SCHEMA}.renter r
    ON h.{quote_col('sernum')} = r.{quote_col('sernum')}
LEFT JOIN {FRS_SCHEMA}.adult a
    ON h.{quote_col('sernum')} = a.{quote_col('sernum')} AND b.{quote_col('benunit')} = a.{quote_col('benunit')}
ORDER BY h.{quote_col('sernum')}, b.{quote_col('benunit')}, a.{quote_col('person')};
"""

SQL_CHILDREN = f"""
SELECT
    {quote_col('sernum')}  AS sernum,
    {quote_col('benunit')} AS benunit,
    {quote_col('person')}  AS person,
    {quote_col('age')}     AS age,
    {quote_col('sex')}     AS sex
FROM {FRS_SCHEMA}.child
ORDER BY {quote_col('sernum')}, {quote_col('benunit')}, {quote_col('person')};
"""

# Childcare: aggregate to BU level with period→weekly conversion
SQL_CHILDCARE = f"""
SELECT
    {quote_col('sernum')}  AS sernum,
    {quote_col('benunit')} AS benunit,
    SUM(
        CASE
            WHEN {quote_col('chamt')} > 0
                 AND {quote_col('chpd')} IS NOT NULL
                 AND TRIM({quote_col('chpd')}) ~ '^[0-9]+$'
            THEN
                {quote_col('chamt')} * CASE CAST(TRIM({quote_col('chpd')}) AS INTEGER)
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
                    ELSE 0
                END
            ELSE 0
        END
    ) AS weekly_childcare_cost
FROM {FRS_SCHEMA}.chldcare
WHERE {quote_col('chamt')} > 0
GROUP BY {quote_col('sernum')}, {quote_col('benunit')}
HAVING SUM({quote_col('chamt')}) > 0;
"""

# Housing, disability & carer benefits with period→weekly conversion
# Period conversion: only apply when benpd is a valid numeric code
# (FRS 2023-24 includes non-numeric codes like 'A' which we skip)
_PERIOD_CONV = f"""
    CASE WHEN TRIM(CAST({quote_col('benpd')} AS TEXT)) ~ '^[0-9]+$' THEN
        {quote_col('benamt')} * CASE CAST(TRIM(CAST({quote_col('benpd')} AS TEXT)) AS INTEGER)
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
    {quote_col('sernum')}  AS sernum,
    {quote_col('benunit')} AS benunit,
    {quote_col('person')}  AS person,
    SUM(CASE WHEN {quote_col('benefit')} = 94 THEN {_PERIOD_CONV} ELSE 0 END) AS housing_benefit_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 95 THEN {_PERIOD_CONV} ELSE 0 END) AS universal_credit_weekly,
    -- JSA: VAR2 flag distinguishes contribution-based (1, 3) from income-based (2, 4)
    SUM(CASE WHEN {quote_col('benefit')} = 14 AND CAST({quote_col('var2')} AS TEXT) IN ('1','3') THEN {_PERIOD_CONV} ELSE 0 END) AS jsa_contrib_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 14 AND CAST({quote_col('var2')} AS TEXT) IN ('2','4') THEN {_PERIOD_CONV} ELSE 0 END) AS jsa_income_weekly,
    -- ESA: same split
    SUM(CASE WHEN {quote_col('benefit')} = 16 AND CAST({quote_col('var2')} AS TEXT) IN ('1','3') THEN {_PERIOD_CONV} ELSE 0 END) AS esa_contrib_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 16 AND CAST({quote_col('var2')} AS TEXT) IN ('2','4') THEN {_PERIOD_CONV} ELSE 0 END) AS esa_income_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 1  THEN {_PERIOD_CONV} ELSE 0 END) AS dla_sc_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 2  THEN {_PERIOD_CONV} ELSE 0 END) AS dla_m_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 96 THEN {_PERIOD_CONV} ELSE 0 END) AS pip_dl_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 97 THEN {_PERIOD_CONV} ELSE 0 END) AS pip_m_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 12 THEN {_PERIOD_CONV} ELSE 0 END) AS attendance_allowance_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 13 THEN {_PERIOD_CONV} ELSE 0 END) AS carers_allowance_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 19 THEN {_PERIOD_CONV} ELSE 0 END) AS income_support_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 3  THEN {_PERIOD_CONV} ELSE 0 END) AS child_benefit_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 4  THEN {_PERIOD_CONV} ELSE 0 END) AS pension_credit_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 5  THEN {_PERIOD_CONV} ELSE 0 END) AS state_pension_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 90 THEN {_PERIOD_CONV} ELSE 0 END) AS working_tax_credit_weekly,
    SUM(CASE WHEN {quote_col('benefit')} = 91 THEN {_PERIOD_CONV} ELSE 0 END) AS child_tax_credit_weekly
FROM {FRS_SCHEMA}.benefits
WHERE {quote_col('benefit')} IN (1, 2, 3, 4, 5, 12, 13, 14, 16, 19, 90, 91, 94, 95, 96, 97)
  AND {quote_col('benamt')} > 0
  AND TRIM(CAST({quote_col('benpd')} AS TEXT)) ~ '^[0-9]+$'
GROUP BY {quote_col('sernum')}, {quote_col('benunit')}, {quote_col('person')}
HAVING SUM({quote_col('benamt')}) > 0;
"""

# ----------------------------------------------------------------------
# Accounts (for dividend income)
# ----------------------------------------------------------------------
# FRS `accounts.account` codes used here (ref: policyengine-uk-data):
#   6 = Government Gilts  (only counts as dividend when invtax=1)
#   7 = Stocks and shares
#   8 = Unit trusts
# `accint` is the interest/dividend amount (weekly). `invtax=1` means basic-rate
# tax was deducted — gross-up by 1.25 to recover pre-tax value.
SQL_MAINTENANCE = f"""
-- FRS `maint` table: maintenance payments made or received per person
-- mrus = 1 (received) or 2 (paid).  mramt = received amount, mruamt = paid amount (weekly £).
SELECT
    {quote_col('sernum')}  AS sernum,
    {quote_col('benunit')} AS benunit,
    {quote_col('person')}  AS person,
    SUM(CASE WHEN TRIM(CAST({quote_col('mrus')} AS TEXT)) = '1'
             THEN COALESCE(CASE WHEN TRIM(CAST({quote_col('mramt')} AS TEXT)) ~ '^-?[0-9]+(\\.[0-9]+)?$'
                               THEN CAST({quote_col('mramt')} AS NUMERIC) ELSE 0 END, 0)
             ELSE 0 END) AS maintenance_income_weekly,
    SUM(CASE WHEN TRIM(CAST({quote_col('mrus')} AS TEXT)) = '2'
             THEN COALESCE(CASE WHEN TRIM(CAST({quote_col('mruamt')} AS TEXT)) ~ '^-?[0-9]+(\\.[0-9]+)?$'
                               THEN CAST({quote_col('mruamt')} AS NUMERIC) ELSE 0 END, 0)
             ELSE 0 END) AS maintenance_expense_weekly
FROM {FRS_SCHEMA}.maint
GROUP BY {quote_col('sernum')}, {quote_col('benunit')}, {quote_col('person')}
HAVING SUM(COALESCE(CASE WHEN TRIM(CAST({quote_col('mramt')} AS TEXT)) ~ '^-?[0-9]+(\\.[0-9]+)?$'
                         THEN CAST({quote_col('mramt')} AS NUMERIC) ELSE 0 END, 0)
         + COALESCE(CASE WHEN TRIM(CAST({quote_col('mruamt')} AS TEXT)) ~ '^-?[0-9]+(\\.[0-9]+)?$'
                         THEN CAST({quote_col('mruamt')} AS NUMERIC) ELSE 0 END, 0)) > 0;
"""

SQL_ACCOUNTS = f"""
WITH clean AS (
    SELECT
        {quote_col('sernum')}  AS sernum,
        {quote_col('benunit')} AS benunit,
        {quote_col('person')}  AS person,
        CASE WHEN TRIM(CAST({quote_col('accint')} AS TEXT)) ~ '^-?[0-9]+(\\.[0-9]+)?$'
             THEN CAST({quote_col('accint')} AS NUMERIC) ELSE 0 END AS accint,
        CASE WHEN TRIM(CAST({quote_col('account')} AS TEXT)) ~ '^[0-9]+$'
             THEN CAST({quote_col('account')} AS INTEGER) ELSE NULL END AS account,
        CASE WHEN TRIM(CAST({quote_col('invtax')} AS TEXT)) ~ '^[0-9]+$'
             THEN CAST({quote_col('invtax')} AS INTEGER) ELSE 0 END AS invtax
    FROM {FRS_SCHEMA}.accounts
    WHERE {quote_col('accint')} IS NOT NULL
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
# Extraction
# ======================================================================


def extract_all() -> dict:
    """Run all four extractions and return row-count metadata."""
    engine = get_db_engine()
    DATA_INPUT.mkdir(parents=True, exist_ok=True)

    metadata: dict = {"timestamp": datetime.now(timezone.utc).isoformat()}

    # --- Adults ---
    log.info("Extracting adults from %s ...", FRS_SCHEMA)
    df_adults = pd.read_sql(SQL_ADULTS, engine)
    log.info(
        "  Adults: %s rows, %s unique households, %s unique BUs",
        f"{len(df_adults):,}",
        f"{df_adults['sernum'].nunique():,}",
        f"{df_adults.groupby(['sernum', 'benunit']).ngroups:,}",
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
    log.info("  Childcare BUs: %s", f"{len(df_childcare):,}")
    df_childcare.to_parquet(
        DATA_INPUT / "frs_raw_childcare.parquet", index=False
    )
    metadata["childcare_rows"] = len(df_childcare)

    # --- Housing, disability & carer benefits ---
    log.info("Extracting housing, disability & carer benefits...")
    df_benefits = pd.read_sql(SQL_BENEFITS, engine)
    log.info("  Benefit recipients: %s", f"{len(df_benefits):,}")
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

    log.info("Extraction complete. Metadata saved to %s", meta_path)
    engine.dispose()
    return metadata


if __name__ == "__main__":
    extract_all()
