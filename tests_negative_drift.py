#!/usr/bin/env python3
"""Negative tests for check_drift.py's data checks.

Same principle as tests_negative_browser.py: break exactly the thing one check
claims to protect, and require that check to FAIL. A check that passes on broken
data is decoration.

These run against in-memory copies of the real blocks and surfaces. Nothing on disk
is touched, and no browser is needed, so this runs anywhere Python does.
"""
import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("cd", ROOT / "check_drift.py")
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)


def load(cc):
    for name, tool, canonical, authoring in cd.TOOLS:
        if name == cc:
            return (json.loads(authoring.read_text(encoding="utf-8")),
                    json.loads(canonical.read_text(encoding="utf-8")))
    raise KeyError(cc)


def scenario_fiscal(block, grid):
    problems, _, _ = cd.check_scenario_fiscal(block, grid)
    return problems


def scenario_statement(block, grid):
    problems, _ = cd.check_scenario_statement(block)
    return problems


# ---- the mutations -------------------------------------------------------------
def m_es_three_term(block, grid):
    """Put Spain's unemployment scenario back on the three-term exchequer cost, the
    exact state the tool shipped in until R1. Cost-effectiveness was overstated x2.02."""
    f = block["data"]["fiscal"]["unemp_3"]
    f["net_exchequer_cost_m"] = round(
        f["benefit_delta_m"] - f["income_tax_delta_m"] - f["sic_delta_m"], 3)
    return block, grid


def m_es_employer_dropped(block, grid):
    """Drop the employer field from one scenario while leaving the headline. The
    headline is then unsupported by its own components, which is how the two tabs
    came to disagree in the first place."""
    del block["data"]["fiscal"]["unemp_5"]["sic_employer_delta_m"]
    block["data"]["fiscal"]["unemp_5"]["net_exchequer_cost_m"] = 8336.948
    return block, grid


def m_uk_income_tax(block, grid):
    """Move the UK's income-tax level for one scenario by a tenth of a billion. The
    UK block stores levels in bn and the surface stores deltas in m, so this is the
    class of error the unit mapping exists to catch."""
    block["data"]["fiscal"]["uc_taper_45"]["it"] += 0.1
    return block, grid


def m_surface_moved(block, grid):
    """Move the SURFACE instead of the block: regenerating a grid without re-embedding
    is the other direction of the same drift, and must be caught from either side."""
    for p in grid["dials"]["min_income_up"]["points"]:
        if p["magnitude"] == 50:
            p["fiscal"]["net_exchequer_cost_m"] += 25.0
    return block, grid


# ---- the mutations the statement check exists for -------------------------------
# Each of these puts one piece of a stale Italian card back, one at a time. Without a
# check tying the statement to the surface, a stale cost and a claim the card's own
# table refutes can both survive a rebuild.
def m_it_stored_cost(block, grid):
    """Reintroduce the stored spine cost, at the value it actually held. It is 37.3 per
    cent above the surface, and before this check nothing compared the two."""
    block["scenario_extra"]["imv_cost_m"] = 5981.263
    return block, grid


def m_it_stored_cost_correct(block, grid):
    """Reintroduce the stored cost at the CORRECT value. This must still fail: the
    defect is that a figure is stored at all, because a correct copy is one rebuild
    away from a stale one. Patching the literal was the fix not taken."""
    block["scenario_extra"]["imv_cost_m"] = 4356.950
    return block, grid


def m_it_dominance_wording(block, grid):
    """Put the dominance claim back into the Italian statement, in its shipped words."""
    block["scenario_extra"]["statement"] = (
        "At broadly comparable exchequer cost (AdI +50% about &euro;5.98bn versus IRPEF "
        "&minus;1pp about &euro;4.93bn, a difference of 21 per cent), the AdI uplift has "
        "the higher welfare effect at every &epsilon; from 0 to 2, and there is no "
        "crossover. Like Spain and Greece, and unlike the UK's crossover, Italy shows "
        "cost-matched dominance.")
    return block, grid


def m_it_stale_ratio(block, grid):
    """Leave the wording sound but let one quoted ratio go stale, from 1.626 to the
    1.64 the card carried before the rebuild. A reader cannot tell; the surface can."""
    block["scenario_extra"]["statement"] = (
        block["scenario_extra"]["statement"].replace("1.626", "1.640"))
    return block, grid


def m_it_pulls_ahead_false(block, grid):
    """Keep the wording and break the arithmetic: swap the two welfare series so the
    'pulls ahead' claim is false at every epsilon while the sentence still asserts it."""
    a, b = block["scenario_extra"]["imv"], block["scenario_extra"]["irpf"]
    w = block["data"]["wevm"]
    w[a], w[b] = w[b], w[a]
    return block, grid


def m_uk_crossover_moved(block, grid):
    """Move the UK's quoted crossover epsilon off the root of its own two series."""
    block["scenario_extra"]["html"] = (
        block["scenario_extra"]["html"].replace("1.62", "1.30"))
    return block, grid


CASES = [
    ("Spain", "scenario_fiscal_matches_surface", m_es_three_term,
     "Spain's unemployment +3pp goes back to the three-term exchequer cost"),
    ("Spain", "scenario_fiscal_matches_surface", m_es_employer_dropped,
     "the employer component is dropped but the headline is left as it was"),
    ("UK", "scenario_fiscal_matches_surface", m_uk_income_tax,
     "the UK's income tax level moves by 0.1bn on one scenario"),
    ("Spain", "scenario_fiscal_matches_surface", m_surface_moved,
     "the surface moves while the block stays put"),
    ("Italy", "scenario_statement_holds", m_it_stored_cost,
     "the stored spine cost comes back, at the 5,981.263 it actually held"),
    ("Italy", "scenario_statement_holds", m_it_stored_cost_correct,
     "the stored spine cost comes back at the CORRECT value, which must still fail"),
    ("Italy", "scenario_statement_holds", m_it_dominance_wording,
     "the shipped dominance wording is restored verbatim"),
    ("Italy", "scenario_statement_holds", m_it_stale_ratio,
     "one quoted per-euro ratio goes stale, 1.626 back to the pre-rebuild 1.64"),
    ("Italy", "scenario_statement_holds", m_it_pulls_ahead_false,
     "the wording stands but the two welfare series are swapped, so it is false"),
    ("UK", "scenario_statement_holds", m_uk_crossover_moved,
     "the UK's quoted crossover epsilon is moved off its own root"),
]

CHECKS = {"scenario_fiscal_matches_surface": scenario_fiscal,
          "scenario_statement_holds": scenario_statement}

allgood = True
print("negative tests for check_drift.py\n")
for cc, target, mutate, why in CASES:
    block, grid = load(cc)
    run = CHECKS[target]
    clean = run(block, grid)
    if clean:
        print(f"[SETUP FAIL] {cc} {target}: the unmutated data already fails: {clean[:2]}")
        allgood = False
        continue
    broken_block, broken_grid = mutate(copy.deepcopy(block), copy.deepcopy(grid))
    problems = run(broken_block, broken_grid)
    caught = bool(problems)
    print(f"{'OK ' if caught else 'BAD'}  {target}  ({cc})")
    print(f"        mutation: {why}")
    if caught:
        print(f"        CAUGHT: {problems[0]}")
    else:
        print("        MISSED -- the check is not load-bearing")
    allgood = allgood and caught

print("\nNEGATIVE TESTS:",
      f"ALL {len(CASES)} MUTATIONS CAUGHT; THE CHECK IS LOAD-BEARING" if allgood
      else "AT LEAST ONE MUTATION WAS MISSED")
sys.exit(0 if allgood else 1)
