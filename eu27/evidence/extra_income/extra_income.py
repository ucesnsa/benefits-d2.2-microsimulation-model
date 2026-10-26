"""Derived 'extra income' (the provider tool's cash-equivalent floor) for all 27 EU countries.

Task `extra_income`, 2026-09-30, under DECISIONS.md D5. Reads, never writes, everything outside
this folder. Run from anywhere:

    py extra_income.py            # uses the cached Eurostat pull in eurostat_extra.json
    py extra_income.py --pull     # re-pulls the extra Eurostat series first

Writes, in this folder: extra_income_results.json (all 27 countries, every profile x eps x reform
size, with inputs, sources and grades), extra_income_tables.md (the validation and summary tables
REPORT.md quotes), and eurostat_extra.json (the ESSPROS pull, cached).

THE QUANTITY (template.html renderProvider, ported as calc() in the plain-language view):
    band = PROFILES[profile] (zero-based deciles), k = len(band)
    pbU  = sum(deciles[ref][0][d] for d in band) * 10 / (k * UNITS_M * HH_SIZE)
    pbW  = same with deciles[ref][eps index];   kappa = pbW / pbU
deciles[ref][e][d] is the welfare-weighted gain of household decile d in EUR m, and
UNITS_M * HH_SIZE is the population in millions, so pbU is EUR per person per year.

THE DERIVATION (recommended; see REPORT.md for the candidates and their validation):
    pbU(c, band, r) = (r/100) * O_c * S_band(r) / ((k/10) * P_c)
    kappa(c, band, eps) = sum_{d in band} s_d(r) W_c,d(eps) / sum_{d in band} s_d(r)
    pbW = pbU * kappa
O_c   annual outlay on the country's main minimum-income scheme (administrative, see OUTLAY_RULE)
s_d   share of the reform's gain accruing to decile d, pooled from the ES, IT and EL model surfaces
S_band = sum of s_d over the band (1 for all deciles)
P_c   Eurostat population on 1 January of the outlay year (demo_pjan)
W_c,d the shipped WEVM social weight (wevm.social_weight: (max(y, 0.6 med)/med)^-eps) evaluated
      on the country's Eurostat equivalised income deciles (ilc_di01, ilc_di03)
"""
import datetime
import hashlib
import json
import math
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(BUILD, "build"))
from paths import DELIV, MACH  # noqa: E402
import views  # noqa: E402
FINDINGS = os.path.join(BUILD, "research", "country_income", "findings.jsonl")
SERIES = os.path.join(BUILD, "series", "eurostat_series.json")
BENADJ = os.path.join(DELIV, "europe", "docs", "benefit_adjustments.json")
WEVM_PY = os.path.join(DELIV, "europe", "Spain", "model", "wevm", "wevm.py")
SOURCES = os.path.join(HERE, "sources.jsonl")
EXTRA = os.path.join(HERE, "eurostat_extra.json")
OUT_JSON = os.path.join(HERE, "extra_income_results.json")
OUT_MD = os.path.join(HERE, "extra_income_tables.md")

EU27 = "AT BE BG HR CY CZ DK EE FI FR DE EL HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split()
MODELLED = {"ES": ("spain", "imv"), "IT": ("italy", "adi"), "EL": ("greece", "kea")}
SIZES = [10, 25, 50]
EPS = [0, 0.5, 1, 1.5, 2]
PROFILES = {"lowest": [0, 1, 2], "lowmid": [3, 4, 5], "all": list(range(10))}
PROFILE_LABEL = {"lowest": "Lowest incomes (deciles 1-3)", "lowmid": "Low-to-middle (deciles 4-6)",
                 "all": "Broad mix (all deciles)"}
PRICE_BASE = 2024
CURRENCY = {"CZ": "CZK", "DK": "DKK", "HU": "HUF", "PL": "PLN", "RO": "RON", "SE": "SEK"}  # else EUR
# Bulgaria joined the euro area on 1 January 2026; Eurostat's ESSPROS 'MIO_NAC' for BG is now EUR
# (asserted below), EU-SILC 'NAC' for BG is still BGN (used only as ratios here). The two BGN
# research records (country_income-003, -129) are converted at the fixed rate.
BGN_PER_EUR = 1.95583
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
EXTRA_SERIES = {
    "esspros_fex": "spr_exp_fex?spdep=CASH_P_INC&spdep=CASH&spdepm=MT&spdepm=TOTAL"
                   "&unit=MIO_NAC&unit=MIO_EUR&sinceTimePeriod=2019",
    "esspros_fun": "spr_exp_fun?spdep=CASH_P_UNE_FULL&spdepm=MT&unit=MIO_NAC&sinceTimePeriod=2019",
}

