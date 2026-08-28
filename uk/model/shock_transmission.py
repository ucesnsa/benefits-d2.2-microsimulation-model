"""
================================================================================
Shock Transmission Module: GDP → Unemployment → Benefits → Service Demand
================================================================================

Author: BENEFITS D2.2 - UCL Data Team IGP
Date: February 2026

Models the full transmission chain from a macroeconomic shock to its impact
on benefit claimants and social service providers:

    GDP shock → Δ unemployment (Okun's Law)
      → Δ benefit claims (UC, JSA, Housing Benefit, Council Tax Support)
        → headcount of affected people (adults, children, by household type)
        → fiscal cost (central gov, local gov, providers)
        → service demand (job centres, mental health, debt advice, food banks, etc.)

Key parameters are sourced from OBR, DWP, and academic literature.
All values use 2024 UK parameters unless otherwise stated.

================================================================================
"""

import copy
import math
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


from parameters import (
    get_param,
    get_benefit_params,
    get_population_params,
    get_tax_params,
    get_service_demand_elasticities,
)

# ==============================================================================
# 1. GDP → UNEMPLOYMENT (Okun's Law for the UK)
# ==============================================================================
#
# Okun's Law: Δu ≈ -β × Δy
#   where Δu = change in unemployment rate (pp)
#         Δy = change in real GDP growth (%)
#         β  = Okun coefficient
#
# Empirical estimates for the UK:
#   - OBR (2023 Fiscal Risks): β ≈ 0.4–0.5
#   - Bank of England (2020): β ≈ 0.35–0.45 for output gap
#   - Ball, Leigh & Loungani (2017 IMF): β ≈ 0.36 for UK
#
# We use β = 0.4 as the central estimate. This means:
#   - A 1% GDP drop → 0.4pp unemployment rise
#   - A 3% GDP drop → 1.2pp unemployment rise
#   - A 5% GDP drop → 2.0pp unemployment rise
#
# For context: during the 2008-09 recession, UK GDP fell ~6% and unemployment
# rose ~3pp (from ~5.2% to ~8.0%), giving an implied β ≈ 0.5.
# During COVID, GDP fell ~11% but furlough limited unemployment rise to ~1.5pp.

# All parameters now read from the centralised registry (parameters.py)
UK_OKUN_COEFFICIENT = get_param("macro.okun_beta")
UK_BASELINE_UNEMPLOYMENT_RATE = get_param("macro.baseline_unemployment_rate")
UK_LABOUR_FORCE_MILLIONS = get_param("macro.labour_force_millions")
UK_WORKING_AGE_HOUSEHOLDS_MILLIONS = get_param("macro.working_age_households_millions")


def gdp_shock_to_unemployment(gdp_change_pct, okun_beta=UK_OKUN_COEFFICIENT):
    """
    Convert a GDP change to an unemployment rate change using Okun's Law.

    Args:
        gdp_change_pct: GDP change as a percentage (negative = contraction).
                        E.g., -3.0 means a 3% GDP drop.
        okun_beta: Okun coefficient (default 0.4 for UK).

    Returns:
        dict with:
            unemployment_change_pp: percentage point change in unemployment
            new_unemployment_rate: projected unemployment rate
            newly_unemployed_thousands: approximate number of newly unemployed people
    """
    # Okun's Law: Δu = -β × Δy
    delta_u_pp = -okun_beta * gdp_change_pct

    new_rate = UK_BASELINE_UNEMPLOYMENT_RATE + (delta_u_pp / 100)
    new_rate = max(new_rate, 0.01)  # Floor at 1%

    newly_unemployed = delta_u_pp / 100 * UK_LABOUR_FORCE_MILLIONS * 1000  # thousands

    return {
        "gdp_change_pct": gdp_change_pct,
        "okun_beta": okun_beta,
        "unemployment_change_pp": round(delta_u_pp, 2),
        "baseline_unemployment_rate": UK_BASELINE_UNEMPLOYMENT_RATE,
        "new_unemployment_rate": round(new_rate, 4),
        "newly_unemployed_thousands": round(newly_unemployed, 1),
    }


