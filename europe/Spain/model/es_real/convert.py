"""
convert.py -- MINIMUM ES 2024 UDB -> EUROMOD input conversion (EXPERIMENT ONLY).

Purpose: produce a runnable EUROMOD ES input DataFrame from the real ES 2024
cross-sectional UDB, implementing only the directly-mapping and lightest-derivation
variables, so the connector accepts it and the two market-income shocks can act. It
is deliberately NOT correct in the benefits or taxes: every benefit/contribution/
asset/expenditure variable not directly mapped is defaulted, and the family
pointers and assessment units are not constructed. See SHORTCUTS below and the
experiment report.

DATA HANDLING: reads the gated RPP UDB by path, read-only; never writes the
converted microdata or any per-person/per-household real data to disk. The result
is returned in memory for a single .run(); only aggregates leave this process.

SHORTCUTS (every one a known source of error, accepted for this go/no-go):
  - idmother/idfather/idpartner set to 0: family pointers and joint assessment
    units not constructed. Corrupts household benefits and joint taxation.
  - All benefit/contribution/asset/expenditure inputs defaulted to 0 except the
    few directly-mapping gross components below; benefits are simulated from an
    incomplete base, so disposable income on the benefit side is unreliable.
  - Household HY...G amounts allocated wholly to the household head (min idperson),
    not shared per the EMC rules.
  - Region (drgn2) defaulted to 0; net-to-gross reconciliation not attempted (ES
    gross is directly grounded, so this is lighter here than for EL/IT).
  - Uprating: run under the ES_training_data dataset uprating, not a 2023->2024
    factor matched to the income reference period.
"""
import glob
import os

import numpy as np
import pandas as pd

# The licensed EU-SILC UDB. Held outside this tree, and outside the sibling
# LOCAL_ONLY, under the IGP data share. Set BENEFITS_SILC_ROOT to the folder holding the
# per-country _CROSS directories to run this anywhere else; the literal below is where it
# sits on the machine the surfaces were built on, kept as the recorded location rather
# than as an assumption about any other machine.
_SILC_ROOT = os.environ.get(
    "BENEFITS_SILC_ROOT",
    "")
UDB = os.path.join(_SILC_ROOT, "ES_CROSS", "2024")
if not os.path.isdir(UDB):
    raise SystemExit(
        "EU-SILC UDB not found at:\n  " + UDB + "\n"
        "Set BENEFITS_SILC_ROOT to the folder containing ES_CROSS/2024, which must hold\n"
        "UDB_cES24D.csv, UDB_cES24H.csv, UDB_cES24P.csv and UDB_cES24R.csv.\n"
        "The data is licensed and is not, and must not be, in this repository.")

# EUROMOD labour status (les): 2 self-employed, 3 employee, 4 pensioner,
# 5 unemployed, 6 student, 7 inactive, 0 child/not-applicable.
# Earners are keyed off PL040A (status in employment), which is income-validated:
# PL040A 3 = employee, PL040A {1,2,4} = self-employed/family worker. Non-employed
# adults are inferred from PL032 (best-effort; documented shortcut).
PL032_NONEMP = {5: 5, 3: 4, 6: 6}  # unemployed, retired, student; else 7 (inactive)
MONTH = 1.0 / 12.0


def _file(letter):
    return glob.glob(os.path.join(UDB, f"UDB_c*{letter}.csv"))[0]


