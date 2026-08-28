#!/usr/bin/env python3
"""Pull the PPP factors and the GDP deflators from source, and save a dated artefact.

These were documented but not verified: the chain was fully
specified in PROVIDER_TOOLREADY_2024.md and FOUNDATION.md, naming the series, the
parameters and the reason for each fallback, but nobody had re-pulled them and no pull
artefact existed on disk. This closes that bullet by pulling both sources, recomputing
every factor the documentation records, comparing against the recorded value, and
writing the raw observations and the comparison to a dated JSON beside the docs.

Standard library only, like the rest of the verification layer. Needs network access to
ec.europa.eu and sdmx.oecd.org; both are public, unauthenticated, read-only endpoints.

  py -3 pull_ppp_deflators.py            pull, compare, and write the dated artefact
  py -3 pull_ppp_deflators.py --check    pull and compare; write nothing, exit 1 on drift

Tolerance is 1e-4 on a factor. The observed differences are around 5e-6 and come from
source revisions between the original pull and this one, not from a different method.
"""

import argparse
import json
import socket
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "docs"
# Eurostat rejects the SDMX Accept header with a 406, so it is sent only to the OECD.
UA = {"User-Agent": "benefits-d22-verify"}
UA_SDMX = dict(UA, Accept="application/vnd.sdmx.data+json")
TOL = 1e-4

EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

# The deflators, FOUNDATION.md section 2b: Eurostat nama_10_gdp, B1GQ, PD15_NAC, the
# 2024-over-2023 ratio. Recorded ES x1.0289, EL x1.0321, IT x1.0197.
Q_DEFLATOR = (f"{EUROSTAT}/nama_10_gdp?format=JSON&lang=EN&na_item=B1GQ&unit=PD15_NAC"
              "&geo=ES&geo=IT&geo=EL&time=2023&time=2024")
RECORDED_DEFLATOR = {"ES": 1.0289, "EL": 1.0321, "IT": 1.0197}

# Household-final-consumption PPP, PROVIDER_TOOLREADY_2024.md section 1: Eurostat
# prc_ppp_ind, na_item=PPP_EU27_2020, ppp_cat=E011, single 2024 round. Primary source
# for transfers inside the euro area.
Q_PPP_EUROSTAT = (f"{EUROSTAT}/prc_ppp_ind?format=JSON&lang=EN&na_item=PPP_EU27_2020"
                  "&ppp_cat=E011&time=2024&geo=ES&geo=IT&geo=EL&geo=UK")
RECORDED_EUROAREA = {("IT", "ES"): 0.932084, ("IT", "EL"): 0.881460, ("ES", "EL"): 0.945687}

# The named fallback for the one transfer that crosses the UK: OECD
# DSD_NAMAIN10@DF_TABLE4 v2.0, MEASURE=PPP_P31S14, UNIT=XDC_USD. Filtered keys are
# rejected by this dataflow (HTTP 422), so the whole 2024 slice is fetched, about 50 kB,
# and filtered here.
Q_PPP_OECD = ("https://sdmx.oecd.org/public/rest/data/"
              "OECD.SDD.NAD,DSD_NAMAIN10@DF_TABLE4,2.0/all"
              "?startPeriod=2024&endPeriod=2024&format=jsondata&dimensionAtObservation=AllDimensions")
RECORDED_UK_CROSSING = {"ESP": 0.861941, "ITA": 0.915660, "GRC": 0.816996}
ISO2 = {"ESP": "ES", "ITA": "IT", "GRC": "EL"}


def fetch(url, headers=UA):
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers)).read()


def eurostat(url):
    """Flatten a Eurostat JSON-stat response to {(geo, time): value}."""
    d = json.loads(fetch(url))
    geo = d["dimension"]["geo"]["category"]["index"]
    time = d["dimension"]["time"]["category"]["index"]
    n = len(time)
    out = {}
    for g, gi in geo.items():
        for t, ti in time.items():
            v = d["value"].get(str(gi * n + ti))
            if v is not None:
                out[(g, t)] = v
    return out, d.get("updated")


def oecd(url):
    """Flatten the OECD SDMX-JSON slice to {(transaction, ref_area): value}."""
    d = json.loads(fetch(url, UA_SDMX))
    dims = d["data"]["structures"][0]["dimensions"]["observation"]
    pos = {dm["id"]: i for i, dm in enumerate(dims)}
    vals = {dm["id"]: [v["id"] for v in dm["values"]] for dm in dims}
    out = {}
    for key, v in d["data"]["dataSets"][0]["observations"].items():
        p = [int(x) for x in key.split(":")]
        out[(vals["TRANSACTION"][p[pos["TRANSACTION"]]],
             vals["REF_AREA"][p[pos["REF_AREA"]]])] = v[0]
    return out


