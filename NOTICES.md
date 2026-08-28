# NOTICES

Third-party software distributed with, or required by, BENEFITS Deliverable D2.2.

This repository's own code is MIT (`LICENSE`). Its documents, response surfaces and
the four HTML tools are CC BY 4.0 (`LICENSE-CC-BY-4.0`), subject to the terms of the
underlying microdata agreements. Any file that imports an engine carries that engine's
licence, whether it imports it directly or reaches it through another module in this tree:
AGPL-3.0 for the files driving PolicyEngine, EUPL-1.2 for those reaching the `euromod`
connector. A `LICENSE` file sits in each directory where such files are concentrated, and
the files that import a connector directly carry a header naming the licence and why.
Everything else is MIT. **Neither engine is redistributed here.**

## How every licence below was determined

Read on 2026-08-05 from each package's own installed metadata, in a Python 3.11
environment built from `uk/requirements.lock`, in this order of authority:

1. the SPDX `License-Expression` field, where the package declares one;
2. a short `License:` field asserting a compound expression, which carries information
   the licence text cannot (see tqdm below);
3. the licence text the package itself ships, matched on the licence's own title line;
4. the OSI trove classifier;
5. the free-text `License:` field.

Nothing here is recalled. Where a package's metadata states only "BSD" without saying
which variant, the table says so rather than choosing one. Three packages in the lock
are gated off this platform by an environment marker and could not be installed to be
read; their rows say where the reading came from instead.

One trap worth recording, because it silently produces a wrong answer: the MPL-2.0 text
names the GNU GPL, LGPL and AGPL in its secondary-licence clause and again in Exhibit B.
A substring search for a licence name therefore reports MPL-licensed packages as AGPL.
`certifi`, `fqdn`, `pathspec` and `pyzmq` all fail that way. The readings below match the
licence's own title line near the top of the text, not a mention of it anywhere in it.

## The engines, which are NOT redistributed

Both engines are obtained and installed by the reader. This repository ships the code
that drives them, the aggregate results, and the documentation.

| component | version | licence | how it was established |
|---|---|---|---|
| PolicyEngine UK (`policyengine-uk`) | 2.45.4 | **AGPL-3.0** | `License-Expression: AGPL-3.0` in the installed METADATA, the classifier `GNU Affero General Public License v3`, and the bundled `LICENSE`, which is the FSF text of the GNU Affero General Public License v3, 19 November 2007 |
| PolicyEngine Core (`policyengine-core`) | 3.23.6 | **AGPL-3.0** | the same classifier and the same bundled FSF text. Its `License:` field is a URL to the FSF's AGPL-3.0 page rather than a licence name, so the classifier and the shipped text are what establish it |
| EUROMOD engine | v3.8.6 | see the JRC model licence | distributed by the European Commission's Joint Research Centre under the EUROMOD model licence, which accompanies the release (`EUROMOD_model_licence_J12.0+.txt`). Not redistributed here |
| `euromod` connector | 0.2.18 | **EUPL-1.2** | see the note immediately below |

### The connector is wrong about its own licence

The `euromod` connector's package metadata carries
`Classifier: License :: Other/Proprietary License`. **That classifier is wrong about its
own package.** The same metadata's `License:` field inlines the full text of the European
Union Public Licence v1.2, and the wheel ships that text again as `LICENSE.txt` together
with a `NOTICE.txt` reading "This program is free software: you can redistribute it
and/or modify it under the terms of the European Union Public Licence, either version 1.2
of the License, or (at your option) any later version", under "Copyright (C) European
Union 2024". The true licence is therefore **EUPL-1.2**, and that is what is recorded
here and what the four `LICENSE` files under `europe/` carry. A tool that reads only the
classifier will report this dependency as proprietary; it is not.

The connector's own `NOTICE.txt` further records that it builds on pandas (BSD-3-Clause),
numpy (BSD-3-Clause), pythonnet (MIT), ctypes (MIT or PSF), the Python standard library
(PSF), and the EUROMOD model itself, which the European Union publishes under CC BY 4.0.

## Licences requiring care

Nine of the dependencies below are not the plain permissive licence a quick reading
gives. Each is recorded at its true licence in the table.

