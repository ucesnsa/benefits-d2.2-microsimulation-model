# The provider tool for all EU member states (version 2)

`BENEFITS_Provider_Tool_EU27_v2.html` is one self-contained page that carries the Provider tab
of the D2.2 tools to all 27 EU member states. Open it in a browser; it needs no server and no
network.

**Version 2 is the Provider tab only.** The Analyst and Scenarios tabs exist for Spain, Italy,
Greece, and the United Kingdom, in the four country tools of this repository
(`europe/{Spain,Italy,Greece}/tools/`, `uk/tools/`). **The United Kingdom is not in this
page**: its provider valuation is the Provider tab of the UK tool.

A country picker chooses the member state, and a switch chooses between two views of the same
calculation:

* **Plain language**: a provider-facing page with a Home tab that explains each input and
  each result in words.
* **Full detail**: the D2.2 Provider tab itself, with every row, grade, and source note.

Both views read the same country block, and a check (below) proves they give the same answers.

## Where the numbers come from

Every value carries its source and a provenance grade in its own note, visible in the full
view, and the grades follow the same rules as the four country tools: no mark for a national
source or a value derived from one, one star for a value borrowed from another country with a
stated adjustment, two stars for a value borrowed without adjustment or an assumption.

* **The rule is the best available evidence for each country.** Where a verified national
  figure measures the service's unit, it is used. Where none exists, the best figure found
  elsewhere is transferred: staff-time unit costs on health-and-social-work labour cost
  (Eurostat `lc_lci_lev`, NACE Q), outcome values on household-consumption purchasing power
  parity (Eurostat `prc_ppp_ind`, E011), after uprating on the source country's GDP deflator
  (`nama_10_gdp`) to 2024. Of the 297 unit costs (11 services in 27 countries), 53 are
  national; of the 243 outcome values that are not zero, 21 are national.
* **Spain, Italy, and Greece carry exactly the provider values of their D2.2 country tools**,
  including the income effect, which is modelled with EUROMOD v3.8.6 on EU-SILC (2024 wave,
  2023 incomes) and brought to 2024 prices on the country's GDP deflator.
* **For the other 24 countries the income effect is estimated**, from the national
  minimum-income outlay (EUROMOD's external statistic for the main minimum-income instrument,
  with named exceptions) and Eurostat income deciles. Tested on the three modelled countries,
  the estimate's mean absolute error is 3.6% against each model's own outlay and 18.6% against
  actual outlays. The page says so for every such country.
* **The shock view is indicative.** For Spain, Italy, and Greece the share of households that
  lose an earner comes from each country's own EUROMOD surface. For the other 24 it is the UK
  model's own share, applied to each country's working-age households (Eurostat `ilc_lvps02`,
  a lower bound).

The technical report (`Documents/`) sets out the method in its section on the provider tool
for all EU member states, and its appendix tabulates the unit cost and central outcome value of
every service in every country.

## What is in this directory

```
BENEFITS_Provider_Tool_EU27_v2.html   the tool
build/                                the build, the checks, and their outputs
  make_frame.py                       per-country frame from Eurostat (writes frame/)
  make_data.py                        the 27 country blocks (writes data/)
  views.py, make_full_template.py,    the two views, from europe/tool_machinery/template.html
  make_lite_template.py               and plain_language_source.html
  build_tool.py                       assembles the page
  apply_to_v1.py                      writes the Spain, Italy, and Greece provider values, and
                                      the UK cash-floor uprate, into the four country blocks
  check_full_vs_shipped.py            positive control for the full view (below)
  check_views.py                      the two views against each other (below)
  mutate_views.py                     proves check_views.py can fail (below)
  make_evidence_table.py              the evidence tables (writes report/)
  frame/, data/, checks/, report/     their outputs, as committed
evidence/
  extra_income/                       the income-effect estimate for the 24 countries, its
                                      inputs, and its validation (extra_income_results.json)
  tables/                             a transcribed source table (FEANTSA 2013, Table 5.2)
  verify/verdicts.jsonl               the second check of each research record below
research/
  country_income/findings.jsonl       the minimum-income records the estimate reads
  used/findings.jsonl                 every other research record a value rests on
series/                               the Eurostat series the income estimate reads
```

`build/report/used_records.json` lists the 133 research records the values rest on, each with
its verdict: `PASS`, `PARTIAL`, `MEANING_MISMATCH` (the figure is right but measures something
else, so it is used only as its note describes), or `FAIL`. The two records that failed were
recomputed from the published figures, and the value in the tool is the recomputed one; the
reason is recorded under `corrected_on_verification`.

A research record has these fields: `id`, `section`, `service`, `country`, `value`,
`value_low`, `value_high`, `unit`, `currency`, `price_year`, `reference_year`, `definition`,
`source` (`authors`, `year`, `title`, `publisher_or_journal`, `url`, `doi`, `locator`),
`source_type`, `opened` (whether the source itself was read), `derivation`, `applicability`,
and `quality_note`.

## Rebuilding and checking

Standard-library Python 3.9 throughout; the three checks also need Chrome or Chromium
(`CHROME_BINARY` overrides the search). Run from this directory:

```
py -3 build/make_full_template.py
py -3 build/make_lite_template.py
py -3 build/make_data.py
py -3 build/make_evidence_table.py
py -3 build/build_tool.py
py -3 build/check_full_vs_shipped.py
py -3 build/check_views.py
py -3 build/mutate_views.py
```

`make_frame.py`, `series/pull_eurostat.py` and `evidence/extra_income/extra_income.py --pull`
re-read Eurostat over the network; without them the build uses the committed pulls.
`extra_income.py` reads EUROMOD's country files if EUROMOD is installed, and otherwise its
committed extract of them (`euromod_extstat.json`, with each file's sha256).

| check | what it proves |
|---|---|
| `check_full_vs_shipped.py` | filled with the Spain, Italy, and Greece country blocks, the full view renders exactly what each country tool's Provider tab renders: 397 configurations per country (every service, three income profiles, three inequality-aversion settings, two reference reforms, two shocks), compared on the value, shock, and evidence panels, and the labels compared once |
| `check_views.py` | for all 27 countries, the plain-language view's `calc()` and the full view's `renderProvider()`, two separate code paths, give the same headline (low, central, high), benefit-cost ratio, extra demand, and extra budget, and fill in the same running cost and staff default: 77 comparisons per country, 2,079 in all |
| `mutate_views.py` | five defects, each planted in one view only, are each caught by `check_views.py` |

## Licence

The code in this directory is under the MIT licence (`LICENSE` at the repository root); the
tool, the country blocks, and the research records are under Creative Commons Attribution 4.0
(`LICENSE-CC-BY-4.0`). The Eurostat series are Eurostat's, reused under the Commission's reuse
policy with the source named on every value; every other source is cited in the record that
uses it.
