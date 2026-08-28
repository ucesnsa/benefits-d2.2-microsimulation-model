# Provider Tool-Ready Layer, 2024-Equivalent (EU: Spain, Italy, Greece; UK reference)

BENEFITS Horizon Europe D2.2, grant 101179032, Work Package 2. Computation-and-record layer over the native evidence in `PROVIDER_EVIDENCE_EU.md` and `PROVIDER_DECISIONS.md`. Compiled from series extracted 2026-07-01.

**All monetary figures here are 2024-equivalent.** This document does not alter any native value; it is the tool-ready layer beside the native layer. No microdata; parameters, series, and citations only.

**Method (applied exactly).** Time-uprating on the GDP deflator of the figure's own country, in its own currency, to a common 2024 base; then, for transferred figures only, exactly one household-final-consumption PPP step at 2024 to the destination. Order: uprate first, then PPP. Native figures used in their own country take no PPP.

**Series used.**
- UK GDP deflator: ONS series **L8GG**, HM Treasury *GDP deflators at market prices* (March 2026 QNA vintage, financial-year index, 2024-25 = 100).
- ES/IT/EL GDP deflator: Eurostat **`nama_10_gdp`**, `na_item=B1GQ`, `unit=PD15_NAC` (implicit GDP deflator, price index 2015 = 100, national currency); Eurostat update 2026-06-26, extracted 2026-07-01 (2024 provisional, "p").
- Household-final-consumption PPP, single 2024 round: within the euro area, Eurostat **`prc_ppp_ind`**, `na_item=PPP_EU27_2020`, `ppp_cat=E011` (household final consumption; EUR per PPS, EU27_2020=1) — primary. For the one UK-crossing transfer, **OECD `DSD_NAMAIN10@DF_TABLE4` v2.0**, `MEASURE=PPP_P31S14`, `UNIT=XDC_USD` (national currency per US dollar) — **named fallback**. The reason once recorded here, that the UK is absent from Eurostat `prc_ppp_ind` post-Brexit, is wrong and was withdrawn on 2026-08-04: Eurostat publishes a 2024 United Kingdom value of 1.05586. The OECD factors are retained because they are the ones the shipped spines were built from and they reproduce exactly; taking the leg from Eurostat instead would give spines of EUR 14,032 (ES), 15,054 (IT) and 13,270 (EL) against the shipped 14,050, 14,925 and 13,317, a difference of at most 0.9 per cent, against the +/-23 per cent band the WELLBY spine itself carries. Both sources are pulled and compared by `europe/model/pull_ppp_deflators.py`, whose dated artefact is beside this file; the same 2024 round; the OECD and Eurostat euro-area price-level ratios agree within ~1% (cross-check below).
- GNI per capita (VSL): World Bank **`NY.GNP.PCAP.CD`** (Atlas, current US$, 2024): Greece 22,730; European Union (EUU) 41,076.43.
- Exchange rate (VSL): Eurostat **`ert_bil_eur_a`** annual average 2024, 1.0824 USD per EUR.
- US GDP deflator (VSL base uprating): **FRED `GDPDEF`** (BEA implicit price deflator, 2017 = 100): 2005 = 81.551, 2024 = 125.422.

---

## 1. Spine (WELLBY) — internal gate

Native: £13,000 per WELLBY, 2019 prices (HM Treasury *Wellbeing Guidance for Appraisal*, July 2021, p.33), low £10,000 / high £16,000.

