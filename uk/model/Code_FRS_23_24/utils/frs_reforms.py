"""
Policy reform modifiers for the FRS 2023-24 microsimulation pipeline.

Mirrors the BENEFITS D2.2 reform catalogue but targets the 2024
simulation period used throughout Code_FRS_23_24.

Usage:
    from Code_FRS_23_24.utils.frs_reforms import get_reform, REFORM_CATALOGUE
"""

# ==============================================================================
# SIMULATION PERIOD — single source of truth
# ==============================================================================

_PE_DATE = "2023-01-01"
_PE_YEAR_PERIOD = "year:2023:1"

# ==============================================================================
# CANONICAL UC TAKE-UP CALIBRATION
# ==============================================================================
# Universal Credit take-up is calibrated to the DWP 2023-24 UC expenditure
# outturn (~£51.2bn), NOT the PolicyEngine default of 0.55. At 0.55 the modelled
# baseline UC is ~£37.8bn (full entitlement ~£69.5bn); 0.731 aligns the modelled
# baseline UC to the outturn (~£51.1bn, residual ~-£0.1bn). This is the canonical
# baseline assumption, applied to the baseline AND every scenario in step 07.
# UC alone is calibrated: HB / Pension Credit / Child Benefit / tax-credit gaps
# are scope/legacy, not take-up, and are left as-is.
# See docs/uc_takeup_calibration.md.
CANONICAL_UC_TAKEUP_RATE = 0.731


# ==============================================================================
# REFORM MODIFIER BUILDERS
# ==============================================================================

def _make_uc_standard_allowance_modifier(multiplier):
    """Scale all UC standard allowance rates by a multiplier."""
    def modifier(sim):
        p = sim.tax_benefit_system.parameters
        sa = p.gov.dwp.universal_credit.standard_allowance.amount
        for rate_name in ["SINGLE_YOUNG", "SINGLE_OLD", "COUPLE_YOUNG", "COUPLE_OLD"]:
            param = getattr(sa, rate_name)
            base_value = param(_PE_DATE)
            param.update(period=_PE_YEAR_PERIOD, value=round(base_value * multiplier, 2))
    return modifier


def _make_uc_standard_allowance_flat_modifier(weekly_increase):
    """Add a flat weekly amount to UC standard allowance (e.g. +£25/week COVID uplift)."""
    monthly_increase = round(weekly_increase * 52 / 12, 2)
    def modifier(sim):
        p = sim.tax_benefit_system.parameters
        sa = p.gov.dwp.universal_credit.standard_allowance.amount
        for rate_name in ["SINGLE_YOUNG", "SINGLE_OLD", "COUPLE_YOUNG", "COUPLE_OLD"]:
            param = getattr(sa, rate_name)
            base_value = param(_PE_DATE)
            param.update(period=_PE_YEAR_PERIOD, value=round(base_value + monthly_increase, 2))
    return modifier


def _make_uc_taper_modifier(new_taper_rate):
    """Set the UC taper rate to a specific value."""
    def modifier(sim):
        p = sim.tax_benefit_system.parameters
        taper = p.gov.dwp.universal_credit.means_test.reduction_rate
        taper.update(period=_PE_YEAR_PERIOD, value=new_taper_rate)
    return modifier


def _make_uc_work_allowance_modifier(multiplier):
    """Scale UC work allowances by a multiplier."""
    def modifier(sim):
        p = sim.tax_benefit_system.parameters
        wa = p.gov.dwp.universal_credit.means_test.work_allowance
        for wa_type in ["with_housing", "without_housing"]:
            param = getattr(wa, wa_type, None)
            if param is not None:
                base_value = param(_PE_DATE)
                param.update(period=_PE_YEAR_PERIOD, value=round(base_value * multiplier, 2))
    return modifier