# Time profile of unemployment build-up after a GDP shock.
# Unemployment doesn't rise instantly — it lags GDP by 2-4 quarters.
# Source: OBR fiscal risks report; BoE quarterly bulletin analysis.
#
# Quarters after GDP trough → fraction of total unemployment rise realised
UNEMPLOYMENT_TIME_PROFILE = get_param("macro.unemployment_time_profile")


def unemployment_time_path(total_delta_u_pp, quarters=8):
    """
    Generate quarter-by-quarter unemployment path after a shock.

    Args:
        total_delta_u_pp: total unemployment rise in percentage points
        quarters: number of quarters to project

    Returns:
        List of (quarter, delta_u_pp, cumulative_unemployment_rate) tuples
    """
    path = []
    for q in range(quarters + 1):
        fraction = UNEMPLOYMENT_TIME_PROFILE.get(q, max(0.5, 1.0 - 0.04 * (q - 4)))
        delta = total_delta_u_pp * fraction
        rate = UK_BASELINE_UNEMPLOYMENT_RATE + (delta / 100)
        path.append({
            "quarter": q,
            "fraction_realised": fraction,
            "unemployment_change_pp": round(delta, 2),
            "unemployment_rate": round(rate, 4),
            "newly_unemployed_thousands": round(
                delta / 100 * UK_LABOUR_FORCE_MILLIONS * 1000, 1
            ),
        })
    return path


# ==============================================================================
# 2. UNEMPLOYMENT → BENEFIT CLAIMS
# ==============================================================================
#
# When someone loses their job, several things happen:
#
# a) New-style JSA (contribution-based):
#    - Available to those with sufficient NI contributions (2 full years in
#      the last 3 complete tax years)
#    - Not means-tested (partner income/savings irrelevant)
#    - £84.80/week (25+) or £67.20/week (<25) in 2024
#    - Maximum 182 days (6 months)
#    - Estimated ~35% of newly unemployed qualify (many don't have sufficient
#      NI record, especially young/part-time workers)
#
# b) Universal Credit:
#    - Means-tested: depends on household income, savings (<£16k), housing
#    - Standard allowance: £311.68/month (<25 single) to £617.60/month (couple 25+)
#    - Plus child elements, housing element, etc.
#    - 5-week wait before first payment
#    - Take-up rate ~87% of entitled caseload (DWP 2023 estimates)
#    - Average UC spell for unemployment: ~8 months
#
# c) Housing Benefit / UC housing element:
#    - If renting, housing costs element becomes critical
#    - Local Housing Allowance (LHA) rates cap the amount
#    - ~60% of UC claimants receive housing element
#
# d) Council Tax Reduction (local scheme):
#    - Administered by local councils, not DWP
#    - Typically 100% reduction for out-of-work claimants
#    - Average council tax ~£2,065/year (2024-25), so reduction worth ~£2k/year
#
# e) No claim at all:
#    - Some people don't claim benefits they're entitled to
#    - Reasons: stigma, complexity, short expected unemployment spell
#    - Non-take-up higher among: young single men, short-term unemployed,
#      those with working partners

# Benefit routing parameters — now read from the centralised registry
BENEFIT_PARAMS = get_benefit_params()


