# EU layer (ES / EL / IT): data issues & limitations for the technical report

Prepared by CC. A single reference of every data issue, limitation, and caveat in the
real-data EU layer (Spain, Greece, Italy) so none is lost before the technical report is
written. Many of these are **outside our control** — they are inherent to EU-SILC (the
survey), to EUROMOD (the model and its Country Report baseline), or to the difference between
running the EU-SILC data directly and
EUROMOD's own bundled input dataset (the EMSD, the EUROMOD SILC Database), which prepares its inputs its own way.
Each entry states what it is, where it comes from, its magnitude, and how it should be
treated in the report.

Data-free: this document records aggregates, ratios, and methodology only; no microdata.

---

## 0. How to read this — issue classes

Every issue is tagged with one of four classes:

- **[SILC]** — an EU-SILC survey limitation. Inherent to the source data. **Outside our
  control.** (e.g. top-wealth under-representation, informal-economy under-coverage.)
- **[EUROMOD]** — a EUROMOD modelling or benchmark choice. Inherent to the model we
  validate against. **Outside our control.** (e.g. tax-compliance adjustments, benefit
  simulation, the deliberate AROP-below-survey for Greece.)
- **[UDB-ceiling]** — the EU-SILC data we run does not
  carry a variable that EUROMOD's own **EMSD input** prepares (national-SILC /
  administrative records / EUROMOD-team imputations); not a converter fault. **An
  input-preparation difference vs the EMSD, whose effect on results is unquantified.**
- **[conversion]** — an approximation we made in the converter because the EU-SILC data
  cannot support the exact construction. Documented; our choice; the honest best proxy.

Two over-arching rules the report must state once:
1. **Validation benchmark = the EUROMOD Country Report baseline, NOT the raw EU-SILC
   survey.** EUROMOD *simulates* taxes and benefits; it does not reproduce the survey. For
   Greece especially the two diverge by design (see EL-1).
2. **The welfare/distributional results are publication-grade against that benchmark for
   all three countries.** The residuals below are about *fiscal-output levels* and
   *income-level concepts*, not the distribution the tool uses.

---

## 1. Cross-cutting issues (apply to all three countries)

> The largest of these is sized in **section 8**, whose percentages are measured against
> the pre-conversion caseload; three of its four do not hold on the shipped one. The asset
> legs of the three minimum income means tests run partly on variables the public EU-SILC
> user database does not carry. As shipped: **Spain's** financial capital leg is now derived
> and live, and its aggregate is a calibration target that cannot validate it; **Italy's**
> dial is overstated by roughly 7% with the main-residence component still missing; and **Greece's**
> dial is **understated**, sitting 4.7% below the published spend its own calibration aims
> at, with the missing floor-area test able only to widen that gap (9.9). Those three are
> the current figures, and they are what the four dial faces carry; section 8's are not.

### 1.1 EU-SILC data vs EUROMOD's own EMSD input — an unquantified input-preparation difference  [UDB-ceiling]
The build runs the **EU-SILC data** (2024 wave) through EUROMOD, rather than EUROMOD's **own bundled input dataset
(the EMSD**, the EUROMOD SILC Database). The EMSD is a *different input preparation*: it
additionally carries NSI-supplied national-SILC variables, administrative/contribution history,
and EUROMOD-team imputations. Because we run EU-SILC directly, contribution bases,
employment/contribution histories, benefit disaggregations, and (for IT) the declared/non-declared
self-employment split are not prepared the way the EMSD prepares them. **The effect of this
input-preparation difference on results is UNQUANTIFIED: it cannot be measured without the EMSD,
which this project does not use. We claim neither equivalence to a standard EUROMOD (EMSD) run nor
inferiority — only that the input preparation differs.** This is the single most important
data-provenance note and the root of most country-specific items.

### 1.2 EUROMOD is a simulation, not the survey  [EUROMOD]
Disposable income, taxes, and means-tested benefits are *simulated*. EUROMOD recodes
negative incomes, applies its own disposable-income concept, and simulates benefits the
survey under-reports. Validating against the raw survey (`HY020`/`HY140G`) mismeasures the
build; the EUROMOD Country Report baseline is the correct target.

### 1.3 EU-SILC top-wealth and capital-income under-capture  [SILC]
Investment and property income are systematically under-captured because wealthy households
are under-represented and capital income is under-reported in household surveys. Documented
in every Country Report. Examples: **ES** investment income ~0.57 and property ~0.62 vs tax
data; wealth/property tax only ~37–38% of revenue captured. **EL** investment income
"heavily underreported" (EL CR §4.1.2). Not among the externally anchored components
(employment / self-employment / pensions); a known SILC limitation, not label-changing, but
it should be stated so absolute capital-income and wealth-tax figures are read with care.

### 1.4 Time period, monthly conversion, and uprating  [EUROMOD]/[SILC]
- Income reference period (prior year) differs from the labour/socio-demographic reference
  (interview time); reconciliation is partial.
- All monetary amounts are divided by 12 to an "average month," assuming income is received
  at a constant rate through the year.
- Uprating assumes every income source grows at one uniform rate, which understates
  distributional change; **uprating of self-employed and farming income is especially
  uncertain** (EL CR §4.4). We validate at the **2023 income reference year** like-for-like
  to remove the legitimate 2023→2024 uprating from the gaps.

### 1.5 NSI-derived gross / net-to-gross  [SILC]/[conversion]
Gross income is NSI-constructed from net (ES: INE; EL: ELSTAT net↔gross, Eurostat
KS-TC-20-001; IT: NSI-derived). We do **not** take it on trust: a component-level
consistency pass checks gross ≥ net and would reconcile from the population gross/net ratio.
In the **2024 wave** the held gross was internally consistent for EL and IT (ratios ~1.0–1.8,
no gross < net), so it was used as held. We cannot independently verify the NSI's gross
construction beyond this consistency check.

