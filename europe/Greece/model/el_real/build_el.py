"""Full six-scenario real EL build (Step EL-3) on the validated converter. Runs the
pipeline reform set on real EL data (system EL_2023, dataset EL_2024_c1_2015_03_e2),
builds the canonical per-household layer IN MEMORY, runs WEVM, reports signs and the
epsilon grids. Data-free: no real layer written to disk.

EL gdp_shock note: the income list uses yemre/ysere (the model derives them from the
gross yem/yse), so the GDP shock scales yem, yse, yemre AND ysere to be robust to the
derivation path; the unemployment shock likewise zeros all four for flipped persons."""
import os
import sys

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
import config          # noqa: E402
import adapter         # noqa: E402
import reforms         # noqa: E402
import convert_el      # noqa: E402
import wevm as W       # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

DATASET = "EL_2024_c1_2015_03_e2"
SYSTEM = "EL_2023"
YEAR = 2023
# EL earnings list components, scaled together with the gross drivers
EARN_VARS = ["yem", "yse", "yemre", "ysere"]


def main():
    mod = engine.load_model()
    cobj = mod.countries["EL"]
    sysobj = engine.get_system(cobj, SYSTEM)
    template = list(cobj.load_data("EL_training_data").columns)
    real, log, nuts1 = convert_el.convert_el_2024_full(template)

    prof = config.PROFILES["EL"]
    frames, base_pu, wbase = [], None, None
    print(f"scenario sign checks (real EL, {SYSTEM}, {DATASET}):")
    for scen in config.SCENARIOS:
        if scen == "baseline":
            out = engine.run(cobj, SYSTEM, real, DATASET).outputs[0]
        else:
            reform = prof["reforms"][scen]
            t = reform["type"]
            if t in ("const_scale", "rate_delta"):
                consts, skipped = reforms.build_const_overwrites(sysobj, reform)
                out = engine.run(cobj, SYSTEM, real, DATASET, constants=consts).outputs[0]
            elif t == "income_scale":
                r2 = dict(reform); r2["vars"] = EARN_VARS   # scale all earnings components
                out = engine.run(cobj, SYSTEM, reforms.income_scale(real, r2), DATASET).outputs[0]
            elif t == "unemployment":
                d, uinfo = reforms.unemployment_shock(real, reform)
                for v in ("yemre", "ysere"):
                    d.loc[d["les"] == config.LES_UNEMPLOYED, v] = 0  # ensure derived earnings drop
                out = engine.run(cobj, SYSTEM, d, DATASET).outputs[0]
        pu = adapter.euromod_to_per_unit(out, "EL", YEAR, scen)
        frames.append(pu)
        if scen == "baseline":
            base_pu = pu
            wbase = adapter.weighted_disposable(pu)
        else:
            delta = adapter.weighted_disposable(pu) - wbase
            nch = int((pu.set_index("unit_id")["net_income"]
                       != base_pu.set_index("unit_id")["net_income"]).sum())
            sign = "+" if delta > 1 else "-" if delta < -1 else "0"
            exp = config.EXPECTED_SIGN[scen]
            print(f"  [{scen:18}] delta={delta:>18,.0f} EUR/yr  sign {sign} (exp {exp}) "
                  f"{'OK' if sign == exp else 'CHECK'}  hh_changed={nch:,}")
    print("ENGINE:", engine.assert_matched_engine())

    layer = pd.concat(frames, ignore_index=True)
    W.validate_schema(layer)
    summary = W.wevm(W.compute_ev(layer), equivalise=True)
    eps_cols = [c for c in summary.columns if c.startswith("wevm_eps_")]
    print("\nWEVM epsilon grids (annual EUR, real EL):")
    for _, r in summary.iterrows():
        grid = "  ".join(f"{c.replace('wevm_', '')}={r[c]:,.0f}" for c in eps_cols)
        print(f"  [{r['scenario']:18}] {grid}")
        print(f"       winners={r['winners_pop']:,.0f} losers={r['losers_pop']:,.0f} "
              f"floored={int(r['units_floored'])}")


if __name__ == "__main__":
    main()