def estimate_benefit_claims(newly_unemployed_thousands, age_profile=None):
    """
    Estimate the number of new benefit claims and annual cost arising
    from a given increase in unemployment.

    Args:
        newly_unemployed_thousands: number of newly unemployed people (thousands)
        age_profile: optional dict with {"under_25": fraction, "25_plus": fraction}
                     defaults to ONS age distribution of unemployed

    Returns:
        dict with claim counts, costs, and breakdowns
    """
    if age_profile is None:
        age_profile = {"under_25": 0.25, "25_plus": 0.75}  # ONS approx

    n = newly_unemployed_thousands  # thousands
    jsa = BENEFIT_PARAMS["jsa"]
    uc = BENEFIT_PARAMS["uc"]
    ctr = BENEFIT_PARAMS["ctr"]

    # --- JSA claims ---
    jsa_claimants_k = n * jsa["eligibility_rate"] * jsa["take_up_rate"]
    jsa_weekly_avg = (
        age_profile["under_25"] * jsa["weekly_rate_under_25"]
        + age_profile["25_plus"] * jsa["weekly_rate_25_plus"]
    )
    # JSA is max 26 weeks, so annual cost = claimants × weekly × 26
    jsa_annual_cost_m = jsa_claimants_k * jsa_weekly_avg * jsa["max_duration_weeks"] / 1000

    # --- UC claims ---
    uc_claimants_k = n * uc["eligibility_rate"] * uc["take_up_rate"]
    uc_monthly_avg = (
        age_profile["under_25"] * uc["monthly_rates"]["single_under_25"]
        + age_profile["25_plus"] * uc["monthly_rates"]["single_25_plus"]
    )
    # Average spell is 8 months
    uc_standard_annual_m = uc_claimants_k * uc_monthly_avg * uc["avg_spell_months"] / 1000

    # Housing element (subset of UC claimants)
    uc_housing_claimants_k = uc_claimants_k * uc["housing_element_rate"]
    uc_housing_annual_m = (
        uc_housing_claimants_k * uc["avg_housing_element_monthly"] * uc["avg_spell_months"] / 1000
    )

    # --- Council Tax Reduction ---
    # Approximate: newly unemployed households ≈ 0.7 × individuals (some are couples)
    newly_unemployed_hh_k = n * 0.70
    ctr_claimants_k = newly_unemployed_hh_k * ctr["eligibility_rate"] * ctr["take_up_rate"]
    ctr_annual_cost_m = ctr_claimants_k * ctr["avg_annual_value"] / 1000

    # --- Non-claimants ---
    non_claimants_k = n * BENEFIT_PARAMS["non_take_up"]["overall_rate"]

    # --- Totals ---
    total_benefit_cost_m = jsa_annual_cost_m + uc_standard_annual_m + uc_housing_annual_m + ctr_annual_cost_m

    return {
        "newly_unemployed_thousands": round(n, 1),
        "newly_unemployed_households_thousands": round(newly_unemployed_hh_k, 1),

        "jsa_claimants_thousands": round(jsa_claimants_k, 1),
        "jsa_annual_cost_millions": round(jsa_annual_cost_m, 1),

        "uc_claimants_thousands": round(uc_claimants_k, 1),
        "uc_standard_allowance_annual_millions": round(uc_standard_annual_m, 1),
        "uc_housing_element_claimants_thousands": round(uc_housing_claimants_k, 1),
        "uc_housing_element_annual_millions": round(uc_housing_annual_m, 1),
        "uc_total_annual_millions": round(uc_standard_annual_m + uc_housing_annual_m, 1),

        "ctr_claimants_thousands": round(ctr_claimants_k, 1),
        "ctr_annual_cost_millions": round(ctr_annual_cost_m, 1),

        "non_claimants_thousands": round(non_claimants_k, 1),

        "total_new_benefit_cost_millions": round(total_benefit_cost_m, 1),
        "total_new_benefit_cost_billions": round(total_benefit_cost_m / 1000, 2),
    }


# ==============================================================================
# 3. AFFECTED POPULATION HEADCOUNT
# ==============================================================================
#
# Beyond the fiscal cost, we need to count actual people affected.
# Key groups:
#   - Adults who lose their jobs
#   - Their partners (household income drops even if partner stays employed)
#   - Dependent children in affected households
#   - People pushed below the poverty line (60% median income)
#
# Parameters from ONS Labour Force Survey (2024):
#   - Average household size of unemployed: 2.4 people
#   - Average children per unemployed household with children: 1.7
#   - ~35% of newly unemployed households have dependent children
#   - Child poverty rate rises ~2pp per 1pp unemployment rise (IFS estimate)

# Population parameters — from registry
POPULATION_PARAMS = get_population_params()


