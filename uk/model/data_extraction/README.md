# Data Extraction Utilities

These scripts are **not part of the D2.2 microsimulation model**. They are personal data preparation utilities used to extract FRS variables from a local PostgreSQL warehouse into the parquet files that the model pipeline requires.

## What these scripts do

| Script | Purpose |
|---|---|
| `01_extract_frs_2022_23.py` | Extracts FRS 2022-23 variables from PostgreSQL schema `frs_2022_23` into six parquet files |
| `01_extract_frs_2023_24.py` | Extracts FRS 2023-24 variables from PostgreSQL schema `frs_2023_24` into six parquet files |

Each script connects to a local PostgreSQL warehouse, queries the raw FRS tables (adults, children, benefits, accounts, childcare, maintenance), and writes parquet files to `inputs/frs_<year>/`.

## Who needs to run these

Only researchers who:
- Hold a UKDS Special Licence for the FRS
- Have loaded the raw FRS data into a compatible PostgreSQL schema

All other users should obtain the pre-extracted parquets from a team member with UKDS access, or apply for access directly at [ukdataservice.ac.uk](https://ukdataservice.ac.uk).

## Model pipeline

The D2.2 model pipeline starts at **step 02** and requires only the parquet files as input. See the main [README](../../../README.md) — Data policy section.
