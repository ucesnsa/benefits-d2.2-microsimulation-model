"""
================================================================================
Centralised Parameter Registry for BENEFITS Microsimulation Platform
================================================================================

Author: BENEFITS D2.2 - UCL Data Team IGP
Date: February 2026

Single source of truth for every parameter, elasticity, and calibration value
used across the microsimulation. Each parameter includes its value, source,
plausible range, unit, and description.

Data sources:
- EHS 2024-25: English Housing Survey (housing tenure, rents)
- Census 2021 RM135: Tenure by household composition
- ONS Families & Households 2023: household composition
- ONS LFS 2024 Q3: unemployment rate, labour force
- ONS ASHE 2024: earnings distribution
- DWP Stat-Xplore 2024: UC caseload, benefit rates
- OBR 2023 Fiscal Risks Report: Okun coefficient, fiscal multipliers
- HMRC 2023-24: income tax and NI receipts per worker
- GOV.UK 2024-25: Council tax levels

Usage:
    from parameters import get_param, PARAMETER_REGISTRY

    beta = get_param("macro.okun_beta")          # 0.4
    elast = get_param("service_demand.food_banks.demand_elasticity")  # 1.5
================================================================================
"""

import json
import copy
import sys

# Prints an arrow in its own output, which a Windows cp1252 console cannot encode, so
# the script died in print() with a UnicodeEncodeError and exited non-zero even though
# it had done its work. Same defect as check_browser.py had; handled here rather than
# by asking the caller to set PYTHONIOENCODING.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError, OSError):
    pass


# ==============================================================================
# PARAMETER REGISTRY
# ==============================================================================