def estimate_affected_population(newly_unemployed_thousands, unemployment_change_pp):
    """
    Estimate the total population affected by an unemployment shock.

    Args:
        newly_unemployed_thousands: newly unemployed individuals
        unemployment_change_pp: unemployment rate change in percentage points

    Returns:
        dict with headcounts of affected groups
    """
    n = newly_unemployed_thousands
    p = POPULATION_PARAMS

    # Direct: newly unemployed adults
    adults_affected_k = n

    # Partners affected (not unemployed themselves, but household income drops)
    partners_affected_k = n * p["partner_fraction"]

    # Children in affected households
    hh_with_children_k = n * 0.70 * p["fraction_with_children"]  # 0.70 = individual→household
    children_affected_k = hh_with_children_k * p["avg_children_if_any"]

    # Total people in affected households
    total_affected_k = adults_affected_k + partners_affected_k + children_affected_k

    # Additional children pushed into poverty
    additional_child_poverty_pp = unemployment_change_pp * p["poverty_elasticity"]
    additional_children_in_poverty_k = (
        additional_child_poverty_pp / 100 * p["total_children_millions"] * 1000
    )

    return {
        "newly_unemployed_adults_thousands": round(adults_affected_k, 1),
        "partners_affected_thousands": round(partners_affected_k, 1),
        "children_in_affected_households_thousands": round(children_affected_k, 1),
        "total_people_in_affected_households_thousands": round(total_affected_k, 1),
        "households_with_children_affected_thousands": round(hh_with_children_k, 1),

        "additional_child_poverty_pp": round(additional_child_poverty_pp, 2),
        "additional_children_in_poverty_thousands": round(additional_children_in_poverty_k, 1),
        "new_child_poverty_rate": round(
            p["baseline_child_poverty_rate"] + additional_child_poverty_pp / 100, 3
        ),
    }


# ==============================================================================
# 4. SERVICE DEMAND MODEL
# ==============================================================================
#
# Unemployment doesn't just create benefit claims — it creates demand on a wide
# range of social services. The transmission mechanisms have different lags and
# elasticities.
#
# Sources:
#   - Barr et al. (2015) "Suicides associated with the 2008-10 recession in England"
#   - Stuckler & Basu (2013) "The Body Economic"
#   - Citizen's Advice annual statistics
#   - Trussell Trust data
#   - Public Health England / OHID fingertips data
#   - JRF poverty reports
#
# The demand elasticity represents: for each 1pp rise in unemployment,
# what % increase in demand does this service see?

# Service demand elasticities — from registry
SERVICE_DEMAND_ELASTICITIES = get_service_demand_elasticities()


def estimate_service_demand(unemployment_change_pp, detailed=True):
    """
    Estimate the additional demand on social services from an unemployment shock.

    Args:
        unemployment_change_pp: percentage point change in unemployment rate
        detailed: if True, return per-service breakdown

    Returns:
        dict with service demand estimates and costs
    """
    results = {}
    total_additional_cost_m = 0

    for service_id, params in SERVICE_DEMAND_ELASTICITIES.items():
        # Additional caseload = baseline × elasticity × (Δu / baseline_u) × scaling
        # Simplified: Δ demand = elasticity × Δu_pp / baseline_u × baseline_caseload
        pct_increase = params["demand_elasticity"] * (
            unemployment_change_pp / (UK_BASELINE_UNEMPLOYMENT_RATE * 100)
        )
        additional_cases_k = params["baseline_caseload_thousands"] * pct_increase
        additional_cost_m = additional_cases_k * params["unit_cost_per_case"] / 1000

        total_additional_cost_m += additional_cost_m

        if detailed:
            results[service_id] = {
                "description": params["description"],
                "pct_demand_increase": round(pct_increase * 100, 1),
                "additional_cases_thousands": round(additional_cases_k, 1),
                "additional_annual_cost_millions": round(additional_cost_m, 1),
                "lag_months": params["lag_months"],
                "funding_source": params["funding_source"],
            }

    # Aggregate by funding source
    cost_by_source = {
        "central_gov": 0, "local_gov": 0, "nhs": 0,
        "voluntary_sector": 0, "mixed": 0,
    }
    for service_id, params in SERVICE_DEMAND_ELASTICITIES.items():
        pct_increase = params["demand_elasticity"] * (
            unemployment_change_pp / (UK_BASELINE_UNEMPLOYMENT_RATE * 100)
        )
        additional_cost_m = (
            params["baseline_caseload_thousands"] * pct_increase
            * params["unit_cost_per_case"] / 1000
        )
        cost_by_source[params["funding_source"]] += additional_cost_m

    results["_summary"] = {
        "unemployment_change_pp": unemployment_change_pp,
        "total_additional_service_cost_millions": round(total_additional_cost_m, 1),
        "total_additional_service_cost_billions": round(total_additional_cost_m / 1000, 2),
        "cost_by_funding_source_millions": {
            k: round(v, 1) for k, v in cost_by_source.items()
        },
    }

    return results


