# Extra income: generated tables

Written by `extra_income.py` on 2026-09-30T15:27:33. Do not edit by hand; REPORT.md quotes these.

## 1. Modelled truth (EUR per person per year, 2023 money, from the D2.2 country blocks)

| country | profile | +10% pbU | +25% pbU | +50% pbU | +25% pbW eps0.5 | eps1 | eps1.5 | eps2 | kappa eps1 (+25%) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ES | Lowest incomes (deciles 1-3) | 15.32 | 38.31 | 76.61 | 49.23 | 63.28 | 81.37 | 104.66 | 1.652 |
| ES | Low-to-middle (deciles 4-6) | 1.79 | 4.46 | 8.93 | 4.82 | 5.22 | 5.67 | 6.17 | 1.170 |
| ES | Broad mix (all deciles) | 5.14 | 12.84 | 25.68 | 16.23 | 20.56 | 26.12 | 33.26 | 1.601 |
| IT | Lowest incomes (deciles 1-3) | 49.87 | 124.18 | 232.51 | 159.76 | 205.58 | 264.59 | 340.61 | 1.655 |
| IT | Low-to-middle (deciles 4-6) | 3.49 | 8.32 | 14.83 | 8.98 | 9.71 | 10.53 | 11.45 | 1.167 |
| IT | Broad mix (all deciles) | 16.05 | 39.82 | 74.27 | 50.68 | 64.64 | 82.58 | 105.66 | 1.623 |
| EL | Lowest incomes (deciles 1-3) | 13.96 | 34.89 | 69.79 | 44.79 | 57.52 | 73.90 | 94.96 | 1.649 |
| EL | Low-to-middle (deciles 4-6) | 2.11 | 5.28 | 10.56 | 5.57 | 5.89 | 6.25 | 6.64 | 1.116 |
| EL | Broad mix (all deciles) | 4.87 | 12.16 | 24.33 | 15.21 | 19.12 | 24.13 | 30.55 | 1.572 |

