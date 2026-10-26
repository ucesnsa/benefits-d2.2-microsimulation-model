"""Country frame for the all-country provider tool: everything per country that is not a service
value. Currency, price levels, household counts, the WELLBY value, the VSL, the unemployment-shock
base. Every figure is a Eurostat series (pulled by API, stored with its code) or a stated constant
with its source. Writes frame/<CC>.json and frame/FRAME_CHECK.md (positive controls against the
shipped Spain, Italy and Greece values).

Run: py make_frame.py
"""
import io, json, os, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "frame")
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
EU27 = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "EL", "HU", "IE", "IT", "LV", "LT",
        "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"]
NAMES = {"AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia", "CY": "Cyprus", "CZ": "Czechia",
         "DK": "Denmark", "EE": "Estonia", "FI": "Finland", "FR": "France", "DE": "Germany", "EL": "Greece",
         "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LV": "Latvia", "LT": "Lithuania", "LU": "Luxembourg",
         "MT": "Malta", "NL": "Netherlands", "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SK": "Slovakia",
         "SI": "Slovenia", "ES": "Spain", "SE": "Sweden"}
# National currency in 2024, the tool's price base. Bulgaria's lev was pegged at 1.95583 per euro
# throughout; values are shown in euro at that rate (Bulgaria entered the euro area in 2026).
NONEURO = {"CZ": "CZK", "DK": "DKK", "HU": "HUF", "PL": "PLN", "RO": "RON", "SE": "SEK"}
BGN_PER_EUR = 1.95583
# HM Treasury Wellbeing Guidance for Appraisal (2021), p.33: GBP 13,000 per WELLBY at 2019 prices,
# low 10,000, high 16,000; applied at 2024 prices by HMT's footnote-102 method as 16,300 / 12,540 /
# 20,064 (the shipped tools' applied figures, Deliverable/europe/docs/PROVIDER_TOOLREADY_2024.md s.1).
SPINE_GBP_2024 = {"L": 12540.0, "C": 16300.0, "H": 20064.0}
# OECD (2025) Mortality Risk Valuation in Policy Assessment, Table 6.1: base VSL for the EU27,
# USD 8.4m (range 7.0-9.8), constant 2022 USD PPP, at EU population-weighted GDP per head;
# recommended income elasticity 1.0. OECD (2012) EU27 base USD 3.6m (2005 USD) as the low case.
VSL_EU_2025 = {"L": 7.0e6, "C": 8.4e6, "H": 9.8e6}
VSL_ELASTICITY = 1.0
# The UK unemployment-shock shares the shipped EU tools borrow (PROVIDER notes, shockInterp):
# share of working-age units whose employment income falls, at 3pp and 5pp.
UK_AFF_SHARE = {3: 0.02176418, 5: 0.03649125}


def get(path):
    url = EUROSTAT + path + "&format=JSON&lang=EN"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(req, timeout=180)), url


def table(path):
    """{geo: {time: value}} for a query with one free dimension besides geo and time."""
    d, url = get(path)
    dims, sizes = d["id"], d["size"]
    inv = {k: {i: v for v, i in d["dimension"][k]["category"]["index"].items()} for k in dims}
    out = {}
    for flat, val in d.get("value", {}).items():
        n, c = int(flat), {}
        for k, s in zip(reversed(dims), reversed(sizes)):
            c[k] = inv[k][n % s]
            n //= s
        out.setdefault(c["geo"], {})[c["time"]] = val
    return out, url


def latest(series, geo, upto=None):
    ys = sorted(y for y in series.get(geo, {}) if (upto is None or y <= str(upto)))
    return (ys[-1], series[geo][ys[-1]]) if ys else (None, None)


