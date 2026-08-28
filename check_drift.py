#!/usr/bin/env python3
"""Drift check: what a tool page holds must equal what the page was built from.

Each country tool HTML carries two duplicated surfaces inside its `const COUNTRY=`
data block. The response surface (COUNTRY.grid) duplicates the canonical
outputs/dial_grid.json. The provider layer (services, outcomes, shock anchors and
targeting profiles) duplicates the authoring block in tool_machinery/country_*.json.
Duplication is the hazard either way: regenerating without re-embedding, or
re-embedding without regenerating, leaves a page presenting stale numbers.

This script parses the embedded COUNTRY object out of each of the four tool pages
and deep-compares both surfaces against their sources, reporting by country. It
reads aggregates only, needs nothing beyond the Python standard library, and exits
non-zero if anything has drifted, so it can gate a build.

Usage:  python3 check_drift.py
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

MACHINERY = ROOT / "europe" / "tool_machinery"

TOOLS = [
    ("UK", ROOT / "uk" / "tools" / "dial_tool_uk.html",
     ROOT / "uk" / "outputs" / "dial_grid.json",
     MACHINERY / "country_uk.json"),
    ("Spain", ROOT / "europe" / "Spain" / "tools" / "dial_tool_spain.html",
     ROOT / "europe" / "Spain" / "outputs" / "dial_grid.json",
     MACHINERY / "country_es.json"),
    ("Italy", ROOT / "europe" / "Italy" / "tools" / "dial_tool_italy.html",
     ROOT / "europe" / "Italy" / "outputs" / "dial_grid.json",
     MACHINERY / "country_it.json"),
    ("Greece", ROOT / "europe" / "Greece" / "tools" / "dial_tool_greece.html",
     ROOT / "europe" / "Greece" / "outputs" / "dial_grid.json",
     MACHINERY / "country_el.json"),
]

# The provider layer is the second duplicated surface: authored in
# tool_machinery/country_*.json and embedded into the page at instantiation.
# Instantiation inserts that file verbatim, so the whole embedded block is
# compared against it; these paths are reported separately because they are the
# provider operational parameters, which no other check covers.
PROVIDER_PATHS = [
    ("data", "services"),     # per-service operational parameters
    ("data", "outcomes"),     # per-outcome valuations, routes and confidence
    ("data", "shockInterp"),  # shock-response anchors
    ("profiles",),            # targeting profiles (decile bands)
]

MARKER = "const COUNTRY="


PLACEHOLDER = "__COUNTRY_JSON__"


def masked_parts(text):
    """A tool page with its COUNTRY literal replaced by the template's placeholder.

    What is left must be the template, byte for byte, because a country tool IS the
    template with one object swapped in. Returns None if no literal is found.
    """
    i = text.find(MARKER)
    if i < 0:
        return None
    start = text.find("{", i)
    if start < 0:
        return None
    depth, j, in_str, esc = 0, start, False, False
    while j < len(text):
        c = text[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    else:
        return None
    return text[:start] + PLACEHOLDER + text[j + 1:]


def normalise_newlines(text):
    """CRLF and CR both to LF.

    instantiate.py used to write through Path.write_text, which translates LF to
    CRLF on Windows while template.html is LF on disk, so a byte comparison of the
    masked parts failed here and passed on macOS: a false negative on the only
    machine the work happens on, which is worse than having no check. Both
    instantiators write bytes now (2026-08-02) and the two platforms agree, so this
    normalisation is no longer load-bearing. It is kept because the check should
    compare tool content, not the line-ending convention of whoever last touched a
    file, and because a tool edited by hand on another platform must still compare.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def check_template_parity(tool_text, template_text, name):
    """The four tools must be one template with four data blocks, nothing else."""
    masked = masked_parts(tool_text)
    if masked is None:
        return [f"{name}: no parsable COUNTRY literal, cannot mask"]
    a, b = normalise_newlines(masked), normalise_newlines(template_text)
    if a == b:
        return []
    # Say where, not just that: the first differing line is the useful part.
    la, lb = a.split("\n"), b.split("\n")
    if len(la) != len(lb):
        return [f"{name}: masked page has {len(la)} lines, template has {len(lb)}"]
    for n, (x, y) in enumerate(zip(la, lb), 1):
        if x != y:
            return [f"{name}: masked page differs from template.html at line {n}: "
                    f"{x.strip()[:70]!r} vs {y.strip()[:70]!r}"]
    return [f"{name}: masked page differs from template.html"]


