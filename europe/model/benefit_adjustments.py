"""benefit_adjustments.py -- the take-up and calibration adjustments on each country's
minimum income: whether they run, at what rate, and against what external figure.

Why this exists. Two claims in this project's documentation depend on the state of two
EUROMOD extensions, and neither had a source. The first is that Spain's minimum income
barely responds to a shock (`DATA_ISSUES` 9.2): a fixed monetary calibration target
cannot let spending rise, so a shock that raises both the eligible count and the average
entitlement exhausts the target after fewer units. The second is that Greece's minimum
income is calibrated towards a published figure it does not reach (`DATA_ISSUES` 9.9), so
the missing floor-area asset test would widen the gap rather than close it. Both were
being asserted from reading the policy spine by eye.

What is read, all of it from the model rather than from a note:

  * BTA and BCA, the Benefit Take-up and Benefit Calibration Adjustments, as switched for
    the system AND dataset this build actually runs. The switch is per (extension,
    dataset, system), so reading it off the country or the system alone is not enough.
  * `$X_BTA_rate`, the take-up rate the adjustment caps the caseload at.
  * `$X_targetBCA_amt`, the calibration target, which is `$extstat_amount_X * 1000000/12`
    in all three countries: a monetary expenditure total, not a caseload.
  * the external statistic that constant resolves to, from the country's own
    `<ExternalStatistic>` table: the amount, the recipient count where one is published,
    and the source. This is the figure the calibration aims at.
  * the modelled outlay for the same instrument, from `baseline_validation_after.json`,
    so target and outcome are reported side by side and the reader can see which of the
    two binds.

The XML is read directly because the connector does not expose the external statistics.
It is read from the installed model, so this script needs EUROMOD; it does not need the
microdata and it runs no simulation.

Aggregates only. Nothing is populated, no surface is touched, no microdata is read.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EUROPE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EUROPE, "common"))

import engine  # noqa: E402

# System and dataset as build_grid.CC_CFG runs them. The switch is per pair, so both matter.
RUNS = {
    "ES": dict(system="ES_2023", dataset="ES_2024_b1_2015_03_e2",
               policy="bsa00_es", stem="bsa00", instrument="bsa00_s"),
    "IT": dict(system="IT_2023", dataset="IT_2024_a1_2015_03_e2",
               policy="bsamm_it", stem="bsamm", instrument="bsamm_s"),
    "EL": dict(system="EL_2023", dataset="EL_2024_c1_2015_03_e2",
               policy="bsa00_el", stem="bsa00", instrument="bsa00_s"),
}
YEAR = "2023"

# The validation table's own name for each instrument, to read the modelled outlay back.
MODELLED_KEY = {"ES": "bsa00_s", "IT": "bsamm_s", "EL": "bsa00_s"}

BLOCK = re.compile(r"<ExternalStatistic>(.*?)</ExternalStatistic>", re.S)
YEARSEP = "°"


def _tag(block, name):
    m = re.search(r"<%s>(.*?)</%s>" % (name, name), block, re.S)
    if m is None:
        return ""
    return re.sub(r"^<!\[CDATA\[|\]\]>$", "", m.group(1).strip()).strip()


def external_statistic(country, reference, year=YEAR):
    """The `<ExternalStatistic>` row the BCA target resolves to, from the country XML.

    A row carries one record per year, pipe-separated as amount|count|level, the amount
    in millions a year and the count in thousands. Both are reported, and so is the
    source, because the source is what makes the figure citable."""
    path = os.path.join(engine.MODEL_PATH, "XMLParam", "Countries", country, country + ".xml")
    if not os.path.isfile(path):
        return {"error": "country XML not found at %s" % path}
    with open(path, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    for block in BLOCK.findall(txt):
        if _tag(block, "Reference") != reference:
            continue
        rec = {"reference": reference, "category": _tag(block, "Category"),
               "description": _tag(block, "Description"), "source": _tag(block, "Source"),
               "comment": _tag(block, "Comment"), "years": {}}
        for row in _tag(block, "YearValues").split(YEARSEP):
            parts = row.split("|")
            if len(parts) >= 3 and parts[0]:
                rec["years"][parts[0]] = {"amount_eur_m": parts[1] or None,
                                          "count_k": parts[2] or None}
        rec["year"] = year
        rec["amount_eur_m"] = (rec["years"].get(year) or {}).get("amount_eur_m")
        rec["count_k"] = (rec["years"].get(year) or {}).get("count_k")
        return rec
    return {"error": "no ExternalStatistic with Reference %r in %s" % (reference, country)}


def switch_state(country_obj, ext, dataset, system):
    """'on' / 'off' for one extension on one (dataset, system) pair."""
    try:
        raw = str(country_obj.get_switch_value(ext_name=ext, dataset_name=dataset,
                                               sys_name=system))
    except Exception as exc:                      # noqa: BLE001 - reported, not swallowed
        return "ERROR: %s" % exc
    m = re.search(r"\|\s*(on|off|n/a|toggle)\b", raw, re.I)
    return m.group(1).lower() if m else raw.strip()


def constants_in_policy(system_obj, policy_name, names):
    """The DefConst values named in `names`, read from one policy."""
    out = {}
    for p in system_obj.policies:
        if (getattr(p, "name", "") or "") != policy_name:
            continue
        for f in (getattr(p, "functions", None) or []):
            if getattr(f, "name", "") != "DefConst":
                continue
            for par in (getattr(f, "parameters", None) or []):
                nm = (getattr(par, "name", "") or "")
                if nm in names:
                    out[nm] = str(getattr(par, "value", "") or "")
    return out


def modelled_outlay(country):
    """The instrument's simulated total from the last baseline validation run."""
    path = os.path.join(EUROPE, "docs", "baseline_validation_after.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    inst = (blob.get(country) or {}).get("instruments_eur_m") or {}
    return inst.get(MODELLED_KEY[country])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", default="ES,IT,EL")
    ap.add_argument("--out", default=os.path.join(EUROPE, "docs", "benefit_adjustments.json"))
    args = ap.parse_args(argv)

    engine.assert_matched_engine()
    mod = engine.load_model()
    report = {}
    for cc in [c.strip() for c in args.countries.split(",") if c.strip()]:
        cfg = RUNS[cc]
        cobj = mod.countries[cc]
        sysobj = engine.get_system(cobj, cfg["system"])
        stem = cfg["stem"]
        consts = constants_in_policy(sysobj, cfg["policy"], {
            "$%s_BTA_rate" % stem, "$%s_targetBCA_amt" % stem, "$%s_BCA_rate" % stem,
            "$%s_rate" % stem, "$%s_target_count" % stem, "$%s_takeup_ratio" % stem})
        ext = external_statistic(cc, cfg["instrument"])
        entry = {
            "system": cfg["system"], "dataset": cfg["dataset"], "policy": cfg["policy"],
            "instrument": cfg["instrument"],
            "BTA": switch_state(cobj, "BTA", cfg["dataset"], cfg["system"]),
            "BCA": switch_state(cobj, "BCA", cfg["dataset"], cfg["system"]),
            "constants": consts,
            "external_statistic": ext,
            "modelled_outlay_eur_m": modelled_outlay(cc),
        }
        target = ext.get("amount_eur_m")
        outlay = entry["modelled_outlay_eur_m"]
        if entry["BCA"] == "on" and target and outlay is not None:
            entry["target_binds"] = float(outlay) >= float(target) * 0.995
        elif entry["BCA"] == "off":
            entry["target_binds"] = False
        report[cc] = entry

        print("=" * 96)
        print("%s  %s on %s" % (cc, cfg["system"], cfg["dataset"]))
        print("  take-up adjustment   BTA %-4s  %s = %s"
              % (entry["BTA"], "$%s_BTA_rate" % stem, consts.get("$%s_BTA_rate" % stem, "-")))
        print("  calibration          BCA %-4s  %s = %s"
              % (entry["BCA"], "$%s_targetBCA_amt" % stem,
                 consts.get("$%s_targetBCA_amt" % stem, "-")))
        print("  effective rate                 %s = %s"
              % ("$%s_rate" % stem, consts.get("$%s_rate" % stem, "-")))
        if "error" in ext:
            print("  external statistic   %s" % ext["error"])
        else:
            print("  external statistic   %s %s: amount %s EUR m, count %s k, source %r"
                  % (ext["reference"], ext["year"], ext["amount_eur_m"], ext["count_k"],
                     ext["source"]))
        print("  modelled outlay      %s EUR m" % outlay)
        if entry.get("target_binds") is True:
            print("  -> the calibration target BINDS: the outlay lands on it, so the aggregate "
                  "is the target and cannot test the rules under it")
        elif entry.get("target_binds") is False and entry["BCA"] == "on":
            print("  -> the calibration target is NOT REACHED: every eligible unit is paid and "
                  "the outlay sits below the figure the adjustment aims at")
        elif entry["BCA"] == "off":
            print("  -> both adjustments are OFF: neither the external figure nor a take-up "
                  "rate is applied")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print("\nwritten", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
