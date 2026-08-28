# BENEFITS D2.2 — Baseline Validation Table (FRS 2023-24)

Validation of the canonical baseline (PolicyEngine UK on FRS 2023-24, working-age
benefit units) against published DWP, HMRC and HBAI sources. **Aggregates only; no FRS
microdata.** This is the D2.2 `Validation_Table` referenced by the README and PLAN.

**Two baselines are reported, marked per line.** The **fiscal and welfare (WEVM)** lines
use the canonical **take-up-calibrated baseline** (`takeup_rate = 0.731`, aligned to the
DWP UC expenditure outturn). The **child-poverty** lines are read off the **uncalibrated
0.55 baseline**, because the uniform take-up calibration matches the UC *expenditure*
aggregate but its stochastic claimant placement distorts the *poverty rate*, so the
poverty diagnostic is taken from the uncalibrated distribution (see the trade-off note
below and the limitations ledger).

**Tolerance:** ±0.4% for the HMRC NI anchor; ±1% for the population count; ±2pp / ±5%
for child poverty on a matching definition. Working-age-scoped aggregates compared with
UK totals are marked **SCOPE** — the gap is coverage, not model error.

| # | Line (scope) | Baseline | Model | Benchmark | Source | % diff | Status |
|---|---|---|---|---|---|---|---|
| 1 | Employee NI (working-age) | 0.731 | **£62.42bn** | £62.2bn | HMRC NIC receipts 2023-24 | +0.35% | **PASS** |
| 2 | Universal Credit (all-BU) | 0.731 | **£51.10bn** | £51.2bn | DWP/OBR UC outturn 2023-24 | −0.20% | **PASS** — take-up calibrated to outturn (0.731) |
| 3 | Income tax (working-age) | 0.731 | £201.29bn | £273.3bn (UK total) | HMRC receipts 2023-24 | −26.3% | SCOPE — pensioner income tax excluded |
| 4 | All-benefits aggregate (working-age) | 0.731 | £85.30bn | per-benefit (see note) | DWP/OBR + HMRC 2023-24 | — | UC calibrated; HB/PC/CB/tax-credit gaps are scope/legacy, **not** calibrated |
| 5 | Net (disposable) income (working-age) | 0.731 | **£819.33bn** | — | (no like-for-like total) | — | **canonical** — reported, not benchmarked: no published working-age total exists to compare it against |
| 6 | Weighted working-age BU count | 0.731 | 21.44m | ~21.5m | DWP working-age population | −0.3% | **PASS** |
| 7 | Child poverty — relative, AHC, child-level | **0.55** | **31.67%** | 30.52% | DWP HBAI 2023/24, Table 4.5db | +1.15pp (+3.8%) | **PASS** (diagnostic baseline) |
| 8 | Child poverty — relative, BHC, child-level | **0.55** | 24.81% | 23.19% | DWP HBAI 2023/24, Table 4.5db | +1.62pp (+7.0%) | **PASS** (diagnostic baseline) |

Context (not benchmarked): unweighted sample = 13,372 working-age BUs; employee NI unchanged across the calibration (take-up does not affect NI).

**UC basis (stated so neither figure is misquoted).** Line 2 is **all-BU** — the £51.2bn DWP outturn it is benchmarked against is all-BU. The **working-age** UC aggregate carried in the tool's data layer (DATA_SCENARIOS, consistent with every other working-age line here) is **£50.10bn**. The £1.0bn difference is pensioner-BU UC. The calibration target (all-BU £51.10bn ≈ £51.2bn outturn) is met; the tool reports working-age £50.10bn.

## Note on the UC line (corrected framing)
The UC under-capture at the PolicyEngine default take-up (0.55, modelled **£37.83bn**) is
**take-up, not FRS under-reporting** — the earlier "under-reporting" framing was incorrect
for UC. Full modelled UC **entitlement is ~£69.5bn** (above the £51.2bn outturn), so there
is no input under-capture; the 0.55 default simply understates take-up. Calibrating
`gov.dwp.universal_credit.takeup_rate` to **0.731** aligns modelled baseline UC to the
outturn (£51.10bn, residual −£0.10bn). HB / Pension Credit / Child Benefit / tax-credit
gaps remain **scope/legacy** and are **not** calibrated. See
[`uc_takeup_calibration.md`](uc_takeup_calibration.md).

## Child-poverty: the calibration trade-off (transparent)
The calibrated (0.731) baseline pays more UC to entitled low-income families, lifting some
children over the line, so on the **fiscal baseline** child poverty falls to **AHC 28.07% /
BHC 21.33%** — now ~8% *below* HBAI. The reported diagnostic (above) therefore uses the
**0.55 baseline** (AHC 31.67% / BHC 24.81%), which is ~+4–7% of HBAI and is the
distributionally-truer poverty estimate. Both figures are kept visible so the trade-off
is explicit:

| Definition | 0.55 (reported diagnostic) | 0.731 (fiscal baseline) | HBAI 2023/24 |
|---|---|---|---|
| Child poverty, rel. AHC, child-level | **31.67%** (+3.8%) | 28.07% (−8.0%) | 30.52% |
| Child poverty, rel. BHC, child-level | **24.81%** (+7.0%) | 21.33% (−8.0%) | 23.19% |

## Child-poverty: definitional resolution
The Excel's "0.24 vs 0.29" was a **BHC-vs-AHC definitional mismatch**, not a discrepancy:
0.24 = the engine's relative child poverty **BHC**; 0.29 ≈ the HBAI **AHC** headline (actual
30.52%). On matching definitions the engine agrees with HBAI within ~1–2pp.

## Standing caveats
1. **Take-up calibration is a uniform, aggregate-calibrated rate.** It aligns the *total*
   modelled UC to the outturn; the distributional placement of the newly-modelled claimants
   is stochastic (PolicyEngine's `would_claim_uc` random draw), not targeted to specific
   household types — which is why the poverty diagnostic is read off the uncalibrated
   baseline. The aggregate and the ε-weighted welfare totals are calibrated; individual
   claimant identity is not.
2. **Child-denominator definitional difference.** The engine's child population (13.51m) is
   below HBAI's dependent-child count (14.59m), which may account for part of the residual
   child-poverty gap; the rates are nonetheless close on matching definitions.
