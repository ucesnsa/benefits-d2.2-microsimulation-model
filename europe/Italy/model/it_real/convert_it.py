"""
convert_it.py -- FULL IT 2024 EU-SILC data -> EUROMOD input conversion.

Italy is the third country, built to the structurally-verified standard of the
corrected ES and EL converters. It clones the EL converter (the
closer structural fit: IT gross is NSI-derived like EL, needing the same net-to-gross
internal-consistency reconciliation, and EL carries the corrected coded mappings),
and adapts the earnings convention to IT. Runs on system IT_2023 with dataset
IT_2024_a1_2015_03_e2 (yearCollection 2024, income year 2023).

IT-SPECIFIC STRUCTURES (established at IT-0 from the IT model spine and template):
  1. EARNINGS. IT's income list uses yem and yse DIRECTLY (yemre/ysere are absent
     from the IT template, unlike EL). The model simulates non-declared
     self-employment (ysenr_s) on top. So feed yem <- PY010G and yse <- PY050G
     directly (ES-style), no reported/non-reported input split.
  2. PENSIONS. ils_pen = poa + phl + pdi + psu (read components). Route PY100G -> poa
     (old age), PY110G -> psu (survivor), PY130G -> pdi (disability, non-taxable).
     phl (invalidity and other taxable benefits) is left 0: the EU-SILC data cannot
     separate the taxable-invalidity component from PY130G; documented limit.
  3. NO FUND VARIABLE. IT has no lpmfc/lpm in its template, so (unlike EL) no
     social-insurance-fund assignment is needed; IT SIC is computed from employment
     status and earnings.
  4. NET-TO-GROSS. IT gross (PY...G) is NSI-derived (like EL), so the same
     component-level internal-consistency reconciliation is applied.
  5. REGION. IT uses drgn2 (a NUTS-2 numeric region code) plus the degree-of-
     urbanisation triplet drgur/drgmd/drgru. The EU-SILC data carries only NUTS-1
     (DB040 = ITC/ITF/ITG/ITH/ITI, 5 macro-areas), so each macro-area is mapped to a
     representative NUTS-2 region; this is the documented NUTS-1 granularity limit,
     and affects only the regional IRPEF surcharge, a small part of income tax.

All coded mappings use the STANDARD EU-SILC 2021+ coding verified in the audit
(PL032, PL040A, HH021, DB100, PE041 hundreds-coded, PB190, RB090); none is the
obsolete scheme that broke ES.

COMPLETED CONVERSION. Italy's derivable set is small and the reason is in
the inventory `europe/model/input_inventory.py` generates: of the 74 input variables a live IT_2023
policy reads and this conversion left at zero, 49 have a published recipe that names a
national-SILC or production variable the public release does not carry, and 18 have no
usable recipe at all. Seven are derivable and are now populated: `xhcrt`, `xhc`, `xhcot`,
`xhcmomi`, `xpp`, `dec` and `loc`. In particular the unemployment components are NOT
derivable -- `bunct01` is `rmcig*cig_e` and `bunct02` is `minden*inden_e`, both national --
and neither are the child (`bchot` = `indmen*ind_e`), education (`bedmy` = `mborst`) or
mortgage (`xhcmo` = `pagmut_e`) variables.

THE CONTRACT CLASS. `lcl` gates every employer and employee contribution component in
`sicer_it` and `sicee_it`, and at zero none of them fires, which is why Italy's employer
contributions read exactly zero. Its documented construction uses `posdip`, the national
occupational-position variable, which the public release does not carry, and NO EUROMOD
country derives `lcl` from occupation: only Austria and Italy define it at all and both
use a national variable. The only collar rule EUROMOD itself states for a dataset without
`lcl` is `SetDefault_it`'s `lcl = 1` for training and hypothetical data, which is all blue
collar. This conversion therefore uses a STATED PROXY OF OURS, not a EUROMOD rule: the
manual / non-manual split of the ISCO-08 major groups, blue collar for major groups 6 to 9
and white collar for 0 to 5, applied to `loc`, which the codebook does publish for Italy.
What it costs is on the tool face and in the report: the proxy assigns a smaller share of
employees to blue collar than the national data does, and because the only rate that
differs between the two classes is sickness and maternity (2.68% blue against 0.46%
white), the whole of that error falls on one component.

DATA HANDLING: reads the EU-SILC data read-only (c files only, hardcoded c-prefix
glob); never writes converted microdata to disk; returns the input DataFrame in
memory for a single .run().
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
UDB = os.path.join(_SILC_ROOT, "IT_CROSS", "2024")
if not os.path.isdir(UDB):
    raise SystemExit(
        "EU-SILC UDB not found at:\n  " + UDB + "\n"
        "Set BENEFITS_SILC_ROOT to the folder containing IT_CROSS/2024, which must hold\n"
        "UDB_cIT24D.csv, UDB_cIT24H.csv, UDB_cIT24P.csv and UDB_cIT24R.csv.\n"
        "The data is licensed and is not, and must not be, in this repository.")
MONTH = 1.0 / 12.0
# Standard EU-SILC PL032 (2021+) -> EUROMOD les, the audit-verified mapping
#   PL032: 2 unemployed, 3 retired, 4 unable/ill, 5 student, 6 domestic, 7 other inactive
#   les:   2 self-emp, 3 employee, 4 sick/disabled, 5 unemployed, 6 retired, 7 inactive
PL032_NONEMP = {2: 5, 3: 6, 4: 4, 5: 7, 6: 7, 7: 7, 8: 4, 9: 1}
PB190_TO_DMS = {1: 1, 2: 2, 3: 3, 4: 5, 5: 4}      # SILC marital -> EUROMOD dms
HH021_TO_AMRTN = {1: 1, 2: 2, 3: 3, 4: 3, 5: 4}    # SILC tenure -> EUROMOD amrtn
# DB040 NUTS-1 macro-area -> representative NUTS-2 (ISTAT) region for drgn2
DB040_TO_DRGN2 = {"ITC": 3, "ITH": 5, "ITI": 12, "ITF": 15, "ITG": 19}
# ISCO-08 two-digit (PL051A) -> EUROMOD loc, the codebook's IT recipe, transcribed.
LOC_BANDS = [((1, 2, 3), 0), (range(11, 15), 1), (range(21, 27), 2), (range(31, 36), 3),
             (range(41, 45), 4), (range(51, 55), 5), (range(61, 64), 6),
             (range(71, 76), 7), (range(81, 84), 8), (range(91, 97), 9)]
# The stated proxy for lcl. Blue collar = ISCO-08 major groups 6 to 9, the manual
# occupations; white collar = 0 to 5. This is OUR convention, not EUROMOD's: see the
# module docstring. Held here as data so that the rule is one line to read and to change.
LCL_BLUE_MAJOR = (6, 7, 8, 9)
# The statutory chain that turns cadastral income into the IMU and ISEE taxable base:
# a 5 per cent revaluation and a category coefficient of 160 for ordinary residential
# property. Both are in the model itself (tpr_it 25.10, bsamm_it), not recalled here.
IT_CADASTRAL_MULT = 1.05 * 160
IT_IMU_RATE_STANDARD = 0.0076      # statutory band 0.76% standard to 1.06% maximum

LOG = []


def _file(letter):
    return glob.glob(os.path.join(UDB, f"UDB_c*{letter}.csv"))[0]


def _deh(pe041):
    """SILC PE041 (ISCED highest, hundreds-coded) -> EUROMOD deh 1/2/3."""
    v = pd.to_numeric(pe041, errors="coerce")
    out = np.where(v >= 500, 3, np.where(v >= 300, 2, 1)).astype("int64")
    out[np.isnan(v)] = 1
    return out


def _degurba(db100):
    v = pd.to_numeric(db100, errors="coerce").fillna(1).to_numpy()
    drgur = (v == 1).astype("int64")
    drgmd = (v == 2).astype("int64")
    drgru = (v == 3).astype("int64")
    drgur[~np.isin(v, [1, 2, 3])] = 1
    return drgur, drgmd, drgru


def _loc(pl051a, has_earnings):
    """EUROMOD loc from ISCO-08 two-digit PL051A, the codebook's IT recipe.

    The Italian recipe carries no imputation clause: missing stays missing, and is carried
    as the recipe's own -1 where the person has no earnings and as 0 otherwise.
    """
    v = pd.to_numeric(pl051a, errors="coerce").to_numpy()
    out = np.full(len(v), np.nan)
    for codes, val in LOC_BANDS:
        out[np.isin(v, list(codes))] = val
    out[np.isnan(out) & ~has_earnings] = -1
    out[np.isnan(out)] = 0
    return out.astype("int64")


def _lcl(loc, has_employment_income):
    """Contract class, from occupation. 1 blue, 2 white, 0 not applicable.

    Scope. The class is assigned to exactly the people the contribution components apply
    to, which the model defines for itself: `sicer_it` computes its base `sin01_s` under
    `comp_cond = ((yem + kfb_s) > 0)`, and every component is then gated on `lcl = 1` or
    `lcl = 2`. So anyone with positive employment income needs a class, whether or not the
    labour-status variable calls them an employee, and nobody else does. Scoping this on
    `les = 3` instead loses the 14% of people with employment income whom `les` classes
    otherwise, and it puts the aggregate below the all-white-collar bound, which is how
    the error was found.

    Rule. Blue collar for ISCO-08 major groups 6 to 9, white collar for 0 to 5. That split
    is OURS (see the module docstring); EUROMOD publishes no occupation-to-collar rule.

    Residual. Where someone has employment income and the release carries no occupation,
    the class falls back to blue, which is EUROMOD's own rule for a dataset that does not
    carry `lcl`: `SetDefault_it` sets `lcl = 1` for the training and hypothetical data.
    Using the model's default for the residual keeps the invented part of this to the one
    line above.
    """
    out = np.zeros(len(loc), dtype="int64")
    out[has_employment_income] = 1                      # EUROMOD's own default: blue
    out[has_employment_income & np.isin(loc, (0, 1, 2, 3, 4, 5))] = 2
    out[has_employment_income & np.isin(loc, LCL_BLUE_MAJOR)] = 1
    return out


def _dec(pe021):
    """EUROMOD dec from the codebook's IT recipe: pe021 recoded, then shifted by one."""
    e21 = pd.to_numeric(pe021, errors="coerce").to_numpy()
    t = np.full(len(e21), np.nan)
    t[e21 == 10] = 1
    t[e21 == 20] = 2
    t[(e21 >= 30) & (e21 <= 39)] = 3
    t[(e21 >= 40) & (e21 <= 49)] = 4
    t[(e21 >= 50) & (e21 <= 80)] = 5
    d = t + 1                       # recode dec (0=1)(1=2)(2=3)(3=4)(4=5)(5=6)
    d[np.isnan(d)] = 0
    return d.astype("int64")


