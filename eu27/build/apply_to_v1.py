"""Apply the reconciled provider evidence to the four D2.2 tools (v1) and rebuild them.

Spain, Italy and Greece: data.services and data.outcomes are replaced by the reconciled blocks
(data/<CC>.json, the same evidence the all-country tool uses), and money is written the English
way (locale en-GB) as in the rest of the page's figures. The UK block gains only
provider_income_uprate (ONS L8GG, FY2023-24 to FY2024-25), so its cash floor sits at the panel's
2024-25 prices. Nothing else in any block changes. Blocks are written exactly as the repository
stores them (json.dumps ensure_ascii=False indent=1, LF, no trailing newline), and the tools are
rebuilt with the repository's own instantiate.py.

Run: py apply_to_v1.py
"""
import io, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import DELIV  # noqa: E402
MACH = os.path.join(DELIV, "europe", "tool_machinery")
TOOLS = {"uk": os.path.join(DELIV, "uk", "tools", "dial_tool_uk.html"),
         "es": os.path.join(DELIV, "europe", "Spain", "tools", "dial_tool_spain.html"),
         "it": os.path.join(DELIV, "europe", "Italy", "tools", "dial_tool_italy.html"),
         "el": os.path.join(DELIV, "europe", "Greece", "tools", "dial_tool_greece.html")}


def load(f):
    return json.loads(io.open(os.path.join(MACH, f), "rb").read().decode("utf-8"))


def save(f, d):
    io.open(os.path.join(MACH, f), "wb").write(json.dumps(d, ensure_ascii=False, indent=1).encode("utf-8"))


def uk_uprate():
    q = json.load(io.open(os.path.join(HERE, "frame", "uk_l8gg.json"), encoding="utf-8"))["quarters"]
    fy = lambda y: (float(q["%d Q2" % y]) + float(q["%d Q3" % y]) + float(q["%d Q4" % y]) + float(q["%d Q1" % (y + 1)])) / 4
    return fy(2024) / fy(2023), fy(2023), fy(2024)


def main():
    for cc in ("ES", "IT", "EL"):
        f = "country_%s.json" % cc.lower()
        B = load(f)
        N = json.load(io.open(os.path.join(HERE, "data", cc + ".json"), encoding="utf-8"))
        assert [s["name"] for s in N["data"]["services"]] == list(N["data"]["outcomes"].keys())
        B["data"]["services"] = N["data"]["services"]
        B["data"]["outcomes"] = N["data"]["outcomes"]
        B["locale"] = "en-GB"
        save(f, B)
        print("updated", f)
    B = load("country_uk.json")
    r, a, b = uk_uprate()
    B["provider_income_uprate"] = round(r, 6)
    B["provider_income_uprate_note"] = (
        "The cash floor and engine income read the FRS 2023-24 surface; the provider panel is priced at 2024-25. "
        "They are brought across by the ONS L8GG implied GDP deflator, financial-year means %.4f (2023-24) and %.4f "
        "(2024-25), ratio %.6f (September 2026 release)." % (a, b, r))
    save("country_uk.json", B)
    print("updated country_uk.json, provider_income_uprate", round(r, 6))
    for k, out in TOOLS.items():
        subprocess.run([sys.executable, os.path.join(MACH, "instantiate.py"), os.path.join(MACH, "country_%s.json" % k), out], check=True)


if __name__ == "__main__":
    main()
