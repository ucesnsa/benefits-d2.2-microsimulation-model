"""
reforms.py -- turn a reform spec into either a constantsToOverwrite dict, an
input-DataFrame transform, or an in-memory parameter mutation. Reform magnitudes
are applied to values read live from the model, so the build never hard-codes
policy values.
"""
import re

import numpy as np

import config
import engine

_NUM = re.compile(r"^(-?[0-9]*\.?[0-9]+)(#[a-zA-Z])?$")


def parse_value(v):
    """'108#m' -> (108.0, '#m'); '0.09' -> (0.09, ''); '5647#Y' -> (5647.0, '#Y')."""
    if v is None:
        return None, None
    m = _NUM.match(str(v).strip())
    if not m:
        return None, None
    return float(m.group(1)), (m.group(2) or "")


def fmt_value(num: float, qual: str) -> str:
    return f"{num:g}{qual}"


# ---------------------------------------------------------------------------
# constantsToOverwrite-based reforms
# ---------------------------------------------------------------------------
def build_const_overwrites(system_obj, reform) -> dict:
    out, skipped = {}, []
    for name, grp in reform["constants"]:
        num, qual = parse_value(engine.read_constant(system_obj, name, grp))
        if num is None:
            skipped.append(name)
            continue
        if reform["type"] == "const_scale":
            new = round(num * reform["factor"], 4)
        elif reform["type"] == "rate_delta":
            new = round(num + reform["delta"], 4)
        else:
            raise ValueError(reform["type"])
        out[(name, str(grp))] = fmt_value(new, qual)
    return out, skipped


# ---------------------------------------------------------------------------
# input-DataFrame transforms
# ---------------------------------------------------------------------------
def income_scale(data, reform):
    d = data.copy()
    for v in reform["vars"]:
        if v in d.columns:
            d[v] = d[v] * reform["factor"]
    return d


def unemployment_shock(data, reform, seed: int = 20240):
    """Raise the unemployment rate by `pp` percentage points: flip a deterministic
    sample of working-age employed individuals (les in LES_EMPLOYED) to unemployed
    (LES_UNEMPLOYED) and zero their earnings. Benefits recompute on the run."""
    d = data.copy()
    employed = d.index[d["les"].isin(config.LES_EMPLOYED) & (d["dag"] >= 18) & (d["dag"] < 65)]
    n_unemployed = int((d["les"] == config.LES_UNEMPLOYED).sum())
    labour_force = len(employed) + n_unemployed
    k = int(round(reform["pp"] * labour_force))
    k = min(k, len(employed))
    rng = np.random.default_rng(seed)
    pick = rng.choice(employed.to_numpy(), size=k, replace=False) if k else np.array([], dtype=int)
    d.loc[pick, "les"] = config.LES_UNEMPLOYED
    for v in ("yem", "yse"):
        if v in d.columns:
            d.loc[pick, v] = 0
    info = {"labour_force": labour_force, "flipped": int(len(pick)),
            "unemployed_before": n_unemployed, "unemployed_after": n_unemployed + int(len(pick))}
    return d, info


# ---------------------------------------------------------------------------
# in-memory parameter mutation (used where the instrument is schedule-based)
# ---------------------------------------------------------------------------
def run_with_param_mutation(country_obj, system_obj, system_name, data, dataset_id, reform):
    """Scale matching schedule amount parameters by `factor`, run, and restore the
    originals. Returns (output_df, info)."""
    params = engine.find_amount_params(
        system_obj, reform["policy"], reform["func"], reform["param"], reform["unit"])
    originals = [(p, p.value) for p in params]
    scaled = []
    try:
        for p, v in originals:
            num, qual = parse_value(v)
            if num is None:
                continue
            p.value = fmt_value(round(num * reform["factor"], 2), qual)
            scaled.append(v)
        sim = engine.run(country_obj, system_name, data, dataset_id)
        out = sim.outputs[0].copy()
    finally:
        for p, v in originals:
            p.value = v
    return out, {"cells_scaled": len(scaled), "policy": reform["policy"]}