PARAMETER_REGISTRY = {

    # ==========================================================================
    # MACRO PARAMETERS
    # ==========================================================================
    "macro": {
        "okun_beta": {
            "value": 0.4,
            "source": "OBR 2023 Fiscal Risks; Ball, Leigh & Loungani 2017 (IMF)",
            "range": [0.35, 0.50],
            "unit": "coefficient",
            "description": "Okun coefficient for UK: 1% GDP drop → 0.4pp unemployment rise",
            "editable": True,
        },
        "baseline_unemployment_rate": {
            "value": 0.043,
            "source": "ONS LFS Jul-Sep 2024 (Employment in the UK: November 2024, 12 Nov 2024)",
            "range": [0.035, 0.055],
            "unit": "fraction",
            "description": "UK baseline unemployment rate (4.3%)",
            "editable": True,
        },
        "labour_force_millions": {
            "value": 33.0,
            "source": "ONS LFS 2024",
            "range": [32.0, 34.0],
            "unit": "millions",
            "description": "UK economically active population",
            "editable": False,
        },
        "working_age_households_millions": {
            "value": 19.4,
            "source": "ONS 2023",
            "range": [18.5, 20.5],
            "unit": "millions",
            "description": "Working-age households in England & Wales",
            "editable": False,
        },
        "unemployment_time_profile": {
            "value": {
                0: 0.15, 1: 0.45, 2: 0.70, 3: 0.90, 4: 1.00,
                5: 0.95, 6: 0.88, 7: 0.80, 8: 0.72,
            },
            "source": "OBR fiscal risks report; BoE quarterly bulletin",
            "range": None,
            "unit": "fraction of peak",
            "description": "Quarter-by-quarter fraction of total unemployment rise realised after GDP trough",
            "editable": False,
        },
    },

    # ==========================================================================
    # BENEFIT PARAMETERS
    # ==========================================================================
    "benefits": {
        # --- JSA ---
        "jsa_eligibility_rate": {
            "value": 0.35,
            "source": "DWP administrative data; requires 2 full years NI in last 3 tax years",
            "range": [0.25, 0.45],
            "unit": "fraction",
            "description": "Fraction of newly unemployed who qualify for new-style JSA",
            "editable": True,
        },
        "jsa_weekly_rate_25_plus": {
            "value": 84.80,
            "source": "DWP benefit rates 2024-25",
            "range": [80.0, 90.0],
            "unit": "£/week",
            "description": "JSA weekly rate for claimants aged 25+",
            "editable": True,
        },
        "jsa_weekly_rate_under_25": {
            "value": 67.20,
            "source": "DWP benefit rates 2024-25",
            "range": [63.0, 72.0],
            "unit": "£/week",
            "description": "JSA weekly rate for claimants under 25",
            "editable": True,
        },
        "jsa_max_duration_weeks": {
            "value": 26,
            "source": "DWP statutory maximum (182 days)",
            "range": [26, 26],
            "unit": "weeks",
            "description": "Maximum duration of new-style JSA claim (6 months)",
            "editable": False,
        },
        "jsa_take_up_rate": {
            "value": 0.70,
            "source": "DWP; many eligible don't claim (stigma, complexity, short expected spell)",
            "range": [0.55, 0.80],
            "unit": "fraction",
            "description": "Take-up rate of JSA among those eligible",
            "editable": True,
        },
        # --- UC ---
        "uc_eligibility_rate": {
            "value": 0.85,
            "source": "DWP Stat-Xplore; means-tested on savings (<£16k) and household income",
            "range": [0.75, 0.92],
            "unit": "fraction",
            "description": "Fraction of newly unemployed eligible for UC (means-tested)",
            "editable": True,
        },
        "uc_take_up_rate": {
            "value": 0.87,
            "source": "DWP 2023 take-up estimates",
            "range": [0.80, 0.92],
            "unit": "fraction",
            "description": "UC take-up rate among entitled",
            "editable": True,
        },
        "uc_five_week_wait": {
            "value": True,
            "source": "DWP policy (first payment after ~5 weeks)",
            "range": None,
            "unit": "boolean",
            "description": "Whether the 5-week wait before first UC payment applies",
            "editable": False,
        },
        "uc_avg_spell_months": {
            "value": 8,
            "source": "DWP Stat-Xplore; average unemployment-related UC spell",
            "range": [6, 12],
            "unit": "months",
            "description": "Average UC spell duration for unemployment claimants",
            "editable": True,
        },
        "uc_standard_allowance_single_under_25": {
            "value": 311.68,
            "source": "DWP UC rates 2024-25",
            "range": [290, 350],
            "unit": "£/month",
            "description": "UC standard allowance: single claimant under 25",
            "editable": True,
        },
        "uc_standard_allowance_single_25_plus": {
            "value": 393.45,
            "source": "DWP UC rates 2024-25",
            "range": [370, 430],
            "unit": "£/month",
            "description": "UC standard allowance: single claimant 25+",
            "editable": True,
        },
        "uc_standard_allowance_couple_both_under_25": {
            "value": 489.23,
            "source": "DWP UC rates 2024-25",
            "range": [460, 530],
            "unit": "£/month",
            "description": "UC standard allowance: couple both under 25",
            "editable": True,
        },
        "uc_standard_allowance_couple_one_25_plus": {
            "value": 617.60,
            "source": "DWP UC rates 2024-25",
            "range": [580, 660],
            "unit": "£/month",
            "description": "UC standard allowance: couple, at least one 25+",
            "editable": True,
        },
        "uc_housing_element_rate": {
            "value": 0.60,
            "source": "DWP Stat-Xplore: ~60% of UC claimants receive housing element",
            "range": [0.50, 0.70],
            "unit": "fraction",
            "description": "Fraction of UC claimants receiving housing element",
            "editable": True,
        },
        "uc_avg_housing_element_monthly": {
            "value": 550,
            "source": "DWP Stat-Xplore average; varies by region and tenure",
            "range": [400, 750],
            "unit": "£/month",
            "description": "Average UC housing element per claimant receiving it",
            "editable": True,
        },
        "uc_taper_rate": {
            "value": 0.55,
            "source": "DWP policy: 55% taper (reduced from 63% in 2021 Autumn Budget)",
            "range": [0.45, 0.65],
            "unit": "fraction",
            "description": "UC taper rate: for each £1 earned above work allowance, UC reduced by 55p",
            "editable": True,
        },
        "uc_work_allowance_with_housing": {
            "value": 404,
            "source": "DWP UC rates 2024-25",
            "range": [350, 500],
            "unit": "£/month",
            "description": "UC work allowance (with housing element): earnings disregarded before taper",
            "editable": True,
        },
        "uc_work_allowance_no_housing": {
            "value": 673,
            "source": "DWP UC rates 2024-25",
            "range": [600, 800],
            "unit": "£/month",
            "description": "UC work allowance (no housing element)",
            "editable": True,
        },
        "uc_child_element_first": {
            "value": 333.33,
            "source": "DWP UC rates 2024-25",
            "range": [310, 370],
            "unit": "£/month",
            "description": "UC child element for first/only child",
            "editable": True,
        },
        "uc_child_element_subsequent": {
            "value": 287.92,
            "source": "DWP UC rates 2024-25 (subject to two-child limit)",
            "range": [270, 320],
            "unit": "£/month",
            "description": "UC child element for second and subsequent children (subject to two-child limit)",
            "editable": True,
        },
        # --- CTR ---
        "ctr_eligibility_rate": {
            "value": 0.80,
            "source": "Local authority schemes; most out-of-work households eligible",
            "range": [0.70, 0.90],
            "unit": "fraction",
            "description": "Fraction of out-of-work households eligible for CTR",
            "editable": True,
        },
        "ctr_take_up_rate": {
            "value": 0.75,
            "source": "DWP/DLUHC estimates; lower than UC take-up",
            "range": [0.65, 0.85],
            "unit": "fraction",
            "description": "CTR take-up rate among those eligible",
            "editable": True,
        },
        "ctr_avg_annual_value": {
            "value": 2065,
            "source": "GOV.UK 2024-25 average Band D council tax",
            "range": [1800, 2400],
            "unit": "£/year",
            "description": "Average annual council tax (Band D, 2024-25)",
            "editable": True,
        },
        # --- Non-take-up ---
        "non_take_up_rate": {
            "value": 0.13,
            "source": "DWP 2023 benefit take-up statistics",
            "range": [0.08, 0.20],
            "unit": "fraction",
            "description": "Fraction of entitled people who don't claim UC",
            "editable": True,
        },
    },

    # ==========================================================================
    # POPULATION PARAMETERS
    # ==========================================================================
    "population": {
        "avg_household_size": {
            "value": 2.4,
            "source": "ONS LFS 2024; for unemployed households",
            "range": [2.2, 2.6],
            "unit": "people",
            "description": "Average household size of unemployed households",
            "editable": False,
        },
        "fraction_with_children": {
            "value": 0.35,
            "source": "ONS LFS 2024; ~35% of newly unemployed HHs have dependent children",
            "range": [0.30, 0.40],
            "unit": "fraction",
            "description": "Fraction of newly unemployed households with dependent children",
            "editable": True,
        },
        "avg_children_if_any": {
            "value": 1.7,
            "source": "ONS Families & Households 2023",
            "range": [1.5, 2.0],
            "unit": "children",
            "description": "Average number of dependent children in HHs that have children",
            "editable": False,
        },
        "partner_fraction": {
            "value": 0.45,
            "source": "ONS LFS 2024",
            "range": [0.40, 0.50],
            "unit": "fraction",
            "description": "Fraction of newly unemployed adults who have a cohabiting partner",
            "editable": True,
        },
        "child_poverty_elasticity": {
            "value": 2.0,
            "source": "IFS 2020 estimate: ~2pp child poverty rise per 1pp unemployment rise",
            "range": [1.5, 3.0],
            "unit": "pp per pp",
            "description": "Percentage point rise in child poverty per 1pp unemployment rise",
            "editable": True,
        },
        "baseline_child_poverty_rate": {
            "value": 0.30,
            "source": "DWP HBAI FYE 2023 (4.3m children in relative poverty AHC = 30%)",
            "range": [0.25, 0.35],
            "unit": "fraction",
            "description": "Baseline UK child poverty rate (30%, after housing costs)",
            "editable": True,
        },
        "total_children_millions": {
            "value": 12.7,
            "source": "ONS mid-year estimates 2023 (children under 16)",
            "range": [12.0, 13.5],
            "unit": "millions",
            "description": "Total UK children under 16",
            "editable": False,
        },
        "age_profile_under_25": {
            "value": 0.25,
            "source": "ONS LFS; ~25% of newly unemployed are under 25",
            "range": [0.20, 0.35],
            "unit": "fraction",
            "description": "Fraction of newly unemployed aged under 25",
            "editable": True,
        },
        "age_profile_25_plus": {
            "value": 0.75,
            "source": "ONS LFS; complement of under-25 fraction",
            "range": [0.65, 0.80],
            "unit": "fraction",
            "description": "Fraction of newly unemployed aged 25+",
            "editable": True,
        },
        "individual_to_household_ratio": {
            "value": 0.70,
            "source": "Derived: some newly unemployed are from same household (couples)",
            "range": [0.65, 0.75],
            "unit": "ratio",
            "description": "Ratio to convert newly unemployed individuals to households",
            "editable": True,
        },
    },

    # ==========================================================================
    # TAX PARAMETERS
    # ==========================================================================
    "tax": {
        "avg_income_tax_per_worker": {
            "value": 5400,
            "source": "HMRC 2023-24; median FT worker",
            "range": [4500, 6500],
            "unit": "£/year",
            "description": "Average annual income tax paid by a median full-time worker",
            "editable": True,
        },
        "avg_ni_per_worker": {
            "value": 3200,
            "source": "HMRC 2023-24; employer + employee NI for median earner",
            "range": [2800, 3800],
            "unit": "£/year",
            "description": "Average annual NI contributions (employer + employee)",
            "editable": True,
        },
        "avg_vat_per_worker": {
            "value": 2100,
            "source": "OBR; indirect estimate based on ~60% of spending subject to standard rate",
            "range": [1800, 2500],
            "unit": "£/year",
            "description": "Estimated annual VAT revenue lost per worker (reduced consumption)",
            "editable": True,
        },
        "personal_allowance": {
            "value": 12570,
            "source": "HMRC 2024-25 income tax thresholds",
            "range": [12570, 15000],
            "unit": "£/year",
            "description": "Income tax personal allowance (frozen since 2021-22)",
            "editable": True,
        },
        "basic_rate": {
            "value": 0.20,
            "source": "HMRC 2024-25",
            "range": [0.18, 0.22],
            "unit": "fraction",
            "description": "Basic rate of income tax (20%)",
            "editable": True,
        },
        "higher_rate_threshold": {
            "value": 50270,
            "source": "HMRC 2024-25",
            "range": [50270, 55000],
            "unit": "£/year",
            "description": "Higher rate income tax threshold",
            "editable": True,
        },
        "ni_primary_threshold_annual": {
            "value": 12570,
            "source": "HMRC 2024-25 (aligned with personal allowance)",
            "range": [11500, 14000],
            "unit": "£/year",
            "description": "Primary NI threshold (employee contributions start here)",
            "editable": True,
        },
        "median_ft_earnings": {
            "value": 37430,
            "source": "ONS ASHE 2024 (Table 1, ref. April 2024, published 29 Oct 2024)",
            "range": [35000, 40000],
            "unit": "£/year",
            "description": "Median full-time annual earnings in the UK",
            "editable": False,
        },
        "child_benefit_first_child_weekly": {
            "value": 26.05,
            "source": "HMRC 2024-25",
            "range": [24.0, 30.0],
            "unit": "£/week",
            "description": "Child benefit: weekly rate for eldest/only child",
            "editable": True,
        },
        "child_benefit_subsequent_weekly": {
            "value": 17.25,
            "source": "HMRC 2024-25",
            "range": [16.0, 20.0],
            "unit": "£/week",
            "description": "Child benefit: weekly rate for each subsequent child",
            "editable": True,
        },
        "hicbc_threshold": {
            "value": 60000,
            "source": "HMRC 2024-25 (raised from £50k in April 2024)",
            "range": [50000, 80000],
            "unit": "£/year",
            "description": "High Income Child Benefit Charge threshold",
            "editable": True,
        },
    },

    # ==========================================================================
    # HOUSING PARAMETERS (EHS 2024-25 + Census 2021)
    # ==========================================================================
    "housing": {
        "tenure_owner_occupied_pct": {
            "value": 0.65,
            "source": "EHS 2024-25 (36% outright + 29% mortgage)",
            "range": [0.62, 0.68],
            "unit": "fraction",
            "description": "National share of households who are owner-occupiers",
            "editable": False,
        },
        "tenure_private_rent_pct": {
            "value": 0.19,
            "source": "EHS 2024-25",
            "range": [0.17, 0.22],
            "unit": "fraction",
            "description": "National share of households in private rented sector",
            "editable": False,
        },
        "tenure_social_rent_pct": {
            "value": 0.16,
            "source": "EHS 2024-25 (4.1m households)",
            "range": [0.14, 0.18],
            "unit": "fraction",
            "description": "National share of households in social rented sector",
            "editable": False,
        },
        "social_rent_weekly": {
            "value": 129,
            "source": "EHS 2024-25 national mean (£119/wk outside London)",
            "range": [100, 170],
            "unit": "£/week",
            "description": "Average social rent per week (national)",
            "editable": True,
        },
        "social_rent_monthly": {
            "value": 559,
            "source": "EHS 2024-25 (£129/wk × 52/12)",
            "range": [430, 740],
            "unit": "£/month",
            "description": "Average social rent per month (national)",
            "editable": True,
        },
        "private_rent_weekly": {
            "value": 250,
            "source": "EHS 2024-25 national mean (£207/wk outside London)",
            "range": [180, 390],
            "unit": "£/week",
            "description": "Average private rent per week (national)",
            "editable": True,
        },
        "private_rent_monthly": {
            "value": 1083,
            "source": "EHS 2024-25 (£250/wk × 52/12)",
            "range": [780, 1700],
            "unit": "£/month",
            "description": "Average private rent per month (national)",
            "editable": True,
        },
        "council_tax_avg_annual": {
            "value": 1668,
            "source": "GOV.UK 2024-25 (average per dwelling; Band D is £2,171)",
            "range": [1500, 2200],
            "unit": "£/year",
            "description": "Average council tax per dwelling per year",
            "editable": True,
        },
        "council_tax_avg_monthly": {
            "value": 139,
            "source": "GOV.UK 2024-25 (£1,668/12)",
            "range": [125, 185],
            "unit": "£/month",
            "description": "Average council tax per dwelling per month",
            "editable": True,
        },
        # Tenure splits by household type (Census 2021 RM135 + EHS 2024-25)
        "tenure_by_household_type": {
            "value": {
                "lone_parent_dep_children": {"owner": 0.28, "private_rent": 0.30, "social_rent": 0.42},
                "single_under_25":          {"owner": 0.11, "private_rent": 0.69, "social_rent": 0.20},
                "single_25_49":             {"owner": 0.40, "private_rent": 0.35, "social_rent": 0.25},
                "single_50_64":             {"owner": 0.65, "private_rent": 0.15, "social_rent": 0.20},
                "couple_no_children_under_25": {"owner": 0.15, "private_rent": 0.65, "social_rent": 0.20},
                "couple_no_children_25_49": {"owner": 0.65, "private_rent": 0.25, "social_rent": 0.10},
                "couple_no_children_50_64": {"owner": 0.80, "private_rent": 0.08, "social_rent": 0.12},
                "couple_with_children":     {"owner": 0.60, "private_rent": 0.25, "social_rent": 0.15},
            },
            "source": "Census 2021 RM135 + EHS 2024-25. Lone parent social rent: Census 2021 (42% for dep. children).",
            "range": None,
            "unit": "fraction dict",
            "description": "Housing tenure split by household type. Each sums to 1.0.",
            "editable": False,
        },
    },

    # ==========================================================================
    # SERVICE DEMAND PARAMETERS (10 services)
    # ==========================================================================
    "service_demand": {
        "jobcentre_plus": {
            "value": {
                "demand_elasticity": 1.0,
                "lag_months": 0,
                "unit_cost_per_case": 1200,
                "baseline_caseload_thousands": 1500,
                "funding_source": "central_gov",
                "staff_ratio": 120,
            },
            "source": "DWP; direct proportional relationship with unemployment",
            "range": {"demand_elasticity": [0.8, 1.2]},
            "unit": "service params",
            "description": "Jobcentre Plus / DWP work coaches",
            "editable": True,
        },
        "uc_processing": {
            "value": {
                "demand_elasticity": 1.0,
                "lag_months": 0,
                "unit_cost_per_case": 400,
                "baseline_caseload_thousands": 6500,
                "funding_source": "central_gov",
                "staff_ratio": 200,
            },
            "source": "DWP admin data",
            "range": {"demand_elasticity": [0.8, 1.2]},
            "unit": "service params",
            "description": "UC claim processing (DWP)",
            "editable": True,
        },
        "food_banks": {
            "value": {
                "demand_elasticity": 1.5,
                "lag_months": 1,
                "unit_cost_per_case": 150,
                "baseline_caseload_thousands": 3000,
                "funding_source": "voluntary_sector",
                "staff_ratio": 250,
            },
            "source": "Trussell Trust data 2023-24; over-indexed due to 5-week UC wait",
            "range": {"demand_elasticity": [1.0, 2.0]},
            "unit": "service params",
            "description": "Food banks (Trussell Trust + independent)",
            "editable": True,
        },
        "debt_advice": {
            "value": {
                "demand_elasticity": 0.8,
                "lag_months": 3,
                "unit_cost_per_case": 500,
                "baseline_caseload_thousands": 2000,
                "funding_source": "mixed",
                "staff_ratio": 100,
            },
            "source": "Citizens Advice annual stats; StepChange data",
            "range": {"demand_elasticity": [0.5, 1.2]},
            "unit": "service params",
            "description": "Debt advice services (Citizens Advice, StepChange, etc.)",
            "editable": True,
        },
        "mental_health_iapt": {
            "value": {
                "demand_elasticity": 0.6,
                "lag_months": 6,
                "unit_cost_per_case": 1200,
                "baseline_caseload_thousands": 1800,
                "funding_source": "nhs",
                "staff_ratio": 50,
            },
            "source": "Barr et al. 2015; NHS England Talking Therapies data",
            "range": {"demand_elasticity": [0.3, 0.9]},
            "unit": "service params",
            "description": "NHS Talking Therapies (IAPT) for anxiety/depression",
            "editable": True,
        },
        "housing_support": {
            "value": {
                "demand_elasticity": 0.5,
                "lag_months": 6,
                "unit_cost_per_case": 3500,
                "baseline_caseload_thousands": 300,
                "funding_source": "local_gov",
                "staff_ratio": 30,
            },
            "source": "DLUHC homelessness statistics; LA housing teams",
            "range": {"demand_elasticity": [0.3, 0.8]},
            "unit": "service params",
            "description": "Local authority housing/homelessness services",
            "editable": True,
        },
        "childrens_services": {
            "value": {
                "demand_elasticity": 0.3,
                "lag_months": 12,
                "unit_cost_per_case": 10965,
                "baseline_caseload_thousands": 400,
                "funding_source": "local_gov",
                "staff_ratio": 15,
            },
            "source": "DfE Children in Need census; family stress → referral lag",
            "unit_cost_provenance": {
                "source": ("Home Office, The economic and social cost of contact child "
                           "sexual abuse (2021), section 6.4.2, Table 10"),
                "source_value": 8640,
                "source_price_year": "2018/19",
                "deflator_series": "ONS L8GG, financial-year index, March 2026 QNA vintage",
                "deflator_index": {"2018-19": 78.7948, "2024-25": 100.0},
                "deflator_factor": 1.269119,
                "target_base": "2024-25 (2024-equivalent, the provider tab's own base)",
                "note": ("Replaces 8000, which had no cost source. The two unit costs in "
                         "Table 10 are separately derived, from distinct expenditure "
                         "lines, but the populations are not separate: the source states "
                         "that looked-after children are a subset of children in need, "
                         "and that 8,640 is the basic level of safeguarding costed for "
                         "every child in need, with looked-after children additionally "
                         "attracting 45,085. So 8,640 is not a children-in-need-excluding-"
                         "looked-after figure. Applying it as a community-support cost "
                         "per child in need mirrors the source's own additive treatment, "
                         "which is the basis on which it is used here."),
            },
            "range": {"demand_elasticity": [0.15, 0.5]},
            "unit": "service params",
            "description": "Children's social care (local authority)",
            "editable": True,
        },
        "domestic_abuse": {
            "value": {
                "demand_elasticity": 0.4,
                "lag_months": 6,
                "unit_cost_per_case": 2500,
                "baseline_caseload_thousands": 150,
                "funding_source": "mixed",
                "staff_ratio": 25,
            },
            "source": "ONS domestic abuse statistics; SafeLives data",
            "range": {"demand_elasticity": [0.2, 0.6]},
            "unit": "service params",
            "description": "Domestic abuse services (refuges, IDVA, helplines)",
            "editable": True,
        },
        "substance_misuse": {
            "value": {
                "demand_elasticity": 0.3,
                "lag_months": 12,
                "unit_cost_per_case": 4488,
                "baseline_caseload_thousands": 280,
                "funding_source": "local_gov",
                "staff_ratio": 30,
            },
            "source": "OHID NDTMS data; Stuckler & Basu 2013",
            "unit_cost_provenance": {
                "source": ("National Audit Office, Tackling problem drug use, HC 297, "
                           "session 2009-10"),
                "source_value": 3000,
                "source_price_year": "2008-09",
                "deflator_series": "ONS L8GG, financial-year index, March 2026 QNA vintage",
                "deflator_index": {"2008-09": 66.8397, "2024-25": 100.0},
                "deflator_factor": 1.496117,
                "target_base": "2024-25 (2024-equivalent, the provider tab's own base)",
                "note": ("The NAO attribution is the one carried in the technical report "
                         "and preferred over the bibliography's NDTMS claim. The service "
                         "`source` above covers the demand relationship, not the cost. "
                         "SCOPE, AN EXTRAPOLATION: nothing in the source covers alcohol. "
                         "Figure 5 is drug treatment budgets, the corroborating paragraph "
                         "refers to adult drug treatment, and the agency's remit as the "
                         "report states it is treatment for drug dependency in England. "
                         "This parameter is labelled drug and alcohol treatment, so "
                         "applying the figure to a combined population extends it beyond "
                         "the population it was measured on. DENOMINATOR: effective "
                         "treatment is defined at note 2, not note 1, and in three parts: "
                         "adults discharged twelve weeks or more after triage, adults "
                         "still in treatment at twelve weeks, and adults discharged "
                         "within twelve weeks in a planned way. The third limb admits "
                         "people treated for less than twelve weeks, so the shorthand "
                         "'12+ weeks' overstates the treatment intensity the denominator "
                         "represents. ROUNDING: 3,000 is the source's own rounding of "
                         "2,979, so this figure inherits about 0.7 per cent of upward "
                         "rounding from the source. ALTERNATIVE NOT TAKEN: paragraph 18 "
                         "of the same report gives a genuinely costed unit price of 4,900 "
                         "from a treatment outcomes study, a different concept sitting "
                         "1,900 away in the same document. The budget-based figure is "
                         "taken deliberately in preference to it."),
            },
            "range": {"demand_elasticity": [0.15, 0.5]},
            "unit": "service params",
            "description": "Drug and alcohol treatment services",
            "editable": True,
        },
        "gp_additional_visits": {
            "value": {
                "demand_elasticity": 0.4,
                "lag_months": 3,
                "unit_cost_per_case": 215,
                "baseline_caseload_thousands": 5000,
                "funding_source": "nhs",
                "staff_ratio": 300,
            },
            "source": "PHE fingertips (demand relationship); see unit_cost_provenance for the cost",
            "unit_cost_provenance": {
                "source": ("Jones et al. (2024) Unit Costs of Health and Social Care 2023 "
                           "Manual, table 9.4.2, DOI 10.22024/UniKent/01.02.105685"),
                "source_value": 49,
                "source_value_unit": "GBP per consultation",
                "source_price_year": "2022/23",
                "deflator_series": "ONS L8GG, financial-year index, March 2026 QNA vintage",
                "deflator_index": {"2022-23": 91.2996, "2024-25": 100.0},
                "deflator_factor": 1.095295,
                "uprated_per_consultation": 53.6695,
                "visits_per_case": 4,
                "visits_source": None,
                "target_base": "2024-25 (2024-equivalent, the provider tab's own base)",
                "note": ("49 x 1.095295 = 53.6695 per consultation at 2024-25, then x4 "
                         "visits = 214.68, rounded to 215. Replaces 160, which used an "
                         "unsourced GBP 39 rate. The four-visit count has NO SOURCE, which "
                         "is why the cell is classed an assumption however well sourced the "
                         "price is; do not read this value as fully sourced. NOT "
                         "LIKE-FOR-LIKE WITH EARLIER MANUALS: the 49 is priced per "
                         "ten-minute surgery consultation, and the manual's own footnote "
                         "records that previous editions used 9.22 minutes, so the "
                         "ten-minute basis is new to this edition and the figure cannot "
                         "be compared with a per-consultation price from an earlier one."),
            },
            "range": {"demand_elasticity": [0.2, 0.6]},
            "unit": "service params",
            "description": "Additional GP consultations (stress, anxiety, physical health)",
            "editable": True,
        },
    },

    # ==========================================================================
    # SocialNetworks-READY PARAMETERS (for NetLogo/pyNetLogo integration)
    # ==========================================================================
    "abm": {
        "network_effect_multiplier": {
            "value": 1.15,
            "source": "Literature estimate; unemployment spreads through social networks",
            "range": [1.0, 1.30],
            "unit": "multiplier",
            "description": "Peer/neighbourhood effect multiplier for unemployment spread in SocialNetworks",
            "editable": True,
        },
        "service_referral_rate": {
            "value": 0.30,
            "source": "Estimated from DWP/LA data; fraction of claimants referred to additional services",
            "range": [0.15, 0.50],
            "unit": "fraction",
            "description": "Fraction of benefit claimants referred to additional support services",
            "editable": True,
        },
        "intervention_success_rate": {
            "value": 0.45,
            "source": "DWP Work Programme evaluation; ~45% enter employment within 12m",
            "range": [0.30, 0.60],
            "unit": "fraction",
            "description": "Probability that an intervention (job coaching, training) leads to employment",
            "editable": True,
        },
        "intervention_duration_months": {
            "value": 6,
            "source": "DWP Work Programme; typical intervention cycle",
            "range": [3, 12],
            "unit": "months",
            "description": "Average duration of employment support intervention",
            "editable": True,
        },
        "job_search_intensity_decay": {
            "value": 0.95,
            "source": "Krueger & Mueller 2011; search effort declines ~5% per month",
            "range": [0.90, 0.98],
            "unit": "fraction per month",
            "description": "Monthly decay rate of job search intensity",
            "editable": True,
        },
        "scarring_wage_penalty": {
            "value": 0.08,
            "source": "Arulampalam et al. 2001; ~8% wage penalty from unemployment spell",
            "range": [0.04, 0.15],
            "unit": "fraction",
            "description": "Long-run wage penalty (scarring) from an unemployment spell",
            "editable": True,
        },
        "health_deterioration_rate": {
            "value": 0.02,
            "source": "Stuckler & Basu 2013; monthly health score decline during unemployment",
            "range": [0.01, 0.05],
            "unit": "fraction per month",
            "description": "Monthly rate of health deterioration during unemployment",
            "editable": True,
        },
        "social_isolation_factor": {
            "value": 0.10,
            "source": "Estimated; reduced social contact per month of unemployment",
            "range": [0.05, 0.20],
            "unit": "fraction per month",
            "description": "Monthly increase in social isolation during unemployment",
            "editable": True,
        },
        "reemployment_rate_monthly": {
            "value": 0.12,
            "source": "ONS LFS flow data; ~12% of unemployed find work each month",
            "range": [0.08, 0.18],
            "unit": "fraction per month",
            "description": "Monthly probability of finding employment (hazard rate)",
            "editable": True,
        },
        "spatial_mismatch_penalty": {
            "value": 0.15,
            "source": "Manning & Petrongolo 2017; spatial friction in job matching",
            "range": [0.05, 0.25],
            "unit": "fraction",
            "description": "Reduction in job-finding rate due to spatial mismatch (jobs far from home)",
            "editable": True,
        },
    },

    # ==========================================================================
    # REGIONAL PROFILES
    # ==========================================================================
    # Override sets for London and North England. Each key maps to a flat
    # parameter path (e.g. "housing.private_rent_monthly") and the regional
    # value.  Use apply_regional_profile() to swap these in at runtime.
    #
    # Sources (all verified against official publications):
    #   London: ONS LFS Jul-Sep 2024, EHS 2024-25 (Ch.2, Annex Table 2.4),
    #           ONS ASHE 2024 (Table 7), DLUHC council tax 2024-25, DWP HBAI FYE 2023
    #   North England: ONS LFS Jul-Sep 2024, ONS PRMS Oct 2022-Sep 2023 (final),
    #           RSH SDR 2024-25, ONS ASHE 2024 (Table 7), DWP HBAI FYE 2023
    #   "North England" = North East + North West + Yorkshire & Humber
    "regions": {
        "london": {
            "value": {
                # --- Housing costs ---
                "housing.private_rent_monthly":  1700,   # EHS 2024-25 Ch.2: £393/wk mean (= £1,703, rounded)
                "housing.private_rent_weekly":   393,
                "housing.social_rent_monthly":   741,    # EHS 2024-25 Annex Table 2.4: £171/wk mean
                "housing.social_rent_weekly":    171,
                "housing.council_tax_avg_annual": 1400,  # DLUHC 2024-25 Live Tables: London avg per dwelling
                "housing.council_tax_avg_monthly": 117,
                # --- Labour market ---
                "macro.baseline_unemployment_rate": 0.059,  # ONS LFS Jul-Sep 2024: London 5.9%
                "macro.labour_force_millions": 4.9,         # ONS LFS 2024
                "macro.working_age_households_millions": 2.8,
                # --- Earnings ---
                "tax.median_ft_earnings": 47455,    # ONS ASHE 2024 Table 7: London FT median
                "tax.avg_income_tax_per_worker": 8500,  # Author est. scaled to ASHE 2024 London earnings
                "tax.avg_ni_per_worker": 4700,
                "tax.avg_vat_per_worker": 2900,
                # --- Population ---
                "population.baseline_child_poverty_rate": 0.33,  # DWP HBAI FYE 2023: London ~33% AHC
                "population.fraction_with_children": 0.30,
            },
            "source": "ONS LFS Nov 2024, EHS 2024-25, ONS ASHE 2024 Table 7, DLUHC 2024-25, DWP HBAI FYE 2023",
            "range": None,
            "unit": "regional override dict",
            "description": "London regional parameter overrides: higher rents, earnings, child poverty",
            "editable": False,
        },
        "north_england": {
            "value": {
                # --- Housing costs ---
                "housing.private_rent_monthly":  625,    # ONS PRMS Oct 2022-Sep 2023: NE £550+NW £675+Y&H £650 median avg
                "housing.private_rent_weekly":   144,
                "housing.social_rent_monthly":   430,    # RSH SDR 2024-25: NE ~£95/wk, Y&H ~£98/wk, avg ~£99/wk
                "housing.social_rent_weekly":    99,
                "housing.council_tax_avg_annual": 1750,  # DLUHC 2024-25 Live Tables: North avg per dwelling
                "housing.council_tax_avg_monthly": 146,
                # --- Labour market ---
                "macro.baseline_unemployment_rate": 0.055,  # ONS LFS Jul-Sep 2024: NE+NW+Y&H avg ~5.5% (NE was 5.6% in adj. periods)
                "macro.labour_force_millions": 7.2,         # ONS LFS 2024: NE+NW+Y&H combined
                "macro.working_age_households_millions": 4.5,
                # --- Earnings ---
                "tax.median_ft_earnings": 33000,    # ONS ASHE 2024 Table 7: NE £32,960; NW+Y&H est. ~£33-34k; avg ~£33k
                "tax.avg_income_tax_per_worker": 4600,  # Author est. scaled to ASHE 2024 North earnings
                "tax.avg_ni_per_worker": 2900,
                "tax.avg_vat_per_worker": 1900,
                # --- Population ---
                "population.baseline_child_poverty_rate": 0.35,  # DWP HBAI FYE 2023: NE ~38%, NW ~34%, Y&H ~30%; wt avg ~35%
                "population.fraction_with_children": 0.38,
            },
            "source": "ONS LFS Nov 2024, ONS PRMS Dec 2023, RSH SDR 2025, ONS ASHE 2024 Table 7, DWP HBAI FYE 2023",
            "range": None,
            "unit": "regional override dict",
            "description": "North England (NE+NW+Y&H) overrides: lower rents/earnings, higher unemployment",
            "editable": False,
        },
    },
}


