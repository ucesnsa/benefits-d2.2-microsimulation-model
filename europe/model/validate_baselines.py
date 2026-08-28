"""validate_baselines.py -- one unmodified baseline per country, reported against the
figures each EUROMOD Country Report publishes.

This is the acceptance test for the completed conversion. It cannot be a reproduction
test: the inputs changed, so the outputs must change. What it does instead is compare the
build against the model's own published baseline and against the external aggregate each
Country Report gives beside it, for the five fiscal lines and the principal benefit
instruments, and for the four distributional statistics.

It runs on whichever converter is importable, so the same script measures the state
before and after a conversion change: point BENEFITS_CONVERTER_DIR at a directory holding
convert_full.py / convert_it.py / convert_el.py and it will import from there instead of
from the per-country model folders.

Aggregates only. Nothing is written except this script's own JSON report.

Usage:  python validate_baselines.py [ES IT EL] [--tag before]
"""
import argparse
import importlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EUROPE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EUROPE, "common"))
sys.path.insert(0, os.path.join(EUROPE, "common", "wevm"))
_ALT = os.environ.get("BENEFITS_CONVERTER_DIR")
if _ALT:
    sys.path.insert(0, _ALT)
else:
    for _d, _s in (("Spain", "es_real"), ("Italy", "it_real"), ("Greece", "el_real")):
        sys.path.insert(0, os.path.join(EUROPE, _d, "model", _s))

import engine        # noqa: E402
import adapter       # noqa: E402
import wevm as W     # noqa: E402

MONTHS = 12
MILLION = 1e6
YEAR = 2023

CC = {
    "ES": dict(name="Spain", system="ES_2023", dataset="ES_2024_b1_2015_03_e2",
               train="ES_training_data", mod="convert_full", fn="convert_es_2024_full"),
    "IT": dict(name="Italy", system="IT_2023", dataset="IT_2024_a1_2015_03_e2",
               train="IT_training_data", mod="convert_it", fn="convert_it_2024_full"),
    "EL": dict(name="Greece", system="EL_2023", dataset="EL_2024_c1_2015_03_e2",
               train="EL_training_data", mod="convert_el", fn="convert_el_2024_full"),
}

# The aggregate income lists every country model defines, plus the two contribution legs
# reported separately because the tool's exchequer identity separates them.
LISTS = ["ils_origy", "ils_earns", "ils_pen", "ils_ben", "ils_benmt", "ils_bennt",
         "ils_tax", "ils_taxin", "ils_taxwl", "ils_sicee", "ils_sicse", "ils_sicot",
         "ils_sicdy", "ils_sicer", "ils_dispy"]

# The instruments each country's dials move, and the components that make up the employer
# contribution in Italy, which is the line the contract-class proxy governs.
INSTRUMENTS = {
    "ES": ["bsa00_s", "bch00_s", "bunct_s", "bunnc_s", "poacm_s", "poanc_s", "psuwdcm_s",
           "tscerpi_s", "tscerui_s", "tscerot_s", "tscerie_s"],
    "IT": ["bsamm_s", "bsals_s", "bfach00_s", "bfalp_s", "bunct01_s", "bunct02_s",
           "tscerpi_s", "tscerui_s", "tscersv_s", "tscerfa_s", "tscersf_s", "tscersi_s",
           "tscertj_s", "sin01_s",
           # the like-for-like tax lines the country report actually publishes, and the
           # two inputs the cadastral-income derivation is checked against
           "tinna_s", "tinrg_s", "tin00_s", "tintceent_s", "tprob_s", "tpr",
           "il_taxabley", "aobiv", "amriv"],
    "EL": ["bsa00_s", "bch_s", "bunct_s", "bunnc_s", "bho00_s", "tpr_s", "boanc_s",
           "tin00_s", "tscerpi_s", "tscersi_s", "tscerui_s", "tscerfa_s", "tscerot_s"],
}


def weighted_sum(out, col):
    """Annualised, weighted population total of a per-person column, EUR millions."""
    if col not in out.columns:
        return None
    per_hh = out.groupby("idhh")[col].sum() * MONTHS
    wt = out.groupby("idhh")["dwt"].first()
    return round(float((per_hh * wt).sum()) / MILLION, 1)


def _gini(y, w):
    order = np.argsort(y, kind="stable")
    y, w = y[order], w[order]
    cw = np.cumsum(w)
    cy = np.cumsum(w * y)
    if cy[-1] <= 0:
        return None
    return round(float(1 - np.sum((cy[1:] + cy[:-1]) * np.diff(cw)) / (cy[-1] * cw[-1])) * 100, 2)