# ------------------------------------------------------------------------------------------
# Outlay rule (recommended).
# Step 1: EUROMOD's own external statistic for the country's main minimum-income instrument
#   (<ExternalStatistic> in the installed EUROMOD J2.0+ country XML; the figure EUROMOD calibrates
#   or validates that instrument against; the ES and EL model outlays are calibrated to exactly this
#   series), amount for the latest year up to 2024. The instrument is the one naming the scheme the
#   SPC 2025 MI Report calls the main scheme (country_income records 001-027).
# Step 2: named exceptions, where the EUROMOD figure is not the main scheme's cash benefit:
#   DE  EUROMOD's MI instrument is Sozialhilfe only; the Buergergeld line (bunnc_s) does not say
#       whether it carries housing costs -> SPC record country_income-180 (EUR 29bn, excl. housing)
#   CZ  EUROMOD bsa_s includes the housing supplement -> SPC record -179, allowance for living only
#   FR  EUROMOD bsa00_s is metropolitan France only -> DREES, whole France (extra_income-S01)
#   IT  the latest EUROMOD figure (2023) is the RdC, replaced by the ADI in 2024 -> SPC record -185
# ESSPROS, the SPC outlays elsewhere, the JRC EUROMOD J1.28 simulation and recipients x rate are
# computed for every country as cross-checks, never as the value.
# ------------------------------------------------------------------------------------------
EUROMOD_XML_DIR = os.path.join(os.environ.get("EUROMOD_MODEL_PATH") or os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "euromod", "EUROMOD_RELEASES_J2.0+"), "XMLParam", "Countries")
EUROMOD_CACHE = os.path.join(HERE, "euromod_extstat.json")
EM_MAX_YEAR = 2024
# cc: (reference, keyword that must be in the description, currency of the amounts)
EM_INSTRUMENT = {
    "AT": ("bsa_s", "Mindestsicherung"), "BE": ("bsa_s", "Income support"),
    "BG": ("bsa00_s", "guaranteed minimum income"), "CY": ("bsamm_s", "guaranteed minimum income"),
    "CZ": ("bsa_s", "socialni potrebnosti"), "DE": ("bunnc_s", "ALG II"),
    "DK": ("bsa_s", "Kontanthj"), "EE": ("bsa00_s", "toimetulekutoetus"), "EL": ("bsa00_s", "GMI"),
    "ES": ("bsa00_s", "Ingreso Minimo Vital"), "FI": ("bsa00_s", "income support"),
    "FR": ("bsa00_s", "RSA"), "HR": ("bsa_s", "minimalna naknada"), "HU": ("bsa_s", "social assistance"),
    "IE": ("bunnc_s", "jobseekers allowance"), "IT": ("bsamm_s", "REI"),
    "LT": ("bsa00_s", "socialine pasalpa"), "LU": ("bsacm_s", "Revenu minimum garanti"),
    "LV": ("bsamm_s", "minimālā ienākuma"), "MT": ("bsa_s", "Social assistance"),
    "NL": ("bsa00_s", "social assistance : main"), "PL": ("bsatm_s", "okresowy"),
    "PT": ("bsa00_s", "social insertion income"), "RO": ("bsa00_s", "Minimum inclusion income"),
    "SE": ("bsamt_s", "Social Assistance (means-tested)"), "SI": ("bsa_s", "social assistance"),
    "SK": ("bsa_s", "Material needs"),
}
EM_EXCEPTION = {
    "DE": "EUROMOD's minimum-income instrument (bsa00_s) is Sozialhilfe only; its Buergergeld line "
          "(bunnc_s, ALG II und Sozialgeld) does not state whether housing costs are in it",
    "CZ": "EUROMOD bsa_s (CZK 6,520m, 2024) carries the housing supplement; the SPC record splits it out",
    "FR": "EUROMOD bsa00_s is metropolitan France only (its own comment 'Figures Metropole')",
    "IT": "EUROMOD's latest figure (2023) is the Reddito di Cittadinanza, replaced by the ADI in 2024",
}
# LU: EUROMOD's 2024 amount repeats 2023 exactly (193.21); read as carried forward, dated 2023.
EM_CARRIED_FORWARD = {"LU": 2023}
EM_BGN = {"BG"}  # BG amounts in the XML are BGN (2023 matches ESSPROS 2023 EUR 26.91m x 1.95583)
ADMIN = {
    # cc: (record id, multiplier to national-currency millions, text that must be in the record, note)
    "DE": ("country_income-180", 1000.0, "Buergergeld",
           "as reported (approximately EUR 29bn); includes social insurance paid for recipients, "
           "excludes municipal housing and heating costs"),
    "EL": ("country_income-181", 1e-6, "Guaranteed Minimum Income", "as reported"),
    "ES": ("country_income-182", 1e-6, "CAPI", "as reported; IMV gross payroll INCLUDING the child "
           "complement CAPI"),
    "FI": ("country_income-183", 1.0, "social assistance", "as reported (basic, supplementary and "
           "preventive social assistance)"),
    "IE": ("country_income-184", 1000.0, "Jobseeker's Allowance", "as reported: Jobseeker's "
           "Allowance, 2025 PREDICTED; Basic Supplementary Welfare Allowance (EUR 137m) not added"),
    "IT": ("country_income-185", 1.0, "ADI", "as reported: 2025 Budget Law AUTHORISATION, not outturn"),
    "LV": ("country_income-187", 1e-6, "GMI", "as reported: GMI benefit only, housing benefit excluded "
           "by the record"),
    "PL": ("country_income-188", 1e-6, "temporary benefits", "as reported: temporary benefit (zasilek "
           "okresowy) only; the permanent allowance is not in it"),
    "PT": ("country_income-189", 12.0, "Rendimento Social", "December 2024 MONTHLY expenditure x 12"),
    "RO": ("country_income-190", 1e-6, "minimum inclusion income", "as reported (all components of the "
           "minimum inclusion income)"),
    "SE": ("country_income-191", 1.0, "ekonomiskt bistand", "as reported"),
    "SI": ("country_income-192", 1e-6, "social cash assistance", "as reported; income support (IS, "
           "EUR 59.7m) excluded by the record"),
    "SK": ("country_income-193", 1e-6, "material need", "as reported"),
}
# CZ: the record total (CZK 6.62bn) includes the housing supplement and extraordinary immediate
# assistance; the record's definition states the allowance-for-living component, which is used.
CZ_SPLIT = ("country_income-179", "allowance for living 4.18bn", 4180.0)
# LT: the record (EUR 215.4m) includes heating and water compensations with no split -> step 3.
LT_EXCLUDED = ("country_income-186", "heating/water compensations")
STEP2 = {"FR": ("extra_income-S01", 1.0), "NL": ("extra_income-S02", 1e-3)}

# Recipients x scheme amount (candidate D, cross-check only). The count is the benefit-unit count
# where the record gives one (often in its unit text), else persons. Amount = the single-person
# rate of the record, monthly (weekly x 52/12).
RECIP = {
    "AT": ("country_income-055", 108206, "households (unit text)", "country_income-001", 1.0),
    "BE": ("country_income-056", 165500, "beneficiaries", "country_income-002", 1.0),
    "BG": ("country_income-057", 48994, "families (unit text)", "country_income-003", 1 / BGN_PER_EUR),
    "CZ": ("country_income-058", 63900, "households", "country_income-005", 1.0),
    "DE": ("country_income-059", 2930000, "households (unit text)", "country_income-006", 1.0),
    "DK": ("country_income-060", 79300, "full-time persons", "country_income-007", 7.4589),  # EUR amount -> DKK at 2024 avg
    "EE": ("country_income-061", 19591, "households (unit text)", "country_income-008", 1.0),
    "EL": ("country_income-062", 172687, "households (unit text)", "country_income-009", 1.0),
    "ES": ("country_income-063", 673729, "households (unit text)", "country_income-010", 1.0),
    "FI": ("country_income-064", 263355, "households (unit text)", "country_income-011", 1.0),
    "FR": ("country_income-065", 1860000, "households", "country_income-012", 1.0),
    "HR": ("country_income-066", 44286, "individuals", "country_income-013", 1.0),
    "HU": ("country_income-067", 57000, "persons", "country_income-014", 1.0),
    "IE": ("country_income-068", 108000, "persons", "country_income-015", 52 / 12),
    "IT": ("country_income-069", 760000, "households (unit text)", "country_income-016", 1.0),
    "LT": ("country_income-070", 68700, "recipients", "country_income-017", 1.0),
    "LU": ("country_income-071", 11273, "households (unit text)", "country_income-018", 1.0),
    "LV": ("country_income-072", 70384, "households (unit text)", "country_income-019", 1.0),
    "MT": ("country_income-073", 3158, "beneficiaries", "country_income-020", 52 / 12),
    "NL": ("country_income-074", 343000, "households (unit text)", "country_income-021", 1.0),
    "PL": ("country_income-075", 421470, "persons and families", "country_income-022", 1.0),
    "PT": ("country_income-076", 114940, "households (unit text)", "country_income-023", 1.0),
    "RO": ("country_income-077", 219569, "families/single persons", "country_income-024", 1.0),
    "SE": ("country_income-078", 260000, "persons", "country_income-025", 1.0),
    "SI": ("country_income-079", 72000, "beneficiaries", "country_income-026", 1.0),
    "SK": ("country_income-080", 61902, "households", "country_income-027", 1.0),
}