# ==============================================================================
# REGIONAL PROFILE HELPERS
# ==============================================================================

# Stash original values so we can reset after a regional run
_ORIGINAL_VALUES = {}


def apply_regional_profile(region_name):
    """
    Apply a regional parameter profile, overriding national defaults.

    Args:
        region_name: "london", "north_england", or "national" (to reset)

    Returns:
        dict of {param_path: new_value} that was applied
    """
    global _ORIGINAL_VALUES

    if region_name == "national":
        # Restore originals
        for path, original in _ORIGINAL_VALUES.items():
            _force_set_param(path, original)
        applied = dict(_ORIGINAL_VALUES)
        _ORIGINAL_VALUES.clear()
        return applied

    if region_name not in PARAMETER_REGISTRY["regions"]:
        available = list(PARAMETER_REGISTRY["regions"].keys())
        raise KeyError(
            f"Region '{region_name}' not found. Available: {available}"
        )

    overrides = PARAMETER_REGISTRY["regions"][region_name]["value"]
    applied = {}

    for path, new_value in overrides.items():
        # Save original if not already saved
        if path not in _ORIGINAL_VALUES:
            try:
                _ORIGINAL_VALUES[path] = get_param(path)
            except KeyError:
                continue
        _force_set_param(path, new_value)
        applied[path] = new_value

    return applied


