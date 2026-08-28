# The like-for-like sweep: what each published line actually counts

2026-08-03. This document reports the sweep; it is the evidence, not the amendment. When it
was written, `BASELINE_VALIDATION.md` and the `DATA_ISSUES` entries were deliberately left
unchanged so the corrections could be decided rather than applied.

> **All five corrections have since been applied**, later on 2026-08-03. See
> "What this changes, once decided" at the foot, which now records what each one did. The
> evidence below is unedited.
>
> **Two of the three corrections flatter this build, one of them by a factor of nearly
> three.** Italy's self-employed contributions go from +450 to +94 per cent and Greece's
> employer contributions from −32 to +6. That is a reason to show the working, not to soften
> it: each corrected row in `BASELINE_VALIDATION.md` names the table, the row label, and what
> the published line counts, so a reader can check it against the report rather than take it
> from us. The third correction, Greece's self-employed line, moves our figure **further**
> from the published one, −22.8 to −25.0, and is applied on exactly the same footing.

## Why

On 2026-08-02 the published Italian income tax line turned out to be `tinna_s`, national
IRPEF alone, against `ils_taxin`, the whole income-tax list this project was comparing to
it. The comparison was not like-for-like and the residual it produced was overstated by
EUR 12.6bn: the gap fell from 67 to 54 billion, and the two bounded mechanisms then closed
85 per cent of what was left rather than half of it.

The same check had never been applied to any other divergent line. It has now been applied
to all of them, in two halves that are independent of each other:

* **What we compare** is read from the live 2023 systems by
  `europe/model/incomelist_members.py`, which prints every income list's members as the
  model defines them.
* **What the report publishes** is read from the reports themselves, refetched on
  2026-08-03 from the JRC (`Y16_CR_{IT,ES,EL}.pdf`) and read page by page. They are third
  party publications and are not committed here.

## The finding

**Three of the twelve comparisons were not like-for-like. One of them is a unit error, and
it is larger than the income tax one.**

### 1. Italy's self-employed contributions are compared against a COUNT OF PEOPLE

`BASELINE_VALIDATION.md` reports EUR 39,037.4m against a published EUR 7,093m, **+450.4 per
cent**, and `DATA_ISSUES` IT-3 calls it "a live ceiling".

**7,093 is not an amount.** It is the 2023 cell of **Table A3.3, "Direct taxes and SIC -
Number of payers (thousands)"**: 7,093 thousand self-employed people paying contributions,
against an external 3,260 thousand, ratio 2.18. The annual amount is in **Table A3.4,
"Direct taxes and SIC - Annual amounts (millions)"**, and there Italy's self-employed
contributions are **EUR 20,144m** for 2023, against an external **EUR 20,716m**, ratio 0.97.

| | figure | ours against it |
|---|---:|---:|
| A3.3, number of payers (thousands) — **what was compared** | 7,093 | +450.4% |
| **A3.4, annual amount (EUR m) — the like-for-like line** | **20,144** | **+93.8%** |
| A3.4, external annual amount (EUR m) | 20,716 | +88.4% |

**Restated: Italy's self-employed contributions are about 94 per cent above the published
figure, not 450 per cent.** Still the largest divergence in the deliverable, still a live
ceiling, and still worth its tool-face caveat; but a factor of 1.94 rather than 5.5, and the
"several times the published figure" framing does not survive.

The two mechanisms behind it are unchanged and are still the explanation: the contribution
base concept the public release cannot carry, on top of a self-employment base 1.69 times
EUROMOD's own because the tax-compliance adjustment cannot run (IT-1, IT-3).

### 2. Greece's employer contributions are compared against a different concept

`BASELINE_VALIDATION.md` reports EUR 11,434.2m against **EUR 16,850m from `PY030G`**, the
employer contributions EU-SILC itself records, and notes "n/a" for EUROMOD. `DATA_ISSUES`
9.8, written on 2026-08-03, records it as **unexplained, 32.1 per cent below**, and as the
largest of Greece's three contribution gaps.

