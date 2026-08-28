#!/usr/bin/env python3
"""Refresh each COUNTRY block's embedded grid from its canonical surface.

The JSON duplication is this project's main hazard: a surface is regenerated, the
page keeps the old copy, and check_drift.py catches it after the fact. This makes the
re-embed a step you run rather than a thing you remember, and it is the only sanctioned
way to update the `grid` key of a country block.

Everything except `grid` is left untouched, byte for byte, so the block's prose,
provenance and provider layer are never disturbed by a surface rebuild.

Usage:  python3 refresh_blocks.py            # all four, report what moved
        python3 refresh_blocks.py --check    # report only, change nothing
"""

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DELIV = HERE.parent.parent

BLOCKS = {
    "uk": (HERE / "country_uk.json", DELIV / "uk" / "outputs" / "dial_grid.json"),
    "es": (HERE / "country_es.json", DELIV / "europe" / "Spain" / "outputs" / "dial_grid.json"),
    "it": (HERE / "country_it.json", DELIV / "europe" / "Italy" / "outputs" / "dial_grid.json"),
    "el": (HERE / "country_el.json", DELIV / "europe" / "Greece" / "outputs" / "dial_grid.json"),
}


def sig(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report whether each block is current; change nothing")
    args = ap.parse_args()

    stale = 0
    for cc, (block_path, surface_path) in BLOCKS.items():
        block = json.loads(block_path.read_text(encoding="utf-8"))
        surface = json.loads(surface_path.read_text(encoding="utf-8"))
        before, after = sig(block.get("grid")), sig(surface)
        if before == after:
            print(f"  {cc}: current   grid {after[:12]}")
            continue
        stale += 1
        print(f"  {cc}: STALE     embedded {before[:12]} -> canonical {after[:12]}")
        if args.check:
            continue
        block["grid"] = surface
        # write_bytes, not write_text: write_text would translate the block's LF to
        # CRLF on Windows and not elsewhere, so the authoring file, and every tool
        # instantiated from it, would differ by platform rather than by content.
        block_path.write_bytes(
            json.dumps(block, ensure_ascii=False, indent=1).encode("utf-8"))
        print(f"       refreshed {block_path.name}")
    if args.check:
        print(f"\n{stale} block(s) stale" if stale else "\nall four blocks current")
        raise SystemExit(1 if stale else 0)
    print(f"\nrefreshed {stale} block(s)" if stale else "\nnothing to do; all current")


if __name__ == "__main__":
    main()