def _force_set_param(path, value):
    """Set a parameter value bypassing the editable check (for regional overrides)."""
    parts = path.split(".")
    current = PARAMETER_REGISTRY

    for part in parts[:-1]:
        if part not in current:
            return
        current = current[part]

    last = parts[-1]
    if last not in current:
        return

    param = current[last]
    if isinstance(param, dict) and "value" in param:
        param["value"] = value


def get_available_regions():
    """Return list of available regional profiles."""
    return list(PARAMETER_REGISTRY["regions"].keys())


def get_regional_profile(region_name):
    """Return the override dict for a named region."""
    if region_name not in PARAMETER_REGISTRY["regions"]:
        raise KeyError(f"Region '{region_name}' not found.")
    return copy.deepcopy(PARAMETER_REGISTRY["regions"][region_name]["value"])


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_param(path):
    """
    Retrieve a parameter value by dot-separated path.

    Examples:
        get_param("macro.okun_beta")  → 0.4
        get_param("benefits.uc_taper_rate")  → 0.55
        get_param("service_demand.food_banks")  → full service dict

    For nested service params:
        get_param("service_demand.food_banks.demand_elasticity")  → 1.5
    """
    parts = path.split(".")
    current = PARAMETER_REGISTRY

    for part in parts:
        if part not in current:
            raise KeyError(f"Parameter '{path}' not found. Failed at '{part}'.")
        current = current[part]

    # If we landed on a parameter dict with "value", return the value
    if isinstance(current, dict) and "value" in current:
        return current["value"]

    return current


