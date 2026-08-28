# BENEFITS D2.2 — Microsimulation Valuation Tool: Technical Report

**Building Economic, Needs-Based and Environmental evaluation Frameworks for Inclusive Transformation of Social services in Europe (BENEFITS)**
Horizon Europe grant agreement no. 101179032 · Work Package 2 · Deliverable D2.2

This report documents the methodology of the D2.2 Microsimulation Valuation Tool — the beta of the BENEFITS Holistic Valuation Framework — and grounds every methodological decision in its justification and source. It is the reference document for the model, the welfare layer, and the provider valuation that the tool implements. The companion user guide (`Documents/USER_GUIDE_UK_D2_2.pdf`) covers operation; `METHODS.md` summarises reproduction; this report is the substantive defence of the numbers.

---

## 1. What the tool is

A static, per-unit tax–benefit microsimulation of the United Kingdom on Family Resources Survey (FRS) 2023-24 microdata, run through PolicyEngine UK, with two layers built on top:

1. a **welfare layer** (the Weighted Equivalent-Variation Measure, WEVM) that converts the distributional impact of a reform or shock into a single, distributionally-weighted monetary figure; and
2. a **provider valuation layer** that estimates the evidence-based social value-added of a social-service caseload using HM Treasury Green Book and WELLBY methods.

The tool ships as two editions — an Excel workbook and a self-contained HTML page — that read the same canonical aggregates and present identical figures. It is a **beta**: the United Kingdom is the live model (single survey wave, FRS 2023-24); the European generalisation is documented and is engine-agnostic by construction (the per-unit export schema is shared with EUROMOD), but is not instantiated here.

## 2. Data, engine, and reproduction-in-principle

- **Microdata.** FRS 2023-24 (UK Data Service, end-user-licensed). The survey is **not** distributed with this deliverable.
- **Engine.** PolicyEngine UK, pinned in `requirements.lock` (policyengine-uk 2.45.4, policyengine-core 3.23.6). The policy basis is the 2023-24 system (`PE_PERIOD = 2023`).
- **Unit of analysis.** Each FRS benefit unit is modelled as a singleton PolicyEngine household (1:1, enforced in the build), so disposable income, market income and survey weight are mutually coherent at benefit-unit level. Two consequences are stated as limitations, not implied: policies whose incidence runs through the dwelling rather than the claim (council-tax single-person discount, shared housing) are mis-stated and carry a caveat; and the distributional weight is only as good as its income concept, which is why equivalisation matters (Section 5).
- **What ships.** Only outputs: the tool, the published aggregates embedded in it, the WEVM result tables (`docs/wevm_*.csv`), and this documentation. No FRS-derived microdata is committed; intermediate FRS-derived files are excluded from the repository; a small synthetic fixture is provided for continuous-integration testing of the pipeline.
- **Reproduction-in-principle.** A licensed holder of FRS 2023-24 can reproduce every figure: place the FRS extracts in `inputs/`, install the pinned environment, and run the pipeline in order (`02 → 03 → 04 → 05 → 06 → 07`). The committed code with the pinned dependencies reproduces the canonical anchors to the penny, the WEVM headline, the ε = 1.62 crossover, and the full WEVM grid that the tool embeds (verified on a clean end-to-end run).

## 3. Baseline calibration: Universal Credit take-up

**Decision.** The canonical baseline sets the Universal Credit take-up rate to **0.731** (`gov.dwp.universal_credit.takeup_rate`).

**Justification.** At PolicyEngine's default take-up (0.55), modelled UC is £37.83bn against a DWP/OBR outturn of ~£51.2bn. The gap is **take-up, not under-reporting**: full modelled entitlement is ~£69.5bn, so the population is eligible but not all claim. Setting take-up to 0.731 aligns modelled baseline UC to the outturn (£51.10bn all-benefit-unit). Calibrating one parameter to one published aggregate is the minimal, defensible adjustment; no other benefit is calibrated.