### 1.6 External national-accounts anchoring — precision tiers and series caveats  [method]
The income block of each country was externally anchored to national-accounts series **not
downstream of EUROMOD**, on a **three-tier precision standard** the report must state:
- **Employment — can be PINNED.** Eurostat `nama_10_gdp`, item **D11** (wages and salaries;
  **NOT** D1 compensation, which adds employers' social contributions). A tight match is a
  level validation.
- **Self-employment — MAGNITUDE-CONSISTENT only, never a tight pin.** Eurostat
  `nasa_10_nf_tr`, **sector S14 (households)**, item **B3G** (gross mixed income). B3G
  carries the **imputed return to own-account capital** and is **gross of consumption of
  fixed capital**, so a like-for-like survey concept sits **below** B3G by an unknown
  margin. The check **rules out gross inflation**; it does not validate the level.
  **Never substitute B2A3G** (combined operating surplus + mixed income) — it carries
  corporate surplus and imputed owner-occupier rents and is not like-for-like. (Sanity: the
  S14 B3G values used — ES 148,330m, IT 263,450m, EL 49,395m — are far below the combined
  B2A3G, confirming S14.)
- **Pensions — MAGNITUDE-CONSISTENT, function caveat.** Eurostat `spr_exp_pens` (ESSPROS),
  old-age + (anticipated old-age, where published) + survivors + disability. ESSPROS social-
  protection pensions are **not strictly like-for-like** with SILC `PY100G/PY110G/PY130G`.

### 1.7 Conversion approximations shared across countries  [conversion]
Because the EU-SILC data lacks the relevant variables:
- The **Heckman imputed wage** (`yivwg`) is proxied (earnings/hours, floored positive).
- **Contribution-base** proxies stand in for the EMSD's constructed bases.
- **Months-receiving** variables are approximated from the SILC months variables.
- **Means-tested benefits** (ES IMV, EL KEA, IT Assegno Unico) are left to the model's
  simulation on the UDB base rather than read from the survey.
- **Household-to-person allocation** is the one substitution the completed conversion
  makes on every household amount. The codebook allocates household money to "the default
  income recipients" or, for housing costs, to the people responsible for the accommodation
  (`hb080`/`hb090`), and the public release identifies neither. The whole household amount
  goes to the oldest member, the EMC sharing rule. Household and population totals are
  exact; only the allocation within a household differs, and every aggregate the tool
  reports is a household or population total.

> Spain's `bfa` (HY050G) and `bsa` (HY060G) are fed, and double-counting the simulated
> benefits is not a reason to withhold them: checked against each model's own income lists,
> neither enters an income list at all — they are read by `bunmt_es` and the uprating list
> as drivers — so feeding them cannot double-count anything. What IS withheld, and for the
> double-counting reason, is anything that would duplicate a simulated instrument:
> `bch00` and `bsa00` remain unfed in Spain because `bch00_s` and `bsa00_s` are simulated
> and are what the income lists read.

---

## 2. Spain (ES)

ES income block matches **both** national accounts **and** the EUROMOD baseline (EUROMOD
applies **no** tax-compliance correction — Y16_CR_ES §3.2.2: gross is "imputed by the
Spanish Statistical Institute based on reported net income"). The live caveats are
fiscal-output, plus the SILC capital under-capture.

| # | Issue | Class | Magnitude / evidence | Report treatment |
|---|-------|-------|----------------------|------------------|
| ES-1 | Self-employed SIC over-stated | [UDB-ceiling]/[OPEN] | **More than half of this row is not a ceiling at all.** Measured raw it is **+41.3%**. Most of that was a conversion defect: `ysemy`, the months-of-receipt count self-employed contributions scale with, was an unconditional 12 while the months-worked variable sat populated and used one line above it. Corrected, the line reads **EUR 17,238.9m against a published EUR 14,551m, +18.5%** (9.13). What remains is the standing hypothesis and nothing more: the model applies the income-based RETA rate to real earnings, and the actual **chosen-base + under-declaration** behaviour (lowers collections ~⅓) is not in the UDB. (Official EUROMOD ES itself over-states SICs under a full-compliance assumption — §4.3/§4.4.) **Nobody has measured how much of the remaining EUR 2,688m it accounts for.** | **Live ceiling**, and now also an open item. Do not publish an ES self-employed-SIC level without flagging it, and do not describe the residual as an absent variable: every input it reads is populated. |
| ES-2 | Income tax over-stated against the external figure, and now **below** the model's own baseline | [UDB-ceiling]/[OPEN] | **On the shipped build: EUR 128,515.7m against an external EUR 118,143m (+8.8%) and against EUROMOD's own published EUR 130,106m (−1.2%)**, the published line verified as `tin_s` at Y16_CR_ES table A3.4. It read 127,948.9, +8.3% and −1.7%, until the rebuild, and this entry carried those until the figure verification found them. So the overshoot against the external figure survives, and the position against the model's own baseline **has flipped from above to below**. The completed conversion did not cause the flip: the before and after columns of `BASELINE_VALIDATION.md` were identical at 127,948.9 through it, so the earlier +1.2% was measured against a different comparator rather than a different build. The 2026-08-03 rebuild then moved the line towards the published baseline, from −1.7% to −1.2%, because lower self-employed contributions leave more taxable income. The mechanism is understood only in part — the IRPF deduction and reduction structure and the regional component need national-SILC variables the release lacks — and **nothing establishes why the two comparators now straddle the build.** Recorded as unexplained. | **Live ceiling**, and an open item. A deduction-level enrichment could recover part; state both comparators, never one alone, because they have opposite signs. |
| ES-3 | Contributory unemployment under-simulated | [UDB-ceiling] | Was 3.5bn simulated vs ~20.6bn survey. **The comparison is not like-for-like:** 20.6bn is `PY090G`, which is insurance plus assistance, and the codebook splits it into `bunct` = `py092g` (15.5bn) and `bunnc` = `py093g` (5.1bn). Both are now fed as the codebook feeds them. The simulated `bunct_s` falls from 3,489m to 2,570m, because the read `bunct` and `bunctmy` drive the simulated caseload and they now cover 4,384 recipients rather than 6,464. So the split is right and the gap to the survey's own contributory line is 2.6bn against 15.5bn. Needs the contribution and duration history absent from the UDB. (Confirmed **not** caused by the PL032 bug — `bunct_s` was unchanged after that fix.) | Live ceiling; lowers disposable. State the contributory comparison against `PY092G`, not `PY090G`. |
| ES-4 | Investment/property income under-captured | [SILC] | yiy ~0.57, ypr ~0.62 vs tax; wealth/property tax ~37–38% of revenue. | Universal SILC limitation (1.3); state, not label-changing. |
| ES-5 | Self-employment sits **above** tax-declared | [SILC] | Survey self-emp +38% vs AEAT tax (2023); employment +15–16%. The report attributes this to the survey covering the whole population vs taxpayers only, and applies **no** correction. | Context for the NA reading: ES survey sits **above** tax-declared but **below** NA B3G (0.43×) — the sound band. |
| ES-6 | País Vasco & Navarra excluded from tax aggregates | [EUROMOD] | The foral regimes follow different tax rules; the Country Report excludes them from the AEAT tax comparison (A3.3/A3.4). | Note when comparing ES tax to external. |
| ES-7 | PL032 labour-status mapping bug (FIXED) | [conversion] | The original ES converter mis-mapped `PL032`, scrambling non-employed status for ~30,700 persons; **fixed** to the EL reference mapping. Invisible to the welfare gate (did not move read incomes/pensions). | Record as a corrected defect (history), now on the EL standard. |

NA anchor (income year 2023): employment `yem` 554,137m = **1.006× D11** 551,014m (pinned);
self-emp `yse` ~64–65k = **0.43× B3G** 148,330m (magnitude-consistent); pensions 194,012m =
**0.98× ESSPROS** 197,083m.

---

## 3. Greece (EL)

EL is the **third shape** and the **weakest-anchored**: EUROMOD ≈ UDB (the TCA is non-binding
on 2023 levels), but the gross sits **below** national accounts by the largest survey-coverage
/ informal-economy margin of the three. The ~4pp baseline-vs-survey AROP gap is **benign**
(documented modelling difference). All of this is documented by the EL Country Report.

| # | Issue | Class | Magnitude / evidence | Report treatment |
|---|-------|-------|----------------------|------------------|
| EL-1 | EUROMOD AROP **below** the SILC survey by design (~4pp) | [EUROMOD] | EUROMOD 15.77% vs SILC 19.60% (0.80× SILC). Documented (Y16_CR_EL §4.2.2 p.60-61): (a) EUROMOD simulates benefits the survey under-reports; (b) the SILC net-to-gross does not account for tax credits/allowances that EUROMOD's gross-to-net does. **Benign** — a disposable-modelling difference, not a gross fault. | State plainly: validate against the EUROMOD baseline, not the survey; the 4pp is documented and benign. |
| EL-2 | Income levels **under-capture** national accounts | [SILC] | Employment UDB **0.88× D11** (EL CR §4.1.2: −6% vs AADE tax); self-employment UDB **0.48× B3G**, and **below even tax-declared** (−32% vs AADE) — under-captured vs both tax and NA. Greek informal economy + survey under-reporting. | **The defining EL caveat.** Income levels sit below NA; **not pinned**. Sound for distribution; absolute EL levels are understated. |
| EL-3 | Self-employed + farmer SIC under EUROMOD | [UDB-ceiling] | **The divergence is −25.0%.** The comparator was a hand sum of the report's components and it dropped one. `ils_sicse` in EL_2023 has seven members, one switched off, so six are live: `tscsepi_s`, `tscsesi_s`, `tscseui_s`, `tscfrpi_s`, `tscfrsi_s`, `tscfrot_s`. Y16_CR_EL table A3.4 publishes all six: **1,347 + 478 + 71 + 433 + 151 + 9 = 2,489**; the sum in use was 2,418, omitting **`tscseui_s`, self-employed SIC: unemployment, EUR 71m**. Ours is 1,867.6. **This correction moves our figure further from the published line, not closer.** EL self-employed contribute on a **chosen EFKA category** with a minimum, not on actual income; the UDB lacks the category. (Official EUROMOD EL over-states the related contribution by 106% vs external — so the converted figure may be closer to administrative reality.) See `LIKE_FOR_LIKE_SWEEP.md` section 3. | Live ceiling; small (~0.62bn). |
| EL-4 | ENFIA real-estate tax not simulated | [UDB-ceiling] | **CLOSED 2026-08-02.** It was never a ceiling. The live 2023 branch of `tpr_el` computes `tpr_s = tpr - i_tpr_red`, and the reduction is gated on income years before 2019, so on this system the model READS the property tax rather than simulating it from property values. The codebook publishes `tpr = hy120g/12*hx010`, and `HY120G` is in the public release for 8,712 Greek households. Populated: **EUR 1,562.7m against the 1,575m external.** Greek disposable falls by 1.5%, towards the EUROMOD baseline it sat above. | Record as a corrected omission. The property-value variables `amrar` and `aobiv` remain absent, and they still govern the KEA asset test (section 8.5); it is the tax that is now simulated, not the wealth. |
| EL-5 | TCA present but non-binding in 2023 | [EUROMOD] | Y16_CR_EL §2.4: tax-compliance extension ON by default; but Annex A3.1 (p.78) shows `yemnr`=`ysenr`=0 for 2023 (non-zero in 2022) — it governs the **tax base**, not the income level, so EUROMOD ≈ UDB. | Methodological note: EL's TCA differs from IT's (which reduces the level). |
| EL-6 | Pension disaggregation limit | [UDB-ceiling] | `poacm`/`poaot`/`psuor` = 0: the UDB cannot separate supplementary, minor, and orphan pensions. SILC aggregates routed wholly into the contributory read components (`poa00`←PY100G, `psuwd`←PY110G, `pdi`←PY130G). | Documented disaggregation limit; pension **total** is at ESSPROS (1.01×). |
| EL-7 | SIC fund (`lpmfc`) approximation | [conversion] | All employees assigned to IKA (the dominant fund); the UDB cannot identify civil-servant/banking/public-enterprise funds. Income-year uprating ~1.0, so this does not move earnings. | Documented approximation; affects fund split, not the SIC total materially. |
| EL-8 | Region | [conversion] | EL has no NUTS region in the EUROMOD input template; degree-of-urbanisation (`DB100`) is used and NUTS-1 (`DB040`) carried out-of-band for the RWI join. | Documented; not a EUROMOD input variable. |
| EL-9 | Macrovalidation data scarcity | [EUROMOD] | The Greek crisis delayed/abandoned administrative statistics; the Country Report flags limited external benchmarks (§4.4). | Context for why several EL lines are loosely validated. |
| EL-10 | `ysemy` unconditional 12 — the ES-1 conversion defect, uncorrected | [conversion]/[OPEN] | **The defect 9.13 diagnoses for Spain is live here.** `convert_el.py:447` sets `ysemy`, the months-of-receipt count self-employed contributions scale with, to an unconditional 12, while `yemmy` on the line immediately above reads `months_work.clip(1, 12)` from the same populated variable. In Spain the same line charged a full year of contributions to the 22.4 per cent of the self-employed the survey records as working less than one; corrected, that line moved from EUR 20,566.8m to EUR 17,238.9m, **+41.3% to +18.5%** (9.13). **The fix is one line and has not been applied here**, because applying it would move a published Greek surface. Direction is unambiguous: the correction can only lower self-employed contributions, so it **widens** the EL-3 divergence of −25.0% rather than narrowing it. Magnitude is unmeasured — the Greek months-worked distribution has not been examined, and Spain's 22.4 per cent short-year share is Spain's own. | Do not read the Greek self-employed and farmer contribution line as a ceiling a conversion fix would close. It is the opposite: the line already sits below its published comparator and the outstanding fix moves it further below. The converter log and `CONVERSION_RECORD.md` now state that `ysemy` is set to 12 rather than derived from months. |

NA anchor (income year 2023): employment `yem` 54,921m = **0.88× D11** 62,120m (below NA,
not pinned); self-emp `yse` 23,660m = **0.48× B3G** 49,395m (below NA, magnitude-consistent);
pensions 31,838m = **1.01× ESSPROS** 31,470m (at NA). B3G S14 cell confirmed **returned**
(not suppressed for Greece).

---

## 4. Italy (IT)

IT ships at NA/UDB income **levels** that **exceed** the EUROMOD baseline, because EUROMOD
applies a **documented, default-ON, proportional Tax Compliance Adjustment** that pulls
self-employment down to tax-declared data. The EU-SILC data carries the un-corrected (higher,
true) survey figure — a **MODEL** concept difference, data sound, not an inflation.

| # | Issue | Class | Magnitude / evidence | Report treatment |
|---|-------|-------|----------------------|------------------|
| IT-1 | Self-employment +69% over EUROMOD = the EUROMOD TCA | [EUROMOD] | UDB 226,735m vs EUROMOD 133,905m (factor 0.591), the latter verified at Y16_CR_IT table A3.2. **The mechanism runs the opposite way to the obvious reading.** `TCA_it` is NOT "default-ON": it reads `switch=off` in all 21 Italian systems, 2005 to 2025, and is turned on by the DATASET, `IT_2024_a1_2015_03_e2`, in `IT_DataConfig.xml`. Anyone checking the system switch would conclude the opposite of the truth. It runs on every point of this surface and does nothing, because the variables it consumes (`yseev`, `ysenr`, `lse00`) are imputations on national SILC and the public release cannot fill them: `yseev` is by definition the evasion-adjusted series, and this conversion puts the unadjusted survey total into it, which asserts that evasion is zero. | **MODEL, data sound.** State the mechanism as dataset-enabled, not default-on. |
| IT-11 | The flat-tax optional regime never fires | [UDB-ceiling] | **New finding, 2026-08-02, recorded nowhere before.** `tinyse_it` charges 15 per cent (`$FlatRate`) on self-employment income net of contributions where `lse01 = 1`, and moves that person out of the progressive base (`il_taxabley` carries `yse00_s`, not `yse`). `lse01` is a national imputation, absent from the release, and `SetDefault_it` sets it to 0 for this dataset class, so **no self-employed person in this build is in the *regime forfetario* and every one is taxed progressively at up to 43 per cent.** The report puts the regime's own revenue at EUR 2,861m (A3.4, `tin00_s`); this build has zero. Bounded: taking everyone statutorily eligible into the regime removes EUR 27,803m from national IRPEF, and Italy actually had about 1.9 million taxpayers in it in 2023 against 7.5 million eligible here. | Live ceiling. It is on the Italian tax dial's face, because the dial reaches a population the real schedule does not. |
| IT-12 | `ysemy` unconditional 12 — the ES-1 conversion defect, uncorrected | [conversion]/[OPEN] | **The defect 9.13 diagnoses for Spain is live here.** `convert_it.py:441` sets `ysemy`, the months-of-receipt count self-employed contributions scale with, to an unconditional 12, while `yemmy` on the line immediately above reads `months_work.clip(1, 12)` from the same populated variable. In Spain correcting the same line moved self-employed contributions from EUR 20,566.8m to EUR 17,238.9m, **+41.3% to +18.5%** (9.13). **The fix is one line and has not been applied here**, because applying it would move a published Italian surface. Direction is unambiguous: the correction can only lower self-employed contributions, so it **narrows** the IT-3 divergence of +93.8%. Magnitude is unmeasured, and the two effects are not additive: IT-3 rests on a unit error in its own comparator, so that comparator must be re-derived before the residual can be attributed. | Do not attribute the whole of the Italian self-employed SIC divergence to EUROMOD or to the UDB. Part of it is a conversion defect this project has identified, quantified in another country, and not yet fixed here. The converter log and `CONVERSION_RECORD.md` now state that `ysemy` is set to 12 rather than derived from months. |
| IT-2 | EMSD self-employment decomposition absent from the UDB | [UDB-ceiling] | The EMSD splits self-employment into declared/non-declared (`yse` + `yseib`/`yseil`); the EU-SILC data carries only the `PY050G` total, routed **whole** into the single `yseev` component the `a1` config reads (no fabricated split). | Documented; a strict cross-build self-emp subgroup match would require the EMSD's own input preparation (effect unquantified). |
| IT-3 | Self-employed SIC **+94%** | [EUROMOD]/[UDB-ceiling] | **This row rests on a unit error larger than the income tax one.** The EUR 7,093m it was measured against **is not an amount**: it is the 2023 cell of **table A3.3, `Direct taxes and SIC - Number of payers (thousands)`**, 7,093 THOUSAND people paying contributions against an external 3,260 thousand. The annual amount is four pages later in **table A3.4, `Direct taxes and SIC - Annual amounts (millions)`**, where the row with the same label reads **EUR 20,144m** against an external **EUR 20,716m**. Both tables carry a row with that label; Spain's figure was read from A3.4 and Italy's from A3.3 in the same pass. Ours is EUR 39,037.4m, so **+93.8% against the model's own line and +88.4% against the external one**, a factor of 1.94 rather than 5.5. The mechanism is unchanged and still explains it: inflated base (1.69×, the un-TCA'd self-emp) × contribution-base concept. The old "3.25× concept" arithmetic was derived from the wrong denominator and does not survive; what survives is that the release cannot carry the contribution-base concept at all. No NA correspondence. See `LIKE_FOR_LIKE_SWEEP.md` section 1. | Live ceiling; flag any IT self-emp-SIC level. Still the largest divergence in the deliverable, but **not "several times the published figure"** — do not use that framing. |
| IT-4 | Pensions above ESSPROS / above EUROMOD | [SILC] | UDB pensions +14.8% vs EUROMOD; **+8.6% above ESSPROS (2023 income reference year**, re-anchored from the 2022 vintage; not like-for-like). | Magnitude-consistent (function caveat); state. |
| IT-5 | `phl` (taxable invalidity) not separable | [UDB-ceiling] | Left 0: the EU-SILC data cannot separate the taxable-invalidity component from `PY130G`. The codebook confirms it: `phl` is `pminv*pinv_e`, both national. | Documented limit. |
| IT-9 | Employer contributions rest on a contract class EU-SILC does not carry | [conversion] | Every component of `sicer_it` is gated on the contract class `lcl`, and EU-SILC carries no such field: ungated, all seven compute zero. `lcl` is derived from occupation by a stated proxy of ours (ISCO-08 major groups 6-9 blue), giving **EUR 181,054m against EUROMOD's own published 179,797m and the 180,821m EU-SILC itself records in PY030G**, inside the bracket the class can produce at all (177,906m all white, 191,133m all blue). The proxy raises Italian shock costs by 1.42x on the GDP dial and 1.60x on the unemployment dial. | The employer leg rests on a labelled proxy: the class is ours, not EUROMOD's, and no EUROMOD country derives `lcl` from occupation. |
| IT-10 | Italy's property tax is simulated and reads zero | [UDB-ceiling] | **Not fixed.** `tpr_it` is live and simulates IMU from `amriv*1.05*160` and `aobiv*1.05*160`, the statutory revaluation. Both cadastral variables are absent, so Italy's simulated property tax is zero against the EUR 12,492m of wealth taxes `HY120G` records Italian households paying. It is the same hole Greece closes, and it cannot be closed the same way: Greece READS `tpr` and Italy SIMULATES it, so supplying the tax is not an option and the only way in is the cadastral value. | Live ceiling. State that Italian property tax is absent from the fiscal side. |
| IT-6 | Region | [conversion] | `drgn2` from `DB040` NUTS-1 → a representative NUTS-2 code (the UDB carries only NUTS-1, 5 macro-areas). Affects only the regional IRPEF surcharge, a small part of income tax. | Documented NUTS-1 granularity limit. |
| IT-7 | EUROMOD-side self-employed subgroup not directly comparable | [UDB-ceiling] | A direct cross-build subgroup comparison needs the EMSD input; scaling is forbidden. Correct positioning is evidenced by the IT-side subgroup, the all-decile overall match, and the sane WEVM directions. | Honest limitation; state. |
| IT-8 | `a1` config consumes self-employment via `yseev` | [conversion] | The real-data config discards a directly-fed `yse`; the UDB total is fed to `yseev` (the component `a1` aggregates into `yse`). | Documented convention (not a fault). |

NA anchor (income year 2023): employment UDB 604,262m = **1.000× D11** 604,461m (pinned);
self-emp UDB 226,735m = **0.86× B3G** 263,450m (below NA, magnitude-consistent); EUROMOD
self-emp 133,905m = 0.51× B3G (pulled down by the TCA); pensions UDB 358,173m above ESSPROS.

---

## 5. What each residual blocks — and does NOT block

| Residual class | Blocks | Does NOT block |
|----------------|--------|----------------|
| Fiscal-output ceilings (ES self-emp SIC + income tax + unemployment; EL self-emp SIC + ENFIA; IT self-emp SIC) | Publishing **absolute fiscal-line levels** without a caveat | The welfare/distributional results, reform *differences*, the WEVM layer |
| IT income-level concept difference (self-emp +69% = TCA) | A strict **level** match to the EUROMOD baseline | The distribution (validates), the NA-soundness of the UDB |
| EL below-NA income levels (employment 0.88×, self-emp 0.48× B3G) | Absolute EL income **levels** read as NA-complete | The distribution (validates vs EUROMOD), the inflation test (ruled out) |
| SILC capital/wealth under-capture | Absolute capital-income and wealth-tax levels | Labour-income and pension analysis |

**None of these blocks the tool's purpose** — welfare and distributional analysis against the
EUROMOD Country Report baseline, which is publication-grade for all three.

---

## 6. Where EUROMOD's own EMSD input would prepare things differently

Under EUROMOD's own EMSD input (the EUROMOD SILC Database) these would be prepared differently (and only these): the IT
self-employment declared/non-declared decomposition and a direct self-emp subgroup match; the
ES/EL/IT contribution-base and chosen-base SIC behaviour; the ES income-tax deduction
structure; contribution/duration history for contributory unemployment; and a strict
income-**level** match to the EUROMOD baseline where currently only the distribution matches.
Property-tax simulation (EL ENFIA, ES wealth tax) needs property objective values that even
the EMSD may not carry.

---

## 7. Provenance

All figures here are sourced from this session's external-anchoring passes (Eurostat
`nama_10_gdp` D11, `nasa_10_nf_tr` S14 B3G, `spr_exp_pens` ESSPROS; the EUROMOD Country
Reports Y16_CR_ES / Y16_CR_EL / Y16_CR_IT with page references) and the on-disk build
reports. No external series was used as a pass/fail benchmark; no input was scaled toward
EUROMOD or national accounts; B2A3G was never substituted for household-sector S14 B3G. The
EU-SILC data was read read-only (c-files only); no microdata is reproduced here.