# A caveat may not be longer than roughly the description of the thing it qualifies.
# The Italian child-benefit caveat was 200 words against a 56-word dial description and
# rendered 303 pixels tall against a 32-pixel headline, which is a presentation failure
# rather than caution: the number and its qualification were competing for the same
# vertical space and the qualification was winning three to one. The rule is a ratio
# rather than an absolute, because a dial that needs seventy words to say what it does can
# carry a longer caveat than one that needs thirty. Anything beyond the cap goes in the
# collapsed `detail`, which is unlimited: nothing is removed, it is one click away.
CAVEAT_WORD_RATIO = 1.4


def _wordcount(s):
    return len(re.sub(r"<[^>]+>", " ", s or "").split())


def check_caveat_length(block):
    """Every dial caveat's VISIBLE part, against its own dial's description."""
    problems = []
    caveats = block.get("dial_caveats") or {}
    texts = block.get("dial_text") or {}
    for dial, v in caveats.items():
        visible = v if isinstance(v, str) else (v or {}).get("short", "")
        base = (texts.get(dial) or {}).get("base")
        if not base:
            # No description to measure against; the ratio rule cannot apply.
            continue
        cap = int(_wordcount(base) * CAVEAT_WORD_RATIO)
        n = _wordcount(visible)
        if n > cap:
            problems.append(
                f"dial_caveats.{dial}: {n} visible words against a {cap}-word cap "
                f"({_wordcount(base)} in the dial's own description x {CAVEAT_WORD_RATIO}). "
                f"Move the rest into the collapsed `detail`.")
    return problems


PRICE_BASE_MARK = "2024-equivalent"


def check_price_base(block):
    """Every provider monetary value must state the panel's price base in its own note.

    The provider tab is a single price base, 2024-equivalent, and a value that does not
    say so is indistinguishable from one left at its source year. Two cells were sitting
    at 2018/19 and 2022/23 while the documentation claimed 2024-equivalent throughout,
    and nothing caught it because nothing was looking. This looks."""
    problems = []
    for s in (dig(block, ("data", "services")) or []):
        if s.get("unitCost") in (None, 0):
            continue
        note = ((s.get("provenance_note") or {}).get("unitCost") or "")
        if PRICE_BASE_MARK not in note:
            problems.append(f"services[{s.get('name')}].unitCost: note does not state the "
                            f"{PRICE_BASE_MARK} price base")
    outcomes = dig(block, ("data", "outcomes")) or {}
    for name, o in outcomes.items():
        if not isinstance(o, dict):
            continue
        money = any(o.get(k) for k in ("convL", "convC", "convH", "wbL", "wbC", "wbH", "sensC"))
        if not money:
            continue
        if PRICE_BASE_MARK not in (o.get("provenance_note") or ""):
            problems.append(f"outcomes[{name}]: valued in money but its note does not state "
                            f"the {PRICE_BASE_MARK} price base")
    return problems


