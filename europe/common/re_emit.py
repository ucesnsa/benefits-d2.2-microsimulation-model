#!/usr/bin/env python3
"""
re_emit.py -- EU fiscal re-emit + provenance verifier for the Level-2 dial surfaces.

BENEFITS D2.2. This is the committed, non-superseded producer/verifier for the per-point
`fiscal` sub-object carried by the EU response surfaces
`europe/<Country>/outputs/dial_grid.json` (ES, EL, IT). It replaces an earlier, retired generator as the canonical reference for the
fiscal fields, and it writes its own proof to disk so the provenance is reproducible from
the folder alone.

The fiscal sub-object per grid point has five fields (EUR millions, 2023 nominal EUR):
    income_tax_delta_m, benefit_delta_m, sic_delta_m, net_income_delta_m, net_exchequer_cost_m
with the public-finance identity
    net_exchequer_cost_m = benefit_delta_m - income_tax_delta_m - sic_delta_m
(a cost to the purse is positive when benefits rise and/or tax+SIC receipts fall). The tool
uprates these to 2024 EUR for display by each country's Eurostat nama_10_gdp deflator; the
surface itself stays 2023 nominal.

Two modes
---------
verify  (default; FOLDER-ONLY, no engine, no microdata):
        Proves the committed surface's fiscal fields are internally consistent and that its
        non-fiscal fields (wevm/deciles/winners/losers) match a recorded signature. Checks:
          (a) non-fiscal byte-preservation signature (sha256) -- the value recorded in
              REEMIT_PROVENANCE.md is reproduced here;
          (b) the exchequer identity holds at every point (max residual reported);
          (c) the three fiscal checks: min-income levers carry zero tax-delta AND zero
              SIC-delta; pure PIT reforms have SIC == 0 while earnings-downturn and
              unemployment have SIC < 0; benefit-only levers carry zero income-tax-delta;
          (d) analytic min-income linearity (EL/ES): the min-income fiscal is exactly linear
              in magnitude, so every point implies the same baseline recipient outlay;
          (e) validate_grid.py PASS/WARN (the surface's own Level-2 structural validator).
        Writes proof to europe/<Country>/outputs/reemit_proof.json plus the captured
        validate_grid output to europe/<Country>/outputs/reemit_validate_grid.log.

produce (requires the matched EUROMOD v3.8.6 engine at %EUROMOD_PATH% AND the gated EU-SILC
        UDB installed in the EUROMOD data folder -- both external to this data-free tree):
        Re-runs each grid point's reform through the matched engine and regenerates the
        fiscal sub-object, leaving every non-fiscal field byte-identical (asserted via the
        signature). Method: weighted per-household fiscal aggregates from the EUROMOD outputs
        (ils_tax / ils_ben / ils_sicdy / ils_dispy), summed per household x12 x survey
        weight, differenced against baseline; EL/ES min-income is an analytic recipient
        top-up (m% x baseline recipient outlay; tax=0, sic=0), IT min-income is engine
        base-scaling. Stages the regenerated surface next to the proof; never overwrites the
        canonical surface without a human copy step. Reproduces the committed fiscal values.

Usage
-----
    py -3 re_emit.py verify            # folder-only proof for ES, EL, IT (default)
    py -3 re_emit.py verify EL         # one country
    py -3 re_emit.py produce EL        # engine regeneration (needs engine + UDB)
"""
import os
import sys
import json
import time
import hashlib
import argparse
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))                 # .../Deliverable/europe/common
EUROPE = os.path.dirname(HERE)                                    # .../Deliverable/europe
DELIV = os.path.dirname(EUROPE)                                   # .../Deliverable
VALIDATE = os.path.join(HERE, "validate_grid.py")

MODEL_DIR = {"ES": "Spain", "EL": "Greece", "IT": "Italy"}
MIN_INCOME_ANALYTIC = {"ES": True, "EL": True, "IT": False}       # EL/ES top-up (analytic); IT base-scaling
# The fiscal field list is DERIVED from the surface, never hard-coded here. It was a
# five-field literal, and when sic_employer_delta_m was added to the EU surfaces this
# file kept checking the old shape: verify tested presence of the five, which an
# extra field passes, while its identity omitted the employer term and failed on ES
# and EL; and produce would have regenerated a five-field object, silently dropping
# the sixth. Reading the shape from the data is what stops that recurring.
# The identity's revenue side is every field except the benefit side, the net income
# line and the result itself.
IDENTITY_RESULT = "net_exchequer_cost_m"
IDENTITY_COST = "benefit_delta_m"
IDENTITY_EXCLUDED = {"net_income_delta_m"}