def make_uc_takeup_modifier(rate: float = CANONICAL_UC_TAKEUP_RATE):
    """Set the UC take-up rate (canonical: calibrated to the DWP UC outturn).

    Public because step 07 applies it to the baseline and every scenario, so the
    whole grid shares one calibrated take-up assumption.
    """
    def modifier(sim):
        p = sim.tax_benefit_system.parameters
        p.gov.dwp.universal_credit.takeup_rate.update(period=_PE_YEAR_PERIOD, value=rate)
    return modifier


def compose_modifiers(*modifiers):
    """Combine simulation modifiers into one (applied in order); None is skipped."""
    mods = [m for m in modifiers if m is not None]
    if not mods:
        return None

    def modifier(sim):
        for m in mods:
            m(sim)

    return modifier


def _make_uc_remove_two_child_limit_modifier():
    """Remove the two-child limit on UC child element.

    Current PolicyEngine UK parameter path (verified against upstream repo):
        gov.dwp.universal_credit.elements.child.limit.child_count
    The upstream baseline sets this to 2 (the limit). PE's built-in
    `repeal_two_child_limit` Scenario only applies from 2026 onwards, so
    for our 2024 simulation we have to override explicitly.
    """
    def modifier(sim):
        p = sim.tax_benefit_system.parameters
        limit = p.gov.dwp.universal_credit.elements.child.limit.child_count
        limit.update(period=_PE_YEAR_PERIOD, value=99)
    return modifier


def _make_personal_allowance_modifier(new_amount):
    """Set the income tax personal allowance to a specific value."""
    def modifier(sim):
        p = sim.tax_benefit_system.parameters
        pa = p.gov.hmrc.income_tax.allowances.personal_allowance.amount
        pa.update(period=_PE_YEAR_PERIOD, value=new_amount)
    return modifier


def _make_ni_threshold_modifier(change_amount_annual):
    """Adjust the primary NI threshold by a given annual amount."""
    def modifier(sim):
        p = sim.tax_benefit_system.parameters
        try:
            pt = p.gov.hmrc.national_insurance.class_1.thresholds.primary_threshold
            base_value = pt(_PE_DATE)
            weekly_change = change_amount_annual / 52
            pt.update(period=_PE_YEAR_PERIOD, value=round(base_value + weekly_change, 2))
        except Exception:
            pass
    return modifier


def _make_freeze_thresholds_modifier():
    """Freeze income tax and NI thresholds (fiscal drag). No-op at 2023."""
    def modifier(sim):
        pass
    return modifier


def _make_cb_remove_hicbc_modifier():
    """Remove the High Income Child Benefit Charge entirely."""
    def modifier(sim):
        p = sim.tax_benefit_system.parameters
        try:
            hitc = p.gov.hmrc.income_tax.charges.CB_HITC
            hitc.phase_out_start.update(period=_PE_YEAR_PERIOD, value=1_000_000)
        except Exception:
            pass
    return modifier

def _make_cb_rate_modifier(multiplier):
    """Scale child benefit rates by a multiplier."""
    def modifier(sim):
        p = sim.tax_benefit_system.parameters
        try:
            cb = p.gov.hmrc.child_benefit.amount
            for rate_name in ["eldest", "additional"]:
                param = getattr(cb, rate_name, None)
                if param is not None:
                    base_value = param(_PE_DATE)
                    param.update(period=_PE_YEAR_PERIOD, value=round(base_value * multiplier, 2))
        except Exception:
            pass
    return modifier


def _make_combined_modifier(*modifiers):
    """Combine multiple modifiers into one."""
    def combined(sim):
        for mod in modifiers:
            mod(sim)
    return combined


# ==============================================================================
# REFORM CATALOGUE
# ==============================================================================

