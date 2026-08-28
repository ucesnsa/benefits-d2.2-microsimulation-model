#!/usr/bin/env python3
"""
validate_grid.py -- country-agnostic validator for a Level 2 dial response surface.

BENEFITS D2.2. This harness proves that a dial_grid.json (the pre-computed welfare
response surface read by tools/dial_tool.html) is structurally sound and internally
consistent before the interface is trusted on it.

Its purpose is the EU reuse, not the UK build (which is already validated): when a
country's pipeline regenerates its surface and the GRID block is swapped into the dial
tool, run this first as a build gate. It validates ANY dial_grid.json, not just the UK
one, by reading the aggregate surface only. It never touches microdata and prints only
aggregates.

Checks (each prints PASS / FAIL / WARN with evidence; the process exits non-zero on any
FAIL so it can gate a build):
  1. Structure         meta, dials and the binary toggle carry the required fields.
  2. Epsilon grid      the full epsilon vector is stored per point and is consistent.
  3. Baseline anchor   every dial's zero-magnitude point is exactly 0 at every epsilon,
                       and every toggle's "off" state is 0 (the baseline is the zero point).
  4. Monotonicity      each dial's WEVM curve is monotonic in one direction across its
                       magnitude grid at every epsilon; the direction is reported, and
                       asserted if the dial declares one. Non-monotonicity is flagged
                       loudly, never passed silently.
  5. Decile sum        each point's decile contributions sum to its headline WEVM at every
                       epsilon, within a rounding tolerance.
  6. Epsilon response  the WEVM actually moves with epsilon (epsilon is wired in, not
                       frozen); the per-dial epsilon gradient is reported so a reviewer can
                       eyeball it (a bottom-targeted expansion should rise with epsilon).

Optionally, with --reference PATH, coincident reference scenarios are reproduced from the
surface and the maximum absolute difference is reported. The reference is a JSON file:

    {
      "eps_grid": [0, 0.5, 1, 1.5, 2],          # optional, checked if present
      "points": [
        {"label": "unemployment +3pp", "dial": "unemployment_shock",
         "magnitude": 3, "wevm": [...one value per epsilon...]},
        {"label": "remove the charge", "toggle": "hicbc_removal",
         "state": "on", "wevm": [...]}
      ]
    }

Dial points are interpolated linearly from the surface (matching the interface); points
whose magnitude lands exactly on a stored node, and toggle states, are compared exactly.

Usage:
    python validate_grid.py outputs/frs_2023_24/dial_grid.json
    python validate_grid.py <grid.json> --reference <ref.json>
"""

from __future__ import annotations

import argparse
import json
import sys

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"

# Semantic meta fields, with the accepted key names. The UK builder emits the first of
# each; a country that renames one only has to land on one of these aliases (or this list
# is the single place to extend). This is what keeps the harness country-agnostic.
META_BASELINE_KEYS = ("baseline_net_income_bn", "baseline_total", "baseline_net_income")
META_UNITS_KEYS = ("n_units_working_age_sample", "n_units", "units", "n_units_total")
META_TAKEUP_KEYS = ("uc_takeup_rate", "takeup_rate", "takeup")

# Direction words a dial may declare in an optional "expected_direction" / "direction" key.
DIR_WORDS = {
    "up": 1, "increasing": 1, "increase": 1, "rising": 1, "+": 1, "pos": 1, "positive": 1,
    "down": -1, "decreasing": -1, "decrease": -1, "falling": -1, "-": -1, "neg": -1, "negative": -1,
}
DIR_NAME = {1: "increasing", -1: "decreasing", 0: "flat"}


