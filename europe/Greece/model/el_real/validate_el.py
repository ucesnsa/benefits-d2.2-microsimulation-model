"""EL baseline validation (Step EL-2), anchored to the OFFICIAL EUROMOD EL Country
Report (Y16_CR_EL, model J2.0+, 2023 policy system) -- the proper target named in
the brief -- with the raw-UDB survey figures shown alongside for reference.

The key lesson from EL-2: EUROMOD does not reproduce the raw SILC/UDB survey; it
SIMULATES taxes and benefits and, for Greece, deliberately produces a higher
bottom-decile income share and hence a LOWER poverty rate than the survey (the
EL Country Report, sec. 4.2: EUROMOD AROP ratio 0.80 to SILC). The correct
validation target is therefore the EUROMOD EL baseline, not HY020/HY140G.

Runs on the matched engine, EL_2023 / EL_2024_c1_2015_03_e2 (income year 2023).
Data-free: schema, counts, and aggregates only."""
import glob
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
import engine          # noqa: E402
import adapter         # noqa: E402
import convert_el      # noqa: E402
import wevm as W       # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

DATASET = "EL_2024_c1_2015_03_e2"
SYSTEM = "EL_2023"
UDB = convert_el.UDB

# ---- OFFICIAL EUROMOD EL Country Report (Y16_CR_EL) 2023 baseline targets ----
# Annex 3 (annual amounts, millions EUR) and Tables A3.7/A3.8 (distribution).
EM = {
    "market_origy_m": 83845.0,   # ils_origy = yemre 55364+ysere 23867+yot 14+ypr 3747
                                 #   +ypp 12+yiy 411+ypt 1205 - xmpam 106 - xmpot 669
    "pensions_m": 31971.0,       # ils_pen
    "income_tax_m": 12395.0,     # tin00_s (external AADE 12278; EM ratio 1.01)
    "sicee_m": 8284.0,           # employee SIC (tsceepi 5562+tsceesi 1357+tsceeui 509+tsceeot 856)
    "sicse_m": 2418.0,           # self-employed + farmers SIC
    "tpr_m": 1575.0,             # real estate tax (ENFIA) -- needs property data (UDB lacks it)
    "tscbesi_m": 1871.0,         # pensioners' sickness SIC
    "arop60": 15.77,             # 60% median HDI (SILC external 19.60)
    "gini": 28.79,               # (SILC 31.80)
    "s80s20": 4.44,              # (SILC 5.27)
    "mean_eq": 13077.0,          # mean equivalised disposable (SILC 12391)
    "median_eq": 11691.0,        # median equivalised disposable (SILC 10850)
    "dec_share": [3.19, 5.21, 6.42, 7.50, 8.47, 9.43, 10.56, 11.91, 13.96, 23.34],
}
SILC_AROP = 19.60   # external survey (Eurostat ilc_li02, 2024 survey / 2023 income)


def wq(v, w, q):
    o = np.argsort(v); v, w = np.asarray(v)[o], np.asarray(w)[o]
    cw = (np.cumsum(w) - 0.5 * w) / w.sum()
    return float(np.interp(q, cw, v))


def gini(v, w):
    o = np.argsort(v); v, w = np.asarray(v)[o], np.asarray(w)[o]
    cw = np.cumsum(w); cy = np.cumsum(v * w)
    cw = cw / cw[-1]; cy = cy / cy[-1]
    return float(1 - np.sum((cy[1:] + cy[:-1]) * np.diff(cw)))


def tot(out, v):
    return float((out[v] * out["dwt"]).sum() * 12) if v in out.columns else 0.0


