"""
FRS Configuration — shared constants, paths, and mapping tables.

Centralises all project paths, FRS-to-PolicyEngine mappings, and
pipeline constants used by the ingestion, processing, and analysis
scripts.  Import from here rather than hard-coding values.

This version targets the FRS 2023-24 dataset.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List

# ======================================================================
# Project paths
# ======================================================================

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent

# FRS_DATA_ROOT relocates the microdata and everything derived from it out of this
# tree, which is data-free by design. Same pattern as the EU side's EUROMOD_MODEL_PATH
# and this project's earlier UKHLS_DATA_ROOT. Unset, the in-tree layout is used, so a
# machine holding its data in place is unaffected. Set it to the directory that
# contains inputs/, processed/ and outputs/ for the FRS build.
_DATA_ROOT: Path = Path(os.getenv("FRS_DATA_ROOT", PROJECT_ROOT))

if os.getenv("FRS_DEMO_MODE"):
    DATA_INPUT: Path = PROJECT_ROOT / "demo" / "inputs" / "frs_2023_24"
    DATA_INTERMEDIATE: Path = PROJECT_ROOT / "demo" / "processed" / "frs_2023_24"
    DATA_OUTPUT: Path = PROJECT_ROOT / "demo" / "outputs" / "frs_2023_24"
else:
    DATA_INPUT = _DATA_ROOT / "inputs" / "frs_2023_24"
    DATA_INTERMEDIATE = _DATA_ROOT / "processed" / "frs_2023_24"
    DATA_OUTPUT = _DATA_ROOT / "outputs" / "frs_2023_24"

# The response surface is a DELIVERABLE, not pipeline data. It always lands in the
# tree at the one canonical path check_drift.py and the four tools read, whatever
# FRS_DATA_ROOT says. Keeping this separate from DATA_OUTPUT is deliberate: step 09
# previously wrote to DATA_OUTPUT / "dial_grid.json", which resolves to a directory
# that does not exist in the Deliverable layout, so a rebuild would have written the
# surface somewhere nothing reads and left the tools on the old one.
SURFACE_PATH: Path = PROJECT_ROOT / "outputs" / "dial_grid.json"

REF_IMPL_DIR: Path = (
    PROJECT_ROOT / "reference_implementation" / "code"
)

# ======================================================================
# Period configuration
# ======================================================================

FRS_FISCAL_YEAR: int = 2023          # FRS 2023-24 fiscal year (Apr 2023–Mar 2024)
PE_PERIOD: int = 2023                # 2023-24 policy: 12% main NI, pre-Apr-2024 cut
PE_PERIOD_STR: str = "2023"          # String form for PE .calculate()

# PostgreSQL schema name
FRS_SCHEMA: str = "frs_2023_24"

# ======================================================================
# FRS gvtregn → PolicyEngine Region enum key
# ======================================================================

REGION_MAP: Dict[int, str] = {
    112000001: "NORTH_EAST",
    112000002: "NORTH_WEST",
    112000003: "YORKSHIRE",
    112000004: "EAST_MIDLANDS",
    112000005: "WEST_MIDLANDS",
    112000006: "EAST_OF_ENGLAND",
    112000007: "LONDON",
    112000008: "SOUTH_EAST",
    112000009: "SOUTH_WEST",
    299999999: "SCOTLAND",
    399999999: "WALES",
    499999999: "NORTHERN_IRELAND",
}

# Human-readable region names (for logging / display)
REGION_NAMES: Dict[int, str] = {
    112000001: "North East",
    112000002: "North West",
    112000003: "Yorks and the Humber",
    112000004: "East Midlands",
    112000005: "West Midlands",
    112000006: "East of England",
    112000007: "London",
    112000008: "South East",
    112000009: "South West",
    299999999: "Scotland",
    399999999: "Wales",
    499999999: "Northern Ireland",
}

# ======================================================================
# FRS tenure → PolicyEngine TenureType enum key
# ======================================================================

TENURE_MAP: Dict[int, str] = {
    1: "OWNED_OUTRIGHT",
    2: "OWNED_WITH_MORTGAGE",
    3: "RENT_FROM_COUNCIL",
    4: "RENT_FROM_HA",
    5: "RENT_PRIVATELY",
    6: "OWNED_OUTRIGHT",          # "Rent free" → treat as owned outright
}

# ======================================================================
# FRS sex → PolicyEngine Gender enum key
# ======================================================================

GENDER_MAP: Dict[int, str] = {
    1: "MALE",
    2: "FEMALE",
}

# ======================================================================
# FRS ctband → PolicyEngine CouncilTaxBand enum key  (A–H)
# ======================================================================

CT_BAND_MAP: Dict[int, str] = {
    1: "A",
    2: "B",
    3: "C",
    4: "D",
    5: "E",
    6: "F",
    7: "G",
    8: "H",
}

# ======================================================================
# Output variables — same 17 as reference implementation
# ======================================================================

OUTPUT_VARIABLES: List[str] = [
    # Benefits
    "universal_credit",
    "uc_standard_allowance",
    "uc_child_element",
    "uc_housing_costs_element",
    "child_benefit",
    "housing_benefit",
    "council_tax_benefit",
    "jsa_contrib",
    "jsa_income",
    "household_benefits",
    # Tax
    "income_tax",
    "national_insurance",         # Employee (Class 1) + self-emp (Class 2 + 4) + Class 3
    "ni_employer",                # Class 1 employer NI (missing from `national_insurance`)
    "ni_self_employed",           # Class 2 + 4 only (subset of national_insurance)
    "total_national_insurance",   # national_insurance + ni_employer — matches OBR headline NIC
    "council_tax",
    # Income measures
    "household_net_income",
    "household_net_income_ahc",   # after housing costs — HBAI AHC income
    "employment_income",
    "total_income",
    "housing_costs",              # gross annual housing costs (for AHC derivation)
    # Work incentive indicators
    "marginal_tax_rate",
    # Poverty
    # HBAI publishes *relative* poverty as its headline (60% of contemporary
    # median equivalised income).  PE also exposes an *absolute* flag
    # (anchored threshold) — we keep both for completeness.
    "in_relative_poverty_bhc",    # HBAI headline — BHC
    "in_relative_poverty_ahc",    # HBAI headline — AHC
    "in_poverty_bhc",             # absolute BHC (anchored)
    "in_poverty_ahc",             # absolute AHC (anchored)
    "poverty_gap_bhc",            # £ distance below BHC line (depth of poverty)
    "poverty_gap_ahc",            # £ distance below AHC line
]

# Variables that may not exist in all PolicyEngine versions
OPTIONAL_VARIABLES: List[str] = [
    "uc_housing_costs_element",
    "council_tax_benefit",
    "jsa_contrib",
    "jsa_income",
    "council_tax",
    "total_income",
    "marginal_tax_rate",
    "uc_child_element",
    "housing_benefit",
    # Poverty / AHC variables added 2024-Q4 refresh of PE UK; guarded
    # for compatibility with older installs.
    "household_net_income_ahc",
    "housing_costs",
    "in_relative_poverty_bhc",
    "in_relative_poverty_ahc",
    "in_poverty_bhc",
    "in_poverty_ahc",
    "poverty_gap_bhc",
    "poverty_gap_ahc",
]

# ======================================================================
# FRS benefit payment period → weekly multiplier
# (same codes for benpd and chpd)
# ======================================================================

PERIOD_TO_WEEKLY: Dict[int, float] = {
    1: 1.0,                  # weekly
    2: 1.0 / 2,              # fortnightly
    3: 1.0 / 3,              # 3 weeks
    4: 1.0 / 4,              # 4 weeks
    5: 12.0 / 52,            # calendar month
    7: 6.0 / 52,             # 2 calendar months
    8: 8.0 / 52,             # 8 times a year
    9: 9.0 / 52,             # 9 times a year
    10: 10.0 / 52,           # 10 times a year
    13: 1.0 / 13,            # quarterly (13 weeks)
    26: 1.0 / 26,            # 6 months (26 weeks)
    52: 1.0 / 52,            # annual (52 weeks)
    90: 1.0,                 # less than 1 week → treat as weekly
    95: 1.0 / 52,            # one-off lump sum → spread over year
}

# ======================================================================
# Council tax estimates by band (2023-24, England average Band D = £2,065)
# Ratios: A=6/9, B=7/9, C=8/9, D=1, E=11/9, F=13/9, G=15/9, H=2
# ======================================================================

_BAND_D_2023: float = 2065.0

CT_ANNUAL_BY_BAND: Dict[str, float] = {
    "A": round(_BAND_D_2023 * 6 / 9, 0),
    "B": round(_BAND_D_2023 * 7 / 9, 0),
    "C": round(_BAND_D_2023 * 8 / 9, 0),
    "D": round(_BAND_D_2023, 0),
    "E": round(_BAND_D_2023 * 11 / 9, 0),
    "F": round(_BAND_D_2023 * 13 / 9, 0),
    "G": round(_BAND_D_2023 * 15 / 9, 0),
    "H": round(_BAND_D_2023 * 2, 0),
}

# ======================================================================
# Helpers
# ======================================================================


def add_ref_impl_to_path() -> None:
    """Add the reference implementation directory to ``sys.path``."""
    ref_str = str(REF_IMPL_DIR)
    if ref_str not in sys.path:
        sys.path.insert(0, ref_str)


# FRS 2023-24 has mixed-case column names.  This lookup maps the
# canonical lowercase name used in 22-23 to the exact case in 23-24.
_COL_CASE_2324: Dict[str, str] = {
    # househol
    "sernum": "SERNUM", "gvtregn": "GVTREGN", "tenure": "TENURE",
    "adulth": "adulth", "depchldh": "depchldh", "gross4": "gross4",
    "ctband": "CTBAND", "hdhhinc": "hdhhinc",
    "mortpay": "mortpay", "mortint": "mortint",
    # adult
    "benunit": "BENUNIT", "person": "PERSON",
    "hdage": "hdage", "age80": "age80", "age": "AGE",
    "sex": "SEX", "marital": "marital", "ms": "MS",
    "empstat": "EMPSTAT", "empstatb": "empstatb",
    "empstati": "empstati", "empstatc": "EMPSTATC",
    # head of household / benunit head flags
    "hrpid": "HRPID", "uperson": "uperson",
    "tothours": "TOTHOURS", "ftwk": "FTWK",
    "sic": "SIC", "soc2020": "SOC2020", "mjobsect": "mjobsect",
    "numjob": "NUMJOB",
    "inearns": "inearns", "seincam2": "seincam2",
    "inpeninc": "inpeninc", "inrinc": "inrinc", "totint": "TOTINT",
    "ethgrps": "ETHGRPS", "nssec20": "NSSEC20",
    "careah": "CAREAH", "health1": "HEALTH1", "limitl": "LIMITL",
    # benunit
    "burent": "BURENT",
    # renter
    "rentfull": "RENTFULL",
    # child  (age/sex/sernum/benunit/person already above)
    # chldcare
    "chamt": "CHAMT", "chpd": "CHPD",
    # benefits
    "benefit": "BENEFIT", "benamt": "BENAMT", "benpd": "BENPD",
    "var2": "VAR2",
    # accounts (dividend / savings income)
    "account": "ACCOUNT", "accint": "ACCINT",
    "acctax": "ACCTAX", "invtax": "INVTAX",
    # education (adult)
    "educft": "EDUCFT", "fted": "EDUCFT",       # FRS 23-24 renamed fted→educft
    "typeed2": "TYPEED2", "educqual": "EDUCQUAL",
    # council tax rebate (househol)
    "ctrebamt": "CTREBAMT", "ctrebpd": "CTREBPD",
    # maintenance (maint table)
    "mrus": "MRUS", "mramt": "MRAMT", "mruamt": "MRUAMT",
    "mrpd": "MRPD", "mrupd": "MRUPD",
}


def quote_col(col: str) -> str:
    """Quote a column name for the FRS 2023-24 schema (mixed-case columns).

    Looks up the exact case from ``_COL_CASE_2324`` and wraps in double
    quotes.  Falls back to the input as-is (quoted) if not in the map.

    Example::

        f"SELECT {quote_col('sernum')}, {quote_col('gross4')} FROM {FRS_SCHEMA}.househol"
        # → 'SELECT "SERNUM", "gross4" FROM frs_2023_24.househol'
    """
    exact = _COL_CASE_2324.get(col.lower(), col)
    return f'"{exact}"'


def get_db_engine():
    """Create a SQLAlchemy engine from ``.env`` credentials.

    Returns:
        sqlalchemy.engine.Engine
    """
    import os

    from dotenv import load_dotenv
    from sqlalchemy import create_engine
    from sqlalchemy.engine import URL

    load_dotenv(PROJECT_ROOT / ".env")

    url = URL.create(
        drivername="postgresql",
        username=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", ""),
    )
    return create_engine(url)