# ------------------------------------------------------------------------------------------
# Loading
# ------------------------------------------------------------------------------------------
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def repo_path(v):
    """A path as it reads in the repository: eu27/... for this build, else from the repository root."""
    v = os.path.abspath(v)
    if v.startswith(BUILD + os.sep):
        return "eu27/" + os.path.relpath(v, BUILD).replace(os.sep, "/")
    return os.path.relpath(v, DELIV).replace(os.sep, "/")


def unpack(d):
    dims, sizes = d["id"], d["size"]
    inv = {k: {i: v for v, i in d["dimension"][k]["category"]["index"].items()} for k in dims}
    out = []
    for flat, val in d.get("value", {}).items():
        n, coords = int(flat), {}
        for k, s in zip(reversed(dims), reversed(sizes)):
            coords[k] = inv[k][n % s]
            n //= s
        coords["value"] = val
        out.append(coords)
    return out


def pull_extra():
    res = {"pulled": datetime.date.today().isoformat(), "urls": {}, "rows": {}}
    for name, path in EXTRA_SERIES.items():
        url = EUROSTAT + path + "&format=JSON&lang=EN"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        d = json.load(urllib.request.urlopen(req, timeout=180))
        res["urls"][name] = url
        res["rows"][name] = [r for r in unpack(d) if r.get("geo") in EU27]
    json.dump(res, open(EXTRA, "w", encoding="utf-8"), indent=0)
    return res