**The automatic-stabiliser finding.** Calibrated UC is more responsive to downturns. Under the modelled GDP and unemployment-shock scenarios, welfare losses are roughly 5% smaller on the calibrated baseline than at default take-up (for example, the +5pp unemployment shock moves from −£15,636m to −£14,770m at ε = 1). Calibrating the safety net to its real reach therefore strengthens its measured role as an automatic stabiliser — a substantive result, not an artefact of the adjustment.

**Trade-off, stated openly.** A single uniform take-up rate matches the UC expenditure aggregate but cannot simultaneously match the poverty distribution (the placement of modelled claimants is stochastic, not observed). Child poverty on the calibrated baseline runs ~8% below the HBAI headline. The poverty diagnostic is therefore read off the uncalibrated (0.55) baseline, kept alongside for visibility. The fiscal headline and the welfare layer use the calibrated baseline; the poverty diagnostic uses the uncalibrated one. Both are reported so neither is misquoted.

## 4. Canonical anchors and dual-baseline reporting

The baseline is validated against published sources (DWP, HMRC, HBAI) within documented tolerances. The canonical anchors, on the take-up-calibrated FRS 2023-24 run, working-age scope:

| Quantity | Value | Benchmark |
|---|---|---|
| Disposable income (working-age) | **£819.33bn** | HBAI-consistent |
| Universal Credit (all benefit units) | **£51.10bn** | DWP/OBR outturn ~£51.2bn |
| Universal Credit (working-age, the tool basis) | **£50.10bn** | all-BU minus £1.0bn pensioner UC |
| Employee National Insurance | **£62.42bn** | HMRC NIC 2023-24 £62.2bn (+0.35%) |
| Income tax (working-age) | **£201.29bn** | HMRC, scoped |
| Weighted working-age benefit units | **21.44m** | population control |

**Dual-basis UC.** Universal Credit is stated on two bases because the tool is working-age-scoped while the DWP outturn is all-benefit-unit. The all-BU figure (£51.10bn) is the calibration target; the working-age figure (£50.10bn) is what the tool's data layer uses throughout; the £1.0bn difference is pensioner-benefit-unit UC. Both appear so the figure is not misquoted in either direction.

**Working-age scope.** Pensioners are excluded, so income-tax and benefit aggregates are working-age-scoped against UK totals — a coverage difference, recorded as such, not a model error.

## 5. The welfare layer: WEVM

**What it measures.** For every reform or shock scenario, the per-unit equivalent variation is the change in disposable income, EV_i = net_income_i(scenario) − net_income_i(baseline) — the quasilinear approximation appropriate to cash reforms. The WEVM is the distributionally-weighted sum of these EVs.

**The distributional weight.** A normalised Atkinson (iso-elastic) social marginal value of income:

  κ(y; ε) = ( max(y, floor) / y_ref )^(−ε)

- **Living standard `y`** is equivalised baseline disposable income on the OECD-modified scale (first adult 1.0, each further adult 0.5, each child 0.3), using the benefit unit's adult and child counts.
- **Reference `y_ref`** is the **weighted median** equivalised living standard — the Green Book convention anchors the weight to one at the median, not the mean. κ is therefore normalised to 1 at the median and the result stays in money terms.
- **Inequality aversion ε** runs over the grid {0, 0.5, 1, 1.5, 2}. ε = 0 is the utilitarian case (κ ≡ 1, and the WEVM reduces exactly to the weighted EV sum, which is the headline validation checksum); ε = 1 is the conventional central value; ε = 2 is strong aversion.

**The AROP floor.** The living standard is floored at **60% of the weighted-median equivalised income** — the Eurostat at-risk-of-poverty / UK HBAI relative low-income line — before the power is taken. This bounds the maximum weight to (0.6)^(−ε) (about 2.78 at ε = 2). The floor is the project's own documented choice, motivated empirically: an earlier weighted-first-percentile floor collapsed to ~£1 on real FRS, where ~4.5% of units have zero or negative baseline income, so those units received near-unbounded weight and dominated the ε ≥ 1 aggregate. The AROP anchor is the standard EU/UK low-income line and removes that pathology; headline scenario rankings are stable across alternative floors (5th and 10th weighted percentiles; 50% and 60% of median), which is reported as a sensitivity.