# ----------------------------------------------------------------------------
# Report accumulator
# ----------------------------------------------------------------------------
class Report:
    def __init__(self):
        self.checks = []  # list of (name, status, lines)

    def add(self, name, status, lines):
        self.checks.append((name, status, list(lines)))

    def any_failed(self):
        return any(s == FAIL for _, s, _ in self.checks)

    def render(self):
        out = []
        for name, status, lines in self.checks:
            out.append(f"[{status}] {name}")
            out.extend("       " + ln for ln in lines)
        n_fail = sum(s == FAIL for _, s, _ in self.checks)
        n_warn = sum(s == WARN for _, s, _ in self.checks)
        n_pass = sum(s == PASS for _, s, _ in self.checks)
        out.append("")
        verdict = "FAIL" if n_fail else "PASS"
        out.append(f"OVERALL: {verdict}   ({n_pass} pass, {n_warn} warn, {n_fail} fail)")
        return "\n".join(out)


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def _first_key(d, keys):
    for k in keys:
        if isinstance(d, dict) and k in d:
            return k
    return None


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _declared_dir(dial):
    raw = dial.get("expected_direction", dial.get("direction"))
    if raw is None:
        return None
    return DIR_WORDS.get(str(raw).strip().lower())


def _eps_grid(grid):
    return list(grid.get("meta", {}).get("eps_grid", []) or [])


def _ref_eps_index(eps):
    """Index of epsilon == 1 if present (the conventional reference), else the middle."""
    for i, e in enumerate(eps):
        if _is_number(e) and abs(e - 1.0) < 1e-9:
            return i
    return len(eps) // 2 if eps else 0


def _sorted_points(dial):
    return sorted(dial["points"], key=lambda p: p["magnitude"])


def _seq_dir(seq, tol):
    """Classify a numeric sequence as increasing / decreasing / const / nonmono."""
    diffs = [seq[k + 1] - seq[k] for k in range(len(seq) - 1)]
    nondec = all(x >= -tol for x in diffs)
    noninc = all(x <= tol for x in diffs)
    if nondec and noninc:
        return "const"
    if nondec:
        return "increasing"
    if noninc:
        return "decreasing"
    return "nonmono"


def _first_reversal(seq, mags, want_up, tol):
    for k in range(len(seq) - 1):
        diff = seq[k + 1] - seq[k]
        if (want_up and diff < -tol) or (not want_up and diff > tol):
            return (mags[k], mags[k + 1], seq[k], seq[k + 1])
    return None


def interp_dial(dial, mag, ei):
    """Linear interpolation of WEVM at epsilon index `ei`, matching the interface.

    Returns (value, is_node) where is_node is True when `mag` coincides with a stored
    grid node (so the comparison is exact rather than interpolated).
    """
    pts = _sorted_points(dial)
    mags = [p["magnitude"] for p in pts]
    x = min(max(mag, mags[0]), mags[-1])
    is_node = any(abs(x - m) < 1e-9 for m in mags)
    i = 0
    while i < len(mags) - 1 and x > mags[i + 1]:
        i += 1
    j = min(i + 1, len(mags) - 1)
    mlo, mhi = mags[i], mags[j]
    f = 0.0 if mhi == mlo else (x - mlo) / (mhi - mlo)
    lo, hi = pts[i]["wevm"][ei], pts[j]["wevm"][ei]
    return lo + f * (hi - lo), is_node