def load_all(pull):
    recs = {}
    for fn in (FINDINGS, SOURCES):
        for line in open(fn, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                recs[r["id"]] = r
    series = json.load(open(SERIES, encoding="utf-8"))
    extra = pull_extra() if (pull or not os.path.exists(EXTRA)) else json.load(open(EXTRA, encoding="utf-8"))
    benadj = json.load(open(BENADJ, encoding="utf-8"))
    return recs, series, extra, benadj


# ------------------------------------------------------------------------------------------
# Modelled truth (ES, IT, EL)
# ------------------------------------------------------------------------------------------
def model_truth():
    out = {}
    for cc, (fn, pre) in MODELLED.items():
        # The income deciles, population basis and profiles of the D2.2 country block, read the
        # same way the provider tab reads them at load.
        path = os.path.join(MACH, "country_%s.json" % cc.lower())
        d = views.extract_static(json.load(open(path, encoding="utf-8")))
        assert d["epsGrid"] == EPS
        for p, band in PROFILES.items():
            assert d["PROFILES"][PROFILE_LABEL[p]] == band, (cc, p)
        units_m = d["pb"]["units_k"] / 1000
        hh = d["pb"]["population_k"] / d["pb"]["units_k"]
        pop_m = units_m * hh
        t = {"source": repo_path(path), "sha256": sha256(path), "units_m": units_m,
             "hh_size": hh, "population_m": pop_m, "refs": {}, "shares": {}, "band_totals": {},
             "pbU": {}, "pbW": {}, "kappa": {}}
        for r in SIZES:
            ref = f"{pre}_{r}"
            D = d["deciles"][ref]
            tot = sum(D[0])
            t["refs"][r] = {"key": ref, "label": d["labels"][ref], "total_gain_eur_m": round(tot, 3)}
            t["shares"][r] = [x / tot for x in D[0]]
            for p, band in PROFILES.items():
                k = len(band)
                vals = [sum(D[ei][x] for x in band) * 10 / (k * units_m * hh) for ei in range(len(EPS))]
                t["pbU"].setdefault(p, {})[r] = vals[0]
                t["pbW"].setdefault(p, {})[r] = vals
                t["kappa"].setdefault(p, {})[r] = [v / vals[0] for v in vals]
        out[cc] = t
    return out


def pooled_shares(truth, members):
    return {r: [sum(truth[c]["shares"][r][d] for c in members) / len(members) for d in range(10)]
            for r in SIZES}


def band_share(shares, p):
    return sum(shares[d] for d in PROFILES[p])


# ------------------------------------------------------------------------------------------
# Eurostat helpers
# ------------------------------------------------------------------------------------------
def s_get(series, name, cc, year):
    v = series["series"][name].get(cc, {}).get(str(year))
    return v


def latest_complete_silc(series, cc, prefer=None):
    years = sorted({k.split("|")[0] for k in series["series"]["decile_top_cutoff_nac"].get(cc, {})})
    if prefer:
        years = [y for y in years if y == str(prefer)]
    for y in reversed(years):
        tc = [series["series"]["decile_top_cutoff_nac"][cc].get(f"{y}|D{i}") for i in range(1, 10)]
        sh = [series["series"]["decile_share_pct"][cc].get(f"{y}|D{i}") for i in range(1, 11)]
        med = s_get(series, "median_equiv_income_nac", cc, y)
        mean = s_get(series, "mean_equiv_income_nac", cc, y)
        if None not in tc and None not in sh and med and mean:
            return {"year": int(y), "tc": tc, "share_pct": sh, "median": med, "mean": mean}
    return None


def social_weight(y, eps, y_ref, floor):
    """wevm.social_weight, verbatim: (max(y, floor) / y_ref) ** (-eps)."""
    return (max(y, floor) / y_ref) ** (-eps)


def decile_weights(silc, method):
    """W_d(eps) for d = 1..10 on the Eurostat deciles. K1: the weight at the decile mean
    (share x 10 x mean). K2: the mean weight over a uniform spread between the decile's cut-offs
    (D1 from max(0, 2 x mean_D1 - TC1), D10 to 2 x mean_D10 - TC9)."""
    med, mean, tc, sh = silc["median"], silc["mean"], silc["tc"], silc["share_pct"]
    floor = 0.6 * med
    m = [sh[d] / 100 * 10 * mean for d in range(10)]
    lo = [max(0.0, 2 * m[0] - tc[0])] + tc[:9]
    hi = tc[:9] + [max(tc[8], 2 * m[9] - tc[8])]
    W = {}
    for eps in EPS:
        row = []
        for d in range(10):
            if method == "K1":
                row.append(social_weight(m[d], eps, med, floor))
            else:
                n = 400
                ys = [lo[d] + (hi[d] - lo[d]) * (i + 0.5) / n for i in range(n)]
                row.append(sum(social_weight(y, eps, med, floor) for y in ys) / n)
        W[eps] = row
    return W, m


def kappa_from(W, shares, p):
    band = PROFILES[p]
    den = sum(shares[d] for d in band)
    return [sum(shares[d] * W[eps][d] for d in band) / den for eps in EPS]


def defl(series, cc, year, base=PRICE_BASE):
    return s_get(series, "gdp_deflator_2015eq100", cc, base) / s_get(series, "gdp_deflator_2015eq100", cc, year)


def fx(series, cc):
    cur = CURRENCY.get(cc)
    return 1.0 if cur is None else series["series"]["eur_exchange_rate_avg"][cur][str(PRICE_BASE)]


# ------------------------------------------------------------------------------------------
# Outlay candidates
# ------------------------------------------------------------------------------------------
def esspros(extra, cc, spdep, year=None, unit="MIO_NAC"):
    rows = [r for r in extra["rows"]["esspros_fex"] if r["geo"] == cc and r["spdep"] == spdep
            and r["spdepm"] == "MT" and r["unit"] == unit and r["value"] not in (None, 0)]
    if year is not None:
        rows = [r for r in rows if r["time"] == str(year)]
    if not rows:
        return None
    r = max(rows, key=lambda x: x["time"])
    return {"value_m": r["value"], "year": int(r["time"]),
            "series": f"spr_exp_fex spdep={spdep} spdepm=MT unit={unit} geo={cc} time={r['time']}"}


def read_euromod():
    """EUROMOD <ExternalStatistic> rows for each country's main MI instrument. Read from the
    installed model if present (and cached here with each XML's sha256), else from the cache."""
    blk = re.compile(r"<ExternalStatistic>(.*?)</ExternalStatistic>", re.S)

    def tag(b, n):
        m = re.search(r"<%s>(.*?)</%s>" % (n, n), b, re.S)
        return "" if m is None else re.sub(r"^<!\[CDATA\[|\]\]>$", "", m.group(1).strip()).strip()

    if not os.path.isdir(EUROMOD_XML_DIR):
        return json.load(open(EUROMOD_CACHE, encoding="utf-8"))
    out = {"read_from": "the installed EUROMOD J2.0+ release, XMLParam/Countries", "read_on": datetime.date.today().isoformat(), "countries": {}}
    for cc, (ref, must) in EM_INSTRUMENT.items():
        path = os.path.join(EUROMOD_XML_DIR, cc, cc + ".xml")
        raw = open(path, "rb").read()
        txt = raw.decode("utf-8", errors="replace")
        row = None
        for b in blk.findall(txt):
            if tag(b, "Reference") == ref and tag(b, "Category") == "ils_benmt":
                years = {}
                for part in tag(b, "YearValues").split("°"):
                    p = part.split("|")
                    if len(p) >= 3 and p[0]:
                        years[p[0]] = {"amount_m": p[1] or None, "count_k": p[2] or None}
                row = {"reference": ref, "description": tag(b, "Description"), "source": tag(b, "Source"),
                       "comment": tag(b, "Comment"), "years": years}
                break
        assert row is not None, (cc, ref)
        assert must.lower() in row["description"].lower(), (cc, ref, row["description"])
        row["xml"] = os.path.relpath(path, os.path.dirname(EUROMOD_XML_DIR.rstrip(os.sep)))
        row["xml_sha256"] = hashlib.sha256(raw).hexdigest()
        row["xml_modified"] = datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
        out["countries"][cc] = row
    json.dump(out, open(EUROMOD_CACHE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return out


def euromod_outlay(cc, em, max_year=EM_MAX_YEAR, year=None):
    row = em["countries"][cc]
    ys = [int(y) for y, v in row["years"].items() if v["amount_m"] not in (None, "", "#N/A")
          and int(y) <= max_year and (year is None or int(y) == year)]
    if not ys:
        return None
    y = max(ys)
    val = float(row["years"][str(y)]["amount_m"])
    dated = EM_CARRIED_FORWARD.get(cc, y) if year is None else y
    if cc in EM_BGN:
        val = val / BGN_PER_EUR
    note = f"EUROMOD external statistic {row['reference']} ({row['description'][:70]}), source: {row['source'][:80] or 'not stated'}"
    if cc in EM_CARRIED_FORWARD and year is None:
        note += f"; the {y} amount repeats {dated} exactly and is dated {dated}"
    if cc in EM_BGN:
        note += f"; BGN {row['years'][str(y)]['amount_m']}m converted at {BGN_PER_EUR}"
    return {"value_m": val, "year": dated, "source": f"EUROMOD J2.0+ {row['xml']} ExternalStatistic "
            f"Reference={row['reference']} year={y}", "note": note,
            "count_k": row["years"][str(y)]["count_k"]}


def spc_outlay(cc, recs):
    if cc in ADMIN:
        rid, mult, must, note = ADMIN[cc]
        r = recs[rid]
        assert must.lower() in (r["definition"] + r["unit"]).lower(), (cc, rid, must)
        return {"value_m": r["value"] * mult, "year": int(r["reference_year"]), "source": rid, "note": note}
    if cc == "CZ":
        rid, must, v = CZ_SPLIT
        assert must in recs[rid]["definition"], rid
        return {"value_m": v, "year": int(recs[rid]["reference_year"]), "source": rid,
                "note": "allowance for living only (CZK 4.18bn), as split in the record definition; housing "
                        "supplement (1.67bn) and extraordinary immediate assistance (0.77bn) excluded; record "
                        "total CZK 6.62bn"}
    if cc == "LT":
        r = recs[LT_EXCLUDED[0]]
        return {"value_m": r["value"], "year": int(r["reference_year"]), "source": r["id"],
                "note": "includes heating and water compensations, no split"}
    return None


def outlay_rule(cc, recs, extra, em):
    """The recommended outlay (national-currency millions) with its provenance."""
    if cc in EM_EXCEPTION:
        if cc == "FR":
            r = recs[STEP2["FR"][0]]
            o = {"value_m": r["value"], "year": int(r["reference_year"]), "source": r["id"],
                 "note": "DREES RSA allocations, whole France, outturn"}
        else:
            o = spc_outlay(cc, recs)
        o = dict(o, step=2, why=EM_EXCEPTION[cc])
        return o
    return dict(euromod_outlay(cc, em), step=1)


def esspros_outlay(cc, extra, year=None):
    """Harmonised alternative: ESSPROS social-exclusion function, means-tested periodic income
    support (CASH_P_INC). HU: all means-tested cash of the function (its income support is recorded
    as zero). DE, IE: plus means-tested full-unemployment cash of the unemployment function, where
    ESSPROS classifies Buergergeld and Jobseeker's Allowance; the year is the latest with both."""
    spdep = "CASH" if cc == "HU" else "CASH_P_INC"
    if cc in ("DE", "IE"):
        fex = {r["time"]: r["value"] for r in extra["rows"]["esspros_fex"] if r["geo"] == cc and r["spdep"] == spdep
               and r["spdepm"] == "MT" and r["unit"] == "MIO_NAC" and r["value"] is not None}
        fun = {r["time"]: r["value"] for r in extra["rows"]["esspros_fun"] if r["geo"] == cc
               and r["spdepm"] == "MT" and r["unit"] == "MIO_NAC" and r["value"] is not None}
        ys = sorted(set(fex) & set(fun))
        if year is not None:
            ys = [y for y in ys if y == str(year)]
        if not ys:
            return None
        y = ys[-1]
        return {"value_m": fex[y] + fun[y], "year": int(y),
                "source": f"spr_exp_fex CASH_P_INC MT + spr_exp_fun CASH_P_UNE_FULL MT, geo={cc} time={y}"}
    e = esspros(extra, cc, spdep, year)
    if e is None:
        return None
    return {"value_m": e["value_m"], "year": e["year"], "source": e["series"]}


def jrc_outlay(cc, recs):
    """JRC144742 Annex 3 'MIS spending' (printed per month) x 12, with the product check."""
    for r in recs.values():
        if r.get("country") == cc and "JRC144742" in r["source"].get("title", "") and "MONTHLY" in r["unit"]:
            m = re.search(r"([\d,]+) beneficiaries x ([\d.]+) average monthly benefit = ([\d.]+)", r["derivation"])
            prod = float(m.group(3)) if m else None
            mult = (1 / BGN_PER_EUR) if cc == "BG" else 1.0
            return {"value_m": r["value"] * 12 * mult, "year": 2024, "source": r["id"],
                    "product_over_printed": (prod / r["value"]) if prod else None}
    return None


def recip_outlay(cc, recs):
    if cc not in RECIP:
        return None
    rid, n, unit, aid, conv = RECIP[cc]
    a = recs[aid]
    per_month = a["value"] * conv
    return {"value_m": n * per_month * 12 / 1e6, "year": int(recs[rid]["reference_year"] or a["reference_year"]),
            "source": f"{rid} ({n:,} {unit}) x {aid} ({a['value']} {a['unit'][:40]})"}


# ------------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------------
def pct(x):
    return None if x is None else round(100 * x, 1)


def main():
    recs, series, extra, benadj = load_all("--pull" in sys.argv)
    # BG: ESSPROS MIO_NAC must equal MIO_EUR (Eurostat has moved BG to EUR)
    bg_nac = esspros(extra, "BG", "CASH_P_INC")
    bg_eur = esspros(extra, "BG", "CASH_P_INC", unit="MIO_EUR")
    assert abs(bg_nac["value_m"] - bg_eur["value_m"]) < 1e-9 and bg_nac["year"] == bg_eur["year"]

    em = read_euromod()
    truth = model_truth()
    pool = pooled_shares(truth, list(MODELLED))
    loo = {c: pooled_shares(truth, [x for x in MODELLED if x != c]) for c in MODELLED}
    md = []

    # ---------------- validation: outlay candidates on ES, IT, EL ----------------------------
    cand = {}
    for cc in MODELLED:
        b = benadj[cc]
        ext = b["external_statistic"]["years"]
        e23 = euromod_outlay(cc, em, year=2023)
        # the EUROMOD install and the Deliverable's own record of the calibration target must agree
        assert abs(e23["value_m"] - float(ext["2023"]["amount_eur_m"])) < 0.5, cc
        cand[cc] = {
            "M_model": {"value_m": b["modelled_outlay_eur_m"], "year": 2023,
                        "source": "Deliverable/europe/docs/benefit_adjustments.json modelled_outlay_eur_m"},
            "R_recommended": outlay_rule(cc, recs, extra, em),
            "E_euromod_2023": dict(e23, source=e23["source"] + " (= benefit_adjustments.json "
                                   "external_statistic 2023, the model-year actual)"),
            "E_euromod_latest": euromod_outlay(cc, em),
            "A_admin_SPC": spc_outlay(cc, recs),
            "B_esspros_2023": esspros_outlay(cc, extra, 2023),
            "B_esspros_latest": esspros_outlay(cc, extra),
            "C_jrc_euromod_x12": jrc_outlay(cc, recs),
            "D_recipients_x_rate": recip_outlay(cc, recs),
        }
    cand_order = list(cand["ES"])

    val_rows = {}
    for cc, t in truth.items():
        d23 = defl(series, cc, 2023)
        for name, o in cand[cc].items():
            pop = s_get(series, "population_1jan", cc, o["year"]) / 1e6
            f = defl(series, cc, o["year"])
            for p in PROFILES:
                k = len(PROFILES[p])
                for r in SIZES:
                    der = (r / 100) * o["value_m"] * f * band_share(loo[cc][r], p) / (k / 10 * pop)
                    tru = t["pbU"][p][r] * d23
                    val_rows.setdefault(name, {}).setdefault(cc, {}).setdefault(p, {})[r] = {
                        "derived_2024": der, "modelled_2024": tru, "err": der / tru - 1}
    # identity check: model outlay, own shares, model population, no price change
    ident = {}
    for cc, t in truth.items():
        O = cand[cc]["M_model"]["value_m"]
        for p in PROFILES:
            k = len(PROFILES[p])
            for r in SIZES:
                der = (r / 100) * O * band_share(t["shares"][r], p) / (k / 10 * t["population_m"])
                ident.setdefault(cc, {}).setdefault(p, {})[r] = der / t["pbU"][p][r] - 1

    def mae(name, profs=("lowest", "lowmid", "all")):
        e = [abs(val_rows[name][c][p][r]["err"]) for c in MODELLED for p in profs for r in SIZES]
        return sum(e) / len(e)

    md.append("## 1. Modelled truth (EUR per person per year, 2023 money, from the D2.2 country blocks)\n")
    md.append("| country | profile | +10% pbU | +25% pbU | +50% pbU | +25% pbW eps0.5 | eps1 | eps1.5 | eps2 | kappa eps1 (+25%) |")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for cc, t in truth.items():
        for p in PROFILES:
            w = t["pbW"][p][25]
            md.append(f"| {cc} | {PROFILE_LABEL[p]} | {t['pbU'][p][10]:.2f} | {t['pbU'][p][25]:.2f} | "
                      f"{t['pbU'][p][50]:.2f} | {w[1]:.2f} | {w[2]:.2f} | {w[3]:.2f} | {w[4]:.2f} | "
                      f"{t['kappa'][p][25][2]:.3f} |")
    md.append("")
    md.append("Gain shares by decile at +25% (share of the reform's total gain, eps 0):\n")
    md.append("| | " + " | ".join(f"D{d}" for d in range(1, 11)) + " | D1-3 | D4-6 |")
    md.append("|---|" + "---:|" * 12)
    for cc, t in truth.items():
        s = t["shares"][25]
        md.append(f"| {cc} | " + " | ".join(f"{100 * x:.1f}" for x in s) +
                  f" | {100 * band_share(s, 'lowest'):.1f} | {100 * band_share(s, 'lowmid'):.1f} |")
    s = pool[25]
    md.append("| pooled | " + " | ".join(f"{100 * x:.1f}" for x in s) +
              f" | {100 * band_share(s, 'lowest'):.1f} | {100 * band_share(s, 'lowmid'):.1f} |")
    md.append("")
    md.append("Reform linearity (total modelled gain / (r x modelled baseline outlay)): " + "; ".join(
        f"{cc} " + ", ".join(f"+{r}%: {truth[cc]['refs'][r]['total_gain_eur_m'] / (r / 100 * cand[cc]['M_model']['value_m']):.3f}"
                             for r in SIZES) for cc in MODELLED) + "\n")
    md.append("Identity check (model outlay, own shares, model population): max |error| "
              + ", ".join(f"{cc} {100 * max(abs(v) for p in ident[cc] for v in ident[cc][p].values()):.1f}%"
                          for cc in MODELLED) + " (IT: the dial scales the base amount, so it is not linear in r).\n")

    md.append("## 2. Outlay candidates on the three modelled countries (EUR m per year, nominal, own year)\n")
    md.append("| candidate | ES | IT | EL | source |")
    md.append("|---|---:|---:|---:|---|")
    for name in cand_order:
        cells = []
        for cc in MODELLED:
            o = cand[cc][name]
            cells.append(f"{o['value_m']:,.1f} ({o['year']})")
        md.append(f"| {name} | " + " | ".join(cells) + f" | {cand['ES'][name]['source'][:90]} ... |")
    md.append("")
    md.append("Ratio to the modelled outlay, both at 2024 prices: " + "; ".join(
        f"{name}: " + ", ".join(
            f"{cc} {cand[cc][name]['value_m'] * defl(series, cc, cand[cc][name]['year']) / (cand[cc]['M_model']['value_m'] * defl(series, cc, 2023)):.2f}"
            for cc in MODELLED) for name in cand_order) + "\n")

    md.append("## 3. Validation: derived pbU vs modelled pbU (leave-one-out band shares, Eurostat population, both at 2024 prices)\n")
    md.append("Error = derived / modelled - 1, in per cent.\n")
    md.append("| candidate | profile | ES +10 | ES +25 | ES +50 | IT +10 | IT +25 | IT +50 | EL +10 | EL +25 | EL +50 | MAE all cells |")
    md.append("|---|---|" + "---:|" * 10)
    for name in cand_order:
        for p in PROFILES:
            cells = [f"{pct(val_rows[name][cc][p][r]['err']):+.1f}" for cc in MODELLED for r in SIZES]
            md.append(f"| {name} | {p} | " + " | ".join(cells) + (f" | {100 * mae(name):.1f} |" if p == "lowest" else " | |"))
    md.append("")
    md.append("MAE by profile group (per cent): " + "; ".join(
        f"{name}: D1-3 & all {100 * mae(name, ('lowest', 'all')):.1f}, D4-6 {100 * mae(name, ('lowmid',)):.1f}"
        for name in cand_order) + "\n")

    # decomposition of the recommended candidate and of the model-year actual
    md.append("## 4. Error decomposition, default profile D1-3, +25%\n")
    md.append("derived/modelled = outlay factor x band-share factor x population factor x reform-shape factor\n")
    md.append("| outlay used | country | outlay (used/model, 2024 prices) | band share (LOO/own) | population (model/Eurostat) | reform shape (linear/model) | product | derived/modelled |")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|")
    decomp = {}
    for name in ("R_recommended", "E_euromod_2023"):
        for cc, t in truth.items():
            oA, oM = cand[cc][name], cand[cc]["M_model"]
            fo = oA["value_m"] * defl(series, cc, oA["year"]) / (oM["value_m"] * defl(series, cc, 2023))
            fs = band_share(loo[cc][25], "lowest") / band_share(t["shares"][25], "lowest")
            fp = t["population_m"] / (s_get(series, "population_1jan", cc, oA["year"]) / 1e6)
            fr = (0.25 * oM["value_m"]) / t["refs"][25]["total_gain_eur_m"]
            tot = fo * fs * fp * fr
            dm = val_rows[name][cc]["lowest"][25]["err"] + 1
            decomp.setdefault(name, {})[cc] = {"outlay": fo, "band_share": fs, "population": fp,
                                               "reform_shape": fr, "product": tot, "derived_over_modelled": dm}
            md.append(f"| {name} | {cc} | {fo:.3f} | {fs:.3f} | {fp:.3f} | {fr:.3f} | {tot:.3f} | {dm:.3f} |")
    md.append("")

    # ---------------- validation: kappa ----------------------------------------------------
    kval = {}
    for cc, t in truth.items():
        for yr in (2024, 2025):
            silc = latest_complete_silc(series, cc, prefer=yr)
            for meth in ("K1", "K2"):
                W, _ = decile_weights(silc, meth)
                for patt, sh in (("own", t["shares"]), ("loo", loo[cc])):
                    for p in PROFILES:
                        for r in SIZES:
                            kd = kappa_from(W, sh[r], p)
                            km = t["kappa"][p][r]
                            kval.setdefault(f"{meth}_{patt}_{yr}", {}).setdefault(cc, {}).setdefault(p, {})[r] = \
                                [kd[i] / km[i] - 1 for i in range(len(EPS))]

    def kmae(key, profs=("lowest", "lowmid", "all")):
        e = [abs(kval[key][c][p][r][i]) for c in MODELLED for p in profs for r in SIZES for i in range(1, len(EPS))]
        return sum(e) / len(e)

    kchoice = min(("K1", "K2"), key=lambda m: kmae(f"{m}_loo_2025"))
    md.append("## 5. Validation: kappa from Eurostat deciles vs modelled kappa\n")
    md.append("Mean absolute error over ES, IT, EL x 3 profiles x 3 sizes x eps 0.5-2 (per cent):\n")
    md.append("| method | pattern | SILC 2024 (model wave) | SILC 2025 (latest) |")
    md.append("|---|---|---:|---:|")
    for meth in ("K1", "K2"):
        for patt in ("own", "loo"):
            md.append(f"| {meth} | {patt} | {100 * kmae(f'{meth}_{patt}_2024'):.2f} | {100 * kmae(f'{meth}_{patt}_2025'):.2f} |")
    md.append(f"\nSelected (lowest MAE, leave-one-out pattern, latest wave): **{kchoice}**.\n")
    md.append(f"Detail, {kchoice}, leave-one-out pattern, SILC 2025, +25%: modelled kappa -> derived kappa (error %)\n")
    md.append("| country | profile | eps 0.5 | eps 1 | eps 1.5 | eps 2 |")
    md.append("|---|---|---|---|---|---|")
    silc_cache = {}
    for cc, t in truth.items():
        silc = latest_complete_silc(series, cc, prefer=2025)
        W, _ = decile_weights(silc, kchoice)
        for p in PROFILES:
            kd = kappa_from(W, loo[cc][25], p)
            km = t["kappa"][p][25]
            md.append(f"| {cc} | {p} | " + " | ".join(
                f"{km[i]:.3f} -> {kd[i]:.3f} ({100 * (kd[i] / km[i] - 1):+.1f})" for i in range(1, len(EPS))) + " |")
    md.append("")

    # ---------------- all 27 --------------------------------------------------------------
    countries = {}
    band_range = {r: {p: (min(band_share(truth[c]["shares"][r], p) for c in MODELLED),
                          max(band_share(truth[c]["shares"][r], p) for c in MODELLED)) for p in PROFILES}
                  for r in SIZES}
    for cc in EU27:
        o = outlay_rule(cc, recs, extra, em)
        cur = CURRENCY.get(cc, "EUR")
        yr = o["year"]
        pop = s_get(series, "population_1jan", cc, yr)
        hh_k = s_get(series, "households_thousands", cc, yr) or s_get(series, "households_thousands", cc, PRICE_BASE)
        f = defl(series, cc, yr)
        rate = fx(series, cc)
        O24 = o["value_m"] * f
        silc = latest_complete_silc(series, cc)
        W, dmeans = decile_weights(silc, kchoice)
        vals = {}
        for p, band in PROFILES.items():
            k = len(band)
            vals[p] = {}
            for r in SIZES:
                pbU = (r / 100) * O24 * band_share(pool[r], p) / (k / 10 * pop / 1e6)
                kap = kappa_from(W, pool[r], p)
                lo, hi = band_range[r][p]
                pbU_lo = (r / 100) * O24 * lo / (k / 10 * pop / 1e6)
                pbU_hi = (r / 100) * O24 * hi / (k / 10 * pop / 1e6)
                vals[p][r] = {
                    "pbU_nac_2024": round(pbU, 2), "pbU_eur_2024": round(pbU / rate, 2),
                    "pbU_range_nac_2024": [round(pbU_lo, 2), round(pbU_hi, 2)],
                    "kappa": [round(x, 4) for x in kap],
                    "pbW_nac_2024": {str(e): round(pbU * kap[i], 2) for i, e in enumerate(EPS)},
                    "pbW_eur_2024": {str(e): round(pbU * kap[i] / rate, 2) for i, e in enumerate(EPS)},
                }
        # tool-ready block: deciles in national-currency millions at 2024 prices, such that the
        # tool's own calc() reproduces pbU and pbW exactly.
        tool = {"pb": {"units_k": hh_k, "population_k": pop / 1000,
                       "note": "units_k = Eurostat lfst_hhnhtych households; population_k = demo_pjan; only "
                               "their product enters pbU/pbW"},
                "deciles": {}, "labels": {}}
        for r in SIZES:
            key = f"mi_{r}"
            tool["deciles"][key] = [[round((r / 100) * O24 * pool[r][d] * W[e][d], 4) for d in range(10)] for e in EPS]
            tool["labels"][key] = f"Minimum income +{r}% (derived)"
            # self-check through the tool's formula
            units_m, hhs = hh_k / 1000, (pop / 1000) / hh_k
            for p, band in PROFILES.items():
                kk = len(band)
                u = sum(tool["deciles"][key][0][x] for x in band) * 10 / (kk * units_m * hhs)
                w1 = sum(tool["deciles"][key][2][x] for x in band) * 10 / (kk * units_m * hhs)
                assert abs(u - vals[p][r]["pbU_nac_2024"]) < 0.02 + 1e-4 * abs(u), (cc, p, r, u)
                assert abs(w1 - vals[p][r]["pbW_nac_2024"]["1"]) < 0.02 + 1e-4 * abs(w1), (cc, p, r, w1)
        alt = {"euromod_extstat_latest": euromod_outlay(cc, em), "spc_admin": spc_outlay(cc, recs),
               "national_other": None, "esspros": esspros_outlay(cc, extra),
               "jrc_euromod_x12": jrc_outlay(cc, recs), "recipients_x_rate": recip_outlay(cc, recs)}
        if cc in STEP2:
            r_ = recs[STEP2[cc][0]]
            alt["national_other"] = {"value_m": r_["value"] * STEP2[cc][1], "year": int(r_["reference_year"]),
                                     "source": r_["id"]}
        for key, a_ in alt.items():
            if a_:
                a_["over_recommended_2024"] = round(a_["value_m"] * defl(series, cc, a_["year"]) / O24, 3)
                a_["default_pbW_eps1_nac_2024_if_used"] = round(
                    vals["lowest"][25]["pbW_nac_2024"]["1"] * a_["over_recommended_2024"], 2)
        flags = ["derived (D5): outlay-based, not microsimulated; the provider can overwrite it",
                 "band shares and within-band gain pattern pooled from the ES, IT and EL EUROMOD surfaces",
                 "intensive margin only: +r% to existing payments, no new entrants (as the ES and EL dials)",
                 "actual take-up: the outlay is what the scheme pays now, not a full-take-up simulation"]
        if o["step"] == 2:
            flags.append("outlay exception to the EUROMOD statistic: " + o["why"])
        if cc == "IT":
            flags.append("outlay is a 2025 budget authorisation, not outturn")
        if cc == "PL":
            flags.append("main scheme = temporary benefit only (SPC); adding the permanent allowance "
                         "(EUROMOD bsapm_s, PLN 1,354m in 2024) would multiply the outlay by about 4")
        if cc == "ES":
            flags.append("EUROMOD 2024 IMV figure (2,840) vs the SPC's IMV payroll incl. CAPI (4,368): scope unresolved")
        c = {"currency": cur, "outlay": dict(o, currency="EUR" if cc == "BG" else cur,
                                             value_m_2024_prices=round(O24, 3),
                                             deflator_factor_to_2024=round(f, 5)),
             "population": {"value": pop, "series": f"demo_pjan geo={cc} time={yr} (1 January)"},
             "households_k": {"value": hh_k, "series": f"lfst_hhnhtych geo={cc} time={yr}"},
             "deflator": {"series": f"nama_10_gdp B1GQ PD15_NAC geo={cc}", "from_year": yr, "to_year": PRICE_BASE},
             "eur_rate_2024": {"value": rate, "series": ("ert_bil_eur_a AVG " + CURRENCY[cc] + " 2024") if cc in CURRENCY else "EUR"},
             "silc": {"year": silc["year"], "series": f"ilc_di01 TC/SHARE, ilc_di03 MED_EI/MEAN_EI geo={cc} time={silc['year']}",
                      "median": silc["median"], "decile_means": [round(x) for x in dmeans],
                      "weights_by_eps": {str(e): [round(x, 4) for x in W[e]] for e in EPS}},
             "use_in_tool": ("modelled (D5: the shipped EUROMOD surface stays; the derived value is the "
                             "positive control only)") if cc in MODELLED else "derived",
             "values": vals, "alternatives": alt, "grade": "national_derived", "flags": flags,
             "confidence": {"lowest": "outlay-limited (band share validated within about 5%)",
                            "all": "outlay-limited (no band share involved)",
                            "lowmid": "low: the borrowed D4-6 share varies 6-13% of the gain across ES, IT, EL"},
             "tool_block": tool}
        if cc in truth:
            t = truth[cc]
            d23 = defl(series, cc, 2023)
            c["modelled"] = {"note": "shipped EUROMOD values, 2023 money; also shown uprated to 2024",
                             "source": t["source"], "sha256": t["sha256"],
                             "values": {p: {r: {"pbU_2023": round(t["pbU"][p][r], 2),
                                                "pbU_2024": round(t["pbU"][p][r] * d23, 2),
                                                "pbW_2023": {str(e): round(t["pbW"][p][r][i], 2) for i, e in enumerate(EPS)},
                                                "kappa": [round(x, 4) for x in t["kappa"][p][r]]}
                                            for r in SIZES} for p in PROFILES}}
        countries[cc] = c

    # side-by-side for ES, IT, EL
    md.append("## 6. ES, IT, EL: modelled vs derived by the recommended rule (EUR per person per year)\n")
    md.append("Modelled at 2023 money and uprated to 2024; derived at 2024 prices (pooled shares, not leave-one-out).\n")
    md.append("| country | profile | size | modelled pbU 2023 | modelled pbU 2024 | derived pbU 2024 | modelled pbW eps1 2023 | derived pbW eps1 2024 | modelled kappa eps1 | derived kappa eps1 |")
    md.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for cc in MODELLED:
        c = countries[cc]
        for p in PROFILES:
            for r in SIZES:
                m, v = c["modelled"]["values"][p][r], c["values"][p][r]
                md.append(f"| {cc} | {p} | +{r}% | {m['pbU_2023']:.2f} | {m['pbU_2024']:.2f} | {v['pbU_nac_2024']:.2f} | "
                          f"{m['pbW_2023']['1']:.2f} | {v['pbW_nac_2024']['1']:.2f} | {m['kappa'][2]:.3f} | {v['kappa'][2]:.3f} |")
    md.append("")

    md.append("## 7. All 27 at the tool default (lowest incomes D1-3, eps 1, +25%), 2024 prices\n")
    md.append("| country | outlay (m, currency, year) | step | source | population (m) | pbU | pbU range (band share) | kappa eps1 | **pbW eps1** | pbW eps1 EUR |")
    md.append("|---|---:|---:|---|---:|---:|---|---:|---:|---:|")
    for cc in EU27:
        c = countries[cc]
        v = c["values"]["lowest"][25]
        o = c["outlay"]
        src = o["source"].replace("EUROMOD J2.0+ ", "EM ").replace(" ExternalStatistic Reference=", " ")
        md.append(f"| {cc} | {o['value_m']:,.1f} {o['currency']} ({o['year']}) | {o['step']} | {src[:48]} | "
                  f"{c['population']['value'] / 1e6:.2f} | {v['pbU_nac_2024']:,.2f} | "
                  f"{v['pbU_range_nac_2024'][0]:,.2f}-{v['pbU_range_nac_2024'][1]:,.2f} | {v['kappa'][2]:.3f} | "
                  f"**{v['pbW_nac_2024']['1']:,.2f}** | {v['pbW_eur_2024']['1']:,.2f} |")
    md.append("")
    md.append("## 8. Outlay cross-checks for all 27 (each alternative over the recommended outlay, 2024 prices)\n")
    md.append("| country | EUROMOD latest | SPC admin | national other | ESSPROS | JRC EUROMOD J1.28 x12 | JRC product/printed | recipients x rate |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for cc in EU27:
        a = countries[cc]["alternatives"]

        def r_(k):
            return a[k]["over_recommended_2024"] if a[k] else ""
        j = a["jrc_euromod_x12"]
        md.append(f"| {cc} | {r_('euromod_extstat_latest')} | {r_('spc_admin')} | {r_('national_other')} | {r_('esspros')} | "
                  f"{r_('jrc_euromod_x12')} | {round(j['product_over_printed'], 3) if j and j['product_over_printed'] else ''} | "
                  f"{r_('recipients_x_rate')} |")
    md.append("")
    ratios = {k: [countries[c]["alternatives"][k]["over_recommended_2024"] for c in EU27
                  if countries[c]["alternatives"][k] and countries[c]["outlay"]["step"] == 1]
              for k in ("spc_admin", "esspros", "jrc_euromod_x12", "recipients_x_rate")}
    md.append("Spread of each alternative over the recommended (step-1 countries only): " + "; ".join(
        f"{k}: n={len(v)}, min {min(v):.2f}, median {sorted(v)[len(v) // 2]:.2f}, max {max(v):.2f}, "
        f"within +/-20%: {sum(1 for x in v if 0.8 <= x <= 1.2)}" for k, v in ratios.items() if v) + "\n")

    result = {
        "meta": {
            "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "script": "evidence/extra_income/extra_income.py",
            "decision": "DECISIONS.md D5",
            "price_base": PRICE_BASE, "eps_grid": EPS, "sizes_pct": SIZES,
            "profiles": {p: {"label": PROFILE_LABEL[p], "deciles_zero_based": b} for p, b in PROFILES.items()},
            "formula": {
                "pbU": "(r/100) * O_2024 * S_band(r) / ((k/10) * P)",
                "kappa": "sum_{d in band} s_d(r) W_d(eps) / sum_{d in band} s_d(r); W_d = wevm.social_weight on Eurostat decile "
                         + ("means" if kchoice == "K1" else "cut-off spreads") + " with y_ref = median, floor = 0.6 x median",
                "pbW": "pbU * kappa",
                "tool": "tool_block.deciles reproduces pbU and pbW through the shipped calc() formula (asserted)"},
            "outlay_rule": "Step 1: EUROMOD J2.0+ <ExternalStatistic> amount for the country's main minimum-income "
                           "instrument (the scheme the SPC 2025 MI Report names), latest year up to 2024. Step 2, "
                           "named exceptions: " + "; ".join(f"{k}: {v}" for k, v in EM_EXCEPTION.items()) +
                           ". Uprated to 2024 on the GDP deflator (RULES.md G3).",
            "euromod_instruments": {cc: {"reference": em["countries"][cc]["reference"],
                                         "description": em["countries"][cc]["description"],
                                         "xml": em["countries"][cc]["xml"],
                                         "xml_sha256": em["countries"][cc]["xml_sha256"]} for cc in EU27},
            "euromod_read_from": em.get("read_from"),
            "kappa_method": kchoice,
            "pooled_shares": {str(r): [round(x, 6) for x in pool[r]] for r in SIZES},
            "band_share_range_across_ES_IT_EL": {str(r): {p: [round(x, 4) for x in band_range[r][p]] for p in PROFILES} for r in SIZES},
            "inputs": {k: {"path": repo_path(v), "sha256": sha256(v)} for k, v in
                       {"findings": FINDINGS, "sources": SOURCES, "series": SERIES, "benefit_adjustments": BENADJ,
                        "wevm_py": WEVM_PY, "eurostat_extra": EXTRA, "euromod_cache": EUROMOD_CACHE}.items()},
            "eurostat_extra_urls": extra["urls"], "eurostat_extra_pulled": extra["pulled"],
            "bgn_per_eur": BGN_PER_EUR,
        },
        "validation": {
            "outlay_candidates": cand,
            "pbU_errors_loo_2024prices": {n: {c: {p: {str(r): {k: round(v, 4) for k, v in x.items()} for r, x in dd.items()}
                                                  for p, dd in cv.items()} for c, cv in nv.items()} for n, nv in val_rows.items()},
            "mae_pct": {n: {"all_cells": round(100 * mae(n), 2), "lowest_and_all": round(100 * mae(n, ("lowest", "all")), 2),
                            "lowmid": round(100 * mae(n, ("lowmid",)), 2)} for n in cand_order},
            "identity_check_errors": ident,
            "decomposition_recommended_lowest_25": decomp,
            "kappa_mae_pct": {k: round(100 * kmae(k), 3) for k in kval},
            "kappa_errors": kval,
        },
        "countries": countries,
    }
    json.dump(result, open(OUT_JSON, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    header = ("# Extra income: generated tables\n\nWritten by `extra_income.py` on "
              f"{result['meta']['generated']}. Do not edit by hand; REPORT.md quotes these.\n\n")
    open(OUT_MD, "w", encoding="utf-8").write(header + "\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
