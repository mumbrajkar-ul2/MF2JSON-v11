#!/usr/bin/env python3
"""Align T-MSIS data-element Size / length coding rules to a target Java VO.

Produces a *new* data-elements.csv + data-elements.md overlay for MES→CMdS
integration specs. Does **not** modify the T-MSIS record-of-truth files under
rules/eligibility/ (those remain generated from source.xlsx).

Usage (from medicare-validation-rules root):

    python tools/align_data_elements_to_vo.py \\
        --vo ../integrations/mes-cmds-member-eligibility/target/MemberEligibilityVO.md \\
        --base rules/eligibility/data-elements.csv \\
        --out-dir rules/eligibility

Length phrases in Coding Requirements are rewritten to match the VO @Size(max).
FLF Start/Stop positions are left unchanged (T-MSIS file-layout provenance).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

# CMdS MemberEligibilityVO attribute -> T-MSIS System DE Number.
# Research-mapped rules plus clear semantic counterparts used at the MES→CMdS boundary.
DEFAULT_VO_TO_DE: dict[str, str] = {
    "gender": "ELG.002.023",
    "race": "ELG.016.213",
    "languageCode": "ELG.003.046",
    "diabilityType": "ELG.017.224",
    "categoryOfEligibility": "ELG.005.087",
    "eligibilityTerminationReasonCode": "ELG.005.095",
    "levelOfCare": "ELG.005.088",
    "maritalStatus": "ELG.003.034",
    "veteransIndicator": "ELG.003.039",
    "primaryLanguageEnglishProficiencyCode": "ELG.003.045",
    "immigrantAdmissionStatus": "ELG.003.042",
    "ssn": "ELG.003.036",
    "medicareIdNumber": "ELG.003.051",
    "memberFirstName": "ELG.002.020",
    "memberLastName": "ELG.002.021",
    "memberMiddleName": "ELG.002.022",
    "mailingAdressLine1": "ELG.004.066",
    "mailingAddressLine2": "ELG.004.067",
    "mailingAddressCity": "ELG.004.069",
    "mailingState": "ELG.004.070",
    "memberContactNumber": "ELG.004.073",
    "geoCountyCode": "ELG.004.072",
    "residenceAdressLine1": "ELG.004.066",
    "residenceAddressLine2": "ELG.004.067",
    "residenceAddressCity": "ELG.004.069",
    "residenceState": "ELG.004.070",
}


def parse_vo_sizes(text: str) -> dict[str, int]:
    """Return VO field name -> @Size(max=N) for fields that declare Size."""
    sizes: dict[str, int] = {}
    cur: int | None = None
    pending = False
    for line in text.splitlines():
        m = re.search(r"@Size\(max\s*=\s*(\d+)\)", line)
        if m:
            cur = int(m.group(1))
            pending = True
            continue
        m = re.search(r"private\s+[\w.<>,\s]+\s+(\w+)\s*;", line)
        if m and pending and cur is not None:
            sizes[m.group(1)] = cur
            pending = False
            cur = None
        elif m:
            pending = False
            cur = None
    return sizes


def parse_size_token(size: str) -> tuple[str, int] | None:
    """Parse Size column like X(30) or 9(8) -> (prefix, length)."""
    m = re.fullmatch(r"([X9A])\((\d+)\)", (size or "").strip())
    if not m:
        return None
    return m.group(1), int(m.group(2))


def _pluralize_unit(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def rewrite_coding_length(coding: str, old_len: int, new_len: int) -> str:
    """Rewrite common T-MSIS length phrases from old_len to new_len."""
    if not coding or old_len == new_len:
        return coding

    out = coding
    new_chars = _pluralize_unit(new_len, "character", "characters")
    new_digits = _pluralize_unit(new_len, "digit", "digits")

    # "N character(s)" / "N character(s) or less"
    out = re.sub(
        rf"\b{old_len} characters?( or less)?\b",
        lambda m: f"{new_len} {new_chars}{m.group(1) or ''}",
        out,
    )
    out = re.sub(
        rf"\b{old_len}-character\b",
        f"{new_len}-character",
        out,
    )
    out = re.sub(
        rf"\b{old_len}-digit\b",
        f"{new_len}-digit",
        out,
    )
    out = re.sub(
        rf"\b{old_len} digits?\b",
        f"{new_len} {new_digits}",
        out,
    )

    # Expanding a formerly fixed single-character free-text field → max length.
    if old_len == 1 and new_len > 1:
        out = re.sub(
            rf"\bValue must be {new_len} characters\b(?! or less)",
            f"Value must be {new_len} characters or less",
            out,
            count=1,
        )

    return out


def resolve_de_targets(
    vo_sizes: dict[str, int],
    vo_to_de: dict[str, str],
) -> dict[str, tuple[int, list[str]]]:
    """Map System DE Number -> (target_len, [vo attributes]).

    When multiple VO fields map to one DE, use the minimum @Size(max) so the
    rule never exceeds any mapped VO constraint.
    """
    targets: dict[str, tuple[int, list[str]]] = {}
    for attr, de in vo_to_de.items():
        if attr not in vo_sizes:
            continue
        vlen = vo_sizes[attr]
        if de not in targets:
            targets[de] = (vlen, [attr])
        else:
            cur_len, attrs = targets[de]
            attrs = attrs + [attr]
            targets[de] = (min(cur_len, vlen), attrs)
    return targets


def write_md_from_csv(csv_path: Path, md_path: Path, banner: str) -> None:
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        rows = list(reader)
    if not rows:
        raise SystemExit(f"ERROR: empty CSV: {csv_path}")

    # First column is sheet name (from xlsx_to_text).
    with md_path.open("w", encoding="utf-8") as fh:
        fh.write(banner)
        current_sheet = None
        header: list[str] | None = None
        for row in rows:
            if not row:
                continue
            sheet, values = row[0], row[1:]
            if sheet != current_sheet:
                current_sheet = sheet
                header = None
                fh.write(f"\n## Sheet: {sheet}\n\n")
            if header is None:
                header = values
                fh.write("| " + " | ".join(header) + " |\n")
                fh.write("| " + " | ".join("---" for _ in header) + " |\n")
            else:
                cells = list(values) + [""] * (len(header) - len(values))
                cells = cells[: len(header)]
                cells = [c.replace("|", "\\|").replace("\n", "<br>") for c in cells]
                fh.write("| " + " | ".join(cells) + " |\n")


def write_changelog(path: Path, changes: list[dict], vo_path: Path, base_path: Path) -> None:
    lines = [
        "# VO-aligned data-elements changelog",
        "",
        "Generated by `tools/align_data_elements_to_vo.py`.",
        "",
        f"- Base: `{base_path.as_posix()}` (T-MSIS dictionary text rendering)",
        f"- VO: `{vo_path.as_posix()}`",
        "",
        "Size and Coding Requirements length phrases were rewritten to match",
        "`@Size(max=N)` on corresponding CMdS VO fields. FLF Start/Stop positions",
        "remain the T-MSIS dictionary values (not cascaded).",
        "",
        "| System DE Number | Data Element | T-MSIS Size | VO-aligned Size | VO field(s) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for c in changes:
        lines.append(
            f"| {c['de']} | {c['name']} | {c['old_size']} | {c['new_size']} | "
            f"{', '.join(c['vo_fields'])} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This overlay minimizes **length-mismatch** gaps in Integration Specs.",
            "- Confirmed VVL member code widths may still exceed VO `@Size` (e.g. Race,",
            "  Marital Status, Level of Care). Those remain separate normalization / VVL gaps.",
            "- Do not treat this overlay as the federal T-MSIS record of truth; cite",
            "  `rules/eligibility/data-elements.*` for CMS dictionary sizes.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Align data-element Size rules to a target Java VO @Size(max)."
    )
    parser.add_argument(
        "--vo",
        type=Path,
        required=True,
        help="Path to target VO markdown (e.g. MemberEligibilityVO.md)",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("rules/eligibility/data-elements.csv"),
        help="Base T-MSIS data-elements.csv (default: rules/eligibility/data-elements.csv)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("rules/eligibility"),
        help="Output directory for aligned csv/md (default: rules/eligibility)",
    )
    args = parser.parse_args(argv)

    if not args.vo.is_file():
        sys.stderr.write(f"ERROR: VO not found: {args.vo}\n")
        return 1
    if not args.base.is_file():
        sys.stderr.write(f"ERROR: base CSV not found: {args.base}\n")
        return 1

    vo_sizes = parse_vo_sizes(args.vo.read_text(encoding="utf-8"))
    targets = resolve_de_targets(vo_sizes, DEFAULT_VO_TO_DE)
    if not targets:
        sys.stderr.write("ERROR: no VO @Size fields matched the DE map\n")
        return 1

    with args.base.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        if not fieldnames or "System DE Number" not in fieldnames:
            sys.stderr.write("ERROR: base CSV missing System DE Number column\n")
            return 1
        rows = list(reader)

    changes: list[dict] = []
    for row in rows:
        de = row.get("System DE Number", "")
        if de not in targets:
            continue
        new_len, vo_fields = targets[de]
        parsed = parse_size_token(row.get("Size", ""))
        if not parsed:
            sys.stderr.write(f"WARNING: skip {de}: unparseable Size {row.get('Size')!r}\n")
            continue
        prefix, old_len = parsed
        if old_len == new_len:
            continue
        old_size = row["Size"]
        row["Size"] = f"{prefix}({new_len})"
        row["Coding Requirements"] = rewrite_coding_length(
            row.get("Coding Requirements", ""), old_len, new_len
        )
        changes.append(
            {
                "de": de,
                "name": row.get("Data Element Name Text", ""),
                "old_size": old_size,
                "new_size": row["Size"],
                "vo_fields": vo_fields,
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.out_dir / "data-elements.csv"
    md_path = args.out_dir / "data-elements.md"
    log_path = args.out_dir / "LENGTH_ALIGNMENT_CHANGELOG.md"
    # Avoid overwriting the domain README when writing into rules/eligibility/
    readme_path = (
        None
        if (args.out_dir / "value-lists").is_dir()
        else args.out_dir / "README.md"
    )

    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    banner = (
        "# Data Elements & Validation Rules (VO-aligned overlay)\n\n"
        "> GENERATED FILE — do not hand-edit. Re-run "
        "`python tools/align_data_elements_to_vo.py` to refresh.\n\n"
        "> Derived from T-MSIS `rules/eligibility/data-elements.csv` with **Size** / "
        "length coding phrases aligned to CMdS `MemberEligibilityVO` `@Size(max)`.\n"
        "> FLF positions remain T-MSIS dictionary values. See `LENGTH_ALIGNMENT_CHANGELOG.md`.\n"
    )
    write_md_from_csv(csv_path, md_path, banner)
    write_changelog(log_path, changes, args.vo, args.base)

    if readme_path is not None:
        readme_path.write_text(
            "\n".join(
                [
                    "# VO-aligned eligibility data elements",
                    "",
                    "T-MSIS eligibility data-element rules with **field length**",
                    "(`Size` + Coding Requirements length phrases) matched to",
                    "CMdS `MemberEligibilityVO` `@Size(max=N)` constraints.",
                    "",
                    "## Regenerate",
                    "",
                    "```bash",
                    "python tools/align_data_elements_to_vo.py \\",
                    "  --vo ../integrations/mes-cmds-member-eligibility/target/MemberEligibilityVO.md \\",
                    "  --base <fresh-tmsis-data-elements.csv> \\",
                    "  --out-dir rules/eligibility",
                    "```",
                    "",
                    "See `LENGTH_ALIGNMENT_CHANGELOG.md` for the DE rows that differ from T-MSIS.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    print(f"Wrote {csv_path} ({len(rows)} data rows + header)")
    print(f"Wrote {md_path}")
    print(f"Wrote {log_path} ({len(changes)} Size alignments)")
    if readme_path is not None:
        print(f"Wrote {readme_path}")
    for c in changes:
        print(f"  {c['de']}: {c['old_size']} -> {c['new_size']} ({', '.join(c['vo_fields'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