# ----------------------------------------------------------------------------
# Check 1: structure
# ----------------------------------------------------------------------------
def check_structure(grid, n_deciles_expected=10):
    errors, warns, info = [], [], []
    meta = grid.get("meta")
    if not isinstance(meta, dict):
        return FAIL, ["meta: missing or not an object"]

    for k in ("country", "year"):
        if k not in meta:
            errors.append(f"meta.{k}: missing")
    bk = _first_key(meta, META_BASELINE_KEYS)
    uk = _first_key(meta, META_UNITS_KEYS)
    tk = _first_key(meta, META_TAKEUP_KEYS)
    if bk is None:
        errors.append(f"meta: no baseline-total key (any of {META_BASELINE_KEYS})")
    if uk is None:
        errors.append(f"meta: no units key (any of {META_UNITS_KEYS})")
    if tk is None:
        warns.append(f"meta: no take-up key (any of {META_TAKEUP_KEYS}); acceptable if the "
                     "country has no take-up concept")
    eps = meta.get("eps_grid")
    if not isinstance(eps, list) or len(eps) < 2:
        errors.append("meta.eps_grid: missing or has fewer than 2 epsilon values")
        eps = eps if isinstance(eps, list) else []
    info.append(f"country={meta.get('country')}  year={meta.get('year')}  "
                f"baseline[{bk}]={meta.get(bk)}  units[{uk}]={meta.get(uk)}  "
                f"takeup[{tk}]={meta.get(tk)}")
    info.append(f"eps_grid={eps}")

    n_eps = len(eps)
    dials = grid.get("dials")
    if not isinstance(dials, dict) or not dials:
        errors.append("dials: missing or empty")
        dials = {}
    info.append(f"dials={list(dials.keys())}")

    det_deciles = None
    for did, d in dials.items():
        for fld in ("label", "lever", "unit", "baseline_magnitude", "magnitudes", "points"):
            if fld not in d:
                errors.append(f"dial '{did}': missing '{fld}'")
        mags = d.get("magnitudes")
        pts = d.get("points")
        if not isinstance(mags, list) or not isinstance(pts, list):
            continue
        if len(mags) != len(pts):
            errors.append(f"dial '{did}': magnitudes ({len(mags)}) and points ({len(pts)}) differ")
        if len(pts) != 11:
            warns.append(f"dial '{did}': {len(pts)} points (the UK design is 11)")
        if "baseline_magnitude" in d and d["baseline_magnitude"] not in mags:
            errors.append(f"dial '{did}': baseline_magnitude {d['baseline_magnitude']} not in grid")
        for idx, p in enumerate(pts):
            for fld in ("wevm", "deciles", "winners_pct", "losers_pct", "magnitude"):
                if fld not in p:
                    errors.append(f"dial '{did}' point {idx}: missing '{fld}'")
            wv, dc = p.get("wevm"), p.get("deciles")
            if isinstance(wv, list) and n_eps and len(wv) != n_eps:
                errors.append(f"dial '{did}' point {idx}: wevm length {len(wv)} != eps {n_eps}")
            if isinstance(dc, list):
                if n_eps and len(dc) != n_eps:
                    errors.append(f"dial '{did}' point {idx}: deciles outer {len(dc)} != eps {n_eps}")
                for row in dc:
                    if isinstance(row, list):
                        if det_deciles is None:
                            det_deciles = len(row)
                        elif len(row) != det_deciles:
                            errors.append(f"dial '{did}' point {idx}: ragged decile rows "
                                          f"({len(row)} vs {det_deciles})")
    if det_deciles is not None:
        info.append(f"deciles per point = {det_deciles}")
        if det_deciles != n_deciles_expected:
            warns.append(f"decile rows have {det_deciles} entries (expected {n_deciles_expected})")

    toggles = grid.get("toggles")
    if not isinstance(toggles, dict) or not toggles:
        warns.append("toggles: none present (acceptable only if this country defines no binary toggle)")
        toggles = {}
    else:
        info.append(f"toggles={list(toggles.keys())}")
    for tid, t in toggles.items():
        for state in ("off", "on"):
            if state not in t:
                errors.append(f"toggle '{tid}': missing '{state}'")
                continue
            for fld in ("wevm", "deciles", "winners_pct", "losers_pct"):
                if fld not in t[state]:
                    errors.append(f"toggle '{tid}'.{state}: missing '{fld}'")

    status = FAIL if errors else (WARN if warns else PASS)
    lines = info + [f"ERROR: {e}" for e in errors] + [f"warn: {w}" for w in warns]
    return status, lines