**EUROMOD does publish a Greek `ils_sicer` baseline**, as the five components of the list,
in Table A3.4 exactly as it publishes the employee list:

| component | 2023 |
|---|---:|
| employer SIC: pension (`tscerpi_s`) | 8,293 |
| employer SIC: sickness (`tscersi_s`) | 1,928 |
| employer SIC: unemployment (`tscerui_s`) | 509 |
| employer SIC: family benefits (`tscerfa_s`) | 0 |
| employer SIC: other benefits (`tscerot_s`) | 89 |
| **`ils_sicer`** | **10,819** |

The list in `EL_2023` has exactly those five members and no others, so the sum is the list.

**Restated: Greece's employer contributions are +5.7 per cent against the model's own
published figure, not −32.1 per cent against the survey.** That puts Greece in line with
Spain at −1.3 per cent and Italy at +0.7 per cent, and it is the third employer-contribution
line in the deliverable to land within six per cent of its published baseline.

`PY030G` is the survey's record of what employers paid across every scheme; `ils_sicer` is
five simulated schemes. They were never the same quantity. The −32.1 per cent is a real
difference between a simulated subset and a survey total, and it belongs in the record as
that rather than as an unexplained shortfall against a baseline.

**`DATA_ISSUES` 9.8 should be withdrawn as an unexplained item.** It is the only one of the
six unexplained items that this sweep closes.

### 3. Greece's self-employed and farmer contributions: the published sum drops a component

The comparator EUR 2,418m was formed by hand from the report's components. The list
`ils_sicse` in `EL_2023` has seven members, and the hand sum has six of them: it omits
**`tscseui_s`, self-employed SIC: unemployment, EUR 71m**.

1,347 + 478 + 71 + 433 + 151 + 9 = **2,489**, against the 2,418 in use.

**Restated: −25.0 per cent, not −22.8 per cent.** Small, and it does not change the
character of the item, but the comparator was incomplete and is now stated as a sum with its
members named.

## The nine that are like-for-like, and stand

| country | line | ours | published (A3.4) | gap | comparator checked |
|---|---|---:|---:|---:|---|
| ES | Income tax | 127,948.9 | 130,106 (`tin_s`) | −1.7% | `ils_taxin` = `tin_s` alone in ES_2023; `ils_taxwl` = `twl` = 0, so `ils_tax` is numerically `tin_s`. **Like-for-like.** Not the Italian error |
| ES | Employee contributions | 32,347.5 | 32,840 | −1.5% | five members both sides, one switched off in this system |
| ES | Self-employed contributions | 17,238.9 | 14,551 | **+18.5%** | four members both sides. **The comparison stands as like-for-like**, and it is the membership that makes it so: the two sides name the same four members, which is this sweep's finding and is independent of what either side reads. See `DATA_ISSUES` 9.13 |
| ES | Employer contributions | 152,313.3 | 154,341 | −1.3% | five members, one off |
| IT | Income tax, national IRPEF | 255,242.6 | 200,784 (`tinna_s`) | +27.1% | the comparator is the single published line |
| IT | Employee contributions | 42,036.0 | 42,543 | **−1.2%** | six members. **Not currently in the validation table at all** |
| IT | Employer contributions | 181,054.4 | 179,797 | +0.7% | seven members both sides |
| EL | Income tax | 12,313.1 | 12,395 (`tin00_s`) | −0.7% | the row already reports `tin00_s`, not the list. Like-for-like |
| EL | Employee contributions | 7,188.9 | 8,284 | −13.2% | six members both sides, one zero, one off. **The −13.2% stands** |

## What this changes, once decided

Five things follow from it. **ALL FIVE ARE NOW APPLIED**, items 4 and the Greek employer half
of item 1 on 2026-08-03, the remainder later the same day. Item 5 was applied when this
document was written, for the reason it gives.

