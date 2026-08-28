"""
build.py -- BENEFITS D2.2 EU synthetic build orchestrator.

>>> SYNTHETIC PIPELINE-VALIDATION FLOOR -- NOT the source of the committed dial surfaces.
This runs the early six-scenario sign-check on EUROMOD's bundled TRAINING data (2,397
households) and writes common/build_summary.json. The committed REAL dial surfaces
(europe/<Country>/outputs/dial_grid.json) are built by build_grid.py on the EU-SILC data -- see europe/<Country>/outputs/surface_provenance.json.

One pipeline, all countries. For EL, IT and ES it: confirms the matched engine;
runs the baseline plus five reforms on the locked 2024 system; maps each scenario
to the canonical per-unit data layer; writes one git-ignored layer per country
(all six scenarios, long format); validates the schema; and runs the layer through
the WEVM welfare layer end to end. Prints a structured report and writes a
machine-readable summary. Data-free: schema, counts and aggregates only.

Run:  python build.py            (all three countries)
      python build.py EL IT      (a subset)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EUROPE = os.path.dirname(HERE)
OUTPUTS = os.path.join(EUROPE, "outputs")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(EUROPE, "wevm"))

import pandas as pd  # noqa: E402

import config  # noqa: E402
import engine  # noqa: E402
import adapter  # noqa: E402
import reforms  # noqa: E402
import wevm as W  # noqa: E402


def _sign(x, tol=1.0):
    return "+" if x > tol else "-" if x < -tol else "0"


def _jsonable(consts):
    return {f"{n}|{g}": v for (n, g), v in consts.items()}


def build_country(short):
    prof = config.PROFILES[short]
    year = prof["system_year"]
    ds = prof["dataset_id"]
    sysname = f"{short}_{year}"
    mod = engine.load_model()
    cobj = mod.countries[short]
    sysobj = engine.get_system(cobj, sysname)
    data = cobj.load_data(ds)

    # baseline
    base_out = engine.run(cobj, sysname, data, ds).outputs[0]
    base_pu = adapter.euromod_to_per_unit(base_out, short, year, "baseline")
    wbase = adapter.weighted_disposable(base_pu)
    frames = [base_pu]
    scen_report = {}

    for scen in config.SCENARIOS[1:]:
        reform = prof["reforms"][scen]
        t = reform["type"]
        info = {"type": t, "note": reform.get("note", "")}
        if t in ("const_scale", "rate_delta"):
            consts, skipped = reforms.build_const_overwrites(sysobj, reform)
            info["overwrites"] = _jsonable(consts)
            info["skipped"] = skipped
            out = engine.run(cobj, sysname, data, ds, constants=consts).outputs[0]
        elif t == "income_scale":
            out = engine.run(cobj, sysname, reforms.income_scale(data, reform), ds).outputs[0]
        elif t == "unemployment":
            d, uinfo = reforms.unemployment_shock(data, reform)
            info.update(uinfo)
            out = engine.run(cobj, sysname, d, ds).outputs[0]
        elif t == "param_mutate_scale":
            out, minfo = reforms.run_with_param_mutation(cobj, sysobj, sysname, data, ds, reform)
            info.update(minfo)
        else:
            raise ValueError(t)

        pu = adapter.euromod_to_per_unit(out, short, year, scen)
        frames.append(pu)
        delta = adapter.weighted_disposable(pu) - wbase
        n_changed = int((pu.set_index("unit_id")["net_income"]
                         != base_pu.set_index("unit_id")["net_income"]).sum())
        sign = _sign(delta)
        info.update({"weighted_dispy_delta_eur_yr": round(delta, 0),
                     "sign": sign, "expected_sign": config.EXPECTED_SIGN[scen],
                     "sign_match": sign == config.EXPECTED_SIGN[scen],
                     "households_changed": n_changed})
        scen_report[scen] = info

    # canonical layer
    export = pd.concat(frames, ignore_index=True)
    W.validate_schema(export)
    cdir = os.path.join(OUTPUTS, short)
    os.makedirs(cdir, exist_ok=True)
    path = os.path.join(cdir, "per_unit_export.parquet")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    export.to_parquet(path, index=False)

    # WEVM end to end via the canonical seam (load -> validate -> compute -> wevm)
    df = W.load_per_unit_export(path)
    summary = W.wevm(W.compute_ev(df), equivalise=True)
    eps_cols = [c for c in summary.columns if c.startswith("wevm_eps_")]
    for scen in config.SCENARIOS[1:]:
        row = summary[summary["scenario"] == scen]
        if row.empty:
            continue
        r = row.iloc[0]
        scen_report[scen]["wevm"] = {c: round(float(r[c]), 0) for c in eps_cols}
        scen_report[scen]["winners_pop"] = round(float(r["winners_pop"]), 0)
        scen_report[scen]["losers_pop"] = round(float(r["losers_pop"]), 0)
        scen_report[scen]["units_floored"] = int(r["units_floored"])

    return {
        "country": short, "system": sysname, "engine": engine.assert_matched_engine(),
        "baseline_shape": list(base_out.shape), "n_households": int(base_pu.shape[0]),
        "layer_path": os.path.relpath(path, EUROPE), "layer_rows": int(export.shape[0]),
        "scenarios": scen_report,
    }


def main(countries):
    results = {}
    for short in countries:
        print(f"\n{'='*78}\nBUILD {short}\n{'='*78}")
        res = build_country(short)
        results[short] = res
        print(f"engine: {res['engine']}")
        print(f"system {res['system']} | baseline {tuple(res['baseline_shape'])} | "
              f"households {res['n_households']} | layer {res['layer_rows']} rows -> {res['layer_path']}")
        for scen, info in res["scenarios"].items():
            ok = "OK" if info["sign_match"] else "CHECK"
            eps1 = info.get("wevm", {}).get("wevm_eps_1")
            eps1s = f"{eps1:,.0f}" if eps1 is not None else "n/a"
            print(f"  [{scen:18}] delta={info['weighted_dispy_delta_eur_yr']:>16,.0f} EUR/yr "
                  f"sign {info['sign']} (exp {info['expected_sign']}) {ok} | "
                  f"hh_changed={info['households_changed']} | WEVM eps1={eps1s}")
            print(f"       winners={info.get('winners_pop')} losers={info.get('losers_pop')} "
                  f"floored={info.get('units_floored')}")

    os.makedirs(OUTPUTS, exist_ok=True)
    with open(os.path.join(OUTPUTS, "build_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)

    print(f"\n{'='*78}\nSUMMARY\n{'='*78}")
    for short, res in results.items():
        signs = {s: i["sign_match"] for s, i in res["scenarios"].items()}
        allok = all(signs.values())
        print(f"  {short}: layer {res['layer_rows']} rows, 6 scenarios | sign checks "
              f"{'ALL OK' if allok else signs}")
    return 0


if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:]] or list(config.PROFILES)
    raise SystemExit(main(args))
