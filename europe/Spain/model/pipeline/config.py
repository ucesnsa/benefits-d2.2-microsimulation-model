"""
config.py -- per-country configuration for the BENEFITS D2.2 EU synthetic build.

>>> DUAL-USE. The reform PROFILES here (levers, magnitudes, constants) are SHARED and are
also read by the REAL surface build (build_grid.py). Only the dataset_id '*_training_data'
fields and the build.py orchestration drive the SYNTHETIC validation floor. The committed
real dial surfaces run on the EU-SILC data -- see surface_provenance.json.

One pipeline, parameterised by country. Each profile carries the system year, the
training dataset id, and the reform set (constant names, magnitudes, transforms,
and documented substitutions). Sizes are uniform across countries and held here,
not in code. All amounts are read live from the model and scaled; the literals
below are reform MAGNITUDES and lever identifiers, not policy values.

Reform lever types:
  const_scale       multiply the named constant(s) by `factor` (constantsToOverwrite)
  rate_delta        add `delta` to the named rate constant(s) (constantsToOverwrite)
  param_mutate_scale multiply matching schedule amount parameters by `factor`
                    (in-memory mutation, restored after the run; used where the
                    instrument exists but is not exposed as a scalar constant)
  income_scale      multiply input income variables by `factor` before the run
  unemployment      flip employed individuals to unemployed to raise the
                    unemployment rate by `pp` percentage points, before the run
"""

SCENARIOS = [
    "baseline",
    "min_income_up",
    "child_benefit_up",
    "pit_give",
    "gdp_shock",
    "unemployment_shock",
]

# Expected sign of the weighted disposable-income change versus baseline, at each
# profile's DEFAULT magnitude (the literals near the top of this file). It is not a
# property of the dial alone once a dial runs both ways: use expected_sign() below,
# which takes the magnitude into account.
EXPECTED_SIGN = {
    "min_income_up": "+",
    "child_benefit_up": "+",
    "pit_give": "+",
    "gdp_shock": "-",
    "unemployment_shock": "-",
}


def expected_sign(scen: str, mag=None) -> str:
    """Expected sign of the disposable-income change for `scen` at magnitude `mag`.

    pit_give is the one two-sided dial: a negative magnitude cuts the first-bracket
    rate and raises net income, a positive magnitude raises the rate and lowers it,
    so the expected sign follows the sign of the magnitude rather than the table.
    Every other dial is one-directional and keeps its table entry. With `mag` omitted
    the table is returned unchanged, which is what the default-magnitude callers want.
    """
    if mag is None:
        return EXPECTED_SIGN[scen]
    if mag == 0:
        return "0"
    if scen == "pit_give":
        return "+" if mag < 0 else "-"
    return EXPECTED_SIGN[scen]

# Uniform reform magnitudes (held here, applied to live-read values).
MIN_INCOME_FACTOR = 1.25      # +25%
CHILD_FACTOR = 1.25           # +25%
PIT_RATE_DELTA = -0.02        # -2pp on the first-bracket rate (documented fallback)
GDP_FACTOR = 0.97             # -3% market income
UNEMPLOYMENT_PP = 0.03        # +3pp unemployment rate