# ==============================================================================
# 5. FISCAL IMPACT DECOMPOSITION
# ==============================================================================
#
# Total fiscal impact of an unemployment shock has multiple components at
# different levels of government:
#
# Central government:
#   (+) UC spending (standard allowance + housing + child elements)
#   (+) JSA spending
#   (+) Additional DWP admin costs
#   (-) Lost income tax revenue
#   (-) Lost NI contributions
#   (-) Lost VAT (reduced consumption, indirect)
#
# Local government:
#   (+) Council Tax Reduction costs
#   (+) Housing/homelessness services
#   (+) Children's services
#   (+) Substance misuse treatment
#   (-) Lost council tax revenue (from CTR)
#
# NHS:
#   (+) Mental health treatment
#   (+) Additional GP visits
#
# Voluntary sector:
#   (+) Food bank costs
#   (+) Debt advice (part-funded by MaPS)
#   (+) Domestic abuse services (part-funded)

# Lost tax revenue parameters — from registry
TAX_PARAMS = get_tax_params()


def full_fiscal_impact(gdp_change_pct, okun_beta=UK_OKUN_COEFFICIENT):
    """
    Compute the complete fiscal impact chain from a GDP shock.

    Args:
        gdp_change_pct: GDP change (e.g., -3.0 for a 3% contraction)
        okun_beta: Okun coefficient

    Returns:
        Comprehensive dict with all layers of impact
    """
    # Step 1: GDP → unemployment
    macro = gdp_shock_to_unemployment(gdp_change_pct, okun_beta)

    # Step 2: Unemployment → benefit claims
    benefits = estimate_benefit_claims(macro["newly_unemployed_thousands"])

    # Step 3: Affected population headcount
    population = estimate_affected_population(
        macro["newly_unemployed_thousands"],
        macro["unemployment_change_pp"],
    )

    # Step 4: Service demand
    services = estimate_service_demand(macro["unemployment_change_pp"])

    # Step 5: Lost tax revenue
    n_k = macro["newly_unemployed_thousands"]
    lost_income_tax_m = n_k * TAX_PARAMS["avg_income_tax_per_worker"] / 1000
    lost_ni_m = n_k * TAX_PARAMS["avg_ni_per_worker"] / 1000
    lost_vat_m = n_k * TAX_PARAMS["avg_vat_per_worker"] / 1000
    total_lost_tax_m = lost_income_tax_m + lost_ni_m + lost_vat_m

    # Step 6: Aggregate fiscal position
    total_additional_spending_m = (
        benefits["total_new_benefit_cost_millions"]
        + services["_summary"]["total_additional_service_cost_millions"]
    )
    total_fiscal_cost_m = total_additional_spending_m + total_lost_tax_m

    # Decompose by level of government
    central_gov_cost_m = (
        benefits["jsa_annual_cost_millions"]
        + benefits["uc_total_annual_millions"]
        + lost_income_tax_m
        + lost_ni_m
        + lost_vat_m
        + services["_summary"]["cost_by_funding_source_millions"]["central_gov"]
    )
    local_gov_cost_m = (
        benefits["ctr_annual_cost_millions"]
        + services["_summary"]["cost_by_funding_source_millions"]["local_gov"]
    )
    nhs_cost_m = services["_summary"]["cost_by_funding_source_millions"]["nhs"]
    voluntary_cost_m = (
        services["_summary"]["cost_by_funding_source_millions"]["voluntary_sector"]
        + services["_summary"]["cost_by_funding_source_millions"]["mixed"]
    )

    fiscal = {
        "lost_income_tax_millions": round(lost_income_tax_m, 1),
        "lost_ni_millions": round(lost_ni_m, 1),
        "lost_vat_millions": round(lost_vat_m, 1),
        "total_lost_tax_revenue_millions": round(total_lost_tax_m, 1),
        "total_additional_benefit_spending_millions": benefits["total_new_benefit_cost_millions"],
        "total_additional_service_cost_millions": services["_summary"]["total_additional_service_cost_millions"],
        "total_fiscal_cost_millions": round(total_fiscal_cost_m, 1),
        "total_fiscal_cost_billions": round(total_fiscal_cost_m / 1000, 2),
        "cost_by_level": {
            "central_government_millions": round(central_gov_cost_m, 1),
            "local_government_millions": round(local_gov_cost_m, 1),
            "nhs_millions": round(nhs_cost_m, 1),
            "voluntary_sector_millions": round(voluntary_cost_m, 1),
        },
    }

    return {
        "macro": macro,
        "benefits": benefits,
        "population": population,
        "services": services,
        "fiscal": fiscal,
    }