| package | licence | why it is not what it looks like |
|---|---|---|
| `tqdm` | MPL-2.0 AND MIT | not a permissive package. Its own metadata declares the compound expression: the body of tqdm is MPL-2.0, and only tqdm/_tqdm.py, README.rst and .gitignore are MIT. The single LICENCE file it ships reproduces the MIT text, so reading that file alone reports it as MIT |
| `numpy` | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | a multi-licence aggregate, not plain BSD. The expression is numpy's own SPDX License-Expression and covers the vendored components it distributes alongside its BSD-3-Clause core |
| `pyzmq` | Apache-2.0 AND BSD-3-Clause AND MPL-2.0 | pyzmq itself is BSD-3-Clause; the wheel also carries libzmq (MPL-2.0) and vendored tornado (Apache-2.0), and ships all three texts |
| `certifi` | MPL-2.0 | the certificate bundle is MPL-2.0; the file it ships is the ca-bundle attribution notice rather than the licence text |
| `fqdn` | MPL-2.0 | copyleft, not permissive |
| `pathspec` | MPL-2.0 | copyleft, not permissive |
| `packaging` | Apache-2.0 OR BSD-2-Clause | dual-licensed at the recipient's choice |
| `greenlet` | MIT AND PSF-2.0 | the package's own SPDX License-Expression |
| `psycopg2-binary` | LGPL-3.0-or-later, with an OpenSSL linking exception | shipped LICENSE: "either version 3 of the License, or (at your option) any later version", plus a special exception permitting linking with OpenSSL |

## Every dependency in `uk/requirements.lock`

169 pinned requirements, hash-locked for Python 3.11 on Windows and macOS.
The two PolicyEngine rows are the engine itself and appear above as well.
Rows with an environment marker install only where the marker holds.

