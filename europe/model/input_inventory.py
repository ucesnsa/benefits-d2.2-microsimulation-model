"""input_inventory.py -- the input inventory: every input variable a live 2023 policy reads
that the conversion leaves at zero, with its EU-SILC source, its codebook recipe, and
whether that recipe is applicable to the public user database.

Reproducible from three machine-read sources and nothing else:

  1. THE MODEL'S OWN READ-LIST. The engine prints, once per run, the line
     "Warning: Variable(s) ... not found in user-provided lists". Feed it a frame carrying
     only the identifiers and the weight and that list is the executed spine's own
     read-list, in the engine's words. Two caveats, both measured rather than assumed:
       - Italy's SetDefault_it uses two consumption variables inside an ArithOp formula,
         where a variable absent from the data is an error rather than a default, so the
         minimal run aborts until those two are supplied. They are added back and then
         counted as read.
       - A variable a SetDefault covers never appears in the warning, because the engine
         has a value for it. Those are read too, and are listed separately.
  2. THE CODEBOOK. `EM_data_codebook_J2.0+.xlsm`, shipped with the model at
     %LOCALAPPDATA%\\euromod\\Documentation, per-country sheets, column
     "Notes: derivation from original data, and comments". This is the EUROMOD input data
     codebook and it carries the actual derivation for each variable, as Stata.
  3. THE PUBLIC USER DATABASE. The 2024 cross-sectional c-files themselves: column
     presence, and non-missing and non-zero counts, because several columns are shipped
     empty (PL111A on all three countries is the consequential one).

Data-free: this script reads the microdata read-only and emits counts and aggregates only.

Usage:  python input_inventory.py            (writes INPUT_CONVERSION_INVENTORY.md)
        python input_inventory.py --print    (to stdout)
"""
import argparse
import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EUROPE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EUROPE, "common"))
for _cc_dir, _sub in (("Spain", "es_real"), ("Italy", "it_real"), ("Greece", "el_real")):
    sys.path.insert(0, os.path.join(EUROPE, _cc_dir, "model", _sub))

SILC_ROOT = os.environ.get(
    "BENEFITS_SILC_ROOT",
    "")
CODEBOOK = os.path.join(os.environ.get("LOCALAPPDATA", ""), "euromod", "Documentation",
                        "EM_data_codebook_J2.0+.xlsm")