def convert_es_2024(template_cols):
    """Return a EUROMOD ES input DataFrame (one row per person, all household
    members) with the template's columns; mapped variables populated, the rest 0."""
    # Household id is the Eurostat-derived RX030 (== DB030); the R file has no RB040.
    D = pd.read_csv(_file("D"), usecols=["DB030", "DB090", "DB040"])
    R = pd.read_csv(_file("R"), usecols=["RB030", "RX030", "RX020", "RB090",
                                         "RB220", "RB230", "RB240"])
    P = pd.read_csv(_file("P"), usecols=["PB030", "PY010G", "PY050G", "PY080G",
                                         "PY090G", "PY100G", "PY110G", "PY120G",
                                         "PY130G", "PY140G", "PL032", "PL040A", "PL060"])
    H = pd.read_csv(_file("H"), usecols=["HB030", "HY040G", "HY050G", "HY060G",
                                         "HY070G", "HY090G"])

    df = R.rename(columns={"RB030": "idperson", "RX030": "idhh",
                           "RX020": "dag", "RB090": "sex"})
    df = df.merge(D.rename(columns={"DB030": "idhh", "DB090": "dwt"})[["idhh", "dwt"]],
                  on="idhh", how="left")
    df = df.merge(P.rename(columns={"PB030": "idperson"}), on="idperson", how="left")

    head = df.groupby("idhh")["idperson"].transform("min")
    is_head = (df["idperson"] == head).to_numpy()
    df = df.merge(H.rename(columns={"HB030": "idhh"}), on="idhh", how="left")
    for c in ("HY040G", "HY050G", "HY060G", "HY070G", "HY090G"):
        df[c] = np.where(is_head, df[c].fillna(0.0), 0.0)

    n = len(df)
    out = pd.DataFrame(0.0, index=np.arange(n), columns=list(template_cols))

    out["idperson"] = df["idperson"].to_numpy("int64")
    out["idhh"] = df["idhh"].to_numpy("int64")
    out["idmother"] = 0
    out["idfather"] = 0
    out["idpartner"] = 0
    out["dag"] = df["dag"].fillna(0).clip(lower=0).to_numpy("int64")
    out["dgn"] = np.where(df["sex"].to_numpy() == 1, 1, 0)  # male=1, female=0
    out["dwt"] = df["dwt"].fillna(0.0).to_numpy()

    adult = (df["dag"] >= 16).to_numpy()
    pl040 = df["PL040A"]
    les = np.zeros(n, dtype="int64")
    les[adult & pl040.isin([1, 2, 4]).to_numpy()] = 2          # self-employed / family worker
    les[adult & (pl040 == 3).to_numpy()] = 3                   # employee
    nonemp = adult & (les == 0)
    inferred = df["PL032"].map(PL032_NONEMP).fillna(7).to_numpy().astype("int64")
    les[nonemp] = inferred[nonemp]
    out["les"] = les
    out["lhw"] = df["PL060"].fillna(0).to_numpy()

    # market incomes (annual gross -> monthly)
    out["yem"] = df["PY010G"].fillna(0.0).to_numpy() * MONTH
    out["yse"] = df["PY050G"].fillna(0.0).to_numpy() * MONTH
    out["ypp"] = df["PY080G"].fillna(0.0).to_numpy() * MONTH   # individual private pension
    out["ypr"] = df["HY040G"].fillna(0.0).to_numpy() * MONTH   # rental income (head)
    out["yiy"] = df["HY090G"].fillna(0.0).to_numpy() * MONTH   # interest/dividends (head)

    # public pension and directly-mapping benefit components (feed ils_ben; some may
    # be overwritten by simulation -- unreliable, kept only to enrich the base)
    out["poa"] = df["PY100G"].fillna(0.0).to_numpy() * MONTH   # old-age
    out["bun"] = df["PY090G"].fillna(0.0).to_numpy() * MONTH   # unemployment
    out["pdi"] = df["PY130G"].fillna(0.0).to_numpy() * MONTH   # disability
    out["bsa"] = df["HY060G"].fillna(0.0).to_numpy() * MONTH   # social exclusion (head)
    out["bfa"] = df["HY050G"].fillna(0.0).to_numpy() * MONTH   # family/children (head)
    out["bho"] = df["HY070G"].fillna(0.0).to_numpy() * MONTH   # housing (head)

    # EUROMOD requires rows contiguous and ascending by household.
    out = out.sort_values(["idhh", "idperson"]).reset_index(drop=True)
    return out