def get_param_info(path):
    """
    Retrieve full parameter metadata (value, source, range, etc.) by path.
    """
    parts = path.split(".")
    current = PARAMETER_REGISTRY

    for part in parts:
        if part not in current:
            raise KeyError(f"Parameter '{path}' not found. Failed at '{part}'.")
        current = current[part]

    if isinstance(current, dict) and "value" in current:
        return copy.deepcopy(current)
    raise KeyError(f"'{path}' is a category, not a parameter. Use get_param() for the value.")


def set_param(path, value):
    """
    Override a parameter value at runtime (for sensitivity analysis).

    Only works for parameters marked as editable.
    """
    parts = path.split(".")
    current = PARAMETER_REGISTRY

    for part in parts[:-1]:
        if part not in current:
            raise KeyError(f"Parameter '{path}' not found.")
        current = current[part]

    last = parts[-1]
    if last not in current:
        raise KeyError(f"Parameter '{path}' not found.")

    param = current[last]
    if isinstance(param, dict) and "value" in param:
        if not param.get("editable", False):
            raise ValueError(f"Parameter '{path}' is not editable.")
        param["value"] = value
    else:
        raise KeyError(f"'{path}' is a category, not a parameter.")


def list_all_params(category=None):
    """
    Print a formatted table of all parameters (or a single category).

    Args:
        category: optional category name (e.g., "macro", "benefits")
    """
    registry = PARAMETER_REGISTRY
    if category:
        if category not in registry:
            raise KeyError(f"Category '{category}' not found.")
        registry = {category: registry[category]}

    count = 0
    for cat_name, cat_params in sorted(registry.items()):
        print(f"\n{'='*80}")
        print(f"  {cat_name.upper()}")
        print(f"{'='*80}")
        for param_name, param_data in sorted(cat_params.items()):
            if not isinstance(param_data, dict) or "value" not in param_data:
                continue
            val = param_data["value"]
            unit = param_data.get("unit", "")
            source = param_data.get("source", "")
            desc = param_data.get("description", "")
            editable = param_data.get("editable", False)

            # Format value display
            if isinstance(val, float) and val < 1:
                val_str = f"{val:.3f}"
            elif isinstance(val, (dict, list)):
                val_str = f"<{type(val).__name__} with {len(val)} entries>"
            else:
                val_str = str(val)

            edit_marker = " [EDITABLE]" if editable else ""
            print(f"\n  {cat_name}.{param_name}{edit_marker}")
            print(f"    Value:  {val_str} {unit}")
            print(f"    Source: {source}")
            if desc:
                print(f"    Desc:   {desc}")
            param_range = param_data.get("range")
            if param_range:
                if isinstance(param_range, list):
                    print(f"    Range:  [{param_range[0]}, {param_range[1]}]")
                elif isinstance(param_range, dict):
                    for k, v in param_range.items():
                        print(f"    Range ({k}): [{v[0]}, {v[1]}]")
            count += 1

    print(f"\n{'─'*80}")
    print(f"Total parameters: {count}")