**Headline figures and the crossover.** At ε = 1, raising the income-tax personal allowance returns a WEVM of £9,177.58m and the GDP-downturn-with-UC-uplift response returns £5,644.8m. As ε rises the ranking reorders, because the UC-uplift response is more progressive: at **ε = 1.62** the two cross, and above it the UC-uplift response is the highest-welfare scenario. The crossover is located on a dense ε sub-grid. A decile decomposition is provided and sums exactly to the WEVM at every ε (zero residual), so the headline can always be read as the sum of its distributional parts.

## 6. The provider valuation layer

**Purpose.** To estimate the evidence-based social value-added of a described social-service caseload, with the distributional weight from the welfare layer applied consistently.

**Method — Green Book plus WELLBY.** Each outcome is valued by exactly one route, to avoid double-counting:

- **ENGINE** — microsimulation income effects (already in the welfare layer; excluded from the outcomes sum).
- **CONVENTIONAL** — a published unit value uprated to 2024 by the GDP deflator.
- **WELLBY** — wellbeing-years valued at the WELLBY spine.
- **COST-INPUT** — a recorded cost with no value-added claim (contributes £0 to value).
- **UNEVIDENCED-EXCLUDED** — an outcome with no defensible published effect size is **excluded** from the headline, not assigned a speculative value. This is the evidence threshold: a figure is either sourced or it does not enter the headline.

**The WELLBY spine.** The spine is £13,000 per WELLBY at 2019 prices, the value recommended in the HM Treasury *Wellbeing Guidance for Appraisal*. It is applied at 2024 prices as £16,300, uprated by the guidance's footnote-102 method (GDP deflator × real-GDP-per-capita growth raised to the power 1.3).

**Weighting.** WELLBYs are valued at **weight 1** — wellbeing-years are not distributionally re-weighted, because the WELLBY value already embeds a population-average willingness-to-pay and re-weighting it would conflate two value judgements. Only ENGINE income and CONVENTIONAL outcomes are WEVM-weighted. The headline is the cash-equivalent floor (engine income, WEVM-weighted) plus CONVENTIONAL outcomes (WEVM-weighted) plus WELLBY outcomes (weight 1).

**Benefit-transfer, stated plainly.** Provider value-added is a **benefit-transfer**: published effect sizes are applied to a described caseload, not measured on the provider's own clients. Every figure carries a confidence tier (STRONG / MODERATE / WEAK) and a low / central / high band that must travel with any quoted figure. The bands are genuine uncertainty, not decoration, and should be carried forward — the lower bound is the conservative claim.

**Cost-effectiveness.** Two cost-effectiveness readings are exposed: in analyst mode, welfare per £bn of exchequer cost (welfare expansions ranked, with savings measures labelled separately, since a saving and a spend are not comparable on the same axis); in provider mode, the benefit-cost ratio (central headline ÷ annual running cost). The cost-effectiveness ranking is a result of the welfare and fiscal layers, not a separate assumption.

**Service-demand response parameters.** The capacity-gap and shock views use service-demand response parameters (elasticities, unit costs, baseline caseloads, staff ratios). These are evidence-informed estimates presented as ranges that reflect genuine uncertainty in how service demand responds to economic conditions; no single definitive elasticity exists for these services, and none would result even from a single provider's data, since one service's demand response does not establish the population elasticity. They are kept distinct from the value-added effect sizes, which are sourced to specific studies.

## 7. Evidence base

Every hardcoded valuation figure carries a source and a confidence tier. The provenance registry travels with the tool (`DATA_SOURCES`, `DATA_OUTCOMES`). The principal evidence:

| Item | Figure | Source | Tier |
|---|---|---|---|
| WELLBY spine | £13,000 / WELLBY at 2019 prices, applied at 2024 prices as £16,300 | HM Treasury, *Wellbeing Guidance for Appraisal* (Supplementary Green Book), 2021, fn102; uprated via ONS GDP deflator and real-GDP-per-capita growth | — |
| Employment, non-pecuniary | +0.46 WELLBY | Clark, Flèche, Layard, Powdthavee & Ward, *The Origins of Happiness*, Princeton University Press, 2018 | STRONG |
| Improved mental health (IAPT, central) | 0.71 WELLBY | Clark et al., 2018 | STRONG |
| IAPT high bound | recovery-specific gain (to 1.5) | Frijters, Clark, Krekel & Layard, "A happy choice", *Behavioural Public Policy*, 2020 | high bound only |
| Averted rough sleeping | £20,128 / year | Crisis, *At What Cost? The economic impact of homelessness*, 2015 | STRONG |
| Family Group Conferencing | 8.6pp lower care entry (pre-proceedings) | Foundations / Coram FGC randomised controlled trial | central; low bound = Nurmatov et al. (2020) null |
| Child maltreatment cost | £89,390 / child (discounted lifetime, non-fatal) | Conti, Morris, Melnychuk & Pizzo (NSPCC), 2017 | STRONG |
| Domestic abuse, intensive advocacy | odds ratio **0.39** (2015 edition); 0.43 is the **2009** edition | Rivas, Ramsay, Sadowski et al., *Cochrane Database Syst Rev* 2015;12:CD005043, DOI 10.1002/14651858.CD005043.pub3; the 0.43 is Ramsay et al., 2009 edition, CD005043.pub2. Intensive advocacy of **12 hours or more**, women recruited **on exit from refuges**, **United States** trials; significant at 24 months (0.39, 0.20–0.77, severe physical abuse), not significant at 12 months (0.61, 0.33–1.14) or 36 months; evidence rated low to very low | MODERATE |
| Domestic abuse cost | £34,015 / victim (2016/17) | Oliver, Alexander, Roe & Wlasny, Home Office RR107, 2019 | confirmed |
| Drug & alcohol treatment | value = benefit-cost ratio × cost | see below | STRONG |
| Debt advice (wellbeing) | central ≈ 0 | Pleasence & Balmer debt-advice RCT (null); 52–63% self-report carried as high bound only (Money and Pensions Service, *Money and Pensions Service-funded Debt Advice Impact Report 2023/24*, published March 2025; 2023/24 is the period covered, not the publication date) | central null |
| GP consultation | £42–£49 (2022/23) | PSSRU, *Unit Costs of Health and Social Care 2023 Manual*, Table 9.4.2, p.64; per 10-minute surgery consultation including direct care staff (£42 excluding, £49 including qualification costs); the manual's own footnote records that previous editions used 9.22 minutes per consultation, so the ten-minute basis is new to this edition and this price is **not like-for-like** with a per-consultation figure from an earlier manual; cost-input only, no value-added claim | cost-input |
| Attribution default | 0.5 (range 0.3–0.7) | Tool's own SROI-style modelling assumption, informed by Green Book additionality principles; UK appraisal guidance (Green Book, MHCLG, GMCA) treats attribution and additionality as case-by-case judgements rather than fixed defaults, so 0.5 is adopted as a neutral central value with a sensitivity band, not taken from any published default | assumption |

### The valuation stages: the rule

The table above records the coefficients and unit costs. These are the two multipliers applied *to* them, and the rule that sets them governs every value in every tool. The complete chain for every point in all four tools, generated from the parameters and recomputed against the shipped figure, is in `europe/docs/VALUATION_CHAINS.md`; the reasoning and the full before-and-after are in `europe/docs/PROVIDER_TOOLREADY_2024.md` §2e and §2f.

**The rule.** An outcome value is `raw × effect share × attribution`. Where the effect share is **already an impact net of a comparison group**, the attribution is **1.0**: the counterfactual is inside the number, and deducting it a second time understates the value. Where the effect share is an **observed outcome rate**, the attribution is what removes the counterfactual. Where a source exists it governs; where none exists the value is declared an assumption.