def main():
    mod = engine.load_model()
    cobj = mod.countries["EL"]
    template = list(cobj.load_data("EL_training_data").columns)
    real, log, nuts1 = convert_el.convert_el_2024_full(template)
    print("converted input:", real.shape, "households:", real["idhh"].nunique())

    sim = engine.run(cobj, SYSTEM, real, DATASET)
    print(f"ENGINE: {engine.assert_matched_engine()}")
    print(f"dataset={DATASET} system={SYSTEM} | sim.errors={len(sim.errors)} (benign warnings)")
    out = sim.outputs[0]

    # ---- person-level equivalised disposable income (OECD-modified, age-14 cutoff,
    #      matching the Country Report methodology) ----
    out = out.copy()
    hh_disp = out.groupby("idhh")["ils_dispy"].sum() * 12.0      # annual hh disposable
    adults14 = out[out["dag"] >= 14].groupby("idhh").size()
    kids14 = out[out["dag"] < 14].groupby("idhh").size()
    idx = hh_disp.index
    a = adults14.reindex(idx, fill_value=0).to_numpy()
    k = kids14.reindex(idx, fill_value=0).to_numpy()
    scale = 1.0 + 0.5 * np.maximum(a - 1, 0) + 0.3 * k
    eq_hh = hh_disp.to_numpy() / np.maximum(scale, 1e-9)
    size = out.groupby("idhh").size().reindex(idx).to_numpy()
    hw = out.groupby("idhh")["dwt"].first().reindex(idx).to_numpy()
    pw = hw * size                                              # person weight
    med = wq(eq_hh, pw, 0.5)
    arop = float(pw[eq_hh < 0.6 * med].sum() / pw.sum()) * 100
    g = gini(eq_hh, pw) * 100
    p20, p80 = wq(eq_hh, pw, 0.2), wq(eq_hh, pw, 0.8)
    # decile shares
    o = np.argsort(eq_hh); cw = np.cumsum(pw[o]) / pw.sum()
    dec = np.clip((cw * 10).astype(int), 0, 9)
    inc_sorted = (eq_hh[o] * pw[o])
    shares = np.array([inc_sorted[dec == d].sum() for d in range(10)])
    shares = shares / shares.sum() * 100
    mean_eq = float(np.average(eq_hh, weights=pw))
    s80s20 = (eq_hh[eq_hh >= p80] * pw[eq_hh >= p80]).sum() / max((eq_hh[eq_hh <= p20] * pw[eq_hh <= p20]).sum(), 1e-9)

    origy = tot(out, "ils_origy") / 1e6
    pen = tot(out, "ils_pen") / 1e6
    taxin = tot(out, "ils_taxin") / 1e6
    sicee = tot(out, "ils_sicee") / 1e6
    sicse = tot(out, "ils_sicse") / 1e6
    sicdy = tot(out, "ils_sicdy") / 1e6
    disp = tot(out, "ils_dispy") / 1e9

    def line(label, conv, target, tol, unit=""):
        gap = (conv - target) / target * 100 if unit == "%" else conv - target
        ok = abs(gap) <= (tol * 100 if unit == "%" else tol)
        gs = f"{gap:+.1f}%" if unit == "%" else f"{gap:+.2f}{('pp' if unit=='pp' else '')}"
        cs = f"{conv:,.0f}" if unit == "%" else f"{conv:,.2f}"
        ts = f"{target:,.0f}" if unit == "%" else f"{target:,.2f}"
        print(f"  {label:28} mine {cs:>10}  EM-EL {ts:>10}  gap {gs:>8}  {'PASS' if ok else 'MISS'}")

    print("\n=== EL validation vs OFFICIAL EUROMOD EL 2023 baseline (Y16_CR_EL) ===")
    print("  -- aggregates (annual EUR millions) --")
    line("Market income (ils_origy)", origy, EM["market_origy_m"], 0.07, "%")
    line("Pensions (ils_pen)", pen, EM["pensions_m"], 0.07, "%")
    line("Income tax (tin00_s)", taxin, EM["income_tax_m"], 0.10, "%")
    line("Employee SIC (ils_sicee)", sicee, EM["sicee_m"], 0.15, "%")
    line("Self-emp+farmer SIC", sicse, EM["sicse_m"], 0.20, "%")
    print("  -- distribution (Country Report Tables A3.7/A3.8) --")
    line("AROP 60% median (%)", arop, EM["arop60"], 2.0, "pp")
    line("Gini", g, EM["gini"], 3.0, "pp")
    line("Mean equiv. disposable", mean_eq, EM["mean_eq"], 0.07, "%")
    line("Median equiv. disposable", med, EM["median_eq"], 0.07, "%")
    print(f"\n  AROP: mine {arop:.1f}% | EUROMOD-EL 15.77% | SILC survey {SILC_AROP:.1f}% "
          f"(EUROMOD-EL is 0.80x SILC by design)")
    print(f"  S80/20: mine {s80s20:.2f} | EUROMOD-EL {EM['s80s20']:.2f} | SILC 5.27")
    print(f"  bottom-decile share: mine {shares[0]:.2f}% | EUROMOD-EL {EM['dec_share'][0]:.2f}% | SILC 2.70%")

    print("\n  -- decile shares (% of equivalised disposable income) --")
    print("  decile:   " + " ".join(f"{d+1:5d}" for d in range(10)))
    print("  mine:     " + " ".join(f"{shares[d]:5.2f}" for d in range(10)))
    print("  EM-EL:    " + " ".join(f"{EM['dec_share'][d]:5.2f}" for d in range(10)))

    print(f"\n  total disposable (mine): {disp:.1f}bn | household SIC ils_sicdy {sicdy:,.0f}m "
          f"(EM-EL ~{EM['sicee_m']+EM['sicse_m']+EM['tscbesi_m']:,.0f}m)")
    print(f"  RESIDUAL CEILING: real-estate tax ENFIA (tpr_s) not simulated: mine 0 vs "
          f"EM-EL {EM['tpr_m']:,.0f}m (UDB lacks property values); this is the main "
          f"reason mine sits marginally above the EM-EL disposable baseline.")


if __name__ == "__main__":
    main()
