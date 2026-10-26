"""Pull every Eurostat series the all-country provider tool needs, for all 51 countries.

Writes eurostat_series.json (raw values by series, country, year) and COVERAGE.md (which
country has which series, latest year). Values are stored exactly as Eurostat returns them;
nothing is converted here. Run: py pull_eurostat.py
"""
import json, time, urllib.request, datetime

EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
EU27 = "AT BE BG HR CY CZ DK EE FI FR DE EL HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split()
ASSOC = "AL AM BA CA EG FO GE IS IL JP XK MD ME NZ MK NO KR RS CH TN TR UA UK".split()
TRANSITIONAL = ["MA"]
COUNTRIES = EU27 + ASSOC + TRANSITIONAL

SERIES = {
    "gdp_deflator_2015eq100": "nama_10_gdp?na_item=B1GQ&unit=PD15_NAC",
    "hfce_ppp_nac_per_pps": "prc_ppp_ind?na_item=PPP_EU27_2020&ppp_cat=E011",
    "labour_cost_eur_per_hour_naceQ": "lc_lci_lev?nace_r2=Q&lcstruct=D1_D4_MD5&unit=EUR",
    "avg_household_size": "ilc_lvph01?unit=AVG",
    "households_thousands": "lfst_hhnhtych?agechild=TOTAL&n_child=TOTAL&phhcomp=TOTAL&unit=THS_HH",
    "population_1jan": "demo_pjan?age=TOTAL&sex=T&unit=NR",
    "mean_equiv_income_nac": "ilc_di03?age=TOTAL&sex=T&statinfo=MEAN_EI&unit=NAC",
    "median_equiv_income_nac": "ilc_di03?age=TOTAL&sex=T&statinfo=MED_EI&unit=NAC",
    "decile_top_cutoff_nac": "ilc_di01?statinfo=TC&unit=NAC",
    "decile_share_pct": "ilc_di01?statinfo=SHARE&unit=NAC",  # share of national equivalised income, percent; unit dimension is nominal for SHARE
}
QUANT = ["D%d" % i for i in range(1, 11)]


def get(path):
    url = EUROSTAT + path + ("&" if "?" in path else "?") + "format=JSON&lang=EN"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.load(urllib.request.urlopen(req, timeout=180)), url
        except Exception as e:
            err = e
            time.sleep(3 * (attempt + 1))
    raise err


def unpack(d):
    """Return {(dim values...): value} keyed by the dimensions that vary."""
    dims = d["id"]
    sizes = d["size"]
    idx = {k: {v: i for v, i in d["dimension"][k]["category"]["index"].items()} for k in dims}
    inv = {k: {i: v for v, i in idx[k].items()} for k in dims}
    out = {}
    for flat, val in d.get("value", {}).items():
        n = int(flat)
        coords = []
        for k, s in zip(reversed(dims), reversed(sizes)):
            coords.append(inv[k][n % s])
            n //= s
        coords = dict(zip(reversed(dims), coords))
        out[tuple(sorted(coords.items()))] = val
    return out


def main():
    result = {"pulled": datetime.date.today().isoformat(), "source": EUROSTAT, "series": {}, "urls": {}}
    for name, path in SERIES.items():
        d, url = get(path)
        result["urls"][name] = url
        rows = unpack(d)
        bycc = {}
        for coords, val in rows.items():
            c = dict(coords)
            geo = c.get("geo")
            if geo not in COUNTRIES:
                continue
            key = c["time"] if "quant_inc" not in c else c["time"] + "|" + c["quant_inc"]
            if "quant_inc" in c and c["quant_inc"] not in QUANT:
                continue
            bycc.setdefault(geo, {})[key] = val
        result["series"][name] = bycc
        print(name, "countries:", len(bycc))
    # Exchange rates: national currency per EUR, annual average, keyed by currency not geo.
    d, url = get("ert_bil_eur_a?statinfo=AVG")
    result["urls"]["eur_exchange_rate_avg"] = url
    fx = {}
    for coords, val in unpack(d).items():
        c = dict(coords)
        fx.setdefault(c["currency"], {})[c["time"]] = val
    result["series"]["eur_exchange_rate_avg"] = fx
    print("exchange rates: currencies", len(fx))
    json.dump(result, open("eurostat_series.json", "w", encoding="utf-8"), indent=1, sort_keys=True)

    lines = ["# Eurostat coverage for the all-country provider tool\n",
             f"Pulled {result['pulled']} by `pull_eurostat.py`. Cell = latest year available; blank = not in Eurostat.\n",
             "| country | " + " | ".join(SERIES) + " |", "|---|" + "---|" * len(SERIES)]
    for cc in COUNTRIES:
        cells = []
        for name in SERIES:
            v = result["series"][name].get(cc, {})
            years = sorted({k.split("|")[0] for k in v})
            cells.append(years[-1] if years else "")
        lines.append(f"| {cc} | " + " | ".join(cells) + " |")
    open("COVERAGE.md", "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
