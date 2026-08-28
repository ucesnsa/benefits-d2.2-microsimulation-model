# uk/docs — UK documentation

Documentation for the UK deliverable: methods and reproducibility (`METHODS.md`), validation tables, the UC take-up calibration, aggregate WEVM tables, and the bibliography (`references.bib`).

## The WEVM tables

Three CSVs, all FRS 2023-24 and all working-age benefit units:

- [`wevm_headline_2023_24.csv`](wevm_headline_2023_24.csv) — scenario-level WEVM in **GBP millions**, one column per epsilon on the 0 to 2 grid.
- [`wevm_deciles_2023_24.csv`](wevm_deciles_2023_24.csv) — **mean equivalent variation per benefit unit, in GBP per year**, by decile of equivalised baseline net income, at **epsilon = 0 only**. Per-unit means, so a column does not sum to the headline: multiply the sum by the units in one decile and divide by 1e6. The file's own header states this and carries that unit count, derived from the surface so it moves with it. The exact zero-residual decomposition in GBP millions, at every epsilon, is the one the surface carries in [`../outputs/dial_grid.json`](../outputs/dial_grid.json).
- [`wevm_takeup_sensitivity_eps1.csv`](wevm_takeup_sensitivity_eps1.csv) — the same headline at epsilon = 1 under the two UC take-up rates, the PolicyEngine default 0.55 and the calibrated 0.731, with each scenario's rank under both.

**`TECHNICAL_REPORT.md` here is the UK-tool report.** It covers this tool only. The programme-level D2.2 technical report, which covers all four tools, is the PDF at [`../../Documents/BENEFITS___D2_2_Tech_Report.pdf`](../../Documents/BENEFITS___D2_2_Tech_Report.pdf). The two share a name at different levels; this one is UK-specific.

Repository guide: [../../README.md](../../README.md).

## What is current

The current UK user guide is the PDF at [`../../Documents/USER_GUIDE_UK_D2_2.pdf`](../../Documents/USER_GUIDE_UK_D2_2.pdf).

`METHODS.md` and `QUICKSTART.md` are current.

## PDFs: not current, and how to rebuild them

`USER_GUIDE.pdf`, `METHODS.pdf` and `TECHNICAL_REPORT.pdf`, and the three `.tex` files they render, do not ship with this repository: they sit in the local-only `_superseded/` archive, which is untracked, and their prose does not match the Markdown in this directory. The Markdown is the source. The current documents are that Markdown and the PDFs in [`../../Documents/`](../../Documents/).

The build chain is **Markdown → pandoc → LaTeX → pdflatex → PDF**.

**1. pandoc**, for the `.md` → `.tex` step. Install it before attempting a rebuild, or the LaTeX you edit will drift from the Markdown that is the real source.

**2. A LaTeX distribution.** Build with `pdflatex -interaction=nonstopmode <file>.tex`, twice if the document grows a table of contents.

**3. Packages the preamble requires.** `lmodern` is the one that bites: the generated preamble loads it unconditionally, and a clean container will fail without it. On Debian or Ubuntu that is `texlive-fonts-recommended`, or `texlive-full` if you would rather not enumerate. The rest, in load order: `amsmath`, `amssymb` (pulls `amsfonts`), `iftex`, `fontenc`, `inputenc`, `textcomp`, `xcolor`, `hyperref`, `url`. Two are loaded behind `\IfFileExists` guards and are genuinely optional: `upquote` and `microtype`.

**4. Any engine works, provided you do not pass a font.** No file in this repository sets `mainfont` or `monofont`, and none carries YAML front-matter, so pandoc's template never emits the non-pdfTeX branch and every engine resolves to a portable default. Build with:

```bash
pandoc METHODS.md -s -o METHODS.tex
```

and then `pdflatex`, `xelatex` or `lualatex` as you prefer. Do **not** add `-V mainfont=...`, which binds the chain to Windows.

A distribution that installs missing packages on demand will build here and fail in a clean container, so a local success is **not** evidence that the requirement list is complete. Test any rebuild in a clean container.
