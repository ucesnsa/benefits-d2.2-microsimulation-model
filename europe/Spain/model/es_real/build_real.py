"""Full six-scenario real ES build on the corrected, validated converter (correct
reference-year dataset, pensions routed to the income-list components). Runs the
pipeline reform set on real data, builds the layer IN MEMORY, runs WEVM, reports
signs and epsilon grids. Data-free: no real layer written to disk."""
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
import engine  # noqa: E402
import config  # noqa: E402
import adapter  # noqa: E402
import reforms  # noqa: E402
import convert_full  # noqa: E402
import wevm as W  # noqa: E402

DATASET = "ES_2024_b1_2015_03_e2"   # correct reference year (2023 income)
SYSTEM = "ES_2023"                  # income reference year
YEAR = 2023


def main():
    mod = engine.load_model()
    cobj = mod.countries["ES"]
    sysobj = engine.get_system(cobj, SYSTEM)
    template = list(cobj.load_data("ES_training_data").columns)
    real, _ = convert_full.convert_es_2024_full(template)

    prof = config.PROFILES["ES"]
    frames, base_pu, wbase = [], None, None
    print(f"scenario sign checks (real ES, {SYSTEM}, {DATASET}):")
    for scen in config.SCENARIOS:
        if scen == "baseline":
            out = engine.run(cobj, SYSTEM, real, DATASET).outputs[0]
        else:
            reform = prof["reforms"][scen]
            t = reform["type"]
            if t in ("const_scale", "rate_delta"):
                consts, _ = reforms.build_const_overwrites(sysobj, reform)
                out = engine.run(cobj, SYSTEM, real, DATASET, constants=consts).outputs[0]
            elif t == "income_scale":
                out = engine.run(cobj, SYSTEM, reforms.income_scale(real, reform), DATASET).outputs[0]
            elif t == "unemployment":
                d, _ = reforms.unemployment_shock(real, reform)
                out = engine.run(cobj, SYSTEM, d, DATASET).outputs[0]
        pu = adapter.euromod_to_per_unit(out, "ES", YEAR, scen)
        frames.append(pu)
        if scen == "baseline":
            base_pu = pu
            wbase = adapter.weighted_disposable(pu)
        else:
            delta = adapter.weighted_disposable(pu) - wbase
            nch = int((pu.set_index("unit_id")["net_income"] != base_pu.set_index("unit_id")["net_income"]).sum())
            sign = "+" if delta > 1 else "-" if delta < -1 else "0"
            exp = config.EXPECTED_SIGN[scen]
            print(f"  [{scen:18}] delta={delta:>18,.0f} EUR/yr  sign {sign} (exp {exp}) "
                  f"{'OK' if sign == exp else 'CHECK'}  hh_changed={nch:,}")
    print("ENGINE:", engine.assert_matched_engine())

    layer = pd.concat(frames, ignore_index=True)
    W.validate_schema(layer)
    summary = W.wevm(W.compute_ev(layer), equivalise=True)
    eps_cols = [c for c in summary.columns if c.startswith("wevm_eps_")]
    print("\nWEVM epsilon grids (annual EUR, real ES):")
    for _, r in summary.iterrows():
        grid = "  ".join(f"{c.replace('wevm_','')}={r[c]:,.0f}" for c in eps_cols)
        print(f"  [{r['scenario']:18}] {grid}")
        print(f"       winners={r['winners_pop']:,.0f} losers={r['losers_pop']:,.0f} floored={int(r['units_floored'])}")


if __name__ == "__main__":
    main()