def export_for_abm():
    """
    Export a flat dict of parameters suitable for NetLogo/pyNetLogo import.

    Returns dict with simple key-value pairs (nested dicts flattened).
    """
    flat = {}

    for cat_name, cat_params in PARAMETER_REGISTRY.items():
        for param_name, param_data in cat_params.items():
            if not isinstance(param_data, dict) or "value" not in param_data:
                continue
            val = param_data["value"]
            key = f"{cat_name}__{param_name}"

            if isinstance(val, (int, float, bool)):
                flat[key] = val
            elif isinstance(val, dict):
                # Flatten nested dicts (e.g., service demand params)
                for sub_key, sub_val in val.items():
                    if isinstance(sub_val, (int, float, bool, str)):
                        flat[f"{key}__{sub_key}"] = sub_val
                    elif isinstance(sub_val, dict):
                        for sub2_key, sub2_val in sub_val.items():
                            if isinstance(sub2_val, (int, float, bool)):
                                flat[f"{key}__{sub_key}__{sub2_key}"] = sub2_val

    return flat


def export_to_json(filepath=None):
    """
    Export the full parameter registry to JSON.

    Args:
        filepath: optional file path. If None, returns JSON string.
    """
    # Convert to JSON-serialisable format
    def _serialise(obj):
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, (int, float, str)):
            return obj
        if isinstance(obj, dict):
            return {str(k): _serialise(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_serialise(i) for i in obj]
        return str(obj)

    data = _serialise(PARAMETER_REGISTRY)

    if filepath:
        # encoding stated and newline fixed to LF: without them Python writes cp1252
        # with CRLF on Windows and UTF-8 with LF elsewhere, so the same registry
        # produced two different files on two platforms.
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2)
        return filepath
    return json.dumps(data, indent=2)


