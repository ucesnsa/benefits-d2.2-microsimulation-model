"""
run_experiment.py -- ES real-vs-synthetic go/no-go experiment.

Converts the real ES 2024 UDB (minimum scope), runs baseline + the two
market-income shocks on the matched engine, builds a real three-scenario canonical
layer IN MEMORY, runs it through WEVM, and compares it against the synthetic ES
layer on the trustworthy parts only (gross income distribution, population scale,
the two shocks). Prints aggregates only. It does NOT write any real-data-derived
per-person or per-household layer to disk; only aggregates leave this process.

NOT VALIDATED. Knowingly rough. Nothing here is publication-grade or shippable.
"""
import os
import sys

import numpy as np
import pandas as pd

# MODEL is the country's model/ directory, which holds pipeline/ and wevm/.
EUROPE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      os.pardir, os.pardir, os.pardir))
MODEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     os.pardir))
sys.path.insert(0, os.path.join(MODEL, "pipeline"))
sys.path.insert(0, os.path.join(MODEL, "wevm"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402
import config  # noqa: E402
import adapter  # noqa: E402
import reforms  # noqa: E402
import wevm as W  # noqa: E402
import convert  # noqa: E402

SCEN = ["baseline", "gdp_shock", "unemployment_shock"]


# ---- weighted helpers ----
def wq(v, w, q):
    v = np.asarray(v, float); w = np.asarray(w, float)
    o = np.argsort(v); v, w = v[o], w[o]
    cw = (np.cumsum(w) - 0.5 * w) / w.sum()
    return float(np.interp(q, cw, v))


def wgini(v, w):
    v = np.asarray(v, float); w = np.asarray(w, float)
    o = np.argsort(v); v, w = v[o], w[o]
    cw = np.cumsum(w); cv = np.cumsum(v * w)
    if cv[-1] <= 0:
        return float("nan")
    cv = cv / cv[-1]; cw = cw / cw[-1]
    return float(1 - np.sum((cv[1:] + cv[:-1]) * np.diff(cw)))


def oecd(na, nc):
    return 1.0 + 0.5 * np.maximum(np.asarray(na, float) - 1, 0) + 0.3 * np.asarray(nc, float)


def baseline_shape(layer, label):
    b = layer[layer.scenario == "baseline"]
    w = b["survey_weight"].to_numpy(float)
    gross = b["income"].to_numpy(float)
    eq = b["net_income"].to_numpy(float) / np.maximum(oecd(b["n_adults"], b["n_children"]), 1e-9)
    med = wq(eq, w, 0.5)
    arop = float(w[eq < 0.6 * med].sum() / w.sum())
    qs = [0.1, 0.25, 0.5, 0.75, 0.9]
    print(f"\n--- baseline shape [{label}] ---")
    print(f"  households={len(b):,} weighted_pop={w.sum():,.0f}")
    print(f"  gross market income (annual EUR): mean={np.average(gross, weights=w):,.0f} "
          f"gini={wgini(gross, w):.3f}")
    print("    quantiles " + " ".join(f"p{int(q*100)}={wq(gross, w, q):,.0f}" for q in qs))
    print(f"  equiv. 'disposable' (annual EUR; UNRELIABLE level): median={med:,.0f} "
          f"gini={wgini(eq, w):.3f} AROP={arop*100:.1f}%")
    print("    quantiles " + " ".join(f"p{int(q*100)}={wq(eq, w, q):,.0f}" for q in qs))
    return {"weighted_pop": w.sum(), "base_disp_total": float((b["net_income"] * b["survey_weight"]).sum())}


def reform_compare(summary, base_total, weighted_pop, label):
    eps_cols = [c for c in summary.columns if c.startswith("wevm_eps_")]
    print(f"\n--- reforms [{label}] (WEVM normalised to baseline disposable; winners/losers as % pop) ---")
    for scen in ("gdp_shock", "unemployment_shock"):
        r = summary[summary.scenario == scen]
        if r.empty:
            print(f"  {scen}: absent"); continue
        r = r.iloc[0]
        grid = "  ".join(f"{c.replace('wevm_','')}={100*r[c]/base_total:+.2f}%" for c in eps_cols)
        print(f"  {scen}: WEVM/base {grid}")
        print(f"      winners={100*r['winners_pop']/weighted_pop:.1f}% losers={100*r['losers_pop']/weighted_pop:.1f}% "
              f"units_floored={int(r['units_floored'])}")


def main():
    mod = engine.load_model()
    cobj = mod.countries["ES"]
    template = list(cobj.load_data("ES_training_data").columns)
    real_input = convert.convert_es_2024(template)
    print(f"converted real ES input: rows={len(real_input):,} "
          f"households={real_input['idhh'].nunique():,} weighted_pop={int(real_input['dwt'].sum()):,}")

    es_reforms = config.PROFILES["ES"]["reforms"]
    frames, baseline_errors, shock_info = [], None, {}
    for scen in SCEN:
        if scen == "baseline":
            data = real_input
        elif scen == "gdp_shock":
            data = reforms.income_scale(real_input, es_reforms["gdp_shock"])
        elif scen == "unemployment_shock":
            data, shock_info = reforms.unemployment_shock(real_input, es_reforms["unemployment_shock"])
        sim = engine.run(cobj, "ES_2024", data, "ES_training_data")
        if scen == "baseline":
            baseline_errors = len(sim.errors)
        frames.append(adapter.euromod_to_per_unit(sim.outputs[0], "ES", 2024, scen))
    print("ENGINE:", engine.assert_matched_engine())
    print("baseline sim.errors:", baseline_errors, "| unemployment flip:", shock_info)

    real_layer = pd.concat(frames, ignore_index=True)
    W.validate_schema(real_layer)
    print("real layer: rows=%d  validate_schema PASS" % len(real_layer))
    real_summary = W.wevm(W.compute_ev(real_layer), equivalise=True)

    syn_path = os.path.join(EUROPE, "outputs", "ES", "per_unit_export.parquet")
    syn = pd.read_parquet(syn_path)
    syn = syn[syn.scenario.isin(SCEN)].copy()
    syn_summary = W.wevm(W.compute_ev(syn), equivalise=True)

    print("\n" + "=" * 78 + "\nBASELINE: REAL vs SYNTHETIC\n" + "=" * 78)
    rb = baseline_shape(real_layer, "REAL")
    sb = baseline_shape(syn, "SYNTHETIC")

    print("\n" + "=" * 78 + "\nREFORMS: REAL vs SYNTHETIC\n" + "=" * 78)
    reform_compare(real_summary, rb["base_disp_total"], rb["weighted_pop"], "REAL")
    reform_compare(syn_summary, sb["base_disp_total"], sb["weighted_pop"], "SYNTHETIC")


if __name__ == "__main__":
    main()
