"""Run the full ES conversion baseline on the matched engine under the correct
reference-year dataset, and validate every fiscal line against the official
UDB-derived targets, with a disposable-income decomposition. Data-free."""
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
import adapter  # noqa: E402
import convert_full  # noqa: E402
import wevm as W  # noqa: E402

# Correct reference-year dataset config (yearCollection=2024 = SILC 2024 = 2023 income).
# Validation runs at the 2023 policy (the income reference year) for a like-for-like
# comparison with the 2023 official figures, removing the legitimate 2023->2024 uprating.
DATASET = "ES_2024_b1_2015_03_e2"
SYSTEM = "ES_2023"

# Official 2023 targets, computed from the UDB (HX090 for AROP, HY020 disposable,
# HY010 gross, HY140G tax+SIC, PY100G+PY110G+PY130G pensions) and the experiment's
# gross market-income figure.
TGT = {
    "AROP": (0.197, 0.03, "pp"),
    "Disposable income": (714.6, 0.05, "%"),
    "Market income (origy)": (655.0, 0.07, "%"),
    "Tax + social contributions": (159.9, 0.10, "%"),
    "Pensions (ils_pen)": (194.0, 0.10, "%"),
}


def wq(v, w, q):
    o = np.argsort(v); v, w = np.asarray(v)[o], np.asarray(w)[o]
    cw = (np.cumsum(w) - 0.5 * w) / w.sum()
    return float(np.interp(q, cw, v))


def oecd(na, nc):
    return 1.0 + 0.5 * np.maximum(np.asarray(na, float) - 1, 0) + 0.3 * np.asarray(nc, float)


def tot(out, v):
    return float((out[v] * out["dwt"]).sum() * 12) if v in out.columns else 0.0


def main():
    mod = engine.load_model()
    cobj = mod.countries["ES"]
    template = list(cobj.load_data("ES_training_data").columns)
    real, log = convert_full.convert_es_2024_full(template)
    print("CONVERSION LOG:")
    for line in log:
        print("  -", line)

    sim = engine.run(cobj, SYSTEM, real, DATASET)
    print(f"\nENGINE: {engine.assert_matched_engine()}")
    print(f"dataset={DATASET} system={SYSTEM} | sim.errors={len(sim.errors)}")
    if sim.errors:
        for e in list(sim.errors)[:10]:
            print("   warn:", str(e)[:130])
    out = sim.outputs[0]
    print("output shape:", out.shape)

    pu = adapter.euromod_to_per_unit(out, "ES", 2024, "baseline")
    W.validate_schema(pu)
    w = pu["survey_weight"].to_numpy(float)
    net = pu["net_income"].to_numpy(float)
    size = (pu["n_adults"] + pu["n_children"]).to_numpy(float)
    pw = w * size
    eq = net / np.maximum(oecd(pu["n_adults"], pu["n_children"]), 1e-9)
    med = wq(eq, pw, 0.5)
    arop = float(pw[eq < 0.6 * med].sum() / pw.sum())

    disp = tot(out, "ils_dispy") / 1e9
    origy = tot(out, "ils_origy") / 1e9
    tax = tot(out, "ils_tax") / 1e9
    sic = tot(out, "ils_sicdy") / 1e9
    pen = tot(out, "ils_pen") / 1e9
    ben = tot(out, "ils_ben") / 1e9
    conv = {"AROP": arop * 100, "Disposable income": disp, "Market income (origy)": origy,
            "Tax + social contributions": tax + sic, "Pensions (ils_pen)": pen}

    print(f"\nvalidate_schema PASS | households {len(pu)} | weighted persons {pw.sum():,.0f}")
    print("\n=== VALIDATION TABLE (converted vs 2023 official) ===")
    npass = 0
    for k, (target, tol, unit) in TGT.items():
        c = conv[k]
        if unit == "pp":
            gap = c - target * 100
            ok = abs(gap) <= tol * 100
            gs = f"{gap:+.1f}pp"
        else:
            gap = (c - target) / target
            ok = abs(gap) <= tol
            gs = f"{gap*100:+.1f}%"
        npass += ok
        tg = f"{target*100:.1f}%" if unit == "pp" else f"{target:.0f}bn"
        cg = f"{c:.1f}%" if unit == "pp" else f"{c:.0f}bn"
        print(f"  {k:30} converted {cg:>9}  official {tg:>9}  gap {gs:>8}  -> {'PASS' if ok else 'MISS'}")
    print(f"\n  {npass}/{len(TGT)} lines within tolerance")

    print("\n=== DISPOSABLE DECOMPOSITION (annual bn) ===")
    print(f"  ils_origy (market)  {origy:8.0f}")
    print(f"  + ils_ben (incl pen){ben:8.0f}   (of which pensions {pen:.0f})")
    print(f"  - ils_tax           {tax:8.0f}")
    print(f"  - ils_sicdy (SIC)   {sic:8.0f}")
    print(f"  = ils_dispy         {disp:8.0f}   (official 714.6)")


if __name__ == "__main__":
    main()