CC_CFG = {
    "ES": dict(dataset="ES_2024_b1_2015_03_e2", system="ES_2023", train="ES_training_data",
               mod="convert_full", fn="convert_es_2024_full", name="Spain"),
    "IT": dict(dataset="IT_2024_a1_2015_03_e2", system="IT_2023", train="IT_training_data",
               mod="convert_it", fn="convert_it_2024_full", name="Italy"),
    "EL": dict(dataset="EL_2024_c1_2015_03_e2", system="EL_2023", train="EL_training_data",
               mod="convert_el", fn="convert_el_2024_full", name="Greece"),
}
IDCOLS = ["idperson", "idhh", "idpartner", "idmother", "idfather", "dwt"]
FIELD = re.compile(r"\b([DHPR][BXELHYS]\d{3}[A-Z]?)\b", re.I)
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# ---------------------------------------------------------------------------
# The classification. Group is a judgement made by reading each recipe against the
# column list, and it is recorded here rather than inferred by a regex, so that every
# call is visible and arguable. The three groups are the ones the task defines:
#   A  derivable from the public database by the recipe the codebook publishes for THAT
#      country
#   B  not derivable: the recipe reaches for a national-SILC or production field the
#      public release does not carry (or carries empty)
#   C  no published recipe for that country, or a recipe that stops short of a value
# `note` states the reason. `decision` is what this build does about it.
# ---------------------------------------------------------------------------
CLASS = {
 "ES": {
  "bhl":      ("A", "py120g/12*hx010", "PY120G", "populate"),
  "bed":      ("A", "py140g/12*hx010", "PY140G", "populate"),
  "bho":      ("A", "hy070g/12*hx010", "HY070G", "populate"),
  "yot":      ("A", "hy110g/12*hx010 split equally between household members under 16",
               "HY110G", "populate"),
  "bunnc":    ("A", "py093g/12", "PY093G", "populate"),
  "poacm":    ("A", "py101g/12*hx010", "PY101G", "populate"),
  "poanc":    ("A", "py103g/12*hx010", "PY103G", "populate"),
  "psuwdcm":  ("A", "py111g/12", "PY111G", "populate"),
  "psuot":    ("A", "psu - psuwdcm - psuwd00", "PY110G,PY111G,PY112G", "populate"),
  "xhcrt":    ("A", "hh060*hx010", "HH060", "populate"),
  "xhcmomi":  ("A", "hy100g/12*hx010", "HY100G", "populate"),
  "xhcmomc":  ("A", "hh071*hx010", "HH071", "populate"),
  "xhc":      ("A", "hh070*hx010, floored at xhcrt+xhcmomi", "HH070", "populate"),
  "xhcot":    ("A", "xhc - xhcrt - xhcmomi", "HH070,HH060,HY100G", "populate"),
  "xpp":      ("A", "py035g/12*hx010", "PY035G", "populate"),
  "kfb":      ("A", "py020g/12*hx010", "PY020G", "populate"),
  "tad":      ("A", "hy145n/12*hx010", "HY145N", "populate"),
  "tis":      ("A", "hy140/12*hx010", "HY140G", "populate"),
  "yds":      ("A", "hy020/12*hx010", "HY020", "populate"),
  "tscer":    ("A", "py030g/12*hx010", "PY030G", "populate"),
  "bfa":      ("A", "hy050g/12*hx010", "HY050G", "populate"),
  "bsa":      ("A", "hy060g/12*hx010", "HY060G", "populate"),
  "bchot":    ("A", "t_bfancmt/12*hx010, t_bfancmt = hy053g", "HY053G", "populate"),
  "bch":      ("A", "bch00 + bchdi + bchot", "HY053G", "populate"),
  "loc":      ("A", "ISCO-2digit pl051a -> 1-digit loc, missing imputed at the mode",
               "PL051A", "populate"),
  "lcs":      ("A", "pl051a in {1,2,3,11,23,34,54} -> 1 else 0", "PL051A", "populate"),
  "dec":      ("A", "pe021 recoded, 0 if pe010==2, age-based imputation on rx010; the "
               "over-16 branch names pe040, which the 2024 release carries as PE041",
               "PE021,PE010,RX010,PE041", "populate, PE040 read as PE041"),
  "afc":      ("A", "(yiy*12)/0.002625, the ECB deposit rate the codebook cites",
               "HY090G", "not derived: asset variable, reported rather than derived"),
  "ysv":      ("C", "severance imputed where the observed benefit exceeds the theoretical "
               "maximum unemployment insurance; the theoretical maximum is not published",
               "PY092G", "not derived: the published recipe stops short of a value"),
  "bch00":    ("C", "imputed from a theoretical child benefit t_bch, not published",
               "HY053G", "not derived: the published recipe stops short of a value"),
  "bchdi":    ("C", "imputed from a theoretical disabled-child benefit, not published",
               "HY053G", "not derived: the published recipe stops short of a value"),
  "bunncmy":  ("C", "round(bunnc*12 / (${iprem}*0.8)); iprem is a national parameter",
               "PY093G", "not derived: the published recipe stops short of a value"),
  "lindi":    ("B", "NACE from pl111a", "PL111A shipped empty", "not derivable"),
 },
 "IT": {
  "xhcrt":    ("A", "hh060", "HH060", "populate"),
  "xhc":      ("A", "hh070*hx010", "HH070", "populate"),
  "xhcmomi":  ("A", "hy100g/12*hx010", "HY100G", "populate"),
  "xhcot":    ("A", "xhc - xhcrt - xhcmomi", "HH070,HH060,HY100G", "populate"),
  "xpp":      ("A", "py035g/12", "PY035G", "populate"),
  "dec":      ("A", "pe021 recoded", "PE021", "populate"),
  "loc":      ("A", "ISCO-2digit pl051a -> 1-digit loc", "PL051A", "populate"),
  "lcl":      ("B", "posdip / posdip_p, the national occupational-position variable",
               "not in the public release",
               "PROXY from loc, labelled; see the collar note"),
  "bsa01":    ("B", "hy060n - fbsa0_ex", "fbsa0_ex national", "not derivable"),
  "yds":      ("B", "(hy020*hy025)/12", "HY025 absent", "not derivable"),
  "yprmr":    ("B", "(altraf_e*quopro)/12, quopro from hb080/hb090",
               "altraf_e national; HB080/HB090 absent", "not derivable"),
  "kivho":    ("B", "hh061*12*quopro if hh031<2006", "HH031/HH061 absent", "not derivable"),
  "lindi":    ("B", "NACE from pl111a", "PL111A shipped empty", "not derivable"),
  "xhcmo":    ("B", "pagmut_e/12*hx010", "pagmut_e national", "not derivable"),
  "xmp00":    ("B", "verman_e/12*hx010 if staciv in {4,5}", "verman_e national", "not derivable"),
  "xmp01":    ("B", "(veralt_e+verman_e)/12*hx010", "veralt_e national", "not derivable"),
  "yot":      ("B", "redmin_e split between children", "redmin_e national", "not derivable"),
  "lcs":      ("B", "settor_v == 1", "settor_v national", "not derivable"),
  "yse":      ("B", "yse = yaut/12", "yaut national",
               "not derivable; the a1 config consumes self-employment through yseev, "
               "which the conversion feeds from PY050G"),
  "amriv":    ("B", "subrent, calibrated on Agenzia del Territorio data",
               "national and administrative", "not derivable: national or administrative source"),
  "bedmy":    ("B", "bedmy = mborst", "mborst national", "not derivable"),
  "bsamy":    ("B", "bsamy = nummes", "nummes national", "not derivable"),
  "bunctmy01": ("B", "bunct01my = rmcig", "rmcig national", "not derivable"),
  "bunctmy02": ("B", "bunct02my = minden", "minden national", "not derivable"),
  "pdimy":    ("B", "pdimy = pmacc if paccomp==2", "national", "not derivable"),
  "phlmy":    ("B", "pinmy = pminv", "pminv national", "not derivable"),
  "poamy":    ("B", "poamy = pmlav", "pmlav national", "not derivable"),
  "psumy":    ("B", "psumy = pmrev", "pmrev national", "not derivable"),
  "l01":      ("B", "built from redcom and the dalco* national indicators", "national",
               "not derivable"),
  "bfa":      ("B", "sum of bfaem, bfap, bfase, bmase, bfaco, bmals, bchot, bfaun01, "
               "bfaun02, each national", "national", "not derivable"),
  "bmase":    ("C", "not included in the original SILC data anymore", "-",
               "the codebook states it is not derived"),
  "xhchm":    ("C", "not recorded in SILC any more, set to 0 for everyone", "-",
               "the codebook sets it to zero"),
  "bhl":      ("C", "NOT DERIVED", "-", "the codebook states it is not derived"),
  "yiyiv":    ("C", "calibrated against external statistics, not used in the baseline", "-",
               "not used in the baseline"),
  "kfbcc":    ("C", "no recipe published", "PY021G carries the company car",
               "not derived: no published recipe, and the ES/EL kfb recipe may not be "
               "transferred to Italy"),
  "ypt00":    ("C", "no recipe published", "-", "not derived: no published recipe"),
  "ypt01":    ("C", "no recipe published", "-", "not derived: no published recipe"),
  "xs06111":  ("C", "no recipe published", "-",
               "consumption share, supplied by the consumption-tax add-on, not by the input"),
  "xs06121":  ("C", "no recipe published", "-",
               "consumption share, supplied by the consumption-tax add-on, not by the input"),
 },
 "EL": {
  "tpr":      ("A", "hy120g/12*hx010, shared between the oldest member and their partner",
               "HY120G", "populate"),
  "yot":      ("A", "hy110g/12*hx010 shared equally between people under 16", "HY110G",
               "populate"),
  "xhcrt":    ("A", "hh060*hx010", "HH060", "populate"),
  "xhcmomi":  ("A", "hy100g/12*hx010", "HY100G", "populate"),
  "xhc":      ("A", "hh070*hx010", "HH070", "populate"),
  "xhcot":    ("A", "xhc - xhcrt - xhcmomi", "HH070,HH060,HY100G", "populate"),
  "xmpot":    ("A", "xmp - xmpam, with xmpam = hy131g/12", "HY130G,HY131G", "populate"),
  "tad":      ("A", "hy145n/12*hx010", "HY145N", "populate"),
  "tis":      ("A", "hy140g/12", "HY140G", "populate"),
  "xpp":      ("A", "py035g/12*hx010", "PY035G", "populate"),
  "kfb":      ("A", "py020g/12*hx010", "PY020G", "populate"),
  "yds":      ("A", "hy020/12*hx010", "HY020", "populate"),
  "dec":      ("A", "pe021 recoded, 0 if pe010==2", "PE021,PE010", "populate"),
  "loc":      ("A", "ISCO-2digit pl051a -> 1-digit loc", "PL051A",
               "populate (no live Greek policy reads it; it is the input to the "
               "published lochz fallback)"),
  "afc":      ("A", "(yiy*12)/0.00302, the rate the codebook states", "HY090G",
               "not derived: asset variable, reported rather than derived"),
  "yemnr":    ("A", "published as zero: 'Non-reported employment income: equal to zero'",
               "n/a", "already correct at zero"),
  "ysenr":    ("A", "published as zero: 'Non-reported self-employment earnings: equal to "
               "zero'", "n/a", "already correct at zero"),
  "lochz":    ("B", "em06; where em06 is missing, a published fallback on lpmfc, loc, lin "
               "and les", "em06 national; lin needs PL111A, shipped empty",
               "not derivable: the fallback needs lin"),
  "drgn2":    ("B", "db040 mapped EL51..EL65 -> NUTS-2", "DB040 carries NUTS-1 only",
               "not derivable"),
  "amrar":    ("B", "sk02_2", "national", "not derivable: national or administrative source"),
  "amolv":    ("B", "pe04_3", "national", "not derivable"),
  "lpm":      ("B", "em03, ea17, ie01", "national", "not derivable"),
  "lpmfr":    ("B", "sm02_1k / ss02_1k / sb02_1k recoded", "national", "not derivable"),
  "ddita":    ("B", "apd01_* and apd04/apd05", "national", "not derivable"),
  "bdi":      ("B", "sb02_04*, sb02_05*", "national", "not derivable"),
  "bunot":    ("B", "eu02_0*", "national", "not derivable"),
  "bunnc":    ("B", "kb02_032, kb02_033", "national", "not derivable"),
  "bfaot":    ("B", "oe02_*", "national", "not derivable"),
  "bmact":    ("B", "oe02_052, oe02_053", "national", "not derivable"),
  "bsaot":    ("B", "kb02_*", "national", "not derivable"),
  "boanc":    ("B", "kb02_072, kb02_073, kb02_102, kb02_103", "national", "not derivable"),
 },
}


