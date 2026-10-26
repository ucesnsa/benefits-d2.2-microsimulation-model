"""Evidence tables for the technical report and the repository, generated from the country blocks
the tool embeds (data/<CC>.json), so the report cannot disagree with the tool.

Writes:
  report/EVIDENCE_TABLES.md      readable tables: per service, every country's unit cost and central
                                 outcome value, each with its provenance mark
  report/evidence_tables.tex     the same as LaTeX longtables for the report appendix
  report/used_records.json       every research record a shipped value rests on, with its source and
                                 its verification verdict (the public evidence file)
Run: py make_evidence_table.py
"""
import io, json, os, re, glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
OUT = os.path.join(HERE, "report")
EU27 = ["AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "EL", "HU", "IE", "IT", "LV", "LT",
        "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"]
MARK = {"national_source": "", "national_derived": "", "borrowed_adjusted": "*", "borrowed_unadjusted": "**",
        "assumption": "**", "user_supplied": ""}


def load():
    B = {cc: json.load(io.open(os.path.join(HERE, "data", cc + ".json"), encoding="utf-8")) for cc in EU27}
    return B


def generic(name):
    return "Minimum income casework" if name.startswith("Minimum income") else name


def tex(s):
    s = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"), ("_", r"\_"),
                 ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")):
        s = s.replace(a, b)
    return s


def main():
    os.makedirs(OUT, exist_ok=True)
    B = load()
    order = sorted(EU27, key=lambda c: B[c]["name"])
    services = [generic(s["name"]) for s in B["DE"]["data"]["services"]]
    md = ["# Evidence tables: the all-country provider tool\n",
          "Generated from the country blocks the tool embeds. Money is per person served, in each country's currency at "
          "2024 prices. Marks: none = a national source or derived from one; * = borrowed from another country with a "
          "stated adjustment; ** = borrowed without adjustment, or an assumption. Every value's full source note is in the "
          "tool (Full detail view) and in the country block.\n"]
    tx = []
    for sv in services:
        md.append("\n## %s\n" % sv)
        md.append("| country | currency | unit cost | outcome value, central (L / C / H) | extra income, lowest incomes, eps 1, +25% |")
        md.append("|---|---|---:|---|---:|")
        tx.append("\\subsection*{%s}\n\\begin{longtable}{llrr}\n\\toprule\nCountry & Currency & Unit cost & Outcome value, central \\\\\n\\midrule\n\\endhead" % tex(sv))
        for cc in order:
            C = B[cc]
            s = [x for x in C["data"]["services"] if generic(x["name"]) == sv][0]
            o = C["data"]["outcomes"][s["name"]]
            cur = C["currency"]["code"]
            lo = o["convL"] + o["wbL"]
            ce = o["convC"] + o["wbC"]
            hi = o["convH"] + o["wbH"]
            um = MARK[s["provenance"]["unitCost"]]
            om = MARK[o["provenance"]] if ce else ""
            prof = C["profiles"]["Lowest incomes (deciles 1-3)"]
            pb = C["grid"]["meta"]["population_basis"]
            ref = C["reference_default"]
            dec = C["data"]["deciles"][ref][C["data"]["epsGrid"].index(1)]
            pbw = sum(dec[i] for i in prof) * 10 / (len(prof) * pb["population_k"] / 1000.0)
            md.append("| %s | %s | %s%s | %s%s (%s / %s / %s) | %s |" % (C["name"], cur, "{:,}".format(s["unitCost"]), um,
                                                                   "{:,.0f}".format(ce), om, "{:,.0f}".format(lo),
                                                                   "{:,.0f}".format(ce), "{:,.0f}".format(hi), "{:,.0f}".format(pbw)))
            tx.append("%s & %s & %s%s & %s%s \\\\" % (tex(C["name"]), cur, "{:,}".format(s["unitCost"]), um, "{:,.0f}".format(ce), om))
        tx.append("\\bottomrule\n\\end{longtable}")
    io.open(os.path.join(OUT, "EVIDENCE_TABLES.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
    io.open(os.path.join(OUT, "evidence_tables.tex"), "w", encoding="utf-8").write("\n".join(tx) + "\n")
    # The records the shipped values rest on: every record id named in a note or in make_data.py's tables.
    recs, verd = {}, {}
    for f in glob.glob(os.path.join(ROOT, "research", "*", "findings.jsonl")):
        for line in io.open(f, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                recs[r["id"]] = r
    for f in glob.glob(os.path.join(ROOT, "evidence", "verify", "*.jsonl")):
        for line in io.open(f, encoding="utf-8"):
            if line.strip():
                v = json.loads(line)
                verd[v["id"]] = v["verdict"]
    U = json.load(io.open(os.path.join(HERE, "data", "USED_RECORDS.json"), encoding="utf-8"))
    ids, corrected = U["used"], U["corrected"]
    used = []
    for rid in ids:
        if rid in recs:
            r = recs[rid]
            used.append({"id": rid, "verdict": verd.get(rid), "corrected_on_verification": corrected.get(rid), "country": r["country"], "service": r.get("service"),
                         "section": r["section"], "value": r["value"], "unit": r.get("unit"), "currency": r.get("currency"),
                         "price_year": r.get("price_year"), "source": r["source"]})
    json.dump({"note": "Research records the shipped values rest on, with the verdict of a second, independent "
                       "check of each record against its source. Values are as the source prints them, before any conversion.",
               "records": used}, io.open(os.path.join(OUT, "used_records.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("tables: %d services x %d countries; used records: %d (%s)" % (len(services), len(order), len(used),
          ", ".join("%s %d" % (k, sum(1 for u in used if u["verdict"] == k)) for k in sorted({u["verdict"] or "none" for u in used}))))


if __name__ == "__main__":
    main()