| row | effect share (L / C / H) | attribution (L / C / H) | central before → after |
|---|---|---|---|
| Children's social care | 0 / **0.086** an IMPACT / 0.086 | **1.0** flat | **£4,988.83 → £9,977.66** |
| Employment support | 0.11 / **0.30** a RATE / 0.46 | 0.20 / **0.22** / 0.27 | **£1,874.50 → £494.87** |
| Domestic abuse | **0.24** flat, a RATE | **13/24 = 0.5417** flat | **£5,588.24 → £5,811.77** |
| Housing | 0.1 / **0.2** an ASSUMPTION / 0.35 | 0.500 / **0.562** / 0.575 | **£2,698.36 → £3,032.96** |
| Talking therapies | 0.4 / **0.5** a RATE / 0.6 | 0.455 / **0.60** / 0.610 | **no change** (band only) |
| Debt advice | 0 / 0 / **0.63** | 1.0 / 1.0 / **0.5** | 0 → 0 (high £4,424.11 → £3,160.08) |
| Drug and alcohol | 2.3 / **2.5** / 4.0, a BCR | **1.0** flat | **unchanged** |

**Children's social care is the clearest case.** The 8.6 percentage points are the difference between two arms of the Foundations and Coram randomised trial, 44.8 per cent care entry in the control arm against 36.2 in the treated arm. The counterfactual is deducted by the trial's own design. The 0.5 attribution this row carried deducted it a second time and halved every value in the row. The band no longer comes from the multipliers at all: the high is now the upper bound of the Conti et al. 95 per cent interval, £145,508, which this project has held since the provider layer was built and had never carried into a value. Two candidate lows were available — the Nurmatov et al. 2020 null, giving £0, and the Conti lower bound of £44,896 at the central effect, giving £5,011.26. **The null was applied**, because a cost-interval low still presumes the effect is real whereas the null asks whether there is one at all.

**Employment support carries the smallest combined multiplier of the six, and both halves are sourced.** The effect share is an outcome rate: 0.30 central from the Work and Health Programme job-outcome rate of 31 per cent and the Restart rate of 30 per cent, which converge; 0.11 low from Additional Work Coach Support; 0.46 high from the Work and Health Programme first-earnings rate. All are per programme **start**, not per referral. The attribution is an impact: 0.20 from the Department's own Restart business case, which projects sustained jobs for an additional six in a hundred participants, over the thirty in a hundred reaching an outcome; 0.27 from the three-percentage-point Additional Work Coach Support impact over its eleven per cent in-work rate, taken from DWP, *The impact of additional Jobcentre Plus support on the employment outcomes of disabled people*, research and analysis, 18 March 2025, and not from the qualitative report of 2 May 2025, which carries no percentage. The 2026 extended impact assessment restates the same twelve-month comparison as 11 per cent against 8.2 per cent, an impact of 2.8 points, which would give 0.2545; the shipped bound follows the 2025 figure and this is recorded rather than left for a reader to find. **The 0.22 central is a choice within that sourced range and is not itself a computed quantity**, and its note says so. The combined multiplier falls from 0.25 to 0.066.

**Domestic abuse rests on a trial rather than on an odds ratio.** An effect share of 0.25 cannot be produced from the cited odds ratio at any baseline: the largest absolute reduction an odds ratio can give is (1 − √OR)/(1 + √OR), which is 0.2079 at OR 0.43 and 0.2311 at OR 0.39. Sullivan and Bybee 1999 report that 24 per cent of women who worked with advocates experienced no physical abuse across two years of follow-up against 11 per cent of controls, so the effect share is 0.24, a treated-arm outcome rate, and the attribution is 13 over 24, which is 0.541667; and 0.24 × 13/24 is 0.13 exactly. The estimate attaches to intensive advocacy of twelve hours or more, women recruited on exit from refuges, principally United States trials, significant at 24 months and not at 12 or 36. The band is narrower than it was because it now comes only from the cost per victim, a factor of 3.7, where before it came from an effect and attribution range whose product spanned 9.3, none of it sourced.