def _auto_class(cbrow, cols):
    """Classify a variable that is not in CLASS above.

    Every variable read by five or more live policies, and every variable in the Greek and
    Spanish lists, is classified by hand in CLASS. This handles the Italian tail, where the
    same answer recurs: the recipe names a national-SILC variable. It is deliberately
    conservative, and it never returns group 1: a machine-read recipe is not enough to
    justify populating anything, so anything this function would call derivable comes back
    as group 3 for a human to look at.
    """
    rec = (cbrow.get("recipe") or "").strip()
    first = rec.splitlines()[0][:120] if rec else ""
    if not rec or rec.lower() in ("nan", "(blank)"):
        return "C", "", "-", "no recipe published for this country"
    low = rec.lower()
    if "not derived" in low or "no longer" in low or "not recorded" in low \
            or "not included in the original silc" in low:
        return "C", first, "-", "the codebook states it is not derived"
    if low.strip() == "simulated" or low.startswith("simulated"):
        return "C", first, "-", "simulated by the model, not an input to supply"
    named = {t.upper() for t in FIELD.findall(rec)}
    resolvable = {t for t in named
                  if any(c.startswith(t) and cols[c][2] > 0 for c in cols)}
    if "national" in low or "_nsilc" in low or "_e" in low or "_d" in low or named - resolvable:
        return ("B", first,
                "national or production source" if not (named - resolvable)
                else ", ".join(sorted(named - resolvable)) + " not usable in the release",
                "not derivable from the public release")
    return "C", first, ", ".join(sorted(resolvable)) or "-", "needs a human decision"


