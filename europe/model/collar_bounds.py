"""collar_bounds.py -- what Italy's employer contribution aggregate is worth under each
possible contract class, measured rather than recalled.

`lcl` gates every component of `sicer_it`, and the only rate that differs between the two
classes is sickness and maternity, 2.68% blue against 0.46% white. So the aggregate is
bounded below by an all-white-collar workforce and above by an all-blue-collar one, and
the proxy has to land inside that bracket to be worth anything. This runs the two bounds
and the proxy on the same input, so the three numbers are comparable to the euro.

Aggregates only.
"""
import importlib
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
EUROPE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EUROPE, "common"))
sys.path.insert(0, os.path.join(EUROPE, "Italy", "model", "it_real"))
import engine  # noqa: E402

SYSTEM, DATASET, TRAIN = "IT_2023", "IT_2024_a1_2015_03_e2", "IT_training_data"
MONTHS, MILLION = 12, 1e6
COMPONENTS = ["tscerpi_s", "tscerui_s", "tscersv_s", "tscerfa_s", "tscersf_s",
              "tscersi_s", "tscertj_s"]


def agg(out, col):
    if col not in out.columns:
        return None
    per_hh = out.groupby("idhh")[col].sum() * MONTHS
    wt = out.groupby("idhh")["dwt"].first()
    return round(float((per_hh * wt).sum()) / MILLION, 1)


def main():
    mod = engine.load_model()
    cobj = mod.countries["IT"]
    template = list(cobj.load_data(TRAIN).columns)
    conv = importlib.import_module("convert_it")
    real = conv.convert_it_2024_full(template)[0]
    has_yem = pd.to_numeric(real["yem"], errors="coerce").fillna(0).to_numpy() > 0

    cases = {"proxy_isco": real["lcl"].to_numpy().copy(),
             "all_white": np.where(has_yem, 2, 0),
             "all_blue": np.where(has_yem, 1, 0)}
    rep = {}
    for name, lcl in cases.items():
        d = real.copy()
        d["lcl"] = lcl
        out = engine.run(cobj, SYSTEM, d, DATASET).outputs[0]
        rep[name] = {"ils_sicer_eur_m": agg(out, "ils_sicer"),
                     "components": {c: agg(out, c) for c in COMPONENTS},
                     "n_blue": int((lcl == 1).sum()), "n_white": int((lcl == 2).sum())}
        print(f"{name:12} ils_sicer = {rep[name]['ils_sicer_eur_m']:>12,.1f} m "
              f"(blue {rep[name]['n_blue']}, white {rep[name]['n_white']})")

    lo = rep["all_white"]["ils_sicer_eur_m"]
    hi = rep["all_blue"]["ils_sicer_eur_m"]
    px = rep["proxy_isco"]["ils_sicer_eur_m"]
    rep["bracket"] = {
        "all_white_bound": lo, "all_blue_bound": hi, "proxy": px,
        "inside_bracket": bool(lo <= px <= hi),
        "implied_blue_share_of_bracket_pct": round(100 * (px - lo) / (hi - lo), 1),
    }
    print(json.dumps(rep["bracket"], indent=1))
    path = os.path.join(EUROPE, "docs", "collar_bounds.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print("written", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