# ==============================================================================
# 5b. CALIBRATE BENEFIT PARAMS FROM POLICYENGINE ARCHETYPE RESULTS
# ==============================================================================

def calibrate_benefit_params_from_archetypes(archetype_results_df):
    """
    Extract average benefit amounts per unemployed archetype from PolicyEngine
    results, replacing hardcoded BENEFIT_PARAMS with micro-founded values.

    This bridges PolicyEngine's archetype-level output with the macro
    transmission model, making the two consistent.

    Args:
        archetype_results_df: DataFrame of archetype-level results with columns
            including 'universal_credit', 'uc_standard_allowance',
            'uc_housing_element', 'household_benefits', 'weight',
            'employment' or similar indicator of employment status.

    Returns:
        dict with calibrated benefit parameters:
            avg_uc_monthly: average UC per claimant (£/month)
            avg_uc_housing_monthly: average UC housing element (£/month)
            avg_benefits_monthly: average total benefits per household (£/month)
            uc_housing_fraction: fraction receiving housing element
            poverty_rate: fraction of unemployed in poverty
    """
    df = archetype_results_df

    # Filter to unemployed archetypes (those with _SHOCKED suffix or zero employment income)
    unemployed_mask = (
        df["id"].str.contains("_SHOCKED|_U_|_U$|_N_|_N$", regex=True)
        | (df.get("employment_income", 0) == 0)
    )
    unemp_df = df[unemployed_mask]

    if len(unemp_df) == 0:
        return None

    total_weight = unemp_df["weight"].sum()
    if total_weight == 0:
        return None

    # Weighted averages
    def _wavg(col):
        if col not in unemp_df.columns:
            return 0.0
        return (unemp_df[col] * unemp_df["weight"]).sum() / total_weight

    avg_uc = _wavg("universal_credit")
    avg_uc_standard = _wavg("uc_standard_allowance")
    avg_uc_housing = _wavg("uc_housing_element")
    avg_uc_child = _wavg("uc_child_element")
    avg_benefits = _wavg("household_benefits")
    avg_housing_benefit = _wavg("housing_benefit")

    # Fraction receiving housing element (non-zero)
    if "uc_housing_element" in unemp_df.columns:
        housing_weight = unemp_df.loc[unemp_df["uc_housing_element"] > 0, "weight"].sum()
        uc_housing_fraction = housing_weight / total_weight if total_weight > 0 else 0
    else:
        uc_housing_fraction = 0

    # Poverty rate among unemployed
    if "in_poverty_bhc" in unemp_df.columns:
        poverty_weight = unemp_df.loc[unemp_df["in_poverty_bhc"] == True, "weight"].sum()
        poverty_rate = poverty_weight / total_weight if total_weight > 0 else 0
    else:
        poverty_rate = None

    calibrated = {
        "avg_uc_annual": round(avg_uc, 2),
        "avg_uc_monthly": round(avg_uc / 12, 2),
        "avg_uc_standard_annual": round(avg_uc_standard, 2),
        "avg_uc_housing_annual": round(avg_uc_housing, 2),
        "avg_uc_child_annual": round(avg_uc_child, 2),
        "avg_benefits_annual": round(avg_benefits, 2),
        "avg_benefits_monthly": round(avg_benefits / 12, 2),
        "avg_housing_benefit_annual": round(avg_housing_benefit, 2),
        "uc_housing_fraction": round(uc_housing_fraction, 3),
        "poverty_rate_unemployed": round(poverty_rate, 3) if poverty_rate is not None else None,
        "sample_size_archetypes": len(unemp_df),
        "total_weight_thousands": round(total_weight, 1),
    }

    return calibrated


