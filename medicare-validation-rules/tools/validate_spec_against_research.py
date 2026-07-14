#!/usr/bin/env python3
"""Validate Integration Specification Markdown against research YAML.

Ensures the Writer did not add field mappings, VVL codes, or GAP IDs beyond research.

Usage:
    python tools/validate_spec_against_research.py research.yaml spec.md

Exits 0 on success, 1 on validation failure.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

GAP_PATTERN = re.compile(r"\bGAP-\d{2}\b")
ASM_PATTERN = re.compile(r"\bASM-\d{2}\b")
# Table rows: | code | ... or first column after leading pipe
TABLE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|", re.MULTILINE)
# COBOL-style field names in spec (uppercase with hyphens)
MMIS_FIELD = re.compile(r"\b[A-Z][A-Z0-9-]{2,}\b")


def extract_section(text: str, heading_pattern: str) -> str:
    """Return text from heading until next ## heading of same or higher level."""
    match = re.search(heading_pattern, text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return ""
    start = match.end()
    rest = text[start:]
    next_heading = re.search(r"\n##\s+\d+\.", rest)
    if next_heading:
        return rest[: next_heading.start()]
    next_major = re.search(r"\n#\s+", rest)
    if next_major:
        return rest[: next_major.start()]
    return rest


def extract_section3(text: str) -> str:
    return extract_section(text, r"^##\s+3\.\s+")


def extract_section2_2(text: str) -> str:
    block = extract_section(text, r"^##\s+2\.\s+")
    sub = re.search(
        r"^###?\s+\*?\*?2\.2\b.*?(?=^###?\s+\*?\*?2\.[345]\b|^##\s+\d+\.|\Z)",
        block,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return sub.group(0) if sub else block


def extract_section4_d(text: str) -> str:
    block = extract_section(text, r"^##\s+4\.\s+")
    sub = re.search(
        r"(\*\*D\.|^###?\s+.*\bD\.|\*\*4\.D)",
        block,
        re.MULTILINE | re.IGNORECASE,
    )
    if not sub:
        return block
    d_start = sub.start()
    d_block = block[d_start:]
    e_match = re.search(r"\*\*E\.|^###?\s+.*\b4\.E\b", d_block, re.MULTILINE | re.IGNORECASE)
    if e_match:
        return d_block[: e_match.start()]
    return d_block


def first_column_codes(section_text: str) -> set[str]:
    """Extract first-column table cell values (skip header/separator rows)."""
    codes: set[str] = set()
    for line in section_text.splitlines():
        if not line.strip().startswith("|"):
            continue
        if re.match(r"^\|\s*[-:| ]+\|\s*$", line):
            continue
        m = TABLE_ROW.match(line)
        if not m:
            continue
        cell = m.group(1).strip()
        if cell.lower() in ("vvl code", "id", "mmis field name", "code", "---"):
            continue
        if cell:
            codes.add(cell)
    return codes


def find_mmis_fields_in_section3(section3: str, known_fields: set[str]) -> set[str]:
    found: set[str] = set()
    for field in known_fields:
        if field in section3:
            found.add(field)
    return found


def validate_spec_against_research(data: dict, spec_text: str) -> list[str]:
    errors: list[str] = []

    research_source_fields = {
        m["source_field"] for m in data.get("field_mappings", []) if m.get("source_field")
    }
    research_vvl_codes: set[str] = set()
    for vvl in data.get("vvl_members", []):
        for row in vvl.get("rows", []):
            code = (row.get("code") or "").strip()
            if code:
                research_vvl_codes.add(code)

    research_gap_ids = {g["id"] for g in data.get("gaps", []) if g.get("id")}
    research_target_attrs = {
        m["target_attribute"]
        for m in data.get("field_mappings", [])
        if m.get("target_attribute")
    }
    research_assumptions = data.get("assumptions") or []

    section3 = extract_section3(spec_text)
    if not section3:
        errors.append("spec missing §3 Core Technical Mapping Matrix")
    else:
        found_fields = find_mmis_fields_in_section3(section3, research_source_fields)
        missing = research_source_fields - found_fields
        if missing:
            sample = sorted(missing)[:5]
            errors.append(
                f"§3 missing {len(missing)} research source_field(s), e.g. {sample}"
            )

        missing_targets = {
            attr for attr in research_target_attrs if attr not in section3
        }
        if missing_targets:
            sample = sorted(missing_targets)[:5]
            errors.append(
                f"§3 missing {len(missing_targets)} research target_attribute(s), e.g. {sample}"
            )

        extra_candidates = find_mmis_fields_in_section3(
            section3, research_source_fields | set()
        )
        # Detect MMIS-like tokens in §3 first column not in research
        for line in section3.splitlines():
            if not line.strip().startswith("|"):
                continue
            m = TABLE_ROW.match(line)
            if not m:
                continue
            cell = m.group(1).strip()
            if cell in research_source_fields or cell.lower() in (
                "mmis field name",
                "---",
            ):
                continue
            if re.match(r"^[A-Z][A-Z0-9-]+$", cell) and cell not in research_source_fields:
                if len(cell) > 4 and "-" in cell:
                    errors.append(f"§3 contains source field not in research: {cell!r}")

    section2_2 = extract_section2_2(spec_text)
    spec_gap_ids = set(GAP_PATTERN.findall(section2_2 or spec_text))
    missing_gaps = research_gap_ids - spec_gap_ids
    if missing_gaps:
        errors.append(f"§2.2 missing research gap id(s): {sorted(missing_gaps)}")
    orphan_gaps = spec_gap_ids - research_gap_ids
    if orphan_gaps:
        errors.append(
            f"§2.2 contains GAP id(s) not in research gaps: {sorted(orphan_gaps)}"
        )

    section4_d = extract_section4_d(spec_text)
    if research_vvl_codes and section4_d:
        spec_vvl_codes = first_column_codes(section4_d)
        # VVL codes are often short; filter to codes that look like VVL members
        invented = spec_vvl_codes - research_vvl_codes - {
            "VVL Code",
            "Source Code",
            "Target Enum / Canonical Value",
            "Target Value",
        }
        # Keep only alphanumeric short codes likely to be VVL
        invented = {c for c in invented if len(c) <= 10 and re.match(r"^[A-Za-z0-9]+$", c)}
        invented = invented - research_vvl_codes
        if invented:
            sample = sorted(invented)[:5]
            errors.append(
                f"§4.D contains VVL code(s) not in research vvl_members, e.g. {sample}"
            )

    spec_asm_ids = set(ASM_PATTERN.findall(spec_text))
    if spec_asm_ids and not research_assumptions:
        errors.append(
            f"spec contains ASM id(s) {sorted(spec_asm_ids)} but research assumptions is empty"
        )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Integration Spec Markdown against research YAML."
    )
    parser.add_argument("research_yaml", type=Path, help="Path to research YAML")
    parser.add_argument("spec_md", type=Path, help="Path to Integration Spec Markdown")
    args = parser.parse_args(argv)

    for path, label in ((args.research_yaml, "research"), (args.spec_md, "spec")):
        if not path.is_file():
            print(f"error: {label} file not found: {path}", file=sys.stderr)
            return 1

    with args.research_yaml.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    spec_text = args.spec_md.read_text(encoding="utf-8")
    errors = validate_spec_against_research(data, spec_text)

    if errors:
        print("Spec vs research validation failed:", file=sys.stderr)
        for msg in errors:
            print(f"  {msg}", file=sys.stderr)
        return 1

    print(f"OK: {args.spec_md} matches {args.research_yaml}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