def _silc_file(cc, letter):
    return glob.glob(os.path.join(SILC_ROOT, f"{cc}_CROSS", "2024", f"UDB_c*{letter}.csv"))[0]


def silc_columns(cc):
    """{column: (file letter, n_nonnull, n_nonzero)} for one country's 2024 c-files."""
    cols = {}
    for letter in "DRPH":
        df = pd.read_csv(_silc_file(cc, letter), low_memory=False)
        for c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            cols[c.upper()] = (letter, int(s.notna().sum()), int((s.fillna(0) != 0).sum()))
    return cols


def codebook(cc):
    df = pd.read_excel(CODEBOOK, sheet_name=cc, header=2)
    df.columns = [str(c).strip() for c in df.columns]
    out = {}
    for _, r in df.iterrows():
        n = str(r.get("Variable", "")).strip()
        if n and n.lower() != "nan":
            out[n] = {
                "label": str(r.get("Label", "") or "").strip(),
                "recipe": str(r.get("Notes: derivation from original data, and comments",
                                    "") or "").strip(),
            }
    return out


def read_lists(cc, engine):
    """The engine's own read-list, and the converter's populated columns."""
    import importlib
    cfg = CC_CFG[cc]
    cobj = engine.load_model().countries[cc]
    template = list(cobj.load_data(cfg["train"]).columns)
    conv = importlib.import_module(cfg["mod"])
    real = getattr(conv, cfg["fn"])(template)[0]
    key = f"{cfg['system']}/{cfg['dataset']}"

    keep, forced = [c for c in IDCOLS if c in real.columns], []
    reads = []
    for _ in range(12):
        engine.NOT_FOUND.clear()
        try:
            engine.run(cobj, cfg["system"], real[keep].copy(), cfg["dataset"])
            reads = list(engine.NOT_FOUND.get(key, []))
            break
        except Exception as exc:                                   # noqa: BLE001
            unknown = sorted(set(re.findall(r"unknown variable (\w+)", str(exc))))
            if not unknown:
                with open(engine.RUN_LOG, encoding="utf-8", errors="replace") as fh:
                    unknown = sorted(set(re.findall(r"unknown variable (\w+)", fh.read())))
            unknown = [u for u in unknown if u in real.columns and u not in keep]
            if not unknown:
                raise
            keep += unknown
            forced += unknown
    engine.NOT_FOUND.clear()
    engine.run(cobj, cfg["system"], real, cfg["dataset"])
    missing_cols = list(engine.NOT_FOUND.get(key, []))

    populated = [c for c in real.columns
                 if np.any(pd.to_numeric(real[c], errors="coerce").fillna(0.0).to_numpy() != 0)]
    reads_all = sorted(set(reads) | set(missing_cols) | set(forced))
    return {
        "reads": reads_all,
        "forced": sorted(set(forced)),
        "missing_cols": sorted(missing_cols),
        "populated": sorted(set(reads_all) & set(populated)),
        "zero": sorted(v for v in reads_all if v not in set(populated)),
        "n_template": len(template),
    }


