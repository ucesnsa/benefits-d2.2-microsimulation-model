# BENEFITS D2.2 — Microsimulation valuation tools

**Deliverable D2.2 of BENEFITS** (Horizon Europe, grant agreement No. 101179032,
HORIZON-CL2-2024-TRANSFORMATIONS-01, Work Package 2).

Four browser-based tools — **United Kingdom, Spain, Italy, Greece** — that report the
**distributional welfare, fiscal, and service-load** effects of tax–benefit reforms and
economic shocks, and the **social value-added of social services**. Each reads a
pre-computed response surface, so the tools run entirely in a browser with no server, no
installation, and no network access.

**This repository ships code, documentation, tools, and aggregate results only. It contains
no microdata.**

**Everything here can be checked without a licence.** The four tools open in a browser, and
the whole verification suite — the drift checks, the live browser assertions, and the three
mutation suites that prove those assertions can fail — runs from a clean copy with nothing
but Python 3.9 and Chrome. No microdata, no engine licence, no network. What cannot be done
here is rebuilding a response surface, which needs the licensed microdata and the matched
engine; see [Requirements](#requirements).

---

## Quick start

Open any of these in a web browser. Nothing else is required.

```
uk/tools/dial_tool_uk.html
europe/Spain/tools/dial_tool_spain.html
europe/Italy/tools/dial_tool_italy.html
europe/Greece/tools/dial_tool_greece.html
```

Each has four tabs: **Home** (method and provenance), **Analyst** (reform dials),
**Provider** (service value-added and capacity), **Scenarios** (a fixed menu with a
cross-scenario comparison). Every figure carries a provenance mark, and every panel that can
be screenshotted on its own carries the legend that explains the marks.

### Checking a figure you are looking at

A figure with **no mark** rests only on national sources or on values derived from them. A
single star means one input was borrowed from another country with a stated adjustment; a
double star means an input was borrowed without adjustment, or is an assumption. A figure
takes the worst grade of the inputs behind it, and a dagger means it rests on a unit cost
**you** entered rather than one of ours. Hovering a mark gives the same wording.

To go from a mark to the evidence:

1. **On the Provider tab**, each service carries its own note: the origin figure, the
   factor applied to it, the price base, and the source each came from.
2. **`europe/docs/VALUATION_CHAINS.md`** prints every provider outcome value whose note carries an ORIGIN clause as
   `raw x effect share x attribution`, with all three factors beside the value they produce,
   recomputed from each parameter's own note rather than transcribed.
3. **Analyst figures** are read from that country's `dial_grid.json`, the response surface.
   `check_drift.py` asserts that the copy embedded in the page is identical to it, so the
   number on screen and the number in the surface cannot disagree.

---

## Scope

### What the tools do

| tab | what it reports |
|---|---|
| **Analyst** | Move one reform dial at a time and read the welfare, distributional, fiscal and poverty effects. Welfare is the **WEVM**, a distributionally weighted equivalent-variation measure, reported across an inequality-aversion grid ε ∈ {0, 0.5, 1, 1.5, 2}. |
| **Provider** | Enter a catchment and a running cost and read the monetised social value-added of a service, its benefit-cost ratio, and the extra demand an unemployment shock would place on it. **Everything on this tab is per person.** A provider may enter their own unit costs, which then carry their own provenance mark. |
| **Scenarios** | A fixed menu per country — the baseline plus 15 for the UK, the baseline plus 12 to 13 for the EU three — with fiscal, service-load and welfare lenses, and a cross-scenario comparison that re-sorts with ε. |

### What is modelled

* **United Kingdom** — 7 dials plus one binary toggle, built on **PolicyEngine UK 2.45.4** /
  policyengine-core 3.23.6 over the **Family Resources Survey 2023/24**.
* **Spain, Italy, Greece** — 5 dials each, built on **EUROMOD v3.8.6** over **EU-SILC**
  (2024 wave; 2023 income reference year and 2023 policy systems).

Reforms are modelled **one at a time**. Reforms interact, so combined effects are not
additive and the tools never display them as such.

### What this repository does not contain

* **No microdata.** The FRS and EU-SILC are licensed and held outside this repository. See
  *Data policy* below.
* **No engines.** PolicyEngine and EUROMOD are open source but are not redistributed here.
* **The D2.2 technical report and the four country user guides are in `Documents/`**, as PDF
  and as LaTeX source.

---

## Requirements

Three different things need three different amounts of setup. **Only the first is needed to
use the tools.**

### 1. To open and use the tools — a web browser

Nothing else. The tools are self-contained single HTML files that read no network and write
nothing. They work offline.

### 2. To verify the repository — Python 3.9 and Chrome

Every check below runs from a clean copy with nothing installed but **Python 3.9** and
**Chrome or Chromium**. Two of the ten need two ordinary packages and say so.

**`py -3` is the Windows Python launcher.** On macOS and Linux run the same commands with
`python3` in its place.

| command | what it proves |
|---|---|
| `py -3 check_parses.py` | every Python file in the tree compiles. 92 files |
| `py -3 check_drift.py` | each page's embedded grid matches its canonical surface, its embedded block matches its authoring file, the page with its data block masked out is byte-identical to `template.html`, the scenario figures match the surface, and every relational claim in each scenario statement is re-derived from the surface at every ε. 20 checks, 5 per tool |
| `py -3 check_browser.py` | loads all four tools in headless Chrome and asserts the contract, including Horizon Europe Article 17 visibility. 61 assertions per country, 244 in total |
| `py -3 tests_negative_drift.py` | breaks 10 things on purpose and requires each to be caught |
| `py -3 tests_negative_browser.py` | breaks 43 things on purpose and requires each to be caught, so the assertions above are load-bearing |
| `py -3 tests_negative_provider.py` | breaks 11 things on purpose in the valuation layer, driving the 7.10d check in `audit_provider_params.py` that recomputes every converted outcome value from the origin and factor its own note states |
| `py -3 europe/tool_machinery/refresh_blocks.py` | re-embeds each canonical surface into its country block. The only sanctioned way to update a block's `grid` key; `--check` reports staleness without changing anything |
| `py -3 europe/tool_machinery/refresh_scenarios.py` | rebuilds the scenario menu in a country block from that country's surface |
| `py -3 europe/tool_machinery/classify_provenance.py` | derives each figure's provenance grade, so the `*` and `**` marks are computed and never applied by hand |
| `py -3 europe/common/validate_grid.py <surface>` | structure, monotonicity and identities on any one of the four `dial_grid.json` |
| `py -3 europe/common/re_emit.py verify` | folder-only provenance proof for the three EU surfaces. **Needs `numpy`** |
| `py -3 uk/model/demo/check_fixture.py` | loads the committed **synthetic** fixture through the welfare layer and asserts it is schema-valid. **Needs `pandas`, `numpy`, `pyarrow`** |

### 3. To rebuild a response surface — not possible from this repository, by design and by licence

Rebuilding needs the microdata and the matched engine, neither of which is here:

* the **UK** pipeline needs PolicyEngine and the FRS;
* the **EU** builders need **EUROMOD v3.8.6 specifically** and the gated EU-SILC user
  database. The engine guard in `europe/common/engine.py` refuses to run on an unmatched
  engine, deliberately: the connector's bundled engine aborts Italy and Spain. These paths
  are Windows-only as written.

This is not a defect. The tools read a pre-computed surface precisely so that *using* them
requires none of the above.

---

## What is in here

```
uk/            the UK tool, its surface, its model code and its own documentation
europe/        Spain, Italy and Greece: tools, surfaces, model code, and the shared tool
               machinery (template.html + one country_<cc>.json per country)
Documents/     the technical report and the four country user guides, PDF and source
assets/        the EU emblem and project logos, with their usage rules
*.py           the verification suite, run from the repository root
```

**How the tools are built, and the one rule that matters.** Every country tool **is** the
single `europe/tool_machinery/template.html` with a swapped `country_<cc>.json` data block,
instantiated by `instantiate.py`. To change a tool or add a country you edit a country block
and re-instantiate. **Never hand-edit a tool file.** A from-scratch build is the exact failure
this deliverable was written to correct, and `check_drift.py` proves all four pages are one
template by comparing a masked-block hash across them.

### Documents

| document | covers | where it goes | status |
|---|---|---|---|
| **D2.2 technical report** | all four tools | `Documents/BENEFITS___D2_2_Tech_Report.pdf` | present |
| **D2.2 user guide, United Kingdom** | the UK tool | `Documents/USER_GUIDE_UK_D2_2.pdf` | present |
| **D2.2 user guide, Spain** | the Spain tool | `Documents/USER_GUIDE_SPAIN_D2_2.pdf` | present |
| **D2.2 user guide, Italy** | the Italy tool | `Documents/USER_GUIDE_ITALY_D2_2.pdf` | present |
| **D2.2 user guide, Greece** | the Greece tool | `Documents/USER_GUIDE_Greece_D2_2.pdf` | present |
| UK edition technical report | the UK tool only | `uk/docs/TECHNICAL_REPORT.md` | present |
| UK methods | the UK tool only | `uk/docs/METHODS.md` | present |
| Quick starts | one per EU tool | `europe/{Spain,Italy,Greece}/docs/QUICKSTART.md` | present |

The UK edition technical report and UK methods cover one tool of four and are cited throughout as UK sources.

---

## Verification

Verified from a clean export with nothing installed but Python 3.9 and Chrome.

| check | result |
|---|---|
| `check_parses.py` | **PASS**, 92 of 92 Python files compile |
| `check_drift.py` | **PASS**, 20 of 20 (5 per country) |
| `check_browser.py` | **PASS**, 244 of 244 (61 per country) |
| `validate_grid.py`, all four surfaces | **PASS**: UK 6/0/0; ES, IT, EL 5 pass 1 warn 0 fail each |
| `re_emit.py verify`, ES / IT / EL | **ALL COUNTRIES PASS** |
| `check_fixture.py` | **SCHEMA GUARD: ALL PASS** |
| `tests_negative_drift.py` | **10 of 10** mutations caught |
| `tests_negative_browser.py` | **43 of 43** mutations caught |
| `tests_negative_provider.py` | **11 of 11** mutations caught |

The three mutation suites exist because a passing check proves nothing unless it can fail. Each
mutation breaks exactly one thing an assertion claims to protect, and the suite passes only
when that assertion fails on the mutated page.

Masked-block sha256, the proof all four pages are one template:
`ebe868f47ec59f61d676487a5c9ba5a8987f19cd717cc748a5678a2f4417cd19`

The four tools:

```
e3da96c2a005f6ea572e77417df72c15b9ac5c04c157f4d8d26d9cec58944ed5  uk/tools/dial_tool_uk.html
0b54742675bfbf991bcb23871c205ae322e38421776e9955e1c40db609a0b821  europe/Spain/tools/dial_tool_spain.html
f6885a30b7b05dd53b616e1ebdd4bcf1cf96e78885cfc02f72e88a030a8780c9  europe/Italy/tools/dial_tool_italy.html
a5efc6549dcd0b30fa2660c326ebac7579ec60163e279b4b2a00035d7822e9d9  europe/Greece/tools/dial_tool_greece.html
```

The four surfaces:

```
99225b6d913e4ad3dcbcff440a40885cde1a1529261552abbe9e302df29d5499  uk/outputs/dial_grid.json
3bcc34df9bf812ccde610b5b70e3e37c0c25f92208cc19eab41405603b515a0c  europe/Spain/outputs/dial_grid.json
32d3bcf6ee428bea3067c37e62a8d08f82007660b0d77a2a3ed0fcbd60b88165  europe/Italy/outputs/dial_grid.json
9d9cbda10320c2355ec6503ac3e50e3533a00f3eca6fbdb2eae46b2248f83b0e  europe/Greece/outputs/dial_grid.json
```

This block goes stale whenever a script is added or a surface is rebuilt, so **re-run it
rather than reading it**.

---

## Data policy

**No microdata is included, and that assertion is literally true of every file here.**

* The **UK FRS** and the **EU-SILC** user database are licensed and are held outside this
  repository entirely.
* Every result is an **aggregate**: response surfaces, weighted population totals, decile
  contributions, and counts.
* `uk/model/demo/per_unit_export.parquet` is **synthetic**, generated for the schema guard,
  and carries a warning file beside it saying so.
* **The published copy contains no non-aggregate row of any kind.** In the working tree the
  build's engine console log, and the two documents that quote it, carried 27 EU-SILC record
  keys — 21 person and 6 household — inside EUROMOD's own uprating warnings. They are the
  survey's anonymised keys and identify nobody, but they were the only non-aggregate rows
  anywhere in the project. None of those three files is published here, and the keys are
  redacted independently of that, so the assertion holds by two separate mechanisms rather
  than one.

---

## Honest limitations

**This repository documents what it cannot do as carefully as what it can.** Anyone using or
reviewing these tools should read:

* **`europe/docs/DATA_ISSUES_FOR_TECHNICAL_REPORT.md`** — the classed list of every data
  limitation, each with its size and its consequence, including the three residuals that
  remain **unexplained** rather than explained.
* **`europe/docs/ppp_deflator_pull_2026-08-03.json`** — the source pull behind the PPP
  factors and the GDP deflators, with the query strings and the extraction date. Re-run it
  with `py -3 europe/model/pull_ppp_deflators.py --check`.

### What these tools cannot tell you

Each of these is disclosed on the tool face as well, and each has a size or a direction
attached rather than being a general caution.

1. **The EU surfaces run EU-SILC through EUROMOD, not EUROMOD's own bundled input dataset**
   (the EMSD), which applies its own harmonisation and imputation. The welfare and
   distributional results are validated against the EUROMOD Country-Report baseline. **The
   effect of that input-preparation difference on the fiscal figures is not quantified**, and
   cannot be without the EMSD.
2. **Greek self-employment is under-captured**, at 0.48 times the household-sector B3G and
   below even the tax-declared figure. Greek employment is also low at 0.88 times D11. The
   Greek downturn and unemployment dials are therefore **biased downward: their income-side
   fiscal figures are a lower bound**, not a central estimate.
3. **The unemployment dial confers no benefit entitlement in any of the three EU countries.**
   Flipping a person out of work removes their earnings but grants no contributory
   unemployment benefit, so **the modelled fiscal cost of an unemployment shock is
   understated**. Spain's contributory unemployment is separately under-simulated, at about
   EUR 3.5bn against roughly EUR 20.6bn in the survey, because the public EU-SILC release
   carries no contribution or duration history.
4. **The downturn dial is not the same experiment in the UK as in the EU.** The UK routes it
   through a transmission to unemployment; the EU tools scale market income directly. Each
   labels its own dial honestly, but **the dial is not comparable across countries** and any
   cross-country reading of it must say so.
5. **Capital and property income are under-captured throughout**, which is inherent to
   EU-SILC. Absolute figures for investment income and wealth taxation should be read with
   that in mind.
6. **The 2024 deflators are Eurostat provisional** and may revise.
7. **The provider layer is heavily transfer-based**, most of all for Greece. The WELLBY spine
   and the employment coefficient are UK values transferred to all three EU countries, and
   every transferred or assumed input is marked `*` or `**` on the tool face, with the mark
   propagating to any headline computed from it.
8. **Four of the fifteen UK scenarios do not sit on a stored grid point** — two combine a
   downturn with a policy response, which a single-reform surface cannot represent, and two
   sit at a magnitude their dial does not carry. Their poverty rows are left blank rather than shown on another
   basis.
9. **The Greek and Italian self-employed contribution lines carry an uncorrected conversion
   defect.** Both converters set `ysemy`, the months count those contributions scale with, to
   twelve for everyone with self-employment income, while the employee equivalent one line above
   reads the months-worked variable. Spain had the same line and correcting it moved its
   divergence from +41.3 to +18.5 per cent. **The fix is one line and is not applied in either
   country**, because it would move a published surface. The direction is certain even though the
   size is not: correcting it lowers self-employed contributions, so it **narrows Italy's +93.8
   per cent and widens Greece's −25.0 per cent**. `ysemy` is an input variable and appears
   nowhere on the tool face, so unlike the items above this one is disclosed in the
   `DATA_ISSUES_FOR_TECHNICAL_REPORT.md` ledger (EL-10, IT-12) and in `CONVERSION_RECORD.md`
   rather than on the tool itself.

---

## Year convention

The tools reference the **EU-SILC 2024 wave** as the single data-year anchor; income reference
year (2023) and policy-system year (2023) are provenance. Analyst money is 2023 nominal EUR
**displayed in 2024 EUR** using each country's own Eurostat deflator; Provider money is
2024-equivalent EUR. The UK is already at 2024 prices.

---

## Licence and citation

Four licences apply, and which one applies to a file depends on what that file is.

| what | licence | where the text is |
|---|---|---|
| The code this project wrote | **MIT** | [`LICENSE`](LICENSE) |
| The documents, the four HTML tools, and the response surfaces, as distributed | **CC BY 4.0** | [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0) |
| Any file that reaches PolicyEngine, directly or through another module in the tree | **AGPL-3.0** | [`uk/model/Code_FRS_23_24/LICENSE`](uk/model/Code_FRS_23_24/LICENSE) |
| Any file that reaches the `euromod` connector, directly or through another module in the tree | **EUPL-1.2** | the `LICENSE` file in each directory where such files are concentrated |

What is not MIT is not MIT because of what it imports, and the rule is the same in both
cases. A file that imports an engine carries that engine's licence, whether it imports it
directly or reaches it through another module in this tree: AGPL-3.0 for the files driving
PolicyEngine, EUPL-1.2 for those reaching the `euromod` connector. Both are reciprocal
licences, so they reach the importing code and no further; a file that reaches neither
engine is MIT. A `LICENSE` file sits in each directory where such files are concentrated,
and the files that import a connector directly carry a header naming the licence and why.

**The surfaces are granted subject to the terms of the underlying microdata agreements.** The
CC BY 4.0 grant is this project's grant of its own work. It cannot and does not license the
microdata the surfaces were computed from: the UK Family Resources Survey, held under its UK
Data Service End User Licence, and the EU-SILC User Database, held under the Eurostat Research
Project Proposal that governs it. Only aggregates are published here. Anyone redistributing or
rebuilding from these surfaces remains bound by those agreements.

**Neither engine is redistributed here.** [`NOTICES.md`](NOTICES.md) records every dependency
with its licence, together with both engines and the `euromod` connector, and states how each
licence was read rather than assumed.

Suggested citation:

> BENEFITS (Horizon Europe grant agreement No. 101179032), *Deliverable D2.2: Microsimulation
> valuation tools*, 2026.

Figures produced by these tools are **model output, not official statistics**. Each tool's
citable export says so, together with the engine and data wave it used and the provenance
marks carried by the figures exported.

---

## Funding

![Funded by the European Union](assets/eu_funded.png)

Funded by the European Union. Views and opinions expressed are however those of the author(s)
only and do not necessarily reflect those of the European Union or the European Research
Executive Agency. Neither the European Union nor the granting authority can be held
responsible for them.

BENEFITS, Horizon Europe grant agreement No. 101179032,
HORIZON-CL2-2024-TRANSFORMATIONS-01, European Research Executive Agency (REA).
