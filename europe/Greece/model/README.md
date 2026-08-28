# europe/Greece/model — Greece model (EUROMOD)

The Greece EUROMOD model. The shared factory (`pipeline/`, `wevm/`, `build_grid.py`, `validate_grid.py`) is **copied per country** alongside Greece's own converter and build scripts (`el_real/`). This interim per-country copy is deliberate and provisional; the shared-versus-per-country structure is settled later (see `../../common/README.md`).

- **Engine:** EUROMOD **v3.8.6** (not redistributed), Greece 2023 policy system, on the EU-SILC 2024 wave (2023 income reference year).
- **Self-loading:** `build_grid.py` locates its own folder and loads only Greece's config, reforms, and converter; running it writes surfaces to `../outputs/`.
- **Five Analyst dials:** GDP / market-income shock; **PIT first-bracket rate (9%)** cut; child benefit A21 (`bch`); minimum income KEA (income-floor top-up to existing recipients); unemployment shock (0–10pp).
- **Data-gated:** the EU-SILC data is held outside this repository; the model is non-functional without it, by design.

Repository guide: [../../../README.md](../../../README.md).