def check_spine_label(block):
    """The spine `value` is documentation: no formula reads it, because the WELLBY
    bands in data.outcomes were multiplied through at build time. That makes it the
    one number in the block that can be edited with no visible effect, which is
    exactly how a page ends up quoting one spine while its arithmetic uses another.
    Assert the label still quotes the value, so the two cannot drift apart silently."""
    spine = block.get("wellby_spine") or {}
    value, label = spine.get("value"), (spine.get("label") or "").strip()
    if value is None:
        return ["wellby_spine.value: absent"]
    symbol = ((block.get("currency") or {}).get("symbol") or "")
    # Anchored, not a substring search: every label also names the GBP 13,000 base
    # in its derivation clause, so a bare `in` test passes when value is set to
    # 13000. The applied figure is the one the label must lead with.
    expected = f"{symbol}{int(value):,}"
    if not label.startswith(expected):
        return [f"wellby_spine: label {label!r} does not lead with the applied "
                f"figure {expected!r}"]
    return []


# The UK block stores its scenario fiscal as LEVELS in bn under short names; the
# surface stores DELTAS in m under long ones. Map one to the other so the two can be
# compared at all. Fields the surface does not carry are simply absent from the map.
UK_FISCAL_MAP = {
    "it": ("income_tax_delta_m", 1000.0),
    "ni": ("sic_delta_m", 1000.0),
    "nier": ("ni_employer_delta_m", 1000.0),
    "uc": ("uc_delta_m", 1000.0),
    "allben": ("benefit_delta_m", 1000.0),
    "childben": ("child_benefit_delta_m", 1000.0),
    "counciltax": ("council_tax_delta_m", 1000.0),
    "net": ("net_income_delta_m", 1000.0),
    "net_exchequer_cost_m": ("net_exchequer_cost_m", 1.0),
}

# The EU blocks name their scenario fiscal fields exactly as the surface does, in the
# same units, so the map is the identity over whichever fields are present.
EU_FISCAL_FIELDS = ("income_tax_delta_m", "benefit_delta_m", "sic_delta_m",
                    "sic_employer_delta_m", "net_income_delta_m", "net_exchequer_cost_m")


def _exch_delta(block, sid):
    """The tool's own exchDelta, in Python: the net exchequer cost of one scenario as a
    change from that country's baseline, in the field the block names."""
    fld = block.get("scenario_fiscal_field")
    fis = (block.get("data") or {}).get("fiscal") or {}
    fs, bs = fis.get(sid), fis.get("baseline")
    if not fld or not fs or not bs or fs.get(fld) is None or bs.get(fld) is None:
        return None
    v = fs[fld] - bs[fld]
    return None if abs(v) < 1e-6 else v


# Every relational claim a scenario statement is allowed to make, as a predicate over the
# two per-euro ratio series. A statement may only assert something this table can decide.
_SPINE_CLAIMS = {
    # "equally efficient at eps=0": the two ratios are equal at the first epsilon.
    "equal_per_unit_at_eps0":
        lambda ra, rb: abs(ra[0] - rb[0]) < 5e-4,
    # "the uplift pulls ahead as epsilon rises": strictly higher at every epsilon above 0.
    "uplift_higher_per_unit_above_eps0":
        lambda ra, rb: all(ra[i] > rb[i] + 5e-4 for i in range(1, len(ra))),
    # the ratio series must be monotone in the direction the prose describes.
    "uplift_ratio_rises_with_eps":
        lambda ra, rb: all(ra[i] >= ra[i - 1] - 1e-9 for i in range(1, len(ra))),
}