def fiscal_shape(grid):
    """The exact key set every point's fiscal object must carry, taken from the
    surface. Returns (sorted_fields, problems); problems is non-empty if any point
    disagrees with any other, which is the shape check the old presence test missed."""
    shapes, problems = {}, []
    for dname in sorted(grid["dials"]):
        for p in grid["dials"][dname]["points"]:
            f = p.get("fiscal")
            if f is None:
                problems.append(f"{dname}@{p['magnitude']}: no fiscal object")
                continue
            shapes.setdefault(tuple(sorted(f)), []).append((dname, p["magnitude"]))
    if not shapes:
        return [], problems + ["no fiscal objects anywhere in the surface"]
    if len(shapes) > 1:
        ranked = sorted(shapes.items(), key=lambda kv: -len(kv[1]))
        common = ranked[0][0]
        for keys, where in ranked[1:]:
            extra, missing = set(keys) - set(common), set(common) - set(keys)
            problems.append(
                f"{len(where)} point(s) carry a different fiscal shape "
                f"(extra {sorted(extra) or '-'}, missing {sorted(missing) or '-'}), "
                f"first at {where[0][0]}@{where[0][1]}")
        return list(common), problems
    return list(next(iter(shapes))), problems


def identity_terms(fields):
    """(cost_field, [revenue_fields], result_field) for the exchequer identity."""
    revenue = [f for f in sorted(fields)
               if f not in IDENTITY_EXCLUDED and f not in (IDENTITY_COST, IDENTITY_RESULT)]
    return IDENTITY_COST, revenue, IDENTITY_RESULT


def identity_formula(fields):
    _, revenue, _ = identity_terms(fields)
    return f"{IDENTITY_RESULT} = {IDENTITY_COST} - " + " - ".join(revenue)
IDENTITY_TOL = 0.01                                              # surface stored to ~3 dp; 0.01 is generous
LINEARITY_TOL = 0.01                                            # relative tolerance on implied outlay


def surface_path(cc):
    return os.path.join(EUROPE, MODEL_DIR[cc], "outputs", "dial_grid.json")


