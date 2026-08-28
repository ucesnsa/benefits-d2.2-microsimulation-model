# europe/common — shared EUROMOD factory (reference copy)

The country-generic EUROMOD factory: the engine adapter, config, reforms, the response-surface builder (`build_grid.py`), the validator (`validate_grid.py`), and the WEVM engine (`wevm/`), plus the build sign-check summary.

**This is a copy, NOT the canonical source.** The final shared-versus-per-country structure is deferred to a later audit. Each country folder (`../Spain/model/`, `../Italy/model/`, `../Greece/model/`) carries its own working copy of this factory plus that country's specifics, and is what is actually run to produce that country's surfaces. **Do not treat this folder as the single source of truth or edit it as such** until the structure is settled.

Engine: **EUROMOD v3.8.6** (not redistributed here).

Repository guide: [../../README.md](../../README.md).