**Housing is the row the rule cannot rescue.** Its effect share of 0.20 stays and is declared an assumption with its reason: every published rate is post-placement tenancy sustainment of 80 to 96 per cent, on a denominator of people already housed, and the referral-to-placement conversion that would connect those to a referred caseload is published nowhere. Its attribution is now sourced, from the Canadian At Home / Chez Soi trial: 0.500, 0.562 and 0.575 from three of its reported housing-stability contrasts. Those trials are an intensive Housing First model with assertive community treatment for people with severe mental illness, and this row is generic housing support, so the fraction is borrowed from a stronger intervention on a more disadvantaged population and is more likely to overstate than understate.

**The same stages apply in the three European tools**, which carry a staged value rather than the raw the United Kingdom stages. Carrying a raw there would be an unfinished transfer of the instrument's own method rather than a country difference. The consequence is large and belongs in any reading of the European provider figures: at each tool's own shipped defaults the benefit-cost ratio falls from **16.32 to 1.23** in Spain, **17.68 to 1.65** in Italy and **15.46 to 1.15** in Greece. The United Kingdom ratio is unchanged at 0.42, because its default service has a central of zero before and after. Drug and alcohol is carved out of the European pass, because the United Kingdom multiplier is a benefit-cost ratio applied to a cost while the European drug values are built from a statistical-life valuation, so the multiplier and the raw are not the same kind of object.

**Drug and alcohol treatment — worked sourcing.** The value-added is the benefit-cost ratio applied to the per-person treatment cost, uprated to 2024:

- **Cost.** £3,000 per adult in effective treatment, 2008-09 prices, from the National Audit Office, *Tackling problem drug use*, HC 297 2009-10, Figure 5 on printed page 24, note 1 ("Funding figures are shown at 2008-09 prices"), corroborated at paragraph 17. Price base verified against the source 2026-08-01. Uprated to 2024 by the GDP deflator (factor 1.4959, HM Treasury December 2025 vintage, 2024-25 = 100). A current spend-per-head cross-check (~£1,985–£2,460, OHID/NDTMS and council budgets) is recorded for transparency.
- **The denominator is not "12+ weeks".** Effective treatment is defined at note 2, not note 1, and in three parts: adults discharged twelve weeks or more after triage, adults still in treatment at twelve weeks, and adults discharged within twelve weeks in a planned way. The third limb admits people treated for less than twelve weeks, so the "12+ weeks" shorthand used in earlier drafts of this report overstates the treatment intensity the denominator represents.
- **Rounding inherited from the source.** £3,000 is the source's own rounding of £2,979, so the shipped figure carries about 0.7 per cent of upward rounding that originates in the source rather than here.
- **An alternative in the same document, deliberately not taken.** Paragraph 18 of the same report gives a genuinely costed unit price of £4,900, from a treatment outcomes study. That is a different concept, sitting £1,900 away from the budget-based figure in the same source. The budget-based figure is used, deliberately and not by oversight, because it is the one that matches the population the row is denominated on.
- **Scope: the source covers drugs, not alcohol.** Figure 5 is drug treatment budgets, the corroborating paragraph refers to adult drug treatment, and the agency's remit as the report states it is treatment for drug dependency in England. Nothing in the source covers alcohol. The row is labelled drug and alcohol treatment, so applying this unit cost to a combined population is an extrapolation beyond the population it was measured on, and is recorded as one. No alcohol-treatment unit cost has been substituted for it; the three EU editions convert this same figure and inherit the same extrapolation.
- **Benefit-cost ratio band (near-term).** Low 2.3 (Dame Carol Black, *Review of Drugs Part 2*, 2021, Annex C Table C1, Year 1); central 2.5 (DTORS / Davies 2009, "£2.50 saved per £1", endorsed by the NAO 2010 review); high 4.0 (Public Health England, *Why invest?*, 2018, near-term).
- **Scope.** The band is deliberately near-term: it excludes the review's Year-5 figure (5.1, the end-point of a five-year plan, not a steady-state ratio) and the longer-run accruals (PHE's £21 per £1 for drug treatment and £26 per £1 for alcohol over ten years). The row is a combined drug-and-alcohol service stated on the better-evidenced drug-treatment basis; alcohol treatment carries a separately-evidenced near-term ratio of about 3:1.
- **Result.** Per-person value-added band £10,322 / £11,219 / £17,951, carried as low / central / high consistently with the other services.