def check_scenario_statement(block):
    """The Scenarios tab's statement card, tied to the surface it describes.

    This is the check that was missing. The card carried two hardcoded costs, imv_cost_m
    and irpf_cost_m, with nothing comparing them to the surface; Italy's went 37.3 per
    cent stale across two rebuilds and printed EUR 6.1bn beside a surface that said 4.4bn.
    Worse, the card's prose asserted a relation between two welfare series -- that one
    reform is higher at every epsilon -- and nothing evaluated it. On the rebuilt Italian
    surface it was false at epsilon = 0, and the card's own table printed the refutation
    one line below the sentence.

    So two classes of thing are checked here, and a statement may contain nothing else:

      1. NO STORED FIGURES. imv_cost_m and irpf_cost_m must be absent. The costs are
         computed from exchDelta at render time and substituted into the prose through
         the {{SPINE_*}} tokens, so there is no stored copy left to go stale. A block that
         reintroduces one fails, whatever value it holds.

      2. EVERY RELATIONAL CLAIM HOLDS, AT EVERY EPSILON. The claims a spine statement may
         make are enumerated in _SPINE_CLAIMS and each is re-evaluated against the wevm
         arrays and the exchequer deltas behind them. The claims are keyed off the words
         actually in the statement, so a statement that says something the table cannot
         decide -- "dominance", "no crossover", "cost-matched" -- fails as unverifiable
         rather than passing unexamined. That is deliberate: those three phrases are what
         the superseded text asserted, and the point of this check is that restoring them
         breaks it.

    The UK card is a crossover rather than a spine, and its one claim is a numeric root,
    so it is checked by solving for the root on the two series it names.
    """
    ex = block.get("scenario_extra") or {}
    kind = ex.get("kind")
    if not kind:
        return [], 0
    problems, checked = [], 0
    data = block.get("data") or {}
    wevm = data.get("wevm") or {}
    eps = data.get("epsGrid") or []

    if kind == "spine":
        for stale in ("imv_cost_m", "irpf_cost_m"):
            if stale in ex:
                problems.append(
                    f"scenario_extra.{stale} is stored ({ex[stale]}). Spine costs must be "
                    f"computed from the surface by exchDelta, not held in the block: the "
                    f"stored copy is what went 37.3 per cent stale on Italy.")
        a_id, b_id = ex.get("imv"), ex.get("irpf")
        ca, cb = _exch_delta(block, a_id), _exch_delta(block, b_id)
        wa, wb = wevm.get(a_id), wevm.get(b_id)
        if ca is None or cb is None or not wa or not wb:
            problems.append(
                f"scenario_extra names {a_id!r} and {b_id!r}; the surface does not carry "
                f"a cost or a welfare series for both, so the statement cannot be checked")
            return problems, checked
        ra = [w / ca for w in wa]
        rb = [w / cb for w in wb]
        text = (ex.get("statement") or "")
        low = text.lower()

        # (2a) phrases the surface cannot support, whatever the numbers say.
        for phrase, why in (
                ("cost-matched", "the two costs are not matched and the statement must "
                                 "state them rather than describe them as matched"),
                ("dominance", "a dominance claim compares absolute welfare across reforms "
                              "of different size, which the larger one wins at eps=0 "
                              "whatever its targeting"),
                ("dominates", "same as 'dominance'"),
                ("no crossover", "the absolute series do cross where the costs differ; the "
                                 "per-unit series are what the statement may describe")):
            if phrase in low:
                problems.append(f"scenario_extra.statement says {phrase!r}: {why}")
            checked += 1

        # (2b) the claims it does make, re-evaluated against the arrays.
        if "equally efficient" in low or "equally efficient at" in low:
            checked += 1
            if not _SPINE_CLAIMS["equal_per_unit_at_eps0"](ra, rb):
                problems.append(
                    f"statement claims the two are equally efficient at eps=0, but the "
                    f"surface gives {ra[0]:.4f} against {rb[0]:.4f}")
        if "pulls ahead" in low:
            checked += 1
            if not _SPINE_CLAIMS["uplift_higher_per_unit_above_eps0"](ra, rb):
                bad = [eps[i] for i in range(1, len(ra)) if not ra[i] > rb[i] + 5e-4]
                problems.append(
                    f"statement claims the uplift pulls ahead as eps rises, but per unit "
                    f"of cost it does not at eps={bad}")
            if not _SPINE_CLAIMS["uplift_ratio_rises_with_eps"](ra, rb):
                problems.append(
                    "statement claims the uplift pulls ahead as eps rises, but its own "
                    "per-unit series is not monotone in eps")

        # (2c) every three-decimal figure quoted in the prose must be a real cell of the
        # per-unit table. This is what makes a stale ratio fail rather than merely read oddly.
        #
        # A statement may also reason about a scenario outside the pair -- Greece's names the
        # menu's larger PIT cut to explain why the smaller one is the spine endpoint. Those
        # have to be declared in scenario_extra.extra_series, so that the figures quoted for
        # them are checked against the surface too rather than being unfalsifiable prose.
        allowed = list(ra) + list(rb)
        for extra in (ex.get("extra_series") or []):
            ce = _exch_delta(block, extra)
            we = wevm.get(extra)
            if ce is None or not we:
                problems.append(
                    f"scenario_extra.extra_series names {extra!r}, which the surface does "
                    f"not carry a cost and a welfare series for")
                continue
            allowed += [w / ce for w in we]
        for m in re.finditer(r"(?<![\d.])(\d\.\d{3})(?![\d])", text):
            checked += 1
            v = float(m.group(1))
            if not any(abs(v - r) < 5e-4 for r in allowed):
                problems.append(
                    f"statement quotes the ratio {m.group(1)}, which is not a value the "
                    f"surface produces at any eps for the pair or for anything declared in "
                    f"extra_series "
                    f"(A: {', '.join(f'{r:.3f}' for r in ra)}; "
                    f"B: {', '.join(f'{r:.3f}' for r in rb)})")

    elif kind == "crossover":
        html = ex.get("html") or ""
        m = re.search(r"ε\s*=\s*(\d+(?:\.\d+)?)", html) or \
            re.search(r"&epsilon;\s*=\s*(\d+(?:\.\d+)?)", html)
        if not m:
            problems.append("crossover statement quotes no epsilon to check")
            return problems, checked
        claimed = float(m.group(1))
        pair = ex.get("pair")
        if not pair or len(pair) != 2:
            problems.append(
                "crossover statement names no scenario pair to check it against "
                "(scenario_extra.pair must hold the two scenario ids the sentence names)")
            return problems, checked
        wa, wb = wevm.get(pair[0]), wevm.get(pair[1])
        if not wa or not wb:
            problems.append(f"crossover pair {pair} is not on the surface")
            return problems, checked
        root = None
        for i in range(len(eps) - 1):
            d0, d1 = wa[i] - wb[i], wa[i + 1] - wb[i + 1]
            if (d0 < 0) != (d1 < 0):
                root = eps[i] + (eps[i + 1] - eps[i]) * (-d0) / (d1 - d0)
                break
        checked += 1
        if root is None:
            problems.append(
                f"crossover statement claims the two series cross at eps={claimed}, but "
                f"{pair[0]} and {pair[1]} do not cross anywhere on the eps grid")
        elif abs(root - claimed) > 0.005:
            problems.append(
                f"crossover statement claims eps={claimed}; the surface puts the root at "
                f"{root:.4f} for {pair[0]} against {pair[1]}")
    return problems, checked