PROFILES = {
    "EL": {
        "system_year": 2024,
        "dataset_id": "EL_training_data",
        "currency": "EUR",
        "reforms": {
            "min_income_up": {
                "type": "const_scale", "factor": MIN_INCOME_FACTOR,
                "constants": [("$bsa00_adult_amt", ""), ("$bsa00_child_amt", "")],
                "note": "Greek social assistance (KEA) adult and child guaranteed-minimum amounts, +25%.",
            },
            "child_benefit_up": {
                "type": "const_scale", "factor": CHILD_FACTOR,
                "constants": [("$bch_amt1", ""), ("$bch_amt2", "")],
                "note": "Greek child benefit (A21) tier amounts, +25%.",
            },
            "pit_give": {
                "type": "rate_delta", "delta": PIT_RATE_DELTA,
                "constants": [("$tin00_rate1", "")],
                "note": "Substitution: a uniform tax-free-allowance constant is not exposed; "
                        "-2pp on the first income-tax bracket rate instead.",
            },
            "gdp_shock": {"type": "income_scale", "factor": GDP_FACTOR, "vars": ["yem", "yse"],
                          "note": "-3% to employment and self-employment market income."},
            "unemployment_shock": {"type": "unemployment", "pp": UNEMPLOYMENT_PP,
                                   "note": "+3pp unemployment rate: employed (les 2,3) flipped to "
                                           "unemployed (les 5), earnings zeroed, benefits recompute."},
        },
    },
    "IT": {
        "system_year": 2024,
        "dataset_id": "IT_training_data",
        "currency": "EUR",
        "reforms": {
            "min_income_up": {
                "type": "const_scale", "factor": MIN_INCOME_FACTOR,
                "constants": [("$bsa_Amount1", "1")],
                "note": "Italian minimum income (Assegno di Inclusione) base amount, +25%.",
            },
            "child_benefit_up": {
                "type": "param_mutate_scale", "factor": CHILD_FACTOR,
                "policy": "bau_it", "func": "BenCalc", "param": "#_Amount", "unit": "#m",
                "note": "Substitution: the Assegno Unico Universale is an ISEE-banded schedule with "
                        "amounts embedded as BenCalc #_Amount parameters, not scalar constants. The "
                        "+25% scales the monthly #_Amount cells via in-memory mutation (restored after "
                        "the run); inline taper constants are not separately scaled, so the realised "
                        "rise is approximately +25%, concentrated in the flat/max bands.",
            },
            "pit_give": {
                "type": "rate_delta", "delta": PIT_RATE_DELTA,
                "constants": [("$tintsna_rate1", "9")],
                "note": "Substitution: -2pp on the first IRPEF bracket rate (no uniform tax-free-allowance constant).",
            },
            "gdp_shock": {"type": "income_scale", "factor": GDP_FACTOR, "vars": ["yem", "yse"],
                          "note": "-3% to employment and self-employment market income."},
            "unemployment_shock": {"type": "unemployment", "pp": UNEMPLOYMENT_PP,
                                   "note": "+3pp unemployment rate: employed (les 2,3) flipped to "
                                           "unemployed (les 5), earnings zeroed, benefits recompute."},
        },
    },
    "ES": {
        "system_year": 2024,
        "dataset_id": "ES_training_data",
        "currency": "EUR",
        "reforms": {
            "min_income_up": {
                "type": "const_scale", "factor": MIN_INCOME_FACTOR,
                "constants": [("$bsa00_amt", "1")],
                "note": "Spanish minimum income (Ingreso Minimo Vital) base amount, +25%.",
            },
            "child_benefit_up": {
                "type": "const_scale", "factor": CHILD_FACTOR,
                "constants": [("$bch00_amt4", ""), ("$bch00_amt5", ""), ("$bch00_amt6", "")],
                "note": "Substitution: Spain has no strong universal child benefit; the closest "
                        "standalone lever is the means-tested child allowance (bch00), whose non-zero "
                        "amounts are scaled +25%. Effect is small by construction.",
            },
            "pit_give": {
                "type": "rate_delta", "delta": PIT_RATE_DELTA,
                "constants": [("$tin_rate1", "")],
                "note": "Substitution: -2pp on the first IRPF bracket rate (no uniform tax-free-allowance constant).",
            },
            "gdp_shock": {"type": "income_scale", "factor": GDP_FACTOR, "vars": ["yem", "yse"],
                          "note": "-3% to employment and self-employment market income."},
            "unemployment_shock": {"type": "unemployment", "pp": UNEMPLOYMENT_PP,
                                   "note": "+3pp unemployment rate: employed (les 2,3) flipped to "
                                           "unemployed (les 5), earnings zeroed, benefits recompute."},
        },
    },
}

# Labour-market status (les) codes in the EUROMOD input (confirmed against the
# training data): 2 = self-employed, 3 = employee, 5 = unemployed.
LES_EMPLOYED = (2, 3)
LES_UNEMPLOYED = 5