**Two cost figures are derived, not surveyed.** Two of the unit costs above are constructed estimates rather than measured population averages, and are used as such. The averted-rough-sleeping figure of £20,128 is a derived, illustrative estimate of the additional public-sector costs incurred over twelve months by one person sleeping rough, built from the vignette modelling in the Crisis 2015 study (Pleace), not a surveyed average across a homeless population. The domestic-abuse figure of £34,015 per victim is likewise derived: the Home Office total estimated cost of domestic abuse of approximately £66bn divided by about 1,946,000 estimated victims in England and Wales in the year ending March 2017, at 2016/17 prices, rather than a directly measured per-victim average. Both unit costs are appropriate for benefit-transfer, but are labelled as derived so that no more precision is claimed for them than the method supports.

## 8. Limitations

- **Uniform take-up calibration.** A single UC take-up rate matches the expenditure aggregate but not the poverty distribution; the poverty diagnostic is therefore read off the uncalibrated baseline (Section 3).
- **Child denominator.** The engine's dependent-children count (13.51m) differs from HBAI (14.59m), which accounts for part of the residual child-poverty gap.
- **Working-age scope.** Pensioners are excluded; aggregates are working-age-scoped against UK totals.
- **Housing Benefit scope/legacy.** The pensioner-HB and UC-migration gap is documented and not corrected; it is a coverage matter, not take-up.
- **Quasilinear EV and the singleton-household / council-tax caveat.** The welfare measure is the change in disposable income; benefit units are modelled as singleton households, so dwelling-level incidence (council-tax single-person discount, shared housing) is approximate.
- **Provider value-added is a benefit-transfer.** Published effect sizes applied to described caseloads, not provider-specific measurement; figures carry confidence tiers and low / central / high bands that must travel with any quoted figure.
- **Stage-specific and bounded effects.** The Family Group Conferencing effect is pre-proceedings-stage-specific (the null systematic-review result is carried as the low bound); the IAPT WELLBY central is 0.71, with 1.5 a high-bound sensitivity only; debt-advice wellbeing is null at the centre, with the self-report figure a high bound only.
- **Service-demand layer.** The least-anchored component: its response parameters are evidence-informed estimates with low / central / high bands, reflecting genuine uncertainty in how demand responds to economic conditions. It is not a substitute for the microsimulation on any quantity the microsimulation models directly.
- **Single wave, UK only as a live model.** FRS 2023-24, one wave; the European generalisation is documented rather than instantiated.

## 9. Reproducibility

The pipeline runs from the FRS 2023-24 inputs in the mandatory order with the canonical settings (UC take-up 0.731, AROP floor at 60% of the median equivalised income, `PE_PERIOD = 2023`) and produces the canonical per-unit export. On a clean run from the pinned environment, the committed code reproduces the canonical anchors of Section 4 exactly, the WEVM headline and the ε = 1.62 crossover of Section 5, and the full WEVM grid that both editions of the tool embed. The four pipeline acceptance checks — income non-null, the survey/policy/export years all 2023, no region defaulted to a fallback, and a valid one-row-per-unit-per-scenario grain at 21.44m weighted benefit units — pass on the clean run. The tool therefore ships exactly what the current pipeline produces.

---

![Funded by the European Union](../../assets/eu_funded.png)

*This report documents the United Kingdom beta of the BENEFITS Holistic Valuation Framework. Funded by the European Union. Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or the European Research Executive Agency. Neither the European Union nor the granting authority can be held responsible for them. Project number: 101179032.*