# ----------------------------------------------------------------------------
# Check 2: epsilon dimension
# ----------------------------------------------------------------------------
def check_eps_dimension(grid):
    eps = _eps_grid(grid)
    n = len(eps)
    errors = []
    if n < 2:
        return FAIL, [f"eps_grid has {n} value(s); a single epsilon cannot drive the control"]

    def visit(label, point):
        wv = point.get("wevm")
        dc = point.get("deciles")
        if not isinstance(wv, list) or len(wv) != n:
            errors.append(f"{label}: wevm length {len(wv) if isinstance(wv, list) else 'NA'} != {n}")
        if not isinstance(dc, list) or len(dc) != n:
            errors.append(f"{label}: deciles outer length {len(dc) if isinstance(dc, list) else 'NA'} != {n}")

    for did, d in grid.get("dials", {}).items():
        for idx, p in enumerate(d.get("points", [])):
            visit(f"dial '{did}' point {idx} (m={p.get('magnitude')})", p)
    for tid, t in grid.get("toggles", {}).items():
        for state in ("off", "on"):
            if state in t:
                visit(f"toggle '{tid}'.{state}", t[state])

    if errors:
        return FAIL, [f"epsilon grid (length {n}): {eps}"] + [f"ERROR: {e}" for e in errors[:20]]
    return PASS, [f"full epsilon vector (length {n}) stored and consistent at every point: {eps}"]


# ----------------------------------------------------------------------------
# Check 3: baseline anchor
# ----------------------------------------------------------------------------
def check_baseline_anchor(grid, anchor_tol):
    eps = _eps_grid(grid)
    lines, status = [], PASS
    for did, d in grid.get("dials", {}).items():
        bm = d.get("baseline_magnitude")
        zero = next((p for p in d.get("points", []) if abs(p.get("magnitude", 1e30) - bm) < 1e-9), None)
        if zero is None:
            status = FAIL
            lines.append(f"{did}: FAIL no point at baseline_magnitude {bm}")
            continue
        bad = [(eps[ei], v) for ei, v in enumerate(zero.get("wevm", [])) if abs(v) > anchor_tol]
        dbad = any(abs(v) > anchor_tol for row in zero.get("deciles", []) for v in row)
        if bad or dbad:
            status = FAIL
            lines.append(f"{did}: FAIL zero point m={bm} not 0 (e.g. {bad[:3]}); deciles_nonzero={dbad}")
        else:
            lines.append(f"{did}: PASS zero point m={bm} is 0 at every epsilon")
    for tid, t in grid.get("toggles", {}).items():
        off = t.get("off", {})
        bad = [(eps[ei], v) for ei, v in enumerate(off.get("wevm", [])) if abs(v) > anchor_tol]
        if bad:
            status = FAIL
            lines.append(f"toggle '{tid}'.off: FAIL not 0 (e.g. {bad[:3]})")
        else:
            lines.append(f"toggle '{tid}'.off: PASS is 0 at every epsilon")
    return status, lines


# ----------------------------------------------------------------------------
# Check 4: monotonicity
# ----------------------------------------------------------------------------
def check_monotonicity(grid, mono_tol):
    eps = _eps_grid(grid)
    ref_ei = _ref_eps_index(eps)
    lines, status = [], PASS
    for did, d in grid.get("dials", {}).items():
        pts = _sorted_points(d)
        mags = [p["magnitude"] for p in pts]
        dirs = [_seq_dir([p["wevm"][ei] for p in pts], mono_tol) for ei in range(len(eps))]
        nonmono = [eps[ei] for ei, dd in enumerate(dirs) if dd == "nonmono"]
        real = sorted({dd for dd in dirs if dd in ("increasing", "decreasing")})
        ref_seq = [p["wevm"][ref_ei] for p in pts]
        span = f"{ref_seq[0]:,.1f} -> {ref_seq[-1]:,.1f} at eps={eps[ref_ei]}"

        if nonmono:
            status = FAIL
            ei = dirs.index("nonmono")
            seq = [p["wevm"][ei] for p in pts]
            up = (seq[-1] - seq[0]) >= 0
            rev = _first_reversal(seq, mags, up, mono_tol)
            lines.append(f"{did}: FAIL non-monotonic at eps={eps[ei]}; reversal m "
                         f"{rev[0]}->{rev[1]} wevm {rev[2]:,.3f}->{rev[3]:,.3f}")
            continue
        if len(real) > 1:
            status = FAIL
            lines.append(f"{did}: FAIL direction flips across epsilon ({real}); range {span}")
            continue

        obs = 1 if real == ["increasing"] else (-1 if real == ["decreasing"] else 0)
        declared = _declared_dir(d)
        if declared is not None and obs != 0 and declared != obs:
            status = FAIL
            lines.append(f"{did}: FAIL declared {DIR_NAME[declared]} but observed {DIR_NAME[obs]}; range {span}")
            continue
        tag = DIR_NAME[obs] if obs else "flat (constant across magnitude)"
        suffix = " [matches declared]" if declared is not None else ""
        lines.append(f"{did}: PASS {tag}{suffix}; range {span}")
        if obs == 0:
            lines.append(f"       note: {did} is flat across its magnitude grid; check the lever is wired")
    return status, lines