1. `BASELINE_VALIDATION.md`: Italy's self-employed contribution row restated on A3.4
   (20,144), Greece's employer row restated on the model's own components (10,819), Greece's
   self-employed row restated on the complete sum (2,489), and Italy's employee
   contributions added, since a −1.2 per cent line is worth having.
   **APPLIED, all four.** Italy's self-employed row now reads **+93.8 per cent** against a
   published 20,144 and **+88.4 per cent** against an external 20,716; Greece's employer row
   **+5.7 per cent** against 10,819, with the PY030G external kept beside it; Greece's
   self-employed row **−25.0 per cent** against 2,489; and Italy's employee contributions
   row **−1.2 per cent** against 42,543 is added. Each of the three corrected rows carries
   its table, its row label, and what the published line counts, in the row's own note.
2. `DATA_ISSUES` **IT-3**: "+450%" becomes "+94%", and the "no NA correspondence" note keeps
   its force. **APPLIED.** The entry now states A3.3 against A3.4 in full. The old
   "3.25× contribution-base concept" arithmetic is withdrawn with it: it was derived by
   dividing by the payer count, so it inherits the same error. What survives is that the
   release cannot carry the contribution-base concept at all, which is unquantified.
3. `DATA_ISSUES` **EL-3**: −22.8 becomes −25.0. **APPLIED**, with the six live members named
   and the omitted one identified. Its size in money goes from ~0.55bn to ~0.62bn.
4. `DATA_ISSUES` **9.8** is withdrawn: Greece's employer contributions are not unexplained
   and not materially below anything, once compared to the model's own figure.
   **Applied.** 9.8 is closed and stated against 10,819. With 9.2 and 9.9
   also closed, the `[OPEN, unexplained]` entries in section 9 are 9.10 and 9.13.

**One consequence of items 2 and 3 that was measured rather than assumed.**
`selfemp_sic_share.py` reads the published figure to attribute part of a displayed cost to
the divergence, so both corrections propagate into `DATA_ISSUES` 9.7. Re-run: the SHARE
columns do not move at all, because they are properties of the run, and only the EXCESS
column moves. Italy's falls from 4.91–5.06 to **2.90–3.00** per cent of the displayed net
exchequer cost on the earnings downturn and from 5.84–6.59 to **3.45–3.90** on the
unemployment shock. Greece's *rises*, from 0.01–0.11 to **0.01–0.13** and from 0.22–0.27 to
**0.25–0.31**, which is the expected direction: its divergence runs the other way, so
completing the published sum widens it.
5. The Italian tool's self-employed contribution caveat quotes 39,037 against 7,093 and
   calls it 5.5 times. The face reads about 94 per cent above EUR 20,144m: a
   category error on a shipped page is not something to hold pending a decision. The share of the displayed net exchequer cost
   attributable to the divergence falls with it, from 4.9-6.6 per cent to **2.9-3.0 per cent
   on the earnings downturn and 3.5-3.9 per cent on the unemployment shock**. Everything
   else waits.

   **That reopens a judgement.** Italy was given a face caveat and Spain and Greece were not,
   on the basis that 5 to 7 per cent of a displayed headline is material where 1.6 per cent
   is not. On the corrected figure Italy is at 3 to 4 per cent. It is still the largest of
   the three and still more than twice Spain's, so the caveat has been kept; whether 3 to 4
   per cent still clears the bar is a decision, and it has not been retaken here.

## Method note

The unit error was findable because the two tables have nearly identical titles, sit four
pages apart, and both carry a row labelled "Self-employed Social Insurance Contributions".
A3.3 is payers in thousands, A3.4 is amounts in millions, and for Italy the payer count and
a plausible amount are the same order of magnitude. Spain's figure was taken from A3.4 and
Italy's from A3.3, in the same pass, by the same method. **A published number is not
identified by its label alone; it is identified by its label and its table.**