---

## 8. Asset tests: how much the minimum income dials are overstated  [UDB-ceiling]/[conversion]

> **These percentages are measured against the pre-conversion caseload.** One of the four
> holds on the shipped one:
> Italy's is roughly 7% rather than 8%. **Greece's arithmetic survives but its sign does
> not**: the 13% is what applying the missing floor-area leg would remove, and the dial is
> not overstated at all. It sits 4.7% *below* the published spend that its own Benefit
> Calibration Adjustment targets and does not reach, so applying the leg would widen that gap
> rather than close it. See 9.9. Two more do not survive.
> Spain's "about 0.5%" used a rate borrowed from the Italian model; at the rate Spain's own
> codebook publishes it is 7.0%, and the caveat now carries the whole range. And section
> 8.4's finding that every Italian child allowance recipient sits in the maximum band is
> **wrong**: it compared a monthly `il_isee` against annual thresholds. Measured on
> `ymn03_s`, the variable the model bands on, 54% of recipients are in the maximum band and
> 40% in the taper, and the rebuild does not bear on that.

This section sizes the flagship input-completeness limitation. It is a
measurement pass: no converter, input variable, or surface was changed. Each country's
**unmodified** baseline was run once on the matched engine, the currently-eligible set was
read from the engine's own output, and the model's own asset thresholds were then applied
to a proxy for whichever leg of the test is inert. Aggregates only; no microdata.

### 8.0 Which leg is inert, per country

The three minimum income means tests are not equally affected, and the earlier shorthand
that "the asset legs never bite" is too broad. Each country has exactly one dead leg, and
it is a different leg in each.

| | movable / financial leg | immovable / property leg |
|---|---|---|
| **ES** `bsa00_es` | **inert.** `afc` is never populated and the ES model has no fallback for it | **live.** `i_apr = ypr*12/0.045`, the model's own 4.5% rental-yield capitalisation, and `ypr` is populated from HY040G |
| **IT** `bsamm_it` / `isee_it` | **live.** `isee_it` derives `afc = yiy/0.0277` on `it_2024_*` datasets, and `yiy` is populated from HY090G | **inert.** `sin02_s` (main residence, from `amriv`), `sin03_s` (other buildings, from `aobiv`), and the standalone `(aobiv*1.05*160) <= 30000` eligibility test |
| **EL** `bsa00_el` | **effectively live.** The deposits leg `afc < i_thres2` is inert, but its presumptive-interest twin `yiyit < i_thres2*0.006` is live, because `SetDefault_el` sets `yiyit = yiy` and `yiy` is populated | **inert.** `i_wealth` is built from `amrar` (main residence m2) and `aobiv*aobar` (secondary), neither of which is populated |

This corrects the earlier shorthand that Italy's ISEE asset component is zero. Only its
immovable part is. It also means Spain's exposure is confined to financial wealth and
Greece's to property.

### 8.1 The baseline each dial rests on

Measured from the unmodified baseline run, 2026-08-02, matched engine v3.8.6:

| | eligible households (unweighted) | weighted households | baseline outlay on the dial's instrument |
|---|---:|---:|---:|
| ES (`bsa00_s`, IMV) | 1,164 | 767,050 | EUR 2,498.5 m/yr |
| IT (`bsamm_s`, AdI) | 2,196 | 1,927,386 | EUR 7,962.4 m/yr |
| EL (`bsa00_s`, KEA) | 454 | 206,825 | EUR 497.7 m/yr |

The Spanish figure identifies the instrument and the eligible set the dial actually moves.
`europe/Spain/outputs/reemit_proof.json` records an implied baseline outlay of
**EUR 2,479.25 m** for the same instrument; see `europe/docs/REEMIT_PROVENANCE.md`. The
reading in the table above is the engine's own baseline outlay on the instrument, and the
proof's figure is the outlay implied by the shipped dial grid. They are two measurements of
the same instrument taken by different routes, and they do not agree, which is why the
identification above is reported as a measurement rather than as an agreement between the
two. Neither number is altered here: they are measurements, not claims.

### 8.2 Spain: small, and a lower bound

Proxy: financial capital inferred from investment income, `afc = HY090G / y`. Threshold:
the model's own `i_wealth_00`, EUR 20,353 for one person rising 40% per additional member
to a cap of EUR 52,919. The annual reading of `$bsa00_lim` is the one the engine applies:
an eligible household carries `i_apr` up to EUR 5,309, which exceeds the monthly reading of
the same constant, so the monthly reading cannot be what fires.

