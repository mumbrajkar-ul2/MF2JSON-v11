#!/usr/bin/env python3
"""Extract Appendix G ISO 639-2 language codes into preferred-language.csv.

Source: T-MSIS Data Dictionary Appendices (Appendix G: ISO 639 Language Codes Reference).
Default input: authoritative-source-registry/Medicare Documents/2b-TMSIS_V2.4.0_Appendix.docx

Usage:
    python tools/appendix_g_to_preferred_language.py
    python tools/appendix_g_to_preferred_language.py --docx path/to/appendix.docx
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCX = Path(
    r"authoritative-source-registry/Medicare Documents/2b-TMSIS_V2.4.0_Appendix.docx"
).resolve()
if not DEFAULT_DOCX.is_file():
    DEFAULT_DOCX = (
        REPO_ROOT
        / "authoritative-source-registry"
        / "Medicare Documents"
        / "2b-TMSIS_V2.4.0_Appendix.docx"
    )
OUTPUT_CSV = REPO_ROOT / "rules" / "eligibility" / "value-lists" / "preferred-language.csv"

T_MSIS_DE = "ELG.003.046"
LIST_NAME = "Preferred Language Code List"
CODE_RE = re.compile(r"^[a-z]{3}$")


def extract_appendix_g_pairs(docx_path: Path) -> list[tuple[str, str]]:
    with zipfile.ZipFile(docx_path) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    texts = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml)

    start = None
    for i, token in enumerate(texts):
        if token == "ISO 639-2 Code" and i > 500:
            start = i
            break
    if start is None:
        raise ValueError(f"Appendix G table not found in {docx_path}")

    pairs: list[tuple[str, str]] = []
    i = start + 4  # skip duplicated header: Code, Language, Code, Language
    while i < len(texts) - 1:
        code, description = texts[i], texts[i + 1]
        if code.startswith("Appendix H"):
            break
        if CODE_RE.fullmatch(code):
            pairs.append((code.upper(), description.strip()))
            i += 2
            continue
        if code.startswith("Appendix "):
            break
        i += 1

    if not pairs:
        raise ValueError(f"No language codes extracted from {docx_path}")

    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for code, description in pairs:
        if code in seen:
            raise ValueError(f"Duplicate ISO 639-2 code in Appendix G: {code}")
        seen.add(code)
        unique.append((code, description))
    return unique


def write_csv(pairs: list[tuple[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "code",
                "description",
                "t_msis_data_element",
                "valid_value_list_name",
                "status",
            ]
        )
        for code, description in pairs:
            writer.writerow([code, description, T_MSIS_DE, LIST_NAME, "CONFIRMED"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docx", type=Path, default=DEFAULT_DOCX)
    parser.add_argument("--output", type=Path, default=OUTPUT_CSV)
    args = parser.parse_args()

    if not args.docx.is_file():
        sys.stderr.write(f"ERROR: docx not found: {args.docx}\n")
        return 1

    pairs = extract_appendix_g_pairs(args.docx)
    write_csv(pairs, args.output)
    print(f"Wrote {len(pairs)} codes to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
