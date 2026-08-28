# BENEFITS D2.2 — Methods and Reproducibility Guide

This guide records how the UK deliverable was produced so that anyone **with their own FRS
licence** can reproduce it in principle. **No data is shipped.** We distribute only outputs (the
tool, the published aggregates embedded in it, the paper) and this guide. The FRS licence is
therefore not engaged by the distribution.

## 1. Data and engine
- **Survey:** Family Resources Survey **2023-24** (UK Data Service, licensed; **not** distributed).
- **Tax-benefit engine:** PolicyEngine UK, version **hash-pinned in `requirements.lock`**, run with
  `PE_PERIOD=2023`.
- **Unit of analysis:** each FRS **benefit unit** is modelled as a singleton PolicyEngine household
  (1:1, enforced). `net_income`, `income` and `survey_weight` are therefore all at benefit-unit level.
  Two caveats follow and are stated in the methods, not implied: dwelling-level policies (council-tax
  single-person discount, shared housing) are mis-stated, so council-tax-touching scenarios carry a
  caveat; and the distributional weight is only as good as its income concept, so equivalisation matters.

## 2. Calibration
- **UC take-up = 0.731**, calibrated to the DWP 2023-24 UC expenditure outturn (~£51.2bn, all-BU). The
  PolicyEngine default (0.55) models UC at £37.83bn — the gap is **take-up, not under-reporting** (full
  modelled entitlement ~£69.5bn). UC alone is calibrated; HB / Pension Credit / Child Benefit / tax-credit
  gaps are scope/legacy and left as-is.
- **Scope:** working-age benefit units. Pensioner BUs excluded (a coverage difference, not a model error).

## 3. Canonical anchors (the figures everything downstream uses)
Net (disposable) income **£819.33bn**; working-age UC **£50.10bn** (all-BU **£51.10bn**, the calibration
target); employee NI **£62.42bn**; income tax **£201.29bn**; weighted working-age BU count **21.44m**.
Child poverty (read off the **0.55** diagnostic baseline): AHC **31.67%** / BHC **24.81%**. Each validated
against DWP/HMRC/HBAI in `docs/Validation_Table_D2.2.md`.

## 4. Scenarios (the baseline plus 15)
`baseline`, `shock_3pp`, `shock_5pp`, `gdp_minus_1`, `gdp_minus_3`, `gdp_minus_5`, `uc_taper_45`,
`uc_taper_65`, `uc_work_allowance_up_20`, `uc_standard_up_10`, `uc_standard_down_10`,
`raise_personal_allowance`, `cb_remove_hicbc`, `cb_increase_10pct`, `gdp_minus_3_plus_uc_boost`,
`gdp_minus_3_plus_tax_cut`.

## 5. WEVM (Weighted Equivalent-Variation Measure)
- Per-unit EV = Δ net income vs baseline (the **quasilinear** approximation appropriate for cash reforms).
- Living standard = OECD-modified **equivalised** baseline income; reference `y_ref` = weighted **median**.
- Social weight (Atkinson): `κ(y;ε) = (max(y, floor)/y_ref)^(−ε)`, with the **AROP floor** = 60% of the
  median (Eurostat at-risk-of-poverty / UK HBAI relative low-income line), bounding κ ≤ (0.6)^(−ε).
- ε grid {0, 0.5, 1, 1.5, 2}. Headline at ε=1. Ranking reorders with ε; `gdp_minus_3_plus_uc_boost`
  overtakes `raise_personal_allowance` at **ε = 1.62** (dense [1.5,2.0] grid). Module: `wevm/wevm.py`.

## 6. Provider value-added (Green Book + WELLBY)
- WELLBY spine **£13,000 at 2019 prices** (HMT *Wellbeing Guidance for Appraisal* 2021), applied at 2024
  prices as **£16,300** by the guidance footnote-102 method (GDP deflator × real-GDP-per-capita growth^1.3).
- Each outcome valued by exactly one route: **ENGINE** (microsim income, excluded from the outcomes sum),
  **CONVENTIONAL** (published unit value × GDP deflator), **WELLBY** (WELLBYs × spine), **COST-INPUT**,
  **UNEVIDENCED-EXCLUDED**. **WELLBYs carry weight 1**; only ENGINE income and CONVENTIONAL outcomes are
  WEVM-weighted. Attribution-adjusted; banded low/central/high. This is a **benefit-transfer** of published
  effect sizes onto described caseloads. Evidence base: `DATA_OUTCOMES`; citations: `DATA_SOURCES`.

## 7. Build steps
`run_pipeline.sh` orchestrates `model/Code_FRS_23_24/`: `02_build_benefit_unit_table` →
`03_build_policyengine_dataset` → `04_run_frs_baseline` → `05_run_frs_reforms` → `06_run_frs_shocks` →
`07_run_frs_combined_scenarios` → scenario aggregates. The WEVM layer consumes the per-unit export
(`wevm/wevm.py`). The tool's `DATA_` layer carries the resulting **aggregates as values**; the analyst
and provider views and the HTML edition read only from that layer (no live engine call).

## 8. Reproduction-in-principle
With an FRS 2023-24 licence and the pinned environment (`requirements.lock`), run the pipeline above to
regenerate the canonical aggregates, then the WEVM layer, then the tool. The committed validation table
and this guide define the targets. Intermediate FRS-derived data files are **git-ignored and not
distributed**.

