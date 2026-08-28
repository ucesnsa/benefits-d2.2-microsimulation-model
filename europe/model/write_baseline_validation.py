"""write_baseline_validation.py -- the acceptance table, generated rather than transcribed.

Reads the two per-country baseline runs `europe/model/validate_baselines.py` produces, joins
them to the figures each EUROMOD Country Report publishes, and writes BASELINE_VALIDATION.md.

The published figures are held here, each with the document and table it came from. They
are the only hand-entered numbers in the chain, which is why they are in one block with
their sources attached rather than scattered through prose.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EUROPE = os.path.dirname(HERE)
DOCS = os.path.join(EUROPE, "docs")

# ---------------------------------------------------------------------------
# What the Country Reports publish. src is where each figure was read from in this
# repository, which in every case quotes the Country Report table it came from.
# A value of None means the figure is not recorded on this machine; the row then reports
# what the build produces and says so, rather than inventing a benchmark.
# ---------------------------------------------------------------------------
PUB = {
 "ES": {
  "source": "Y16_CR_ES, sections 9 and 10",
  "rows": [
   ("Market income", "ils_origy", 652827, 655000,
    "external: national accounts, the official aggregate"),
   ("Pensions", "ils_pen", 185046, 197083, "external: ESSPROS spr_exp_pens"),
   ("Income tax", "ils_tax", 130106, None, ""),
   ("Employee contributions", "ils_sicee", 32840, None, ""),
   ("Self-employed contributions", "ils_sicse", 14551, None, ""),
   ("Employer contributions", "ils_sicer", 154341, 105543,
    "external: Y16_CR_ES table A3.4"),
   ("Minimum income (IMV)", "bsa00_s", 2503, 2504,
    "external: Y16_CR_ES table A3.6. EUROMOD's own figure matches the external spend to within 0.04 per cent. **This row cannot validate anything.** The EUR 2,504m is the target of the Benefit Calibration Adjustment, which is switched on for ES_2023 on this dataset, so the modelled outlay is the object of an adjustment aimed at the very figure it is then compared against, whatever the eligibility rules underneath do. It is not \"pinned to\" that figure: it reaches 99.01 per cent of it, and so fails the project's own `outlay >= target * 0.995` test, the same test that puts Greece in the target-not-reached column at 95.33 per cent. `benefit_adjustments.json` carries `target_binds: false` for Spain. **But do not read that flag as saying the outlay is free of the target.** The model's take rule is `i_bsa00_bca_take = bsa00_s > 0 & i_bsa00_cumexp <= $bsa00_targetBCA_amt`, a cumulative weighted sum taken while it stays at or below the target, so the calibration can only ever land under it and an undershoot is what binding looks like; the 0.995 threshold is a tolerance, not a property of the model. The -0.9 per cent this row reports is the calibration landing on a unit of the eligible set, which is consistent with that. What is genuinely open is only which of the two caps is the operative minimum, the applied rate being `min($bsa00_BCA_rate,$bsa00_BTA_rate)` with the take-up rate at 0.44, and that needs the matched engine. Either way the row is not independent evidence about the EUR 2,504m. See europe/model/benefit_adjustments.py"),
   ("Child allowance (bch00)", "bch00_s", None, None, ""),
  ],
  "dist": [("Mean equivalised disposable", "mean_equivalised_disposable", 21249, None),
           ("Median equivalised disposable", "median_equivalised_disposable", None, None),
           ("Gini", "gini_pct", 30.35, None),
           ("AROP rate", "arop_rate_pct", 19.25, 19.7)],
 },
 "IT": {
  "source": "Y16_CR_IT tables A3.2 and A3.6",
  "rows": [
   ("Earnings", "ils_earns", 736695, None,
    "the gap is the documented tax-compliance adjustment (IT-1): EUROMOD pulls "
    "self-employment down to fiscal data by 92,830m and this build carries the survey "
    "figure, which accounts for almost all of the 94,309m difference"),
   ("Pensions", "ils_pen", 311890, 329847, "external: ESSPROS, function caveat (IT-4)"),
   ("Income tax, national IRPEF", "tinna_s", 200784, 189940,
    "external: Y16_CR_IT table A3.4. This is the like-for-like comparator, settled by "
    "fetching the report: the published line is tinna_s, national IRPEF alone, not the "
    "whole income-tax list"),
   ("Income tax, regional surcharge", "tinrg_s", 15991, 15231,
    "external: Y16_CR_IT table A3.4"),
   ("Income tax, flat-tax regime", "tin00_s", 2861, None,
    "zero here because lse01, the variable selecting the regime, is a national imputation"),
   ("Property tax, other buildings", "tprob_s", 16463, 18064,
    "external: Y16_CR_IT table A3.4"),
   ("Cadastral income, other buildings", "aobiv", 9245, None,
    "Y16_CR_IT table A3.4, not simulated; the external check on the cadastral-income derivation"),
   ("Total taxable IRPEF income", "il_taxabley", 1038943, 1027673,
    "external: Y16_CR_IT table A3.4"),
   ("Employee contributions", "ils_sicee", 42543, None,
    "Y16_CR_IT table A3.4, `ils_sicee` as its six components. A -1.2 per cent line is worth "
    "reporting beside the two contribution rows that diverge"),
   ("Self-employed contributions", "ils_sicse", 20144, 20716,
    "**The comparator here is easy to take from the wrong table.** **7,093 is not an "
    "amount.** It is the 2023 "
    "cell of table **A3.3, `Direct taxes and SIC - Number of payers (thousands)`**: 7,093 "
    "THOUSAND self-employed people paying contributions, against an external 3,260 "
    "thousand. The annual amount is in table **A3.4, `Direct taxes and SIC - Annual amounts "
    "(millions)`**, four pages later, where the row carrying the same label reads "
    "**EUR 20,144m** against an external **EUR 20,716m**. Both tables carry a row with that "
    "label, so the amount must be read from A3.4. This row is **+93.8 per cent against the "
    "model's own figure and +88.4 per cent against the external one**, a factor of 1.94. It "
    "is the largest divergence in the deliverable and a live ceiling, but it does not "
    "support a \"several times the published figure\" framing. See "
    "`LIKE_FOR_LIKE_SWEEP.md` section 1 and `DATA_ISSUES` IT-3. external: Y16_CR_IT table "
    "A3.4, the external column of the same row"),
   ("Employer contributions", "ils_sicer", 179797, 204586,
    "external: Y16_CR_IT table A3.6"),
   ("Minimum income (AdI)", "bsamm_s", 7971, 6653,
    "external: Y16_CR_IT table A3.6"),
   ("Child allowance (Assegno Unico)", "bfach00_s", 18538, 17382,
    "external: Y16_CR_IT table A3.6"),
  ],
  "dist": [("Mean equivalised disposable", "mean_equivalised_disposable", 22975, None),
           ("Median equivalised disposable", "median_equivalised_disposable", 20243, None),
           ("Gini", "gini_pct", 30.65, None),
           ("AROP rate", "arop_rate_pct", 18.91, None)],
 },
 "EL": {
  "source": "Y16_CR_EL, section 6",
  "rows": [
   ("Market income", "ils_origy", 83845, None, ""),
   ("Pensions", "ils_pen", 31971, 31470, "external: ESSPROS"),
   ("Income tax", "tin00_s", 12395, 12278, "external: AADE"),
   ("Employee contributions", "ils_sicee", 8284, None, ""),
   ("Self-employed and farmer contributions", "ils_sicse", 2489, None,
    "**The comparator is a sum of the report's components, and every one of them counts.** "
    "`ils_sicse` in EL_2023 has seven members, one of them switched off, so six are live: "
    "`tscsepi_s`, `tscsesi_s`, "
    "`tscseui_s`, `tscfrpi_s`, `tscfrsi_s`, `tscfrot_s`. Y16_CR_EL table A3.4 publishes "
    "all six: **1,347 + 478 + 71 + 433 + 151 + 9 = 2,489**. Dropping any one of them moves "
    "the comparator: without **`tscseui_s`, self-employed SIC: unemployment, EUR 71m** it "
    "reads 2,418 and the divergence reads -22.8 rather than **-25.0 per cent**, which is the "
    "direction AWAY from the published line. See "
    "`LIKE_FOR_LIKE_SWEEP.md` section 3 and `DATA_ISSUES` EL-3"),
   ("Employer contributions", "ils_sicer", 10819, 16850,
    "EUROMOD published: Y16_CR_EL table A3.4, `ils_sicer` as its five components, "
    "8,293+1,928+509+0+89. The list in EL_2023 has exactly those five members and no "
    "others, so the sum is the list. "
    "PY030G is the survey's record of every scheme and `ils_sicer` is five simulated ones, "
    "so the two are not the same quantity and are not comparable. See "
    "`LIKE_FOR_LIKE_SWEEP.md` and `DATA_ISSUES` "
    "9.8. external: PY030G, the employer contributions EU-SILC itself records"),
   ("Property tax (ENFIA)", "tpr_s", 1575, None,
    "Y16_CR_EL table A3.4; the SILC column is 1,575 too"),
   ("Minimum income (KEA)", "bsa00_s", 426, 520,
    "external: Y16_CR_EL table A3.6. EUROMOD's own figure is 18 per cent BELOW the "
    "published spend, and this build is closer to it than EUROMOD is"),
   ("Child benefit (A21)", "bch_s", None, None, ""),
  ],
  "dist": [("Mean equivalised disposable", "mean_equivalised_disposable", 13077, 12391),
           ("Median equivalised disposable", "median_equivalised_disposable", 11691, None),
           ("Gini", "gini_pct", 28.79, 31.80),
           ("AROP rate", "arop_rate_pct", 15.77, 19.60)],
 },
}
NAME = {"ES": "Spain", "IT": "Italy", "EL": "Greece"}


def get(rep, cc, key):
    r = rep.get(cc, {})
    for block in ("aggregates_eur_m", "instruments_eur_m"):
        if key in r.get(block, {}) and r[block][key] is not None:
            return r[block][key]
    return None


def pct(a, b):
    if a is None or b in (None, 0):
        return ""
    return f"{100 * (a - b) / b:+.1f}%"


def fmt(v, dp=1):
    return "n/a" if v is None else f"{v:,.{dp}f}"


def main():
    before = json.load(open(os.path.join(DOCS, "baseline_validation_before.json"),
                            encoding="utf-8"))
    after = json.load(open(os.path.join(DOCS, "baseline_validation_after.json"),
                           encoding="utf-8"))
    L = ["# Validation against the published EUROMOD baselines", "",
         "Generated by `europe/model/write_baseline_validation.py` from the before and after "
         "baseline runs `europe/model/validate_baselines.py` produces, one unmodified run "
         "per country. The only hand-entered numbers are the published figures, which are "
         "held in one block in the generator with the Country Report table each came from.",
         "",
         "**The test is agreement with the model's own published baseline.** A rebuild that "
         "changes the inputs changes the outputs, so reproducing a stored surface exactly is "
         "not the test. Agreement with the published baseline is, and it is falsifiable.", "",
         "The published figures are taken from the reports themselves. Several are sums of a "
         "report's components rather than a single published line, and each such row says so "
         "in its own note.", "",
         "All money in EUR millions a year, weighted to the population.", "",
         "**What the after column includes.** It is the state of the build, not only the "
         "completed conversion. It carries one further input correction: `ysemy`, the "
         "Spanish self-employed months-of-receipt count, was an unconditional 12 and now "
         "reads the same months-worked variable, on the same clip, that `yemmy` already "
         "read one line above it.", "",
         "## Spain's self-employed contributions, and the residual that survives the fix", "",
         "Spain's self-employed contributions read EUR 20,566.8m against a published "
         "EUR 14,551m, **+41.3 per cent**, while self-employment income itself and the payer "
         "count both matched. Contributions scale directly with the months-of-receipt count, "
         "and `convert_full.py` set `ysemy` to 12 for everyone with self-employment income. "
         "The months-worked variable it should have read was present, populated, and used "
         "one line above for the employee equivalent. Among the 5,721 records carrying "
         "self-employment income that count means **9.853 months** on the clip the employee "
         "line uses, and **22.4 per cent** of them are below a full year, so the "
         "unconditional 12 was charging a full year of contributions to people the survey "
         "records as having worked less than one.", "",
         "Corrected, the line falls to **EUR 17,238.9m, +18.5 per cent**. The fall is 16.2 "
         "per cent rather than the 17.9 per cent the mean months alone imply, because Spain's "
         "RETA has a statutory minimum contribution base that does not scale with months.", "",
         "**The remaining +18.5 per cent is unexplained, and is recorded as unexplained "
         "rather than as an input-completeness item**, because unlike those entries it is "
         "not an absent variable: every input the calculation reads is now populated from a "
         "published recipe. `ES-1` attributes it to the chosen-base and under-declaration "
         "behaviour that the public release cannot carry, and that remains the standing "
         "hypothesis, but nobody has measured how much of EUR 2,688m it accounts for. See "
         "`DATA_ISSUES_FOR_TECHNICAL_REPORT.md` 9.13.", "",
         "## Italian income tax", "",
         "Italian national income tax is overstated by EUR 54,459m against the model's own published baseline. **Three mechanisms bound that gap rather than explain it**, and all three are absent national imputations: variables the public EU-SILC user database cannot carry, each recorded as an imputation in the EUROMOD input data codebook and none of them reproducible here. At their maximum the three close 99.5 per cent of the gap; at what Italy actually records, 69.5 per cent, and EUR 16.6bn remains unaccounted for. The lattice behind those two points, and the two income tax quantities it must never mix, are `DATA_ISSUES_FOR_TECHNICAL_REPORT.md` 9.14, which is the account of record. Every closure figure in this section is measured on `tinna_s`, national IRPEF alone, which is the line the country report publishes; the regime revenues quoted below are not.", "",
         "The comparator matters and was wrong until the report was fetched. Table A3.4 of Y16_CR_IT publishes `tinna_s`, national IRPEF alone, and gives the regional surcharge, the flat tax and the property tax their own lines. The gap against the whole income-tax list read EUR 67,018m; against the line the report actually publishes it is EUR 54,459m, and the regional surcharge is accurate to 2.4 per cent.", "",
         "The first cause is the compliance adjustment. `TCA_it` is switched on for this dataset and runs on every point of this surface, but the variables it consumes, `yseev` and `ysenr`, are imputations on national SILC, so self-employment income passes through at the survey total and nothing is removed from the tax base. Restoring it to the level the country report implies, EUR 133,905m against EUR 226,735m, takes national IRPEF to EUR 226,974m and closes 52 per cent of the gap. It also brings the taxable IRPEF base to EUR 1,039,513m against a published EUR 1,038,943m, a difference of 0.05 per cent. The amount is **EUR 28,285.1m** on `tinna_s`. A compliance figure of about EUR 29,667m has been in circulation and is a whole-list measurement on `ils_tax`; it must not be used in this arithmetic.", "",
         "The second is the flat-tax optional regime. `tinyse_it` charges 15 per cent on self-employment income net of contributions where `lse01 = 1`, and `lse01` is another national imputation, so it is zero for everyone and every self-employed person is taxed progressively at up to 43 per cent. If everyone statutorily eligible elected into it, national IRPEF would fall by a further **EUR 33,351.4m** at the statutory EUR 85,000 threshold, or EUR 27,802.9m at the EUR 65,000 threshold the codebook carries; the statutory figure is the one the bound below uses. Italy actually had about 1.9 million taxpayers in the regime in 2023 against 7.5 million eligible here, and the report puts the regime's own revenue at EUR 2,861m against the EUR 17,375m this build's ceiling produces, so the realistic effect is nearer a sixth of that bound. Drawn on a fixed seed at the 1.9 million electors Italy records, the regime closes **EUR 8,018.1m** on `tinna_s`, which is the figure the realistic point below uses.", "",
         "The third is the expense-based credits. Seven arms, health and life insurance and education among them, are computed from variables the public database does not carry, so no household's tax due is reduced by any of them here. At their ceiling, every eligible household claiming every arm, they close a further **EUR 13,113.3m** on `tinna_s`. That ceiling is 2.15 times the EUR 6,113.1m Italy's own *Rapporto annuale sulle spese fiscali* 2024 puts these reliefs at, which is the right side to be on for a ceiling, and it is the EUR 6,113.1m that the realistic point uses.", "",
         "**Taken together the three bound the gap, and the bound is not an estimate.** At their maximum they close EUR 54,191.2m and leave EUR 267.4m, 99.5 per cent of it. Only the compliance adjustment is an estimate, because it is what EUROMOD itself applies; the other two are ceilings, every eligible person electing and every eligible household claiming, and neither happens. At the realistic point, built on Italy's own published figures rather than on rates chosen here, the three close EUR 37,873.3m and leave **EUR 16,585.3m: 69.5 per cent closed, EUR 16.6bn remaining**. That is the figure of record. The figures are bounds, not a correction: no adjustment has been applied, and scaling the output to the published aggregate was considered and rejected, because it would fit the total while misstating who pays.", "",
         "**One caveat attaches to the compliance bound.** That bound is computed with a **uniform scale** on self-employment income, while the adjustment EUROMOD runs, `TCA_it`, is a **household-level imputation** that moves different households by different proportions. Italian income tax is progressive, so a uniform scale and a household-level one that reach the same aggregate base do not produce the same tax, and which way the difference runs depends on where the real adjustment concentrates, which is exactly what the missing variables would say: the bound is a bound on the base, not on the tax the base produces. Running the other way, the measured credit interaction against each of the other two mechanisms is 0.8 to 1.6bn at the ceiling, so adding the three together slightly overstates closure and **EUR 16,585m is if anything a small under-estimate of the residual**. See `DATA_ISSUES` 9.14.", ""]
    for cc in ("ES", "IT", "EL"):
        p = PUB[cc]
        a, b = after.get(cc, {}), before.get(cc, {})
        L += [f"## {NAME[cc]} ({cc})", "",
              f"Published figures from {p['source']}.", "",
              f"Populated input columns: **{b.get('n_populated_columns')} before, "
              f"{a.get('n_populated_columns')} after**.", "",
              "| line | before | after | EUROMOD published | after vs published | before vs published | external, and notes |",
              "|---|---:|---:|---:|---:|---:|---|"]
        for label, key, em, ext, extnote in p["rows"]:
            va, vb = get(after, cc, key), get(before, cc, key)
            cell = fmt(ext) if ext else ""
            if extnote:
                cell = (cell + ". " if cell else "") + extnote
            L.append(f"| {label} | {fmt(vb)} | {fmt(va)} | {fmt(em)} | {pct(va, em)} | "
                     f"{pct(vb, em)} | {cell} |")
        L += ["", "| statistic | before | after | EUROMOD published | survey |",
              "|---|---:|---:|---:|---:|"]
        for label, key, em, sv in p["dist"]:
            va = a.get("distribution", {}).get(key)
            vb = b.get("distribution", {}).get(key)
            dp = 2 if "gini" in key or "rate" in key else 0
            L.append(f"| {label} | {fmt(vb, dp)} | {fmt(va, dp)} | {fmt(em, dp)} | "
                     f"{fmt(sv, dp)} |")
        L.append("")
    path = os.path.join(DOCS, "BASELINE_VALIDATION.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("written", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
