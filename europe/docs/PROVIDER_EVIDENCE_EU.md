# Provider Evidence Base, EU (Spain, Italy, Greece) with UK Reference

BENEFITS Horizon Europe D2.2, grant 101179032, Work Package 2. Compiled 30 June 2026.

**This file is data-free.** It holds valuation parameters and citations only, no microdata.

**Native price years and native currencies only.** Every figure is recorded at its native price year and native currency. Uprating to the common 2024 base and PPP-adjustment of the spine and of every cross-country transfer are the **next task** and are **not performed here**. Where a figure carries two years (a source year and the price year of a displayed value), both are kept distinct.

**Flags.** TRANSFER names the source country or source and marks a benefit-transfer. DERIVED or INFERRED names the inputs and method. CS marks a country-specific figure. UNEVIDENCED-EXCLUDED marks an outcome that is not valued and not transferred. NOT FOUND marks an absent national source.

**One route per outcome.** Each outcome is valued by exactly one route (ENGINE, WELLBY, CONVENTIONAL, COST-INPUT, or UNEVIDENCED-EXCLUDED). No outcome carries two routes; no double-counting. Where a service has both an income outcome and a wellbeing outcome (employment), these are two distinct outcomes, each on one route.

---

## A. Valuation spine (WELLBY)

- **1 WELLBY = £13,000 (2019 prices)**, low £10,000, high £16,000. Source: HM Treasury, *Wellbeing Guidance for Appraisal: Supplementary Green Book Guidance*, July 2021, page 33 ("£13,000 [Low: £10,000, High £16,000] ... in 2019 prices and values"); re-verified against the primary PDF (Task-2 web pass). Native: 2019 GBP.
- The **£16,300** applied at 2024 prices is the **same spine uprated**, not a second value. The spine is always cited as £13,000 at 2019 prices; £16,300 is the applied figure, and it IS shown on every tool face (2026-08-01), always with its derivation.
- The **EU spine** is built **from £13,000 (2019)**, PPP-adjusted to national price levels and uprated to 2024, and flagged a TRANSFER (UK). It is **never** built from £16,300 (that would double-uprate). The price year is always carried.
- WELLBYs are valued at weight 1 (not distributionally re-weighted).
- **[NEXT STEP]** PPP-adjustment and uprating of the spine to 2024 are deferred to the uprating task.

## B. Attribution default

- **0.5 (range 0.3 to 0.7)** is the **tool's own SROI-style modelling assumption**, informed by Green Book additionality principles. It is **not** a GMCA default.
- The GMCA citation (New Economy / HM Treasury, *Supporting Public Service Transformation: Cost Benefit Analysis Guidance for Local Partnerships*, v2.0, April 2014; Unit Cost Database v3.0, November 2025) is retained for the broad cost-benefit-analysis framing only, **never** for the 0.5 figure.

## C. Price-year handling

- Every figure carries its native price year and native currency.
- The common uprating base is **2024**, chosen because the UK tool already operates in 2024, so uprating the EU figures to 2024 preserves cross-tool comparability.
- **Spain Analyst money is 2023 nominal EUR underlying, displayed uprated to 2024 EUR** (Eurostat `nama_10_gdp` deflator ×1.0289; a display-layer uprate, the surface staying 2023 nominal); **Spain Provider money is 2024-equivalent EUR**. The 2024 display year and the 2023 income-reference-year provenance both appear on the face of the tool.
- UK base figures displayed in the tool are in **2024 prices**, so their **source year** and their **displayed price year** are distinct and are both recorded.
- **Identified uprating and PPP sources (for the next step; nothing uprated or PPP-adjusted here).** GDP deflator: Eurostat `teina110` for ES/IT/EL, with AMECO as the comparator vintage; for the UK spine, the UK Government / ONS *GDP deflators at market prices* collection. PPP conversion (the £13,000 2019 spine and all cross-country transfers): Eurostat purchasing power parities / price level indices (EU-internal method), with OECD PPPs as the alternative.
- **[NEXT STEP]** No uprating, deflation, or PPP-adjustment is performed in this file.

## D. Standing exclusions (UNEVIDENCED-EXCLUDED; do not value, do not transfer)

- **Food aid and food banks**, non-income outcome: excluded for all four countries, including the UK.
- **Mental-health talking therapies (IAPT)** for ES, IT, EL. The UK IAPT row stays evidenced; the UK 0.71 WELLBY is **not** transferred to the EU countries.
- **UC and income-support processing**, non-income "averted hardship": excluded for all.
- **Minimum-income claim-support hardship** unit value, distinct from the ENGINE income effect: excluded for all three.

