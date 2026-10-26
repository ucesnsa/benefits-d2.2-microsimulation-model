"""Country blocks for the all-country provider tool: one data/<CC>.json per EU member state.

Every value follows a rule in ../DECISIONS.md and ../evidence/RULES.md and rests on a research
record that passed verification (../evidence/verify/*.jsonl). A national record is used only if
its verdict is PASS (or a MEANING_MISMATCH this script handles explicitly, as noted). Otherwise the
rule's fallback applies, which is the shipped method: a UK figure converted on the country's
labour cost (unit costs) or household-consumption PPP (outcome values).

Spain, Italy and Greece start from their shipped blocks, which keep their modelled income effect
(EUROMOD decile surfaces). The other 24 are built fresh, with the income effect derived
(../evidence/extra_income/). Every country gets the same service list, the same rules and the same
English money format.

Run: py make_data.py   ->  data/<CC>.json and data/DATA_REPORT.md
"""
import io, json, glob, os, re, copy, collections, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import ROOT, DELIV  # noqa: E402
OUTD = os.path.join(HERE, "data")
EU27 = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "EL", "HU", "IE", "IT", "LV", "LT",
        "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"]
MODELLED = {"ES": "es", "IT": "it", "EL": "el"}
BGN_PER_EUR, HRK_PER_EUR = 1.95583, 7.53450
UK_LABOUR_GBP_PER_HOUR = 30.2165   # shipped UK denominator (PROVIDER notes: lc_lci_lev 2016 + ASHE uprate)