| package | version | licence | marker |
|---|---|---|---|
| `annotated-doc` | 0.0.4 | MIT |  |
| `annotated-types` | 0.7.0 | MIT |  |
| `anyio` | 4.12.1 | MIT |  |
| `appnope` | 0.1.4 | BSD (variant not stated) | sys_platform == 'darwin' |
| `argon2-cffi` | 25.1.0 | MIT |  |
| `argon2-cffi-bindings` | 25.1.0 | MIT |  |
| `arrow` | 1.4.0 | Apache-2.0 |  |
| `asttokens` | 3.0.1 | Apache-2.0 |  |
| `async-lru` | 2.2.0 | MIT |  |
| `attrs` | 25.4.0 | MIT |  |
| `babel` | 2.18.0 | BSD-3-Clause |  |
| `beautifulsoup4` | 4.14.3 | MIT |  |
| `black` | 26.1.0 | MIT |  |
| `bleach` | 6.3.0 | MIT |  |
| `blosc2` | 4.5.1 | BSD-3-Clause |  |
| `certifi` | 2026.2.25 | MPL-2.0 |  |
| `cffi` | 2.0.0 | MIT |  |
| `charset-normalizer` | 3.4.4 | MIT |  |
| `click` | 8.3.1 | BSD-3-Clause |  |
| `colorama` | 0.4.6 | BSD-3-Clause | sys_platform == 'win32' |
| `comm` | 0.2.3 | BSD-3-Clause |  |
| `contourpy` | 1.3.3 | BSD-3-Clause |  |
| `cycler` | 0.12.1 | BSD-3-Clause |  |
| `debugpy` | 1.8.20 | MIT |  |
| `decorator` | 5.2.1 | BSD-2-Clause |  |
| `defusedxml` | 0.7.1 | PSF-2.0 |  |
| `dpath` | 2.2.0 | MIT |  |
| `et-xmlfile` | 2.0.0 | MIT |  |
| `executing` | 2.2.1 | MIT |  |
| `fastjsonschema` | 2.21.2 | BSD-3-Clause |  |
| `filelock` | 3.24.3 | MIT |  |
| `fonttools` | 4.61.1 | MIT |  |
| `fqdn` | 1.5.1 | MPL-2.0 |  |
| `fsspec` | 2026.2.0 | BSD-3-Clause |  |
| `greenlet` | 3.5.3 | MIT AND PSF-2.0 | platform_machine == 'AMD64' or ... |
| `h11` | 0.16.0 | MIT |  |
| `h5py` | 3.15.1 | BSD-3-Clause |  |
| `hf-xet` | 1.3.2 | Apache-2.0 | platform_machine == 'AMD64' or ... |
| `httpcore` | 1.0.9 | BSD-3-Clause |  |
| `httpx` | 0.28.1 | BSD-3-Clause |  |
| `huggingface-hub` | 1.5.0 | Apache-2.0 |  |
| `idna` | 3.11 | BSD-3-Clause |  |
| `iniconfig` | 2.3.0 | MIT |  |
| `ipykernel` | 7.2.0 | BSD-3-Clause |  |
| `ipython` | 8.38.0 | BSD-3-Clause |  |
| `ipywidgets` | 8.1.8 | BSD-3-Clause |  |
| `isoduration` | 20.11.0 | ISC |  |
| `isort` | 8.0.1 | MIT |  |
| `jedi` | 0.19.2 | MIT |  |
| `jinja2` | 3.1.6 | BSD-3-Clause |  |
| `json5` | 0.13.0 | Apache-2.0 |  |
| `jsonpickle` | 4.1.1 | BSD-3-Clause |  |
| `jsonpointer` | 3.0.0 | BSD-2-Clause |  |
| `jsonschema` | 4.26.0 | MIT |  |
| `jsonschema-specifications` | 2025.9.1 | MIT |  |
| `jupyter` | 1.1.1 | BSD-3-Clause |  |
| `jupyter-client` | 8.8.0 | BSD-3-Clause |  |
| `jupyter-console` | 6.6.3 | BSD-3-Clause |  |
| `jupyter-core` | 5.9.1 | BSD-3-Clause |  |
| `jupyter-events` | 0.12.0 | BSD-3-Clause |  |
| `jupyter-lsp` | 2.3.0 | BSD-3-Clause |  |
| `jupyter-server` | 2.17.0 | BSD-3-Clause |  |
| `jupyter-server-terminals` | 0.5.4 | BSD-3-Clause |  |
| `jupyterlab` | 4.5.5 | BSD-3-Clause |  |
| `jupyterlab-pygments` | 0.3.0 | BSD-3-Clause |  |
| `jupyterlab-server` | 2.28.0 | BSD-3-Clause |  |
| `jupyterlab-widgets` | 3.0.16 | ISC |  |
| `kiwisolver` | 1.4.9 | BSD-3-Clause |  |
| `lark` | 1.3.1 | MIT |  |
| `linkify-it-py` | 2.1.0 | MIT |  |
| `markdown-it-py` | 4.0.0 | MIT |  |
| `markupsafe` | 3.0.3 | BSD-3-Clause |  |
| `matplotlib` | 3.10.8 | MIT |  |
| `matplotlib-inline` | 0.2.1 | BSD-3-Clause |  |
| `mdit-py-plugins` | 0.6.1 | MIT |  |
| `mdurl` | 0.1.2 | MIT |  |
| `microdf-python` | 1.2.2 | MIT |  |
| `mistune` | 3.2.0 | BSD-3-Clause |  |
| `msgpack` | 1.2.1 | Apache-2.0 |  |
| `mypy-extensions` | 1.1.0 | MIT |  |
| `nbclient` | 0.10.4 | BSD-3-Clause |  |
| `nbconvert` | 7.17.0 | BSD-3-Clause |  |
| `nbformat` | 5.10.4 | BSD-3-Clause |  |
| `nbstripout` | 0.9.1 | MIT |  |
| `ndindex` | 1.10.1 | MIT |  |
| `nest-asyncio` | 1.6.0 | BSD-2-Clause |  |
| `networkx` | 3.6.1 | BSD-3-Clause |  |
| `notebook` | 7.5.4 | BSD-3-Clause |  |
| `notebook-shim` | 0.2.4 | BSD-3-Clause |  |
| `numexpr` | 2.14.1 | MIT |  |
| `numpy` | 2.4.2 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |  |
| `openpyxl` | 3.1.5 | MIT |  |
| `overrides` | 7.7.0 | Apache-2.0 | python_full_version < '3.12' |
| `packaging` | 26.0 | Apache-2.0 OR BSD-2-Clause |  |
| `pandas` | 3.0.1 | BSD-3-Clause |  |
| `pandocfilters` | 1.5.1 | BSD-3-Clause |  |
| `parso` | 0.8.6 | MIT |  |
| `pathspec` | 1.0.4 | MPL-2.0 |  |
| `pexpect` | 4.9.0 | ISC | sys_platform != 'emscripten' and sys_platform != 'win32' |
| `pillow` | 12.1.1 | MIT-CMU |  |
| `platformdirs` | 4.9.2 | MIT |  |
| `plotext` | 5.3.2 | MIT |  |
| `plotly` | 5.24.1 | MIT |  |
| `pluggy` | 1.6.0 | MIT |  |
| `polars` | 1.38.1 | MIT |  |
| `polars-runtime-32` | 1.38.1 | MIT |  |
| `policyengine-core` | 3.23.6 | AGPL-3.0 |  |
| `policyengine-uk` | 2.45.4 | AGPL-3.0 |  |
| `prometheus-client` | 0.24.1 | Apache-2.0 AND BSD-2-Clause |  |
| `prompt-toolkit` | 3.0.52 | BSD-3-Clause |  |
| `psutil` | 6.1.1 | BSD-3-Clause |  |
| `psycopg2-binary` | 2.9.11 | LGPL-3.0-or-later, with an OpenSSL linking exception |  |
| `ptyprocess` | 0.7.0 | ISC | os_name != 'nt' or ... |
| `pure-eval` | 0.2.3 | MIT |  |
| `py-cpuinfo` | 9.0.0 | MIT |  |
| `pyarrow` | 23.0.1 | Apache-2.0 |  |
| `pycparser` | 3.0 | BSD-3-Clause | implementation_name != 'PyPy' |
| `pydantic` | 2.12.5 | MIT |  |
| `pydantic-core` | 2.41.5 | MIT |  |
| `pygments` | 2.19.2 | BSD-2-Clause |  |
| `pyparsing` | 3.3.2 | MIT |  |
| `pytest` | 8.4.2 | MIT |  |
| `python-dateutil` | 2.9.0.post0 | BSD-3-Clause |  |
| `python-dotenv` | 1.2.1 | BSD-3-Clause |  |
| `python-json-logger` | 4.0.0 | BSD-2-Clause |  |
| `pytokens` | 0.4.1 | MIT |  |
| `pyvis` | 0.3.2 | BSD-3-Clause |  |
| `pywinpty` | 3.0.5 | MIT | os_name == 'nt' |
| `pyyaml` | 6.0.3 | MIT |  |
| `pyzmq` | 27.1.0 | Apache-2.0 AND BSD-3-Clause AND MPL-2.0 |  |
| `referencing` | 0.37.0 | MIT |  |
| `requests` | 2.32.5 | Apache-2.0 |  |
| `rfc3339-validator` | 0.1.4 | MIT |  |
| `rfc3986-validator` | 0.1.1 | MIT |  |
| `rfc3987-syntax` | 1.1.0 | MIT |  |
| `rich` | 14.3.3 | MIT |  |
| `rpds-py` | 0.30.0 | MIT |  |
| `seaborn` | 0.13.2 | BSD-3-Clause |  |
| `send2trash` | 2.1.0 | BSD-3-Clause |  |
| `shellingham` | 1.5.4 | ISC |  |
| `six` | 1.17.0 | MIT |  |
| `sortedcontainers` | 2.4.0 | Apache-2.0 |  |
| `soupsieve` | 2.8.3 | MIT |  |
| `sqlalchemy` | 2.0.47 | MIT |  |
| `stack-data` | 0.6.3 | MIT |  |
| `standard-imghdr` | 3.13.0 | PSF-2.0 |  |
| `tables` | 3.11.1 | BSD-3-Clause |  |
| `tenacity` | 9.1.4 | Apache-2.0 |  |
| `terminado` | 0.18.1 | BSD-2-Clause |  |
| `textual` | 8.2.7 | MIT |  |
| `textual-plotext` | 1.0.1 | MIT |  |
| `threadpoolctl` | 3.6.0 | BSD-3-Clause | platform_machine != 'wasm32' |
| `tinycss2` | 1.4.0 | BSD-3-Clause |  |
| `tornado` | 6.5.4 | Apache-2.0 |  |
| `tqdm` | 4.67.3 | MPL-2.0 AND MIT |  |
| `traitlets` | 5.14.3 | BSD-3-Clause |  |
| `typer` | 0.24.1 | MIT |  |
| `typing-extensions` | 4.15.0 | PSF-2.0 |  |
| `typing-inspection` | 0.4.2 | MIT |  |
| `tzdata` | 2025.3 | Apache-2.0 |  |
| `uc-micro-py` | 2.0.0 | MIT |  |
| `uri-template` | 1.3.0 | MIT |  |
| `urllib3` | 2.6.3 | MIT |  |
| `wcwidth` | 0.6.0 | MIT |  |
| `webcolors` | 25.10.0 | BSD-3-Clause |  |
| `webencodings` | 0.5.1 | BSD (variant not stated) |  |
| `websocket-client` | 1.9.0 | Apache-2.0 |  |
| `wheel` | 0.47.0 | MIT |  |
| `widgetsnbextension` | 4.0.15 | BSD-3-Clause |  |

### Tally

| licence | packages |
|---|---:|
| MIT | 71 |
| BSD-3-Clause | 55 |
| Apache-2.0 | 14 |
| BSD-2-Clause | 6 |
| ISC | 5 |
| MPL-2.0 | 3 |
| PSF-2.0 | 3 |
| AGPL-3.0 | 2 |
| BSD (variant not stated) | 2 |
| Apache-2.0 AND BSD-2-Clause | 1 |
| Apache-2.0 AND BSD-3-Clause AND MPL-2.0 | 1 |
| Apache-2.0 OR BSD-2-Clause | 1 |
| BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 1 |
| LGPL-3.0-or-later, with an OpenSSL linking exception | 1 |
| MIT AND PSF-2.0 | 1 |
| MIT-CMU | 1 |
| MPL-2.0 AND MIT | 1 |

## Assets

The European Union emblem and the "Funded by the European Union" lockup in `assets/`
are official European Commission artwork, used under the Horizon Europe grant
agreement's Article 17 visibility obligations. `assets/README.md` records which files
are the official assets and that none may be redrawn, recoloured, cropped or combined.
They are not covered by this repository's own licences.