- Deflator ratio 2019-20 → 2024-25 (L8GG): 100 / 80.8738 = **1.236494**.
- £13,000 × 1.236494 = **£16,074.4** (2024 GBP, central).
- **CHECK PASSED:** −1.38% vs the applied £16,300, within ±3%. This confirms £16,300 is the 2024 uprate of the same £13,000 spine (the ~1.4% gap is the real-GDP-per-capita-growth term of HMT's footnote-102 method, which this plain-deflator step omits).

**PPP to euro** (UK→destination, OECD per-USD, EUR/GBP factors: ES 0.861941, IT 0.915660, EL 0.816996). Applied 2024 value of the £13,000 (2019) spine: **£16,300** (HM Treasury footnote-102 method); band £12,540 / £16,300 / £20,064 (the fn102 2024 uprates of £10,000 / £13,000 / £16,000):

| Country | 2024 value-per-WELLBY (EUR) | low | high |
|---|---|---|---|
| ES | **€14,050** | €10,809 | €17,294 |
| IT | **€14,925** | €11,482 | €18,374 |
| EL | **€13,317** | €10,245 | €16,392 |

**Applied 2024 value (settled decision): £16,300, not £16,074.** £16,300 is HM Treasury's methodologically complete uprate of the £13,000 (2019) value, including the real-GDP-per-capita-growth term of the footnote-102 method; the plain-deflator £16,074.4 omits that term. Using HMT's own complete method is both more correct and preserves cross-tool consistency with the UK tool, which applies £16,300. **The spine itself is always cited as £13,000 at 2019 prices; £16,300 is the applied figure, stated here so the chain stays reproducible, and it is not shown on any tool face (2026-07-31).** The spine gate stands (the plain deflator gives £16,074.4, −1.38% from £16,300, confirming they are the same £13,000 spine under the two documented methods); the euro conversions are rebased on £16,300. Each euro spine is a **PPP-adjusted transfer of the HM Treasury value (a modelling assumption).**

---

## 2. Per-service, per-country conversions

WELLBY-route figures ride the spine (no separate PPP). CONVENTIONAL/COST-INPUT figures follow uprate-then-PPP. Flags: **national** (own deflator, no PPP), **transfer-from-X** (uprated on X's deflator, one HFCE-PPP step), **rides-spine**, **derived**.

> **Every figure in this section is a RAW, not a shipped value.** Since 2026-08-05 each is then multiplied by an effect share and an attribution before it reaches a tool face, so the shipped value is a fraction of the figure below. Section 2e gives the stages, the before-and-after for every point, and the reasoning; `VALUATION_CHAINS.md` gives the complete chain per point.

### Employment (+0.46 WELLBY) — rides the spine
+0.46 applied per country at that country's converted spine (central, on the £16,300 applied 2024 value); **not separately PPP-adjusted**. Per-person wellbeing value pre-attribution: ES 0.46 × €14,050 = **€6,463**; IT 0.46 × €14,925 = **€6,866**; EL 0.46 × €13,317 = **€6,126**. Flag: rides-spine (transfer of the Britain FE unemployment-to-employment coefficient).

### Homelessness averted-cost — transfer from UK (£20,128, 2015-16)
2024 GBP = 20,128 × 1.340835 = £26,988.3, then OECD HFCE PPP UK→dest:

| Dest | deflator ratio | 2024 GBP | PPP factor | 2024 EUR | flag |
|---|---|---|---|---|---|
| ES | 1.340835 | £26,988.3 | 0.861941 | **€23,262** | transfer-from-UK, PPP (OECD fallback) |
| IT | 1.340835 | £26,988.3 | 0.915660 | **€24,712** | transfer-from-UK, PPP (OECD fallback) |
| EL | 1.340835 | £26,988.3 | 0.816996 | **€22,049** | transfer-from-UK, PPP (OECD fallback) |

ES closes the parked homelessness item as a flagged UK transfer for now; a component-built ES alternative (Panadero-Herrero 2018 unit costs) remains available, not computed here.

### Children's social care — IT €87,389 (2010), transfer to ES/EL
IT 2024 (national) = 87,389 × 1.277791 = **€111,665** (no PPP). Transfer via Eurostat EUR/PPS:

| Country | 2024 EUR | flag |
|---|---|---|
| IT | **€111,665** | national (IT deflator 1.277791; no PPP) |
| ES | 111,665 × 0.932084 = **€104,081** | transfer-from-IT, PPP |
| EL | 111,665 × 0.881460 = **€98,428** | transfer-from-IT, PPP |

(native carried as €87,389, the committed foundation value; the brief wrote €87,388 — same figure, exact quotient €87,388.45.)

### GBV / domestic abuse
| Country | native (year) | 2024 value | flag |
|---|---|---|---|
| ES | central GBV €3,015m / €3,014.61m (2022) | ×1.093186 = **€3,295.5m** | national |
| ES | tangible €4,933.22m (2022) | **€5,392.9m** | national |
| ES | intangible €4,110m / €4,110.04m (2022) | **€4,493.0m** (carried SEPARATELY) | national |
| ES | per-victim €2,109 (2022) | **€2,305.5** | national |
| IT | €16,719,540,330 (2013) | ×1.221292 = **€20,419.4m** | national |
| IT | per-victim €14,539 (2013) | **€17,756** | national |
| EL | EIGE aggregate ~€2,400m IPV (2016 basis) | ×1.180183 = **€2,832m** | national-scale context; **AGGREGATE, not a per-victim unit** |
| EL | per-victim (tool-usable), **chosen = IT-transfer** | IT→EL: €17,756 × 0.881460 = **€15,651** (chosen; the figure reproduces from the €17,756 the tool holds, not from the unrounded €17,756.36); ES→EL €2,180 recorded as alternative | transfer-from-IT, PPP; harm-inclusive |

Advocacy effect (unchanged, dimensionless): OR 0.43 central, OR 0.39 severe bound.
**EL GBV per-victim (settled decision): use the IT-transfer €15,651 (harm-inclusive), not the ES-transfer €2,180 (tangible-only).** The UK GBV cell (£34,015) is harm-inclusive, and the Italian per-victim is harm-inclusive (it includes the €14.3bn intangible component), so transferring the Italian per-victim matches the construction of the UK and Italian GBV cells; the Spanish per-victim is tangible-only and would place a scope-mismatched figure in an otherwise harm-inclusive row. The EIGE €2.4bn is an aggregate, not a per-victim unit. The Greek GBV cell is therefore a per-victim transferred from Italy, doubly flagged (EIGE extrapolated the Greek aggregate from UK costs, and the per-victim is transferred from Italy), which makes it among the weakest-evidenced cells in the set. The ES-transfer €2,180 is carried as a recorded alternative, not the chosen value.

### Drug and alcohol — VSL route (see §3 for VSL and averted-death rate)
OST costs (documentary; load-bearing only under a BCR route), uprated to 2024 on own deflator:
| Country | native (year) | 2024 value | flag |
|---|---|---|---|
| ES | €4/day methadone, ex-medication (2004) | ×1.438347 = **€5.75/day** (€2,100/yr) | national |
| EL | €1.8/day methadone, medication-only (2009) | ×1.147861 = **€2.07/day** (€754/yr) | national |
| IT | per-capita SERT excl. inpatient €3,654.6 (2013) / €3,900.0 (2014) | **€4,463.3 / €4,720.5** | national |
| IT | per-capita SERT incl. inpatient €26,270.6 (2013) / €25,949.0 (2014) | **€32,084.1 / €31,408.0** | national |

### Primary-care GP consultation (cost-input, zero value-added)
| Country | native (year) | 2024 value | flag |
|---|---|---|---|
| ES | €14.78 (2008, Antares) | ×1.249942 = **€18.47** | national |
| IT | €12 (2003, Garattini/DYSCO) | ×1.470047 = **€17.64** | national (native 2003; €15.17 not used) |
| EL | ES €14.78 (2008) transferred | ES 2024 €18.47 × 0.945687 = **€17.47** | transfer-from-ES, PPP; cost-input, zero value-added |

### UK reference figures
Already at 2024 prices in the UK tool (WELLBY, applied value £16,300; rough sleeping, child maltreatment £89,390, domestic abuse £34,015, drug, GP): **not re-uprated**; recorded as 2024-price for the cross-tool comparability note.

### 2d. Operational unit costs (cost per case) — the same base

The per-case operating costs in `data.services[*].unitCost` are the other monetary layer on the provider tab, and they sit on the same 2024-equivalent base as everything above. Uprating uses the same series and vintage as the spine: **ONS L8GG, financial-year index, March 2026 QNA vintage, 2024-25 = 100**.

Index values and factors, all from that one vintage:

| Financial year | L8GG index | factor to 2024-25 | applied to |
|---|---:|---:|---|
| 2008-09 | 66.8397 | 1.496117 | drug and alcohol, £3,000 → **£4,488** |
| 2015-16 | 74.5804 | 1.340835 | homelessness averted-cost, £20,128 → £26,988.3 (§2) |
| 2018-19 | 78.7948 | **1.269119** | children's social care, £8,640 → **£10,965** |
| 2019-20 | 80.8738 | 1.236494 | WELLBY spine gate (§1) |
| 2022-23 | 91.2996 | **1.095295** | GP consultation, £49/visit → £53.6695/visit |
| 2024-25 | 100.0000 | 1.000000 | the base |

* **Children's social care.** Home Office (2021) §6.4.2 Table 10, £8,640 per child in need per year at 2018/19 prices. £8,640 × 1.269119 = £10,965.19 → **£10,965**. The two unit costs in that table are separately derived, from distinct expenditure lines, but the **populations overlap**: the source states that looked-after children are a subset of children in need, and that £8,640 is the basic level of safeguarding costed for every child in need, with looked-after children additionally attracting £45,085. £8,640 is therefore **not** a children-in-need-excluding-looked-after figure. Applying it as a community-support cost per child in need mirrors the source's own additive treatment, which is the basis on which it is used.
* **Drug and alcohol treatment.** NAO, *Tackling problem drug use*, HC 297 2009-10, Figure 5, £3,000 at 2008-09 prices → **£4,488**. Three things the earlier note did not carry. **Scope is an extrapolation:** nothing in the source covers alcohol; Figure 5 is drug treatment budgets, the corroborating paragraph refers to adult drug treatment, and the agency's remit as the report states it is treatment for drug dependency in England. The row is labelled drug and alcohol treatment, so the combined population extends beyond what was measured, and the three EU editions convert this same figure and inherit it. **The denominator is not "12+ weeks":** effective treatment is defined at note 2, not note 1, and in three parts, the third of which admits people discharged within twelve weeks in a planned way, so the shorthand overstates the treatment intensity. **Rounding:** £3,000 is the source's own rounding of £2,979, so about 0.7 per cent of upward rounding is inherited from the source. A genuinely costed unit price of £4,900 sits at paragraph 18 of the same report, from a treatment outcomes study; it is a different concept and the budget-based figure was taken in preference to it, deliberately.
* **GP consultation.** Jones et al. (2024) *Unit Costs of Health and Social Care 2023 Manual* table 9.4.2, £49 per consultation at 2022/23 prices. Uprate first: £49 × 1.095295 = £53.6695. Then × 4 visits = £214.68 → **£215**. The four-visit count remains an explicit assumption with **no source**, which is why the cell stays classed `assumption` however well sourced the price is. The £49 is priced per ten-minute surgery consultation, and the manual's own footnote records that previous editions used 9.22 minutes, so the ten-minute basis is new to this edition and the figure is **not like-for-like** with a per-consultation price from an earlier manual.
* **Seven cells carry no source price year** (Jobcentre Plus, UC processing, food banks, debt advice, talking therapies, housing, domestic abuse). They are assumption-valued and have no independent vintage to preserve, so they are **declared at the 2024-equivalent base rather than uprated to it**. Their notes say so explicitly; declaring a base is not evidence that a 2024-25 source was consulted.

The three EU editions convert from the UK figure on the labour-cost ratios in §2, so children's social care and the GP consultation moved in all three: ES 7,777 → **9,870** and 176 → **194**; IT 8,464 → **10,741** and 192 → **211**; EL 3,202 → **4,064** and 73 → **80**.

`check_drift.py` now fails if any provider monetary value reaches a page without its price base stated in its own note, so a value cannot arrive without one.

### 2e. The valuation stages — the rule

This section applies a rule to the seven multipliers rather than recording their standing, and
the rule governs every value in all four tools. The full chain for every point, generated from
the parameters themselves and recomputed against the shipped figure, is in
[`VALUATION_CHAINS.md`](VALUATION_CHAINS.md).

**THE RULE.** An outcome value is `raw x effect share x attribution`. Where the effect share is
**already an impact net of a comparison group**, the attribution is **1.0**, because the
counterfactual is inside the number and deducting it a second time understates the value. Where
the effect share is an **observed outcome rate**, the attribution is what removes the
counterfactual. Where a source exists, the source governs. Where none exists, the value is
declared an assumption and its note says so.

The rule applies in all four tools, the three European ones included: each carries a staged
value rather than a raw. Carrying a raw there where the United Kingdom carries a staged value
would be an unfinished transfer of the instrument's own method, not a country difference. An attribution
share is the tool's convention rather than a national fact, so it needs no national warrant; an
effect share is an empirical value borrowed between countries and is flagged as such on each cell.

#### The stages, per row

| row | effect share (L / C / H) | quantity | attribution (L / C / H) | quantity | source of the attribution |
|---|---|---|---|---|---|
| Employment | 0.11 / **0.30** / 0.46 | RATE | 0.20 / **0.22** / 0.27 | IMPACT | DWP Restart additionality (6 in 100 over 30 in 100 = 0.20); Additional Work Coach Support (3pp over 11% = 0.27), from DWP, *The impact of additional Jobcentre Plus support on the employment outcomes of disabled people*, research and analysis, 18 March 2025; the 2026 extended impact assessment restates it as 2.8pp over 11% = 0.2545 and is not followed. **The 0.22 central is a choice within that range, not a computed quantity** |
| Talking therapies | 0.4 / **0.5** / 0.6 | RATE | 0.455 / **0.60** / 0.610 | IMPACT | Norwegian Prompt Mental Health Care trial 0.455 (DOI 10.1159/000504453); Cuijpers et al. 2021 0.610 vs waitlist, 0.585 vs care as usual (DOI 10.1111/acps.13335) |
| Housing | 0.1 / **0.2** / 0.35 | **ASSUMPTION** | 0.500 / **0.562** / 0.575 | IMPACT | At Home / Chez Soi: 31/62 = 0.500 at two years; 41/73 = 0.562 time stably housed; 42/73 = 0.575 at one year (Aubry et al., *Psychiatric Services* 2015;66(5):463–469, DOI 10.1176/appi.ps.201400167) |
| Children's social care | 0 / **0.086** / 0.086 | **IMPACT** | **1.0** flat | — | none needed: the 8.6pp is a randomised-trial arm difference, so the counterfactual is already inside it |
| Domestic abuse | **0.24** flat | RATE | **13/24 = 0.5417** flat | IMPACT | Sullivan and Bybee 1999, 24% of the advocacy arm free of physical abuse over two years against 11% of controls (DOI 10.1037/0022-006x.67.1.43). 0.24 × 13/24 = **0.13 exactly** |
| Drug and alcohol | 2.3 / **2.5** / 4.0 (a BCR) | IMPACT | **1.0** flat | — | none needed: the DTORS ratio is measured against a constructed no-treatment comparison group. **Unchanged** |
| Debt advice | 0 / 0 / **0.63** | central IMPACT, high RATE | 1.0 / 1.0 / **0.5** | — | the central is a null randomised result, so 1.0; the high is a self-report, so it takes the documented 0.5 default |

#### The values the rule produces

Every shipped outcome value, with its origin, its factor and both stages, is in
[`VALUATION_CHAINS.md`](VALUATION_CHAINS.md), recomputed from the parameters and compared
against the figure the tool displays. That file is the record of what each value is; this
section states the rule that produces it.

#### Three band ends that were not what they appeared to be

Applying the stages to a European band end would have double-counted, because those ends were not
raws. They were the **United Kingdom cell's own final low and high ratios** applied to a national
central, so they already contained the old effect and attribution ranges. Each is now rebuilt from
a documented raw or withdrawn:

* **Housing.** The band origins are now the UK cost band, £15,000 and £35,000 at 2015-16, uprated
  on the same 1.340835 as the central. The `NOT DERIVED` declaration those ends carried is
  withdrawn, and 7.10d now verifies all three points in all three countries.
* **Children's social care.** The high was exactly **1.4 times the central** — the old attribution
  range of 0.7 over 0.5, baked into the raw. Once the attribution is 1.0 that 1.4 has no basis.
  The Italian source publishes no interval, so the raw band is the central at both ends and the
  only surviving end is the Nurmatov null. **The Conti 95 per cent interval is NOT carried to
  Europe**: it is the dispersion of a British lifetime-cost estimate, and the project's own
  borrowability rule forbids transferring anything that encodes a price level.
* **Domestic abuse / GBV.** The band has **collapsed to the central** in all three countries. The
  old ends were the UK ratios 0.141114 and 4.844169; the national per-victim cost carries no
  published interval and a single trial's arm rates carry none either. The row never had a band of
  its own — it had the United Kingdom's, and that is now visible.

#### Carved out, with the reason

**Drug and alcohol is out of scope for the European tools.** The United Kingdom multiplier is a
benefit-cost ratio applied to a treatment cost; the three European drug values are built from a
statistical-life valuation times an averted-death rate. The multiplier and the raw are not the
same kind of object, so there is no stage to apply. **Talking therapies is out of scope** in all
three European tools because it is already on the excluded route there.

#### The two deflator vintages: recorded, not standardised

The layer uses **December 2025** L8GG for the outcome chains (1.4959, 1.3406, 1.3143, 1.2979) and
**March 2026** for the unit costs and the European housing conversion (1.496117, 1.269119,
1.095295, 1.340835). **The divergence is recorded rather than standardised, and this is the
decision taken.** Three reasons. Both are legitimate published editions of one series and the
largest difference is **0.017 per cent**, against the ±23 per cent band the WELLBY spine itself
carries. Standardising would move eleven shipped United Kingdom values for a rounding-scale gain,
including the drug and alcohol row that is otherwise left alone. And the one consequence
that actually matters is now named on the face of the parameter rather than left to be discovered:
**the same £20,128 is carried at £26,983.60 in the United Kingdom chain and £26,988.30 in the
European one**, a gap of £4.70. Standardising is a four-line change to four factors and belongs in
the next re-basing, not in the middle of a stages pass.

### 2f. Where a multiplier sat in the wrong slot, and what it cost

An effect share should hold an **outcome rate** and an attribution an **impact net of a comparison
group**. Four rows crossed that line. Three are now fixed and one was already right.

1. **Children's social care — the largest error in the layer, now corrected.** The effect share
   held 0.086, the 8.6-percentage-point family group conferencing effect, which is the difference
   between two arms of a randomised trial: 44.8 per cent care entry in the control arm against
   36.2 in the treated arm. The counterfactual is deducted by the trial's own design. A 0.5
   attribution was then applied on top, deducting it a second time and **halving every value in
   the row**. The attribution is now 1.0 and the central is exactly double what it was.
2. **Domestic abuse — the effect share could not be produced at all.** It was said to stand for the
   Cochrane odds ratio, but the largest absolute reduction an odds ratio can give at any baseline
   is `(1 − √OR)/(1 + √OR)`, which is **0.2079 at OR 0.43** and **0.2311 at OR 0.39** — both below
   the 0.25 shipped. It was also an impact in an outcome-rate slot, so an attribution was applied
   on top of it. Rebuilt on the trial's own arm rates, which are a rate and a fraction respectively.
3. **Debt advice — the row that needed both answers.** Its central rests on a null randomised
   result, an impact, so it takes 1.0; its high rests on a self-reported outcome rate, so it takes
   an attribution. The unsourced 0.7 that served both is withdrawn.
4. **Drug and alcohol — already right, and the only row where the double count had been
   consciously avoided.** Its effect-share slot holds a benefit-cost ratio rather than a share,
   which is why its value exceeds one, and its attribution is 1.0 precisely so the adjustment is
   not repeated. Unchanged.

**Housing is the row the rule cannot rescue.** Its effect share of 0.20 has no source and is now
declared an assumption with its reason: every published rate is post-placement tenancy sustainment
of 80 to 96 per cent, on a denominator of **people already housed**, and the referral-to-placement
conversion that would connect those to a referred caseload is published nowhere. Its attribution
is now sourced, but from an **intensive Housing First model with assertive community treatment for
people with severe mental illness**, where this row is generic housing support — a scope mismatch
that travels with the number and is more likely to overstate the fraction than understate it.

## 3. Derived values (exist only after this step)

### Greek VSL — income-scaled transfer (NOT PPP)
OECD (2012) income-elasticity benefit transfer, every ingredient:
- Base VSL: **USD 3.6m** (2005 USD; OECD 2012 EU base; range 1.8–5.4m).
- Uprate 2005 → 2024 in USD (FRED GDPDEF): 125.422 / 81.551 = 1.537958 → **USD 5,536,648** (2024).
- Income scaling: (GNI Greece / GNI EU)^0.8 = (22,730 / 41,076.43)^0.8 = 0.553359^0.8 = **0.622881**.
- Income-scaled: 5,536,648 × 0.622881 = **USD 3,448,675** (2024).
- Convert to EUR (Eurostat `ert_bil_eur_a` 2024, 1.0824 USD/EUR): 3,448,675 / 1.0824 = **€3,186,137 ≈ €3.19m** (2024).
- Elasticity 0.8 (OECD 2012 central). Flag: **OECD income-scaled transfer.**
- **Method note:** the VSL uses income-elasticity scaling because that is the OECD's documented benefit-transfer method; the WELLBY uses PPP because that is the health-economics standard for per-person value transfer. The two methods differ deliberately, each following its source's convention.

ES and IT use their **national** VSLs, uprated on their own deflators, no income-scaling:
- ES road-context CV/SG €1.3–1.7m (2017) × 1.218311 = **€1.58m – €2.07m** (2024). Hedonic-wage bounds €2.0–8.3m (2000–2008) are a multi-year sensitivity, carried native, not uprated here (flag).
- IT €1.022m median / €2.264m mean (2004) × 1.432369 = **€1.46m / €3.24m**; upper anchor €6.437m (2011) × 1.256074 = **€8.09m** (2024).

### Drug averted-death rate — treated-cohort basis
Sordo et al. (2017): out-of-treatment 36.1 vs in-treatment 11.3 per 1,000 person-years (RR 3.20). Averted-death rate = 36.1 − 11.3 = **24.8 per 1,000 OST patient-years**. The Provider mode multiplies this by the provider's OST caseload and the national VSL. Flag: **derived**; the mortality rates are the Sordo international cohort, transferred to all three countries. The EUDA national drug-induced-death figures (ES 38/million 2022, IT 6/million 2023, EL 35/million 2021; *European Drug Report 2025*, Annex Table 6) are national-scale context and a plausibility check, **not** the multiplier. The drug cell values averted mortality only — a strict subset of the UK CONVENTIONAL drug figure, not comparable as equals.

---

## 4. PPP cross-check, fallbacks, caveats

- **PPP factors used.** UK→ES 0.861941, UK→IT 0.915660, UK→EL 0.816996 (OECD per-USD, EUR/GBP). IT→ES 0.932084, IT→EL 0.881460, ES→EL 0.945687 (Eurostat EUR/PPS). Single 2024 round.
- **Cross-check (single-round consistency):** euro-area price-level ratios agree across sources within ~1% — IT→ES OECD 0.9413 vs Eurostat 0.9321; ES→EL OECD 0.9479 vs Eurostat 0.9457. Eurostat PLIs (EU27=100): EL 86.0, ES 90.9, IT 97.5.
- **Fallback flagged:** OECD HFCE PPP for the UK-crossing conversions (spine, homelessness), because they are the ones the shipped spines were built from and they reproduce exactly. Same 2024 round as the Eurostat euro-area PPP.
- **Provisional data:** Eurostat 2024 deflator and PPP values carry provisional status ("p").
- **EL GBV native year:** the EIGE Greece €2.4bn is taken at a 2016 basis per the foundation's label; its precise price-base year is not independently pinned (flag).
- **NOT FOUND:** none. Every series required was retrieved with its identifier.

## 5. Data-free confirmation
Parameters, series identifiers, and citations only; no microdata. All figures 2024-equivalent by the settled method (uprate-then-PPP, own-country deflator, single 2024 HFCE-PPP round). The native layer, `PROVIDER_EVIDENCE_EU.md` and `PROVIDER_DECISIONS.md`, is unchanged: this layer computes over it and alters no value in it. All four dial tools (UK, Spain, Greece, Italy) are built as template swaps and pass the gate defined in `europe/tool_machinery/README.md`; this provider layer is embedded in the ES/EL/IT tools and cross-checks to it exactly.
