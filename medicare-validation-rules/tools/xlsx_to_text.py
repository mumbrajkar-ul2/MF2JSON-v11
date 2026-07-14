#!/usr/bin/env python3
"""Deterministic converter: T-MSIS rules .xlsx -> .csv + .md (text-first for Cursor).

The .xlsx is binary and Cursor cannot read it without a script. This tool produces
text renderings (CSV for grep, Markdown for human + Cursor reading) so the searchable
copy never drifts from the binary record of truth.

Usage:
    python tools/xlsx_to_text.py rules/eligibility/source.xlsx
    python tools/xlsx_to_text.py rules/eligibility/source.xlsx --out-dir rules/eligibility

Writes <stem>... actually writes data-elements.csv and data-elements.md next to the input
(or into --out-dir). Re-run whenever source.xlsx changes (wire into a pre-commit hook / CI).

Requires: openpyxl  ->  python -m pip install openpyxl
"""
import argparse
import csv
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.stderr.write(
        "ERROR: openpyxl is required. Install with:\n    python -m pip install openpyxl\n"
    )
    sys.exit(2)


def _cell(value) -> str:
    """Normalize a cell to a single-line trimmed string."""
    if value is None:
        return ""
    return str(value).replace("\r\n", "\n").strip()


def read_rows(xlsx_path: Path):
    """Yield (sheet_title, list_of_row_values) for every non-empty row across all sheets."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            if any(c is not None and str(c).strip() != "" for c in row):
                yield ws.title, [_cell(c) for c in row]


def write_csv(rows, csv_path: Path) -> int:
    count = 0
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        for sheet, values in rows:
            # Collapse embedded newlines so each data element is one CSV row.
            writer.writerow([sheet] + [v.replace("\n", " / ") for v in values])
            count += 1
    return count


def write_md(rows, md_path: Path, source_name: str) -> None:
    with md_path.open("w", encoding="utf-8") as fh:
        fh.write(f"# Data Elements & Validation Rules (generated from `{source_name}`)\n\n")
        fh.write(
            "> GENERATED FILE — do not hand-edit. Re-run "
            "`python tools/xlsx_to_text.py <source.xlsx>` to refresh.\n\n"
        )
        current_sheet = None
        header = None
        for sheet, values in rows:
            if sheet != current_sheet:
                current_sheet = sheet
                header = None
                fh.write(f"\n## Sheet: {sheet}\n\n")
            if header is None:
                header = values
                fh.write("| " + " | ".join(header) + " |\n")
                fh.write("| " + " | ".join("---" for _ in header) + " |\n")
            else:
                # pad/truncate to header width, escape pipes and newlines for table cells
                cells = list(values) + [""] * (len(header) - len(values))
                cells = cells[: len(header)]
                cells = [c.replace("|", "\\|").replace("\n", "<br>") for c in cells]
                fh.write("| " + " | ".join(cells) + " |\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Convert T-MSIS rules xlsx to csv + md.")
    parser.add_argument("xlsx", type=Path, help="Path to source .xlsx")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: same folder as the xlsx)",
    )
    parser.add_argument(
        "--basename",
        default="data-elements",
        help="Base name for outputs (default: data-elements)",
    )
    args = parser.parse_args(argv)

    if not args.xlsx.is_file():
        sys.stderr.write(f"ERROR: not found: {args.xlsx}\n")
        return 1

    out_dir = args.out_dir or args.xlsx.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / f"{args.basename}.csv"
    md_path = out_dir / f"{args.basename}.md"

    # Materialize rows once (read_only generator is single-pass).
    rows = list(read_rows(args.xlsx))
    n = write_csv(rows, csv_path)
    write_md(rows, md_path, args.xlsx.name)

    print(f"Wrote {csv_path} ({n} rows)")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
