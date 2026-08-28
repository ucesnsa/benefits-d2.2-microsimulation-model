# BENEFITS D2.2 — Country-tool machinery (the swap contract)

This folder holds the **one sanctioned way** to produce a country tool. A country tool **IS** the UK tool with a swapped data block — never a rewrite. Spain is the completed reference; Italy and Greece are a **pure data swap**.

## What a country tool is

`dial_tool_uk.html` (the UK 4-tab tool: Home · Analyst/dials · Provider · Scenarios) is the standard. `template.html` here is that exact tool with every country-varying value lifted into a single placeholder, `const COUNTRY=__COUNTRY_JSON__;`. A country tool is `template.html` with `__COUNTRY_JSON__` replaced by that country's COUNTRY block. **Nothing else changes.** The template's structure, CSS, machinery, card copy, epsilon treatment, WEVM ladder, capacity-gap model, scenario lenses and footer are identical for every country.

## Files

- **`template.html`** — the country-generic 4-tab template (`__COUNTRY_JSON__` placeholder). Do not edit per country.
- **`instantiate.ps1`** — `template.html` + a COUNTRY block → a finished tool. Location-independent.
- **`instantiate.py`** — the same instantiator for macOS/Linux (Python port, identical semantics): `python3 instantiate.py country_it.json ../Italy/tools/dial_tool_italy.html`.
- **`country_uk.json`**, **`country_es.json`**, **`country_el.json`**, **`country_it.json`** — the UK, Spain, Greece and Italy COUNTRY blocks (the only country-varying content). The EU set (ES/EL/IT) is complete; each instantiates the same template.
- **`refresh_blocks.py`** — rewrites each COUNTRY block's embedded grid from its canonical surface, so the grid in a block is never filled or corrected by hand.
- **`refresh_scenarios.py`** — rewrites the EU blocks' precomputed SCENARIO figures from their own grids, on the same principle.
- **`classify_provenance.py`** — stamps `provenance` and `provenance_note` onto the blocks' operational provider layer.

## To build Italy or Greece

1. Copy `country_es.json`, the completed reference block, to the new country's `country_*.json` and refill it against that country's `outputs/dial_grid.json`: currency/locale, `deflator`, `wellby_spine`, `toggle` (null), the country's dial text with concrete national anchors, the country's provider values + flags, the country's scenario menu and spine/crossover, and the country caveats. Run `refresh_blocks.py` and `refresh_scenarios.py` to write the embedded grid and the precomputed scenario figures; neither is filled by hand.
2. `./instantiate.ps1 -countryJson country_it.json -outPath ..\Italy\tools\dial_tool_italy.html`
3. **Pass the same gate Spain passed** (below). If it does not pass, the block is wrong — never patch the template per country.

## The gate (every country must pass)

- **(a)** UK-vs-country diff, with the `const COUNTRY=…` block masked, is **byte-identical** — the only difference is the data block.
- **(b)** file size comparable to the template, not a fraction.
- **(c)** all four tabs render live in a browser with **zero page console errors** (the Chrome-extension `:0:0` message-channel noise is not a page error).
- **(d)** the per-point `fiscal` sub-object threads to the Analyst fiscal card.
- **(e)** every caveat the country's own block carries — `dial_caveats`, `unemployment_caveat`, `capacity_caveat` — surfaces on the tool face, and the scenario labels are that country's own and not another's.

Currency, locale and the display deflator come from the COUNTRY block; do not hardcode them.