def nonfiscal_sig(grid):
    """Deterministic sha256 over every NON-fiscal field, in a fixed order.

    Identical construction to the producer used at build time, so verifying the committed
    surface reproduces the byte-preservation signature recorded in REEMIT_PROVENANCE.md.
    """
    parts = []
    for dname in sorted(grid["dials"]):
        for p in grid["dials"][dname]["points"]:
            parts.append(json.dumps(
                [dname, p["magnitude"], p["wevm"], p["deciles"], p["winners_pct"], p["losers_pct"]],
                sort_keys=True))
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def verify(cc):
    """Folder-only provenance proof for one country's committed surface."""
    path = surface_path(cc)
    grid = json.load(open(path, encoding="utf-8"))
    dials = grid["dials"]

    # (a) non-fiscal byte-preservation signature
    sig = nonfiscal_sig(grid)

    # (b) fiscal shape + exchequer identity at every point. The shape is taken from
    # the surface and every point must match it exactly: a point carrying an extra or
    # a missing field is a failure, not something to be passed over. The identity is
    # then built from that shape, so a field added to the surface joins the identity
    # instead of being quietly left out of it.
    fields, shape_problems = fiscal_shape(grid)
    cost_f, revenue_f, result_f = identity_terms(fields)
    n_points = 0
    missing = []
    max_resid = 0.0
    worst = None
    for dname, d in dials.items():
        for p in d["points"]:
            n_points += 1
            f = p.get("fiscal")
            if f is None or sorted(f) != sorted(fields):
                missing.append((dname, p["magnitude"]))
                continue
            resid = abs(f[cost_f] - sum(f[r] for r in revenue_f) - f[result_f])
            if resid > max_resid:
                max_resid, worst = resid, (dname, p["magnitude"])

    # (c) the three fiscal checks
    def pts(dname):
        return dials[dname]["points"] if dname in dials else []

    mininc_tax0 = all(p["fiscal"]["income_tax_delta_m"] == 0.0 for p in pts("min_income_up"))
    mininc_sic0 = all(p["fiscal"]["sic_delta_m"] == 0.0 for p in pts("min_income_up"))
    pit_sic0 = all(p["fiscal"]["sic_delta_m"] == 0.0 for p in pts("pit_give"))
    gdp_sic_neg = all(p["fiscal"]["sic_delta_m"] < 0 for p in pts("gdp_shock") if p["magnitude"] != 0)
    unemp_sic_neg = all(p["fiscal"]["sic_delta_m"] < 0 for p in pts("unemployment_shock") if p["magnitude"] != 0)
    child_tax0 = all(p["fiscal"]["income_tax_delta_m"] == 0.0 for p in pts("child_benefit_up"))

    # (d) analytic min-income linearity (EL/ES): implied outlay must be constant across magnitudes
    implied_outlays = []
    linearity_ok = None
    if MIN_INCOME_ANALYTIC[cc]:
        for p in pts("min_income_up"):
            m = p["magnitude"]
            if m == 0:
                continue
            implied_outlays.append((m, round(p["fiscal"]["net_exchequer_cost_m"] / (m / 100.0), 3)))
        if implied_outlays:
            vals = [v for _, v in implied_outlays]
            spread = (max(vals) - min(vals)) / max(abs(sum(vals) / len(vals)), 1e-9)
            linearity_ok = spread <= LINEARITY_TOL

    # (e) validate_grid.py (captured verbatim)
    # This output is COMMITTED as reemit_validate_grid.log, so it has to be the same bytes
    # on every machine. validate_grid echoes its argv verbatim in its first line, so passing
    # an absolute path here wrote the operator's home directory into a tracked file: anyone
    # running the verification suite dirtied three tracked files and got a diff for their
    # trouble. The scrub could not help, because the verifier re-stamps the log AFTER the
    # scrub has run. Passing the path repository-relative with forward slashes, and running
    # the subprocess from the repository root so it still resolves, makes the line identical
    # anywhere. Nothing is lost: the line exists to say WHICH surface the PASS/WARN below
    # belongs to, and a repository-relative path says that exactly.
    rel = os.path.relpath(path, DELIV).replace(os.sep, "/")
    proc = subprocess.run([sys.executable, VALIDATE, rel],
                          capture_output=True, text=True, cwd=DELIV)
    vg_out = proc.stdout + ("\n[stderr]\n" + proc.stderr if proc.stderr.strip() else "")
    vg_status = "PASS" if proc.returncode == 0 else "FAIL"
    log_path = os.path.join(EUROPE, MODEL_DIR[cc], "outputs", "reemit_validate_grid.log")
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    open(log_path, "w", encoding="utf-8").write(vg_out)

    # An employer contribution that is identically zero at every point of every dial is
    # not a result, it is a missing input. Nothing was looking: the SIC check above reads
    # sic_delta_m, the employee leg, so Italy passed every check for a month while its
    # employer column was flat zero and its shock costs were understated by roughly a
    # third to three quarters. Spain reads 3.1 to 4.2 times its employee response and
    # Greece 1.5 to 1.6, so a zero is conspicuous once anything asks.
    #
    # Italy was gated BY NAME here for a month rather than the check being weakened to
    # accommodate it, because every one of its six employer components is gated in the
    # model on (lcl = 1) | (lcl = 2), the blue/white-collar contract class, and
    # convert_it.py never populated lcl. THE GATE IS NOW EMPTY, and deliberately so: the
    # 2026-08-02 rebuild derives lcl from occupation and Italy's employer contributions
    # come out at 181,054m against EUROMOD's own published 179,797m, responding on every
    # dial that destroys jobs. The set is kept rather than deleted so that a country
    # regressing to a flat zero fails here loudly, as Italy now would.
    EMPLOYER_ZERO_KNOWN = set()
    empr_vals = [p["fiscal"].get("sic_employer_delta_m", 0.0)
                 for d in grid["dials"].values() for p in d["points"]]
    empr_all_zero = all(abs(v or 0.0) < 1e-9 for v in empr_vals)
    empr_ok = (not empr_all_zero) or (cc in EMPLOYER_ZERO_KNOWN)

    checks_pass = (not missing and not shape_problems and max_resid <= IDENTITY_TOL
                   and mininc_tax0 and mininc_sic0
                   and pit_sic0 and gdp_sic_neg and unemp_sic_neg and child_tax0
                   and empr_ok
                   and (linearity_ok is not False) and proc.returncode == 0)

    proof = {
        "country": cc,
        "surface": os.path.relpath(path, DELIV).replace("\\", "/"),
        "n_points": n_points,
        "nonfiscal_sha256": sig,
        "fiscal_fields": sorted(fields),
        "fiscal_shape_uniform": not shape_problems,
        "fiscal_shape_problems": shape_problems,
        "fiscal_fields_present": not missing,
        "missing_fiscal_points": missing,
        "exchequer_identity": {
            "formula": identity_formula(fields),
            "max_abs_residual": round(max_resid, 6),
            "worst_point": worst,
            "tolerance": IDENTITY_TOL,
            "holds": max_resid <= IDENTITY_TOL,
        },
        "three_checks": {
            "min_income_zero_tax_and_sic": bool(mininc_tax0 and mininc_sic0),
            "pit_sic_zero": bool(pit_sic0),
            "downturn_and_unemployment_sic_negative": bool(gdp_sic_neg and unemp_sic_neg),
            "benefit_only_zero_income_tax": bool(child_tax0),
        },
        "employer_contributions": {
            "identically_zero_at_every_point": bool(empr_all_zero),
            "gated_as_known": cc in EMPLOYER_ZERO_KNOWN,
            "passes": bool(empr_ok),
            "min": min(empr_vals) if empr_vals else None,
            "max": max(empr_vals) if empr_vals else None,
            "note": ("Known absent and under investigation: the IT_2023 model defines seven "
                     "employer components, simulates them, and has sicer_it switched on, so a "
                     "flat zero is not a model limitation. Italy's shock exchequer costs are "
                     "understated while this stands." if cc in EMPLOYER_ZERO_KNOWN and empr_all_zero
                     else "Employer contributions respond, as they must."),
        },
        "min_income_lever": grid["meta"].get("min_income_lever"),
        "min_income_analytic": MIN_INCOME_ANALYTIC[cc],
        "min_income_linearity": {
            "checked": MIN_INCOME_ANALYTIC[cc],
            "implied_baseline_outlay_m_per_point": implied_outlays,
            "constant_within_tol": linearity_ok,
        },
        "validate_grid": {"exit_code": proc.returncode, "status": vg_status,
                          "log": os.path.relpath(log_path, DELIV).replace("\\", "/")},
        "all_checks_pass": bool(checks_pass),
        "verified_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": ("Folder-reproducible proof. The fiscal values themselves are regenerated only "
                 "by `produce` mode with the matched EUROMOD v3.8.6 engine + the gated UDB; this "
                 "verify pass proves internal consistency + non-fiscal preservation from the "
                 "committed surface alone."),
    }
    proof_path = os.path.join(EUROPE, MODEL_DIR[cc], "outputs", "reemit_proof.json")
    os.makedirs(os.path.dirname(proof_path) or ".", exist_ok=True)
    json.dump(proof, open(proof_path, "w", encoding="utf-8"), indent=2)
    return proof, proof_path