# ----------------------------------------------------------------------------
# Check 5: decile sum consistency
# ----------------------------------------------------------------------------
def check_decile_sum(grid, decile_tol):
    eps = _eps_grid(grid)
    worst = (0.0, None)

    def visit(label, point):
        nonlocal worst
        for ei in range(len(eps)):
            s = sum(point["deciles"][ei])
            diff = abs(s - point["wevm"][ei])
            if diff > worst[0]:
                worst = (diff, f"{label} at eps={eps[ei]} (sum {s:,.4f} vs wevm {point['wevm'][ei]:,.4f})")

    for did, d in grid.get("dials", {}).items():
        for p in d.get("points", []):
            visit(f"dial '{did}' m={p['magnitude']}", p)
    for tid, t in grid.get("toggles", {}).items():
        for state in ("off", "on"):
            if state in t:
                visit(f"toggle '{tid}'.{state}", t[state])

    if worst[0] > decile_tol:
        return FAIL, [f"max |sum(deciles) - wevm| = {worst[0]:.6f} > tol {decile_tol} at {worst[1]}"]
    return PASS, [f"deciles sum to the headline everywhere; max |diff| = {worst[0]:.6f} (tol {decile_tol})",
                  f"worst case: {worst[1]}"]


# ----------------------------------------------------------------------------
# Check 6: epsilon response
# ----------------------------------------------------------------------------
def check_eps_response(grid, eps_tol):
    eps = _eps_grid(grid)
    lines = []
    any_varies = False

    def grad_line(label, point, mag):
        nonlocal any_varies
        v0, vL = point["wevm"][0], point["wevm"][-1]
        g = vL - v0
        if abs(g) > eps_tol:
            any_varies = True
        move = "rises" if g > eps_tol else ("falls" if g < -eps_tol else "flat")
        lines.append(f"{label} (m={mag}): WEVM eps[{eps[0]}]={v0:,.1f} -> eps[{eps[-1]}]={vL:,.1f}  "
                     f"(gradient {g:+,.1f}, {move} with epsilon)")

    for did, d in grid.get("dials", {}).items():
        bm = d.get("baseline_magnitude")
        pts = d.get("points", [])
        extreme = max(pts, key=lambda p: abs(p["magnitude"] - bm)) if pts else None
        if extreme is not None:
            grad_line(did, extreme, extreme["magnitude"])
    for tid, t in grid.get("toggles", {}).items():
        if "on" in t:
            grad_line(f"toggle '{tid}'", t["on"], "on")

    if not any_varies:
        return FAIL, ["epsilon appears NOT wired in: WEVM is flat across the epsilon grid for every "
                      "dial and toggle"] + lines
    return PASS, ["epsilon is wired in (WEVM responds to epsilon). Per-dial gradients for eyeballing:"] + lines


