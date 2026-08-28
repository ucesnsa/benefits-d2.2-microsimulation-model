"""IT-3 VALIDATION GATE. Runs the IT baseline on the matched engine and validates
against the OFFICIAL EUROMOD IT Country Report (Y16_CR_IT, J2.0+, 2023 policy)
baseline. Reports the full table (converted vs EUROMOD-IT) with gaps and PASS/MISS,
a disposable decomposition (offsetting check), and the distribution. Data-free."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
import numpy as np, pandas as pd
# MODEL is the country's model/ directory, which holds pipeline/ and wevm/.
EUROPE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      os.pardir, os.pardir, os.pardir))
MODEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     os.pardir))
sys.path.insert(0, os.path.join(MODEL, "pipeline"))
sys.path.insert(0, os.path.join(MODEL, "wevm"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine, adapter   # noqa
import wevm as W         # noqa
import convert_it as IT  # noqa
DATASET, SYSTEM = "IT_2024_a1_2015_03_e2", "IT_2023"

# OFFICIAL EUROMOD IT Country Report (Y16_CR_IT) 2023 baseline (Annex 3).
EM = {
    "earns_m": 736695.0,          # ils_earns (yem 559928+yemtj 27271+yemxp 4675+yse 133905
                                  #   +yseib 4228+yemaj 102+yempv 4205+yseil 2381)
    "pen_read_m": 311890.0,       # poa 247752 + pdi 17665 + psu 46473 (read components I populate)
    "pen_full_m": 326678.0,       # + phl 14788 (taxable invalidity, not separable in UDB)
    "tax_nat_m": 200784.0,        # national IRPEF tinna_s (external 189940, EM ratio 1.06)
    "sicse_m": 7093.0,            # self-employed SIC (external 3260, EM ratio 2.18)
    "arop": 18.91, "gini": 30.65, "mean": 22975.0, "median": 20243.0, "s80s20": 4.93,
    "dec": [3.00, 4.82, 5.99, 7.15, 8.25, 9.40, 10.66, 12.19, 14.63, 23.91],
}
SILC_AROP = 18.90


def wq(v, w, q):
    o = np.argsort(v); v, w = np.asarray(v)[o], np.asarray(w)[o]
    cw = (np.cumsum(w) - 0.5 * w) / w.sum(); return float(np.interp(q, cw, v))
def gini(v, w):
    o = np.argsort(v); v, w = np.asarray(v)[o], np.asarray(w)[o]
    cw = np.cumsum(w); cy = np.cumsum(v * w); cw = cw / cw[-1]; cy = cy / cy[-1]
    return float(1 - np.sum((cy[1:] + cy[:-1]) * np.diff(cw)))
def tot(out, v): return float((out[v] * out["dwt"]).sum() * 12) if v in out.columns else 0.0


def main():
    mod = engine.load_model(); cobj = mod.countries["IT"]
    template = list(cobj.load_data("IT_training_data").columns)
    real, log, nuts1 = IT.convert_it_2024_full(template)
    print("converted:", real.shape, "households", real["idhh"].nunique())
    sim = engine.run(cobj, SYSTEM, real, DATASET)
    print(f"ENGINE: {engine.assert_matched_engine()}")
    print(f"dataset={DATASET} system={SYSTEM} | sim.errors={len(sim.errors)}")
    for e in list(sim.errors)[:8]:
        print("   warn:", str(e)[:120])
    out = sim.outputs[0].copy()
    pu = adapter.euromod_to_per_unit(out, "IT", 2024, "baseline")
    W.validate_schema(pu)

    # distribution (OECD-modified, age-14 cutoff, person-weighted)
    hh = out.groupby("idhh")["ils_dispy"].sum() * 12.0
    a = out[out["dag"] >= 14].groupby("idhh").size().reindex(hh.index, fill_value=0).to_numpy()
    k = out[out["dag"] < 14].groupby("idhh").size().reindex(hh.index, fill_value=0).to_numpy()
    eq = hh.to_numpy() / np.maximum(1.0 + 0.5 * np.maximum(a - 1, 0) + 0.3 * k, 1e-9)
    size = out.groupby("idhh").size().reindex(hh.index).to_numpy()
    hw = out.groupby("idhh")["dwt"].first().reindex(hh.index).to_numpy(); pw = hw * size
    med = wq(eq, pw, 0.5); arop = float(pw[eq < 0.6 * med].sum() / pw.sum()) * 100
    g = gini(eq, pw) * 100; p20, p80 = wq(eq, pw, 0.2), wq(eq, pw, 0.8)
    o = np.argsort(eq); cwc = np.cumsum(pw[o]) / pw.sum(); dec = np.clip((cwc * 10).astype(int), 0, 9)
    inc = eq[o] * pw[o]; sh = np.array([inc[dec == d].sum() for d in range(10)]); sh = sh / sh.sum() * 100
    mean_eq = float(np.average(eq, weights=pw)); s80 = (eq[eq >= p80] * pw[eq >= p80]).sum() / max((eq[eq <= p20] * pw[eq <= p20]).sum(), 1e-9)

    yem_o = tot(out, "yem") / 1e6; yse_o = tot(out, "yse") / 1e6
    earns = tot(out, "ils_earns") / 1e6; origy = tot(out, "ils_origy") / 1e6
    pen = tot(out, "ils_pen") / 1e6; taxin = tot(out, "ils_taxin") / 1e6
    sicee = tot(out, "ils_sicee") / 1e6; sicse = tot(out, "ils_sicse") / 1e6
    sicdy = tot(out, "ils_sicdy") / 1e6; ben = tot(out, "ils_ben") / 1e6
    tax = tot(out, "ils_tax") / 1e6; disp = tot(out, "ils_dispy") / 1e9

    def line(lbl, conv, target, tol, unit="%"):
        if unit == "pp": gap = conv - target; ok = abs(gap) <= tol; gs = f"{gap:+.2f}pp"; cs, ts = f"{conv:.2f}", f"{target:.2f}"
        else: gap = (conv - target) / target * 100; ok = abs(gap) <= tol * 100; gs = f"{gap:+.1f}%"; cs, ts = f"{conv:,.0f}", f"{target:,.0f}"
        print(f"  {lbl:30} mine {cs:>11}  EM-IT {ts:>11}  gap {gs:>8}  {'PASS' if ok else 'MISS'}")

    print("\n=== IT validation vs OFFICIAL EUROMOD IT 2023 baseline (Y16_CR_IT) ===")
    print("  -- aggregates (annual EUR millions) --")
    line("Employment (out yem)", yem_o, 559928.0, 0.07)
    line("Self-employment (out yse)", yse_o, 133905.0, 0.10)
    line("Earnings (ils_earns)", earns, EM["earns_m"], 0.07)
    line("Pensions read (poa+pdi+psu)", pen, EM["pen_read_m"], 0.07)
    line("Income tax national (ils_taxin)", taxin, EM["tax_nat_m"], 0.10)
    line("Self-employed SIC (ils_sicse)", sicse, EM["sicse_m"], 0.20)
    print(f"     [employee SIC ils_sicee mine {sicee:,.0f}m; EM-IT subtotal hidden in report]")
    print("  -- distribution (Tables A3.7/A3.8) --")
    line("AROP 60% median (%)", arop, EM["arop"], 2.0, "pp")
    line("Gini", g, EM["gini"], 3.0, "pp")
    line("Mean equiv disposable", mean_eq, EM["mean"], 0.07)
    line("Median equiv disposable", med, EM["median"], 0.07)
    print(f"\n  AROP: mine {arop:.1f}% | EUROMOD-IT 18.91% | SILC {SILC_AROP:.1f}% (EM-IT ~1.00x SILC)")
    print(f"  S80/20 mine {s80:.2f} | EM-IT {EM['s80s20']:.2f}")
    print("  decile shares mine : " + " ".join(f"{x:.2f}" for x in sh))
    print("  decile shares EM-IT: " + " ".join(f"{x:.2f}" for x in EM["dec"]))

    print("\n=== DISPOSABLE DECOMPOSITION (annual bn) ===")
    print(f"  ils_origy (market)   {origy/1e3:8.1f}")
    print(f"  + ils_ben (incl pen) {ben/1e3:8.1f}   (of which pensions {pen/1e3:.1f})")
    print(f"  - ils_tax            {tax/1e3:8.1f}")
    print(f"  - ils_sicdy (SIC)    {sicdy/1e3:8.1f}   (sicee {sicee/1e3:.1f} + sicse {sicse/1e3:.1f})")
    print(f"  = ils_dispy          {disp:8.1f}")
    print(f"\n  pensions full EM-IT (incl phl) {EM['pen_full_m']:,.0f}m; mine {pen:,.0f}m "
          f"(phl=14,788m taxable invalidity not separable in UDB)")


if __name__ == "__main__":
    main()