def _reconcile_gross(P, log):
    """Net-to-gross internal-consistency pass on the NSI-derived IT gross. Where the
    held gross is missing or below net but net is positive, impute gross from the
    population gross/net ratio. Logs diagnostics."""
    comps = {"PY010G": "PY010N", "PY050G": "PY050N", "PY090G": "PY090N",
             "PY100G": "PY100N", "PY110G": "PY110N", "PY120G": "PY120N",
             "PY130G": "PY130N", "PY140G": "PY140N"}
    out = {}
    for g, n in comps.items():
        gs = pd.to_numeric(P.get(g, 0), errors="coerce").fillna(0.0)
        if n not in P.columns:
            out[g] = gs
            continue
        ns = pd.to_numeric(P[n], errors="coerce").fillna(0.0)
        both = (gs > 0) & (ns > 0)
        ratio = float((gs[both].sum() / ns[both].sum())) if both.sum() else 1.0
        ratio = min(max(ratio, 1.0), 1.8)
        bad = (ns > 0) & (gs < ns)
        nbad = int(bad.sum())
        fixed = gs.copy()
        fixed[bad] = ns[bad] * ratio
        out[g] = fixed
        if nbad:
            log.append(f"net-to-gross {g}: G/N ratio={ratio:.3f}; {nbad} records gross<net, "
                       f"imputed gross=net*ratio")
        else:
            log.append(f"net-to-gross {g}: G/N ratio={ratio:.3f}; gross internally consistent, "
                       f"used as held")
    return out