# ----------------------------------------------------------------------------
# Optional: reference reproduction
# ----------------------------------------------------------------------------
def check_reference(grid, ref, node_tol, interp_tol):
    eps = _eps_grid(grid)
    lines = []
    ref_eps = ref.get("eps_grid")
    if ref_eps is not None and list(ref_eps) != list(eps):
        lines.append(f"warn: reference eps_grid {ref_eps} differs from surface {eps}")
    points = ref.get("points", ref if isinstance(ref, list) else [])
    node_max, interp_max = 0.0, 0.0
    status = PASS
    for rp in points:
        label = rp.get("label", "?")
        expect = rp.get("wevm", [])
        if len(expect) != len(eps):
            status = FAIL
            lines.append(f"{label}: FAIL reference wevm length {len(expect)} != eps {len(eps)}")
            continue
        if "toggle" in rp:
            t = grid.get("toggles", {}).get(rp["toggle"])
            if not t or rp.get("state") not in t:
                status = FAIL
                lines.append(f"{label}: FAIL toggle '{rp.get('toggle')}'.{rp.get('state')} not in surface")
                continue
            got = t[rp["state"]]["wevm"]
            md = max(abs(a - b) for a, b in zip(got, expect))
            node_max = max(node_max, md)
            lines.append(f"{label}: toggle {rp['toggle']}.{rp['state']}  max|diff|={md:.4f}  (exact)")
        else:
            did = rp.get("dial")
            d = grid.get("dials", {}).get(did)
            if not d:
                status = FAIL
                lines.append(f"{label}: FAIL dial '{did}' not in surface")
                continue
            got, is_node = zip(*[interp_dial(d, rp["magnitude"], ei) for ei in range(len(eps))])
            is_node = is_node[0]
            md = max(abs(a - b) for a, b in zip(got, expect))
            if is_node:
                node_max = max(node_max, md)
            else:
                interp_max = max(interp_max, md)
            kind = "exact node" if is_node else "interpolated"
            lines.append(f"{label}: dial {did}@{rp['magnitude']}  max|diff|={md:.4f}  ({kind})")
    if node_max > node_tol:
        status = FAIL
    if interp_max > interp_tol:
        status = FAIL
    head = (f"exact-node/toggle reproduction max|diff| = {node_max:.4f} (tol {node_tol}); "
            f"interpolated reproduction max|diff| = {interp_max:.4f} (tol {interp_tol})")
    return status, [head] + lines


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
def run(grid, args):
    rep = Report()

    def safe(name, fn):
        try:
            status, lines = fn()
        except Exception as exc:  # a malformed surface should fail loudly, not crash
            status, lines = FAIL, [f"check raised {type(exc).__name__}: {exc}"]
        rep.add(name, status, lines)

    safe("1. Structure", lambda: check_structure(grid))
    safe("2. Epsilon dimension", lambda: check_eps_dimension(grid))
    safe("3. Baseline anchor", lambda: check_baseline_anchor(grid, args.anchor_tol))
    safe("4. Monotonicity", lambda: check_monotonicity(grid, args.mono_tol))
    safe("5. Decile sum consistency", lambda: check_decile_sum(grid, args.decile_tol))
    safe("6. Epsilon response", lambda: check_eps_response(grid, args.eps_tol))

    if args.reference:
        with open(args.reference, encoding="utf-8") as f:
            ref = json.load(f)
        safe("7. Reference reproduction", lambda: check_reference(grid, ref, args.node_tol, args.interp_tol))

    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate a Level 2 dial response surface (dial_grid.json).")
    ap.add_argument("grid_path", help="path to a dial_grid.json")
    ap.add_argument("--reference", help="optional reference JSON of coincident scenarios to reproduce")
    ap.add_argument("--mono-tol", type=float, default=0.01, help="monotonicity slack, surface units (default 0.01)")
    ap.add_argument("--decile-tol", type=float, default=0.01, help="decile-sum tolerance (default 0.01)")
    ap.add_argument("--eps-tol", type=float, default=0.001, help="min epsilon gradient counted as varying (default 0.001)")
    ap.add_argument("--anchor-tol", type=float, default=1e-9, help="baseline-zero tolerance (default 1e-9)")
    ap.add_argument("--node-tol", type=float, default=0.01, help="reference exact-node tolerance (default 0.01)")
    ap.add_argument("--interp-tol", type=float, default=5.0, help="reference interpolated tolerance (default 5.0)")
    args = ap.parse_args(argv)

    with open(args.grid_path, encoding="utf-8") as f:
        grid = json.load(f)

    print(f"Validating dial surface: {args.grid_path}\n")
    rep = run(grid, args)
    print(rep.render())
    return 1 if rep.any_failed() else 0


if __name__ == "__main__":
    sys.exit(main())
