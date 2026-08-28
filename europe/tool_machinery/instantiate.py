#!/usr/bin/env python3
"""Location-independent instantiator: template.html + a COUNTRY block -> a finished tool.

Python port of instantiate.ps1 with identical semantics. This is the ONLY sanctioned
way to produce a country tool. Never rewrite the tool; only swap the COUNTRY block.

BYTES, NOT TEXT, THROUGHOUT. This used to read and write through Path.read_text /
write_text, which decodes to str and re-encodes on write, translating every LF in the
template to CRLF on Windows and leaving it alone on macOS and Linux. The same template
and the same block therefore produced two different files on the two platforms, and the
masked-block hash that proves all four tools share one template differed by operating
system rather than by content. check_drift.py normalises line endings before comparing,
which hid it. Reading and writing bytes means the output is a byte-for-byte splice of
two files that are themselves bytes on disk, so the result depends on the inputs and
nothing else.

Usage:  python3 instantiate.py <country_json> <out_path>
"""

import json
import sys
from pathlib import Path

PLACEHOLDER = b"__COUNTRY_JSON__"


def main(country_json, out_path):
    here = Path(__file__).resolve().parent
    template = (here / "template.html").read_bytes()
    block = Path(country_json).read_bytes()
    json.loads(block.decode("utf-8"))  # fail fast if the COUNTRY block is not valid JSON
    if template.count(PLACEHOLDER) != 1:
        raise SystemExit(f"expected exactly one {PLACEHOLDER.decode()} in template.html, "
                         f"found {template.count(PLACEHOLDER)}")
    out = template.replace(PLACEHOLDER, block)
    if PLACEHOLDER in out:
        raise SystemExit("placeholder not fully replaced")
    Path(out_path).write_bytes(out)  # UTF-8, no BOM, line endings exactly as the inputs
    print(f"wrote {Path(out_path).name} : {len(out)} bytes")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__.strip())
    main(sys.argv[1], sys.argv[2])