def check_scenario_fiscal(block, grid):
    """A scenario's fiscal figures must equal the surface at the point it sits on.

    The Scenarios tab reads data.fiscal; the Analyst tab reads the surface. They are
    two copies of the same quantity and nothing was comparing them, so Spain and
    Greece spent a month reporting a three-term net exchequer cost on one tab and the
    four-term one on the other, and the cost-effectiveness row was overstated by up to
    a factor of two. Both sides are stored as levels or as deltas depending on the
    country, so the comparison is on the delta from that country's own baseline, which
    is what the page displays either way.

    Scenarios with no stored grid point are skipped and counted, not failed: four of
    the UK's fifteen are combinations, or sit at a magnitude the dial does not carry,
    and have nothing to be compared against. Reporting the skip is the point; passing over it silently is how
    a gap becomes invisible."""
    fiscal = dig(block, ("data", "fiscal")) or {}
    baseline = fiscal.get("baseline")
    if not baseline:
        return ["data.fiscal: no baseline entry to take deltas from"], 0, 0
    meta = {s.get("id"): s for s in (block.get("scenarios") or [])}
    dials = grid.get("dials") or {}
    toggles = grid.get("toggles") or {}
    is_uk = "net" in baseline and "allben" in baseline
    problems, compared, skipped = [], 0, 0

    for sid in (dig(block, ("data", "sc15")) or []):
        f = fiscal.get(sid)
        if not f:
            skipped += 1
            continue
        m = meta.get(sid) or {}
        dial, mag, tog = m.get("dial"), m.get("mag"), m.get("toggle")
        point = None
        d = dials.get(dial)
        if d and mag is not None:
            for p in d["points"]:
                if abs(p["magnitude"] - mag) < 1e-9:
                    point = p
                    break
        if point is None and dial in toggles and mag is not None:
            point = toggles[dial].get("on" if mag else "off")
        # A scenario that engages a toggle names it under "toggle", not "dial", so the
        # branch above never fired for the only toggle in the tree and the scenario was
        # counted unmappable while its point sat in grid.toggles all along.
        if point is None and tog and tog in toggles:
            point = toggles[tog].get("on")
        if point is None or not point.get("fiscal"):
            skipped += 1
            continue
        surface = point["fiscal"]
        for key in (UK_FISCAL_MAP if is_uk else
                    {k: (k, 1.0) for k in EU_FISCAL_FIELDS}):
            if key not in f or key not in baseline:
                continue
            field, scale = (UK_FISCAL_MAP if is_uk else
                            {k: (k, 1.0) for k in EU_FISCAL_FIELDS})[key]
            if field not in surface:
                continue
            got = (f[key] - baseline[key]) * scale
            want = surface[field]
            # 0.6m absolute, or 0.2 per cent, whichever is looser: the UK block stores
            # bn to six decimals, so a delta of tens of billions cannot round tighter.
            if abs(got - want) > max(0.6, abs(want) * 2e-3):
                problems.append(f"{sid}.{key}: block delta {got:,.3f} vs surface "
                                f"{field} {want:,.3f}")
            compared += 1
    return problems, compared, skipped


