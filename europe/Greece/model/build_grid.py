"""
build_grid.py -- compute the Analyst dial response surfaces (dial_grid.json) for the
EU countries by running each country's REAL-BUILD logic across an 11-point magnitude
grid per dial, the 5-point epsilon grid at each point, 10 kappa-weighted decile
contributions per epsilon, and winners/losers shares.

Real-build logic, not the generic pipeline:
  ES earnings = [yem, yse]; IT = [yem, yse, yseev]; EL = [yem, yse, yemre, ysere].
  Unemployment flips: a NESTED, fixed-permutation sample (seed 20240) so the surface
  is monotone in pp (the validated single-point reform draws a fresh sample; the
  nested construction is statistically equivalent at a given count and is the correct
  shape for a response surface; documented).

min_income lever (per country, most-faithful-first):
  base   -- scale the base-amount constant (models payment level AND eligibility entry).
  topup  -- income-floor top-up: raise the simulated minimum-income benefit for existing
            recipients by m%, eligibility held at baseline (a deterministic add-on, not a
            EUROMOD constant). Used only where base-scaling is non-monotone. The decile and
            epsilon machinery is IDENTICAL to every other dial (same adapter for the
            baseline, same point_from_pu); only the reform injection differs.

WEVM via the canonical europe/wevm/wevm.py (sha256 6f696baa, not forked): headline and
deciles from W.living_standard / W._weighted_median / W._income_floor / W.social_weight,
each point cross-checked against W.wevm() and the eps=0 decile row against W.wevm_by_decile.
Units: EUR millions (UK convention); native 2023 income reference year; no uprating/PPP.

Data-free: aggregates only -> europe/<Country>/outputs/dial_grid.json (canonical per-country location).

Usage:
  python build_grid.py ES                              # full 5-dial, min_income base-scaling
  python build_grid.py ES --min-income topup --splice  # rebuild only min_income (topup) into existing grid
  python build_grid.py ES --quick                      # dry-run: gdp_shock only, 3 magnitudes
"""
import argparse
import importlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

EUROPE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(EUROPE, "pipeline"))
sys.path.insert(0, os.path.join(EUROPE, "wevm"))
for d in ("es_real", "it_real", "el_real"):
    sys.path.insert(0, os.path.join(EUROPE, d))

import engine        # noqa: E402
import config        # noqa: E402
import adapter       # noqa: E402
import reforms       # noqa: E402
import wevm as W     # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

EPS = list(W.EPS_GRID)
YEAR = 2023
MILLION = 1e6

CC_CFG = {
    "ES": dict(dataset="ES_2024_b1_2015_03_e2", system="ES_2023",
               train="ES_training_data", mod="convert_full",
               fn="convert_es_2024_full", earn=["yem", "yse"]),
    "IT": dict(dataset="IT_2024_a1_2015_03_e2", system="IT_2023",
               train="IT_training_data", mod="convert_it",
               fn="convert_it_2024_full", earn=["yem", "yse", "yseev"]),
    "EL": dict(dataset="EL_2024_c1_2015_03_e2", system="EL_2023",
               train="EL_training_data", mod="convert_el",
               fn="convert_el_2024_full", earn=["yem", "yse", "yemre", "ysere"]),
}

