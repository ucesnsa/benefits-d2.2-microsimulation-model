"""Validate the minimum ES conversion: aggregates + a matched-engine baseline run.
Data-free (counts, distributions, weighted aggregates only)."""
import os
import sys

# MODEL is the country's model/ directory, which holds pipeline/ and wevm/.
EUROPE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      os.pardir, os.pardir, os.pardir))
MODEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     os.pardir))
sys.path.insert(0, os.path.join(MODEL, "pipeline"))
sys.path.insert(0, os.path.join(MODEL, "wevm"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pandas as pd  # noqa: E402
import engine  # noqa: E402
import convert  # noqa: E402

mod = engine.load_model()
cobj = mod.countries["ES"]
template = list(cobj.load_data("ES_training_data").columns)
real = convert.convert_es_2024(template)

print("converted rows:", len(real), "cols:", real.shape[1])
print("n households:", real["idhh"].nunique())
print("dag range:", int(real["dag"].min()), "-", int(real["dag"].max()))
print("les dist:", {int(k): int(v) for k, v in pd.Series(real["les"]).value_counts().sort_index().items()})
print("dgn dist:", {int(k): int(v) for k, v in pd.Series(real["dgn"]).value_counts().sort_index().items()})
print("weighted pop (sum dwt):", f"{float(real['dwt'].sum()):,.0f}")
print("yem monthly mean among les=3:", f"{float(real.loc[real.les == 3, 'yem'].mean()):,.2f}")
print("yse monthly mean among les=2:", f"{float(real.loc[real.les == 2, 'yse'].mean()):,.2f}")

sim = engine.run(cobj, "ES_2024", real, "ES_training_data")
print("\nENGINE:", engine.assert_matched_engine())
print("baseline errors:", len(sim.errors), "shape:", sim.outputs[0].shape)
out = sim.outputs[0]
for v in ("ils_dispy", "ils_origy", "ils_ben"):
    if v in out.columns:
        hh = out.groupby("idhh")[v].sum()
        w = out.groupby("idhh")["dwt"].first()
        print(f"  {v}: weighted total (monthly EUR) = {float((hh * w).sum()):,.0f} | mean per hh = {float(hh.mean()):,.2f}")
