"""Render both views of the all-country provider tool from ONE country block.

A country block has the shape of the shipped `country_<cc>.json` (the full tool's COUNTRY), with
one optional addition, `income_basis` ("model" or "derived"). The full view is that block in
full_template.html. The lite view needs the plain-language tool's data object D, which that tool's
own build read out of a RUNNING full tool; here it is computed
from the block directly, with the same expressions the full tool evaluates at load. check_views.py
proves the two routes give identical D for the three shipped EU blocks.
"""
import io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
import sys  # noqa: E402
sys.path.insert(0, HERE)
from paths import MACH  # noqa: E402
SHIPPED_TEMPLATE = os.path.join(MACH, "template.html")
PROFILE_NAMES = ["Lowest incomes (deciles 1-3)", "Low-to-middle (deciles 4-6)", "Broad mix (all deciles)"]
EPS_OPTIONS = ["0", "0.5", "1", "1.5", "2"]
LOCNAME = {"es-ES": "Spanish", "it-IT": "Italian", "el-GR": "Greek"}
EXAMPLE = {"es-ES": "€230.762", "it-IT": "€230.762", "el-GR": "€230.762"}


def shipped_footer():
    t = io.open(SHIPPED_TEMPLATE, encoding="utf-8").read()
    m = re.search(r'<footer class="brandfoot".*?</footer>', t, re.S)
    assert m, "footer not found in the shipped template"
    return m.group(0)


def extract_static(C):
    """The same object extract.py reads from a running tool, computed from the block."""
    data, grid = C["data"], C.get("grid") or {}
    pb = (grid.get("meta") or {}).get("population_basis")
    units_m = pb["units_k"] / 1000 if (pb and pb.get("units_k") is not None) else data["bu"]
    hh = (pb["population_k"] / pb["units_k"]) if (pb and pb.get("population_k") is not None and pb.get("units_k")) else 1
    labels = C.get("labels") or {}
    return {
        "COUNTRY": C, "services": data["services"], "outcomes": data["outcomes"],
        "deciles": {r: data["deciles"][r] for r in data["sc15"]},
        "labels": {r: labels.get(r, r) for r in data["sc15"]},
        "epsGrid": data["epsGrid"], "bu": data["bu"], "shockInterp": data["shockInterp"], "sc15": data["sc15"],
        "pb": pb, "UNITS_M": units_m, "HH_SIZE": hh, "PROFILES": C["profiles"],
        "SPINE": C.get("wellby_spine") or {"label": C["currency"]["symbol"]},
        "CUR": C["currency"]["symbol"], "LOC": C["locale"],
        "UNITN_ONE": C.get("unit_noun_singular") or "household", "UNITN": C.get("unit_noun") or "households",
        "footer": shipped_footer(),
        "defaults": {"sv": C.get("provider_default") or data["services"][0]["name"], "pe": "500", "co": "",
                     "pr": PROFILE_NAMES[0], "ep": "1", "rf": C.get("reference_default") or data["sc15"][0],
                     "st": "12", "cp": "50", "sh": "4"},
        "epsOptions": EPS_OPTIONS, "profOptions": PROFILE_NAMES,
    }


