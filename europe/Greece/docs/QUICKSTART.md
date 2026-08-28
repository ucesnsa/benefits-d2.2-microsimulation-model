# Greece tool — quick-start guide

*A plain-language card for anyone who just wants to use the tool and read the answer.*

**What it is.** A one-page interactive tool for Greece: move a reform or a shock and instantly see **how much better or worse off Greek households are**, **what it costs the public purse**, and **who gains and loses**. It reads pre-computed results (the EUROMOD tax-benefit model on the EU-SILC 2024 survey) — it does **not** run a live model — and shows money in **2024 euros**. Open `europe/Greece/tools/dial_tool_greece.html` in any web browser; nothing to install.

**The 30-second version.** Click a tab along the top. On **Analyst**, drag one slider and read the answer. On **Scenarios**, pick a ready-made reform and compare. On **Provider**, value a service. The **Home** tab explains everything, inside the tool.

## The four tabs

**Home** — what the tool is, the five dials, and how to read the numbers. Start here first time.

**Analyst — move one reform, read the effect.**
1. **Set ε (epsilon)** first — a value judgement, not a result (see below).
2. **Drag one slider.** Five sliders: **minimum income (KEA)** up to +50%; the **child benefit (A21)** up to +50%; the **PIT first-bracket rate cut** (the 9% rate, down to −5 percentage points); an **earnings downturn** (0 to −10%); and an **unemployment shock** (0 to +10 percentage points).
3. **One at a time.** Move any slider and the others reset — the tool only shows one reform at a time.
4. **Read** the welfare figure, the ε strip, the **fiscal cost**, the winners-and-losers split (shares of households, not of people), and the decile chart.

**Scenarios — compare ready-made reforms.** The baseline plus thirteen fixed reforms and shocks (for example KEA +25%, PIT −0.5pp, unemployment +5pp), each with its **cost**, its **winners and losers**, its **welfare** effect and its **value-for-money**, plus the **spine** (below).

**Provider — value a service.** Enter who you help and how many; read the **value ladder** (cash floor → headline → low–central–high band → social value per €1 spent) and the capacity view.

## What each number means (in plain words)

- **Welfare figure** — how much better or worse off households are, in money, after counting €1 to a poorer household as worth more than €1 to a richer one.
- **Fiscal figure** — what the reform costs (or saves) the public purse in a year.
- **Winners / losers** — the share of households that gain versus lose.
- **ε (epsilon)** — how much extra weight you give the poorest. **ε=0**: every €1 counts the same. **ε=1**: the standard middle setting. **ε=2**: strong priority to the poorest. Your choice — slide it and the welfare figure re-reads.
- **The "spine" (headline comparison)** — a minimum-income boost (**KEA +50%**) against a tax cut (**PIT −0.5pp**). The two are **not the same size**: their costs are about **2.1%** apart, with the tax cut the cheaper, so comparing their absolute welfare would mostly tell you which reform is larger. The comparison is therefore **per euro of exchequer cost**. On that measure the two are **exactly equal at ε=0** — 1.000 against 1.000, where welfare is simply the money moved — and the minimum-income boost **pulls ahead as ε rises**: **1.572 against 0.862** at ε=1 and 2.512 against 0.846 at ε=2. It is a statement about ratios, not a claim that one reform beats the other outright.

## Good to know (Greece — read these before quoting a number)

- **The earnings-downturn and unemployment money figures are understated.** Greek self-employment income is only partly captured in the survey (about **half** of the national-accounts total), so those two dials' cost figures are a **lower bound** — treat them as "at least this much." The tool flags this on those dials.
- **The gender-based-violence (GBV) value in Provider mode is borrowed from Italy** — there is no Greek figure, so it is transferred and flagged on the tool's face. Handle it as indicative.
- The **capacity model is indicative**. Its demand elasticities and staff ratios are registry assumptions rather than measured national figures, and the share of households losing an earner is the UK's own share applied to this country's working-age household count, matching the base the UK measures that share on, so only that base is local. The shock magnitudes themselves are computed on this country's own surface.
- Built on the **EU-SILC data** (2024 wave), run through EUROMOD — not EUROMOD's own bundled input dataset (the EMSD), which prepares its inputs its own way. The welfare and distributional results are validated; how much this input difference moves the fiscal figures is not known.
- **Aggregate results only — no personal data.**