def produce(cc):
    """Engine regeneration of the fiscal sub-object. Requires the matched engine + gated UDB.

    Adapts the committed grid builder harness (europe/<Country>/model/build_grid.py). Stages
    the regenerated surface + a proof beside it; never overwrites the canonical surface.
    """
    import importlib
    import numpy as np
    os.environ.setdefault("EUROMOD_PATH", r"C:\Program Files\EUROMOD\Executable")
    G = os.path.join(EUROPE, MODEL_DIR[cc], "model")
    sys.path.insert(0, G)
    for d in ("pipeline", "wevm", "es_real", "it_real", "el_real"):
        sub = os.path.join(G, d)
        if os.path.isdir(sub):
            sys.path.insert(0, sub)
    import build_grid as BG
    engine, config, adapter = BG.engine, BG.config, BG.adapter

    grid = json.load(open(surface_path(cc), encoding="utf-8"))
    sig_before = nonfiscal_sig(grid)

    cfg = BG.CC_CFG[cc]
    sysname, dataset = cfg["system"], cfg["dataset"]
    print(f"== produce {cc} (system {sysname}, dataset {dataset}) ==")
    engine.assert_matched_engine()
    mod = engine.load_model()
    cobj = mod.countries[cc]
    sysobj = engine.get_system(cobj, sysname)
    template = list(cobj.load_data(cfg["train"]).columns)
    real = getattr(importlib.import_module(cfg["mod"]), cfg["fn"])(template)[0]
    earn = cfg["earn"]
    perm, lf = BG.nested_employed(real)
    # Engine columns for every field the surface carries EXCEPT the derived result.
    # Kept in step with europe/common/build_grid.py, which is the builder this mode
    # reproduces. If the surface grows a field with no column here, produce stops
    # rather than emitting a short object: that is exactly how sic_employer_delta_m
    # would have been dropped.
    COLUMN = {"income_tax_delta_m": "ils_tax", "benefit_delta_m": "ils_ben",
              "sic_delta_m": "ils_sicdy", "sic_employer_delta_m": "ils_sicer",
              "net_income_delta_m": "ils_dispy"}
    want_fields, shape_problems = fiscal_shape(grid)
    if shape_problems:
        raise SystemExit("produce %s: the surface's fiscal shape is not uniform: %s"
                         % (cc, "; ".join(shape_problems)))
    cost_f, revenue_f, result_f = identity_terms(want_fields)
    unmapped = [f for f in want_fields if f != result_f and f not in COLUMN]
    if unmapped:
        raise SystemExit("produce %s: the surface carries %s with no engine column mapped; "
                         "add it to COLUMN before regenerating, or produce would drop it"
                         % (cc, unmapped))
    fmap = {f: COLUMN[f] for f in want_fields if f != result_f}
    print("   fiscal shape from surface: %s" % sorted(want_fields))
    print("   identity: %s" % identity_formula(want_fields))

    def fagg(out, v):
        per_hh = out.groupby("idhh")[v].sum() * 12
        wt = out.groupby("idhh")["dwt"].first()
        return float((per_hh * wt).sum()) / 1e6

    base_out = engine.run(cobj, sysname, real, dataset).outputs[0]
    base_pu = adapter.euromod_to_per_unit(base_out, cc, BG.YEAR, "baseline")
    BG.base_pu_global = base_pu
    base_fisc = {k: fagg(base_out, col) for k, col in fmap.items()}

    outlay_m = None
    if MIN_INCOME_ANALYTIC[cc]:
        imv_col = BG.detect_imv_col(cc, base_out)
        imv_map = (base_out.groupby("idhh")[imv_col].sum() * 12).to_dict()
        idx = base_pu["unit_id"].astype(float).astype("int64").to_numpy()
        imv_hh = np.array([imv_map.get(i, 0.0) for i in idx], float)
        w = base_pu["survey_weight"].to_numpy(float)
        outlay_m = float((w * imv_hh).sum()) / 1e6

    def fdelta(out):
        d = {k: round(fagg(out, col) - base_fisc[k], 3) for k, col in fmap.items()}
        d[result_f] = round(d[cost_f] - sum(d[r] for r in revenue_f), 3)
        return d

    profile = config.PROFILES[cc]["reforms"]
    faith = []
    for dname in grid["dials"]:
        for pt in grid["dials"][dname]["points"]:
            mag = pt["magnitude"]
            if mag == 0:
                pt["fiscal"] = {k: 0.0 for k in want_fields}
                continue
            if dname == "min_income_up" and MIN_INCOME_ANALYTIC[cc]:
                # A pure benefit top-up: no tax, no contributions of either kind.
                f = round((mag / 100.0) * outlay_m, 3)
                pt["fiscal"] = dict({k: 0.0 for k in want_fields},
                                    **{cost_f: f, "net_income_delta_m": f, result_f: f})
                continue
            reform = BG.magnitude_to_reform(profile[dname], mag)
            out = BG.run_point(cobj, sysobj, sysname, dataset, real, earn, perm, lf, reform)
            pt["fiscal"] = fdelta(out)
            if sorted(pt["fiscal"]) != sorted(want_fields):
                raise SystemExit("produce %s: regenerated %s@%s with shape %s, expected %s"
                                 % (cc, dname, mag, sorted(pt["fiscal"]), sorted(want_fields)))
            wevm_re, *_ = BG.point_from_output(out, base_pu, cc, f"{dname}__m{mag}")
            faith.append(max(abs(wevm_re[i] - pt["wevm"][i]) for i in range(len(wevm_re))))

    sig_after = nonfiscal_sig(grid)
    staged = os.path.join(EUROPE, MODEL_DIR[cc], "outputs", "dial_grid.regenerated.json")
    os.makedirs(os.path.dirname(staged) or ".", exist_ok=True)
    json.dump(grid, open(staged, "w", encoding="utf-8"), indent=1)
    print(f"non-fiscal signature before={sig_before} after={sig_after} identical={sig_before==sig_after}")
    print(f"faithfulness max|dwevm| = {max(faith, default=0):.5f} over {len(faith)} engine points")
    print(f"STAGED (not canonical): {staged}")
    return sig_before == sig_after


