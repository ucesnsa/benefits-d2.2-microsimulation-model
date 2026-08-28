"""
Generate synthetic FRS parquet files for demo / CI use.

Produces 2,000 realistic but entirely synthetic benefit units covering the
six raw parquet files that the pipeline expects, for FRS 2023-24, which is the
year the demo pipeline runs.  All values are fabricated — do NOT use for policy
analysis.

Output directory:
    demo/inputs/frs_2023_24/
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
SEED = 42
N_HH = 2_000      # benefit units (each household has exactly 1 BU for simplicity)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

REGION_CODES = [
    112000001, 112000002, 112000003, 112000004,
    112000005, 112000006, 112000007, 112000008,
    112000009, 299999999, 399999999, 499999999,
]
# ---------------------------------------------------------------------------


def _generate_year(out_dir: Path, seed: int) -> None:
    """Generate all six synthetic parquet files into *out_dir*."""
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    # Household type mix: single / couple / single-parent / couple+children
    hh_types = rng.choice(
        ["single", "couple", "single_parent", "couple_children"],
        size=N_HH,
        p=[0.35, 0.25, 0.15, 0.25],
    )
    n_adults_by_type = {"single": 1, "couple": 2, "single_parent": 1, "couple_children": 2}
    n_children_by_type = {"single": 0, "couple": 0, "single_parent": 2, "couple_children": 2}

    sernums = np.arange(1, N_HH + 1)

    # ------------------------------------------------------------------
    # 1. Adults
    # ------------------------------------------------------------------
    adult_rows = []
    for i, (sernum, hh_type) in enumerate(zip(sernums, hh_types)):
        n_adults = n_adults_by_type[hh_type]
        n_children = n_children_by_type[hh_type]
        gvtregn = int(rng.choice(REGION_CODES))
        tenure = int(rng.choice([1, 2, 4], p=[0.30, 0.35, 0.35]))
        ctband = int(rng.integers(1, 9))
        gross4 = float(rng.uniform(900, 1100))   # ~1000 so weight_sum ≈ 2M (demo)
        rentfull = float(rng.uniform(100, 400)) if tenure == 4 else 0.0
        mortpay = float(rng.uniform(100, 600)) if tenure == 2 else 0.0
        mortint = round(mortpay * 0.4, 2)
        ctrebamt = float(rng.uniform(5, 20)) if rng.random() < 0.08 else 0.0

        for p in range(1, n_adults + 1):
            age = int(rng.integers(22, 65))
            sex = int(rng.choice([1, 2]))
            # empstati: 2=FT_EMPLOYED 3=PT_EMPLOYED 6=UNEMPLOYED 8=STUDENT
            empstati = int(rng.choice([2, 3, 6, 8], p=[0.55, 0.20, 0.15, 0.10]))
            inearns = float(rng.uniform(200, 900)) if empstati in (2, 3) else 0.0
            seincam2 = float(rng.uniform(50, 300)) if rng.random() < 0.05 else 0.0
            tothours = float(rng.uniform(20, 40)) if inearns > 0 else 0.0

            adult_rows.append({
                "sernum": sernum,
                "gvtregn": gvtregn,
                "tenure_code": tenure,
                "adulth": n_adults,
                "depchldh": n_children,
                "gross4": gross4,
                "ctband": ctband,
                "hdhhinc": round(inearns * 52, 2),
                "ctrebamt": ctrebamt,
                "ctrebpd": 1,
                "benunit": 1,
                "burent": rentfull,
                "rentfull": rentfull,
                "mortpay": mortpay,
                "mortint": mortint,
                "person": p,
                "hrpid": 1 if p == 1 else 0,
                "uperson": 1 if p == 1 else 0,
                "hdage": age,
                "age80": age,
                "sex": sex,
                "marital": int(rng.choice([1, 2, 3, 4, 5, 6], p=[0.35, 0.15, 0.30, 0.08, 0.07, 0.05])),
                "educft": 2,
                "typeed2": 0,
                "educqual": int(rng.integers(1, 9)),
                "empstat": empstati,
                "empstatb": empstati,
                "empstati": empstati,
                "tothours": tothours,
                "ftwk": 1 if empstati == 2 else 0,
                "sic": int(rng.integers(1, 100)),
                "soc2020": int(rng.integers(1, 10)),
                "numjob": 1 if inearns > 0 else 0,
                "inearns": round(inearns, 2),
                "seincam2": round(seincam2, 2),
                "inpeninc": 0.0,
                "inrinc": 0.0,
                "totint": round(float(rng.uniform(0, 5)), 2),
                "ethgrps": int(rng.integers(1, 6)),
                "nssec20": int(rng.integers(1, 8)),
                "careah": 0.0,
                "health1": int(rng.choice([1, 2, 3], p=[0.6, 0.3, 0.1])),
                "limitl": int(rng.choice([1, 2], p=[0.15, 0.85])),
            })

    adults_df = pd.DataFrame(adult_rows)
    adults_df.to_parquet(out_dir / "frs_raw_adults.parquet", index=False)
    print(f"  adults:      {len(adults_df):,} rows")

    # ------------------------------------------------------------------
    # 2. Children
    # ------------------------------------------------------------------
    child_rows = []
    cp = 1
    for sernum, hh_type in zip(sernums, hh_types):
        for _ in range(n_children_by_type[hh_type]):
            child_rows.append({
                "sernum": int(sernum),
                "benunit": 1,
                "person": cp,
                "age": int(rng.integers(0, 18)),
                "sex": int(rng.choice([1, 2])),
            })
            cp += 1

    children_df = pd.DataFrame(child_rows)
    children_df.to_parquet(out_dir / "frs_raw_children.parquet", index=False)
    print(f"  children:    {len(children_df):,} rows")

    # ------------------------------------------------------------------
    # 3. Childcare costs (only BUs with children, ~30% of families)
    # ------------------------------------------------------------------
    cc_rows = []
    for sernum, hh_type in zip(sernums, hh_types):
        if n_children_by_type[hh_type] > 0 and rng.random() < 0.30:
            cc_rows.append({
                "sernum": int(sernum),
                "benunit": 1,
                "weekly_childcare_cost": round(float(rng.uniform(40, 200)), 2),
            })

    childcare_df = pd.DataFrame(cc_rows)
    childcare_df.to_parquet(out_dir / "frs_raw_childcare.parquet", index=False)
    print(f"  childcare:   {len(childcare_df):,} rows")

    # ------------------------------------------------------------------
    # 4. Benefits (sparse — only BUs actually receiving something)
    # ------------------------------------------------------------------
    benefit_cols = [
        "housing_benefit_weekly", "universal_credit_weekly",
        "jsa_contrib_weekly", "jsa_income_weekly",
        "esa_contrib_weekly", "esa_income_weekly",
        "dla_sc_weekly", "dla_m_weekly",
        "pip_dl_weekly", "pip_m_weekly",
        "attendance_allowance_weekly", "carers_allowance_weekly",
        "income_support_weekly", "child_benefit_weekly",
        "pension_credit_weekly", "state_pension_weekly",
        "working_tax_credit_weekly", "child_tax_credit_weekly",
    ]
    ben_rows = []
    for sernum, hh_type in zip(sernums, hh_types):
        n_adults = n_adults_by_type[hh_type]
        has_children = n_children_by_type[hh_type] > 0
        for p in range(1, n_adults + 1):
            row: dict = {"sernum": int(sernum), "benunit": 1, "person": p}
            for col in benefit_cols:
                row[col] = 0.0
            # UC: ~15% of working-age BUs
            if rng.random() < 0.15:
                row["universal_credit_weekly"] = round(float(rng.uniform(50, 300)), 2)
            # Housing benefit: ~10% renters
            if rng.random() < 0.10:
                row["housing_benefit_weekly"] = round(float(rng.uniform(30, 150)), 2)
            # Child benefit for families
            if has_children and p == 1:
                row["child_benefit_weekly"] = round(float(rng.uniform(20, 60)), 2)
            # JSA: ~3%
            if rng.random() < 0.03:
                row["jsa_income_weekly"] = round(float(rng.uniform(50, 80)), 2)

            if any(row[c] > 0 for c in benefit_cols):
                ben_rows.append(row)

    benefits_df = pd.DataFrame(ben_rows)
    benefits_df.to_parquet(out_dir / "frs_raw_benefits.parquet", index=False)
    print(f"  benefits:    {len(benefits_df):,} rows")

    # ------------------------------------------------------------------
    # 5. Accounts / dividends (only ~2% of adults)
    # ------------------------------------------------------------------
    accounts_df = adults_df[["sernum", "benunit", "person"]].copy()
    accounts_df = accounts_df.sample(frac=0.02, random_state=SEED).copy()
    accounts_df["dividend_weekly"] = rng.uniform(5, 50, size=len(accounts_df)).round(2)
    accounts_df.to_parquet(out_dir / "frs_raw_accounts.parquet", index=False)
    print(f"  accounts:    {len(accounts_df):,} rows")

    # ------------------------------------------------------------------
    # 6. Maintenance (only ~1% of adults)
    # ------------------------------------------------------------------
    maint_df = adults_df[["sernum", "benunit", "person"]].copy()
    maint_df = maint_df.sample(frac=0.01, random_state=SEED + 1).copy()
    maint_df["maintenance_income_weekly"] = rng.uniform(20, 100, size=len(maint_df)).round(2)
    maint_df["maintenance_expense_weekly"] = 0.0
    maint_df.to_parquet(out_dir / "frs_raw_maintenance.parquet", index=False)
    print(f"  maintenance: {len(maint_df):,} rows")

    # ------------------------------------------------------------------
    # Warning file
    # ------------------------------------------------------------------
    (out_dir / "SYNTHETIC_DATA_WARNING.txt").write_text(
        "ALL DATA IN THIS DIRECTORY IS SYNTHETIC.\n"
        "Generated by uk/model/demo/generate_demo_data.py for pipeline demo/CI use only.\n"
        "Do NOT use for policy analysis or publication.\n"
    )
    print(f"\nSynthetic data written to: {out_dir}")


def main() -> None:
    """Generate synthetic data for FRS 2023-24."""
    print("=== FRS 2023-24 ===")
    _generate_year(PROJECT_ROOT / "demo" / "inputs" / "frs_2023_24", seed=SEED + 1)


if __name__ == "__main__":
    main()