| assumed yield | households newly excluded | share of caseload | share of outlay |
|---|---:|---:|---:|
| 0.60% (the Greek model's own deposit rate) | 51 | 3.6% | 2.5% |
| 2.77% (the Italian model's own rate) | 14 | 1.2% | 0.5% |
| 5.00% | 8 | 0.7% | 0.4% |

Only 191 of the 1,164 eligible households report any investment income at all, and the
median among those is EUR 101 a year. Second properties are not a route either: exactly one
eligible household rents its home and pays any wealth tax.

**Estimate: the Spanish minimum income dial is overstated by about 0.5%, and by no more
than about 2.5%.**

**Confidence: high that the effect is small, but the estimate is a lower bound.** A deposit
that pays no interest is invisible to this proxy, and EU-SILC under-captures capital income
generally (see 1.3). The direction of that error is known and one-sided: the true exclusion
share can only be higher, not lower.

### 8.3 Italy: material, and confirmed by two independent routes

Route A, the standalone second-property test. `aobiv*1.05*160` is the cadastral value of
non-main-residence property, which is also the IMU base, and IMU exempts the main residence.
Back-solving HY120G at the statutory IMU range gives:

| assumed IMU rate | households newly excluded | share of caseload | share of outlay |
|---|---:|---:|---:|
| 0.76% (standard) | 249 | 9.5% | 7.8% |
| 1.06% (maximum) | 226 | 8.5% | 7.2% |

Route B, the ISEE threshold. The AdI requires ISEE <= EUR 9,360. Restoring the immovable
component raises ISEE by `0.2*(sin02_s+sin03_s)/scale`, with the main residence valued at
`amriv*1.05*160` less mortgage capital and less an exemption of EUR 52,500 plus EUR 2,500
per dependent child after the first, two thirds of the excess counting. Valuing the main
residence from imputed rent:

| assumed yield / cadastral-to-market ratio | households newly excluded | share of caseload | share of outlay |
|---|---:|---:|---:|
| 5% / 50% | 193 | 7.6% | 6.1% |
| 4% / 50% | 207 | 8.1% | 6.6% |
| 4% / 70% | 345 | 14.0% | 9.9% |

Taking either test at the central setting (4% yield, 50% cadastral-to-market, 1.06% IMU)
excludes 239 households, 9.2% of the caseload and **7.6% of the outlay**.

**Estimate: the Italian minimum income dial is overstated by roughly 8%, with a defensible
range of 6% to 10%.**

**Confidence: moderate.** Route A rests on one assumption, the IMU rate, within a narrow
statutory range, and on HY120G measuring IMU, which for Italy it does. Route B stacks two
assumptions and is correspondingly weaker. The two land within two percentage points of
each other, which is the main reason for reporting the band rather than a point. The
estimate omits mortgage capital outstanding, which the ISEE deducts and which the EU-SILC
data does carry in HH071, so it is if anything slightly high.

### 8.4 Italy: the same omission also flattens the child allowance dial

The Assegno Unico is banded on the same ISEE, at EUR 16,215 for the maximum amount and
EUR 43,240 for the minimum. Measured on the committed baseline, the modelled ISEE
distribution across all households is a median of EUR 1,748, a 90th percentile of
EUR 4,055 and a 99th of EUR 10,329; among households with children the median is EUR 1,306.
**Every modelled Assegno Unico recipient, 100% of a weighted 6.35 m households and an
outlay of EUR 20,477 m/yr, therefore sits in the maximum-amount band.**

The missing immovable component is one identified cause and is arithmetically sufficient to
matter: a two-person household owning a main residence with a cadastral value of
EUR 100,000 would see ISEE rise by about EUR 4,000, which on this distribution moves
households across bands. It is not the only cause, because the income side of ISEE is also
depressed by the input components recorded elsewhere in this document.

The consequence for the tool is not primarily the level. It is that the child allowance
dial applies its uplift uniformly at the top of the schedule instead of across the ISEE
gradient, so the **distributional profile of the Italian child dial is flatter than reality**,
and its effect is concentrated in the flat band by construction rather than by policy. The
report should say this next to the child dial, not only next to the minimum income dial.

### 8.5 Greece: the largest of the three

Proxy: `amrar` inferred from HH030, the number of rooms, at an assumed floor area per room,
valued at the model's own unit values of EUR 1,338 per m2 urban and EUR 745 rural, against
the model's own threshold of EUR 90,000 plus EUR 15,000 per additional member, capped at
EUR 150,000. Only owner-occupiers are tested, as the model tests them. Separately, 26 of the
454 eligible households rent their home yet pay ENFIA, so they own property elsewhere, which
`aobiv*aobar` would have caught.

| assumed m2 per room | on the m2 route alone | including the owns-elsewhere route |
|---|---|---|
| 20 | 12 hh, 2.0% of caseload, 2.2% of outlay | 38 hh, 8.9% of caseload, 8.9% of outlay |
| 25 | 39 hh, 6.6% of caseload, 6.6% of outlay | 65 hh, 13.5% of caseload, 13.3% of outlay |
| 30 | 52 hh, 9.2% of caseload, 9.9% of outlay | 78 hh, 16.2% of caseload, 16.6% of outlay |

36.5% of the eligible caseload are owner-occupiers with a median of 3 rooms, and 43.5% pay
some ENFIA.

**Estimate: the Greek minimum income dial is overstated by roughly 13%, with a defensible
range of 9% to 17%.**

> **Wrong in sign, corrected at 9.9.** The 13% is sound as a measure of what applying the
> missing leg would remove, and it is used there. Calling the dial *overstated* is not: the
> baseline it would remove that 13% from already sits 4.7% below the published spend that
> Greece's own calibration adjustment targets and fails to reach, so the removal takes the
> dial further away from the published figure, not towards it.

**Confidence: moderate to low on the point, higher on the floor.** The rooms-to-m2
conversion is crude and the m2 route is sensitive to it, moving from 2.2% to 9.9% across the
range tested. The owns-elsewhere route needs no such assumption and on its own accounts for
6.9 percentage points of caseload, so the floor of the range is firmer than its centre.
EU-SILC carries no dwelling area for Greece, so nothing better is available on this machine.

### 8.6 What this does to the dial

In all three countries the asset test, when it fails, removes the whole payment rather than
tapering it: ES applies `Comp_perTU = -i_bsa_00`, IT applies it as an `Elig_Cond`, and EL
applies it inside the benefit's `Comp_Cond`. So the share of outlay above is the share of
the baseline that should not be there.

The `min_income_up` dial is an income-floor top-up to existing recipients with eligibility
held at baseline, and its implied baseline outlay is constant across magnitudes, as the
re-emit proofs record. Its fiscal cost is therefore proportional to that baseline outlay,
and an overstatement of the baseline by share `s` overstates the dial's fiscal cost by the
same `s` at every point of the grid.

The welfare figure moves the same way to first order and possibly by more. The households
this test would exclude are asset-rich and income-poor, so they sit low in the equivalised
income distribution, which is exactly where the inequality-averse epsilon weights are
largest. The welfare overstatement is therefore at least proportional to `s` and rises with
epsilon.

**Summary for the report.** Spain's minimum income results stand with a stated caveat: the
overstatement is about half a percentage point and immaterial at the precision the tool
displays. Italy's and Greece's do not stand unqualified. The report must state that the
Italian minimum income dial is overstated by roughly 8% and the Greek by roughly 13%,
because their asset tests run on variables the public EU-SILC user database does not carry,
and that the Italian child allowance dial is additionally flattened because every modelled
recipient falls in the maximum ISEE band.

> **Read this in place of the paragraph above**, which is written as an instruction to the
> report rather than as a measurement. What the report should say:
>
> * **Spain.** The financial capital leg is derived and live. Its aggregate is the target of a
>   calibration adjustment, so the aggregate cannot be used to validate it or the eligibility
>   rules underneath it.
> * **Italy.** Roughly **7%**, not 8%, and the second-property component is now supplied. The
>   main-residence component is still missing and is the larger of the two. The child
>   allowance is **not** flat: the band shares are 47 / 42 / 11 per cent of recipients, and
>   the claim that every recipient sits in the maximum band was an artefact of comparing a
>   monthly `il_isee` against annual thresholds.
> * **Greece.** **Not overstated.** The dial sits 4.7% below the published spend that its own
>   calibration adjustment targets and does not reach, and the missing floor-area test would
>   only widen that gap. See 9.9.

### 8.7 Provenance for section 8

Eligible sets and baseline outlays: one unmodified baseline run per country on the matched
engine (v3.8.6, `C:\Program Files\EUROMOD\Executable`), systems ES_2023 / IT_2023 / EL_2023,
datasets ES_2024_b1 / IT_2024_a1 / EL_2024_c1, read from the engine's own output frame. All
thresholds, rates, exemptions, unit values, and equivalence scales are the models' own
constants read from `XMLParam/Countries/{ES,IT,EL}/*.xml`, not values recalled or borrowed.
The 4.5% rental yield is `$prelim_ry_rate` in the ES model, the 2.77% capital yield is the
divisor in `isee_it`, and the 0.6% deposit rate is `$bsa00_int_rate` in the EL model. The
only assumptions not taken from a model are the Italian cadastral-to-market ratio, the
Italian imputed-rent yield, and the Greek floor area per room, each of which is reported as
a range rather than a point. EU-SILC was read read-only, c-files only. No counterfactual run
with a populated asset variable was performed, because changing an input variable is out
of scope here; such a run would replace the ranges above with a single
measured figure and is the obvious next step if the limitation is ever closed.

---

## 9. Residual items, recorded so that everything known sits in one place

None of these is fixed. They are
here because a limitation nobody has written down is indistinguishable from a
limitation nobody has found.

### 9.1 The Greek region code: in the input completeness list

**It sits in section 10 with the other absent variables, and is given no special treatment
there.** `drgn2` is one absent variable among many: the release carries
NUTS-1 in `DB040` and not NUTS-2, the Greek model reads it in one place, no dial or scenario
depends on it, and there is **no tool-face consequence**. A numbered entry of its own
invited the question of why the twenty-three Italian ones and the empty `PL111A` did not
have one, and there was no good answer.

Spain asks for nothing it does not get. Italy is missing 23 variables, and the engine names
every one of them in its own run log and in the NOT FOUND banner each run prints.

### 9.2 Spain's minimum income cannot respond to a shock, because it is calibrated to a fixed sum of money  [CLOSED, documented modelling convention]

On comparable legs, the change in benefit spending is:

| | GDP shock, −5% | GDP shock, −10% | unemployment +5pp | unemployment +10pp |
|---|---:|---:|---:|---:|
| Spain | +25 m | +35 m | −17 m | +27 m |
| Italy | +561 m | +1,167 m | +2,287 m | +4,633 m |
| UK | | | +2,890 m | +6,001 m |

Spain is two orders of magnitude out of line with Italy on a benefit system of broadly
comparable size, and its own modelled IMV outlay is EUR 2,498 m. A 10 percentage point
unemployment shock raising benefit spending by EUR 27 m is not a credible automatic
stabiliser response.

It was recorded here as wholly unexplained, then narrowed to one question, and **that
question was answered on 2026-08-03. This entry is closed.** It is kept in full, including
the two disproved hypotheses, because both were plausible and the record of what was ruled
out is worth as much as the answer. The answer itself is at the foot of the entry.

**Disproved: the prior-year means test.** The IMV is assessed on the previous fiscal
year in Spanish law, and if the model implemented it that way a current-year shock
could not reach the entitlement, and the near-zero response would be correct behaviour
rather than a defect. **That is not what this model does.** `il_bsa00`, the income list
the IMV means test reads, expands to leaves including `+yem` and `+yse`, which are
exactly the two variables the Spanish shock levers touch
(`europe/model/means_test_income.py`, `europe/model/incomelist_members.py`). And the
test demonstrably sees the shock: at unemployment +10pp the aggregate means-test income
**falls by EUR 48,363m**.

**Also disproved: a fixed caseload cap.** All three countries carry a take-up cap, and
in all three it is `$X_target_count = $sum_i_X_elig * $X_rate`, proportional to the
eligible count rather than fixed, so it scales with eligibility and cannot pin spending
against a shock.

**What is actually happening, measured.** `europe/model/shock_benefit_decomposition.py`
differences every simulated benefit instrument in each country's `ils_ben` at
unemployment +10pp:

| | `ils_ben` change | what moves |
|---|---:|---|
| Spain | **+29.7 m** | child allowance `bch00_s` +175.3, almost entirely offset by the child tax credits `tintrch*` at −176.5. **The IMV `bsa00_s` moves −2.5.** |
| Italy | +4,192.8 m | `bsamm_s` (AdI) **+4,346.9** |
| Greece | +278.5 m | `bch_s` +118.9, `bho00_s` +80.6, `bsa00_s` (KEA) +45.0 |

So the Spanish total is not small because many instruments each move a little. It is
small because **the minimum income does not move at all**, and the one instrument that
does move is cancelled by an offsetting tax credit inside the same list.

**And the IMV does not move for a locatable reason.** Entitlement is flat, EUR 2,502.5m
to EUR 2,500.0m **(both readings from the pre-conversion surface, superseded 2026-08-02; the
shipped surface now implies a baseline outlay of EUR 2,479.25 m, and the flatness, not the
level, is what this paragraph rests on)**, while the **weighted recipient count falls 19 per cent, from 755,746
to 609,679**. The model computes a larger entitlement for more households and then does
not pay it: the paid caseload is set by `$bsa00_target_count` applied to a cumulative
person count over a seeded random ordering (`i_bsa00_sort = i_bsa00_rand`). The draw is
reproducible, so this is a mechanism and not noise: two identical baseline runs give
identical aggregates and the identical recipient set.

**The last question is answered, and the item closes. 2026-08-03.** Why the paid recipient
count falls when the eligible population rises: **because the target the cap is set from is
expressed in MONEY, not in people.** Read from the model by
`europe/model/benefit_adjustments.py`, the Spanish spine is

    $bsa00_BTA_rate    = 0.44
    $bsa00_targetBCA_amt = $extstat_amount_bsa00_s * 1000000/12     <- EUR 2,504m a year
    i_bsa00_sort       = i_bsa00_rand                               <- a seeded random draw
    i_bsa00_cumexp     = CumulativeSum(bsa00_s, weighted, sorted by i_bsa00_sort)
    i_bsa00_bca_take   = bsa00_s > 0 & i_bsa00_cumexp <= $bsa00_targetBCA_amt
    $bsa00_BCA_rate    = $sum_i_bsa00_bca_take / $sum_i_bsa00_elig
    $bsa00_rate        = min($bsa00_BCA_rate, $bsa00_BTA_rate)
    $bsa00_target_count = $sum_i_bsa00_elig * $bsa00_rate

The cap is proportional to the eligible count, which is why a fixed caseload cap was
correctly disposed of above. But **the rate it is proportional to is itself derived from an
expenditure cutoff**. A shock raises the eligible count and the average entitlement at the
same time, the cumulative expenditure therefore reaches the same fixed EUR 2,504m after
**fewer** units, `$bsa00_BCA_rate` falls on both its numerator and its denominator, and
`$bsa00_target_count` collapses to the number of units the money stretches to. The
proportionality is real and it is not what governs the answer.

The figures already in this entry are the identity: the count falls 19.3 per cent, the mean
paid entitlement rises from EUR 3,311 to EUR 4,101, **+23.8 per cent**, and the product of
the two is 0.999 against a total that moves 0.999. The total cannot move because it is the
target.

**So this is a documented modelling convention, not a defect.** Spain's minimum income is
calibrated to an external expenditure total and therefore **cannot respond to a shock by
construction**. The right way to report the Spanish shock scenarios' benefit response is
that the minimum income component is **held fixed by calibration**, which is more specific
and more useful than either "small" or "not modelled".

**Italy and Greece are the control, and both behave as their own settings predict.**

| | BTA | BCA | rate | target | outlay | `ils_ben` at unemployment +10pp |
|---|---|---|---|---:|---:|---:|
| Spain | on | on | 0.44 | 2,504 | 2,479.3, **-0.99%, target not reached** | +29.7m, IMV **-2.5m** |
| Italy | **off** | **off** | not applied | 6,653 | 8,853.8, free | +4,192.8m, AdI **+4,346.9m** |
| Greece | on | on | 1 | 520 | 495.7, **-4.67%, target not reached** | +278.5m, KEA **+45.0m** |

**The Spanish label weakens this section's argument.** The
row read **pinned** until then. That was computed on a superseded outlay of 2,502.5, which is
99.94 per cent of the target; the current 2,479.3 is 99.01 per cent of it and fails the same
`outlay >= target * 0.995` test that puts Greece in the not-reached column at 95.33 per cent.
Calling one of them pinned and the other unreached could not survive both being scored by the
same rule. `europe/docs/benefit_adjustments.json` now carries `target_binds: false` for Spain,
with the origin of the change in its own note.

What survives the correction, and it is most of it. The take rule set out below is
`i_bsa00_bca_take = bsa00_s > 0 & i_bsa00_cumexp <= $bsa00_targetBCA_amt`: a cumulative
weighted sum taken while it stays **at or below** the target. **The calibration can therefore
only ever land under the target, never on or above it**, so an undershoot is what binding looks
like and not evidence against it, and the 0.995 threshold is a tolerance for how far under
still counts rather than anything the model sets. The mechanism below is unaffected, and so is
the explanation of the flatness. Italy runs neither adjustment, so its AdI is unconstrained and
moves by EUR 4.3bn. Greece runs both, falls 4.67 per cent short, every eligible household is
paid, and its KEA moves freely (9.9). Spain runs both, falls 0.99 per cent short, and does not
move. **There is no clean binary.** On one shared rule Spain and Greece sit
on the same side of it and behave differently, so what separates them is how far short each
lands, which is a matter of degree and not of a switch. The one thing genuinely left open is
which of the two caps is the operative minimum for Spain, the applied rate being
`min($bsa00_BCA_rate,$bsa00_BTA_rate)` with the take-up rate at 0.44; that needs the matched
engine and cannot be decided in a verification tree.

Part of the original diagnosis stands and is still relevant. `les` is read by no live
policy in the Spanish model, contributory unemployment eligibility runs off `lunmy`,
the months-unemployed count, which the shock does not change, and the one place Spain
tests `les = 5` is switched off in ES_2023. That is why the contributory unemployment
benefit does not respond either; it is not the reason the IMV does not.

**One consequence worth stating**, because it was met independently and from the other
direction: the same mechanism makes Spain's `min_income_up` dial **non-monotonic under
base-amount scaling**. Scaling `$bsa00_amt` raises entitlement per unit, the same monetary
target is exhausted after fewer units, and the dial's cost bounces between EUR 0.5m and
EUR 39m across the whole magnitude range instead of rising. That is why the shipped Spanish
dial uses the income-floor topup lever, which holds eligibility at baseline and produces the
clean EUR 125m to EUR 1,251m grid. `build_grid.py`'s note that topup is "used only where
base-scaling is non-monotone" had never said WHY, and this is why.

### 9.3 The three sourced UK unit costs, now checked against their publications  [CLOSED]

Children's social care, drug and alcohol treatment, and additional GP consultations
each carry a full derivation in their own note: a source, a page or table reference, a
base year, and a deflator series. Each derivation was checked for internal consistency
and reproduces the figure on disk. **Each of the three publications has
been opened**: the audit compared the tool against the registry and against the note, and
did not verify that the note described the source correctly.

All three have now been verified against the publications themselves. **No value moved.**
Three note corrections followed, and they are the substance of this entry.

* **Children's social care.** The note claimed the source separates children in need from
  looked-after children. It does not. The two unit costs in Table 10 are separately
  derived, from distinct expenditure lines, but the populations overlap: the report states
  that looked-after children are a subset of children in need, and that GBP 8,640 is the
  basic level of safeguarding costed for every child in need, with looked-after children
  additionally attracting GBP 45,085. GBP 8,640 is therefore not a
  children-in-need-excluding-looked-after figure. Applying it as a community-support cost
  per child in need mirrors the source's own additive treatment and is defensible; claiming
  the source nets the subset out was not.
* **Drug and alcohol treatment — a scope mismatch, the largest of the three.** Nothing in
  the source covers alcohol. Figure 5 is drug treatment budgets, the corroborating
  paragraph refers to adult drug treatment, and the agency's remit as the report states it
  is treatment for drug dependency in England. The parameter is labelled drug and alcohol
  treatment on all four tools, so applying this unit cost to a combined population is an
  extrapolation beyond the population it was measured on. It is now caveated as one on all
  four faces; the three EU editions convert the same figure and inherit it. Two further
  corrections: the definition of effective treatment is at note 2, not note 1, and is
  three-part, the third limb admitting adults discharged within twelve weeks in a planned
  way, so the "12+ weeks" shorthand overstated the treatment intensity the denominator
  represents; and GBP 3,000 is the source's own rounding of GBP 2,979, so the shipped
  figure inherits about 0.7 per cent of upward rounding from the source. The same report
  gives a genuinely costed unit price of GBP 4,900 at paragraph 18, from a treatment
  outcomes study, a different concept sitting GBP 1,900 away in the same document; the
  budget-based figure was taken in preference to it, deliberately, and the note now says so.
* **GP consultation.** No correction. One fact added: the manual's own footnote records
  that previous editions used 9.22 minutes per consultation, so the ten-minute basis is new
  to this edition and GBP 49 is not like-for-like with a per-consultation figure from an
  earlier manual.

The other seven UK unit costs are assumptions stated at the panel's own base and make no
source claim to check.

### 9.7 Self-employed contributions: how much of a displayed figure rests on them  [OPEN]

`ES-1` (+18.5 per cent), `IT-3` (+93.8 per cent) and `EL-3` (−25.0 per cent) record how far
each country's self-employed contributions sit from the published EUROMOD baseline. What none
of them recorded is **how much of a figure a reader actually sees rests on that divergence.**
Measured by `europe/model/selfemp_sic_share.py`; it reproduces every one of the twenty-one shipped surface points it
measures, exactly, so it is on the same footing as the surface.

**Re-measured after the Spanish rebuild of the same day.** The table below is the second
measurement. Spain's divergence fell from +41.3 to +18.5 per cent when `ysemy` was corrected
(9.13) and its exposure roughly halved with it; the Italian and Greek rows are unchanged to
the decimal, which is the control on the re-measurement.

**Where a reader meets it.** The Analyst tab row *Employee social contributions change* and
the Scenarios tab row *Employee SIC change* both render `sic_delta_m`, which is `ils_sicdy`:
employee **plus self-employed plus other**. The label names only the employee leg. The UK
label, *Employee and self-employed NI change*, names both. `sic_delta_m` also enters
`net_exchequer_cost_m`, the headline fiscal figure on both tabs and the denominator of the
cost-effectiveness ratio and of the Scenarios spine card.

**Which dials.** Only the two shock dials. `pit_give`, `child_benefit_up` and `min_income_up`
carry `sic_delta_m` identically zero at every point in all three countries, which `re_emit.py`
already asserts for two of them. On the Scenarios tab that means the five shock scenarios and
no policy scenario.

**Sizes**, as a share of the displayed net exchequer cost:

| | self-employed leg, share of the contributions row | share of the net exchequer cost | of which attributable to the divergence |
|---|---|---|---|
| IT, earnings downturn | 33.7% to 36.0% | 6.00% to 6.19% | **2.90% to 3.00%** |
| IT, unemployment shock | 44.4% to 48.7% | 7.14% to 8.05% | **3.45% to 3.90%** |
| ES, earnings downturn | 10.1% to 12.1% | 0.84% to 1.05% | 0.13% to 0.16% |
| ES, unemployment shock | 32.4% to 33.9% | 5.19% to 5.49% | 0.81% to 0.86% |
| EL, earnings downturn | 0.2% to 2.1% | 0.04% to 0.38% | 0.01% to 0.13% |
| EL, unemployment shock | 3.2% to 3.9% | 0.76% to 0.93% | 0.25% to 0.31% |

**Only the excess column moves with the re-measurement**, which is the check on the
re-measurement: the share columns are properties of the run and the excess column is the only
one that reads a published figure. Italy's fell from 4.91-5.06 and 5.84-6.59 when its
comparator was corrected from a payer count to an amount, and Greece's rose slightly, from
0.01-0.11 and 0.22-0.27, when its comparator gained the component it had dropped. Greece's
rising is the expected direction: its divergence runs the other way, so completing the
published sum widens it.

The last column is a proportional attribution, not a re-simulation: it is the self-employed
change scaled by the baseline shortfall against the published figure, and says what the change
would have been had the contribution base been at its published level and responded in the same
proportion. It is a bound, not a correction, and no correction has been applied.

**What this establishes.** Italy's **+93.8 per cent** is the largest divergence in the
deliverable and it reaches **3 to 4 per cent** of the headline fiscal cost on the two shock
dials. Spain's **+18.5 per cent reaches 0.86 per cent at most**, down from 1.64 per cent
before `ysemy` was corrected. Greece's **−25.0 per cent** reaches 0.31 per cent at most.

**BOTH JUDGEMENTS ARE NOW SETTLED, 2026-08-03.**

**The Italian caveat is KEPT, restated.** It was written when the exposure was 5 to 7 per cent
of the displayed headline cost; after the payer-count correction it is 3 to 4. Spain's 1.6 per
cent was judged not to warrant a face note, and **3 to 4 sits above that and above several
residuals that do carry one**, so consistency keeps it. It now leads with the finding rather
than with the history of the error, states the divergence as **93.8 per cent** and the exposure
as **2.9 to 3.0 per cent** on the earnings downturn and **3.5 to 3.9 per cent** on the
unemployment shock, and says in its own words why it survives at the lower number. Greece's
self-employed leg is **25.0** per cent below its published line, which is what `EL-3`
carries.

**The contributions row label needs nothing, because it was fixed on 2026-08-03 and this entry
never caught up.** All three EU blocks read *Employee and self-employed social contributions
change* on the Analyst tab and *Employee and self-employed SIC change* on the Scenarios tab,
which is the UK row's own construction, *Employee and self-employed NI change*. It is applied, and it ships: the string is in
every EU tool. A row named for one component while containing two is mislabelled whatever the
size of the second, so there is no threshold question here: the label is either right or it is
not.

### 9.8 Greece's employer contributions were compared against the wrong concept; they are 5.7 per cent ABOVE the model's own baseline  [CLOSED]

**The premise of this entry was false and the entry is withdrawn.** It read: Greece's
simulated employer contributions are EUR 11,434.2m against the EUR 16,850m EU-SILC itself
records in `PY030G`, 32.1 per cent below, unexplained, and the largest of Greece's three
contribution gaps. It said the Greek Country Report publishes no `ils_sicer` baseline, so the
survey line was the only external check there is.

**The Country Report does publish one**, and the like-for-like sweep found it the same day
(`LIKE_FOR_LIKE_SWEEP.md` section 2). Table A3.4 publishes `ils_sicer` as its five components,
exactly as it publishes the employee list, and `ils_sicer` in `EL_2023` has exactly those five
members and no others, so the sum IS the list:

| component | published, 2023 | this build |
|---|---:|---:|
| employer SIC: pension (`tscerpi_s`) | 8,293 | 8,345.1 |
| employer SIC: sickness (`tscersi_s`) | 1,928 | 2,358.3 |
| employer SIC: unemployment (`tscerui_s`) | 509 | 622.0 |
| employer SIC: family benefits (`tscerfa_s`) | 0 | 0.0 |
| employer SIC: other benefits (`tscerot_s`) | 89 | 108.8 |
| **`ils_sicer`** | **10,819** | **11,434.2** |

**Restated: +5.7 per cent above the model's own published baseline, not 32.1 per cent below a
survey total.** That puts Greece in line with Spain at -1.3 per cent and Italy at +0.7 per
cent, and makes it the third employer-contribution line in the deliverable to land within six
per cent of its published baseline. It is not the largest of Greece's three contribution gaps;
it is the smallest, against the employee leg at -13.2 per cent and the self-employed leg at
-25.0 per cent.

`PY030G` is the survey's record of what employers paid across every scheme; `ils_sicer` is five
simulated schemes. They were never the same quantity. The -32.1 per cent is a real difference
between a simulated subset and a survey total and belongs in the record as that, not as an
unexplained shortfall against a baseline. `EL-7`'s IKA fund-split approximation was offered
here as a candidate cause and is not needed: there is no 32 per cent gap to explain.

The exposure figures stand as measured. `sic_employer_delta_m` still renders as *Employer
social contributions change* and still accounts for 28.0 to 28.5 per cent of the displayed net
exchequer cost on the earnings downturn and 29.2 to 38.2 per cent on the unemployment shock,
and it is still the single largest component of the Greek shock cost after the benefit
response. What has changed is that the quantity behind it is accurate to 5.7 per cent rather
than adrift by a third.

**Removed from the unexplained list.** With 9.2 and 9.9 closing on the same day, what carries
`[OPEN, unexplained]` in this section is now **9.10**, Italy's EUR 8.3bn income tax residual,
and **9.13**, Spain's EUR 2,688m self-employed contributions residual. `ES-2`, Spain's income
tax straddling its two comparators, is the third unexplained item and sits in the country table
rather than here.

### 9.9 Greece's minimum income dial sits below the published spend, and the missing asset test would take it further below  [CLOSED, direction established]

The KEA dial's means test has an asset leg that cannot be applied: the test reads the floor
area of the main residence and the public release does not carry it, so no household is
excluded on property. Section 8.5 sizes that as an **overstatement of roughly 13 per cent**,
and the arithmetic of the 13 per cent holds. **The overstatement conclusion is wrong in
sign**, which is why neither the tool face nor this entry states it.

Three figures, all of them cells of the same row of the same table (Y16_CR_EL table A3.6),
so the scheme, the year, and the concept are identical and the comparison is like for like:

| figure | EUR m, 2023 | against the published spend |
|---|---:|---:|
| published external spend, sourced to the Greek General Accounting Office | **520.0** | - |
| this build | **495.7** | -4.7% |
| EUROMOD's own simulation (`bsa00_s`) | **426.0** | -18.1% |

**The published figure is the target, not merely a comparator.** Greece runs both of
EUROMOD's benefit adjustments on this instrument: `BTA` and `BCA` are switched **on** for
`EL_2023` on `EL_2024_c1_2015_03_e2`, `$bsa00_BTA_rate = 1`, and
`$bsa00_targetBCA_amt = $extstat_amount_bsa00_s * 1000000/12`, which resolves to the
**EUR 520m GAO figure** in the country's own `<ExternalStatistic>` table. The calibration
therefore aims at exactly the published spend and **does not reach it**: because the modelled
outlay stays under the target the cap never binds, every eligible household is paid, and the
build lands 4.7 per cent short. Read from the model by `europe/model/benefit_adjustments.py`,
which also writes `benefit_adjustments.json`.

Given that, the direction follows. An asset test can only remove eligible units, so applying
the missing floor-area leg would move the dial **further below** the published spend, not
closer to it. On the measured 8.9 to 16.7 per cent of outlay, the
result would be **EUR 413m to EUR 452m**, a range that brackets EUROMOD's own EUR 426m and
sits further from EUR 520m than this build does. That the two simulations differ by about
what the missing leg is worth is consistent with EUROMOD applying it and this build not, and
neither of them reaches the published spend.

The earlier entry treated EUROMOD's own 426 as a second comparator pointing the other way,
and concluded that the two "point in opposite directions and there is no basis for choosing
between them". That was the error. EUROMOD's figure is not a target; it is another simulation
of the same scheme, under-reaching the same published figure by more. The direction of the
net error is downwards, it is stated as downwards on the dial's own face, and this entry is
closed.

Section 8.5's Greek percentage is measured against the pre-conversion caseload, and its
overstatement conclusion is the one this entry withdraws.

### 9.10 Italy's income tax residual: EUR 8.3bn is unaccounted for by either bounded mechanism, and part of it is a property of the bound  [OPEN, unexplained, qualified]

Italian national income tax is **EUR 54,459m above the model's own published baseline**
(`tinna_s`, Y16_CR_IT table A3.4). Two mechanisms are bounded in `BASELINE_VALIDATION.md`: the
tax-compliance adjustment that cannot run because its inputs are national imputations, worth
EUR 28,318m at the level the country report implies, and the flat-tax regime that never fires
(`IT-11`), worth EUR 27,803m at its own ceiling. **Taken together at their maximum the two
close EUR 46,121m, and EUR 8.3bn of the gap remains unexplained by either.** Nobody has
established what it is. Both mechanisms are bounds rather than corrections, no adjustment has
been applied, and scaling the output to the published aggregate was considered and rejected
because it would fit the total while misstating who pays.

> **SUPERSEDED 2026-08-03 by a third mechanism and a measured lattice. The EUR 8.3bn does
> not survive, in either direction.** `europe/model/it_credit_bound.py` measures all three
> mechanisms on the same input and runs every combination of them, so the corners are
> differences of runs rather than sums of separately recorded singles. Two results follow.
>
> **First, the recorded EUR 46,121m two-way does not reproduce.** The two singles do: the
> flat-tax bound is 27,802.9 against a recorded 27,803 at the codebook threshold, and the
> compliance bound is 28,285.2 against a recorded 28,318. But their sum is **56,088** and
> their **measured** two-way is **40,010**, and 46,121 is neither. The EUR 8.3bn residual is
> derived from the 46,121; on the measured two-way the residual is **EUR 14,449m**. The two
> mechanisms overlap heavily, because both act on self-employment income, which is why
> adding them overstates what they close by about 16bn.
>
> **Second, there is a third mechanism of the same kind and it closes most of what is left.**
> Every Italian income tax credit that runs off a claim selector is switched off for every
> household, because each selector is a national imputation the release does not carry. At
> the ceiling the credits close **EUR 13,113m**. All three together close **EUR 51,411m** at
> the codebook flat-tax threshold, leaving **EUR 3,048m**, or **EUR 54,191m** at the
> statutory 2023 threshold, leaving **EUR 267m** of a EUR 54,459m gap.
>
> The section below is left unedited as the record of the two-mechanism account. See 9.14.

**One qualification on the residual, and it makes the 8.3bn a weaker claim
than it reads.** The compliance bound was computed by applying a **uniform scale** to
self-employment income, taking the aggregate down to the level the country report implies.
The adjustment EUROMOD actually runs is nothing of the sort: `TCA_it` is a **household-level
imputation**, and it moves different households by different proportions. **Italian income
tax is progressive**, so a uniform scale and a household-level one that reach the same
aggregate self-employment income do **not** produce the same income tax. Which way the
difference runs depends on where in the distribution the real adjustment concentrates, and
that is exactly what the missing variables would tell us, so it is not signed here either.

The consequence is that **part of the EUR 8.3bn is a property of the bounding method rather
than an unexplained gap**. The bound is a bound on the aggregate base, not on the tax the
base produces, and it was being read as though it were the second. How much of the 8.3bn
that accounts for is not established, and establishing it would need `yseev` and `ysenr` at
household level, which is the same national-SILC wall that stops the adjustment running at
all. The item stays open on that basis: the residual is real, its size is uncertain by more
than the arithmetic suggests, and the uncertainty is in our method as well as in the model.

### 9.14 Italy's income tax credits: the third mechanism, and the lattice that replaces the EUR 8.3bn  [MEASURED, nothing applied]

> **RECONCILED AND SPLIT, later on 2026-08-03, by `europe/model/it_gap_reconcile.py`. Read
> this before the entry below, which is correct but incomplete in two ways that matter.**
>
> **1. There are two income tax quantities and they must never be mixed.** `tinna_s` is
> national IRPEF alone, the line Y16_CR_IT A3.4 publishes at EUR 200,784m, so it is the only
> correct basis for closing this gap. `ils_tax` is the whole income tax list, national IRPEF
> plus the regional surcharge plus the flat-tax regime's own revenue `tin00_s` plus the rest.
> Measured on both:
>
> | mechanism | on `tinna_s` | on `ils_tax` |
> |---|---:|---:|
> | compliance adjustment | **28,285.1** | 29,684.2 |
> | flat-tax regime, statutory EUR 85,000 | **33,351.4** | 15,874.9 |
> | flat-tax regime, codebook EUR 65,000 | 27,802.9 | 12,402.7 |
> | credits, all seven at their ceiling | **13,113.3** | 13,424.2 |
>
> For the compliance adjustment and the credits the two bases sit within 5 per cent of each
> other, because those mechanisms shrink the base. **For the flat-tax regime they diverge by
> a factor of more than two and in the direction opposite to intuition**, because the regime
> does not remove revenue, it MOVES it: `tinna_s` falls 33,351 while `tin00_s` rises from
> zero to 19,711, so the whole list falls by only 15,875. **A flat-tax figure near 15,875 is
> a whole-list figure and cannot be added to national-IRPEF figures for the other two.**
>
> **The sum on the national income tax basis is 28,285.1 + 33,351.4 + 13,113.3 =
> EUR 74,749.8m**, which is what the entry below reports. It was right.
>
> **2. The headline conflated a bound with an estimate, and the difference is EUR 16bn.**
> The compliance adjustment is what EUROMOD itself applies, so restoring it estimates an
> actual effect. The other two are ceilings: every eligible person electing, every eligible
> household claiming. Neither happens.
>
> | | closes | residual | share of the gap |
> |---|---:|---:|---:|
> | **the bound**, all three at maximum | **54,191.2** | **267.4** | 99.5% |
> | the bound at the codebook flat-tax threshold | 51,410.4 | 3,048.2 | 94.4% |
> | **the realistic point** | **37,873.3** | **16,585.3** | **69.5%** |
>
> The realistic point is built on Italy's own published figures, not on rates chosen here.
> The flat-tax regime is set to the **1.9 million electors Italy records against the 7.5
> million statutorily eligible in this build**, drawn on a fixed seed, which closes 8,018.1
> on `tinna_s` and 3,775.5 on `ils_tax`; Italy's own tax expenditure report puts the
> *regime forfetario* at **EUR 3,490.8m**, so the measured whole-list effect overshoots it by
> 8 per cent, which is the cross-check on the method. The credits are set to the
> **EUR 6,113.1m** the same report puts them at. Compliance keeps its full effect.
>
> **Adding the credits to the measured compliance-plus-flat-tax pair slightly overstates
> closure**, because the measured credit interaction against each of the other two runs at
> 0.8 to 1.6bn at the ceiling, so **EUR 16,585m is if anything a small under-estimate of the
> residual.**
>
> **The sentence for the report: the three mechanisms BOUND the Italian income tax gap
> rather than explain it.** At their maximum they close 99.5 per cent of it; at what Italy
> actually records, 69.5 per cent, and EUR 16.6bn remains unaccounted for.
>
> **One figure is retired.** A compliance figure of about **EUR 29,667m** has been in
> circulation; it is a **whole-list** measurement, reproducing here at 29,684.2 on `ils_tax`,
> and it must not be used in gap arithmetic. The compliance figure of record is
> **EUR 28,285.1m on `tinna_s`**, which also supersedes the EUR 28,318m in the older account.
> The EUR 46,121m two-way remains unreproducible on any basis: it is neither the sum of the
> two `tinna_s` singles (56,088 at the codebook threshold, differing by exactly 10,000, which
> is consistent with a transposed digit), nor the measured two-way (42,875.4 at the statutory
> threshold, 40,009.8 at the codebook one), nor the sum of the two `ils_tax` singles
> (45,559.1). It is retired in favour of the measured two-way.
>
> **The credit ceiling is sound in aggregate and under-bounded in three named arms.** At
> EUR 13,113.3m it is **2.15 times** the EUR 6,113.1m Italy reports these reliefs actually
> costing, which is the right side to be on for a ceiling. Per arm, against the Rapporto
> annuale sulle spese fiscali 2024:
>
> | our arm | ceiling | Italy reports | ratio |
> |---|---:|---:|---:|
> | health (`tintchl_s`) | 6,632.4 | 4,472.5 | 1.48 |
> | life insurance (`tintclf_s`) | 1,915.2 | 282.7 | 6.77 |
> | education (`tintcst_s`) | 565.5 | 675.7 | **0.84** |
> | funeral (`tintcfu_s`) | 0.0 | 163.1 | **0.00** |
> | childcare (`tintccd_s`) | 0.0 | 8.1 | **0.00** |
> | other arms (`tintcox_s` + `tintaox_s`) | 4,086.9 | not separately itemised | - |
>
> **Education is below what Italy reports actually being claimed**, because its branch
> carries a second gate, `(sin01_s#20 > 0)`, which only 2,437 records and 2.8m weighted
> households satisfy against Italy's 3.88m beneficiaries. **Funeral and childcare are zero
> because no branch of those functions runs on this dataset class at all**; their branches
> are gated to `IT_2006_*` and `IT_2007_*`. **The rent credit is excluded entirely**, because
> `tintc01_s = tintcho` is an input amount and the model carries no schedule; Italy reports it
> at **EUR 353.3m** for the main residence plus **EUR 96.5m** for student leases, so the
> exclusion is worth about **EUR 450m** and can now be stated rather than guessed. `xhcrt` is
> populated for Italy, so the credit is derivable if the statutory schedule is supplied.
> Together the under-bounded and excluded arms are worth about **EUR 0.7bn at Italy's actual
> rates**, which would raise the ceiling and leaves the aggregate verdict unchanged.

Measured by `europe/model/it_credit_bound.py`. **Nothing was
changed, applied or rebuilt.** The product is a bound for the technical report.

**The mechanism.** `SetDefault_it` sets `tintchlyn`, `tintcoxyn`, `tintclfyn`, `tintcstyn`,
`tintaoxyn`, `tintccdyn` and `tintcfuyn` to zero, because each is a national imputation the
public EU-SILC user database does not carry. Every credit's `Comp_Cond` opens with
`(tintXXXyn > 0)`, so **no household in this build claims any income tax credit.** Credits
reduce tax; all of them being off overstates it. Same class of cause as the other two, same
source, and acting on the same line:

    tinna_s = tintsna_s - tintc01_s - tintcst_s - tintcmi_s - tintchl_s
              - tintccd_s - tintcox_s - tintclf_s - tintcfu_s - tintc_s      (floored at 0)

**The bound.** Floor is the shipped build, every selector zero. Ceiling is every household
whose income band the credit's own schedule covers claiming it, which is what setting the
selector to one does. Deliberately generous: in reality only households that incurred the
expenditure claim. **No approximation was needed for the five rate-based credits**, and that
is a property of the 2017-onwards formulation rather than luck: each applies a rate directly
to `il_taxabley` in an income band, so the model has already done the imputation from
expenditure to income and there is no expenditure term left to approximate. Rates and bands
are read from the live `IT_2023` system.

| credit | selector | rate on `il_taxabley` | credit at the ceiling | households, records | households, weighted (k) | tax reduction |
|---|---|---|---:|---:|---:|---:|
| Health expenses | `tintchlyn` | 10.8% to 1.2% by band | 7,166.4 | 30,349 | 24,937.1 | **6,632.4** |
| Other-expense allowance | `tintaoxyn` | 3.11% to 1.5% by band | 10,592.9 | 30,349 | 24,937.1 | **3,038.0** |
| Life insurance | `tintclfyn` | 4.3% to 0.4% by band | 2,130.9 | 30,349 | 24,937.1 | **1,915.2** |
| Other expenses | `tintcoxyn` | 6.0% to 0.2% by band | 1,118.2 | 30,363 | 24,948.7 | **1,048.9** |
| Education and study | `tintcstyn` | banded, then ×0.19 | 1,325.6 | 2,437 | 2,813.9 | **565.5** |
| Childcare | `tintccdyn` | no branch runs on this dataset | 0.0 | 0 | 0.0 | **0.0** |
| Funeral expenses | `tintcfuyn` | no branch runs on this dataset | 0.0 | 0 | 0.0 | **0.0** |
| **All seven together** | | | | **30,450** | **25,060.0** | **13,113.4** |

The sum of the singles is 13,199.9 against 13,113.4 measured together, an interaction of
**86.5**, small because the credits are subtracted from one tax and only the floor at zero
makes them interact at all.

**One credit cannot be bounded from the model and is not guessed.** `tintc01_s = tintcho`,
the rent credit, is an input **amount** the model reads rather than a rate it applies, and
`SetDefault_it` sets it to zero. There is no schedule in the model to take rates or caps
from. The survey does carry rent (`xhcrt`), so a bound is derivable the moment the statutory
schedule is supplied from outside. It is therefore **absent from the 13,113.4**, which is to
that extent a lower bound on the ceiling.

**The corners, measured rather than assembled.** All three mechanisms applied to the same
input, every combination run. The gap is EUR 54,458.6m.

| corner | closes | `tinna_s` | vs published | share of gap |
|---|---:|---:|---:|---:|
| none of the three | 0.0 | 255,242.6 | +27.1% | 0.0% |
| credits | 13,113.4 | 242,129.3 | +20.6% | 24.1% |
| compliance | 28,285.2 | 226,957.5 | +13.0% | 51.9% |
| flat tax | 33,351.4 | 221,891.2 | +10.5% | 61.2% |
| compliance + credits | 40,579.3 | 214,663.4 | +6.9% | 74.5% |
| compliance + flat tax | 42,875.4 | 212,367.2 | +5.8% | 78.7% |
| flat tax + credits | 44,875.2 | 210,367.4 | +4.8% | 82.4% |
| **all three** | **54,191.2** | **201,051.4** | **+0.1%** | **99.5%** |

Sum of the three singles 74,750.0 against 54,191.2 together: **an interaction of 20,558.8**,
which is why the corners cannot be added. The compliance adjustment and the flat-tax regime
both act on self-employment income and overlap almost completely.

The flat-tax arm above uses the **statutory** EUR 85,000 threshold for the 2023 income year,
because a ceiling defined as "everyone statutorily eligible" has to. At the EUR 65,000 the
EUROMOD input data codebook records, the flat tax alone closes 27,802.9, the two-way closes
40,009.8, and all three close **51,410.5**, leaving **3,048.2**.

**What this does to the EUR 8.3bn. It does not survive, and the reason is not the third
mechanism.** The two recorded singles reproduce: 27,803 exactly at the codebook threshold and
28,318 to within 0.1 per cent. Their **two-way** does not. Their sum is 56,088 and their
measured two-way is 40,010, and the recorded **46,121 is neither**. The EUR 8.3bn is derived
from the 46,121; on the measured two-way the residual after those two mechanisms is
**EUR 14,449m**, not 8,338.

So the honest statement for the report is: **two mechanisms leave about EUR 14.4bn, and the
third takes it to about EUR 3.0bn at the codebook threshold or about EUR 0.3bn at the
statutory one.** The three together account for essentially the whole gap at their maximum.

**These are bounds, not corrections, and the qualification at 9.10 applies to all three.**
The compliance arm is still a uniform scale standing in for a household-level imputation
under a progressive schedule; the flat-tax arm still puts 7,968 records into a regime about
1.9 million of Italy's 7.5 million eligible taxpayers actually elected; and the credit arm
still has every eligible household claiming. Nothing has been applied to the build, no
surface has moved, and the shipped Italian income tax is unchanged at EUR 255,242.6m.


### 9.13 Spain's self-employed contributions: EUR 2,688m remains after the months multiplier is fixed  [OPEN, unexplained]

**This is not an input-completeness item and must not be filed as one.**
Every input the calculation reads is populated, and each from a recipe the EUROMOD input data
codebook publishes for Spain. It is a residual with a size and no established cause.

**What it was.** Spain's self-employed contributions read **EUR 20,566.8m against a published
EUR 14,551m, +41.3 per cent** (`ES-1`), while self-employment income itself and the payer count
both matched the published figures to four decimal places. A level error confined to one line,
with its own base and its own headcount both correct, points at a multiplier.

**What it was, mechanically.** `convert_full.py` set `ysemy`, the self-employed
months-of-receipt count, to **12 unconditionally** for everyone with self-employment income.
Contributions scale directly with it. The months-worked variable that should have supplied it
was present, populated, and used one line above for the employee equivalent, `yemmy`. Among the
5,721 records carrying self-employment income it means **9.853 months** on the clip `yemmy`
uses, and **22.4 per cent of them are below a full year**, so the unconditional 12 charged a
full year of contributions to people the survey records as having worked less than one. The
fix was transcription: `ysemy` now reads the same variable on the same clip.

**What it is now.** **EUR 17,238.9m against the same published EUR 14,551m, +18.5 per cent.**
The line fell 16.2 per cent, slightly less than the 17.9 per cent the mean months alone imply,
because the RETA carries a statutory minimum contribution base that does not scale with months.
Its exposure on the tool face fell with it, from 1.64 to **0.86 per cent** of the displayed net
exchequer cost at worst (9.7).

**The residual is EUR 2,688m and it is unexplained.** `ES-1`'s standing hypothesis is the
chosen-base and under-declaration behaviour that the public EU-SILC release cannot carry, and
it remains the only candidate on the table, but **nobody has measured how much of the
EUR 2,688m it accounts for**, and EUROMOD's own documentation notes that the official Spanish
model over-states contributions under a full-compliance assumption, which would put part of the
residual in the published baseline rather than in this build. No adjustment has been applied.

Recorded here rather than in section 10 for the reason stated at the top of this entry: the
input-completeness list is a list of variables the release does not carry, and this is not one.

### 9.4 What a provider case is: resolved in people, and the conversion is on the face  [CLOSED]

The capacity panel multiplied a catchment the user enters in **people** by a national
affected fraction that is a share of **units**, and by a per-**unit** money figure. Each
side was internally consistent, the audit's F1 and F2 record how each was made so, and the
two did not describe the same objects. It was the largest open question in the provider
layer.

**Resolved in people rather than in units**, for three reasons that are about the user and
not about the arithmetic. A provider knows how many people they saw and what it cost, and
does not hold a caseload in households, so asking them to convert would push the error onto
them. Almost every service in the registry counts individuals. And the catchment field
already asks for people, so the question put to the user does not change at all.

**No new parameter and no assumption.** The conversion is each country's own average
household size, which the surface already carries as `population_basis.population_k /
population_basis.units_k`, on the surface's own scope: the UK's are working-age benefit
units and the people in them, the EU's are all households and all people.

| | population | units | people per unit |
|---|---:|---:|---:|
| UK | 46,068.2k | 21,443.5k benefit units | **2.1484** |
| Spain | 48,264.2k | 19,316.7k households | **2.4986** |
| Italy | 58,664.5k | 26,206.6k households | **2.2385** |
| Greece | 10,187.9k | 4,298.1k households | **2.3703** |

**Two rates convert and nothing else does.** `affFrac`, the share losing an earner, from a
share of units to a share of people; and `pbW`/`pbU`, the decile-derived value, from per
unit to per person. The outcome values are already published per person helped and the
service unit cost is a cost per case, which is a person, so neither moves. **Kappa is the
ratio `pbW/pbU` and is therefore exactly invariant**: the distributional weight does not
change, only the level.

**What moved on the face**, at the shipped defaults of 500 people and a 4pp shock. Extra and
unmet demand fall by the household-size factor; extra budget with them; the cash floor and
engine income halve or better, and the headline falls by that much because the outcome rows
do not move. The UK moves proportionally most, because its value ladder is dominated by the
cash floor where the three EU ladders are dominated by outcome rows: **the UK benefit-cost
ratio goes from 0.90 to 0.42 and so crosses 1**, which is a real change in what a UK debt
advice provider reads at the default catchment. Extra caseworkers does not move at the
default scale, because both sides round to one worker; at a 20,000-person catchment it does,
UK 400 to 395 and the three EU tools 402 to 395 or 396.

**Stated on the face.** The catchment input says individual people and not households; the
catchment row names the conversion factor and where it comes from; and a panel note says
every figure is per person.

**One thing recorded rather than solved.** A few services are naturally household-based,
food aid and housing support especially, and a provider may hold a cost per household for
them. The tool offers **one** unit rather than two, and says so plainly with the instruction
to divide by their own household size first. Two units on one panel would be a worse answer
than one clear one.

### 9.5 Forty-six numeric paths in the country blocks have no reader  [known, deliberate]

Enumerated in the provider parameter audit table 7.12. They are staying. Removing them
would mean regenerating four country blocks and re-instantiating four tools for no
change to anything the tools compute, and every regeneration is an opportunity to ship
a page holding a stale grid, which is the standing hazard this project guards against.
`staffRatio` joined the list when the staffing recommendation was fixed to use the
provider's own throughput. They are documented, they are inert, and this note is the
record that they are deliberate rather than overlooked.


### 9.12 How much of a panel a caveat may occupy, and where the rest goes  [rule, checked]

Every open item above has to reach a reader, and by 2026-08-03 the aggregate of them had
stopped communicating. Measured on the Italian Analyst tab with the child-benefit dial at
+50 per cent: the headline welfare figure occupied **32 pixels** and the caveat below it
occupied **303**, nine and a half times the height of the number it qualified. The Italian
tool carried 941 words of caveat against 1,435 words of description, and the employer
contribution gloss, 309 words, was rendered **between the rows of the four-row fiscal
table**, pushing the net-cost headline more than 300 pixels from the rows it totals. On the
Greek Analyst tab the same 41-word sentence about self-employment under-capture appeared
**five times on one screen**, 205 of 1,218 words.

That is a presentation failure rather than caution, and it is now bounded by three rules.
None of them removes a word: everything that was on a face is still on that face.

1. **A dial caveat's VISIBLE part may not exceed 1.4 times the words in that dial's own
   description of what it does.** A ratio rather than an absolute, because a dial that
   needs seventy words to explain itself can carry a longer qualification than one that
   needs thirty. The visible part carries the **direction and the size** of the error,
   which is what a reader needs beside the figure; the derivation goes behind a closed
   disclosure that states how many more words it holds. `check_drift.py` asserts the cap
   (`check_caveat_length`, `CAVEAT_WORD_RATIO = 1.4`), so the rule is checkable rather than
   remembered.
2. **A fiscal row gloss longer than fourteen words is a footnote, not a label.** Above that
   it is collected below the card behind a numbered disclosure, and the row carries a
   superscript. Four figures then read as four figures.
3. **A limitation is printed once per screen.** The Greek self-employment note is on the
   two shock dials' own descriptions, where the lever it qualifies is, and nowhere else on
   that screen: it came off both winners-and-losers panels, off five scenario duplicates,
   and off the fiscal-card caveat that repeated the dial description directly above it.

After: the child-benefit caveat is **80 pixels** against the same 32-pixel headline, from
303. The Greek Analyst screen carries the note **twice, once per shock dial**, from five,
and the Scenarios screen **once**, from three. Nothing collapsed is hidden from search or
print: the text is in the document and `@media print` opens every disclosure.

### 9.11 The decisions, recorded as decisions rather than as omissions  [deliberate]

Six things in this deliverable are the way they are because somebody chose, not because
something was missing. They are collected here so that a reader does not read a choice as a
gap.

1. **The population bases differ between the four tools, deliberately.** The UK is
   working-age units only, meaning benefit units with at least one adult aged 18 to 64,
   excluding units in which every adult is 65 or over: 46.1m people in 21.4m units. The three
   EU tools are all households with no age filter: ES 48.3m in 19.3m, IT 58.7m in 26.2m, EL
   10.2m in 4.3m. They were not harmonised because harmonising would mean rebuilding either
   the UK surface on a household basis or the three EU surfaces on a working-age basis, and
   each surface is validated against a different published baseline on its own basis. Every
   panel that prints a level states its own basis and says the four are not comparable across
   tools, which is the consequence the decision has to carry.
2. **There is no country selector.** Four separate self-contained HTML files, not one tool
   with a country dropdown. A selector would require one page to hold four surfaces, four
   provider registries and four currency and locale settings, and the standing hazard in this
   project is a page holding a stale grid. Four files, each with its own drift check against
   its own canonical JSON, is the form that makes that checkable. The cost is that a reader
   comparing countries must open four files, and the basis sentence on every panel is there
   because of it.
3. **The scenario menus are not the same across countries, and are not meant to be.** The UK
   has the baseline plus fifteen fixed scenarios and a binary toggle, the EU tools the baseline
   plus twelve or thirteen and no toggle, because the dial sets differ and each menu is drawn from its own country's dials.
   Two UK scenarios are combinations and two sit at a magnitude their dial does not carry, so
   four of the fifteen have no stored grid point; their poverty rows are gated to blank rather than shown on another basis
   (AUDIT §8 item 17).
4. **Forty-six numeric paths in the country blocks have no reader.** Enumerated in
   the provider parameter audit table 7.12, and kept. Removing them would mean regenerating four
   country blocks and re-instantiating four tools for no change to anything the tools compute,
   and every regeneration is an opportunity to ship a page holding a stale grid. See 9.5.
5. **Financial capital is derived for Spain and declined for Greece, on the same recipe, and
   the grounds for both are set out here.** The EUROMOD input data codebook
   publishes an `afc` recipe for both. **Neither decision rests on the minimum income
   aggregate any more, and neither should have.**

   **Spain: derived and shipped.** The IMV means test reads it. The old ground was that the
   modelled outlay lands within 0.1 per cent of the EUR 2,504m the scheme is published as
   spending. **That was circular**: EUR 2,504m is the target of the Benefit Calibration
   Adjustment, which is on for this system and dataset, so the outlay could not have landed
   anywhere else and the test could not have failed. The grounds that stand are that the
   recipe is published in the codebook for Spain, so it is the model's own rule and not a
   convention of ours; and that zero is the more extreme of the two assumptions available,
   because `afc = (yiy*12)/r` makes `afc = 0` the implication of an infinite return on
   capital. What the derivation moves is the composition of the recipient set, not the total,
   and the size of that compositional move has not been measured.

   **Greece: implemented, measured, and not shipped.** The old ground was that the derivation
   moves the KEA aggregate away from the published EUR 520m. **That test cannot discriminate
   here** for the reason 9.9 sets out: the build already sits below the published spend and an
   asset test can only remove recipients, so any asset test at all moves it further away. The
   ground that stands is about the input: Greek investment income is captured at **0.05** of
   the external figure in the same country report, against **0.57** for Spain, so capitalising
   it produces a stock that is wrong by construction rather than merely imprecise.

   Both decisions are unchanged, both are stated on their own dial's face, and only their
   grounds have moved. See
   `europe/model/benefit_adjustments.py`.
6. **Italy's minimum income lever is not the same experiment as Spain's and Greece's.** Italy
   scales the AdI base amount, which models both a higher payment to existing recipients and
   newly-eligible households entering the scheme; Spain and Greece top up existing recipients
   with eligibility held fixed. Take-up-expansion modelling for ES and EL is out of scope. The
   Italian dial says so on its own face, and its welfare and fiscal effects are correspondingly
   larger, which is why the AdI spine result is not read across to the other two.

### 9.6 The completed conversion, and what it changes in this document

Section 10 records the input conversion being completed. It changes several entries above,
and each has been amended in place with a dated note rather than rewritten, so the record
of what was believed when still reads: **EL-4** is closed, **ES-3** is restated on a
like-for-like comparison, **1.7** loses its double-counting rationale and gains the
household-allocation substitution, **IT-9** and **IT-10** are new. Section 8's measured
percentages are computed against the pre-conversion eligible populations; the figures that
hold on the shipped caseload are the ones at the head of section 8.

---

## 10. The completed input conversion

Every input variable a live 2023 policy reads, for which the EUROMOD input data codebook
publishes a recipe for that country and whose source fields the public EU-SILC user
database carries, is now populated from that recipe. Each case was decided by the inventory
generated by `europe/model/input_inventory.py`; what
was populated and from where is `CONVERSION_RECORD.md`; the acceptance test is
`BASELINE_VALIDATION.md`.

**Method, in one line.** The read-list is the engine's own — feed it a frame carrying only
the identifiers and the weight, and its `not found in user-provided lists` warning IS the
executed spine's read-list — and each variable on it was then classified by reading the
codebook recipe against the release's actual column list.

**Counts.** Populated columns in the converted frame: Spain 41 to 68, Italy 36 to 44,
Greece 41 to 55.

**What remains absent, and why.** Three reasons, in order of how much they cost:

1. **The recipe names a national-SILC or production variable.** This is almost all of it,
   and all but seven of Italy's. `bunct01` is `rmcig*cig_e`, `bchot` is `indmen*ind_e`,
   `afc` for Italy is "derived from national dataset", every Greek benefit component is a
   `kb02_`/`eu02_`/`sb02_`/`oe02_` national variable. Nothing can be done with the public
   release, and extending another country's recipe is forbidden.
2. **The release ships the column empty, or carries it at the wrong resolution.**
   `PL111A`, the NACE industry code, has zero non-missing values in all three countries.
   That kills `lindi` outright, which leaves Spain's agricultural contribution group unable
   to fire and the published Greek `lochz` fallback unable to be evaluated. **`drgn2`, the
   Greek NUTS-2 region code**, is the same class: `DB040` carries NUTS-1, the Greek model
   reads `drgn2` in one place, no dial or scenario depends on it, and the engine reports it
   as not found and uses zero, so every Greek household is assigned region zero. It has no
   consequence on any tool face. It is listed at 9.1 and
   is now a line here, because it is one absent variable among many and singling it out
   invited the question of why the others were not.
3. **The recipe stops short of a value.** Spain's `bch00`, `bchdi`, `ysv` and `bunncmy`
   each rest on a theoretical benefit amount the codebook describes but does not publish.
   Choosing one would be inventing it.

And one held back by decision rather than by data: the three asset variables, reported
rather than derived. For Spain and Greece the codebook does
publish an `afc` recipe, so this is a decision and not a ceiling, and the note says so.

**What it cost.** One figure moved away from its published baseline rather than towards
it: Italy's Assegno Unico. The ISEE deducts rent and mortgage interest, and those are now
populated, so the modelled ISEE falls and the allowance rises, from EUR 20,477m to
EUR 21,386m against an external EUR 17,382m. The property component that would push ISEE
the other way is exactly what section 8 says is missing, so the two halves of the ISEE are
now asymmetrically populated. That is a real cost of completing the conversion, it is
stated on the Italian child dial's own face, and it is the strongest argument for revisiting
the asset decision.
