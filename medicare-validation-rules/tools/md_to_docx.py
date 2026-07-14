#!/usr/bin/env python3
"""Convert an Integration Specification (.md) to Microsoft Word (.docx).

Markdown remains the canonical, version-controlled spec. Run this tool after
regenerating the spec when stakeholders need a Word deliverable for review.

Usage:
    python tools/md_to_docx.py path/to/Integration_Spec.md
    python tools/md_to_docx.py path/to/Integration_Spec.md -o path/to/output.docx
    python tools/md_to_docx.py path/to/Integration_Spec.md --reference-doc templates/reference.docx

Requires: Pandoc on PATH — https://pandoc.org/installing.html
    Windows: winget install --id JohnMacFarlane.Pandoc
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def find_pandoc() -> str | None:
    return shutil.which("pandoc")


def convert(
    md_path: Path,
    docx_path: Path,
    reference_doc: Path | None = None,
) -> None:
    pandoc = find_pandoc()
    if pandoc is None:
        sys.stderr.write(
            "ERROR: pandoc is not on PATH.\n"
            "Install Pandoc, then retry:\n"
            "  Windows: winget install --id JohnMacFarlane.Pandoc\n"
            "  macOS:   brew install pandoc\n"
            "  Linux:   see https://pandoc.org/installing.html\n"
        )
        raise SystemExit(2)

    cmd = [
        pandoc,
        str(md_path),
        "-f",
        "markdown-yaml_metadata_block",
        "-t",
        "docx",
        "-o",
        str(docx_path),
        "--standalone",
        "--wrap=none",
    ]
    if reference_doc is not None:
        cmd.extend(["--reference-doc", str(reference_doc)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout or "pandoc failed\n")
        raise SystemExit(result.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert Integration Specification Markdown to Word (.docx) via Pandoc."
    )
    parser.add_argument("markdown", type=Path, help="Path to the source .md file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .docx path (default: same name as input, .docx extension)",
    )
    parser.add_argument(
        "--reference-doc",
        type=Path,
        default=None,
        help="Optional Pandoc reference .docx for Word styling (fonts, headings)",
    )
    args = parser.parse_args(argv)

    md_path = args.markdown.resolve()
    if not md_path.is_file():
        sys.stderr.write(f"ERROR: not found: {md_path}\n")
        return 1

    docx_path = (args.output or md_path.with_suffix(".docx")).resolve()
    docx_path.parent.mkdir(parents=True, exist_ok=True)

    if args.reference_doc is not None:
        ref = args.reference_doc.resolve()
        if not ref.is_file():
            sys.stderr.write(f"ERROR: reference doc not found: {ref}\n")
            return 1
    else:
        ref = None

    convert(md_path, docx_path, ref)
    print(f"Wrote {docx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