def count_params():
    """Count total number of parameters in the registry."""
    count = 0
    for cat_params in PARAMETER_REGISTRY.values():
        for param_data in cat_params.values():
            if isinstance(param_data, dict) and "value" in param_data:
                count += 1
    return count


# ==============================================================================
# CONVENIENCE: Re-export commonly used parameter dicts for backwards compat
# ==============================================================================

def get_benefit_params():
    """
    Return the BENEFIT_PARAMS dict in the format expected by shock_transmission.py.
    This bridges the new registry with the existing code.
    """
    b = PARAMETER_REGISTRY["benefits"]
    return {
        "jsa": {
            "eligibility_rate": b["jsa_eligibility_rate"]["value"],
            "weekly_rate_25_plus": b["jsa_weekly_rate_25_plus"]["value"],
            "weekly_rate_under_25": b["jsa_weekly_rate_under_25"]["value"],
            "max_duration_weeks": b["jsa_max_duration_weeks"]["value"],
            "take_up_rate": b["jsa_take_up_rate"]["value"],
        },
        "uc": {
            "eligibility_rate": b["uc_eligibility_rate"]["value"],
            "take_up_rate": b["uc_take_up_rate"]["value"],
            "five_week_wait": b["uc_five_week_wait"]["value"],
            "avg_spell_months": b["uc_avg_spell_months"]["value"],
            "monthly_rates": {
                "single_under_25": b["uc_standard_allowance_single_under_25"]["value"],
                "single_25_plus": b["uc_standard_allowance_single_25_plus"]["value"],
                "couple_both_under_25": b["uc_standard_allowance_couple_both_under_25"]["value"],
                "couple_one_25_plus": b["uc_standard_allowance_couple_one_25_plus"]["value"],
            },
            "housing_element_rate": b["uc_housing_element_rate"]["value"],
            "avg_housing_element_monthly": b["uc_avg_housing_element_monthly"]["value"],
        },
        "ctr": {
            "eligibility_rate": b["ctr_eligibility_rate"]["value"],
            "take_up_rate": b["ctr_take_up_rate"]["value"],
            "avg_annual_value": b["ctr_avg_annual_value"]["value"],
        },
        "non_take_up": {
            "overall_rate": b["non_take_up_rate"]["value"],
        },
    }