def distribution(pu):
    """Mean and median equivalised disposable income, Gini, and the AROP rate.

    Equivalisation is the OECD-modified scale the tool itself uses, and the person weight
    is the household weight times household size, so the statistics are person-based, as
    the Country Reports publish them.
    """
    w_hh = pu["survey_weight"].to_numpy(float)
    size = pu["n_adults"].to_numpy(float) + pu["n_children"].to_numpy(float)
    scale = np.maximum(W._oecd_modified(pu["n_adults"].to_numpy(), pu["n_children"].to_numpy()),
                       1e-6)
    y = pu["net_income"].to_numpy(float) / scale
    w = w_hh * size
    med = W._weighted_median(y, w)
    line = 0.6 * med
    return {
        "mean_equivalised_disposable": round(float(np.sum(w * y) / np.sum(w)), 0),
        "median_equivalised_disposable": round(float(med), 0),
        "gini_pct": _gini(y, w),
        "arop_rate_pct": round(float(100 * w[y < line].sum() / w.sum()), 2),
        "arop_threshold": round(float(line), 0),
        "population_k": round(float(w.sum()) / 1e3, 1),
        "households_k": round(float(w_hh.sum()) / 1e3, 1),
    }


def run_country(cc):
    cfg = CC[cc]
    mod = engine.load_model()
    cobj = mod.countries[cc]
    template = list(cobj.load_data(cfg["train"]).columns)
    conv = importlib.import_module(cfg["mod"])
    res = getattr(conv, cfg["fn"])(template)
    real = res[0]
    t0 = time.time()
    out = engine.run(cobj, cfg["system"], real, cfg["dataset"]).outputs[0]
    pu = adapter.euromod_to_per_unit(out, cc, YEAR, "baseline")

    populated = [c for c in real.columns
                 if np.any(pd.to_numeric(real[c], errors="coerce").fillna(0.0).to_numpy() != 0)]
    rep = {
        "country": cc, "system": cfg["system"], "dataset": cfg["dataset"],
        "converter": os.path.dirname(os.path.abspath(conv.__file__)),
        "seconds": round(time.time() - t0, 1),
        "n_input_columns": int(real.shape[1]),
        "n_populated_columns": len(populated),
        "populated_columns": sorted(populated),
        "output_shape": list(out.shape),
        "aggregates_eur_m": {k: weighted_sum(out, k) for k in LISTS},
        "instruments_eur_m": {k: weighted_sum(out, k) for k in INSTRUMENTS[cc]},
        "distribution": distribution(pu),
        "not_found": engine.NOT_FOUND.get(f"{cfg['system']}/{cfg['dataset']}", []),
    }
    if cc == "IT":
        # The contract-class split, weighted the way the contribution is: by the earnings
        # base each class carries, not by headcount. sin01_s is an intermediate the engine
        # does not return, so the base is the input yem, which is what sin01_s is built
        # from before its floor and ceiling.
        r = real.sort_values(["idhh", "idperson"]).reset_index(drop=True)
        lcl = pd.to_numeric(r["lcl"], errors="coerce").fillna(0).to_numpy()
        yem = pd.to_numeric(r["yem"], errors="coerce").fillna(0).to_numpy()
        w = pd.to_numeric(r["dwt"], errors="coerce").fillna(0).to_numpy()
        emp = lcl > 0
        base = yem * w * MONTHS
        rep["collar"] = {
            "n_blue": int((lcl == 1).sum()), "n_white": int((lcl == 2).sum()),
            "n_with_employment_income": int((yem > 0).sum()),
            "blue_share_headcount_pct": round(float(100 * (lcl == 1).sum() / max(emp.sum(), 1)), 1),
            "blue_share_earnings_base_pct": round(
                float(100 * base[lcl == 1].sum() / max(base[emp].sum(), 1e-9)), 1),
            "earnings_base_eur_m": round(float(base[emp].sum()) / MILLION, 1),
        }
    return rep


def main(countries, tag):
    reports = {}
    for cc in countries:
        print(f"\n{'='*84}\n{CC[cc]['name']} ({cc})\n{'='*84}")
        r = run_country(cc)
        reports[cc] = r
        print(f"  converter {r['converter']}")
        print(f"  {r['n_populated_columns']} populated input columns of {r['n_input_columns']}; "
              f"output {tuple(r['output_shape'])}; {r['seconds']}s")
        for k, v in r["aggregates_eur_m"].items():
            if v is not None:
                print(f"    {k:12} {v:>14,.1f}")
        print("   instruments:")
        for k, v in r["instruments_eur_m"].items():
            if v is not None:
                print(f"    {k:12} {v:>14,.1f}")
        print("   distribution:", json.dumps(r["distribution"]))
        if "collar" in r:
            print("   collar:", json.dumps(r["collar"]))
    path = os.path.join(EUROPE, "docs", f"baseline_validation_{tag}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(reports, fh, indent=1)
    print("\nwritten", path)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("countries", nargs="*", default=["ES", "IT", "EL"])
    ap.add_argument("--tag", default="after")
    a = ap.parse_args()
    raise SystemExit(main([c.upper() for c in a.countries] or ["ES", "IT", "EL"], a.tag))