MAGS = {
    "gdp_shock":          [0, -1, -2, -3, -4, -5, -6, -7, -8, -9, -10],
    # pit_give is the one two-sided dial: negative cuts the first-bracket rate, positive
    # raises it. The negative leg is the committed 11-point grid, unchanged; the positive
    # leg mirrors its step so the two halves interpolate on the same spacing.
    "pit_give":           [-5, -4.5, -4, -3.5, -3, -2.5, -2, -1.5, -1, -0.5, 0,
                           0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5],
    "child_benefit_up":   [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
    "min_income_up":      [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50],
    "unemployment_shock": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
}
DIAL_ORDER = ["gdp_shock", "pit_give", "child_benefit_up", "min_income_up", "unemployment_shock"]
UNITS = {"gdp_shock": "% change", "pit_give": "pp change", "child_benefit_up": "% change",
         "min_income_up": "% change", "unemployment_shock": "pp"}
LABELS = {
    "ES": {"gdp_shock": "GDP / market-income shock", "pit_give": "IRPF first-bracket rate change",
           "child_benefit_up": "Means-tested child allowance (bch00)",
           "min_income_up": "Minimum income (IMV, bsa00)", "unemployment_shock": "Unemployment shock"},
    "IT": {"gdp_shock": "GDP / market-income shock", "pit_give": "IRPEF first-bracket rate change",
           "child_benefit_up": "Assegno Unico Universale (bau_it)",
           "min_income_up": "Assegno di Inclusione (bsa_Amount1)", "unemployment_shock": "Unemployment shock"},
    "EL": {"gdp_shock": "GDP / market-income shock", "pit_give": "PIT first-bracket rate change",
           "child_benefit_up": "Child benefit A21 (bch)",
           "min_income_up": "Minimum income KEA (bsa00)", "unemployment_shock": "Unemployment shock"},
}

# min_income income-floor top-up: candidate simulated recipient benefit column, per country.
IMV_CANDIDATES = {"ES": ["bsa00_s"], "IT": ["bsadi_s", "bsa_s", "bsa00_s"], "EL": ["bsa00_s", "bsa_s"]}
# INSTRUMENT NAMING. Each country's minimum income is written
# by its instrument code: IMV, AdI, KEA. The Italian one was written ADI, AdI and ADI/RdC
# in different places; AdI is now the only form, and RdC is a different and superseded
# scheme rather than a spelling of this one. Where the scheme name is written out it is
# "Assegno di Inclusione (AdI)" and IT IS THIS PROJECT'S NAME FOR THE INSTRUMENT, not a
# label read from the model: what the model supplies is the instrument code bsamm_s and
# the constant $bsa_Amount1 in system IT_2023, and those are the identifiers to quote when
# a claim has to be checkable.
IMV_NAME = {"ES": "IMV", "IT": "AdI", "EL": "KEA"}
TOPUP_LABEL = {"ES": "Minimum income (IMV): higher guarantee for existing recipients",
               "IT": "Minimum income (AdI): higher payment to existing recipients",
               "EL": "KEA minimum income: higher payment to existing recipients"}
# LABELS["IT"]["min_income_up"] deliberately keeps the string the three shipped surfaces
# already carry. It is grid metadata: the tool face reads dial_text.label and falls back to
# this only if that is absent, which it never is, so it reaches no page. Changing it here
# would put this file out of step with a surface this tree cannot rebuild, and the
# duplication between code and surface is the hazard the project guards hardest.


def topup_scope(cc):
    return (f"Models a more generous payment to households already receiving {IMV_NAME[cc]}; "
            "eligibility held at baseline. Does NOT model take-up expansion or newly-eligible entry.")


def magnitude_to_reform(profile_reform, mag):
    r = dict(profile_reform)
    t = r["type"]
    if t in ("const_scale", "param_mutate_scale", "income_scale"):
        r["factor"] = 1.0 + mag / 100.0
    elif t == "rate_delta":
        r["delta"] = mag / 100.0
    elif t == "unemployment":
        r["pp"] = mag / 100.0
    return r


def nested_employed(real):
    employed = real.index[real["les"].isin(config.LES_EMPLOYED)
                          & (real["dag"] >= 18) & (real["dag"] < 65)]
    n_unemp = int((real["les"] == config.LES_UNEMPLOYED).sum())
    lf = len(employed) + n_unemp
    perm = np.random.default_rng(20240).permutation(employed.to_numpy())
    return perm, lf


def apply_unemployment(real, perm, lf, pp, earn_vars):
    d = real.copy()
    k = min(int(round(pp * lf)), len(perm))
    pick = perm[:k]
    d.loc[pick, "les"] = config.LES_UNEMPLOYED
    for v in earn_vars:
        if v in d.columns:
            d.loc[pick, v] = 0
    return d, int(k)


def run_point(cobj, sysobj, sysname, dataset, real, earn, perm, lf, reform):
    t = reform["type"]
    if t in ("const_scale", "rate_delta"):
        consts, _ = reforms.build_const_overwrites(sysobj, reform)
        return engine.run(cobj, sysname, real, dataset, constants=consts).outputs[0]
    if t == "income_scale":
        r2 = dict(reform); r2["vars"] = earn
        return engine.run(cobj, sysname, reforms.income_scale(real, r2), dataset).outputs[0]
    if t == "unemployment":
        d, _ = apply_unemployment(real, perm, lf, reform["pp"], earn)
        return engine.run(cobj, sysname, d, dataset).outputs[0]
    if t == "param_mutate_scale":
        out, _ = reforms.run_with_param_mutation(cobj, sysobj, sysname, real, dataset, reform)
        return out
    raise ValueError(t)


def point_from_pu(base_pu, ref_pu):
    """Canonical WEVM point from a baseline and a reform per-unit frame, in EUR millions.
    Identical machinery for every dial (engine or top-up); only ref_pu's source differs."""
    ev = W.compute_ev(pd.concat([base_pu, ref_pu], ignore_index=True))
    y = W.living_standard(ev, True)
    w = ev["survey_weight"].to_numpy(float)
    evv = ev["ev"].to_numpy(float)
    y_ref = W._weighted_median(y, w)
    floor = W._income_floor(y, w, None, y_ref)
    order = np.argsort(y, kind="stable")
    cum = np.empty_like(y, float)
    cum[order] = np.cumsum(w[order]) / w.sum()
    dec = np.clip((cum * 10).astype(int), 0, 9) + 1

    wevm, deciles = [], []
    for eps in EPS:
        kappa = W.social_weight(y, eps, y_ref, floor)
        contrib = w * kappa * evv
        deciles.append([round(float(contrib[dec == d].sum() / MILLION), 3) for d in range(1, 11)])
        wevm.append(round(float(contrib.sum() / MILLION), 3))

    chk = W.wevm(ev, equivalise=True).iloc[0]
    for i, eps in enumerate(EPS):
        if abs(float(chk[f"wevm_eps_{eps:g}"]) / MILLION - wevm[i]) > 1e-3:
            raise AssertionError(f"wevm eps={eps} {wevm[i]} != canonical")
    dby = {int(r.decile): r.total_ev / MILLION for r in W.wevm_by_decile(ev, equivalise=True).itertuples()}
    for d in range(1, 11):
        if abs(dby.get(d, 0.0) - deciles[0][d - 1]) > 1e-3:
            raise AssertionError(f"eps0 decile {d} mismatch vs wevm_by_decile")

    winners = round(float(100 * w[evv > 0].sum() / w.sum()), 1)
    losers = round(float(100 * w[evv < 0].sum() / w.sum()), 1)
    return wevm, deciles, winners, losers


def point_from_output(out, base_pu, cc, scen):
    ru = adapter.euromod_to_per_unit(out, cc, YEAR, scen)
    return point_from_pu(base_pu, ru)


# ---------------------------------------------------------------------------
# Fiscal and poverty lenses, emitted per point beside the welfare figures.
#
# Fiscal reproduces europe/common/re_emit.py exactly (the committed producer of the
# fiscal sub-object): weighted per-household ils_tax / ils_ben / ils_sicdy / ils_dispy,
# summed within idhh, x12, x survey weight, differenced against baseline, EUR millions,
# with net_exchequer_cost_m = benefit_delta_m - income_tax_delta_m - sic_delta_m.
# Emitting it here rather than in a second pass means one engine run per point, not two.
#
# Poverty follows the UK surface's field names and convention exactly: LEVELS not deltas,
# headcounts of people in thousands, gaps as amounts in millions, and the two denominators
# a rate needs emitted beside them, so the denominator decision stays in the tool layer.
#
# The four AHC and absolute fields are null for the EU. The EUROMOD per-unit layer carries
# no housing-cost concept, and no sourced fixed-base-year line exists for ES, IT or EL.
# Null is what the UK builder itself emits when a column is absent (_point_poverty returns
# None), so the schema is the same object in all four countries. Never an invented number.
# ---------------------------------------------------------------------------
FISCAL_MAP = {"income_tax_delta_m": "ils_tax", "benefit_delta_m": "ils_ben",
              "sic_delta_m": "ils_sicdy", "sic_employer_delta_m": "ils_sicer",
              "net_income_delta_m": "ils_dispy"}
FISCAL_FIELDS = ["income_tax_delta_m", "benefit_delta_m", "sic_delta_m",
                 "sic_employer_delta_m", "net_income_delta_m", "net_exchequer_cost_m"]
MONTHS = 12


def fiscal_aggregate(out, col):
    per_hh = out.groupby("idhh")[col].sum() * MONTHS
    wt = out.groupby("idhh")["dwt"].first()
    return float((per_hh * wt).sum()) / MILLION


def point_fiscal(out):
    d = {k: round(fiscal_aggregate(out, col) - base_fisc_global[k], 3)
         for k, col in FISCAL_MAP.items()}
    # Employer contributions are exchequer revenue and belong in the net cost, matching
    # the UK, whose identity folds in ni_employer. sic_delta_m maps to ils_sicdy, which is
    # employee plus self-employed plus other and EXCLUDES the employer leg, so it has to
    # enter separately or the two sides of the tool disagree about what an exchequer cost
    # is. Reported as its own field as well, so summing the components reproduces the
    # headline. Zero for every policy dial in all three countries, because none of them
    # changes employment; it is the two shocks that destroy jobs and so destroy the
    # contributions. Italy simulates all seven components, every one of them gated on the
    # blue/white-collar contract class lcl. EU-SILC does not carry lcl, so convert_it.py
    # derives it from occupation by a stated proxy of ours; without it no employer
    # component fires at all, and with it Italy's employer leg is non-zero on every shock
    # point. See DATA_ISSUES_FOR_TECHNICAL_REPORT.md IT-9.
    d["net_exchequer_cost_m"] = round(
        d["benefit_delta_m"] - d["income_tax_delta_m"] - d["sic_delta_m"]
        - d["sic_employer_delta_m"], 3)
    return {k: d[k] for k in FISCAL_FIELDS}


def zero_fiscal():
    return {k: 0.0 for k in FISCAL_FIELDS}


def equivalised(pu):
    """OECD-modified equivalised household disposable income, and the scale itself."""
    scale = np.maximum(
        W._oecd_modified(pu["n_adults"].to_numpy(), pu["n_children"].to_numpy()), 1e-6)
    return pu["net_income"].to_numpy(float) / scale, scale


def arop_line(pu):
    """The at-risk-of-poverty threshold for one state: 60% of that state's own weighted
    median equivalised income. Raw, unrounded, so it can be held as an anchor."""
    w = pu["survey_weight"].to_numpy(float)
    y, _ = equivalised(pu)
    return W._income_floor(y, w, None, W._weighted_median(y, w))


def point_poverty(pu, anchor=None):
    """Poverty for one state, on two thresholds.

    RELATIVE moves with the state: 60% of that point's own median. It is the published
    AROP convention and it is what the social weight uses as its floor, but it is not a
    clean reform comparison, because a reform that lowers the median lowers the line and
    can cut the measured count without moving anyone's income up.

    ANCHORED holds the threshold computed once at the zero-magnitude baseline point and
    applies it at every point of every dial. It is internally defined, so it needs no
    external source, and it is the right measure for a reform against its own baseline.

    ANCHORED IS NOT THE ABSOLUTE MEASURE. The absolute fields stay null: those mean a
    fixed external base year, and no sourced one exists for ES, IT or EL. Anchored-at-
    baseline is a different concept and is named so the two cannot be confused.
    """
    w = pu["survey_weight"].to_numpy(float)
    people = pu["n_adults"].to_numpy(float) + pu["n_children"].to_numpy(float)
    y, scale = equivalised(pu)
    net = pu["net_income"].to_numpy(float)
    line = W._income_floor(y, w, None, W._weighted_median(y, w))
    held = anchor if anchor is not None else (
        anchor_line_global if anchor_line_global is not None else line)
    poor = y < line
    gap = np.maximum(line * scale - net, 0.0)
    return {
        "relative_bhc_headcount_k": round(float((people * w)[poor].sum()) / 1e3, 3),
        "relative_ahc_headcount_k": None,
        "absolute_bhc_headcount_k": None,
        "absolute_ahc_headcount_k": None,
        "anchored_bhc_headcount_k": round(float((people * w)[y < held].sum()) / 1e3, 3),
        "anchored_ahc_headcount_k": None,
        "anchored_bhc_threshold_cur": round(float(held), 3),
        "poverty_gap_bhc_m": round(float((gap * w).sum()) / MILLION, 3),
        "poverty_gap_ahc_m": None,
        "population_k": round(float((people * w).sum()) / 1e3, 3),
        "units_k": round(float(w.sum()) / 1e3, 3),
    }


def zero_point(mag, poverty=None):
    """The baseline point. Fiscal is a delta, so it is zero; poverty is a level, so it is
    the baseline level, not zero."""
    return {"wevm": [0.0] * len(EPS), "deciles": [[0.0] * 10 for _ in EPS],
            "winners_pct": 0.0, "losers_pct": 0.0, "magnitude": mag,
            "fiscal": zero_fiscal(),
            "poverty": dict(poverty if poverty is not None else base_poverty_global)}


def detect_imv_col(cc, base_out):
    for c in IMV_CANDIDATES[cc]:
        if c in base_out.columns:
            return c
    cand = [c for c in base_out.columns if c.startswith("bsa") and c.endswith("_s")]
    return cand[0] if cand else None


def build_min_income_topup(cc, base_pu, base_out):
    """Income-floor top-up dial: raise the recipient minimum-income benefit by m%
    (eligibility held). ref_pu = baseline per-unit with net_income += m% * recipient benefit."""
    imv_col = detect_imv_col(cc, base_out)
    if imv_col is None:
        raise RuntimeError(f"{cc}: no minimum-income recipient output column found")
    idx = base_pu["unit_id"].astype(float).astype("int64").to_numpy()
    imv_map = (base_out.groupby("idhh")[imv_col].sum() * 12).to_dict()
    imv_hh = np.array([imv_map.get(i, 0.0) for i in idx], float)
    base_net = base_pu["net_income"].to_numpy(float)
    w = base_pu["survey_weight"].to_numpy(float)
    recip_w = float(w[imv_hh > 1.0].sum())
    outlay_m = float((w * imv_hh).sum()) / MILLION

    pts = []
    for m in MAGS["min_income_up"]:
        if m == 0:
            pts.append(zero_point(0)); continue
        ref = base_pu.copy()
        ref["net_income"] = base_net + (m / 100.0) * imv_hh
        ref["scenario"] = f"min_income_up__topup_m{m}"
        wevm, deciles, winners, losers = point_from_pu(base_pu, ref)
        # Analytic top-up: the whole cost is benefit spend, so tax and SIC are exactly
        # zero and the exchequer cost is m% of the baseline recipient outlay. Identical
        # to re_emit.py's MIN_INCOME_ANALYTIC branch.
        f = round((m / 100.0) * outlay_m, 3)
        pts.append({"wevm": wevm, "deciles": deciles, "winners_pct": winners,
                    "losers_pct": losers, "magnitude": m,
                    "fiscal": {"income_tax_delta_m": 0.0, "benefit_delta_m": f,
                               "sic_delta_m": 0.0, "sic_employer_delta_m": 0.0,
                               "net_income_delta_m": f, "net_exchequer_cost_m": f},
                    "poverty": point_poverty(ref)})
    dial = {
        "label": TOPUP_LABEL[cc],
        "lever": f"{imv_col} recipient top-up +m% (income-floor; deterministic add-on; baseline eligibility)",
        "unit": "% change", "baseline_magnitude": 0, "magnitudes": MAGS["min_income_up"],
        "points": pts, "scope_note": topup_scope(cc),
    }
    print(f"   [min_income TOPUP] recipients={recip_w:,.0f} hh, baseline outlay={outlay_m:,.1f} EUR m, "
          f"col={imv_col}; eps1 m=50 -> {pts[-1]['wevm'][2]:,.1f}m win={pts[-1]['winners_pct']}%")
    return dial


def build_engine_dial(cc, cobj, sysobj, sysname, dataset, real, earn, perm, lf, dial, profile):
    mags = MAGS[dial]
    pts = []
    for mag in mags:
        if mag == 0:
            pts.append(zero_point(0)); continue
        reform = magnitude_to_reform(profile[dial], mag)
        t0 = time.time()
        out = run_point(cobj, sysobj, sysname, dataset, real, earn, perm, lf, reform)
        ru = adapter.euromod_to_per_unit(out, cc, YEAR, f"{dial}__m{mag}")
        wevm, deciles, winners, losers = point_from_pu(base_pu_global, ru)
        pts.append({"wevm": wevm, "deciles": deciles, "winners_pct": winners,
                    "losers_pct": losers, "magnitude": mag,
                    "fiscal": point_fiscal(out), "poverty": point_poverty(ru)})
        exp = config.expected_sign(dial, mag)
        got = "+" if wevm[0] > 1e-6 else "-" if wevm[0] < -1e-6 else "0"
        flag = "" if got == exp else f"   SIGN CHECK: expected {exp}, got {got}"
        print(f"   [{dial:18} m={mag:>5}] eps1={wevm[2]:>12,.3f}m  win={winners:4.1f}% los={losers:4.1f}%  "
              f"({time.time()-t0:.1f}s){flag}")
    return {"label": LABELS[cc][dial],
            "lever": f"{profile[dial]['type']}: " + (
                ", ".join(n for n, _ in profile[dial].get("constants", []))
                or profile[dial].get("policy", "input transform")),
            "unit": UNITS[dial], "baseline_magnitude": 0, "magnitudes": mags, "points": pts}


base_pu_global = None       # set per build (engine dial helper reads it)
base_fisc_global = None     # baseline fiscal aggregates, the reference for every delta
base_poverty_global = None  # baseline poverty levels, the value the zero point carries
anchor_line_global = None   # AROP threshold held at the baseline, applied at every point


def build_country(cc, quick=False, min_income_mode="base", splice=False):
    global base_pu_global, base_fisc_global, base_poverty_global, anchor_line_global
    cfg = CC_CFG[cc]
    sysname, dataset = cfg["system"], cfg["dataset"]
    print(f"== build_grid {cc} (system {sysname}, dataset {dataset}) "
          f"min_income={min_income_mode}{' splice' if splice else ''} ==")
    engine.assert_matched_engine()
    mod = engine.load_model()
    cobj = mod.countries[cc]
    sysobj = engine.get_system(cobj, sysname)
    print("ENGINE:", engine.assert_matched_engine())
    template = list(cobj.load_data(cfg["train"]).columns)
    real = getattr(importlib.import_module(cfg["mod"]), cfg["fn"])(template)[0]
    earn = cfg["earn"]
    perm, lf = nested_employed(real)

    t0 = time.time()
    base_out = engine.run(cobj, sysname, real, dataset).outputs[0]
    base_pu = adapter.euromod_to_per_unit(base_out, cc, YEAR, "baseline")
    base_pu_global = base_pu
    base_fisc_global = {k: fiscal_aggregate(base_out, col) for k, col in FISCAL_MAP.items()}
    # The anchor is fixed here, once, before any point is computed. Every point of every
    # dial is then measured against it as well as against its own moving line.
    anchor_line_global = arop_line(base_pu)
    base_poverty_global = point_poverty(base_pu, anchor_line_global)
    print(f"   baseline run {time.time()-t0:.1f}s, households={base_pu.shape[0]}, labour_force={lf}")
    print(f"   baseline AROP {base_poverty_global['relative_bhc_headcount_k']:,.1f}k of "
          f"{base_poverty_global['population_k']:,.1f}k people, gap "
          f"{base_poverty_global['poverty_gap_bhc_m']:,.1f}m EUR; "
          f"anchor held at {anchor_line_global:,.2f} EUR equivalised")

    profile = config.PROFILES[cc]["reforms"]
    # Canonical per-country location: europe/<Country>/outputs/dial_grid.json. Resolve the
    # europe/ tree root from this file's path so the surface lands canonically whether run from
    # the shared europe/common/ copy or a per-country europe/<Country>/model/ copy.
    parts = os.path.normpath(os.path.abspath(__file__)).split(os.sep)
    if "europe" not in parts:
        raise RuntimeError("build_grid.py: could not locate the europe/ tree root")
    europe_root = os.sep.join(parts[:parts.index("europe") + 1])
    country_dir = {"ES": "Spain", "IT": "Italy", "EL": "Greece"}[cc]
    outdir = os.path.join(europe_root, country_dir, "outputs")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "dial_grid.json" if not quick else "dial_grid_quick.json")

    if splice:
        if not os.path.exists(path):
            raise FileNotFoundError(f"--splice needs an existing {path}")
        grid = json.load(open(path, encoding="utf-8"))
        dial = (build_min_income_topup(cc, base_pu, base_out) if min_income_mode == "topup"
                else build_engine_dial(cc, cobj, sysobj, sysname, dataset, real, earn, perm, lf,
                                       "min_income_up", profile))
        grid["dials"]["min_income_up"] = dial
        grid["meta"]["min_income_lever"] = ("income-floor top-up (recipients; eligibility held)"
                                            if min_income_mode == "topup" else "base-amount scaling")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        json.dump(grid, open(path, "w", encoding="utf-8"), indent=1)
        print(f"   spliced min_income ({min_income_mode}) into {path}")
        return path

    dial_keys = ["gdp_shock"] if quick else DIAL_ORDER
    dials = {}
    for dial in dial_keys:
        if quick and dial == "gdp_shock":
            mags = [0, -5, -10]
            pts = []
            for mag in mags:
                if mag == 0:
                    pts.append(zero_point(0)); continue
                out = run_point(cobj, sysobj, sysname, dataset, real, earn, perm, lf,
                                magnitude_to_reform(profile[dial], mag))
                ru = adapter.euromod_to_per_unit(out, cc, YEAR, f"{dial}__m{mag}")
                wevm, deciles, winners, losers = point_from_pu(base_pu, ru)
                pts.append({"wevm": wevm, "deciles": deciles, "winners_pct": winners,
                            "losers_pct": losers, "magnitude": mag,
                            "fiscal": point_fiscal(out), "poverty": point_poverty(ru)})
            dials[dial] = {"label": LABELS[cc][dial], "lever": "income_scale", "unit": UNITS[dial],
                           "baseline_magnitude": 0, "magnitudes": mags, "points": pts}
            continue
        if dial == "min_income_up" and min_income_mode == "topup":
            dials[dial] = build_min_income_topup(cc, base_pu, base_out)
        else:
            dials[dial] = build_engine_dial(cc, cobj, sysobj, sysname, dataset, real, earn, perm, lf,
                                            dial, profile)

    base_w = adapter.weighted_disposable(base_pu)
    grid = {
        "meta": {
            "country": cc, "year": YEAR, "eps_grid": EPS,
            "baseline_net_income_bn": round(base_w / 1e9, 4),
            "n_units_working_age_sample": int(base_pu["is_working_age"].sum()),
            "n_units": int(base_pu.shape[0]),
            # What the numbers cover. The EU builder runs over every household; the UK
            # builder filters to working-age units first. Same field names, different
            # populations, so the basis travels with the data instead of living in one
            # sentence on one panel. Harmonising the two populations is a separate job.
            "population_basis": {
                "scope": "all_households",
                "includes": "Every household in the EU-SILC sample. No age filter is applied.",
                "excludes": "Nothing.",
                "units_k": round(float(base_pu["survey_weight"].sum()) / 1e3, 3),
                "population_k": round(float(((base_pu["n_adults"] + base_pu["n_children"])
                                             * base_pu["survey_weight"]).sum()) / 1e3, 3),
                "summary": "All households, with no age filter.",
            },
            "min_income_lever": ("income-floor top-up (recipients; eligibility held)"
                                 if min_income_mode == "topup" else "base-amount scaling"),
            "note": (f"{cc} Analyst response surface. Single-reform magnitude grids; one lever per point; "
                     "baseline is the zero point of each dial. WEVM and decile contributions in EUR MILLIONS, "
                     "equivalised, median-anchored, AROP-floored. Native 2023 income reference year (EU-SILC "
                     "2024 wave); nominal EUR, no uprating, no PPP (downstream). Real-build logic per country "
                     "(ES yem/yse; IT +yseev; EL +yemre/ysere); unemployment flips nested for monotonicity."),
            "units": {
                "wevm": "EUR millions, welfare-weighted, versus baseline",
                "fiscal": "EUR millions versus baseline; net_exchequer_cost_m = benefit - tax - sic - sic_employer, "
                          "positive is a cost to the exchequer",
                "poverty": "levels, not deltas: headcounts of people in thousands, poverty gaps in EUR "
                           "millions, anchored_bhc_threshold_cur in EUR of equivalised annual income, with "
                           "population_k and units_k as the denominators a rate needs",
                # winners_pct and losers_pct sit on the same panel as poverty rows denominated
                # in people, and a reader who has just read one may take the other the same way.
                # The tool names the base on the face; this says it in the surface too.
                "winlose": "the weighted count of households with a gain, and with a loss, each "
                           "over the weighted count of all households, times 100. Shares of "
                           "households, not of people, unlike every poverty headcount in the same "
                           "object, which counts people. Both rows are labelled with this base on "
                           "the tool face.",
            },
            "poverty_basis": (
                "Two thresholds, both emitted at every point. RELATIVE (relative_*): 60% of that point's "
                "own weighted median equivalised (OECD-modified) household disposable income, the "
                "published AROP convention and the same line the social weight uses as its floor; it "
                "moves with the reform, so a reform that lowers the median lowers the line and can cut "
                "the measured count without raising anyone's income. ANCHORED (anchored_*): the same "
                "60%-of-median line computed once at the zero-magnitude baseline point and held fixed "
                "across every point of every dial, emitted as anchored_bhc_threshold_cur so it is auditable; "
                "internally defined, needing no external source, and the right comparison of a reform "
                "against its own baseline. ANCHORED IS NOT ABSOLUTE: the absolute_* fields mean a fixed "
                "EXTERNAL base year and stay null because no sourced one exists for ES, IT or EL. The "
                "AHC fields are null throughout because the EUROMOD per-unit layer carries no "
                "housing-cost concept. All other field names follow the UK surface exactly."),
            "rebuild": (
                "Built on EUROMOD v3.8.6, on a COMPLETED input conversion. Every input variable a "
                "live 2023 policy reads, for which the EUROMOD input data codebook publishes a "
                "recipe and whose sources the public EU-SILC user database carries, is populated "
                "from that recipe: Spain carries 68 populated input columns, Greece 55, Italy 44. "
                "The consequential ones are Spain's pension and unemployment decompositions and its "
                "rent, mortgage and private-pension deductions; Greece's property tax, which is the "
                "ENFIA the model reads and passes through; and Italy's contract class, without "
                "which no employer contribution fires at all. A surface is a function of its "
                "inputs, so reproducing a stored surface is not the test; the test is agreement "
                "with each country's own published EUROMOD baseline, recorded in "
                "europe/docs/BASELINE_VALIDATION.md. Conventions this surface holds: the stable "
                "sort in build_grid.point_from_pu and in wevm._weighted_median / "
                "wevm.wevm_by_decile, the two-sided pit_give grid, and the fiscal and poverty "
                "objects emitted in the same pass, fiscal by the method of re_emit.py. Poverty "
                "carries both a relative (moving) and an anchored (held at baseline) threshold; "
                "see poverty_basis."),
        },
        "dials": dials,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    json.dump(grid, open(path, "w", encoding="utf-8"), indent=1)
    print(f"   wrote {path}")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("country", choices=list(CC_CFG))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--min-income", choices=["base", "topup"], default="base")
    ap.add_argument("--splice", action="store_true", help="rebuild only min_income into the existing grid")
    args = ap.parse_args(argv)
    t = time.time()
    path = build_country(args.country, quick=args.quick, min_income_mode=args.min_income, splice=args.splice)
    print(f"DONE {args.country} in {time.time()-t:.0f}s -> {path}")


if __name__ == "__main__":
    main()