---

## E. Per-service evidence

### 1. Employment / work coaches

Routes: ENGINE (income effect, from the microsim engine) and WELLBY (non-pecuniary wellbeing of employment). These are two distinct outcomes.

**WELLBY effect: +0.46, retained and relabelled.** This is a **Britain fixed-effects unemployment-to-employment WELLBY transfer**: the symmetric employment-side use of the unemployment coefficient of approximately -0.46 in the Britain panel fixed-effects specification (full-time employment the reference category). Source: Clark, Flèche, Layard, Powdthavee and Ward, *The Origins of Happiness* (Princeton University Press, 2018), Table 4.2. Corroboration: New Zealand Treasury, Public Benefit Exchange technical annex, restating the employment wellbeing gain as 0.46 (95% CI 0.38 to 0.54), attributed to Clark et al. Tables 4.1 and 4.2. Applied to all three countries as a flagged UK/EU transfer. (Attribution note: the brief's DECISION 1 wrote "Clark, Frijters and Layard"; the author list here follows the verified `europe/docs/references.bib` entry.)

The earlier "years 2 to 5" qualifier is **removed as unverifiable**: Table 4.2 is a cross-sectional labour-force-status coefficient, not a dynamic time-path, and no source supports a years-2-to-5 framing. The 0.7 WELLBY figure (Layard et al. 2020) was **considered and rejected** for this cell on estimand grounds: it is the psychic cost of a year of unemployment, not the unemployment-to-employment transition gain.

| Country | WELLBY effect | National ALMP warrant (qualitative; no effect size carried) | Unit value | Tier |
|---|---|---|---|---|
| UK | +0.46 WELLBY (Britain FE; Clark, Flèche, Layard, Powdthavee and Ward 2018, Table 4.2) | reference country | WELLBY £13,000 (2019), native | STRONG effect |
| ES | +0.46 WELLBY, TRANSFER (UK/EU) | national ALMP evaluation of participation and job-finding exists (Arranz et al., *Journal for Labour Market Research*, 2024); effect size not extracted, non-load-bearing | WELLBY spine TRANSFER + PPP (next step) | STRONG effect, MODERATE transfer |
| IT | +0.46 WELLBY, TRANSFER (UK/EU) | national evidence the Reddito di Cittadinanza is employment-neutral (Aprea, Gallo and Raitano, *Italian Economic Journal*, 2023); effect size not extracted, non-load-bearing | WELLBY spine TRANSFER + PPP (next step) | STRONG effect, MODERATE transfer |
| EL | +0.46 WELLBY, TRANSFER (UK/EU) | national ALMP evidence that DYPA wage subsidies are positive (OECD 2024 DYPA evaluation, referenced, not independently re-retrieved); effect size not extracted, non-load-bearing | WELLBY spine TRANSFER + PPP (next step) | STRONG effect, MODERATE transfer |

No ALMP effect-size figure is carried (none feeds a displayed value). A future use (for example a technical-report evidence-table appendix) requiring an effect-size figure must verify it against source first.

### 2. Minimum income / UC processing

| Country | Route | Detail | Tier |
|---|---|---|---|
| UK | ENGINE | income effect from the engine | n/a (ENGINE) |
| ES | ENGINE | IMV income effect from the engine. Context (CS, AIReF 2026): poverty-gap reduction 30.3% (potential 58.2%), poverty-rate reduction 9.5%, non-take-up 55%, cost €3,106m | n/a (ENGINE) |
| IT | ENGINE | Assegno di Inclusione income effect from the engine | n/a (ENGINE) |
| EL | ENGINE | KEA income effect from the engine | n/a (ENGINE) |

Non-income "averted hardship", all countries: **UNEVIDENCED-EXCLUDED**. The hardship unit value, distinct from the ENGINE income effect, is excluded.

### 3. Food aid / food banks

| Country | Route | Detail |
|---|---|---|
| UK / ES / IT / EL | ENGINE for any income transfer | Non-income outcome **UNEVIDENCED-EXCLUDED**, all four. Do not value, do not transfer. |

### 4. Debt advice

Route: WELLBY.

| Country | Effect | Unit value | Tier |
|---|---|---|---|
| UK | central approximately zero (Pleasence and Balmer 2007 RCT, null); high bound 52 to 63% self-report (MaPS 2023/24) | WELLBY £13,000 (2019), native | WEAK |
| ES / IT / EL | transfer the UK structure (service near-absent in EL) TRANSFER | WELLBY spine TRANSFER + PPP (next step) | WEAK |

### 5. Talking therapies (IAPT)

| Country | Route | Effect | Unit value | Tier |
|---|---|---|---|---|
| UK | WELLBY | 0.71 central, 1.5 high (Clark 2018; Frijters et al. 2020) | WELLBY, 2019 prices, native | STRONG |
| ES / IT / EL | UNEVIDENCED-EXCLUDED | do **not** transfer the UK 0.71 | none | UNEVIDENCED |

### 6. Housing / homelessness

Route: CONVENTIONAL (averted public-sector cost), all countries, matching the UK and preserving cross-country comparability.

| Country | Averted-cost unit value | Status | Tier |
|---|---|---|---|
| UK | £20,128 per person per year, DERIVED 12-month rough-sleeper vignette (Crisis 2015, Pleace; DCLG), 2015-16 | native, derived | reference |
| ES | NO native averted cost (NOT FOUND) | fill ranked, see below | MODERATE (if derived) |
| IT | NO native averted cost (NOT FOUND) | flagged TRANSFER (UK / FEANTSA), PPP-adjusted | WEAK (transfer) |
| EL | no study (NOT FOUND) | flagged TRANSFER (UK / FEANTSA), or exclude | WEAK (transfer) |

**ES fill, ranked:** (1) build the averted cost downstream from 2018 component unit costs [DERIVED]; (2) flagged TRANSFER of the UK or FEANTSA (Pleace et al. 2013) averted-cost, PPP-adjusted. ES 2018 component unit costs to record for the downstream build (Panadero-Herrero et al. 2021, 2018 prices, CS): prison €2,287 per inmate per month; hospital admission €554.65; emergency consultation with referral €255.20, without €145.01; emergency reception centre €27.58 per day; shelter €23.78 per day.

**IT context only (not averted costs):** Housing First €26 per day, hospital €600 per day, psychiatric community €150 per day (Dardes via Altreconomia 2022, reference period 2021 to January 2022). These are intervention or comparator day-costs, not averted costs.

**Hábitat finding (reported in prose, NOT monetised):** +1.25 life satisfaction on a 1-to-7 scale, tenancy retention 96.0 to 96.6% at 18 months, 11.25 fewer homeless nights per month (Martínez-Cantos and Martín-Fernández 2024, RCT 2015-20). Intervention cost €46.01 per person per day total (accommodation €31.79, support €9.33, indirect €4.89), 2018 prices (price base CONFIRMED 2018). The €525 per month is the **incremental** cost versus control, not a standalone cost. The Hábitat €46.01 per person per day is an **intervention** cost and must **not** be used as an averted cost. The 1-to-7 to 0-10 rescaling is **dropped**; the result is not monetised via WELLBY.

### 7. Children's social care

Route: CONVENTIONAL (averted lifetime cost per averted care-entry). Effect: FGC 8.6 percentage points (36.2% versus 44.8%, Coram/Foundations RCT 2023); low bound Nurmatov 2020 null; TRANSFER (international), applied to all.

| Country | Unit value (averted lifetime cost) | Flag | Tier |
|---|---|---|---|
| UK | £89,390 discounted lifetime incidence cost per nonfatal case (95% UI £44,896 to £145,508; Conti et al. 2021, 2015 GBP) | native | STRONG effect |
| IT | €87,389 per new case, INFERRED lifetime present value (€910,412,855 divided by 10,418 new 2010 cases; Bocconi 2013, reference year 2010, 4.6% real discount) | CS, INFERRED (not a published figure) | cost CS |
| ES / EL | no native study; flagged TRANSFER of IT €87,389 (Southern-EU, preferred) or UK £89,390 (both lifetime), PPP-adjusted | TRANSFER | cost transfer |

Do **not** use €130,259 (the annual prevalence-based societal-average artefact; wrong construction for this route). Cite **Bocconi 2013** (reference year 2010) as primary, **not** Ferrara 2015 (secondary commentary). The €87,389 reproduces as €87,388.45 at full precision; see Section F.

### 8. Domestic abuse / GBV

Route: CONVENTIONAL (cost per victim) plus advocacy effect. Effect: **OR 0.43 central** (physical abuse at 12 to 24 months; Ramsay / Campbell 2009); **OR 0.39 the severe-physical-abuse-at-24-months bound** (NNT 8; Rivas / Cochrane 2015); TRANSFER (international), applied to all. 0.43 is the central and 0.39 the severe bound, not the reverse.

| Country | Aggregate | Per-victim | Flag | Tier |
|---|---|---|---|---|
| UK | £66,192m, harm-inclusive, annual, 2016/17 (Oliver, Home Office RR107, 2019) | £34,015 per victim (over approximately 1,946,000 victims) | native, DERIVED per-victim | reference |
| ES | Follow the primary study, do NOT sum. **Central: gender violence alone €3,015m** (option C; precise €3,014.61m), 2022, 0.23% of GDP, €64 per capita. Joint tangible upper bound (gender + sexual violence outside partnership): €4,933.22m, 2022, 0.37% of GDP, €104 per capita (Table 1). Intangible (pain and suffering, gender violence): €4,110m (precise €4,110,037,260, Table 5), carried SEPARATELY | tangible-only per-victim €2,109 (€4,933.22m / 2,338,627, any VG 12-month + VSfp), 2022 | CS; study does not sum tangibles and intangibles | cost CS |
| IT | €16,719,540,330 (2013; includes €14.3bn intangible; harm-inclusive; WeWorld/Intervita 2013) | €14,539 per victim on ISTAT-2006 annual denominator 1,150,000 (matching the UK annual basis); €2,480 per lifetime victim as the alternative | CS aggregate, DERIVED per-victim with transferred ISTAT denominator | cost CS |
| EL | NOT FOUND (no Greek primary costing) | ranked transfer: (1) **preferred** EIGE Greece-specific extrapolation of approximately €2.4bn per year for intimate-partner violence against women (EIGE, *Combating Violence Against Women: Greece*, 2017 factsheet), flagged a transfer/extrapolation, not a Greek primary costing; (2) EU-level anchors (EIGE 2021, doi:10.2839/23187): total GBV €366bn, violence against women €289bn, IPV against women €151.95bn. EIGE per-victim scalar not stated in the 2021 report; not recorded as a figure | TRANSFER / extrapolation | cost transfer |

**Spain, follow-the-study (supersedes the earlier composite).** Source: Universidad de Alcalá / Delegación del Gobierno contra la Violencia de Género, *Impacto de la violencia de género y de la violencia sexual contra las mujeres en España (II): una valoración de sus costes en 2022* (Ministerio de Igualdad, 2024, NIPO 048-24-002-4). The study estimates **tangible** costs for the year 2022 but **intangible** costs on a lifetime-from-2022 basis (different time horizons), and for that reason the study itself does **not** sum tangibles and intangibles. The previously composed harm-inclusive **€9,043m is therefore superseded** by the study's own structure; it is a project-level construction the primary source does not make, and must never be presented as a source-native total. If any harm-inclusive figure is retained downstream it must be labelled an external composition.

### 9. Drug and alcohol

Route: **VSL times averted-mortality (EU)**, **not** BCR times cost.

**Scope caveat (record prominently).** The EU route values **averted drug-related deaths only**, whereas the UK CONVENTIONAL drug cell (BCR times cost) values the full benefit bundle (crime, health, productivity, mortality). The EU figure is a **strict subset** of the UK figure and is **smaller by construction**. The two are **not like-for-like** and must never be compared as equals.

Effect: methadone all-cause mortality **RR 3.20** (unadjusted out-to-in; Sordo et al. 2017, *BMJ* 2017;357:j1550, an international systematic review and meta-analysis; the related OAT all-cause **RR 0.47** is from the Santo / EUDA summary). The mortality effect is a **flagged transfer for all three countries**; only the national VSLs and OST costs are country-specific.

**Baseline drug-related mortality (denominator for RR 3.20).** ES 38 drug-induced deaths per million aged 15-64 (1,202 deaths, 2022); IT 6 per million (225 deaths, 2023); EL 35 per million (239 deaths, 2021). Source: EUDA *European Drug Report 2025*, Annex Table 6. Caveat: these are crude, not age-standardised, and under-ascertained (Italy's low rate reflects register limitations), so the averted-death computation inherits that uncertainty.

| Country | VSL | Flag |
|---|---|---|
| ES | national, road-context CV/SG €1.3 to 1.7m (2017; Sánchez-Martínez et al. 2021); hedonic-wage bounds €2.0 to 8.3m (2000 to 2008) as sensitivity, flagged that the road context may understate non-accident mortality | national, CS |
| IT | national €1.022m median / €2.264m mean (approximately 2004; Alberini, Hunt and Markandya 2006); €6.437m (approximately 2011, PPP euros; Guignet and Alberini 2015) as the upper anchor | national, CS |
| EL | OECD-transfer (EU base USD 3.6m 2005, range 1.8 to 5.4m, or updated USD 8.4m 2022; income elasticity 0.8 central, 0.4 sensitivity, 0.5 high-income-group) | TRANSFER |

EL transfer ingredients (GNI per capita, Atlas current USD 2024; do **not** compute the transfer here): EL 22,730, IT 38,590, ES 33,550, EU-27 41,076.43 (World Bank NY.GNP.PCAP.CD, EUU, 2024; identical to the tool-ready VSL ingredient).

OST costs (documentary under this route; load-bearing only under a BCR route): ES €4 per day methadone (2004, excluding medication; €1,460 per year DERIVED on 365 days), €5 buprenorphine; EL €1.8 per day methadone medication-only (approximately 2009-10; €657 per year DERIVED), flagged medication-only at roughly one-third of full delivery cost; **IT per-capita SERT cost (attribution corrected): EMCDDA *Insights 24* (2017), Chapter 7 (Bergamo case study), Table 7.8, SERT rows — per-capita total excluding inpatient €3,654.6 (2013) and €3,900.0 (2014); including inpatient €26,270.6 (2013) and €25,949.0 (2014); both scope variants recorded. This corrects the prior attribution to Chapter 8 (Genetti et al.), a different chapter.** UK BCR 2.3 / 2.5 / 4.0 near-term (Black Year 5, DTORS, PHE 2018) is a UK transfer with no EU national BCR.

**NOT ADOPTED: Italy and Greece each hold a national OST cost that the shipped tool does not use.**
Both shipped unit costs are the Spanish 2024-equivalent figure of €2,100 scaled on Eurostat `lc_lci_lev` section Q
labour-cost ratios at 2023: Italy €2,100 × 29.6/27.2 = **€2,285**, Greece €2,100 × 11.2/27.2 = **€865**. Set against
them:

* **Italy** has the per-capita SERT cost above, EMCDDA *Insights 24* (2017), Chapter 7 (Bergamo), Table 7.8, which at
  2024 is **€4,463.3** excluding inpatient care on the 2013 base and **€4,720.5** on the 2014 base, or **€32,084.1**
  and **€31,408.0** including it. The adopted €2,285 is about half the lower national reading and about a fourteenth
  of the higher one.
* **Greece** has methadone at **€1.8 per day**, medication-only, at about 2009-10: €657 a year native, **€2.07 per day
  or €754 a year** once uprated by 1.147861. It is flagged medication-only at roughly a third of full delivery cost,
  so it is not scope-comparable with a full delivery cost without an adjustment nobody has made. The adopted €865 is
  above it.

**Both non-adoptions are now decided, and the reasons are recorded here and on each cell's own note
(2026-08-05).** They were previously recorded as facts with no justification.

**Italy: not adopted, three reasons, any one sufficient.** It is **not national** — Bergamo is one city's
service, carried in the source as a case study, so adopting it would read a local observation as an Italian
unit cost. It is **not the same quantity** — whole-service expenditure per client of a SERT covers clients
and activities this row does not, against a per-case cost of delivering opioid substitution. And **its scope
is unresolved** — the two variants differ by a factor of about seven on nothing more than whether inpatient
care is counted, and nothing in this tree chooses between them. Adopting either would also break the
one-concept-per-row discipline that lets the three cells be read beside each other. *The size of the choice,
recorded and not applied:* €2,285 → €4,463 (×1.95) on the excluding-inpatient variant, or → €32,084 (×14.04)
on the including-inpatient one.

**Greece: not adopted, because it is a different quantity.** This row is a per-case cost of **delivering**
opioid substitution, and the Spanish figure it converts from is explicitly **excluding medication**. The Greek
figure is the medication alone. The two are complements, not alternatives, so adopting it would put a drug
price in a delivery-cost row and leave the Greek cell measuring something neither of the other two measures.
**The non-adoption is not neutral, and the direction matters.** €754 for medication alone against €865 shipped
for the whole of delivery is not credible. Grossing the national figure to full scope on this document's own
one-third flag gives about **€2,262, roughly 2.6 times the shipped €865**. That is a flag and not a
measurement — the one-third is a qualitative note, not a measured ratio — so **no value is changed on it**.
What it says is that the Greek cell is more likely too low than too high, and by a factor rather than a margin.

Both national figures remain documentary here and neither is load-bearing: under the COST-INPUT route these
services carry a value-added of zero, so the unit cost reaches only the extra-running-cost row on the Provider
tab. That is why the Greek understatement is recorded rather than acted on: it moves a running-cost line, not
a value.

Tier: MODERATE (ES and IT national VSL), WEAK (EL transfer VSL).

### 10. Additional GP consultations

Route: COST-INPUT (unit cost only, value-added zero). Low stakes: feeds no displayed value.

| Country | Unit cost | Flag |
|---|---|---|
| UK | £42 to £49 per 10-minute surgery consultation including direct care staff (PSSRU 2023 Manual, Table 9.4.2, p.64, 2022/23) | native |
| IT | **approximately €12 per ambulatory visit (2003)**, the primary figure: Garattini et al. (2003), DYSCO, *Farmeconomia* 4(2):109-114. **€15.17 is dropped** (not a primary figure but a downstream CPI-inflation of €12 to 2016, Dal Negro et al. 2016); uprate the €12 (2003) in-house | CS; native 2003. Do **not** use the €20.66 code-89.7 specialist tariff for the GP route |
| ES | €14.78 per visit (2008, Antares, average economic cost), or Brotons et al. 2007 centre-level (2005) | CS. Public-price tariffs €45 to €46.88 (2024-25, Madrid/Navarra) are reimbursement rates, not economic costs |
| EL | **€10 retired as wrong-basis** (a capitation or reimbursement figure, not an economic cost per visit; the Tsiantou capitation wording is not independently re-verified, and a separate €10-per-visit EOPYY figure also existed in 2014, so the basis is easily confused). The Greek GP cell is a **flagged transfer from the Spanish €14.78 (2008)**, zero value-added (cost-input route) | TRANSFER (from ES); cost-input, zero value-added |

No OECD-average euro-per-consultation exists (NOT FOUND).

---

## F. Internal-consistency (transcription) checks

Transcription checks only; no figure was silently corrected.

- ES GBV tangible-only per-victim: €4,933.22m / 2,338,627 = €2,109.45, recorded €2,109. Reproduces.
- ES GBV: the earlier composed aggregate €4,933.22m + €4,110m = €9,043.22m is **superseded** (the primary study does not sum tangibles and intangibles; see Section E.8), so the composed per-victim €3,867 is no longer carried. Retained separately from the study: central gender-violence tangible €3,015m (precise €3,014.61m, option C) and intangible €4,110m (precise €4,110,037,260, Table 5).
- IT GBV per-victim: €16,719,540,330 / 1,150,000 = €14,538.73, recorded €14,539. Reproduces.
- IT child-maltreatment: €910,412,855 / 10,418 = €87,388.45. The decided figure is €87,389. **FLAG**: the exact quotient is €87,388.45; the decided €87,389 rounds this up by about €0.55 (one euro at integer precision). Recorded as decided, not altered.
- OST annualisations: ES €4 x 365 = €1,460; EL €1.8 x 365 = €657. Both reproduce.
- UK domestic-abuse per-victim (additional check): £66,192m / 1,946,000 = £34,014.4. The published Home Office figure is £34,015. **FLAG**: a sub-pound rounding gap reflecting rounding in the published aggregate; the published £34,015 is authoritative and is recorded.

Both flags are sub-unit rounding presentations, not substantive errors.

## G. Next-step retrievals (wiring dependencies, not gaps for this task)

- **Drug baseline mortality rate** — NOW RECORDED (Section E.9): ES 38 / IT 6 / EL 35 drug-induced deaths per million aged 15-64 (EUDA *European Drug Report 2025*, Annex Table 6). No longer a pending retrieval; the crude / under-ascertainment caveat carries into the averted-death computation.
- **IT OST per-capita cost** — NOW RECORDED (Section E.9): EMCDDA *Insights 24* (2017) **Chapter 7, Table 7.8, SERT** (€3,654.6 / €3,900.0 excl. inpatient; €26,270.6 / €25,949.0 incl.), correcting the earlier Chapter 8 attribution. Documentary under the VSL route.
- **ES homelessness averted-cost**: downstream build from the 2018 component unit costs, or a flagged UK/FEANTSA transfer.
- **Uprating and PPP**: every figure carries its native price year; uprating to the 2024 common base and PPP-adjustment of the spine and all transfers is the next task. Not performed here.