def compare(label, computed, recorded, rows):
    ok = abs(computed - recorded) <= TOL
    rows.append({"factor": label, "computed": round(computed, 6),
                 "recorded": recorded, "abs_diff": round(abs(computed - recorded), 8),
                 "within_tolerance": ok})
    print(f"  {label:34s} computed {computed:.6f}  recorded {recorded:.6f}  "
          f"diff {abs(computed - recorded):.2e}  {'MATCH' if ok else 'DIFFERS'}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="pull and compare only; write nothing, exit 1 on drift")
    args = ap.parse_args()
    socket.setdefaulttimeout(90)

    rows, raw = [], {}

    print("GDP deflators, Eurostat nama_10_gdp B1GQ PD15_NAC, 2024 over 2023")
    defl, defl_updated = eurostat(Q_DEFLATOR)
    raw["deflator_observations"] = {f"{g}:{t}": v for (g, t), v in sorted(defl.items())}
    for cc, rec in sorted(RECORDED_DEFLATOR.items()):
        compare(f"deflator {cc}", defl[(cc, "2024")] / defl[(cc, "2023")], rec, rows)

    print("\nHousehold-final-consumption PPP, Eurostat prc_ppp_ind PPP_EU27_2020 E011, 2024")
    ppp_es, ppp_updated = eurostat(Q_PPP_EUROSTAT)
    P = {g: v for (g, t), v in ppp_es.items()}
    raw["eurostat_ppp_observations"] = dict(sorted(P.items()))
    for (src, dst), rec in sorted(RECORDED_EUROAREA.items()):
        compare(f"PPP {src}->{dst} (euro area)", P[dst] / P[src], rec, rows)

    print("\nUK-crossing PPP, OECD DSD_NAMAIN10@DF_TABLE4 PPP_P31S14 XDC_USD, 2024")
    o = oecd(Q_PPP_OECD)
    raw["oecd_ppp_observations"] = {a: o[("PPP_P31S14", a)]
                                    for a in ("GBR", "ESP", "ITA", "GRC")}
    for iso3, rec in sorted(RECORDED_UK_CROSSING.items()):
        compare(f"PPP UK->{ISO2[iso3]} (OECD fallback)",
                o[("PPP_P31S14", iso3)] / o[("PPP_P31S14", "GBR")], rec, rows)

    # Recorded as a caveat rather than a check. PROVIDER_TOOLREADY_2024.md justifies the
    # OECD fallback by saying the UK is absent from Eurostat prc_ppp_ind post-Brexit. It
    # is not absent: Eurostat returns a 2024 United Kingdom observation. The recorded
    # factors are still the OECD ones and still reproduce, and the two sources agree
    # inside the ~1% the document's own cross-check claims, so this is a wrong reason
    # attached to right numbers. Switching source would move three spines that appear on
    # every EU tool face, so nothing here changes one.
    if "UK" in P:
        raw["uk_in_eurostat_ppp"] = {
            "present": True, "value_2024": P["UK"],
            "eurostat_native_uk_crossing": {
                ISO2[i]: round(P[ISO2[i]] / P["UK"], 6) for i in RECORDED_UK_CROSSING},
            "note": ("PROVIDER_TOOLREADY_2024.md justifies the OECD fallback by the UK's "
                     "absence from this series. The UK is present. The recorded OECD "
                     "factors still reproduce; only the stated reason is wrong.")}
        print("\n  NOTE: the UK IS present in Eurostat prc_ppp_ind (2024 = "
              f"{P['UK']}), contrary to the reason recorded for the OECD fallback.")

    passed = all(r["within_tolerance"] for r in rows)
    print(f"\nOVERALL: {'ALL FACTORS REPRODUCE' if passed else 'DRIFT'} "
          f"({sum(r['within_tolerance'] for r in rows)} of {len(rows)}, tolerance {TOL})")

    if args.check:
        return 0 if passed else 1

    stamp = datetime.now(timezone.utc)
    artefact = {
        "what": "Source pull of the PPP factors and GDP deflators used by the provider layer.",
        "why": ("The factors were documented but never recomputed and never saved as a "
                "pull artefact. This file is that artefact."),
        "extracted_utc": stamp.isoformat(timespec="seconds"),
        "queries": {"eurostat_deflator": Q_DEFLATOR,
                    "eurostat_ppp": Q_PPP_EUROSTAT,
                    "oecd_ppp": Q_PPP_OECD},
        "source_last_updated": {"eurostat_nama_10_gdp": defl_updated,
                                "eurostat_prc_ppp_ind": ppp_updated},
        "tolerance": TOL,
        "all_reproduce": passed,
        "comparisons": rows,
        "raw": raw,
        "reverify": "py -3 europe/model/pull_ppp_deflators.py --check",
    }
    out = DOCS / f"ppp_deflator_pull_{stamp:%Y-%m-%d}.json"
    out.write_text(json.dumps(artefact, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"artefact written: {out.relative_to(HERE.parent.parent)}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
