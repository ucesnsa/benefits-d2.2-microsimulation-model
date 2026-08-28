"""Phase F: full six-scenario real IT build on the convention-fixed converter. Runs
the pipeline reform set on real IT (system IT_2023, dataset IT_2024_a1_2015_03_e2),
builds the canonical per-household layer IN MEMORY, runs WEVM, reports signs, epsilon
grids, and a self-employed-subgroup WEVM sanity check. Data-free: no real layer
written to disk.

IT earnings note: self-employment is fed via yseev (the a1 convention), so the GDP
shock scales yem, yse AND yseev, and the unemployment shock zeros all three for the
flipped persons. Child benefit (Assegno Unico, bau_it) is an ISEE-schedule instrument
with no scalar constant, so its +25% is applied by in-memory #_Amount mutation."""
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
import engine, config, adapter, reforms   # noqa
import wevm as W                          # noqa
import convert_it as IT                   # noqa
DATASET, SYSTEM, YEAR = "IT_2024_a1_2015_03_e2", "IT_2023", 2023
EARN_VARS = ["yem", "yse", "yseev"]


def main():
    mod = engine.load_model(); cobj = mod.countries["IT"]
    sysobj = engine.get_system(cobj, SYSTEM)
    template = list(cobj.load_data("IT_training_data").columns)
    real, log, nuts1 = IT.convert_it_2024_full(template)
    se_hh = set(real.loc[real["yseev"].to_numpy() > 0, "idhh"])   # self-employed households

    prof = config.PROFILES["IT"]
    frames, base_pu, wbase = [], None, None
    print(f"scenario sign checks (real IT, {SYSTEM}, {DATASET}):")
    for scen in config.SCENARIOS:
        if scen == "baseline":
            out = engine.run(cobj, SYSTEM, real, DATASET).outputs[0]
        else:
            reform = prof["reforms"][scen]; t = reform["type"]
            if t in ("const_scale", "rate_delta"):
                consts, _ = reforms.build_const_overwrites(sysobj, reform)
                out = engine.run(cobj, SYSTEM, real, DATASET, constants=consts).outputs[0]
            elif t == "income_scale":
                r2 = dict(reform); r2["vars"] = EARN_VARS
                out = engine.run(cobj, SYSTEM, reforms.income_scale(real, r2), DATASET).outputs[0]
            elif t == "unemployment":
                d, _ = reforms.unemployment_shock(real, reform)
                d.loc[d["les"] == config.LES_UNEMPLOYED, "yseev"] = 0
                out = engine.run(cobj, SYSTEM, d, DATASET).outputs[0]
            elif t == "param_mutate_scale":
                out, minfo = reforms.run_with_param_mutation(cobj, sysobj, SYSTEM, real, DATASET, reform)
                print(f"   (AUU #_Amount cells scaled: {minfo.get('cells_scaled')})")
        pu = adapter.euromod_to_per_unit(out, "IT", YEAR, scen)
        frames.append(pu)
        if scen == "baseline":
            base_pu = pu; wbase = adapter.weighted_disposable(pu)
        else:
            delta = adapter.weighted_disposable(pu) - wbase
            nch = int((pu.set_index("unit_id")["net_income"] != base_pu.set_index("unit_id")["net_income"]).sum())
            sign = "+" if delta > 1 else "-" if delta < -1 else "0"; exp = config.EXPECTED_SIGN[scen]
            print(f"  [{scen:18}] delta={delta:>18,.0f} EUR/yr  sign {sign} (exp {exp}) "
                  f"{'OK' if sign == exp else 'CHECK'}  hh_changed={nch:,}")
    print("ENGINE:", engine.assert_matched_engine())

    layer = pd.concat(frames, ignore_index=True)
    W.validate_schema(layer)
    ev = W.compute_ev(layer); summary = W.wevm(ev, equivalise=True)
    eps_cols = [c for c in summary.columns if c.startswith("wevm_eps_")]
    print("\nWEVM epsilon grids (annual EUR, real IT):")
    for _, r in summary.iterrows():
        grid = "  ".join(f"{c.replace('wevm_', '')}={r[c]:,.0f}" for c in eps_cols)
        print(f"  [{r['scenario']:18}] {grid}")
        print(f"       winners={r['winners_pop']:,.0f} losers={r['losers_pop']:,.0f} floored={int(r['units_floored'])}")

    # self-employed subgroup WEVM sanity (share of EV accruing to self-employed hh)
    print("\nself-employed-subgroup WEVM sanity (share of weighted EV to self-employed hh):")
    ev["is_se"] = ev["unit_id"].astype(float).astype("int64").isin(se_hh)
    print(f"   (self-employed hh matched in layer: {ev[ev['scenario']==config.SCENARIOS[1]]['is_se'].sum():,})")
    for scen in config.SCENARIOS[1:]:
        s = ev[ev["scenario"] == scen]
        tot_ev = float((s["ev"] * s["survey_weight"]).sum())
        se_ev = float((s.loc[s["is_se"], "ev"] * s.loc[s["is_se"], "survey_weight"]).sum())
        sh = se_ev / tot_ev * 100 if abs(tot_ev) > 1 else float("nan")
        print(f"  [{scen:18}] total EV {tot_ev:>16,.0f} | self-emp EV {se_ev:>16,.0f} | "
              f"self-emp share {sh:6.1f}% (self-emp = 30.4% of pop)")


if __name__ == "__main__":
    main()
