# uk/model — UK model (PolicyEngine)

Driver code for the UK deliverable. Engine: **PolicyEngine UK 2.45.4 / policyengine-core 3.23.6** (pinned in `../requirements.lock`), 2023-24 policy system.

Contents: the numbered pipeline (`Code_FRS_23_24/`, steps 02–10), shared utilities, the WEVM engine (`wevm/`), the response-surface builder (`Code_FRS_23_24/09_build_dial_grid.py`), the surface validator (`Code_FRS_23_24/validate_grid.py`), and a synthetic CI fixture (`demo/`, the only tracked `.parquet`).

**Data-gated by design.** FRS microdata is licensed and is not in this repository (it lives outside the repo, under UKDS Special Licence). The extraction utilities in `data_extraction/` and the pipeline from step 02 are therefore non-functional without the licensed data; this is deliberate, not a defect. See `data_extraction/README.md`.

Repository guide: [../../README.md](../../README.md).
