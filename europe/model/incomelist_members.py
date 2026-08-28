"""incomelist_members.py -- what each EUROMOD income list this project validates against
actually contains, read from the live 2023 system rather than assumed.

Why this exists. On 2026-08-02 it turned out that the published Italian income tax line is
`tinna_s`, national IRPEF alone, while this project had been comparing it against
`ils_taxin`, the model's whole income-tax list. The comparison was not like-for-like and
the residual it produced was overstated by EUR 12.6bn. The two quantities and the rule that
they must never be mixed are `DATA_ISSUES_FOR_TECHNICAL_REPORT.md` 9.14.

The same check had never been applied to any other divergent line. Half of it is a question
about the reports and half is a question about this model, and this script answers the model
half exactly: for every income list the validation table reports, it prints the list's
members as the system defines them, so a gap can be attributed to a concept difference
rather than left as a residual.

An income list in EUROMOD is defined by a DefIL function whose parameters name its members;
a member may itself be a list, so the expansion is recursive and both the direct members and
the fully expanded leaf set are reported.

Aggregates only. Nothing is run, no data is read, no surface is touched.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EUROPE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(EUROPE, "common"))

import engine  # noqa: E402

SYSTEMS = {"ES": "ES_2023", "IT": "IT_2023", "EL": "EL_2023"}

# The lists the validation table reports, plus the two tax lists the Italian finding turned on.
LISTS = ["ils_tax", "ils_taxin", "ils_taxwl", "ils_sicee", "ils_sicse", "ils_sicot",
         "ils_sicdy", "ils_sicer", "ils_ben", "ils_pen", "ils_earns", "ils_origy",
         "ils_dispy"]


def defined_lists(system_obj):
    """{list name: [signed member names]} for every DefIl in the system.

    The connector presents a DefIl as a parameter bag in which `Name` carries the list's
    own name and EVERY OTHER parameter is a member: the parameter's NAME is the member and
    its VALUE is the sign, '+' or '-'. A member whose value is 'n/a' is switched off for
    this system and is reported as such rather than silently counted."""
    out = {}
    SKIP = {"name", "run_cond", "warn_if_nonmonetary", "regexp_def", "regexp_factor",
            "#_databasename", "comment"}
    for p in system_obj.policies:
        for f in (getattr(p, "functions", None) or []):
            if getattr(f, "name", "") != "DefIl":
                continue
            pars = [((getattr(x, "name", "") or ""), (getattr(x, "value", "") or ""))
                    for x in (getattr(f, "parameters", None) or [])]
            name = next((v.strip() for k, v in pars if k.strip().lower() == "name"), None)
            if not name:
                continue
            members = []
            for k, v in pars:
                kl = k.strip().lower()
                if kl in SKIP or kl.startswith("#"):
                    continue
                sign = v.strip()
                if sign in ("+", "-"):
                    members.append(sign + k.strip())
                elif sign.lower() in ("n/a", "na", ""):
                    members.append("(off)" + k.strip())
            out.setdefault(name, [])
            out[name].extend(members)
    return out


def expand(name, lists, seen=None):
    """Leaf members of `name`, following nested lists. Signs are not composed: the point is
    which underlying variables the list touches, not the arithmetic."""
    seen = seen or set()
    if name in seen:
        return []
    seen = seen | {name}
    out = []
    for m in lists.get(name, []):
        bare = m.lstrip("+-").replace("(off)","")
        if bare in lists:
            out.extend(expand(bare, lists, seen))
        else:
            out.append(m)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", default="ES,IT,EL")
    ap.add_argument("--out", default=os.path.join(EUROPE, "docs", "incomelist_members.json"))
    args = ap.parse_args(argv)

    engine.assert_matched_engine()
    mod = engine.load_model()
    report = {}
    for cc in [c.strip() for c in args.countries.split(",") if c.strip()]:
        sysname = SYSTEMS[cc]
        sysobj = engine.get_system(mod.countries[cc], sysname)
        lists = defined_lists(sysobj)
        entry = {"system": sysname, "n_lists_defined": len(lists), "lists": {}}
        print("=" * 90)
        print("%s (%s): %d income lists defined" % (cc, sysname, len(lists)))
        for name in LISTS:
            if name not in lists:
                print("   %-12s NOT DEFINED in this system" % name)
                entry["lists"][name] = None
                continue
            direct = lists[name]
            leaves = expand(name, lists)
            entry["lists"][name] = {"direct": direct, "leaves": leaves}
            print("   %-12s %2d direct: %s" % (name, len(direct), ", ".join(direct)))
            if leaves != direct:
                print("   %-12s %2d leaves: %s" % ("", len(leaves), ", ".join(leaves)))
        report[cc] = entry
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
    print("\nwritten", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
