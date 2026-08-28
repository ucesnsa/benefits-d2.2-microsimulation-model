"""
CI schema guard — load the committed SYNTHETIC per-unit fixture through the WEVM
layer and assert it is schema-valid and computable. Synthetic data only; no FRS,
no PolicyEngine.

Import resolution
-----------------
Both paths are resolved from this file, not from an assumed repository root. They
used to be `<parents[2]>/wevm` and `<parents[2]>/code/demo/per_unit_export.parquet`,
which described an earlier layout where this script sat in `code/demo/`. In this tree
it sits in `uk/model/demo/`, so both pointed at directories that do not exist and the
script could not run at all. It is not in the check suite, which is why nothing said
so until the W2 sweep on 2026-08-02.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # uk/model/demo
MODEL = HERE.parent                             # uk/model
sys.path.insert(0, str(MODEL / "wevm"))         # uk/model/wevm/wevm.py
import wevm  # noqa: E402

FIXTURE = HERE / "per_unit_export.parquet"


def main() -> None:
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"

    # load_per_unit_export runs validate_schema internally.
    df = wevm.load_per_unit_export(str(FIXTURE))
    print("load_per_unit_export: PASS  (rows=%d)" % len(df))

    missing = [c for c in wevm.REQUIRED_COLUMNS if c not in df.columns]
    assert not missing, f"missing required columns: {missing}"
    print("required columns present:", list(wevm.REQUIRED_COLUMNS))

    wevm.validate_schema(df)
    print("validate_schema: PASS")

    ev = wevm.compute_ev(df)
    assert len(ev) > 0, "compute_ev produced no rows"
    print("compute_ev: PASS  (rows=%d, scenarios=%s)"
          % (len(ev), sorted(ev["scenario"].unique())))

    summ = wevm.wevm(ev)
    assert len(summ) > 0, "wevm produced no rows"
    print("wevm: PASS  (rows=%d)" % len(summ))

    print("emitted columns:", list(df.columns))
    print("SCHEMA GUARD: ALL PASS")


if __name__ == "__main__":
    main()