def get_population_params():
    """Return POPULATION_PARAMS dict for shock_transmission.py."""
    p = PARAMETER_REGISTRY["population"]
    return {
        "avg_household_size": p["avg_household_size"]["value"],
        "fraction_with_children": p["fraction_with_children"]["value"],
        "avg_children_if_any": p["avg_children_if_any"]["value"],
        "partner_fraction": p["partner_fraction"]["value"],
        "poverty_elasticity": p["child_poverty_elasticity"]["value"],
        "baseline_child_poverty_rate": p["baseline_child_poverty_rate"]["value"],
        "total_children_millions": p["total_children_millions"]["value"],
    }


def get_tax_params():
    """Return TAX_PARAMS dict for shock_transmission.py."""
    t = PARAMETER_REGISTRY["tax"]
    return {
        "avg_income_tax_per_worker": t["avg_income_tax_per_worker"]["value"],
        "avg_ni_per_worker": t["avg_ni_per_worker"]["value"],
        "avg_vat_per_worker": t["avg_vat_per_worker"]["value"],
    }


def get_service_demand_elasticities():
    """Return SERVICE_DEMAND_ELASTICITIES dict for shock_transmission.py."""
    sd = PARAMETER_REGISTRY["service_demand"]
    result = {}
    for service_id, param_data in sd.items():
        val = param_data["value"]
        result[service_id] = {
            "description": param_data["description"],
            "demand_elasticity": val["demand_elasticity"],
            "lag_months": val["lag_months"],
            "unit_cost_per_case": val["unit_cost_per_case"],
            "funding_source": val["funding_source"],
            "baseline_caseload_thousands": val["baseline_caseload_thousands"],
        }
    return result


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    print("BENEFITS D2.2 - Parameter Registry")
    print(f"Total parameters: {count_params()}")
    print()
    list_all_params()

    print("\n\n" + "=" * 80)
    print("SocialNetworks EXPORT (flat dict)")
    print("=" * 80)
    abm = export_for_abm()
    for k, v in sorted(abm.items()):
        print(f"  {k}: {v}")
    print(f"\nTotal SocialNetworks-exportable parameters: {len(abm)}")
