#!/usr/bin/env python3
"""Refresh the EU blocks' precomputed SCENARIO figures from their own grids.

`refresh_blocks.py` re-embeds `COUNTRY.grid` and nothing else, by design: everything
outside `grid` is authored prose, provenance and the provider layer, and a surface
rebuild must not disturb any of it. But `COUNTRY.data` is neither. For the three EU
blocks it holds the Scenarios tab's precomputed welfare, decile, fiscal and
winners/losers figures, and every one of them IS a point of the grid: each scenario in
`COUNTRY.scenarios` names the `dial` and `mag` it was read from, and the stored values
equal that point.

So a rebuilt surface leaves `COUNTRY.data` stale while `COUNTRY.grid` is current, and the
tool shows one set of numbers on the Analyst tab and another on the Scenarios tab.
`check_drift.py` catches HALF of that: its `check_scenario_fiscal` compares `data.fiscal`
against the grid point, which is exactly this hazard for the fiscal fields. It compares
nothing for `data.wevm`, `data.deciles` or `data.winlose`, which are the welfare figures the
Scenarios tab leads with. This script keeps all four in step, and running it leaves the
drift check's own comparison passing rather than replacing it.

THE UK BLOCK IS NOT TOUCHED, and not because the UK was not rebuilt. Its scenario data
is a different object: `data.fiscal` carries the UK's own ten-field named schema rather
than the grid's six, `data.winlose` carries decile vectors the EU blocks do not have, and
five of its scenarios are combinations that correspond to no single grid point. It is
authored, not derived, and this script has no business in it.

Usage:  py -3 refresh_scenarios.py            # report and refresh
        py -3 refresh_scenarios.py --check    # report only, change nothing
"""

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOCKS = ["country_es.json", "country_it.json", "country_el.json"]
TOL = 5e-4          # the grid rounds to three decimals; anything under that is the same


def close(a, b):
    """Numeric-aware equality over the nested shapes these fields take."""
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(close(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= TOL
    return a == b


def ordered_like(new, old):
    """`new` with the key order of `old`, so a refresh does not reshuffle the file."""
    if not isinstance(old, dict) or not isinstance(new, dict):
        return new
    out = {k: new[k] for k in old if k in new}
    out.update({k: v for k, v in new.items() if k not in out})
    return out


def point_for(grid, dial, mag):
    d = grid.get("dials", {}).get(dial)
    if not d:
        return None
    for p in d["points"]:
        if p["magnitude"] == mag:
            return p
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    stale_total = 0
    for name in BLOCKS:
        path = HERE / name
        block = json.loads(path.read_text(encoding="utf-8"))
        grid, data = block.get("grid") or {}, block.get("data") or {}
        moved, skipped, same = [], [], 0
        for scen in block.get("scenarios", []):
            sid, dial, mag = scen.get("id"), scen.get("dial"), scen.get("mag")
            if sid == "baseline" or not dial or mag is None:
                continue
            pt = point_for(grid, dial, mag)
            if pt is None:
                skipped.append(sid)
                continue
            new = {"wevm": pt["wevm"], "deciles": pt["deciles"], "fiscal": pt["fiscal"],
                   "winlose": {"gain": round(pt["winners_pct"] / 100, 4),
                               "lose": round(pt["losers_pct"] / 100, 4)}}
            if all(close(data.get(f, {}).get(sid), new[f]) for f in new):
                same += 1
                continue
            moved.append(sid)
            if not args.check:
                for f, v in new.items():
                    data.setdefault(f, {})[sid] = ordered_like(v, data.get(f, {}).get(sid))
        print(f"  {name}: {same} current, {len(moved)} stale"
              + (f" -> {', '.join(moved)}" if moved else "")
              + (f"; not in the grid: {', '.join(skipped)}" if skipped else ""))
        stale_total += len(moved)
        if moved and not args.check:
            block["data"] = data
            path.write_bytes(
                json.dumps(block, ensure_ascii=False, indent=1).encode("utf-8"))
            print(f"       rewrote {name}")
    if args.check:
        print(f"\n{stale_total} scenario figure(s) stale" if stale_total
              else "\nevery precomputed EU scenario figure matches its grid point")
        raise SystemExit(1 if stale_total else 0)
    print(f"\nrefreshed {stale_total} scenario figure(s)" if stale_total
          else "\nnothing to do")


if __name__ == "__main__":
    main()