def convert_it_2024_full(template_cols):
    LOG.clear()
    tset = set(template_cols)

    def setcol(out, name, values):
        if name in tset:
            out[name] = values

    D = pd.read_csv(_file("D"), usecols=["DB030", "DB090", "DB040", "DB100"])
    R = pd.read_csv(_file("R"), usecols=["RB030", "RX030", "RX020", "RB090",
                                         "RB220", "RB230", "RB240"])
    pcols = ["PB030", "PB190", "PE021", "PE041", "PL032", "PL040A", "PL051A", "PL060",
             "PL073", "PL074", "PL075", "PL076", "PL200", "PL085",
             "PY010G", "PY010N", "PY035G", "PY050G", "PY050N", "PY080G",
             "PY090G", "PY090N", "PY100G", "PY100N", "PY110G", "PY110N",
             "PY120G", "PY120N", "PY130G", "PY130N", "PY140G", "PY140N"]
    Phead = pd.read_csv(_file("P"), nrows=0).columns
    P = pd.read_csv(_file("P"), usecols=[c for c in pcols if c in Phead])
    H = pd.read_csv(_file("H"), usecols=["HB030", "HY040G", "HY050G", "HY060G",
                                         "HY070G", "HY080G", "HY090G", "HY100G",
                                         "HY110G", "HY120G", "HY130G",
                                         "HH021", "HH060", "HH070"])

    grossP = _reconcile_gross(P, LOG)

    df = R.rename(columns={"RB030": "idperson", "RX030": "idhh",
                           "RX020": "dag", "RB090": "sex"})
    df = df.merge(D.rename(columns={"DB030": "idhh", "DB090": "dwt",
                                    "DB040": "nuts1", "DB100": "degurba"}),
                  on="idhh", how="left")
    df = df.merge(P.rename(columns={"PB030": "idperson"}), on="idperson", how="left")
    pmap = P.assign(**{g + "_rec": v for g, v in grossP.items()}).set_index("PB030")
    for g in grossP:
        df[g + "_rec"] = df["idperson"].map(pmap[g + "_rec"]).fillna(0.0).to_numpy()

    n = len(df)
    df = df.merge(H.rename(columns={"HB030": "idhh"}), on="idhh", how="left")

    # household monetary amounts -> oldest member (EMC); HH021 stays per-member
    oldest = df.groupby("idhh")["dag"].transform("max")
    first_oldest = df.assign(_o=(df["dag"] == oldest)).sort_values(
        ["idhh", "_o", "idperson"], ascending=[True, False, True])
    recip = first_oldest.groupby("idhh").head(1).index
    is_recip = np.zeros(n, dtype=bool)
    is_recip[df.index.get_indexer(recip)] = True
    # ALLOCATION SUBSTITUTION, stated once. The codebook allocates household money to the
    # default income recipients or, for housing costs, to the people responsible for the
    # accommodation (hb080/hb090), neither of which the public release identifies. The
    # whole household amount goes to the oldest member, the EMC sharing rule already used
    # here; household totals are exact and only the within-household allocation differs.
    for c in ["HY040G", "HY050G", "HY060G", "HY070G", "HY080G", "HY090G", "HY100G",
              "HY110G", "HY120G", "HY130G", "HH060", "HH070"]:
        df[c] = np.where(is_recip, pd.to_numeric(df[c], errors="coerce").fillna(0.0), 0.0)
    LOG.append("household amounts allocated to oldest hh member (EMC): HY040/050/060/070/"
               "080/090/100/110/120/130G, HH060, HH070")

    out = pd.DataFrame(0.0, index=np.arange(n), columns=list(template_cols))

    # ---- identifiers and pointers ----
    setcol(out, "idperson", df["idperson"].to_numpy("int64"))
    setcol(out, "idhh", df["idhh"].to_numpy("int64"))
    for src, dst in (("RB220", "idfather"), ("RB230", "idmother"), ("RB240", "idpartner")):
        v = pd.to_numeric(df[src], errors="coerce").fillna(0)
        setcol(out, dst, np.where(v > 0, v, 0).astype("int64"))
    LOG.append("pointers idfather/idmother/idpartner <- RB220/RB230/RB240")

    # ---- demographics ----
    setcol(out, "dag", df["dag"].fillna(0).clip(lower=0).to_numpy("int64"))
    setcol(out, "dgn", np.where(df["sex"].to_numpy() == 1, 1, 0))
    dms = df["PB190"].map(PB190_TO_DMS)
    setcol(out, "dms", dms.where(df["dag"] >= 16, 1).fillna(1).to_numpy("int64"))
    setcol(out, "ddi", (df["PY130G_rec"].fillna(0) > 0).astype("int64").to_numpy())
    setcol(out, "deh", _deh(df["PE041"]))
    drgur, drgmd, drgru = _degurba(df["degurba"])
    setcol(out, "drgur", drgur); setcol(out, "drgmd", drgmd); setcol(out, "drgru", drgru)
    setcol(out, "drgn2", df["nuts1"].map(DB040_TO_DRGN2).fillna(12).to_numpy("int64"))
    setcol(out, "amrtn", df["HH021"].map(HH021_TO_AMRTN).fillna(3).to_numpy("int64"))
    setcol(out, "dwt", df["dwt"].fillna(0.0).to_numpy())
    LOG.append("dms<-PB190; ddi<-(PY130G>0); deh<-PE041(hundreds ISCED); "
               "drgur/md/ru<-DB100; drgn2<-DB040(NUTS1->repr NUTS2); amrtn<-HH021; dwt<-DB090")

    # ---- labour (standard PL040A + audit-verified PL032 mapping) ----
    adult = (df["dag"] >= 16).to_numpy()
    pl040 = df["PL040A"]
    les = np.zeros(n, dtype="int64")
    les[adult & pl040.isin([1, 2, 4]).to_numpy()] = 2
    les[adult & (pl040 == 3).to_numpy()] = 3
    nonemp = adult & (les == 0)
    inferred = df["PL032"].map(PL032_NONEMP).fillna(7).to_numpy().astype("int64")
    les[nonemp] = inferred[nonemp]
    setcol(out, "les", les)
    lhw = pd.to_numeric(df["PL060"], errors="coerce").fillna(0).to_numpy(float)
    lhw = np.where((les == 3) & (lhw <= 0), 38.0, lhw)
    setcol(out, "lhw", lhw)
    months_work = df[["PL073", "PL074", "PL075", "PL076"]].apply(
        pd.to_numeric, errors="coerce").fillna(0).sum(axis=1).clip(0, 12)
    setcol(out, "liwmy", months_work.to_numpy())
    setcol(out, "liwwh", (pd.to_numeric(df["PL200"], errors="coerce").fillna(0) * 12)
           .clip(lower=0).to_numpy())
    setcol(out, "lunmy", pd.to_numeric(df["PL085"], errors="coerce").fillna(0)
           .clip(0, 12).to_numpy())
    LOG.append("les<-PL040A/PL032(standard); lhw<-PL060; liwmy<-sum(PL073..076); "
               "liwwh<-PL200*12; lunmy<-PL085 (no lpmfc: IT has no fund variable)")

    # ---- market incomes (gross, monthly) ----
    # CONVENTION (verified empirically, IT GATE 2): the real-data config IT_2024_a1
    # consumes employment via yem directly, but self-employment via yseev, NOT the
    # directly-fed yse (which a1 discards, zeroing self-employment and its SIC). The
    # EU-SILC data carries only the self-employment TOTAL (PY050G) with no decomposition,
    # so the total is routed into yseev, the single component a1 aggregates into yse;
    # no split is fabricated. Feeding yseev restores output yse and the self-employed
    # SIC (confirmed: yse 0->226.7bn, ils_sicse 0->39.0bn).
    yem = df["PY010G_rec"].fillna(0.0).to_numpy() * MONTH
    yse = df["PY050G_rec"].fillna(0.0).to_numpy() * MONTH
    setcol(out, "yem", yem)            # employment (consumed directly on a1)
    setcol(out, "yseev", yse)          # self-employment total -> the yseev component a1 reads
    setcol(out, "ypp", df["PY080G"].fillna(0.0).to_numpy() * MONTH)   # private pension
    setcol(out, "yiy", df["HY090G"].fillna(0.0).to_numpy() * MONTH)   # investment (oldest)
    setcol(out, "ypr", df["HY040G"].fillna(0.0).to_numpy() * MONTH)   # property/rent (oldest)
    setcol(out, "ypt", df["HY080G"].fillna(0.0).to_numpy() * MONTH)   # inter-hh transfers in
    setcol(out, "xmp", df["HY130G"].fillna(0.0).to_numpy() * MONTH)   # maintenance paid (oldest)
    LOG.append("market: yem<-PY010G; SELF-EMPLOYMENT yseev<-PY050G (a1 consumes yseev, "
               "not yse; UDB has only the total, routed whole, no fabricated split); "
               "ypp<-PY080G, yiy<-HY090G, ypr<-HY040G, ypt<-HY080G, xmp<-HY130G (/12)")

    # ---- pensions (gross, monthly): route to read income-list components ----
    setcol(out, "poa", df["PY100G_rec"].fillna(0.0).to_numpy() * MONTH)   # old age
    setcol(out, "psu", df["PY110G_rec"].fillna(0.0).to_numpy() * MONTH)   # survivor
    setcol(out, "pdi", df["PY130G_rec"].fillna(0.0).to_numpy() * MONTH)   # disability (non-tax)
    # phl (taxable invalidity) left 0: not separable from PY130G in the EU-SILC data
    LOG.append("pensions: poa<-PY100G, psu<-PY110G, pdi<-PY130G; phl=0 (UDB cannot "
               "separate taxable invalidity)")

    # ---- read benefits + unemployment driver ----
    setcol(out, "bun", df["PY090G_rec"].fillna(0.0).to_numpy() * MONTH)   # unemployment driver
    setcol(out, "bed", df["PY140G_rec"].fillna(0.0).to_numpy() * MONTH)   # education
    setcol(out, "bho", df["HY070G"].fillna(0.0).to_numpy() * MONTH)       # housing (read)
    LOG.append("bun<-PY090G (unemployment driver; contributory NASpI simulated), "
               "bed<-PY140G, bho<-HY070G")
    LOG.append("LEFT TO SIMULATION (input 0): Assegno Unico (bfach00_s), ANF family "
               "allowances, social assistance, energy bonuses; family/social-exclusion "
               "SILC aggregates not fed to read components to avoid double-counting")

    # ---- months-receiving and proxies ----
    # ---- The seven derivable variables, and the contract-class proxy ----
    has_earn = ((pd.to_numeric(df["PY010G"], errors="coerce").fillna(0) > 0)
                | (pd.to_numeric(df["PY050G"], errors="coerce").fillna(0) > 0)).to_numpy()
    loc = _loc(df["PL051A"], has_earn)
    setcol(out, "loc", loc)
    # lcl: OUR stated proxy, not a EUROMOD rule. See the module docstring.
    lcl = _lcl(loc, yem > 0)
    setcol(out, "lcl", lcl)
    n_blue = int((lcl == 1).sum()); n_white = int((lcl == 2).sum())
    share = n_blue / max(n_blue + n_white, 1)
    base_blue = float(yem[lcl == 1].sum()); base_all = float(yem[lcl > 0].sum())
    share_base = base_blue / max(base_all, 1e-9)
    # housing costs: HH060 and HH070 are held monthly in SILC, HY100G annually.
    xhcrt = df["HH060"].to_numpy()
    xhcmomi = df["HY100G"].to_numpy() * MONTH
    xhc = df["HH070"].to_numpy()
    setcol(out, "xhcrt", xhcrt)
    setcol(out, "xhcmomi", xhcmomi)
    if "xhc" not in out.columns:
        out["xhc"] = 0.0
    out["xhc"] = xhc
    setcol(out, "xhcot", np.maximum(xhc - xhcrt - xhcmomi, 0.0))
    setcol(out, "xpp", pd.to_numeric(df["PY035G"], errors="coerce").fillna(0.0).to_numpy() * MONTH)
    setcol(out, "dec", _dec(df["PE021"]))
    LOG.append(f"loc<-PL051A (codebook IT recipe); lcl PROXY <- ISCO major groups 6-9 "
               f"blue, 0-5 white, over everyone with employment income (the model's own "
               f"gate), residual blue per SetDefault_it: {n_blue} blue and {n_white} white, "
               f"a blue share of {share:.1%} by headcount and {share_base:.1%} of the "
               f"contribution base. OUR convention, not a EUROMOD rule: no country derives "
               f"lcl from occupation and Italy's own rule uses posdip, which the public "
               f"release does not carry")
    LOG.append("xhcrt<-HH060, xhcmomi<-HY100G, xhc<-HH070, xhcot<-xhc-xhcrt-xhcmomi; "
               "xpp<-PY035G; dec<-PE021")

    # ---- Cadastral income of buildings other than the main residence ----
    # This is NOT a codebook recipe. The codebook says "yprob_d + yprobiv_d & calibration
    # with data from Agenzia del Territorio", which the public release cannot supply. It is
    # a STATUTORY inversion, and the statute is in the model itself, written twice:
    #     tpr_it  25.10   sin05_s = aobiv * 1.05 * 160
    #     bsamm_it Elig   (aobiv * 1.05 * 160) <= 30000
    # 1.05 is the statutory revaluation of cadastral income and 160 the category
    # coefficient for ordinary residential property, so aobiv*1.05*160 IS the base that IMU
    # and the ISEE are levied on. IMU exempts the main residence, so HY120G, regular taxes
    # on wealth, falls on exactly the property aobiv measures, and the chain inverts:
    #     aobiv = HY120G / rate / (1.05 * 160)
    # ONE free parameter, the municipal rate, confined by statute to 0.76 per cent standard
    # and 1.06 per cent maximum. The standard rate is used, not fitted: at 0.76 per cent
    # this gives an aggregate cadastral income of about EUR 9.8bn against the EUR 9,245m
    # Y16_CR_IT table A3.4 publishes for aobiv in 2023, within 6 per cent, and the published
    # figure sits inside the statutory band (it implies 0.80 per cent).
    #
    # The main residence value amriv stays at zero and that is deliberate: tpr_it 25.9 sets
    # the main-residence property tax to zero outright (TASI is abolished), so there is no
    # tax to invert and nothing in the public release identifies the value.
    #
    # The recorded property tax tpr also stays at zero, to avoid counting HY120G twice: the
    # model adds the read tpr on top of the tax it simulates from aobiv (tpr_it 25.12,
    # "Recorded property tax is used"), so deriving aobiv from HY120G and then also feeding
    # HY120G as tpr would charge the same tax through both routes.
    hy120 = pd.to_numeric(df["HY120G"], errors="coerce").fillna(0.0).to_numpy()
    aobiv = hy120 / IT_IMU_RATE_STANDARD / IT_CADASTRAL_MULT * MONTH
    setcol(out, "aobiv", aobiv)
    LOG.append(f"aobiv <- HY120G / {IT_IMU_RATE_STANDARD} / (1.05*160), the statutory "
               f"inversion the model itself writes (tpr_it 25.10, bsamm_it Elig). One free "
               f"parameter, the municipal IMU rate, inside its statutory band; the standard "
               f"rate is used rather than fitted. amriv and tpr stay at zero, the first "
               f"because tpr_it zeroes the main-residence tax outright and the second to "
               f"avoid charging HY120G through both routes")
    LOG.append("NOT POPULATED, and why: the unemployment components (bunct01=rmcig*cig_e, "
               "bunct02=minden*inden_e), the child, maternity and social-assistance "
               "components, the employment sub-components (yemtj/yemaj/yemxp/yemnt/yempv), "
               "tpr, kfb and xhcmo are all national-SILC; amriv, aobiv and afc are the "
               "asset variables reported rather than derived; lindi needs PL111A, which "
               "ships empty; kfbcc has no published recipe and the ES/EL kfb recipe is not "
               "transferable to Italy")

    setcol(out, "yemmy", np.where(yem > 0, months_work.to_numpy().clip(1, 12), 0))
    setcol(out, "ysemy", np.where(yse > 0, 12, 0))
    wage = np.where(lhw > 0, (yem * 12.0) / np.maximum(lhw * 52.0, 1.0), 0.0)
    setcol(out, "yivwg", np.where(adult, np.maximum(wage, 7.0), 0.0))
    LOG.append("CEILING: yivwg Heckman wage proxied; yemmy from months variables; "
               "ysemy set to 12 for everyone with self-employment income, the defect "
               "DATA_ISSUES 9.13 describes for Spain, not corrected here")

    out = out.sort_values(["idhh", "idperson"]).reset_index(drop=True)
    nuts1 = (df.sort_values(["idhh", "idperson"]).reset_index(drop=True)
             [["idhh", "nuts1"]].drop_duplicates("idhh"))
    return out, list(LOG), nuts1