# ---------------------------------------------------------------------------------------------
# Loaders
RECS = {}
for f in glob.glob(os.path.join(ROOT, "research", "*", "findings.jsonl")):
    if "uc_assoc" in f:
        continue
    for line in io.open(f, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            RECS[r["id"]] = r
VERD = {}
for f in glob.glob(os.path.join(ROOT, "evidence", "verify", "*.jsonl")):
    for line in io.open(f, encoding="utf-8"):
        if line.strip():
            v = json.loads(line)
            VERD[v["id"]] = v
FRAME = {cc: json.load(io.open(os.path.join(HERE, "frame", cc + ".json"), encoding="utf-8"))["frame"] for cc in EU27}
L8GG = json.load(io.open(os.path.join(HERE, "frame", "uk_l8gg.json"), encoding="utf-8"))["quarters"]
FEANTSA = json.load(io.open(os.path.join(ROOT, "evidence", "tables", "feantsa_2013_table52.json"), encoding="utf-8"))


USED = set()
# Records the outcome rules rest on by text (their notes name the study, not the id).
OUTCOME_IDS = ["svc_income-073", "svc_income-091", "svc_income-092", "svc_income-101", "svc_income-102",
               "svc_health2-023", "svc_health-007", "svc_health2-030", "svc_health-079", "svc_care-069", "svc_care-070",
               "svc_care-086", "svc_care-087", "svc_care2-017", "svc_care-115", "svc_care2-046", "svc_care-152",
               "svc_care-031", "svc_care-156", "svc_health2-012", "svc_health2-013", "svc_health-017",
               "country_valuation-004", "country_valuation-006", "svc_income-085", "svc_income-086", "svc_income-139",
               "svc_income-148", "svc_income-150", "svc_health2-037"] + ["svc_care2-%03d" % i for i in range(19, 29)]


def verdict(rid):
    return (VERD.get(rid) or {}).get("verdict")


# Figures a verifier recomputed from the source when the record was wrong (evidence/verify, V3):
# (value, currency, price year, what was wrong). A corrected record counts as verified.
CORRECTED = {
    "uc2_west-004": (684974, "SEK", 2024, "the record divided by the girls-only placement rate; recomputed on the total rate (Kolada N33022 / N33817 total)"),
    "uc2_west-015": (68901, "EUR", 2024, "the record divided two rates on different population bases; recomputed from the published absolute values (EUR 1,188,684 thousand / 17,252 children, Sotkanet)"),
    "uc_west-020": (21630, "EUR", 2019, "the central figure included after-care allowances for care leavers aged 18+; the record's own low figure excludes them"),
}


def ok(rid):
    return verdict(rid) == "PASS" or rid in CORRECTED


def cite(rid):
    USED.add(rid)
    s = RECS[rid]["source"]
    a = (s.get("authors") or "").split(";")[0].strip()
    return "%s (%s), %s" % (a, s.get("year"), (s.get("title") or "").strip().rstrip("."))


def uk_fy(y):
    """ONS L8GG financial-year index for FY y/y+1: the mean of Q2-Q4 of y and Q1 of y+1."""
    q = L8GG
    return (float(q["%d Q2" % y]) + float(q["%d Q3" % y]) + float(q["%d Q4" % y]) + float(q["%d Q1" % (y + 1)])) / 4


CLAMPED = set()


def defl(cc, year, to=2024):
    """GDP deflator ratio to 2024. A price year after the last published deflator year is taken
    at that last year (recorded in CLAMPED and stated in the value's note)."""
    s = FRAME[cc]["deflator_2015eq100"]
    y = str(year)
    if y not in s:
        last = max(k for k in s if k <= y) if any(k <= y for k in s) else None
        assert last is not None, (cc, year)
        CLAMPED.add((cc, int(year), int(last)))
        y = last
    return s[str(to)] / s[y]


def to_nac_2024(cc, value, currency, year):
    """A national figure in its own currency and price year -> the tool's currency at 2024 prices."""
    if currency == "BGN":
        value = value / BGN_PER_EUR
    if currency == "HRK":
        value = value / HRK_PER_EUR
    return value * defl(cc, int(year))


def labour_factor(cc):
    """Tool currency per GBP of staff time: the shipped conversion (country labour cost per hour
    in health and social work, 2023, over the UK's GBP 30.2165)."""
    f = FRAME[cc]
    eur = f["labour_cost_naceQ"]["eur_per_hour"]
    nac_per_eur = 1.0 if f["currency"]["code"] == "EUR" else f["fx_nac_per_eur"]["2024"]
    return eur * nac_per_eur / UK_LABOUR_GBP_PER_HOUR


# Spain, Italy and Greece keep the PPP factors the shipped tools use (OECD household-consumption
# PPP, UK to country, 2024; PROVIDER_TOOLREADY_2024.md s.1), so their WELLBY value and every PPP
# transfer equal the shipped ones. The other 24 use Eurostat prc_ppp_ind E011 (within 1% of OECD).
SHIPPED_PPP = {"ES": 0.861941, "IT": 0.915660, "EL": 0.816996}


def ppp_factor(cc):
    return SHIPPED_PPP.get(cc, FRAME[cc]["ppp_factor_per_gbp"])


def ppp_source(cc):
    """The parity a UK-to-country note names: the one ppp_factor() actually applied."""
    if cc in SHIPPED_PPP:
        return ("household-consumption PPP (OECD, 2024, the factor of %.6f per GBP the %s tool uses for every transfer from "
                "the UK)" % (SHIPPED_PPP[cc], FRAME[cc]["name"]))
    return "household-consumption PPP (Eurostat, 2024)"


# ---------------------------------------------------------------------------------------------
# Services, units and UK anchors (GBP at 2024-25 prices, as the shipped tools carry them)
SERVICES = ["Employment support", "Minimum income casework", "Food aid / food banks", "Debt advice",
            "Talking therapies", "Housing / homelessness", "Children's social care", "Domestic abuse / GBV",
            "Drug & alcohol treatment", "GP consultation", "Opioid substitution treatment (OST)"]
SCHEME = {"AT": "Sozialhilfe", "BE": "revenu d'intégration / leefloon", "BG": "social assistance", "CY": "GMI",
          "CZ": "příspěvek na živobytí", "DE": "Bürgergeld", "DK": "kontanthjælp", "EE": "toimetulekutoetus",
          "EL": "KEA", "ES": "IMV", "FI": "toimeentulotuki", "FR": "RSA", "HR": "zajamčena minimalna naknada",
          "HU": "FHT", "IE": "SWA", "IT": "AdI", "LT": "socialinė pašalpa", "LU": "REVIS", "LV": "GMI",
          "MT": "Social Assistance", "NL": "bijstand", "PL": "zasiłek okresowy", "PT": "RSI", "RO": "VMI",
          "SE": "ekonomiskt bistånd", "SI": "denarna socialna pomoč", "SK": "pomoc v hmotnej núdzi"}
UNIT = {"Employment support": "one participant in an employment-support episode",
        "Minimum income casework": "one claim supported",
        "Food aid / food banks": "one recipient for a year",
        "Debt advice": "one advice case",
        "Talking therapies": "one course of treatment",
        "Housing / homelessness": "one homeless person supported for a year",
        "Children's social care": "one child supported at home for a year",
        "Domestic abuse / GBV": "one victim supported",
        "Drug & alcohol treatment": "one client for a treatment year",
        "GP consultation": "one consultation",
        "Opioid substitution treatment (OST)": "one patient for a year"}
UK_COST = {  # GBP, 2024-25 prices, with the statement of where it comes from
    "Employment support": (1200, "the UK tool's unit cost for Jobcentre Plus work coaching, GBP 1,200 per participant, itself an assumption declared at the 2024 base"),
    "Minimum income casework": (400, "the UK tool's unit cost for benefit claim support, GBP 400 per claim, itself an assumption declared at the 2024 base"),
    "Food aid / food banks": (150, "the UK tool's unit cost for food banks, GBP 150 per recipient, itself an assumption declared at the 2024 base"),
    "Debt advice": (500, "the UK tool's unit cost for debt advice, GBP 500 per case, itself an assumption declared at the 2024 base"),
    "Talking therapies": (1200, "the UK tool's unit cost for NHS Talking Therapies, GBP 1,200 per course, itself an assumption declared at the 2024 base"),
    "Housing / homelessness": (None, "uc_west-003"),
    "Children's social care": (10965, "Home Office (2021) GBP 8,640 per child in need per year at 2018/19 prices, uprated to GBP 10,965 (the UK tool's figure)"),
    "Domestic abuse / GBV": (2500, "the UK tool's unit cost for domestic abuse services, GBP 2,500 per case, itself an assumption declared at the 2024 base"),
    "Drug & alcohol treatment": (4488, "National Audit Office (2010) GBP 3,000 per person in effective drug treatment at 2008-09 prices, uprated to GBP 4,488 (the UK tool's figure)"),
    "GP consultation": (53.6695, "Jones et al. (2024) Unit Costs of Health and Social Care, GBP 49 per ten-minute surgery consultation at 2022/23 prices, uprated to GBP 53.67 (the UK tool's price)"),
    "Opioid substitution treatment (OST)": (None, "uc_west-008"),
}
ELAST = {  # low, central, high; source
    "Employment support": ((0.8, 1.0, 1.2), "borrowed_unadjusted", "UK register value for Jobcentre Plus work coaches (demand moves one-for-one with unemployment, range 0.8 to 1.2), transferred unadjusted"),
    "Minimum income casework": ((0.3, 0.55, 1.0), "borrowed_adjusted", "US SNAP evidence: enrolment rises about 6% in the year per percentage point of unemployment and 11 to 20% over three years, which at an unemployment rate near 5% is 0.3 in the first year and 0.55 to 1.0 cumulatively (svc_income-085); Spanish regional minimum-income exits slow by 0.6 points per point of unemployment (svc_income-086)"),
    "Food aid / food banks": ((0.1, 0.25, 0.5), "borrowed_adjusted", "Sosenko et al. (2022), 325 English local authorities: one point of unemployment adds about 2% to food-parcel use; Loopstra et al. (2016), 21 EU countries: one point adds 0.29 points to food insecurity (svc_income-150, -139). Crises cause separate surges of 30 to 100%"),
    "Debt advice": ((0.5, 0.8, 1.2), "borrowed_unadjusted", "UK register value for debt advice, transferred unadjusted; no European elasticity was found"),
    "Talking therapies": ((0.3, 0.6, 0.9), "borrowed_unadjusted", "UK register value for NHS Talking Therapies, transferred unadjusted"),
    "Housing / homelessness": ((0.3, 0.5, 0.8), "borrowed_unadjusted", "UK register value, transferred unadjusted; Dutch and Danish series do not support a stable relationship with unemployment"),
    "Children's social care": ((0.15, 0.3, 0.5), "borrowed_unadjusted", "UK register value, transferred unadjusted; a systematic review (Hiilamo et al. 2021) found no European population-level recession effect"),
    "Domestic abuse / GBV": ((0.2, 0.4, 0.6), "borrowed_unadjusted", "UK register value, transferred unadjusted"),
    "Drug & alcohol treatment": ((0.15, 0.3, 0.5), "borrowed_unadjusted", "UK register value, transferred unadjusted"),
    "GP consultation": ((0.2, 0.25, 0.3), "borrowed_adjusted", "Buffel et al. (2015), 27 EU countries: the odds of consulting a GP for a mental-health problem rise 2 to 3% per point of unemployment (svc_health2-037); a contact measure, not a consultation count"),
    "Opioid substitution treatment (OST)": ((0.15, 0.3, 0.5), "borrowed_unadjusted", "UK register value, transferred unadjusted"),
}
STAFF = {"Employment support": 120, "Minimum income casework": 200, "Food aid / food banks": 250, "Debt advice": 100,
         "Talking therapies": 50, "Housing / homelessness": 30, "Children's social care": 15, "Domestic abuse / GBV": 25,
         "Drug & alcohol treatment": 30, "GP consultation": 300, "Opioid substitution treatment (OST)": 30}


# ---------------------------------------------------------------------------------------------
# National unit costs, converted to each service's unit. (record id, multiplier to the unit,
# words for the conversion). Used only if the record's verdict is PASS.
SESS = {"BE": 6, "FR": 12.1, "ES": 7}   # sessions per course where a national figure states one
DEF_SESS = 7                           # UK NHS Talking Therapies GBP 1,200 / GBP 169 per contact
NATIONAL_COST = {
    "GP consultation": {
        "BE": ("uc2_west-036", 1, "per consultation"), "BG": ("uc2_southeast-019", 1, "per visit"),
        "DK": ("uc2_west-027", 1, "fee per daytime consultation (capitation paid separately)"),
        "ES": ("uc_southeast-021", 1, "per consultation"),
        "FI": ("uc2_west-012", 1, "full-cost regional price per doctor visit"), "FR": ("uc2_west-022", 1, "national tariff per consultation"),
        "IE": ("uc_west-022", 1, "price paid per private consultation"), "LU": ("uc2_west-038", 1, "national tariff per consultation"),
        "NL": ("uc_west-012", 1, "average per consultation"), "PT": ("uc2_southeast-001", 1, "per subsequent consultation"),
        "RO": ("uc2_southeast-017", 1, "fee per consultation"), "SE": ("uc2_west-006", 1, "inter-regional price per doctor visit")},
    "Talking therapies": {
        "BE": ("uc2_west-037", SESS["BE"], "session fee x 6 sessions (the mean course in the INAMI evaluation)"),
        "DK": ("uc2_west-045", DEF_SESS, "session fee x 7 sessions"), "EE": ("uc2_southeast-002", DEF_SESS, "session fee x 7 sessions"),
        "ES": ("uc_southeast-022", SESS["ES"], "session price x 7 sessions (the PsicAP course)"),
        "FI": ("uc2_west-013", DEF_SESS, "price per psychologist visit x 7"), "FR": ("uc2_west-023", SESS["FR"], "session fee x 12.1 sessions (the course costed for the reimbursement programme)"),
        "HR": ("uc2_southeast-012", DEF_SESS, "session tariff x 7"), "IT": ("uc2_southeast-020", DEF_SESS, "SSN session tariff x 7"),
        "LU": ("uc2_west-039", DEF_SESS, "session tariff x 7"), "LV": ("uc2_southeast-009", DEF_SESS, "consultation tariff x 7"),
        "NL": ("uc_west-013", DEF_SESS, "price per contact x 7"), "PT": ("uc_southeast-038", DEF_SESS, "SNS session price x 7"),
        "RO": ("uc2_southeast-018", DEF_SESS, "session tariff x 7"), "SE": ("uc2_west-007", DEF_SESS, "price per visit x 7")},
    "Housing / homelessness": {
        "FR": ("svc_care-079", 1, "Housing First cost per person-year"), "NL": ("svc_care2-039", 1, "Housing First cost per client-year"),
        "IT": ("svc_care2-034", 365, "daily Housing First cost x 365"), "ES": ("svc_care-089", 365, "daily Housing First cost x 365"),
        "DK": ("svc_care2-010", 1, "intensive case management per person-year"), "FI": ("uc2_west-046", 1, "housing services per client-year"),
        "CZ": ("svc_care2-003", 1, "Housing First social work per family-year")},
    "Children's social care": {
        "FR": ("uc2_west-025", 1, "in-home educational support per beneficiary-year"), "AT": ("uc2_west-034", 1, "in-home support per child-year"),
        "PT": ("svc_care2-054", 12, "family-preservation grant per family-month x 12"), "NL": ("svc_care-122", 1, "supervision order per child-year")},
    "Domestic abuse / GBV": {"DE": ("svc_care-126", 1, "specialist counselling per woman per year")},
    "Drug & alcohol treatment": {
        "DK": ("uc2_west-031", 1, "municipal drug treatment per person-year"), "FR": ("uc2_west-026", 1, "outpatient addiction centre per patient-year (Occitanie)"),
        "HU": ("uc_southeast-025", 1, "community addiction care support per client-year")},
    "Opioid substitution treatment (OST)": {
        "FI": ("uc2_west-010", 1, "per OST patient treated in the year"), "LT": ("uc_southeast-037", 1, "per patient-year, methadone maintenance")},
    "Debt advice": {"FI": ("uc2_west-041", 1, "per debt counselling case"), "IE": ("uc_west-024", 1, "grant cost per new client"),
                    "AT": ("svc_income-107", 1 / 61221.0, "public funding of state-recognised debt advice, EUR 24m, over the 61,221 people supported in the year")},
    "Food aid / food banks": {
        "ES": ("uc_southeast-009", 1, "per person supported per year (FEAD)"), "PT": ("uc_southeast-008", 1, "per person supported per year (FEAD)"),
        "CY": ("uc_southeast-007", 1, "per person supported per year (FEAD)"), "IT": ("uc_southeast-030", 1, "municipal distribution per user-year"),
        "NL": ("uc_west-018", 1, "food-bank cash spend per person helped per year")},
}
# Out-of-home care per child-year: the cost a placement avoided saves (children's social care outcome).
PLACEMENT = {
    "AT": ("uc2_west-033", 1), "DE": ("uc2_west-020", 1), "DK": ("uc2_west-029", 1), "FI": ("uc2_west-015", 1),
    "FR": ("uc2_west-024", 1), "IE": ("uc_west-020", 1), "IT": ("uc_southeast-032", 1), "LT": ("uc2_southeast-035", 1),
    "PL": ("uc2_southeast-015", 12), "PT": ("uc2_southeast-028", 12), "RO": ("uc_southeast-001", 1), "SE": ("uc2_west-004", 1),
    "SK": ("uc2_southeast-006", 1), "CZ": ("uc2_southeast-004", 1), "BG": ("uc_southeast-005", 1), "CY": ("uc2_southeast-039", 1),
    "ES": ("uc2_southeast-029", 365), "HU": ("uc2_southeast-021", 1),
}
UK_PLACEMENT = "uc_west-005"   # GBP per looked-after child per year


def rec_money(rid):
    USED.add(rid)
    if rid in CORRECTED:
        v, cur, yr, _ = CORRECTED[rid]
        return float(v), cur, yr
    r = RECS[rid]
    cur = (r.get("currency") or "").upper()
    cur = "EUR" if cur.startswith("EUR") else cur
    yr = r.get("price_year") or r.get("reference_year")
    return float(r["value"]), cur, yr


ES_OST_2024 = 2100.0
ES_OST_NOTE = ("a Spanish national figure: methadone at EUR 4 a day excluding medication, a 2004 observation, "
               "annualised on 365 days and uprated by 1.438347 to EUR 5.75 a day, EUR 2,098.75 a year, recorded "
               "as EUR 2,100 (the D2.2 Spain tool's figure; PROVIDER_TOOLREADY_2024.md, drug and alcohol table)")
IT_GP_2024 = 17.64
IT_GP_NOTE = ("an Italian national figure: about EUR 12 per ambulatory GP visit at 2003 prices (Garattini et al. "
              "2003, DYSCO, Farmeconomia 4(2):109-114), uprated by 1.470047 on Italy's GDP deflator to EUR 17.64 "
              "(PROVIDER_TOOLREADY_2024.md, GP table)")


def conv(cur, origin, factor):
    """The machine-readable clause a unit-cost note ends on: the figure the note starts from and the
    single factor that turns it into the tool's value. audit_provider_params.py (7.10c) recomputes
    every unit cost from it, and a note without one fails there."""
    return "CONVERSION: %s %s x %s." % (cur, repr(round(origin, 6)), "%.8f" % factor)


def unit_cost(cc, svc):
    """(value in the tool's currency at 2024 prices, grade, note)."""
    f = FRAME[cc]
    nac = 1.0 if f["currency"]["code"] == "EUR" else f["fx_nac_per_eur"]["2024"]
    if svc.startswith("Opioid") and cc == "ES":
        return ES_OST_2024, "national_source", "EUR 2,100 per patient-year, %s. %s PRICE BASE: 2024-equivalent." % (
            ES_OST_NOTE, conv("EUR", 4 * 365, 1.438347))
    if svc == "GP consultation" and cc == "IT":
        return IT_GP_2024, "national_source", "EUR 17.64 per consultation, %s. %s PRICE BASE: 2024-equivalent." % (
            IT_GP_NOTE, conv("EUR", 12, 1.470047))
    if svc == "GP consultation" and cc == "EL":
        es, _, _ = unit_cost("ES", svc)
        r = f["labour_cost_naceQ"]["eur_per_hour"] / FRAME["ES"]["labour_cost_naceQ"]["eur_per_hour"]
        return es * r, "borrowed_adjusted", ("EUR %s per consultation, the Spanish national price per GP consultation "
                                            "(EUR %s, a 2025 public price) scaled by the ratio of labour costs in health and "
                                            "social work, Greece to Spain, %.6f (Eurostat lc_lci_lev, NACE Q, 2023), as the "
                                            "D2.2 Greece tool borrows its GP cost from Spain. The EOPYY fee of EUR 10 to 13 a "
                                            "visit is paid to contracted specialists, not GPs. %s PRICE BASE: 2024-equivalent."
                                            % ("{:,.2f}".format(es * r), "{:,.2f}".format(es), r, conv("EUR", es, r)))
    ch = NATIONAL_COST.get(svc, {}).get(cc)
    if svc.startswith("Opioid") and not (ch and ok(ch[0])):
        r = f["labour_cost_naceQ"]["eur_per_hour"] / FRAME["ES"]["labour_cost_naceQ"]["eur_per_hour"]
        v = ES_OST_2024 * r * nac
        return v, "borrowed_adjusted", ("%s %s per patient-year, the Spanish national figure of EUR 2,100 (%s) scaled by "
                                        "the ratio of labour costs in health and social work, %s to Spain, %.6f (Eurostat "
                                        "lc_lci_lev, NACE Q, 2023), as the D2.2 Italy and Greece tools do. %s PRICE BASE: "
                                        "2024-equivalent." % (f["currency"]["code"], "{:,.0f}".format(v), ES_OST_NOTE, f["name"], r,
                                                              conv("EUR", ES_OST_2024, r * nac)))
    if ch and ok(ch[0]):
        v, cur, yr = rec_money(ch[0])
        if yr is None:
            yr = 2024
        val = to_nac_2024(cc, v * ch[1], cur, yr)
        lastd = max(FRAME[cc]["deflator_2015eq100"])
        yrtxt = ("%s (taken at %s prices, the last published deflator year)" % (yr, lastd)) if str(yr) > lastd else str(yr)
        note = ("%s %s: %s %s (%s), %s; brought from %s to 2024 on %s's GDP deflator (Eurostat nama_10_gdp). "
                "%s PRICE BASE: 2024-equivalent." % (FRAME[cc]["currency"]["code"], "{:,.0f}".format(val), cur, "{:,.2f}".format(v), ch[2], cite(ch[0]), yrtxt, FRAME[cc]["name"],
                                                     conv(cur, v * ch[1], val / (v * ch[1]))))
        return val, "national_source", note
    gbp, src = UK_COST[svc]
    if gbp is None:   # new-unit anchors from verified UK records
        rid = src
        if not ok(rid):
            return None, None, "no verified UK anchor"
        v, cur, yr = rec_money(rid)
        mult = 52 if svc.startswith("Opioid") else 1
        gbp = v * mult * uk_fy(2024) / uk_fy(int(yr) if int(yr) < 2024 else 2024)
        src = "%s, GBP %s%s at %s prices, uprated to GBP %s on ONS L8GG" % (cite(rid), "{:,.0f}".format(v), " a week x 52" if mult == 52 else "", yr, "{:,.0f}".format(gbp))
    lf = labour_factor(cc)
    val = gbp * lf
    note = ("%s %s, converted from %s. Converted on average hourly labour cost in health and social work "
            "(Eurostat lc_lci_lev, NACE Q, 2023: %s EUR %.2f an hour; UK GBP 30.2165), ratio %.6f. %s "
            "%s PRICE BASE: 2024-equivalent." % (FRAME[cc]["currency"]["code"], "{:,.0f}".format(val), src, FRAME[cc]["name"],
                                            FRAME[cc]["labour_cost_naceQ"]["eur_per_hour"], lf,
                                            ("No verified %s figure for this unit was found." % FRAME[cc]["name"]) if not ch else
                                            ("A %s figure exists (%s) but did not pass verification." % (FRAME[cc]["name"], cite(ch[0]))),
                                            conv("GBP", gbp, lf)))
    return val, "borrowed_adjusted", note


# ---------------------------------------------------------------------------------------------
# Raw values behind the conventional outcomes
UK_HOMELESS_GBP_2024 = 26988.3   # Crisis GBP 20,128 (2015-16) x 1.340835 (ONS L8GG, the UK tool's figure)
FEANTSA_RATIO = {cc: v["ratio"] for cc, v in FEANTSA["common_item_ratio_to_UK"].items()}


def housing_raw(cc):
    if cc == "ES" and ok("svc_care-086"):
        v = 1157.84 * 12 * defl("ES", 2018)
        return v, ("Hábitat randomised trial, usual-care cost EUR 1,157.84 a month at 2018 prices, x 12, uprated on Spain's GDP "
                   "deflator"), "national_source"
    if cc == "BE" and verdict("svc_care2-017") in ("PASS", "MEANING_MISMATCH"):
        v = (599245 - 317437) / 5153.0 * 365 * defl("BE", 2019)
        return v, ("Brussels-Capital, DULBEA 2022: public service use by homeless people, EUR 281,808 a day for 5,153 people at "
                   "2019 prices (the study's total of EUR 599,245 a day less EUR 317,437 of lost tax and contributions, which the "
                   "other countries' figures do not include), x 365, uprated on Belgium's GDP deflator"), "national_derived"
    if cc in FEANTSA_RATIO:
        f = FRAME[cc]
        gbp_per_eur = json.load(io.open(os.path.join(HERE, "frame", cc + ".json"), encoding="utf-8"))["meta"]["gbp_per_eur_2024"]
        eur = UK_HOMELESS_GBP_2024 / gbp_per_eur * FEANTSA_RATIO[cc]
        nac = eur * (1.0 if f["currency"]["code"] == "EUR" else f["fx_nac_per_eur"]["2024"])
        items = FEANTSA["common_item_ratio_to_UK"][cc]["common_items"]
        return nac, ("the UK tool's GBP 26,988 (Crisis 2015, uprated) scaled by the cost of the same year of homelessness in %s "
                     "relative to the UK, %.3f, from Pleace et al. (2013), The Costs of Homelessness in Europe, Table 5.2, compared on "
                     "the %d cost items both countries priced (%s), at 2024 market exchange rates" %
                     (f["name"], FEANTSA_RATIO[cc], len(items), ", ".join(i.replace("_", " ") for i in items))), "borrowed_adjusted"
    v = UK_HOMELESS_GBP_2024 * ppp_factor(cc)
    return v, ("the UK tool's GBP 26,988 (Crisis 2015, a derived 12-month rough-sleeper vignette, uprated) converted at "
               "%s; no %s cost of homelessness was found" % (ppp_source(cc), FRAME[cc]["name"])), "borrowed_adjusted"


PLACEMENT_NOTE = {
    "IT": " Per child served in the year, not per full child-year, so a lower bound.",
    "CZ": " A state-budget contribution, not the full cost, so a lower bound.",
    "PT": " The rate for residential homes adapted to the current regulation.",
    "SK": " The maximum state contribution, not the full cost, so a lower bound.",
}


def placement_cost(cc):
    ch = PLACEMENT.get(cc)
    if ch and ok(ch[0]):
        v, cur, yr = rec_money(ch[0])
        val = to_nac_2024(cc, v * ch[1], cur, yr or 2024)
        return val, "%s, %s %s%s at %s prices, uprated on the GDP deflator.%s" % (
            cite(ch[0]), cur, "{:,.0f}".format(v), " x 12 months" if ch[1] == 12 else (" x 365 days" if ch[1] == 365 else ""), yr,
            PLACEMENT_NOTE.get(cc, "")), "national_source"
    v, cur, yr = rec_money(UK_PLACEMENT)
    gbp = v * uk_fy(2024) / uk_fy(int(yr))
    lf = labour_factor(cc)
    return gbp * lf, ("%s, GBP %s per looked-after child a year at %s prices, uprated to GBP %s and converted on labour cost in "
                      "health and social work (ratio %.4f); no verified %s figure was found" %
                      (cite(UK_PLACEMENT), "{:,.0f}".format(v), yr, "{:,.0f}".format(gbp), lf, FRAME[cc]["name"])), "borrowed_adjusted"


def maltreatment_sensitivity(cc):
    """The UK tool's route: Italy's lifetime cost per new maltreatment case, EUR 111,665 at 2024
    prices (Bocconi 2013, EUR 87,389 at 2010 prices, uprated), at PPP, x effect 0.086."""
    return 111665 * (FRAME[cc]["ppp_e011_2024"] / FRAME["IT"]["ppp_e011_2024"]) * 0.086


def gbv_raw(cc):
    es = 2305.5   # the D2.2 Spain tool's figure: EUR 3,014.61m tangible (2022) over physical or sexual victims
    it = 2067.33 * defl("IT", 2012) if ok("svc_care-031") else None
    intang_es = 10808 * defl("ES", 2022)
    pps = lambda v, c: v / FRAME[c]["ppp_e011_2024"]
    sens = pps(intang_es, "ES") * FRAME[cc]["ppp_e011_2024"]
    if cc == "ES" and es:
        return es, ("Spain, Universidad de Alcalá for the Ministerio de Igualdad (2024): tangible costs of gender violence in "
                    "2022, EUR 3,014.61m, per victim of physical or sexual violence, the D2.2 Spain tool's figure"), "national_source", sens
    if cc == "IT" and it:
        return it, ("Italy, Intervita (2013), Quanto costa il silenzio?: EUR 2,067 per victim a year, tangible costs, at 2012 "
                    "prices, uprated"), "national_source", sens
    have = [pps(es, "ES")] if es else []
    have += [pps(it, "IT")] if it else []
    v = sum(have) / len(have) * FRAME[cc]["ppp_e011_2024"]
    return v, ("the mean of the Spanish and Italian national figures (tangible costs per victim of partner violence, from victim "
               "surveys), each uprated to 2024 and converted at household-consumption PPP; the EIGE per-country table is not used "
               "because it scales the UK cost by population"), "borrowed_adjusted", sens


# ---------------------------------------------------------------------------------------------
# Outcome values per person helped: (wbL, wbC, wbH, convL, convC, convH, sensC), rows, grade, note.
def money(cc, v):
    return "%s %s" % (FRAME[cc]["currency"]["code"], "{:,.0f}".format(v))


def spine(cc):
    if cc in SHIPPED_PPP:
        return {k: v * SHIPPED_PPP[cc] for k, v in {"L": 12540.0, "C": 16300.0, "H": 20064.0}.items()}
    return FRAME[cc]["spine"]


OPIOID_EXTRA = {  # from the UNODC file's Export sheet, found by the verifier (V1): latest complete year
    "BG": (0.684, "UNODC World Drug Report 2025, Statistical Annex 5.1, Export sheet: 4,510 opioid of 6,589 persons treated, 2018"),
    "DK": (0.130, "UNODC World Drug Report 2025, Statistical Annex 5.1, Export sheet: 613 opioid of 4,705 persons treated, 2014"),
    "LT": (0.720, "UNODC World Drug Report 2025, Statistical Annex 5.1, Export sheet: 1,051 opioid of 1,460 persons treated, 2018")}
ENTRANTS_ONLY = {"ES", "DE", "HU", "LV", "LU", "BE", "PL"}
RATE = (6.5, 21.45, 24.8)   # averted deaths per 1,000 opioid-client-years: CZ (svc_health2-013), FR 2026 (-012), Sordo 2017 (svc_health-017)


def opioid_share(cc):
    if cc in OPIOID_EXTRA:
        return OPIOID_EXTRA[cc]
    for rid, r in sorted(RECS.items()):
        if rid.startswith("svc_health-0") and r["country"] == cc and r["section"] == "other" and "opioid" in (r.get("unit") or ""):
            if verdict(rid) in ("PASS", "MEANING_MISMATCH"):
                txt = "%s: %s" % (cite(rid), r.get("derivation") or r["value"])
                if cc in ENTRANTS_ONLY:
                    txt += ". It counts people starting treatment in the year, so it understates the opioid share of a year's caseload: a lower bound"
                return float(r["value"]), txt
    raise KeyError("no opioid share for " + cc)


def _n(x):
    return ("%.10f" % x).rstrip("0").rstrip(".")


def _chain(origins, factors, eff, att):
    o, f = origins, factors
    return ("ORIGIN %s FACTOR %s; BAND ORIGIN %s AND %s; BAND FACTOR %s AND %s; STAGE EFFECT %s %s %s ATTRIBUTION %s %s %s;"
            % (_n(o[1]), _n(f[1]), _n(o[0]), _n(o[2]), _n(f[0]), _n(f[2]), _n(eff[0]), _n(eff[1]), _n(eff[2]),
               _n(att[0]), _n(att[1]), _n(att[2])))


SPINE_GBP = (12540.0, 16300.0, 20064.0)
CHAIN = {
    "Employment support": lambda cc: _chain(SPINE_GBP, [0.46 * ppp_factor(cc)] * 3, (0.11, 0.30, 0.46), (0.20, 0.22, 0.27)),
    "Minimum income casework": lambda cc: _chain((44.0, 91.0, 91.0 * 20773 / 8205), [uk_fy(2024) / uk_fy(2023) * ppp_factor(cc)] * 3, (1, 1, 1), (1, 1, 1)),
    "Debt advice": lambda cc: _chain(SPINE_GBP, (0.0, 0.355 * ppp_factor(cc), 0.5 * ppp_factor(cc)), (0, 0.10, 0.63), (1, 1, 0.5)),
    "Talking therapies": lambda cc: _chain(SPINE_GBP, (0.0, 0.42 * ppp_factor(cc), 1.5 * ppp_factor(cc)), (0, 1, 0.6), (1, 1, 0.61)),
    "Housing / homelessness": lambda cc: (lambda r: _chain((r, r, r), (1, 1, 1), (0.112, 0.407, 0.438), (1, 1, 1)))(housing_raw(cc)[0]),
    "Children's social care": lambda cc: (lambda r: _chain((r, r, r), (1, 1, 1), (0, 0.056, 0.119), (1, 1, 1)))(placement_cost(cc)[0]),
    "Domestic abuse / GBV": lambda cc: (lambda r: _chain((r, r, r), (1, 1, 1), (0.24, 0.24, 0.24), (0.5416667,) * 3))(gbv_raw(cc)[0]),
    "Drug & alcohol treatment": lambda cc: (lambda v, sh: _chain((v["L"], v["C"], v["H"]), [sh * r / 1000.0 for r in RATE], (1, 1, 1), (1, 1, 1)))(FRAME[cc]["vsl"], opioid_share(cc)[0]),
    "Opioid substitution treatment (OST)": lambda cc: (lambda v: _chain((v["L"], v["C"], v["H"]), [r / 1000.0 for r in RATE], (1, 1, 1), (1, 1, 1)))(FRAME[cc]["vsl"]),
}


def outcome(cc, svc):
    sp = spine(cc)
    ppf = ppp_factor(cc)
    Z = dict(wbL=0, wbC=0, wbH=0, convL=0, convC=0, convH=0, sensC=0)
    if svc == "Employment support":
        eff, att = (0.11, 0.30, 0.46), (0.20, 0.22, 0.27)
        w = [sp[k] * 0.46 * e * a for k, e, a in zip("LCH", eff, att)]
        Z.update(wbL=w[0], wbC=w[1], wbH=w[2])
        rows = [("Move into employment (wellbeing)", "WELLBY", "MODERATE", w[1])]
        g = "borrowed_unadjusted"
        n = ("+0.46 WELLBY for a move from unemployment into work (Clark et al. 2018, the Britain fixed-effects coefficient HM Treasury's "
             "guidance uses), valued at the WELLBY value for %s, then staged as in the UK tool: effect 0.11 / 0.30 / 0.46 x attribution "
             "0.20 / 0.22 / 0.27. European trial evidence (Card, Kluve and Weber 2018) puts job-search assistance impacts at 1 to 2 "
             "percentage points, which suggests the staged central may be high." % FRAME[cc]["name"])
    elif svc == "Minimum income casework":
        up = uk_fy(2024) / uk_fy(2023)
        c = [x * up * ppf for x in (44, 91, 91 * 20773 / 8205)]
        Z.update(convL=c[0], convC=c[1], convH=c[2])
        rows = [("Income effect", "ENGINE", "STRONG" if cc in MODELLED else "WEAK", 0),
                ("Health-service use avoided", "CONVENTIONAL", "MODERATE", c[1])]
        g = "borrowed_adjusted"
        n = ("Income effect: the extra-income figure. Health-service use avoided: Liverpool Citizens Advice on Prescription (SSM "
             "Population Health 2025), an instrumental-variable study on linked NHS records: GBP 91 per person a year (95%% CI 44 to "
             "107) at 2023 prices, an impact, so attribution 1.0. The saving is per household member; the central counts the client "
             "only, the high counts every member (20,773 members of 8,205 client households). Uprated to 2024-25 on ONS L8GG and "
             "converted at %s. The advice covered benefits, debt and housing together." % ppp_source(cc))
    elif svc == "Food aid / food banks":
        rows = [("Food aid", "UNEVIDENCED-EXCLUDED", "-", 0)]
        g = "assumption"
        n = ("Excluded for every country: no robust per-person effect exists. Randomised evidence shows small effects on food "
             "insecurity (for example Briefel et al., -2.8 points) and none on wellbeing; the Greek DIATROFI school-meal trial is a "
             "different service. The tool shows the income effect only, as a floor.")
    elif svc == "Debt advice":
        w = [0, 0.355 * sp["C"] * 0.10, 0.5 * sp["H"] * 0.63 * 0.5]
        Z.update(wbL=w[0], wbC=w[1], wbH=w[2])
        rows = [("Debt advice (wellbeing)", "WELLBY", "WEAK", w[1])]
        g = "borrowed_unadjusted"
        n = ("Being in arrears lowers life satisfaction by 0.355 points (FCA / Simetrica-Jacobs 2020, individual fixed effects). "
             "Central: advice moves 10 percentage points more clients out of unmanageable debt than no advice (Money Advice "
             "Service / YouGov 2012: 25% against 15%), an impact, so attribution 1.0: 0.355 x 0.10 WELLBY. Low: zero, because the "
             "only randomised trial (Pleasence and Balmer 2007) cannot rule it out. High: the UK tool's high.")
    elif svc == "Talking therapies":
        w = [0, 0.06 * 7 * sp["C"], 1.5 * 0.6 * 0.61 * sp["H"]]
        Z.update(wbL=w[0], wbC=w[1], wbH=w[2])
        rows = [("Recovery from depression or anxiety (wellbeing)", "WELLBY", "MODERATE", w[1])]
        g = "national_derived" if cc == "ES" else "borrowed_unadjusted"
        n = ("Central: 0.06 QALY per patient from adding transdiagnostic group CBT to usual primary care in Spain (the PsicAP "
             "randomised trial; abstract), converted at HM Treasury's 7 WELLBYs per QALY = 0.42 WELLBY, an impact, so attribution "
             "1.0. Low: zero (German and Swedish trials found no QALY difference). High: the UK tool's high for NHS Talking "
             "Therapies (1.5 x 0.6 x 0.61 WELLBY). Nordic studies find no net saving from reduced sick leave, so no cost-avoided "
             "value is added.")
    elif svc == "Housing / homelessness":
        raw, rawnote, rawg = housing_raw(cc)
        sh = (0.112, 0.407, 0.438)
        c = [raw * s for s in sh]
        Z.update(convL=c[0], convC=c[1], convH=c[2])
        rows = [("Public cost of homelessness avoided", "CONVENTIONAL", "MODERATE", c[1])]
        g = rawg
        n = ("A year of homelessness costs the public %s per person (%s). Share avoided by a year of housing support: central 0.407 "
             "(Spain, Hábitat randomised trial: EUR 470.97 of EUR 1,157.84 a month), high 0.438 (France, Un chez-soi d'abord "
             "randomised trial, on a consistent cost basis), both impacts, so attribution 1.0; low 0.112, the UK tool's "
             "central (0.20 x 0.562), whose effect share is an assumption." % (money(cc, raw), rawnote))
    elif svc == "Children's social care":
        pc, pnote, pg = placement_cost(cc)
        sh = (0.0, 0.056, 0.119)
        c = [pc * s for s in sh]
        sens = maltreatment_sensitivity(cc)
        Z.update(convL=c[0], convC=c[1], convH=c[2], sensC=sens)
        rows = [("Out-of-home placement avoided", "CONVENTIONAL", "WEAK", c[1]),
                ("Lifetime cost of maltreatment averted (not added)", "SENSITIVITY", "WEAK", sens)]
        g = pg
        n = ("A year of out-of-home care costs %s per child (%s). Reduction in the chance of a residential placement: central "
             "0.056 (Italy, P.I.P.P.I. against a comparison group, residential placements only: 6.4%% against 0.8%%), high 0.119 "
             "(the same, counting day foster care too), low zero (Al et al. 2012 meta-analysis: intensive family preservation "
             "generally does not prevent placement). One year of placement avoided is counted, which is conservative. The "
             "sensitivity row is the UK tool's route: the lifetime cost of a maltreatment case (Bocconi 2013, Italy) x 0.086."
             % (money(cc, pc), pnote))
    elif svc == "Domestic abuse / GBV":
        raw, rawnote, rawg, sens_raw = gbv_raw(cc)
        st = 0.24 * 0.5416667
        Z.update(convL=raw * st, convC=raw * st, convH=raw * st, sensC=sens_raw * st)
        rows = [("Abuse reduced (tangible costs avoided)", "CONVENTIONAL", "MODERATE", raw * st),
                ("Including pain and suffering (not added)", "SENSITIVITY", "WEAK", sens_raw * st)]
        g = rawg
        n = ("Tangible cost of intimate-partner violence per victim a year: %s (%s). Effect and attribution as in the UK tool "
             "(0.24 x 0.5417: advocacy reduces physical abuse, odds ratio 0.43, Ramsay et al. 2009). Pain and suffering are shown "
             "as a sensitivity, not added, as settled decision 8 does for Spain." % (money(cc, raw), rawnote))
    elif svc in ("Drug & alcohol treatment", "Opioid substitution treatment (OST)"):
        vsl = FRAME[cc]["vsl"]
        if svc.startswith("Drug"):
            share, snote = opioid_share(cc)
        else:
            share, snote = 1.0, "every OST patient is an opioid client"
        c = [vsl[k] * share * r / 1000.0 for k, r in zip("LCH", RATE)]
        Z.update(convL=c[0], convC=c[1], convH=c[2])
        rows = [("Deaths averted (opioid clients)", "CONVENTIONAL", "MODERATE", c[1])]
        g = "borrowed_unadjusted"
        n = ("Value of a statistical life for %s: %s (OECD 2025 base VSL for the EU, USD 8.4m at 2022 PPP, transferred by GDP per "
             "head in PPS with income elasticity 1.0, as the OECD recommends). Deaths averted per 1,000 opioid-client-years: "
             "central 21.45 (France, 175,000 patients, 2026), low 6.5 (Czechia), high 24.8 (Sordo et al. 2017, methadone). "
             "Share of clients who are opioid clients: %.3f (%s). Non-opioid clients carry no averted-death value in these figures."
             % (FRAME[cc]["name"], money(cc, vsl["C"]), share, snote))
    elif svc == "GP consultation":
        rows = [("GP consultation", "COST-INPUT", "COST-INPUT", 0)]
        g = "assumption"
        n = "Valued only at its cost: no defensible value per additional consultation was found (searched, none found)."
    else:
        raise KeyError(svc)
    for k in ("wbL", "wbC", "wbH", "convL", "convC", "convH", "sensC"):
        Z[k] = round(Z[k], 2)
    cen = {"WELLBY": Z["wbC"], "CONVENTIONAL": Z["convC"], "SENSITIVITY": Z["sensC"]}
    rows = [{"outcome": a, "method": b, "conf": c_, "valC": cen.get(b, 0)} for a, b, c_, d in rows]
    if any(Z[k] for k in ("wbL", "wbC", "wbH", "convL", "convC", "convH", "sensC")):
        n = n + " " + CHAIN.get(svc, lambda cc: "")(cc) + " PRICE BASE: 2024-equivalent."
    Z.update(rows=rows, provenance=g, provenance_note=n)
    return Z


# ---------------------------------------------------------------------------------------------
# Assembly
GRADE_NOTE = {"national_source": "a national source", "national_derived": "derived from national sources",
              "borrowed_adjusted": "borrowed from another country with a stated adjustment",
              "borrowed_unadjusted": "borrowed from another country without adjustment", "assumption": "an assumption"}
PROFILES = {"Lowest incomes (deciles 1-3)": [0, 1, 2], "Low-to-middle (deciles 4-6)": [3, 4, 5],
            "Broad mix (all deciles)": list(range(10))}


def svc_name(cc, svc):
    if svc == "Minimum income casework":
        return "Minimum income (%s) casework" % SCHEME[cc]
    return svc


def service_record(cc, svc):
    val, g, note = unit_cost(cc, svc)
    el, eg, en = ELAST[svc]
    prov = {"elastLow": eg, "elastCentral": eg, "elastHigh": eg, "staffRatio": "borrowed_unadjusted", "unitCost": g}
    pn = {"elastLow": en, "elastCentral": en, "elastHigh": en,
          "staffRatio": ("UK register benchmark, shown for reference only: no formula in the tool reads it; the extra-caseworker "
                         "figure uses the provider's own cases per caseworker."),
          "unitCost": note + " Unit: %s." % UNIT[svc]}
    return {"name": svc_name(cc, svc), "elastLow": el[0], "elastCentral": el[1], "elastHigh": el[2],
            "unitCost": round(val), "staffRatio": STAFF[svc], "provenance": prov, "provenance_note": pn}


def flag(cc, svc, o):
    grade = GRADE_NOTE.get(o["provenance"], o["provenance"])
    return "Unit: %s. Outcome value: %s. %s" % (UNIT[svc], grade, o["provenance_note"])


def spine_block(cc):
    sp = spine(cc)
    f = FRAME[cc]
    return {"value": round(sp["C"]), "label": "%s (HM Treasury's GBP 13,000 per WELLBY at 2019 prices, applied as GBP 16,300 at 2024 "
                                             "prices, converted at household-consumption PPP)" % money(cc, sp["C"]),
            "provenance": "borrowed_adjusted",
            "provenance_note": ("HM Treasury (2021) Wellbeing Guidance for Appraisal, GBP 13,000 per WELLBY at 2019 prices (low "
                                "10,000, high 16,000), applied as GBP 16,300 (12,540 / 20,064) at 2024 prices by HM Treasury's own "
                                "uprating method, converted at %s %.4f per GBP (Eurostat prc_ppp_ind, E011 household final "
                                "consumption, 2024). A transfer, flagged as such." % (f["currency"]["code"], f["ppp_factor_per_gbp"]))}


def country_block(cc, income):
    """income: dict(deciles, sc15, labels, reference_default, income_basis, income_year, wave_label)."""
    f = FRAME[cc]
    services = [service_record(cc, s) for s in SERVICES]
    outcomes = {}
    for s in SERVICES:
        o = outcome(cc, s)
        outcomes[svc_name(cc, s)] = o
        services[SERVICES.index(s)]["flag"] = flag(cc, s, o)
    if cc in MODELLED:
        base = json.load(io.open(os.path.join(DELIV, "europe", "tool_machinery", "country_%s.json" % MODELLED[cc]), encoding="utf-8"))
        shock = base["data"]["shockInterp"]
        pb = base["grid"]["meta"]["population_basis"]
        dials = {k: v for k, v in base["grid"]["dials"].items() if k == "unemployment_shock"}
        meta = dict(base["grid"]["meta"])
    else:
        hh = f["households_k"]["value"]
        ipb = income["pb"]
        pb = {"scope": "all_households", "includes": "Every private household (Eurostat).", "excludes": "Nothing.",
              "units_k": ipb["units_k"], "population_k": ipb["population_k"],
              "summary": ("All private households (Eurostat labour force survey household count) and the resident population on "
                          "1 January (Eurostat demo_pjan), the population the estimated extra income is spread over.")}
        a = {int(k): v for k, v in f["shock_aff_k"].items()}
        wa = f["working_age_households_k"]
        shock = {"du3": 3, "du5": 5, "aff3": round(a[3], 1), "aff5": round(a[5], 1),
                 "provenance": {"du3": "borrowed_adjusted", "du5": "borrowed_adjusted", "aff3": "borrowed_adjusted", "aff5": "borrowed_adjusted"},
                 "provenance_note": {
                     "du3": "The shock sizes are the UK model's computed points (3 and 5 percentage points); there is no model for %s." % f["name"],
                     "du5": "The shock sizes are the UK model's computed points (3 and 5 percentage points); there is no model for %s." % f["name"],
                     "aff3": ("The UK's modelled share of working-age units whose employment income falls at 3pp (2.176418%%), applied to "
                              "%s's working-age households: %.0f thousand households x %.4f working-age share (EU-SILC ilc_lvps02, %s: "
                              "households other than one adult aged 65+ or two adults with one aged 65+, a lower bound) = %.1f thousand."
                              % (f["name"], hh, wa["share"], wa["year"], a[3])),
                     "aff5": ("The same at 5pp (3.649125%%): %.1f thousand." % a[5])}}
        dials = {}
        meta = {"eps_grid": [0, 0.5, 1, 1.5, 2]}
        base = {}
    meta["population_basis"] = pb
    C = {
        "code": cc, "name": f["name"], "lang": "en", "locale": "en-GB",
        "currency": {"symbol": f["currency"]["symbol"], "code": f["currency"]["code"]},
        "title": "BENEFITS provider tool: %s" % f["name"],
        "deflator": (json.load(io.open(os.path.join(DELIV, "europe", "tool_machinery", "country_%s.json" % MODELLED[cc]), encoding="utf-8"))["deflator"]
                     if cc in MODELLED else 1),
        "income_basis": income["income_basis"], "income_year": income["income_year"],
        "wave_label": income["wave_label"],
        # ES, IT and EL keep the D2.2 spine block verbatim: same value, same note, as in the v1 tools.
        "wellby_spine": base["wellby_spine"] if cc in MODELLED else spine_block(cc),
        "labels": income["labels"], "profiles": PROFILES,
        "provider_default": "Employment support", "reference_default": income["reference_default"],
        "unit_noun": "households", "unit_noun_singular": "household",
        "capacity_caveat": ("The capacity and shock model is INDICATIVE: demand elasticities and staff ratios are mostly UK register "
                            "values, and the share of households losing an earner is the UK model's own share applied to %s's "
                            "working-age households. It is not calibrated to %s." % (f["name"], f["name"])),
        "analyst_price_base": "2024 prices",
        "provenance": (("Income effect from EUROMOD v3.8.6 run on EU-SILC data (2024 wave, income reference year 2023, policy "
                        "system %s_2023), as in the D2.2 %s tool. " % (cc, f["name"])) if cc in MODELLED else
                       ("No microsimulation for %s: the income effect is estimated from the national minimum-income outlay and "
                        "Eurostat income deciles, and household counts, price levels and labour costs are Eurostat database tables "
                        "(nama_10_gdp, prc_ppp_ind, lc_lci_lev, lfst_hhnhtych, demo_pjan, ilc_di01, ilc_lvps02), retrieved "
                        "September 2026. " % f["name"]))
                      + "Provider values are per person served, in %s at 2024 prices. Every value carries its source and a "
                        "grade in its own note; a value borrowed from another country is marked." % f["currency"]["code"],
        "data": {"services": services, "outcomes": outcomes, "deciles": income["deciles"], "sc15": income["sc15"],
                 "epsGrid": [0, 0.5, 1, 1.5, 2], "bu": base["data"]["bu"] if cc in MODELLED else pb["units_k"] / 1000.0, "shockInterp": shock, "scenarios": []},
        "grid": {"meta": meta, "dials": dials},
    }
    return C


def modelled_income(cc):
    base = json.load(io.open(os.path.join(DELIV, "europe", "tool_machinery", "country_%s.json" % MODELLED[cc]), encoding="utf-8"))
    d = base["data"]
    return {"deciles": {r: d["deciles"][r] for r in d["sc15"]}, "sc15": d["sc15"],
            "labels": {r: base["labels"].get(r, r) for r in d["sc15"]}, "reference_default": base["reference_default"],
            "income_basis": "model", "income_year": "2024", "wave_label": base.get("wave_label")}


def main(only=None):
    os.makedirs(OUTD, exist_ok=True)
    report = ["# Data report\n", "| cc | service | unit cost | grade | outcome central (conv+wb) | grade |", "|---|---|---|---|---|---|"]
    for cc in (only or EU27):
        income = modelled_income(cc) if cc in MODELLED else derived_income(cc)
        C = country_block(cc, income)
        json.dump(C, io.open(os.path.join(OUTD, cc + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        for s in C["data"]["services"]:
            o = C["data"]["outcomes"][s["name"]]
            report.append("| %s | %s | %s | %s | %s | %s |" % (cc, s["name"], "{:,}".format(s["unitCost"]), s["provenance"]["unitCost"],
                                                          "{:,.0f}".format(o["convC"] + o["wbC"]), o["provenance"]))
    io.open(os.path.join(OUTD, "DATA_REPORT.md"), "w", encoding="utf-8").write("\n".join(report) + "\n")
    used = sorted((USED | set(OUTCOME_IDS)) & set(RECS))
    json.dump({"used": used, "corrected": {k: v[3] for k, v in CORRECTED.items() if k in used},
               "clamped_price_years": sorted([list(x) for x in CLAMPED])},
              io.open(os.path.join(OUTD, "USED_RECORDS.json"), "w", encoding="utf-8"), indent=1)
    print("\n".join(report[:3] + report[3:40]))


EXTRA = json.load(io.open(os.path.join(ROOT, "evidence", "extra_income", "extra_income_results.json"), encoding="utf-8"))["countries"]


def derived_income(cc):
    """Extra income for a country without our microsimulation: the derivation in
    ../evidence/extra_income/REPORT.md (scheme outlay x pooled band share / population, welfare
    weights from Eurostat income deciles). Its tool_block reproduces the derived values through the
    tool's own formula; its population basis is used so that holds exactly."""
    tb = EXTRA[cc]["tool_block"]
    size = {"mi_10": "+10%", "mi_25": "+25%", "mi_50": "+50%"}
    return {"deciles": tb["deciles"], "sc15": ["mi_10", "mi_25", "mi_50"],
            "labels": {k: "Minimum income (%s) %s, estimated" % (SCHEME[cc], v) for k, v in size.items()},
            "reference_default": "mi_25", "income_basis": "derived", "income_year": "2024",
            "wave_label": ("No microsimulation for this country: extra income estimated from national minimum-income outlays "
                           "(EUROMOD external statistics and named national sources) and Eurostat income deciles"),
            "pb": tb["pb"]}


if __name__ == "__main__":
    import sys
    main([a for a in sys.argv[1:]] or None)
