# Project assets

Six files. Four of them are European Union assets and are **not to be redrawn,
recoloured, cropped, or combined with anything else**: Horizon Europe grant agreement
Article 17.2 requires the emblem to remain distinct and separate and forbids modifying
it by adding other visual marks, brands or text. If a different size or format is
needed, take it from the Commission's own download centre rather than editing these.

It sits at the project root because the emblem belongs to the project, not to the UK
tool.

| file | size | what it is |
|---|---:|---|
| `EN-Funded by the EU-POS.jpg` | 4247 x 891 | **The official "Funded by the European Union" logo**, English, positive version, at print resolution, exactly as downloaded from the European Commission. The source of record. Its filename is the Commission's own. Not referenced by any artefact; kept because a print or large-format use must come from here rather than from an upscaled web copy. |
| `eu_funded.png` | 572 x 120 | The same official artwork at web resolution. **This is the file the four tools embed**, base64-inlined by `template.html` so each tool stays a single self-contained page. Verified byte-identical to what the tools carry. |
| `eu_flag.jpg` | 600 x 401 | The plain emblem, no funding statement. Unused. Kept for a context where the statement is already set in text beside it. |
| `eu_flag.png` | 180 x 120 | The same, smaller. Unused. |
| `benefits_logo.svg` | vector | The BENEFITS project logo. The tools carry their own inline copy in `template.html`. |
| `benefits_logo.png` | 126 x 71 | Raster fallback of the same. Unused. |

## Which one to use

* **A tool or a web page**: `eu_funded.png`, or the inline copy already in
  `template.html`. It carries the emblem and the funding statement together in the
  Commission's own lockup, so both Article 17.2 obligations are met by one image.
* **A document**: reference `eu_funded.png` by relative path, as `README.md` and
  `uk/docs/TECHNICAL_REPORT.md` do.
* **Print**: `EN-Funded by the EU-POS.jpg`.

## The rule that is easy to get wrong

Where the emblem appears next to any other logo, including the BENEFITS project logo,
it must be **at least as prominent**. In the tools both are rendered at 50px height and
`check_browser.py` asserts it live against the rendered page, so a layout change cannot
quietly shrink one below the other. The project logo is a project logo; it may never
stand in for the emblem, and no other visual identity may be used to signal EU support.