def main():
    os.makedirs(OUT, exist_ok=True)
    geos = "&".join("geo=" + g for g in EU27 + ["UK", "US", "EU27_2020"])
    S, U = {}, {}
    q = {
        "defl": "nama_10_gdp?na_item=B1GQ&unit=PD15_NAC&" + geos,
        "ppp_e011": "prc_ppp_ind?na_item=PPP_EU27_2020&ppp_cat=E011&" + geos,
        "ppp_gdp": "prc_ppp_ind?na_item=PPP_EU27_2020&ppp_cat=GDP&" + geos,
        "gdp_pps_hd": "nama_10_pc?na_item=B1GQ&unit=CP_PPS_EU27_2020_HAB&" + geos,
        "labour_q": "lc_lci_lev?nace_r2=Q&lcstruct=D1_D4_MD5&unit=EUR&" + geos,
        "hh": "lfst_hhnhtych?agechild=TOTAL&n_child=TOTAL&phhcomp=TOTAL&unit=THS_HH&" + geos,
        "pop": "demo_pjan?age=TOTAL&sex=T&unit=NR&" + geos,
    }
    for k, p in q.items():
        S[k], U[k] = table(p)
    # Share of POPULATION living in pensioner-type households (EU-SILC ilc_lvps02): one adult aged
    # 65+, and two adults at least one aged 65+ (no children). Each is converted to a share of
    # HOUSEHOLDS at one and two people per household. Working-age households are the rest: a lower
    # bound, since some two-adult households with one person aged 65+ have a working-age partner.
    # Checked against the shipped EU tools' own EU-SILC shares (ES 0.783, IT 0.659, EL 0.627).
    LCI_OS_FR, U["lci_os_fr"] = table("lc_lci_r2_a?unit=I20&lcstruct=D1_D4_MD5&nace_r2=O-S&geo=FR")
    LCI_OS_FR = LCI_OS_FR["FR"]
    PENS = {}
    for h in ("A1_GE65", "A2_GE1_GE65"):
        PENS[h], U["pens_" + h] = table("ilc_lvps02?rskpovth=TOTAL&unit=PC&hhcomp=" + h + "&" + geos)
    fx, U["fx"] = {}, None
    d, U["fx"] = get("ert_bil_eur_a?statinfo=AVG&time=2024&time=2022")
    inv = {k: {i: v for v, i in d["dimension"][k]["category"]["index"].items()} for k in d["id"]}
    for flat, val in d["value"].items():
        n, c = int(flat), {}
        for k, s in zip(reversed(d["id"]), reversed(d["size"])):
            c[k] = inv[k][n % s]
            n //= s
        fx.setdefault(c["currency"], {})[c["time"]] = val

    def defl(cc, frm, to=2024):
        s = S["defl"][cc]
        return s[str(to)] / s[str(frm)]

    ppp_uk = S["ppp_e011"]["UK"]["2024"]
    ppp_us22 = S["ppp_gdp"]["US"]["2022"]
    y_eu22 = S["gdp_pps_hd"]["EU27_2020"]["2022"]
    frames, check = {}, []
    for cc in EU27:
        cur = NONEURO.get(cc, "EUR")
        sym = "€" if cur == "EUR" else cur + " "
        ppp_c = S["ppp_e011"][cc]["2024"]
        if cc == "BG":           # Eurostat reports BGN; the tool shows euro at the fixed rate
            ppp_c = ppp_c / BGN_PER_EUR
        fac_uk = ppp_c / ppp_uk  # national currency per GBP, household-consumption PPP 2024
        spine = {k: v * fac_uk for k, v in SPINE_GBP_2024.items()}
        # VSL: OECD base x (GDP per head PPS / EU) ^ 1.0, USD PPP 2022 -> national currency 2022
        # (GDP PPP ratio to the US), then 2022 -> 2024 on the national GDP deflator.
        y_ratio = S["gdp_pps_hd"][cc]["2022"] / y_eu22
        nac_per_usd_ppp = S["ppp_gdp"][cc]["2022"] / ppp_us22
        if cc == "BG":
            nac_per_usd_ppp = nac_per_usd_ppp / BGN_PER_EUR
        up = defl(cc, 2022)
        vsl = {k: v * (y_ratio ** VSL_ELASTICITY) * nac_per_usd_ppp * up for k, v in VSL_EU_2025.items()}
        # Labour cost per hour in health and social work, 2023 (the year the shipped tools use).
        # France's NACE Q level stops at 2020 and its NACE Q index is empty, so the 2020 level is
        # carried to 2023 on the nearest published index, O-S (lc_lci_r2_a, I20, D1_D4_MD5).
        ly, lab = latest(S["labour_q"], cc, 2023)
        lab_note = "Eurostat lc_lci_lev, NACE Q, D1_D4_MD5, %s" % ly
        if ly != "2023":
            assert cc == "FR", "labour cost for %s stops at %s" % (cc, ly)
            ix = LCI_OS_FR
            lab = lab * ix["2023"] / ix[ly]
            lab_note += ", carried to 2023 on the O-S labour cost index (x%.4f)" % (ix["2023"] / ix[ly])
            ly = "2023"
        hy, hh = latest(S["hh"], cc, 2024)
        py_, pop = latest(S["pop"], cc, 2024)
        wy, a1 = latest(PENS["A1_GE65"], cc, 2024)
        _, a2 = latest(PENS["A2_GE1_GE65"], cc, int(wy) if wy else 2024)
        wa_share = (1 - (a1 / 100.0) * pop / (hh * 1000.0) - (a2 / 100.0) * pop / 2.0 / (hh * 1000.0)) if (a1 is not None and a2 is not None and hh) else None
        hhwa = hh * wa_share if wa_share else None
        base_wa = hh * wa_share if wa_share else None
        frames[cc] = {
            "code": cc, "name": NAMES[cc], "currency": {"code": cur, "symbol": sym}, "locale": "en-GB",
            "ppp_e011_2024": S["ppp_e011"][cc]["2024"], "ppp_factor_per_gbp": fac_uk,
            "spine": spine, "vsl": vsl, "vsl_inputs": {"gdp_pps_head_ratio_2022": y_ratio,
                                                      "nac_per_usd_ppp_2022": nac_per_usd_ppp, "deflator_2022_2024": up},
            "labour_cost_naceQ": {"year": ly, "eur_per_hour": lab, "note": lab_note},
            "households_k": {"year": hy, "value": hh}, "population": {"year": py_, "value": pop},
            "hh_size": (pop / 1000.0) / hh if (pop and hh) else None,
            "working_age_households_k": {"year": wy, "value": hhwa, "share": wa_share,
                                         "pensioner_pop_pct": {"A1_GE65": a1, "A2_GE1_GE65": a2}},
            "shock_aff_k": ({3: base_wa * UK_AFF_SHARE[3], 5: base_wa * UK_AFF_SHARE[5]} if base_wa else None),
            "deflator_2015eq100": S["defl"][cc],
            "fx_nac_per_eur": (fx.get(cur, {}) if cur != "EUR" else {"2024": 1.0, "2022": 1.0}),
        }
    meta = {"pulled": datetime.date.today().isoformat(), "urls": U, "ppp_uk_e011_2024": ppp_uk,
            "ppp_us_gdp_2022": ppp_us22, "eu_gdp_pps_head_2022": y_eu22, "gbp_per_eur_2024": fx["GBP"]["2024"]}
    for cc, f in frames.items():
        json.dump({"frame": f, "meta": meta}, io.open(os.path.join(OUT, cc + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    # Positive controls against the shipped EU tools.
    shipped = {"ES": {"spine": 14050, "wa": 0.7832846446, "hh": 2.498571, "units_k": 19316.723},
               "IT": {"spine": 14925, "wa": 0.6587291601, "hh": 2.238543, "units_k": 26206.558},
               "EL": {"spine": 13317, "wa": 0.6267113451, "hh": 2.370350, "units_k": 4298.067}}
    lines = ["# Frame check against the shipped EU tools\n", "| country | quantity | shipped | frame | ratio |", "|---|---|---|---|---|"]
    for cc, s in shipped.items():
        f = frames[cc]
        lines.append("| %s | WELLBY value (central) | %s | %.0f | %.4f |" % (cc, s["spine"], f["spine"]["C"], f["spine"]["C"] / s["spine"]))
        lines.append("| %s | household size | %.4f | %.4f | %.4f |" % (cc, s["hh"], f["hh_size"], f["hh_size"] / s["hh"]))
        lines.append("| %s | households (k) | %.0f | %.0f | %.4f |" % (cc, s["units_k"], f["households_k"]["value"], f["households_k"]["value"] / s["units_k"]))
        if "wa" in s and f["working_age_households_k"]["share"]:
            lines.append("| %s | working-age household share | %.4f | %.4f | %.4f |" % (cc, s["wa"], f["working_age_households_k"]["share"], f["working_age_households_k"]["share"] / s["wa"]))
    lines.append("\n## Every country\n")
    lines.append("| cc | currency | spine C | VSL C (m) | labour cost (yr) | households k (yr) | hh size | working-age share | aff5 k |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for cc in EU27:
        f = frames[cc]
        wa = f["working_age_households_k"]["share"]
        lines.append("| %s | %s | %.0f | %.2f | %s (%s) | %.0f (%s) | %.3f | %s | %s |" % (
            cc, f["currency"]["code"], f["spine"]["C"], f["vsl"]["C"] / 1e6, f["labour_cost_naceQ"]["eur_per_hour"],
            f["labour_cost_naceQ"]["year"], f["households_k"]["value"], f["households_k"]["year"], f["hh_size"],
            ("%.3f" % wa) if wa else "n/a", ("%.1f" % f["shock_aff_k"][5]) if f["shock_aff_k"] else "n/a"))
    io.open(os.path.join(OUT, "FRAME_CHECK.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
