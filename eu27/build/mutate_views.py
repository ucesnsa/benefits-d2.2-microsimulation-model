"""Negative control for check_views.py: each mutant breaks one fix in ONE view only, and
check_views must fail on it. A mutant that passes means the check cannot see that defect.

Run: py mutate_views.py   (about two minutes per mutant)
"""
import io, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import short_workdir  # noqa: E402
SRC = os.path.join(HERE, "..", "BENEFITS_Provider_Tool_EU27_v2.html")
MUTANTS = [
    ("lite staff default back to 10", '"st":"12"', '"st":"10"'),
    ("lite running cost no longer fills itself in", "if(COST_TOUCHED)return;var s=svcByName", "return;var s=svcByName"),
    ("lite cash floor not uprated to the panel price base", "const UP=(D.uprate||1),", "const UP=1,"),
    # calc() is a line-for-line port, so this line is in BOTH templates; only the last
    # occurrence (the lite template, embedded after the full one) is mutated.
    ("lite outcome value 1% high", "people*o.wbC,", "people*o.wbC*1.01,", "last"),
    # And the converse: the full view alone, so the check is seen to read both sides.
    ("full outcome value 1% high", "people*o.wbC,", "people*o.wbC*1.01,", "first"),
]


def main():
    with short_workdir() as wd:
        run_all(os.path.join(wd, "mutant.html"))


def run_all(MUT):
    page = io.open(SRC, encoding="utf-8").read()
    missed = 0
    for m in MUTANTS:
        why, old, new, where = (m + ("all",))[:4]
        n = page.count(old)
        if n == 0 or (where != "all" and n != 2):
            print("ANCHOR MISSING  %s (%d sites)" % (why, n))
            missed += 1
            continue
        i = page.rfind(old) if where == "last" else page.find(old)
        mutant = page.replace(old, new) if where == "all" else page[:i] + new + page[i + len(old):]
        io.open(MUT, "w", encoding="utf-8", newline="\n").write(mutant)
        r = subprocess.run([sys.executable, os.path.join(HERE, "check_views.py"), MUT], capture_output=True, text=True,
                           encoding="utf-8", timeout=1800)
        first = (r.stdout.splitlines() or ["(no output)"])[0]
        ok = r.returncode != 0
        missed += not ok
        print("%s  %s (%d sites)\n        %s" % ("CAUGHT" if ok else "MISSED", why, n, first))
    os.remove(MUT)
    print("mutants: %d, missed: %d" % (len(MUTANTS), missed))
    sys.exit(1 if missed else 0)


if __name__ == "__main__":
    main()
