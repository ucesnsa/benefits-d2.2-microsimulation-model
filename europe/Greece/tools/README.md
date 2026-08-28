# The Greece tool

`dial_tool_greece.html` is Deliverable D2.2's tool for Greece, and it is the whole thing:
one self-contained HTML file. It needs no server, no build step, no installation and no data.
Every figure it shows is already inside it, and it reads nothing from the network.

## Opening it

Open the file in a web browser — double-click it, or drag it onto a browser window. It works
offline.

As you move a control, the tool writes its full state into the address bar: the tab you are
on, which dial is active and how far it is moved, the inequality-aversion setting, the
Provider fields including any unit cost you typed in, and the scenario you have selected.
Copy that address and it reopens on exactly what you were looking at. The address carries the
state and not the page, so anyone you send it to needs their own copy of this file.

## What it reads

The page carries its own copy of the Greek response surface, embedded when the tool was built.
The canonical copy is [`../outputs/dial_grid.json`](../outputs/dial_grid.json), and
`check_drift.py` at the repository root asserts that the two are identical, so the number on
screen and the number in the surface cannot disagree.

That surface was computed with **EUROMOD** over **EU-SILC** (the 2024 wave, 2023 income
reference year, Greece's 2023 policy system). Neither the engine nor the microdata is in
this repository, and using the tool needs neither: the surface is the aggregate result.

## The tabs

* **Home** — what the tool is, what each dial does, where the numbers come from, and how to
  read the provenance mark that every figure carries.
* **Analyst mode** — move one reform dial and read the welfare, distributional, fiscal and
  poverty effects. Five dials, one at a time: moving any dial resets the others, because
  reforms interact and their effects are not additive.
* **Provider mode** — enter a catchment and a running cost and read the monetised social
  value-added of a service, its low-central-high band, its benefit-cost ratio, and the extra
  demand an unemployment shock would place on it. Everything on this tab is per person, and
  you may substitute your own unit cost for one of ours.
* **Scenarios** — a fixed menu of reforms and shocks with fiscal, service-load and welfare
  lenses, and a cross-scenario comparison that re-sorts as the inequality-aversion setting
  changes.

## Where to go next

* **Method** — [`../../../Documents/BENEFITS___D2_2_Tech_Report.pdf`](../../../Documents/BENEFITS___D2_2_Tech_Report.pdf),
  the D2.2 technical report, which covers all four country tools.
* **A walkthrough** — [`../docs/QUICKSTART.md`](../docs/QUICKSTART.md), a plain-language card
  for reading the tool tab by tab.
* **The provider chains** — [`../../docs/VALUATION_CHAINS.md`](../../docs/VALUATION_CHAINS.md),
  which prints every provider outcome value as `raw x effect share x attribution`. It covers
  all four countries, Greece included.
