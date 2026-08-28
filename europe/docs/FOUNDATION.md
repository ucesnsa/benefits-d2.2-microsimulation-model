# BENEFITS D2.2 EU Tool: Foundation (Master Document)

BENEFITS Horizon Europe D2.2, grant 101179032, Work Package 2. Single source of truth for the EU valuation tool (Spain, Italy, Greece) across both tabs (Analyst and Provider). This document **consolidates** existing material; it creates no new evidence and no new figures.

Sources consolidated: `PROVIDER_EVIDENCE_EU.md`, `PROVIDER_DECISIONS.md` and `PROVIDER_TOOLREADY_2024.md`, the validated `europe/<Country>/outputs/dial_grid.json` surfaces, and the verified EUROMOD dial baselines. Data-free: parameters, series, and citations only; no microdata.

---

## 1. Coverage map

Per country and service: **national** (country-specific figure), **transfer-from-X** (benefit-transfer, flagged), **derived**, or **EXCLUDED** (UNEVIDENCED). The Analyst dials are all country-specific by construction (each built on that country's own validated EUROMOD system).

| Service | ES | IT | EL |
|---|---|---|---|
| Employment | ENGINE national + WELLBY transfer | ENGINE national + WELLBY transfer | ENGINE national + WELLBY transfer |
| Minimum income / UC processing | ENGINE national; hardship **EXCLUDED** | ENGINE national; hardship **EXCLUDED** | ENGINE national; hardship **EXCLUDED** |
| Food aid / food banks | **EXCLUDED** | **EXCLUDED** | **EXCLUDED** |
| Debt advice | transfer (UK structure), WEAK | transfer, WEAK | transfer, WEAK |
| Talking therapies (IAPT) | **EXCLUDED** | **EXCLUDED** | **EXCLUDED** |
| Housing / homelessness | transfer-from-UK | transfer-from-UK | transfer-from-UK |
| Children's social care | transfer-from-IT | **national** | transfer-from-IT |
| Domestic abuse / GBV | **national** | **national** | transfer-from-IT (doubly flagged); EIGE aggregate = context only |
| Drug and alcohol | national VSL; mortality transfer | national VSL; mortality transfer | **derived** (income-scaled VSL); mortality transfer |
| Additional GP consultation | **national** | **national** | transfer-from-ES |

**Greece leans hardest on transfers.** Its only genuinely native provider cells are the minimum-income ENGINE effect (KEA) and the medication-only OST cost; its GBV (transfer-from-IT, itself doubly flagged), GP (transfer-from-ES), children's care (transfer-from-IT), housing (transfer-from-UK), VSL (income-scaled) and WELLBY (PPP transfer) are all transferred or derived. **Standing exclusions across all countries:** food aid, EU talking therapies, and the UC / minimum-income "averted hardship" unit value.

---

## 2. Provider layer

Two sub-layers, clearly separated. **Native-and-decided** (from `PROVIDER_EVIDENCE_EU.md`; native price years). **Tool-ready** (from `PROVIDER_TOOLREADY_2024.md`; 2024-equivalent, deflator-uprated then one HFCE-PPP step for transfers, single 2024 PPP round).

### 2a. Native-and-decided layer (native years; committed)
- **Employment:** +0.46 WELLBY, Britain fixed-effects unemployment-to-employment transfer (Clark, Flèche, Layard, Powdthavee and Ward 2018, Table 4.2); national ALMP qualitative warrant per country (ES Arranz 2024; IT RdC employment-neutral 2023; EL DYPA OECD 2024), no effect-size carried. STRONG effect.
- **Minimum income:** ENGINE (ES IMV, IT AdI, EL KEA); non-income hardship UNEVIDENCED-EXCLUDED.
- **Debt advice:** WELLBY, central ≈0 (Pleasence and Balmer 2007), high bound MaPS 2023/24; WEAK; transfer.
- **Talking therapies:** UK 0.71 WELLBY only; ES/IT/EL UNEVIDENCED-EXCLUDED (UK 0.71 not transferred).
- **Housing:** CONVENTIONAL; UK £20,128 (2015-16, Crisis/DCLG vignette); ES/IT/EL transfer.
- **Children's care:** CONVENTIONAL; IT €87,389 (2010, inferred lifetime PV, Bocconi 2013, not Ferrara; not €130,259); FGC 8.6pp effect transfer; ES/EL transfer-from-IT.
- **GBV:** ES €3,015m central gender violence / €4,933.22m tangible / €4,110m intangible (2022, Univ. Alcalá / Delegación; study does not sum, €9,043m composite superseded); IT €16,719,540,330 (2013, WeWorld); OR 0.43 central / 0.39 severe (Ramsay-Campbell 2009 / Rivas-Cochrane 2015); EL transfer-from-IT per-victim, EIGE €2.4bn aggregate context.
- **Drug:** VSL × averted-mortality; Sordo 2017 RR 3.20 transfer; ES/IT national VSL, EL income-scaled; OST costs ES €4/day (2004), EL €1.8/day (2009 medication-only), IT SERT per-capita (Insights 24 Ch.7 Table 7.8, 2013/14).
- **GP:** COST-INPUT, zero value-added; ES €14.78 (2008, Antares), IT €12 (2003, Garattini/DYSCO; €15.17 not used), EL transfer-from-ES.
- Attribution default 0.5 (0.3-0.7): the tool's own SROI-style assumption, not a GMCA default.

### 2b. Tool-ready layer (2024-equivalent)
2024-equivalent throughout. Deflators: ONS L8GG (UK); Eurostat `nama_10_gdp` B1GQ PD15_NAC (ES/IT/EL). PPP: single 2024 round — Eurostat `prc_ppp_ind` PPP_EU27_2020 E011 (euro area, primary); OECD `DF_TABLE4` v2.0 PPP_P31S14 XDC_USD (UK, named fallback). Spine £13,000 at 2019 prices, applied at 2024 prices as **£16,300**.

| Cell | ES (2024) | IT (2024) | EL (2024) | flag |
|---|---|---|---|---|
| WELLBY spine (central) | €14,050 | €14,925 | €13,317 | transfer-from-UK, PPP |
| Employment (0.46 × spine, **before the effect share and the attribution**; the shipped values are €427, €453 and €404) | €6,463 | €6,866 | €6,126 | rides-spine |
| Homelessness averted-cost | €23,262 | €24,712 | €22,049 | transfer-from-UK, PPP |
| Children's care (per averted entry) | €104,081 (from IT) | €111,665 (national) | €98,428 (from IT) | national / transfer-from-IT |
| GBV per-victim | €2,305.5 (national, tangible-only) | €17,756 (national, harm-inclusive) | €15,651 (transfer-from-IT, harm-inclusive; ES-alt €2,180) | national / transfer-from-IT |
| GBV aggregate (context) | €3,295.5m central / €5,392.9m tangible / €4,493.0m intangible | €20,419.4m | €2,832m (EIGE aggregate, not per-victim) | national / context |
| GP consultation | €18.47 (national) | €17.64 (national) | €17.47 (from ES) | national / transfer-from-ES |
| VSL (drug route) | €1.58-2.07m (national, uprated) | €1.46m / €3.24m / €8.09m (national) | €3.19m (income-scaled, derived) | national / derived |
| Drug averted-death rate | 24.8 per 1,000 OST patient-years (Sordo, transfer to all three) | | | derived / transfer |
| OST cost (documentary) | €5.75/day | SERT €4,463-4,720 excl / €32,084-31,408 incl | €2.07/day (medication-only) | national |

Deflator ratios and PPP factors are recorded per cell in `PROVIDER_TOOLREADY_2024.md`; the Greek VSL ingredients (base USD 3.6m 2005, US deflator 1.537958, GNI ratio 0.553359^0.8 = 0.622881, 2024 USD/EUR 1.0824) and the drug rate (36.1 − 11.3) are in its §3.

---

## 3. Analyst layer

### 3a. Dial set, baselines, on-face labels
Five dials per country. Magnitude grids: GDP shock 0 to −10% (step 1); tax first-bracket rate cut −5pp to +5pp (step 0.5, 21 points, two-sided); child and minimum income 0 to +50% (step 5); unemployment 0 to +10pp (step 1). Baselines are the verified EUROMOD constants (policy systems ES_2023 / IT_2023 / EL_2023, i.e. the 2023 policy year; year convention in §3e).

**Why five, and not the United Kingdom's seven.** `uc_taper` and `uc_work_allowance` are Universal Credit mechanics with no EU analogue, and `hicbc_removal` is a UK-only Child Benefit clawback with no EU instrument, so neither the two dials nor the toggle has a counterpart here. The Spanish IMV taper and earnings disregard are not dialled either: base-amount scaling through the means test and the regional-minimum coordination is structurally non-monotone and does not validate.


| Dial | ES baseline (lever) | IT baseline (lever) | EL baseline (lever) |
|---|---|---|---|
| GDP / market-income shock | market income (income_scale yem, yse) | market income (income_scale yem, yse, yseev) | market income (income_scale yem, yse, yemre, ysere) |
| Tax first-bracket rate cut | **9.5%** (tin_rate1; state first-bracket) | **23%** to €15,000 (tintsna_rate1 grp 9) | **9%** to €10,000 (tin00_rate1) |
| Child benefit | bch00 €1,000 / €5,439.60 / €588 per year (const_scale) | Assegno Unico max €189.18/month per child (bau_it BenCalc #_Amount) | A21 €70 / €140 per month (bch const_scale) |
| Minimum income | IMV base €6,784.44/year (bsa00_amt) | AdI base €6,000/year (bsa_Amount1) | KEA per-adult and per-child amounts (bsa00_adult_amt, bsa00_child_amt) |
| Unemployment shock | les-flip, +pp | les-flip, +pp (yseev zeroed) | les-flip, +pp (yemre, ysere zeroed) |

**Baseline figures above are human-reference values, not build inputs.** The build reads each parameter live from that country's EUROMOD system at runtime and stores only reform magnitudes and lever identifiers (`europe/common/config.py`, `europe/common/reforms.py`; runnable per-country copies under `europe/<Country>/model/pipeline/`), so a dial cannot drift from the national scheme by construction. ES and IT baselines are faithful by this verified live-read mechanism; EL's are additionally byte-proven on disk (`europe/common/build_summary.json`); an ES/IT build re-run remains available if byte-level confirmation is ever wanted.

On-face labels: "GDP / market-income shock"; ES "IRPF first-bracket rate cut", IT "IRPEF first-bracket rate cut", EL "PIT first-bracket rate cut"; ES "Means-tested child allowance (bch00)", IT "Assegno Unico Universale (bau_it)", EL "Child benefit A21 (bch)"; minimum income (see 3b); "Unemployment shock".

### 3a-bis. Instrument naming

Each country's minimum income is written by its **instrument code**: **IMV**, **AdI**, **KEA**. The Italian one had been written `ADI`, `AdI` and `ADI/RdC` in different places; **`AdI` is now the only form across the tree, the model and the tools**, and `RdC` is a different and superseded scheme rather than a spelling of this one, so the compound form is gone.

**Where the scheme name is written out, it is written as "Assegno di Inclusione (AdI)" and it is marked as this project's name for the instrument.** That marking is not politeness. What EUROMOD supplies is the instrument code **`bsamm_s`** and the constant **`$bsa_Amount1`** in system **IT_2023**, and those are the identifiers a reader can check; the scheme name is a gloss this project attaches, and the 2023 policy year sits across a period in which the Italian minimum-income scheme changed, which is exactly how `ADI/RdC` came to be written in the first place. Quote the code when a claim has to be checkable; quote the name only to be read.

The naming block sits in `europe/common/build_grid.py` beside `IMV_NAME`, and in the three per-country copies of that file. One string is deliberately left on the old form: `LABELS["IT"]["min_income_up"]`, which is the grid metadata the three shipped surfaces already carry. It reaches no tool face, the face reading `dial_text.label` and falling back to it only if that is absent, which it never is; changing it would put the code out of step with a surface this tree cannot rebuild.

### 3b. Minimum-income lever per country (not strictly comparable)
- **IT: base-amount scaling** (AdI, this project's name for it being Assegno di Inclusione). Models both the payment level and eligibility entry; standard label.
- **ES and EL: income-floor top-up** (IMV / KEA). Raises the guaranteed payment to existing recipients, eligibility held at baseline; on-face label "higher payment to existing recipients"; scope note: "does NOT model take-up expansion or newly-eligible entry."
- **Limitation to state in any cross-country framing:** the minimum-income dial is therefore **not strictly comparable across countries** (IT models eligibility entry; ES and EL do not). Base-amount scaling was retained for IT because it was monotone; ES and EL fell to the top-up because base-scaling was structurally non-monotone through the means-test / regional-minimum coordination.

### 3c. Response surfaces
Per country: **`europe/<Country>/outputs/dial_grid.json`** (ES, IT, EL) — the canonical, git-tracked copies of the validated surfaces — 5 dials × 11 magnitudes × 5-epsilon grid × 10 kappa-weighted decile contributions + winners/losers, EUR millions, EU-SILC 2024 wave (native nominal EUR; income reference year 2023; year convention in §3e). All **pass `europe/common/validate_grid.py`** (six checks; all five dials; Check 4 monotone), re-verified byte-identical in the tracked location. These are **aggregates only** (no microdata). The shared build code lives in `europe/common/` (with runnable per-country copies under `europe/<Country>/model/`); the tracked `europe/<Country>/outputs/dial_grid.json` copies are canonical (any surface a rebuild emits to a relative `europe/outputs/<CC>/` path is a non-canonical build artifact, not part of the shippable tree). The surfaces are referenced here, not reproduced.

### 3d. Analyst notes to surface on the tool
- **Tax-dial on-face labels (build requirement, all three countries).** Each tax dial must name the real national first-bracket rate it moves, and must keep the note that a first-bracket rate cut is used because no tax-free-allowance constant is exposed in the EUROMOD system (a documented substitution, not an allowance move):
  - ES: "IRPF state first-bracket rate (9.5%)", disambiguating the state rate from the combined statutory 19% (state 9.5% plus autonomic 9.5%).
  - IT: "IRPEF first-bracket rate (23%, to €15,000)".
  - EL: "PIT first-bracket rate (9%)".
  IT and EL inherit the same labelling discipline when their tool faces are built.
- **EL heaviest income-side caveat:** self-employment under-captures national accounts at 0.48× household B3G; the EL GDP-shock and unemployment-shock dials inherit this and it must surface on the tool.
- **EL smaller baseline:** net income ~€93.7bn, ~10,445 units (vs ES ~€673.4bn / 29,781; IT ~€883.2bn / 31,790). EL magnitudes read on their own scale and must not be flattened beside ES/IT.

### 3e. Year convention (standing rule; do not re-litigate)
**The tool references the EU-SILC wave year (2024 wave) as its single data-year anchor,** on the tool face and in all prose. The income reference year (2023) and the EUROMOD policy-system year (2023) are provenance: documented once, in the line below, and never used as the tool's data-year label.

**Provenance line (the single place the three years are stated together):** EU-SILC 2024 wave; income reference year 2023; EUROMOD policy system 2023 (ES_2023 / IT_2023 / EL_2023).

**Confirmed on disk (do not re-derive wrongly later).** The committed surfaces are built by `europe/common/build_grid.py` (runnable per-country copy at `europe/<Country>/model/build_grid.py`), whose `CC_CFG` runs the 2023 policy systems (`system=ES_2023/IT_2023/EL_2023`, passed to `engine.get_system`/`engine.run`) on the EU-SILC 2024-wave cross-sectional data (datasets `*_2024_*`; income reference year 2023). The `europe/common/build_summary.json` "EL_2024" label comes from a separate build, `europe/common/build.py` (2024 policy system, "locked 2024 system"), which emits only the six-scenario sign-check summary and did NOT produce the surfaces; the surface system year must not be read from it.

**Tool-face requirement (build).** Analyst mode shows the EU-SILC 2024 wave as its data-year label, never a bare collection year. Analyst monetary values are **2023 nominal EUR underlying, displayed uprated to 2024 EUR** by each country's own Eurostat `nama_10_gdp` PD15_NAC deflator (ES ×1.0289, EL ×1.0321, IT ×1.0197) — a **display-layer uprate**; the underlying surfaces stay 2023 nominal. Provider-mode monetary values are 2024-equivalent EUR. All four tools display 2024 EUR. ES first, then IT and EL, all follow this.

---

## 4. Decisions and method

**Settled provider decisions** (full text in `PROVIDER_DECISIONS.md`): employment +0.46 retained and relabelled (Britain FE transfer; years-2-5 removed; 0.7 rejected on estimand grounds); Spain GBV follow-the-study (central €3,015m; tangible €4,933.22m; intangible €4,110m separate; €9,043m composite superseded); one-route discipline; standing exclusions; GBV OR 0.43 central / 0.39 severe; drug route VSL × averted-mortality on the treated-cohort basis (24.8 per 1,000); housing CONVENTIONAL transfer (Hábitat not monetised, rescaling dropped); IT child-maltreatment incidence construction (€87,389 inferred, Bocconi not Ferrara, not €130,259); attribution 0.5 the tool's own SROI assumption; FRS SN 9367 1st Edition, DOI 10.5255/UKDA-SN-9367-1 (9256 alternative). Plus two further settled decisions: **spine on £16,300** (fn102), and **EL GBV per-victim = IT-transfer €15,652** (harm-inclusive).

**Uprating and PPP method, with citations:**
- Time-uprating on the GDP deflator (WHO-CHOICE 2003; ISPOR / *Value in Health* 2019).
- Order uprate-then-PPP (ISPOR).
- Household-final-consumption PPP for per-person value transfer (Eurostat / ILOSTAT), not GDP PPP.
- Single PPP vintage / round (ICP / World Bank) — the 2024 round throughout.
- WELLBY spine £13,000 at 2019 prices (HM Treasury 2021), applied at 2024 prices as £16,300 (HMT footnote-102 method).
- Greek VSL by income-elasticity scaling (OECD 2012, elasticity 0.8). **VSL uses income-scaling by OECD convention; the WELLBY uses PPP by health-economics convention — deliberately different methods, each following its source.**
- ALMP evidence is recorded as a **qualitative warrant only, no effect-size figure**; if a future technical-report evidence-table appendix needs an effect-size, it must be verified against source before use.

---

## 5. Open items
- **`valuation_tool.xlsx` DATA_SOURCES GMCA-0.5 string — FIXED (2026-07-04, hand-patched; committed since, and the workbook itself quarantined to `uk/tools/_superseded/` on 2026-08-01):** cell `E35` reworded from "GMCA CBA methodology; HMT Green Book additionality" to "Tool's own SROI-style modelling assumption, informed by Green Book additionality principles; not a GMCA default" (matches the corrected docs/HTML). Surgical shared-string edit — every other workbook part (sheets, charts, images, drawings) byte-identical.
- **Response surfaces tracked (resolved):** the three validated `dial_grid.json` surfaces are canonical and git-tracked at `europe/<Country>/outputs/dial_grid.json`. **Build-harness output path — FIXED (2026-07-04, no rebuild run):** `build_grid.py` (all four copies) now resolves the `europe/` tree root from its own path and writes to the canonical `europe/<Country>/outputs/dial_grid.json`. On disk the per-country copies at `europe/<Country>/model/build_grid.py` already resolved there (location-based `dirname`); only the shared `europe/common/build_grid.py` wrote to the non-canonical `europe/outputs/`, and the "`europe/outputs/<CC>/`" was a docstring artefact never emitted by the code — both corrected (docstring + output-path line, all four copies).
- **ES homelessness averted-cost:** currently a flagged UK transfer (£20,128 → €23,262); a component-built ES alternative (Panadero-Herrero 2018 unit costs) is available but not computed.
- **Eurostat 2024 provisional data:** the 2024 GDP-deflator and PPP values carry provisional status ("p").
- **`unemployment_shock` helper is NOT dead code — left in place (correction, 2026-07-04):** `europe/common/reforms.py` (and the per-country copies under `europe/<Country>/model/pipeline/`) carries an `unemployment_shock` helper that zeroes only `[yem, yse]`. An earlier note called it "never called" — that is **wrong**: a whole-tree grep shows it is invoked in **8 places** (`build.py` synthetic floor ×4 + the four `*_real` build/experiment scripts `es_real/build_real.py`, `es_real/run_experiment.py`, `el_real/build_el.py`, `it_real/build_it.py`), each of which `import reforms`. It is simply **not on the surface path**: the surface builder uses `build_grid.apply_unemployment`, which zeroes the full country `earn` set, so `yseev` (IT) and `yemre`/`ysere` (EL) are correctly zeroed and the built surfaces are faithful. Removing the helper would break those 8 callers; on the floor/experiment path it applies the narrower `[yem, yse]` zeroing (latent, not in scope). Do not remove as "dead code".

---

## 6. Consistency
This document reproduces figures faithfully from, and is consistent with, `PROVIDER_EVIDENCE_EU.md`, `PROVIDER_DECISIONS.md`, `TECHNICAL_REPORT.md`, `europe/docs/references.bib` and `PROVIDER_TOOLREADY_2024.md`. The native layer is unchanged; this document consolidates, it does not re-decide. Where a figure could differ by rounding or method, the tool-ready value governs the 2024-equivalent layer and the native value governs the native layer, each labelled with its price year and flag.
