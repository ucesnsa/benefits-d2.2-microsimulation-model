# UK tool — quick-start guide

*A plain-language card for anyone who just wants to use the tool and read the answer. (For the fuller analyst/methodology walk-through, see [the UK user guide](../../Documents/USER_GUIDE_UK_D2_2.pdf).)*

**What it is.** A one-page interactive tool for the UK: move a reform or a shock and instantly see **how much better or worse off households are**, **what it costs the public purse**, and **who gains and loses**. It reads pre-computed results (Family Resources Survey 2023-24) — it does **not** run a live model — and shows money in **2024 pounds**. Open `uk/tools/dial_tool_uk.html` in any web browser; nothing to install.

**The 30-second version.** Click a tab along the top. On **Analyst**, drag one slider and read the answer. On **Scenarios**, pick a ready-made reform and compare. On **Provider**, enter your caseload and read what your service is worth. The **Home** tab explains everything, inside the tool.

## The four tabs

**Home** — what the tool is, what each dial does, and how to read the numbers. Start here first time.

**Analyst — move one reform, read the effect.**
1. **Set ε (epsilon)** first — the one control that's a value judgement, not a result (see below).
2. **Drag one slider.** Seven sliders: minimum income (the Universal Credit standard allowance), Child Benefit, the personal allowance (the income-tax threshold — a *higher* allowance means *less* tax, shown as a gain), a GDP shock, an unemployment shock, the UC taper, and the UC work allowance. Plus one on/off switch: remove the High Income Child Benefit Charge.
3. **One at a time.** Move any slider and the others snap back to normal — the tool only shows one reform at a time, because two reforms together are not simply the sum of their parts.
4. **Read** the welfare figure, the little ε strip beside it, the winners-and-losers split (shares of benefit units, not of people), and the decile chart (which part of the income range the change lands on).

**Scenarios — compare ready-made reforms.** The baseline plus fifteen fixed reforms and shocks (for example UC standard allowance +10%, raise the personal allowance, unemployment +5pp, plus two combination scenarios), each with its **cost**, **service-load**, **welfare** and **value-for-money**, plus a full ε-ranking and the **crossover** (below).

**Provider — value your service.**
1. Enter your service type, how many people you help a year, who they are (lowest incomes / low-to-middle / broad mix), and optionally your running cost.
2. Read the **value ladder** top to bottom: a conservative **cash floor**, a fuller **headline** (adds the service's social benefits), a **low–central–high band** (real uncertainty — carry the whole range), and a **benefit-cost ratio** (social value per £1 you spend).
3. The **capacity view** projects demand against your staffing (a rough planning aid, not a local forecast).

## What each number means (in plain words)

- **Welfare figure** — how much better or worse off households are, in money, after counting £1 to a poorer household as worth more than £1 to a richer one.
- **Fiscal figure** — what the reform costs (or saves) the public purse in a year.
- **Winners / losers** — the share of households that gain versus lose.
- **ε (epsilon)** — how much extra weight you give to the poorest. **ε=0**: every £1 counts the same (pure efficiency). **ε=1**: the standard middle setting. **ε=2**: strong priority to the poorest. It's *your* choice — slide it and the welfare figure re-reads at that setting.
- **The "spine" (headline comparison)** — the scenarios are ranked by welfare, and the ranking **re-sorts as you change ε**. The headline is a **crossover at about ε≈1.62**: below it, raising the income-tax personal allowance is the highest-welfare scenario; above it, a 3% downturn met with a UC uplift response overtakes it. The two are **not the same size, and not the same kind of thing**: the tool costs the allowance rise at about **£5.5bn** and gives the combined scenario no costing at all, because it is a downturn plus a response rather than a costed reform. So this is a ranking of whole scenarios on welfare, not a comparison of two reforms of matched size — and the difference in size is part of why the ranking crosses: the larger reform leads at low ε, and the more tightly targeted one overtakes it as ε rises. The **Scenarios tab shows this** — the ranking re-sorts as you change ε, and the crossover is spelled out in the cross-scenario panel.

## Good to know

- **Provider values are evidence-based estimates drawn from research**, each tagged **STRONG / MODERATE / WEAK** — quote the band and the tag, never a bare central number.
- The **capacity model is indicative** (rule-of-thumb staffing parameters), not a precise local forecast.
- The tool ships **aggregate results only — no personal data.**