def extract_country(html_path):
    """Parse the embedded COUNTRY object out of a tool page."""
    text = html_path.read_text(encoding="utf-8")
    idx = text.find(MARKER)
    if idx < 0:
        raise ValueError(f"no '{MARKER}' block found in {html_path.name}")
    start = text.find("{", idx)
    if start < 0:
        raise ValueError(f"no object literal after '{MARKER}' in {html_path.name}")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj


def first_differences(a, b, path="grid", limit=5, found=None):
    """Walk two parsed JSON values and collect the first few difference paths.

    `a` is always the copy embedded in the page, `b` the source it was built from.
    """
    if found is None:
        found = []
    if len(found) >= limit:
        return found
    if type(a) is not type(b):
        found.append(f"{path}: type {type(a).__name__} vs {type(b).__name__}")
    elif isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                found.append(f"{path}.{k}: missing from the page")
            elif k not in b:
                found.append(f"{path}.{k}: in the page but not in the source")
            else:
                first_differences(a[k], b[k], f"{path}.{k}", limit, found)
            if len(found) >= limit:
                break
    elif isinstance(a, list):
        if len(a) != len(b):
            found.append(f"{path}: length {len(a)} vs {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                first_differences(x, y, f"{path}[{i}]", limit, found)
                if len(found) >= limit:
                    break
    elif a != b:
        found.append(f"{path}: {a!r} vs {b!r}")
    return found


def dig(obj, path):
    """Follow a key path into a parsed object; None if any step is missing."""
    for key in path:
        if not isinstance(obj, dict) or key not in obj:
            return None
        obj = obj[key]
    return obj


def count_params(obj):
    """Count the scalar numbers below a node, as a size for the report."""
    if isinstance(obj, bool):
        return 0
    if isinstance(obj, (int, float)):
        return 1
    if isinstance(obj, dict):
        return sum(count_params(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(count_params(v) for v in obj)
    return 0


def check_block(embedded, authoring):
    """Compare the whole embedded COUNTRY block against its authoring file.

    Every provider path must be present on both sides (so the provider layer can
    never pass by being absent), and the blocks must then be identical.
    """
    problems, provider_params = [], 0
    for path in PROVIDER_PATHS:
        label = ".".join(path)
        emb, auth = dig(embedded, path), dig(authoring, path)
        if emb is None or auth is None:
            problems.append(f"{label}: missing from "
                            f"{'the page' if emb is None else 'the authoring block'}")
            continue
        provider_params += count_params(emb)
    problems.extend(check_spine_label(embedded))
    problems.extend(check_price_base(embedded))
    problems.extend(check_caveat_length(embedded))
    if embedded != authoring:
        problems.extend(first_differences(embedded, authoring, path="COUNTRY"))
    return problems, provider_params


def main():
    failures = 0
    template_path = MACHINERY / "template.html"
    try:
        template_text = template_path.read_text(encoding="utf-8")
        template_hash = hashlib.sha256(
            normalise_newlines(template_text).encode("utf-8")).hexdigest()
    except OSError as exc:
        print(f"template: ERROR: {exc}")
        return 1
    print(f"template.html: masked-block sha256 {template_hash} "
          f"(line endings normalised)")

    for name, tool, canonical, authoring_path in TOOLS:
        try:
            tool_text = tool.read_text(encoding="utf-8")
            country = extract_country(tool)
            reference = json.loads(canonical.read_text(encoding="utf-8"))
            authoring = json.loads(authoring_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            print(f"{name}: ERROR: {exc}")
            failures += 1
            continue

        if country.get("grid") == reference:
            n_dials = len(reference.get("dials", {}))
            print(f"{name}: PASS: embedded grid identical to canonical "
                  f"({canonical.name}, {n_dials} dials)")
        else:
            failures += 1
            print(f"{name}: FAIL: embedded grid differs from canonical")
            for diff in first_differences(country.get("grid"), reference):
                print(f"  {diff}")

        problems, provider_params = check_block(country, authoring)
        if not problems:
            n_services = len(dig(country, ("data", "services")) or [])
            print(f"{name}: PASS: embedded block identical to authoring "
                  f"({authoring_path.name}; provider layer {n_services} services, "
                  f"{provider_params} numeric parameters)")
        else:
            failures += 1
            print(f"{name}: FAIL: embedded block differs from "
                  f"{authoring_path.name}")
            for p in problems[:5]:
                print(f"  {p}")

        parity = check_template_parity(tool_text, template_text, name)
        if not parity:
            print(f"{name}: PASS: masked block identical to template.html "
                  f"({template_hash[:12]})")
        else:
            failures += 1
            print(f"{name}: FAIL: {parity[0]}")

        scen, compared, skipped = check_scenario_fiscal(country, reference)
        if not scen:
            print(f"{name}: PASS: scenario fiscal matches the surface "
                  f"({compared} field comparisons over the mapped scenarios; "
                  f"{skipped} scenario(s) have no stored grid point)")
        else:
            failures += 1
            print(f"{name}: FAIL: scenario fiscal differs from the surface")
            for p in scen[:5]:
                print(f"  {p}")

        stmt, stmt_checked = check_scenario_statement(country)
        kind = (country.get("scenario_extra") or {}).get("kind") or "none"
        if not stmt:
            print(f"{name}: PASS: scenario statement holds against the surface "
                  f"({kind} card, {stmt_checked} claim(s) re-derived)")
        else:
            failures += 1
            print(f"{name}: FAIL: scenario statement does not hold against the surface")
            for p in stmt[:5]:
                print(f"  {p}")

    print(f"OVERALL: {'PASS' if failures == 0 else 'FAIL'} "
          f"({5 * len(TOOLS) - failures} of {5 * len(TOOLS)} checks clean)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