Gain shares by decile at +25% (share of the reform's total gain, eps 0):

| | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 | D1-3 | D4-6 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ES | 58.4 | 21.6 | 9.4 | 5.8 | 4.1 | 0.5 | 0.1 | 0.0 | 0.0 | 0.0 | 89.5 | 10.4 |
| IT | 65.5 | 21.4 | 6.6 | 3.9 | 1.4 | 0.9 | 0.1 | 0.0 | 0.0 | 0.0 | 93.6 | 6.3 |
| EL | 68.8 | 12.0 | 5.2 | 5.8 | 6.4 | 0.8 | 0.4 | 0.5 | 0.0 | 0.0 | 86.1 | 13.0 |
| pooled | 64.2 | 18.4 | 7.1 | 5.2 | 4.0 | 0.8 | 0.2 | 0.2 | 0.0 | 0.0 | 89.7 | 9.9 |

Reform linearity (total modelled gain / (r x modelled baseline outlay)): ES +10%: 1.000, +25%: 1.000, +50%: 1.000; IT +10%: 1.063, +25%: 1.055, +50%: 0.984; EL +10%: 1.000, +25%: 1.000, +50%: 1.000

Identity check (model outlay, own shares, model population): max |error| ES 0.0%, IT 5.9%, EL 0.0% (IT: the dial scales the base amount, so it is not linear in r).

## 2. Outlay candidates on the three modelled countries (EUR m per year, nominal, own year)

| candidate | ES | IT | EL | source |
|---|---:|---:|---:|---|
| M_model | 2,479.3 (2023) | 8,853.8 (2023) | 495.7 (2023) | Deliverable/europe/docs/benefit_adjustments.json modelled_outlay_eur_m ... |
| R_recommended | 2,840.0 (2024) | 5,731.0 (2025) | 510.0 (2024) | EUROMOD J2.0+ Countries\ES\ES.xml ExternalStatistic Reference=bsa00_s year=2024 ... |
| E_euromod_2023 | 2,504.0 (2023) | 6,653.0 (2023) | 520.0 (2023) | EUROMOD J2.0+ Countries\ES\ES.xml ExternalStatistic Reference=bsa00_s year=2023 (= benefit ... |
| E_euromod_latest | 2,840.0 (2024) | 6,653.0 (2023) | 510.0 (2024) | EUROMOD J2.0+ Countries\ES\ES.xml ExternalStatistic Reference=bsa00_s year=2024 ... |
| A_admin_SPC | 4,368.1 (2024) | 5,731.0 (2025) | 525.7 (2024) | country_income-182 ... |
| B_esspros_2023 | 4,764.8 (2023) | 11,751.0 (2023) | 541.8 (2023) | spr_exp_fex spdep=CASH_P_INC spdepm=MT unit=MIO_NAC geo=ES time=2023 ... |
| B_esspros_latest | 5,450.0 (2024) | 10,125.0 (2024) | 525.7 (2024) | spr_exp_fex spdep=CASH_P_INC spdepm=MT unit=MIO_NAC geo=ES time=2024 ... |
| C_jrc_euromod_x12 | 10,347.1 (2024) | 5,032.0 (2024) | 225.1 (2024) | country_income-143 ... |
| D_recipients_x_rate | 5,326.3 (2024) | 7,706.4 (2024) | 447.6 (2024) | country_income-063 (673,729 households (unit text)) x country_income-010 (658.81 EUR per m ... |

Ratio to the modelled outlay, both at 2024 prices: M_model: ES 1.00, IT 1.00, EL 1.00; R_recommended: ES 1.11, IT 0.62, EL 1.00; E_euromod_2023: ES 1.01, IT 0.75, EL 1.05; E_euromod_latest: ES 1.11, IT 0.75, EL 1.00; A_admin_SPC: ES 1.71, IT 0.62, EL 1.03; B_esspros_2023: ES 1.92, IT 1.33, EL 1.09; B_esspros_latest: ES 2.14, IT 1.12, EL 1.03; C_jrc_euromod_x12: ES 4.06, IT 0.56, EL 0.44; D_recipients_x_rate: ES 2.09, IT 0.85, EL 0.87

## 3. Validation: derived pbU vs modelled pbU (leave-one-out band shares, Eurostat population, both at 2024 prices)

Error = derived / modelled - 1, in per cent.

| candidate | profile | ES +10 | ES +25 | ES +50 | IT +10 | IT +25 | IT +50 | EL +10 | EL +25 | EL +50 | MAE all cells |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M_model | lowest | +0.6 | +0.7 | +0.9 | -12.0 | -11.6 | -5.6 | +4.0 | +4.2 | +4.4 | 16.3 |
| M_model | lowmid | -5.9 | -7.1 | -8.5 | +67.8 | +76.1 | +97.7 | -36.2 | -37.2 | -38.3 | |
| M_model | all | +0.4 | +0.4 | +0.4 | -6.5 | -5.8 | +1.0 | -2.1 | -2.1 | -2.1 | |
| R_recommended | lowest | +10.7 | +10.9 | +11.1 | -45.2 | -44.9 | -41.2 | +3.9 | +4.1 | +4.3 | 18.2 |
| R_recommended | lowmid | +3.6 | +2.2 | +0.8 | +4.6 | +9.7 | +23.2 | -36.3 | -37.2 | -38.3 | |
| R_recommended | all | +10.5 | +10.5 | +10.5 | -41.7 | -41.3 | -37.1 | -2.1 | -2.1 | -2.1 | |
| E_euromod_2023 | lowest | +1.6 | +1.7 | +1.9 | -33.8 | -33.6 | -29.1 | +9.1 | +9.3 | +9.5 | 16.8 |
| E_euromod_2023 | lowmid | -4.9 | -6.2 | -7.6 | +26.1 | +32.3 | +48.6 | -33.1 | -34.1 | -35.2 | |
| E_euromod_2023 | all | +1.4 | +1.4 | +1.4 | -29.7 | -29.2 | -24.1 | +2.7 | +2.7 | +2.7 | |
| E_euromod_latest | lowest | +10.7 | +10.9 | +11.1 | -33.8 | -33.6 | -29.1 | +3.9 | +4.1 | +4.3 | 18.1 |
| E_euromod_latest | lowmid | +3.6 | +2.2 | +0.8 | +26.1 | +32.3 | +48.6 | -36.3 | -37.2 | -38.3 | |
| E_euromod_latest | all | +10.5 | +10.5 | +10.5 | -29.7 | -29.2 | -24.1 | -2.1 | -2.1 | -2.1 | |
| A_admin_SPC | lowest | +70.3 | +70.6 | +70.9 | -45.2 | -44.9 | -41.2 | +7.1 | +7.3 | +7.5 | 37.5 |
| A_admin_SPC | lowmid | +59.4 | +57.3 | +55.0 | +4.6 | +9.7 | +23.2 | -34.3 | -35.3 | -36.4 | |
| A_admin_SPC | all | +70.0 | +70.0 | +70.0 | -41.7 | -41.3 | -37.1 | +0.9 | +0.9 | +0.9 | |
| B_esspros_2023 | lowest | +93.2 | +93.6 | +94.0 | +16.8 | +17.3 | +25.3 | +13.7 | +13.9 | +14.1 | 56.0 |
| B_esspros_2023 | lowmid | +80.9 | +78.5 | +75.9 | +122.8 | +133.7 | +162.4 | -30.3 | -31.4 | -32.5 | |
| B_esspros_2023 | all | +92.9 | +92.9 | +92.9 | +24.1 | +25.1 | +34.1 | +7.1 | +7.1 | +7.1 | |
| B_esspros_latest | lowest | +112.5 | +112.8 | +113.3 | -1.4 | -1.0 | +5.8 | +7.1 | +7.3 | +7.5 | 53.0 |
| B_esspros_latest | lowmid | +98.9 | +96.2 | +93.4 | +88.0 | +97.3 | +121.5 | -34.3 | -35.3 | -36.4 | |
| B_esspros_latest | all | +112.1 | +112.1 | +112.1 | +4.8 | +5.6 | +13.2 | +0.9 | +0.9 | +0.9 | |
| C_jrc_euromod_x12 | lowest | +303.4 | +304.1 | +304.9 | -51.0 | -50.8 | -47.4 | -54.1 | -54.0 | -54.0 | 129.4 |
| C_jrc_euromod_x12 | lowmid | +277.5 | +272.5 | +267.1 | -6.6 | -2.0 | +10.1 | -71.9 | -72.3 | -72.8 | |
| C_jrc_euromod_x12 | all | +302.7 | +302.6 | +302.6 | -47.9 | -47.5 | -43.7 | -56.8 | -56.8 | -56.8 | |
| D_recipients_x_rate | lowest | +107.6 | +108.0 | +108.4 | -24.9 | -24.6 | -19.5 | -8.8 | -8.6 | -8.5 | 52.2 |
| D_recipients_x_rate | lowmid | +94.3 | +91.8 | +89.0 | +43.1 | +50.2 | +68.6 | -44.1 | -44.9 | -45.8 | |
| D_recipients_x_rate | all | +107.3 | +107.3 | +107.3 | -20.3 | -19.7 | -13.9 | -14.1 | -14.1 | -14.1 | |

MAE by profile group (per cent): M_model: D1-3 & all 3.6, D4-6 41.6; R_recommended: D1-3 & all 18.6, D4-6 17.3; E_euromod_2023: D1-3 & all 12.5, D4-6 25.4; E_euromod_latest: D1-3 & all 14.6, D4-6 25.0; A_admin_SPC: D1-3 & all 38.8, D4-6 35.0; B_esspros_2023: D1-3 & all 42.5, D4-6 83.1; B_esspros_latest: D1-3 & all 40.6, D4-6 77.9; C_jrc_euromod_x12: D1-3 & all 135.6, D4-6 117.0; D_recipients_x_rate: D1-3 & all 46.5, D4-6 63.5

## 4. Error decomposition, default profile D1-3, +25%

derived/modelled = outlay factor x band-share factor x population factor x reform-shape factor

| outlay used | country | outlay (used/model, 2024 prices) | band share (LOO/own) | population (model/Eurostat) | reform shape (linear/model) | product | derived/modelled |
|---|---|---:|---:|---:|---:|---:|---:|
| R_recommended | ES | 1.113 | 1.004 | 0.993 | 1.000 | 1.109 | 1.109 |
| R_recommended | IT | 0.622 | 0.938 | 0.995 | 0.948 | 0.551 | 0.551 |
| R_recommended | EL | 0.997 | 1.064 | 0.982 | 1.000 | 1.041 | 1.041 |
| E_euromod_2023 | ES | 1.010 | 1.004 | 1.004 | 1.000 | 1.017 | 1.017 |
| E_euromod_2023 | IT | 0.751 | 0.938 | 0.994 | 0.948 | 0.664 | 0.664 |
| E_euromod_2023 | EL | 1.049 | 1.064 | 0.979 | 1.000 | 1.093 | 1.093 |

## 5. Validation: kappa from Eurostat deciles vs modelled kappa

Mean absolute error over ES, IT, EL x 3 profiles x 3 sizes x eps 0.5-2 (per cent):

| method | pattern | SILC 2024 (model wave) | SILC 2025 (latest) |
|---|---|---:|---:|
| K1 | own | 0.80 | 0.76 |
| K1 | loo | 1.70 | 1.69 |
| K2 | own | 0.71 | 0.66 |
| K2 | loo | 1.66 | 1.60 |

Selected (lowest MAE, leave-one-out pattern, latest wave): **K2**.

Detail, K2, leave-one-out pattern, SILC 2025, +25%: modelled kappa -> derived kappa (error %)

| country | profile | eps 0.5 | eps 1 | eps 1.5 | eps 2 |
|---|---|---|---|---|---|
| ES | lowest | 1.285 -> 1.286 (+0.1) | 1.652 -> 1.655 (+0.2) | 2.124 -> 2.129 (+0.2) | 2.732 -> 2.740 (+0.3) |
| ES | lowmid | 1.081 -> 1.069 (-1.1) | 1.170 -> 1.145 (-2.2) | 1.270 -> 1.229 (-3.2) | 1.381 -> 1.324 (-4.2) |
| ES | all | 1.263 -> 1.263 (-0.0) | 1.601 -> 1.601 (-0.0) | 2.034 -> 2.034 (+0.0) | 2.590 -> 2.592 (+0.1) |
| IT | lowest | 1.287 -> 1.284 (-0.2) | 1.655 -> 1.650 (-0.4) | 2.131 -> 2.120 (-0.5) | 2.743 -> 2.725 (-0.7) |
| IT | lowmid | 1.079 -> 1.068 (-1.0) | 1.167 -> 1.144 (-2.0) | 1.265 -> 1.228 (-3.0) | 1.376 -> 1.321 (-4.0) |
| IT | all | 1.273 -> 1.257 (-1.3) | 1.623 -> 1.586 (-2.3) | 2.074 -> 2.008 (-3.2) | 2.654 -> 2.549 (-3.9) |
| EL | lowest | 1.284 -> 1.284 (+0.0) | 1.649 -> 1.649 (+0.0) | 2.118 -> 2.119 (+0.0) | 2.721 -> 2.723 (+0.1) |
| EL | lowmid | 1.055 -> 1.069 (+1.3) | 1.116 -> 1.146 (+2.7) | 1.183 -> 1.231 (+4.0) | 1.257 -> 1.325 (+5.4) |
| EL | all | 1.250 -> 1.265 (+1.2) | 1.572 -> 1.606 (+2.2) | 1.983 -> 2.043 (+3.0) | 2.512 -> 2.604 (+3.7) |

## 6. ES, IT, EL: modelled vs derived by the recommended rule (EUR per person per year)

Modelled at 2023 money and uprated to 2024; derived at 2024 prices (pooled shares, not leave-one-out).

| country | profile | size | modelled pbU 2023 | modelled pbU 2024 | derived pbU 2024 | modelled pbW eps1 2023 | derived pbW eps1 2024 | modelled kappa eps1 | derived kappa eps1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ES | lowest | +10% | 15.32 | 15.77 | 17.44 | 25.31 | 28.82 | 1.652 | 1.652 |
| ES | lowest | +25% | 38.31 | 39.41 | 43.66 | 63.28 | 72.14 | 1.652 | 1.652 |
| ES | lowest | +50% | 76.61 | 78.83 | 87.44 | 126.56 | 144.49 | 1.652 | 1.652 |
| ES | lowmid | +10% | 1.79 | 1.84 | 1.95 | 2.09 | 2.24 | 1.170 | 1.150 |
| ES | lowmid | +25% | 4.46 | 4.59 | 4.82 | 5.22 | 5.54 | 1.170 | 1.150 |
| ES | lowmid | +50% | 8.93 | 9.18 | 9.55 | 10.45 | 10.97 | 1.170 | 1.149 |
| ES | all | +10% | 5.14 | 5.29 | 5.84 | 8.22 | 9.34 | 1.601 | 1.598 |
| ES | all | +25% | 12.84 | 13.21 | 14.60 | 20.56 | 23.35 | 1.601 | 1.599 |
| ES | all | +50% | 25.68 | 26.43 | 29.21 | 41.12 | 46.72 | 1.601 | 1.600 |
| IT | lowest | +10% | 49.87 | 50.93 | 28.51 | 82.54 | 47.05 | 1.655 | 1.650 |
| IT | lowest | +25% | 124.18 | 126.82 | 71.37 | 205.58 | 117.79 | 1.655 | 1.650 |
| IT | lowest | +50% | 232.51 | 237.45 | 142.93 | 385.00 | 235.91 | 1.656 | 1.651 |
| IT | lowmid | +10% | 3.49 | 3.57 | 3.18 | 4.08 | 3.65 | 1.167 | 1.147 |
| IT | lowmid | +25% | 8.32 | 8.50 | 7.88 | 9.71 | 9.03 | 1.167 | 1.146 |
| IT | lowmid | +50% | 14.83 | 15.15 | 15.61 | 17.30 | 17.89 | 1.166 | 1.145 |
| IT | all | +10% | 16.05 | 16.39 | 9.55 | 26.01 | 15.24 | 1.621 | 1.596 |
| IT | all | +25% | 39.82 | 40.67 | 23.87 | 64.64 | 38.12 | 1.623 | 1.597 |
| IT | all | +50% | 74.27 | 75.85 | 47.74 | 120.74 | 76.28 | 1.626 | 1.598 |
| EL | lowest | +10% | 13.96 | 14.40 | 14.68 | 23.01 | 24.23 | 1.649 | 1.651 |
| EL | lowest | +25% | 34.89 | 36.01 | 36.74 | 57.52 | 60.65 | 1.649 | 1.651 |
| EL | lowest | +50% | 69.79 | 72.03 | 73.58 | 115.05 | 121.47 | 1.649 | 1.651 |
| EL | lowmid | +10% | 2.11 | 2.18 | 1.64 | 2.36 | 1.86 | 1.116 | 1.139 |
| EL | lowmid | +25% | 5.28 | 5.45 | 4.06 | 5.89 | 4.62 | 1.116 | 1.138 |
| EL | lowmid | +50% | 10.56 | 10.90 | 8.04 | 11.79 | 9.14 | 1.116 | 1.137 |
| EL | all | +10% | 4.87 | 5.02 | 4.92 | 7.65 | 7.84 | 1.571 | 1.596 |
| EL | all | +25% | 12.16 | 12.55 | 12.29 | 19.12 | 19.62 | 1.572 | 1.597 |
| EL | all | +50% | 24.33 | 25.11 | 24.58 | 38.23 | 39.25 | 1.571 | 1.597 |

## 7. All 27 at the tool default (lowest incomes D1-3, eps 1, +25%), 2024 prices

| country | outlay (m, currency, year) | step | source | population (m) | pbU | pbU range (band share) | kappa eps1 | **pbW eps1** | pbW eps1 EUR |
|---|---:|---:|---|---:|---:|---|---:|---:|---:|
| AT | 1,247.0 EUR (2024) | 1 | EM Countries\AT\AT.xml bsa_s year=2024 | 9.16 | 101.77 | 97.64-106.16 | 1.636 | **166.49** | 166.49 |
| BE | 2,166.0 EUR (2024) | 1 | EM Countries\BE\BE.xml bsa_s year=2024 | 11.82 | 137.01 | 131.44-142.91 | 1.619 | **221.84** | 221.84 |
| BG | 62.1 EUR (2024) | 1 | EM Countries\BG\BG.xml bsa00_s year=2024 | 6.45 | 7.20 | 6.91-7.51 | 1.657 | **11.94** | 11.94 |
| HR | 63.0 EUR (2024) | 1 | EM Countries\HR\HR.xml bsa_s year=2024 | 3.86 | 12.19 | 11.70-12.72 | 1.651 | **20.13** | 20.13 |
| CY | 191.1 EUR (2024) | 1 | EM Countries\CY\CY.xml bsamm_s year=2024 | 0.97 | 147.82 | 141.81-154.18 | 1.642 | **242.66** | 242.66 |
| CZ | 4,180.0 CZK (2024) | 2 | country_income-179 | 10.90 | 286.64 | 274.98-298.98 | 1.603 | **459.60** | 18.30 |
| DK | 9,850.0 DKK (2024) | 1 | EM Countries\DK\DK.xml bsa_s year=2024 | 5.96 | 1,235.12 | 1,184.89-1,288.28 | 1.621 | **2,002.72** | 268.50 |
| EE | 39.0 EUR (2024) | 1 | EM Countries\EE\EE.xml bsa00_s year=2024 | 1.37 | 21.21 | 20.34-22.12 | 1.653 | **35.06** | 35.06 |
| FI | 782.8 EUR (2024) | 1 | EM Countries\FI\FI.xml bsa00_s year=2024 | 5.60 | 104.42 | 100.17-108.91 | 1.630 | **170.22** | 170.22 |
| FR | 12,218.0 EUR (2023) | 2 | extra_income-S01 | 68.28 | 136.49 | 130.94-142.37 | 1.641 | **223.92** | 223.92 |
| DE | 29,000.0 EUR (2024) | 2 | country_income-180 | 83.46 | 259.75 | 249.18-270.93 | 1.642 | **426.46** | 426.46 |
| EL | 510.0 EUR (2024) | 1 | EM Countries\EL\EL.xml bsa00_s year=2024 | 10.38 | 36.74 | 35.25-38.32 | 1.651 | **60.65** | 60.65 |
| HU | 14,069.0 HUF (2024) | 1 | EM Countries\HU\HU.xml bsa_s year=2024 | 9.58 | 1,097.23 | 1,052.61-1,144.46 | 1.627 | **1,784.68** | 4.51 |
| IE | 1,852.5 EUR (2024) | 1 | EM Countries\IE\IE.xml bunnc_s year=2024 | 5.35 | 258.75 | 248.23-269.89 | 1.631 | **422.03** | 422.03 |
| IT | 5,731.0 EUR (2025) | 2 | country_income-185 | 58.94 | 71.37 | 68.47-74.44 | 1.650 | **117.79** | 117.79 |
| LV | 11.9 EUR (2024) | 1 | EM Countries\LV\LV.xml bsamm_s year=2024 | 1.88 | 4.72 | 4.53-4.92 | 1.659 | **7.83** | 7.83 |
| LT | 114.0 EUR (2024) | 1 | EM Countries\LT\LT.xml bsa00_s year=2024 | 2.89 | 29.53 | 28.33-30.80 | 1.659 | **48.99** | 48.99 |
| LU | 193.2 EUR (2023) | 1 | EM Countries\LU\LU.xml bsacm_s year=2024 | 0.66 | 228.55 | 219.26-238.39 | 1.634 | **373.40** | 373.40 |
| MT | 35.0 EUR (2024) | 1 | EM Countries\MT\MT.xml bsa_s year=2024 | 0.56 | 46.40 | 44.51-48.40 | 1.648 | **76.45** | 76.45 |
| NL | 6,551.0 EUR (2024) | 1 | EM Countries\NL\NL.xml bsa00_s year=2024 | 17.94 | 272.91 | 261.81-284.66 | 1.625 | **443.49** | 443.49 |
| PL | 422.6 PLN (2024) | 1 | EM Countries\PL\PL.xml bsatm_s year=2024 | 36.62 | 8.63 | 8.28-9.00 | 1.626 | **14.03** | 3.26 |
| PT | 352.0 EUR (2024) | 1 | EM Countries\PT\PT.xml bsa00_s year=2024 | 10.64 | 24.73 | 23.72-25.79 | 1.639 | **40.52** | 40.52 |
| RO | 1,697.3 RON (2024) | 1 | EM Countries\RO\RO.xml bsa00_s year=2024 | 19.07 | 66.54 | 63.83-69.40 | 1.650 | **109.77** | 22.07 |
| SK | 143.8 EUR (2024) | 1 | EM Countries\SK\SK.xml bsa_s year=2024 | 5.42 | 19.82 | 19.01-20.67 | 1.618 | **32.08** | 32.08 |
| SI | 274.8 EUR (2024) | 1 | EM Countries\SI\SI.xml bsa_s year=2024 | 2.12 | 96.69 | 92.76-100.86 | 1.632 | **157.84** | 157.84 |
| ES | 2,840.0 EUR (2024) | 1 | EM Countries\ES\ES.xml bsa00_s year=2024 | 48.62 | 43.66 | 41.89-45.54 | 1.652 | **72.14** | 72.14 |
| SE | 10,916.0 SEK (2024) | 1 | EM Countries\SE\SE.xml bsamt_s year=2024 | 10.55 | 773.30 | 741.86-806.59 | 1.640 | **1,268.39** | 110.95 |

## 8. Outlay cross-checks for all 27 (each alternative over the recommended outlay, 2024 prices)

| country | EUROMOD latest | SPC admin | national other | ESSPROS | JRC EUROMOD J1.28 x12 | JRC product/printed | recipients x rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| AT | 1.0 |  |  | 0.995 | 3.046 | 1.089 | 1.31 |
| BE | 1.0 |  |  | 0.984 | 1.159 | 1.212 | 1.205 |
| BG | 1.0 |  |  | 0.835 | 3.424 | 1.225 | 1.528 |
| HR | 1.0 |  |  | 1.063 | 1.105 | 1.248 | 1.35 |
| CY | 1.0 |  |  | 0.673 | 0.496 | 0.999 |  |
| CZ | 1.56 | 1.0 |  | 0.776 | 1.713 | 1.0 | 0.892 |
| DK | 1.0 |  |  | 1.53 | 1.851 | 1.0 | 1.225 |
| EE | 1.0 |  |  | 0.698 | 3.803 | 1.007 | 1.259 |
| FI | 1.0 | 0.996 |  | 1.007 | 1.355 | 1.023 | 2.404 |
| FR | 0.876 |  | 1.0 | 2.046 | 1.065 | 1.0 | 1.161 |
| DE | 1.272 | 1.0 |  | 0.872 | 0.027 | 1.08 | 0.683 |
| EL | 1.0 | 1.031 |  | 1.031 | 0.441 | 1.001 | 0.878 |
| HU | 1.0 |  |  | 1.148 | 4.273 | 1.0 | 1.108 |
| IE | 1.0 | 0.968 |  | 1.143 | 1.082 | 0.999 | 0.74 |
| IT | 1.207 | 1.0 |  | 1.799 | 0.894 | 2.176 | 1.369 |
| LV | 1.0 | 1.161 |  | 1.005 | 2.802 | 1.004 | 11.817 |
| LT | 1.0 | 1.889 |  | 0.535 | 1.502 | 1.074 | 2.308 |
| LU | 1.0 |  |  | 1.486 | 1.458 | 1.0 | 1.239 |
| MT | 1.0 |  |  | 0.484 | 1.702 | 1.0 | 0.653 |
| NL | 1.0 |  | 1.065 | 1.942 | 0.847 | 0.999 | 0.845 |
| PL | 1.0 | 1.199 |  | 4.595 | 4.939 | 1.0 | 10.25 |
| PT | 1.0 | 0.88 |  | 1.033 | 0.933 | 1.141 | 0.93 |
| RO | 1.0 | 1.002 |  | 4.17 | 3.058 | 1.59 | 0.568 |
| SK | 1.0 | 1.0 |  | 2.395 | 3.472 | 1.059 | 0.447 |
| SI | 1.0 | 0.994 |  | 1.24 | 2.318 | 1.014 | 1.525 |
| ES | 1.0 | 1.538 |  | 1.919 | 3.643 | 1.934 | 1.875 |
| SE | 1.0 | 0.979 |  | 1.008 | 2.916 | 1.036 | 1.523 |

Spread of each alternative over the recommended (step-1 countries only): spc_admin: n=12, min 0.88, median 1.00, max 1.89, within +/-20%: 10; esspros: n=23, min 0.48, median 1.03, max 4.59, within +/-20%: 11; jrc_euromod_x12: n=23, min 0.44, median 1.85, max 4.94, within +/-20%: 5; recipients_x_rate: n=22, min 0.45, median 1.26, max 11.82, within +/-20%: 4