def main():
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument("mode", choices=["verify", "produce"], nargs="?", default="verify")
    ap.add_argument("countries", nargs="*", default=["ES", "EL", "IT"])
    a = ap.parse_args()
    ccs = [c.upper() for c in a.countries] or ["ES", "EL", "IT"]
    if a.mode == "produce":
        for cc in ccs:
            produce(cc)
        return
    all_ok = True
    for cc in ccs:
        proof, pth = verify(cc)
        ei = proof["exchequer_identity"]
        tc = proof["three_checks"]
        lin = proof["min_income_linearity"]
        print(f"\n=== {cc}  ({proof['surface']}, {proof['n_points']} points) ===")
        print(f"  non-fiscal sha256          : {proof['nonfiscal_sha256']}")
        print(f"  fiscal fields              : {', '.join(proof['fiscal_fields'])}")
        print(f"  fiscal shape uniform       : {proof['fiscal_shape_uniform']}"
              + ("" if proof["fiscal_shape_uniform"]
                 else "  " + "; ".join(proof["fiscal_shape_problems"])))
        print(f"  fiscal fields present      : {proof['fiscal_fields_present']}")
        print(f"  exchequer identity         : {ei['formula']}")
        print(f"  exchequer identity holds   : {ei['holds']}  (max residual {ei['max_abs_residual']}, worst {ei['worst_point']})")
        print(f"  check min-income tax&sic=0 : {tc['min_income_zero_tax_and_sic']}")
        print(f"  check PIT sic=0            : {tc['pit_sic_zero']}")
        print(f"  check downturn/unemp sic<0 : {tc['downturn_and_unemployment_sic_negative']}")
        print(f"  check benefit-only tax=0   : {tc['benefit_only_zero_income_tax']}")
        ec = proof["employer_contributions"]
        print(f"  employer SIC responds      : {not ec['identically_zero_at_every_point']}"
              + (f"  (range {ec['min']} to {ec['max']})" if not ec["identically_zero_at_every_point"]
                 else "  IDENTICALLY ZERO"
                      + ("  -- gated by name, known absent, see R4" if ec["gated_as_known"]
                         else "  -- FAILS")))
        if lin["checked"]:
            print(f"  min-income linearity       : constant_outlay={lin['constant_within_tol']}  points={lin['implied_baseline_outlay_m_per_point']}")
        else:
            print(f"  min-income linearity       : N/A (IT engine base-scaling)")
        print(f"  validate_grid.py           : {proof['validate_grid']['status']} (exit {proof['validate_grid']['exit_code']})")
        print(f"  ALL CHECKS PASS            : {proof['all_checks_pass']}")
        print(f"  proof written              : {os.path.relpath(pth, DELIV)}")
        all_ok = all_ok and proof["all_checks_pass"]
    print(f"\nOVERALL: {'ALL COUNTRIES PASS' if all_ok else 'ONE OR MORE FAILED'}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
