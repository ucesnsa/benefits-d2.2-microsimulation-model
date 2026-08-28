# EU fiscal re-emit — reproducible provenance

BENEFITS D2.2. The EU response surfaces `europe/<Country>/outputs/dial_grid.json` (ES, EL, IT) carry a per-grid-point `fiscal` sub-object (tax/benefit/SIC/net-income/net-exchequer deltas, EUR millions, 2023 nominal). This document makes that re-emit's provenance **reproducible from the folder**.

The byte-preservation signatures and the validator result are written to disk by the verifier rather than carried as narrative, and the only script referencing the fiscal fields was the retired `europe/Spain/tools/_superseded/generate_es_tools.py`. Both are now resolved:

- **Producer/verifier script (committed, non-superseded):** [`europe/common/re_emit.py`](../common/re_emit.py).
- **Saved proof (per country):** `europe/<Country>/outputs/reemit_proof.json` and `europe/<Country>/outputs/reemit_validate_grid.log`.

## Reproduce from the folder (no engine, no microdata)

**`py -3` is the Windows Python launcher.** On macOS and Linux run the same commands with
`python3` in its place.

```
cd europe/common
py -3 re_emit.py verify            # ES, EL, IT
```

This reads only the committed aggregate surfaces and proves: the non-fiscal fields hash to a fixed signature; the exchequer identity `net_exchequer_cost_m = benefit_delta_m − income_tax_delta_m − sic_delta_m − sic_employer_delta_m` holds at every point; the three fiscal checks pass; the analytic min-income fiscal is exactly linear in magnitude (EL/ES); and `validate_grid.py` passes.

## Reproduced results

This table carries the byte-preservation signatures. A signature is a property of the surface it
was taken from, so it must be read from the shipped surface rather than copied forward: the
figures below come from a verifier run on the surfaces this build ships, and re-running the
verifier is the only way to confirm them.

| Country | Non-fiscal sha256 | Exchequer identity (max residual) | Three checks | Min-income | validate_grid |
|---|---|---|---|---|---|
| **ES** | `d798695e…d65883` | holds (0.000, worst at gdp_shock −10%) | all pass | analytic; constant outlay **€2,479.25m** | PASS (5/1 warn/0) |
| **EL** | `312620ce…99702a` | holds (0.000, worst at gdp_shock −6%) | all pass | analytic; constant outlay **€495.73m** | PASS (5/1 warn/0) |
| **IT** | `c4e774a0…b23683` | holds (0.000, worst at gdp_shock −8%) | all pass | engine base-scaling (n/a) | PASS (5/1 warn/0) |

**The one WARN, named in full.** It is the same warning in all three countries and it is
check 1, Structure. That check carries three lines, and all three are named here:

1. `meta: no take-up key (any of ('uc_takeup_rate', 'takeup_rate', 'takeup')); acceptable if the
   country has no take-up concept` — none of ES, IT or EL has a modelled take-up rate, that being
   a UK Universal Credit concept, so there is no key to carry.
2. `dial 'pit_give': 21 points (the UK design is 11)` — deliberate, and it is the one documented
   exception to the eleven-point grid: the European first-bracket personal-income-tax dial is
   two-sided, from a 5pp cut to a 5pp rise, so both directions are computed rather than
   interpolated through zero. Recorded in `FOUNDATION.md` §3a and on the tool face.
3. `toggles: none present (acceptable only if this country defines no binary toggle)` — the UK's
   binary toggle has no European counterpart, so the EU grids define none.

All three are the EU design behaving as specified, and each is the exact condition the check
itself says is acceptable. The correct reading is that no European surface produces an
unexplained warning, not that a warning is being tolerated.

The two min-income outlays are properties of the surface and must be re-read rather than recalled.
The Spanish figure is **€2,479.25m** and the Greek **€495.73m**, each the outlay the shipped
surface implies and the one this table carries. The ES non-fiscal signature is read here from
`europe/Spain/outputs/reemit_proof.json`; the EL and IT signatures
were current and are unchanged.

The exchequer identity itself gained a fourth term when employer contributions were folded into
the EU exchequer basis on 2026-08-01, and the sentence above now states the identity the verifier
actually checks rather than the three-term one it checked in July.

**The three fiscal checks** (verified as live data facts across all 65 points of each country):
1. Min-income levers carry **zero income-tax delta and zero SIC delta** (pure transfers).
2. Pure PIT reforms have **SIC = 0**; earnings-downturn and unemployment have **SIC < 0**.
3. Benefit-only levers (child benefit, min-income) carry **zero income-tax delta**.

## Regenerating the fiscal values themselves (engine + EU-SILC data)

The `verify` pass above proves internal consistency and non-fiscal preservation from the folder alone. Regenerating the fiscal **values** requires re-running the reforms through the model:

```
py -3 re_emit.py produce EL        # needs the matched EUROMOD v3.8.6 engine + the EU-SILC data
```

Method: weighted per-household fiscal aggregates from the EUROMOD outputs (`ils_tax` / `ils_ben` / `ils_sicdy` / `ils_dispy`), summed per household ×12 × survey weight, differenced against baseline; EL/ES min-income is an analytic recipient top-up (m% × baseline recipient outlay; tax=0, sic=0), IT min-income is engine base-scaling. `produce` stages a `dial_grid.regenerated.json` beside the canonical surface and re-asserts the non-fiscal signature; it never overwrites the canonical surface without a human copy step. The engine and the EU-SILC data are external to this data-free tree (as the whole EU build is), so `produce` is not folder-only — but its output reproduces the committed fiscal values, and the folder-only `verify` proof stands as the portable provenance.
