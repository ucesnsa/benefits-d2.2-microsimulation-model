#!/usr/bin/env python3
"""Byte-compile every Python file in the tree and report anything that fails.

Three artefacts have been found broken by accident this month, and all three were a
syntax or indentation error at bottom: the UK pipeline could not import at all, the
provenance verifier was advertised as runnable and was not, and the provider audit
script had not parsed since an indentation slip survived a commit. The common factor
is that the check suite exercises five scripts and the repository contains far more.

This closes that class. It compiles, it does not import: importing runs module-level
code, and several scripts in this tree resolve engine paths or read licensed microdata
at import time. Compilation catches exactly what all three failures were.

Usage:
    py -3 check_parses.py            # every tracked .py file
    py -3 check_parses.py --list     # also list what was checked

Exit code 0 if everything compiles, 1 otherwise. Read-only.
"""
from __future__ import annotations

import py_compile
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules"}
# Retired artefacts are kept on disk deliberately and are not expected to run. They are
# still compiled, but a failure there is reported separately and does not fail the run:
# the point of _superseded/ is that it is out of service.
SOFT_DIRS = {"_superseded"}


def collect() -> list[Path]:
    out = []
    for p in sorted(ROOT.rglob("*.py")):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        out.append(p)
    return out


def main(argv: list[str]) -> int:
    show = "--list" in argv
    files = collect()
    hard_bad, soft_bad = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for p in files:
            target = Path(tmp) / (p.relative_to(ROOT).as_posix().replace("/", "_") + "c")
            soft = any(part in SOFT_DIRS for part in p.parts)
            try:
                py_compile.compile(str(p), cfile=str(target), doraise=True)
                if show:
                    print(f"  ok    {p.relative_to(ROOT).as_posix()}")
            except py_compile.PyCompileError as exc:
                msg = str(exc).strip().splitlines()[-1]
                (soft_bad if soft else hard_bad).append(
                    (p.relative_to(ROOT).as_posix(), msg))

    print(f"compiled {len(files)} Python files under {ROOT.name}/")
    if soft_bad:
        print(f"\n{len(soft_bad)} failing under _superseded/ (retired, not a failure):")
        for rel, msg in soft_bad:
            print(f"  {rel}\n      {msg}")
    if hard_bad:
        print(f"\nFAIL: {len(hard_bad)} file(s) do not compile:")
        for rel, msg in hard_bad:
            print(f"  {rel}\n      {msg}")
        return 1
    print("OVERALL: PASS (every live Python file compiles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