## 9. Level 2 dial tool (continuous magnitude response surface)
The fixed scenario tool (Section 4) is complemented by a **Level 2 dial edition**
(`uk/tools/dial_tool_uk.html`) that lets the user vary each reform family **continuously** across its modelled
range and read the welfare response, rather than choosing from fixed magnitudes. It reads a pre-computed
surface and **does not run the engine live**.

- **Surface build.** `model/Code_FRS_23_24/09_build_dial_grid.py` drives the existing reform modifiers
  (`utils/frs_reforms.py`) and the seeded shock mechanism (matching step 06, `SEED=42`) across **eleven-
  point magnitude grids**, runs every calibrated point through the WEVM layer, and writes
  `outputs/frs_2023_24/dial_grid.json` (git-ignored; aggregate WEVM + decile contributions +
  winners/losers per point only — **no microdata**). Every point shares the canonical UC take-up
  calibration (0.731), so the surface is consistent with the shipped baseline.
- **Seven dials + one toggle.** Minimum income / UC standard allowance (0 → +50%); Child Benefit rate
  (0 → +50%); personal allowance (−20% → +20% of £12,570, two-directional); GDP shock (−10% → 0%, routed
  through the GDP→unemployment transmission); unemployment shock (0 → +10pp); UC taper (45% → 65%,
  baseline 55%); UC work allowance (0 → +50%). **HICBC removal is a binary toggle**, not a slider. The
  baseline is the zero point of each dial.
- **Single-reform only.** Exactly one lever moves per grid point, and the interface enforces one active
  control at a time (moving any control resets the others to baseline). Combinations are **out of
  scope**: single-reform grids cannot represent interacting reforms, so the two shipped combination
  scenarios (`gdp_minus_3_plus_uc_boost`, `gdp_minus_3_plus_tax_cut`) are deliberately excluded.
- **Full ε dimension.** Each point stores the WEVM and decile contributions at **every ε on the grid
  {0, 0.5, 1, 1.5, 2}**, so ε is exposed as a live control: the welfare verdict updates as the user
  reweights the distribution. A bottom-targeted dial (minimum income) grows with ε; a top-of-distribution
  change (HICBC removal) shrinks with ε.
- **Interpolation.** The interface reads only the surface and **interpolates linearly** between the 11
  stored points. Interpolation error is negligible where checkable: at the personal-allowance point
  coinciding with the shipped raise-to-£15,000 reform (≈ +19.3%) the interpolated WEVM matches the
  directly-computed scenario to £1m (0.01%).
- **Validation.** The surface reproduces the shipped baseline anchor exactly (£819.33bn over 13,372
  working-age units, take-up 0.731), every dial zero-point is exactly 0, and every grid point coinciding
  with one of the scenarios reproduces its WEVM **across the whole ε grid** to ≤ £0.0005m (the 3-dp
  JSON rounding). The interface logic is country-agnostic — all labels, ranges, units and the ε grid come
  from the grid layer — so an EU grid layer loads into the same code unchanged.
- **Readability layer.** Each dial carries a plain-language note giving its baseline in real terms and
  what the percentage changes (for example the UC standard allowance, about £368.74 a month for a single
  adult aged 25 or over in 2023-24); AROP, the WEVM and ε are defined at the point they appear, not only
  in this guide. The personal-allowance dial is framed as the income-tax threshold (£12,570), with a
  higher allowance shown as less tax paid, that is a tax cut and so a welfare gain. The surface sign
  already encodes this (a positive magnitude gives a positive WEVM, about 73% winners and no losers), so
  the relabelling is presentational, not a re-computation. The plain-language strings sit in a single
  `DIAL_TEXT` block that an EU edition swaps, exactly as it swaps GRID.
- **Provider mode (dial edition).** The provider view scales the unemployment-shock demand by the
  provider's own catchment: additional demand = the service demand elasticity × the provider's people
  served × the national affected fraction, in cases per year. That fraction is the share of modelled UNITS that lose an earner, taken from the surface's own `units_k`, not a share of people: the shock zeroes one earner per selected benefit unit, so `aff` is a unit-scale count. It is compared like-for-like against a
  capacity built as caseworkers × cases each handles per year, with total projected demand = people
  served + additional, driving the RAG status. The extra caseworkers needed to close the gap are
  computed from that same cases-per-caseworker figure, the provider's own, and NOT from the
  registry `staff_ratio`; the registry states no unit for that field and no formula now reads it. The shock is no longer clamped to [3, 5]pp: 0pp gives no
  effect, 3pp and 5pp are the directly modelled points, and values above 5pp are linearly extrapolated.
  The fixed-scenario edition's provider view is unchanged; that edition has since been folded
  into the Scenarios tab of the consolidated tool and its standalone file withdrawn to
  `uk/tools/_superseded/valuation_tool.html`.
  a formula-only (no-macro) workbook that embeds the same surface and provider aggregates and reproduces
  the HTML's arithmetic in Excel formulas, so the two editions are lockstep. The analyst interpolation is
  an `INDEX`/`MATCH` bracket-and-blend over the embedded grid; single-reform is enforced by layout (one
  active control feeds the result). Verified by recalculating the workbook in LibreOffice headless and
  matching the HTML at sampled dial/epsilon points and the provider defaults to the displayed precision.
