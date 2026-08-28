# UC take-up calibration — finding and welfare effect

Documentation of the Universal Credit take-up calibration adopted for the canonical
FRS 2023-24 baseline. Aggregates only.

## 1. The finding: under-capture was take-up, not under-reporting
At the PolicyEngine UK default take-up rate (**0.55**), modelled baseline UC is **£37.83bn**,
against the DWP 2023-24 UC expenditure outturn of **~£51.2bn** — a £13.4bn shortfall that
V1 initially attributed to FRS benefit under-reporting. A take-up diagnostic showed
otherwise:

| Quantity | Value |
|---|---|
| UC received (modelled, take-up 0.55) | £37.83bn |
| UC full entitlement (take-up forced to 1.0) | £69.52bn |
| UC reported (FRS — unpopulated; dataset is entitlement-based) | £0.00bn |
| DWP UC outturn 2023-24 | ~£51.2bn |

Full modelled **entitlement (£69.52bn) exceeds the outturn**, so there is **no input
under-capture**: the model holds ample UC entitlement from the FRS inputs. The whole gap
is the take-up rate — the 0.55 default understates the ~0.73 take-up implied by actual UC
expenditure. PolicyEngine UK exposes take-up as the parameter
`gov.dwp.universal_credit.takeup_rate` and the `would_claim_uc` variable
(`random() < takeup_rate`), so it is directly correctable.

## 2. The calibration (canonical)
`takeup_rate` is set to **0.731**, the value that aligns modelled baseline UC to the
outturn: realised baseline UC = **£51.10bn** (all-BU), residual **−£0.10bn**. This is set in
`code/Code_FRS_23_24/utils/frs_reforms.py` (`CANONICAL_UC_TAKEUP_RATE`) and applied by
step 07 to the baseline **and every scenario**, so the whole grid shares one calibrated
take-up assumption (and a re-run reproduces the canonical export).

**Only UC is calibrated.** HB, Pension Credit, Child Benefit and tax-credit gaps are
scope/legacy -- pensioner coverage, UC migration, working-age scope -- not take-up, and
are left at their PolicyEngine defaults.

Net effect on the baseline: net income (working-age) £807.18bn → **£819.33bn**; all-benefits
£73.15bn → £85.30bn; NI, income tax and the BU count are unchanged.

## 3. Welfare effect (the point)
On the calibrated baseline, the **UC scenarios' WEVM rise in magnitude by ~33–77%** — more
entitled units now claim, so the reform's equivalent variation registers for them
(e.g. `uc_taper_45` ε=1 £4,151m → £5,585m, +34%; `gdp_minus_3_plus_uc_boost` £3,184m →
£5,645m, +77%).

**The ε=1 scenario ranking changes** (rank-ρ = 0.979 vs the 0.55 headline; three local
swaps). The headline #1 (`raise_personal_allowance`) is stable, but
**`gdp_minus_3_plus_uc_boost` rises from 4th to 2nd** — the COVID-style UC response now
reaches the calibrated claimant base. The canonical ε=1 order:
`raise_personal_allowance > gdp_minus_3_plus_uc_boost > uc_taper_45 > gdp_minus_3_plus_tax_cut > uc_standard_up_10 > …`
(full grid: [`wevm_headline_2023_24.csv`](wevm_headline_2023_24.csv); deciles:
[`wevm_deciles_2023_24.csv`](wevm_deciles_2023_24.csv)).

### Automatic-stabiliser effect
Calibrated UC cushions the GDP/unemployment-shock scenarios: with more claimants, the
income loss is partly offset by UC, so the welfare **losses are ~5% smaller** (e.g.
`shock_5pp` ε=1 −£15,636m → −£14,770m). This is the mechanism behind the
`uc_taper_65` / `gdp_minus_3` swap (ranks 11↔12): the GDP-shock loss is cushioned while the
UC-cut scenario's loss deepens with more claimants. The CB scenarios are unaffected (CB is
disregarded in UC); `raise_personal_allowance` moves only −1% (UC partly claws back the PA
gain).

## 4. Child-poverty trade-off (a documented limitation)
The uniform calibration matches the UC **expenditure** aggregate but **not** the poverty
distribution: paying more UC to entitled families lifts children over the line, so on the
calibrated baseline child poverty falls to AHC **28.07%** / BHC 21.33% — ~8% *below* HBAI
(30.52% / 23.19%), having been ~+4–7% *above* at 0.55 (31.67% / 24.81%). The V1 poverty
diagnostic is therefore read off the **uncalibrated 0.55 baseline**. A uniform take-up rate
cannot simultaneously match the UC expenditure aggregate and the poverty rate — see the
limitations ledger (README §9). This demonstrates that **take-up heterogeneity is
welfare-relevant**; targeted (household-type-conditional) take-up is a v2 refinement.

## 5. Sensitivity — 0.55 vs 0.731 (retained, not discarded)
The headline is reported under both take-up assumptions so the effect of the take-up
assumption is visible (exactly as the floor sweep does for the AROP floor):
[`wevm_takeup_sensitivity_eps1.csv`](wevm_takeup_sensitivity_eps1.csv).
**0.55** is the PolicyEngine default; **0.731** is the outturn-calibrated value and is
**canonical because it matches administrative reality** (the £51.2bn UC outturn). The
ε=1 ranking is stable in broad shape across the two (rank-ρ 0.979), with the local swaps
above.