# ==============================================================================
# 6. APPLY SHOCK TO ARCHETYPES (enhanced version)
# ==============================================================================

def apply_gdp_shock_to_archetypes(archetypes, gdp_change_pct, okun_beta=UK_OKUN_COEFFICIENT):
    """
    Apply a GDP shock to archetypes using Okun's Law, returning both the
    shocked archetype population AND the transmission analysis.

    This replaces the direct shock_pp approach with a macro-founded mechanism.

    Args:
        archetypes: list of archetype dicts
        gdp_change_pct: GDP change (negative = contraction)
        okun_beta: Okun coefficient

    Returns:
        (shocked_archetypes, transmission_report) tuple
    """
    macro = gdp_shock_to_unemployment(gdp_change_pct, okun_beta)
    shock_pp = macro["unemployment_change_pp"] / 100  # Convert to fraction

    if shock_pp <= 0:
        return archetypes, {"macro": macro, "shock_applied_pp": 0}

    shocked = copy.deepcopy(archetypes)
    new_unemployed = []
    total_weight_transferred = 0

    for arch in shocked:
        if arch["employment"] in ("unemployed", "neither"):
            continue

        weight_lost = arch["weight"] * shock_pp
        arch["weight"] -= weight_lost
        total_weight_transferred += weight_lost

        # Create unemployed version
        unemp = copy.deepcopy(arch)
        unemp["id"] = arch["id"] + "_SHOCKED"
        unemp["label"] = arch["label"] + " (GDP shock → unemployed)"
        unemp["weight"] = weight_lost

        if arch["household_type"] == "single":
            unemp["employment"] = "unemployed"
            unemp["earnings"] = 0
        else:
            if arch["employment"] == "both":
                unemp["employment"] = "one"
                unemp["earnings"] = [0, arch["earnings"][1]]
            elif arch["employment"] == "one":
                unemp["employment"] = "neither"
                unemp["earnings"] = [0, 0]

        new_unemployed.append(unemp)

    shocked.extend(new_unemployed)

    # Count children in affected households
    children_affected = sum(
        a.get("num_children", 0) * a["weight"]
        for a in new_unemployed
    )

    report = {
        "macro": macro,
        "shock_applied_pp": round(shock_pp * 100, 2),
        "weight_transferred_thousands": round(total_weight_transferred, 1),
        "new_unemployed_archetypes": len(new_unemployed),
        "children_in_affected_households_thousands": round(children_affected, 1),
    }

    return shocked, report