REFORM_CATALOGUE = {
    "uc_taper_45": {
        "name": "UC Taper Rate → 45%",
        "category": "UC",
        "direction": "expansionary",
        "estimated_cost_bn": 3.5,
        "modifier": _make_uc_taper_modifier(0.45),
    },
    "uc_taper_65": {
        "name": "UC Taper Rate → 65%",
        "category": "UC",
        "direction": "contractionary",
        "estimated_cost_bn": -2.5,
        "modifier": _make_uc_taper_modifier(0.65),
    },
    "uc_work_allowance_up_20": {
        "name": "UC Work Allowance +20%",
        "category": "UC",
        "direction": "expansionary",
        "estimated_cost_bn": 1.8,
        "modifier": _make_uc_work_allowance_modifier(1.20),
    },
    "uc_remove_two_child_limit": {
        "name": "Remove UC Two-Child Limit",
        "category": "UC",
        "direction": "expansionary",
        "estimated_cost_bn": 1.3,
        "modifier": _make_uc_remove_two_child_limit_modifier(),
    },
    "uc_standard_up_10": {
        "name": "UC Standard Allowance +10%",
        "category": "UC",
        "direction": "expansionary",
        "estimated_cost_bn": 2.5,
        "modifier": _make_uc_standard_allowance_modifier(1.10),
    },
    "uc_standard_down_10": {
        "name": "UC Standard Allowance -10%",
        "category": "UC",
        "direction": "contractionary",
        "estimated_cost_bn": -2.5,
        "modifier": _make_uc_standard_allowance_modifier(0.90),
    },
    "raise_personal_allowance": {
        "name": "Personal Allowance → £15,000",
        "category": "Tax",
        "direction": "expansionary",
        "estimated_cost_bn": 5.5,
        "modifier": _make_personal_allowance_modifier(15000),
    },
    "lower_ni_threshold": {
        "name": "NI Primary Threshold -£1,000",
        "category": "Tax",
        "direction": "contractionary",
        "estimated_cost_bn": -3.0,
        "modifier": _make_ni_threshold_modifier(-1000),
    },
    "freeze_all_thresholds": {
        "name": "Freeze All Tax/NI Thresholds",
        "category": "Tax",
        "direction": "contractionary",
        "estimated_cost_bn": -2.0,
        "modifier": _make_freeze_thresholds_modifier(),
    },
    "cb_remove_hicbc": {
        "name": "Remove High Income Child Benefit Charge",
        "category": "Child Benefit",
        "direction": "expansionary",
        "estimated_cost_bn": 1.8,
        "modifier": _make_cb_remove_hicbc_modifier(),
    },
    "cb_increase_10pct": {
        "name": "Child Benefit +10%",
        "category": "Child Benefit",
        "direction": "expansionary",
        "estimated_cost_bn": 1.2,
        "modifier": _make_cb_rate_modifier(1.10),
    },
    "gdp_minus_3_plus_uc_boost": {
        "name": "GDP -3% + UC +£25/week (COVID-style)",
        "category": "Combined",
        "direction": "combined",
        "estimated_cost_bn": 15.0,
        "modifier": _make_uc_standard_allowance_flat_modifier(25),
        "gdp_change_pct": -3.0,
    },
    "gdp_minus_3_plus_tax_cut": {
        "name": "GDP -3% + Raise Personal Allowance",
        "category": "Combined",
        "direction": "combined",
        "estimated_cost_bn": 14.5,
        "modifier": _make_personal_allowance_modifier(15000),
        "gdp_change_pct": -3.0,
    },

}


# ==============================================================================
# PUBLIC API
# ==============================================================================

def get_reform(name: str) -> dict:
    """Get a reform by name."""
    if name not in REFORM_CATALOGUE:
        available = ", ".join(sorted(REFORM_CATALOGUE.keys()))
        raise KeyError(f"Reform '{name}' not found. Available: {available}")
    return REFORM_CATALOGUE[name]


def get_reform_names(category: str = None) -> list:
    """Return list of reform ids, optionally filtered by category."""
    if category:
        return [k for k, v in REFORM_CATALOGUE.items() if v["category"] == category]
    return list(REFORM_CATALOGUE.keys())