def spine(cc, engine):
    """{variable: [live policies that mention it]} on the 2023 system."""
    sysobj = engine.load_model().countries[cc].systems[CC_CFG[cc]["system"]]
    hits, n_live = {}, 0
    for p in sysobj.policies:
        if str(getattr(p, "switch", "")).lower() not in ("on", "toggle"):
            continue
        n_live += 1
        for f in (getattr(p, "functions", None) or []):
            if str(getattr(f, "switch", "")).lower() not in ("on", "toggle"):
                continue
            for par in (getattr(f, "parameters", None) or []):
                val = getattr(par, "value", "")
                nm = getattr(par, "name", "") or ""
                toks = set(TOKEN.findall(val if isinstance(val, str) else "")) | set(
                    TOKEN.findall(nm))
                for t in toks:
                    hits.setdefault(t, set()).add(p.name)
    return {k: sorted(v) for k, v in hits.items()}, n_live, len(sysobj.policies)


def main(to_stdout):
    # The engine must be audible: BENEFITS_ENGINE_QUIET=1 suppresses the connector's
    # warning capture, and the warning IS the read-list this script is built on.
    os.environ.pop("BENEFITS_ENGINE_QUIET", None)
    import engine
    rows, meta = {}, {}
    for cc in ("ES", "IT", "EL"):
        cb = codebook(cc)
        cols = silc_columns(cc)
        rl = read_lists(cc, engine)
        sp, n_live, n_pol = spine(cc, engine)
        out = []
        for v in rl["zero"]:
            cbrow = cb.get(v, {})
            if v in CLASS.get(cc, {}):
                g, recipe, src, decision = CLASS[cc][v]
            else:
                g, recipe, src, decision = _auto_class(cbrow, cols)
            out.append({
                "var": v,
                "label": (cbrow.get("label", "") or "").splitlines()[0],
                "group": g, "recipe": recipe, "source": src, "decision": decision,
                "policies": sp.get(v, []),
                "n_pol": len(sp.get(v, [])),
                "in_codebook": v in cb,
            })
        out.sort(key=lambda r: (r["group"], -r["n_pol"], r["var"]))
        rows[cc] = out
        meta[cc] = {"reads": len(rl["reads"]), "populated": len(rl["populated"]),
                    "zero": len(rl["zero"]), "n_live_policies": n_live,
                    "n_policies": n_pol, "n_template": rl["n_template"],
                    "missing_cols": rl["missing_cols"], "forced": rl["forced"]}
        print(f"{cc}: reads {meta[cc]['reads']}, populated {meta[cc]['populated']}, "
              f"zero {meta[cc]['zero']}", file=sys.stderr)

    lines = ["# The input conversion inventory", "",
             "Generated by `europe/model/input_inventory.py`. Every row is machine-read: the "
             "read-list from the engine, the recipe from the shipped codebook, the field "
             "presence from the 2024 user database itself. The group and the decision are "
             "judgements, held in the script so that each one is visible.", "",
             "## How the read-list was obtained", "",
             "The engine prints, once per run, the line `Warning: Variable(s) ... not found "
             "in user-provided lists`. Give it a frame carrying only the identifiers and the "
             "weight, and that line is the executed spine's own read-list, in the engine's "
             "words rather than in ours. Two things it does not say, both established by "
             "measurement rather than assumed:", "",
             "* Italy's `SetDefault_it` uses two consumption variables inside an `ArithOp` "
             "formula, where a variable absent from the data is an error rather than a "
             "default, so the minimal run aborts until `xs06111` and `xs06121` are supplied. "
             "They are added back and counted as read.",
             "* A variable a `SetDefault` covers never appears in the warning, because the "
             "engine has a value for it. For Spain that hides `pdicm`, `pdinc`, `poaot`, "
             "`pdiot`, `bunot` and others, each of which the model's own SetDefault sets to "
             "zero for this dataset class. Where the model itself declares a zero default "
             "for a dataset like ours, this build leaves it at zero.", "",
             "A separate measurement settles what SetDefault does to a variable the input "
             "does supply: **nothing**. Feeding `yemmy` and `bunctpc` values that Spain's "
             "SetDefault would set to 12 and 0 leaves both untouched in the output frame. "
             "Supplied columns win, so a populated component is respected.", "",
             "## What the table shows", "",
             "Five findings change what can be populated, and three of them correct an "
             "expectation the task carried in:", "",
             "1. **Spain's pension routing is wrong today, not merely incomplete.** The "
             "codebook puts `poa00` at `py102g`, the old-age contributory pension, and gives "
             "`poacm` `py101g` and `poanc` `py103g` separately. The conversion currently "
             "routes the whole `PY100G` aggregate into `poa00`. The same applies to "
             "survivors (`psuwd00` is `py112g` and only for the widowed) and to disability "
             "(`pdi00` is `py132g`). The identities hold exactly in the 2024 release: "
             "`PY100G = PY101G + PY102G + PY103G` to the euro, and likewise for `PY110G` "
             "and `PY130G`.",
             "2. **Greece's property tax is derivable and is close to the external figure.** "
             "`tpr` is `hy120g/12`, `HY120G` is present for 8,712 Greek households, and it "
             "grosses to EUR 1,562.7 m against the EUR 1,575 m the Country Report gives for "
             "ENFIA. The live 2023 branch of `tpr_el` computes `tpr_s = tpr - i_tpr_red`, "
             "and the reduction only applies to income years before 2019, so the read input "
             "passes through unchanged. This is the whole of residual EL-4.",
             "3. **Italy's unemployment components are not derivable.** `bunct01` is "
             "`rmcig*cig_e` and `bunct02` is `minden*inden_e`, both national. So is the "
             "education, child and housing-cost group the task expected to find: `bchot` is "
             "`indmen*ind_e`, `xhcmo` is `pagmut_e`, `bhl` is stated as NOT DERIVED. Italy's "
             "derivable set is seven variables, not the larger set anticipated.",
             "4. **There is no published EUROMOD rule mapping occupation to collar.** Only "
             "Austria and Italy define `lcl` at all, and both derive it from a national "
             "variable. The only collar rule EUROMOD itself states for a dataset that does "
             "not carry `lcl` is `SetDefault_it`'s `lcl = 1` for training and hypothetical "
             "data, which is all blue collar. The proxy this build uses is therefore ours "
             "and is labelled as ours.",
             "5. **`PL111A` ships empty in all three countries.** The column exists and "
             "carries no values, so `lindi` cannot be built, which leaves Spain's "
             "agricultural contribution group unable to fire and the Greek `lochz` fallback "
             "unable to be evaluated.", ""]
    for cc in ("ES", "IT", "EL"):
        m = meta[cc]
        lines += [f"## {CC_CFG[cc]['name']} ({cc})", "",
                  f"The live {CC_CFG[cc]['system']} spine is {m['n_live_policies']} of "
                  f"{m['n_policies']} policies. It reads **{m['reads']}** input variables. "
                  f"The conversion populates **{m['populated']}** and leaves "
                  f"**{m['zero']}** at zero.", ""]
        for g, title in (("A", "Group 1: derivable from the public database by a published recipe"),
                         ("B", "Group 2: not derivable, the source is not in the public release"),
                         ("C", "Group 3: derivable in principle, no complete published recipe")):
            sel = [r for r in rows[cc] if r["group"] == g]
            if not sel:
                continue
            lines += [f"### {title} ({len(sel)})", "",
                      "| variable | live policies | reads it | source | recipe | decision |",
                      "|---|---:|---|---|---|---|"]
            for r in sel:
                pol = ", ".join(r["policies"][:4]) + (" ..." if len(r["policies"]) > 4 else "")
                lines.append(f"| `{r['var']}` | {r['n_pol']} | {pol or 'none'} | "
                             f"{r['source'] or '-'} | {r['recipe'][:120]} | {r['decision']} |")
            lines.append("")
    text = "\n".join(lines)
    if to_stdout:
        print(text)
    else:
        path = os.path.join(EUROPE, "docs", "INPUT_CONVERSION_INVENTORY.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("written", path, file=sys.stderr)
    with open(os.path.join(EUROPE, "docs", "input_inventory.json"), "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "rows": rows}, fh, indent=1)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true")
    raise SystemExit(main(ap.parse_args().print))