def lite_data(d):
    """The plain-language tool's D, from an extract-format dict; plus the derived-country fields."""
    C = d["COUNTRY"]
    code, loc = C["code"], d["LOC"]
    uk = code == "GB"
    derived = C.get("income_basis") == "derived"
    services = [{k: s.get(k) for k in ("name", "elastLow", "elastCentral", "elastHigh", "unitCost", "provenance", "flag")}
                for s in d["services"]]
    outcomes = {n: {k: o.get(k) for k in ("convL", "convC", "convH", "wbL", "wbC", "wbH", "sensC", "rows", "provenance")}
                for n, o in d["outcomes"].items()}
    si = d["shockInterp"]
    unit_cap = d["UNITN"][:1].upper() + d["UNITN"][1:]
    if uk:
        work = "These are the rows, labels and values the full D2.2 tool shows for the same inputs."
        fmt = "The full D2.2 tool writes numbers the same way."
    elif loc in LOCNAME:
        work = ("These are the rows, labels and values the full D2.2 tool shows for the same inputs. The full tool "
                "writes money the %s way, with a point for thousands, so there the same total reads %s."
                % (LOCNAME[loc], EXAMPLE[loc]))
        fmt = ("The full D2.2 tool writes money the %s way, with a point for thousands (%s is two hundred and thirty "
               "thousand), so check which way a figure is written before copying it from one tool to the other."
               % (LOCNAME[loc], EXAMPLE[loc]))
    else:
        work = "These are the rows, labels and values the full view shows for the same inputs."
        fmt = "The full view writes money in this country's own convention; check which way a figure is written before copying it."
    low = d["PROFILES"]["Lowest incomes (deciles 1-3)"]
    offered = [r for r in d["sc15"]
               if not re.match(r"^(shock|gdp|unemp|earn)", r) and sum(d["deciles"][r][0][i] for i in low) > 0]
    assert d["defaults"]["rf"] in offered, "default reference reform filtered out"
    D = {
        "sc15Offered": offered, "code": code, "countryName": C["name"], "cur": d["CUR"],
        "engine": ("national minimum-income data" if derived else
                   ("PolicyEngine UK" if uk else "EUROMOD, the EU’s tax-benefit model")),
        "survey": ("" if derived else ("the Family Resources Survey 2023-24" if uk else "the EU-SILC 2024 survey")),
        "spine": {"value": d["SPINE"]["value"], "label": d["SPINE"]["label"], "provenance": d["SPINE"].get("provenance")},
        "pb": {"units_k": d["pb"]["units_k"], "population_k": d["pb"]["population_k"]} if d["pb"] else None,
        "bu": d["bu"], "profiles": d["PROFILES"], "profOptions": d["profOptions"], "epsOptions": d["epsOptions"],
        "epsGrid": d["epsGrid"], "sc15": d["sc15"], "labels": d["labels"], "deciles": d["deciles"],
        "services": services, "outcomes": outcomes,
        "shockInterp": {"du3": si["du3"], "du5": si["du5"], "aff3": si["aff3"], "aff5": si["aff5"],
                        "provenance": {k: v for k, v in (si.get("provenance") or {}).items() if k in ("aff3", "aff5")}},
        "defaults": d["defaults"], "unitNounCap": unit_cap, "workNote": work, "fmtNote": fmt,
        "incomeYear": C.get("income_year") or ("2024-25" if uk else "2024"),
        "uprate": C.get("provider_income_uprate") or C.get("deflator") or 1,
    }
    if derived:
        D["derived"] = True
    return D


def footer_parts(footer):
    svg = re.search(r"<svg\b.*?</svg>", footer, re.S).group(0)
    emblem = re.search(r'<img class="emblem"[^>]*>', footer).group(0)
    assert 'alt="Funded by the European Union"' in emblem and "data:image/" in emblem, "emblem not found"
    return svg, emblem


def render_lite(C, template=None):
    d = extract_static(C)
    D = lite_data(d)
    svg, emblem = footer_parts(d["footer"])
    t = template or io.open(os.path.join(HERE, "lite_template.html"), encoding="utf-8").read()
    data = json.dumps(D, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = (t.replace("@@COUNTRY_NAME@@", C["name"]).replace("@@LOGO_SVG@@", svg)
             .replace("@@EMBLEM_IMG@@", emblem).replace("@@DATA@@", data))
    assert "@@" not in page, "unfilled placeholder"
    return page


def render_full(C, template=None):
    t = template or io.open(os.path.join(HERE, "full_template.html"), encoding="utf-8").read()
    block = json.dumps(C, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return t.replace("__COUNTRY_JSON__", block)