# ==============================================================================
# MAIN: print example analysis
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SHOCK TRANSMISSION ANALYSIS")
    print("GDP Drop → Unemployment → Benefits → Service Demand → Fiscal Cost")
    print("=" * 70)

    for gdp_drop in [-1.0, -3.0, -5.0]:
        print(f"\n{'='*70}")
        print(f"SCENARIO: GDP drops {abs(gdp_drop):.0f}%")
        print(f"{'='*70}")

        result = full_fiscal_impact(gdp_drop)

        m = result["macro"]
        print(f"\n  MACRO TRANSMISSION (Okun's Law, β={m['okun_beta']})")
        print(f"    GDP change:              {m['gdp_change_pct']:+.1f}%")
        print(f"    Unemployment change:     +{m['unemployment_change_pp']:.2f}pp")
        print(f"    New unemployment rate:   {m['new_unemployment_rate']*100:.1f}%")
        print(f"    Newly unemployed:        {m['newly_unemployed_thousands']:.0f}k people")

        b = result["benefits"]
        print(f"\n  BENEFIT CLAIMS")
        print(f"    New JSA claimants:       {b['jsa_claimants_thousands']:.0f}k")
        print(f"    New UC claimants:        {b['uc_claimants_thousands']:.0f}k")
        print(f"    UC housing element:      {b['uc_housing_element_claimants_thousands']:.0f}k")
        print(f"    Council Tax Reduction:   {b['ctr_claimants_thousands']:.0f}k")
        print(f"    Non-claimants:           {b['non_claimants_thousands']:.0f}k")
        print(f"    Total new benefit cost:  £{b['total_new_benefit_cost_billions']:.2f}bn/year")

        p = result["population"]
        print(f"\n  AFFECTED POPULATION")
        print(f"    Adults losing jobs:      {p['newly_unemployed_adults_thousands']:.0f}k")
        print(f"    Partners affected:       {p['partners_affected_thousands']:.0f}k")
        print(f"    Children affected:       {p['children_in_affected_households_thousands']:.0f}k")
        print(f"    Total people affected:   {p['total_people_in_affected_households_thousands']:.0f}k")
        print(f"    Additional child poverty: +{p['additional_child_poverty_pp']:.1f}pp "
              f"({p['additional_children_in_poverty_thousands']:.0f}k children)")
        print(f"    New child poverty rate:  {p['new_child_poverty_rate']*100:.1f}%")

        s = result["services"]
        print(f"\n  SERVICE DEMAND")
        for sid, sdata in s.items():
            if sid.startswith("_"):
                continue
            print(f"    {sdata['description']:<55} "
                  f"+{sdata['pct_demand_increase']:5.1f}%  "
                  f"+{sdata['additional_cases_thousands']:6.0f}k cases  "
                  f"£{sdata['additional_annual_cost_millions']:7.0f}m  "
                  f"(lag: {sdata['lag_months']}m)")

        f = result["fiscal"]
        print(f"\n  FISCAL IMPACT")
        print(f"    Lost income tax:         £{f['lost_income_tax_millions']:,.0f}m")
        print(f"    Lost NI contributions:   £{f['lost_ni_millions']:,.0f}m")
        print(f"    Lost VAT (indirect):     £{f['lost_vat_millions']:,.0f}m")
        print(f"    Additional benefits:     £{f['total_additional_benefit_spending_millions']:,.0f}m")
        print(f"    Additional services:     £{f['total_additional_service_cost_millions']:,.0f}m")
        print(f"    ─────────────────────────────────────────")
        print(f"    TOTAL FISCAL COST:       £{f['total_fiscal_cost_billions']:.2f}bn")
        print(f"      Central government:    £{f['cost_by_level']['central_government_millions']:,.0f}m")
        print(f"      Local government:      £{f['cost_by_level']['local_government_millions']:,.0f}m")
        print(f"      NHS:                   £{f['cost_by_level']['nhs_millions']:,.0f}m")
        print(f"      Voluntary sector:      £{f['cost_by_level']['voluntary_sector_millions']:,.0f}m")

    # Time profile example
    print(f"\n\n{'='*70}")
    print("UNEMPLOYMENT TIME PROFILE: 3% GDP drop")
    print("='*70")
    macro = gdp_shock_to_unemployment(-3.0)
    path = unemployment_time_path(macro["unemployment_change_pp"])
    print(f"\n  Quarter  |  Fraction  |  Δ Unemployment  |  Rate  |  Newly Unemp")
    print(f"  ─────────┼────────────┼──────────────────┼────────┼─────────────")
    for step in path:
        print(f"    Q+{step['quarter']:<5} |   {step['fraction_realised']:.0%}     |"
              f"    +{step['unemployment_change_pp']:.2f}pp       |"
              f"  {step['unemployment_rate']*100:.1f}%  |"
              f"    {step['newly_unemployed_thousands']:.0f}k")
