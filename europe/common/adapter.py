"""
adapter.py -- map per-person EUROMOD output to the canonical per-unit data layer.

The canonical contract (from wevm.py) is per-household, long format, one row per
household per scenario. EUROMOD output is per person, so household aggregates are
formed within idhh. Monetary values are annualised (x12) to match the UK layer's
annual units; the 2024 price year is the reference and deflation is downstream.
"""
import pandas as pd

ADULT_AGE = 18
PENSION_AGE = 65
MONTHS = 12


def euromod_to_per_unit(df: pd.DataFrame, country: str, year: int, scenario: str) -> pd.DataFrame:
    """One row per household with the canonical columns.

    net_income    = annualised within-idhh sum of person-level ils_dispy (disposable)
    income        = annualised within-idhh sum of person-level ils_origy (market)
    survey_weight = a representative per-household dwt (FLAGGED: training dwt varies
                    within household; the real UDB DB090 is household-constant)
    n_adults / n_children / is_working_age / household_type from dag (composition)
    region is absent from synthetic data and is intentionally omitted.
    """
    g = df.groupby("idhh")
    idx = g.size().index
    adults = df[df["dag"] >= ADULT_AGE].groupby("idhh").size().reindex(idx, fill_value=0)
    kids = df[df["dag"] < ADULT_AGE].groupby("idhh").size().reindex(idx, fill_value=0)
    wa = df[(df["dag"] >= ADULT_AGE) & (df["dag"] < PENSION_AGE)].groupby("idhh").size().reindex(idx, fill_value=0)
    hh = pd.DataFrame({
        "country": country,
        "year": year,
        "scenario": scenario,
        "unit_id": idx.astype(str),
        "net_income": (g["ils_dispy"].sum() * MONTHS).to_numpy(),
        "income": (g["ils_origy"].sum() * MONTHS).to_numpy(),
        "survey_weight": g["dwt"].first().to_numpy(),
        "n_adults": adults.to_numpy(),
        "n_children": kids.to_numpy(),
        "is_working_age": wa.to_numpy() > 0,
    })
    hh["household_type"] = [
        ("Single, no children" if a == 1 and c == 0 else
         "Single, with children" if a == 1 else
         "Couple/multi, no children" if c == 0 else
         "Couple/multi with children")
        for a, c in zip(hh["n_adults"], hh["n_children"])
    ]
    return hh


def weighted_disposable(per_unit: pd.DataFrame) -> float:
    return float((per_unit["net_income"] * per_unit["survey_weight"]).sum())
