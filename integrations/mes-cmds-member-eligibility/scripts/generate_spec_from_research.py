#!/usr/bin/env python3
"""Generate Integration Spec Markdown from approved research YAML (Writer phase)."""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import yaml

RULES_WITH_VVL = {
    "ELG.002.023": "sex.csv",
    "ELG.003.034": "marital-status.csv",
    "ELG.003.039": "veteran-indicator.csv",
    "ELG.003.045": "english-proficiency.csv",
    "ELG.003.046": "preferred-language.csv",
    "ELG.003.047": "household-size.csv",
    "ELG.005.087": "eligibility-group.csv",
    "ELG.005.088": "level-of-care-status.csv",
}


def json_constraints(java_type: str, picture: str) -> str:
    if java_type == "LocalDate":
        return "DateYyyyMmDd pattern ^\\d{8}$"
    if java_type == "YearMonth":
        return "YearMonthYyyyMm pattern ^\\d{6}$"
    if java_type == "BigDecimal":
        return "Decimal7Scale2 or Decimal9Scale2"
    if java_type == "Integer":
        return "integer"
    if "PIC X(02)" in picture and "ST-CD" in picture:
        return "string maxLength 2"
    if "PIC X(05)" in picture and "ZIP" in picture:
        return "string maxLength 5"
    if "PIC X(04)" in picture:
        return "string maxLength 4 (source); see GAPs for width normalization"
    if "PIC X(12)" in picture and "PHN" in picture:
        return "string maxLength 10–12; see GAP-10"
    if "PIC X" in picture:
        return f"string per OpenAPI maxLength for target attribute"
    return "per OpenAPI schema"


def transform_rules(m: dict) -> str:
    parts: list[str] = []
    picture = m.get("picture") or ""
    java_type = m.get("java_type") or "String"
    rule = m.get("t_msis_rule")
    vvl = m.get("vvl_file")

    if "COMP-3" in picture:
        parts.append(
            "Slice packed decimal bytes with boundary-safe `Math.min`; decode COMP-3 to "
            f"`{java_type}`. See §4.C and GAP-07."
        )
    elif "COMP" in picture and "COMP-3" not in picture:
        parts.append(
            f"Decode binary COMP field to `{java_type}`. See §4.C and GAP-08."
        )
    elif java_type == "LocalDate":
        parts.append(
            "Extract PIC X(08) via ISO_8859_1 + `.trim()`; parse to LocalDate. "
            "See §4.B and GAP-09 for sentinel handling."
        )
    elif java_type == "YearMonth":
        parts.append(
            "Extract PIC X(08) via ISO_8859_1 + `.trim()`; derive YearMonth (YYYYMM). "
            "See §4.B and GAP-02."
        )
    elif java_type == "String" and picture.startswith("PIC X"):
        parts.append(
            "Byte-slice with `Math.min` upper bound; instantiate via "
            "`StandardCharsets.ISO_8859_1` + `.trim()`. See §4.A."
        )
    elif java_type in ("BigDecimal", "Integer"):
        parts.append(f"Map to `{java_type}` per §4.C.")
    else:
        parts.append(f"Map to `{java_type}`.")

    if rule:
        parts.append(f"Validate against **Medicaid_Rule ({rule})**.")
    if vvl:
        parts.append(f"VVL cross-ref: §4.D ({vvl}).")
    if m["source_field"] == "MBR-RACE-CD":
        parts.append("Race VVL not confirmed — see GAP-04.")

    return " ".join(parts)


def mapping_row(m: dict) -> str:
    pos = f"{m['start_pos']}–{m['end_pos']} ({m['length']})"
    prov = f"{m['source_ref']} → {m['target_ref']}"
    return (
        f"| {m['source_field']} "
        f"| {m['picture']} "
        f"| {pos} "
        f"| {m['target_attribute']} "
        f"| {m['java_type']} "
        f"| {json_constraints(m['java_type'], m['picture'])} "
        f"| {transform_rules(m)} "
        f"| {prov} |"
    )


def gap_table(gaps: list) -> str:
    lines = [
        "| ID | Topic | What is missing | Why it matters | Owner | Priority |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for g in gaps:
        lines.append(
            f"| {g['id']} | {g['topic']} | {g['evidence']} | "
            f"Blocks deterministic ingest without SME decision. | {g['owner']} | {g['priority']} |"
        )
    return "\n".join(lines)


def outstanding_questions(gaps: list) -> str:
    p1 = [g for g in gaps if g["priority"] == "P1"]
    p2 = [g for g in gaps if g["priority"] == "P2"]
    lines = ["**P1 (must resolve before build):**", ""]
    for i, g in enumerate(p1, 1):
        lines.append(f"{i}. **[{g['id']}]** {g['topic']} — {g['evidence']}")
    lines.extend(["", "**P2 (resolve before production):**", ""])
    for i, g in enumerate(p2, 1):
        lines.append(f"{i}. **[{g['id']}]** {g['topic']} — {g['evidence']}")
    return "\n".join(lines)


def vvl_section(vvl_members: list) -> str:
    parts: list[str] = []
    for vvl in vvl_members:
        de = vvl["de"]
        fname = vvl["file"]
        parts.append(f"#### {fname} — Medicaid_Rule ({de})\n")
        parts.append("| Code | Description | Medicaid_Rule |")
        parts.append("| --- | --- | --- |")
        for row in vvl["rows"]:
            code = row["code"]
            desc = row["description"].replace("|", "\\|")
            parts.append(f"| {code} | {desc} | Medicaid_Rule ({de}) |")
        parts.append("")
    return "\n".join(parts)


def vvl_index(vvl_members: list) -> str:
    lines = [
        "| VVL File | Data Element | §3 Field(s) | Medicaid_Rule |",
        "| --- | --- | --- | --- |",
    ]
    field_by_vvl = {
        "sex.csv": "MBR-GNDR-CD → gender",
        "marital-status.csv": "MRTL-STAT-CD → maritalStatus",
        "veteran-indicator.csv": "VET-IND-CD → veteransIndicator",
        "english-proficiency.csv": "ENG-PRFCY-CD → primaryLanguageEnglishProficiencyCode",
        "preferred-language.csv": "MBR-LANG-CD → languageCode",
        "household-size.csv": "HH-SIZE-NUM → householdSize",
        "eligibility-group.csv": "MBR-ELIG-CAT → categoryOfEligibility",
        "level-of-care-status.csv": "LTC-LVL-CARE-CD → levelOfCare",
    }
    for vvl in vvl_members:
        fname = vvl["file"]
        de = vvl["de"]
        fields = field_by_vvl.get(fname, "—")
        lines.append(f"| {fname} | {de} | {fields} | Medicaid_Rule ({de}) |")
    return "\n".join(lines)


def t_msis_rules_section(mappings: list) -> str:
    seen: dict[str, list[str]] = {}
    for m in mappings:
        rule = m.get("t_msis_rule")
        if rule:
            seen.setdefault(rule, []).append(
                f"{m['source_field']} → {m['target_attribute']}"
            )
    lines = [
        "| Medicaid_Rule | Source → Target | VVL Reference |",
        "| --- | --- | --- |",
    ]
    for rule, fields in sorted(seen.items()):
        vvl = RULES_WITH_VVL.get(rule, "—")
        ref = f"§4.D ({vvl})" if vvl != "—" else "— (see GAP-04 for ELG.016.213)"
        lines.append(
            f"| Medicaid_Rule ({rule}) | {', '.join(fields)} | {ref} |"
        )
    return "\n".join(lines)


def generate(data: dict) -> str:
    meta = data["meta"]
    flow = meta["flow"]
    dv = meta["dictionary_version"]
    mappings = data["field_mappings"]
    gaps = data["gaps"]
    vvl_members = data["vvl_members"]

    mapping_table = "\n".join(mapping_row(m) for m in mappings)

    return textwrap.dedent(f"""\
# Integration Specification: MES to CMdS ({flow})

**T-MSIS Dictionary Version:** {dv}

## 1. Document Header & Executive Summary

### Business Objective

This integration migrates fixed-width Member Eligibility records from the legacy MES (MMIS)
extract into the CMdS cloud-native relational domain model. Each 1473-byte record carries member
demographics, eligibility spans, Medicare/Medicaid identifiers, health-home and LTC attributes,
and related contact data. The objective is to enable core claims, financials, and external
T-MSIS validations against a typed JSON payload persisted in PostgreSQL via CMdS REST APIs.

### Target Architectural Pattern

The implementation MUST follow this deterministic pipeline:

1. **Raw Byte Extract Ingestion** — Read the legacy file as raw `byte[]` per record (1473 bytes)
   to avoid mixed-mode corruption from COMP-3 or binary COMP fields.
2. **Boundary-Safe Parsing** — Slice each field using explicit start/end indices with
   `Math.min(record.length, endIndex)` guards; reject or DLQ records shorter than the layout
   requires (see GAP-11).
3. **Text Normalization** — All PIC X fields: decode with `StandardCharsets.ISO_8859_1` and
   `.trim()` at the ingestion boundary (see GAP-01 for charset confirmation).
4. **MapStruct Conversion** — Map parsed intermediate properties into the target Java VO using
   MapStruct; `@Named` / `qualifiedByName` identifiers MUST match this specification
   character-for-character.
5. **T-MSIS Validation** — Apply **Medicaid_Rule** constraints tagged in §3 and §4.F against
   dictionary version **{dv}**.
6. **Canonical JSON Serialization** — Serialize the validated VO to JSON conforming to
   `member-eligibility.openapi.yaml`.
7. **Idempotent CMdS REST API Delivery** — POST each record to CMdS `/member-eligibility` with
   OAuth2 client credentials; idempotency key format pending GAP-14.

---

## 2. Gaps & Assumptions (Human-in-the-Loop Handoff)

### 2.1 Document Conventions for This Section

| Symbol | Meaning |
| --- | --- |
| **GAP-NN** | Information missing from source/target artifacts; requires BA/SME resolution before build. |
| **ASM-NN** | Placeholder assumption awaiting BA confirmation (none registered in research). |
| **Medicaid_Rule (ELG.xxx.xxx)** | T-MSIS data-element validation rule from dictionary {dv}. |
| **P1 / P2 / P3** | Priority: P1 = build-blocking; P2 = production-blocking; P3 = nice-to-have. |
| **Owner roles** | MMIS SME, CMdS API, Sec/Compliance — responsible party for closure. |

### 2.2 GAPS — Information Missing from Source/Target Artifacts

{gap_table(gaps)}

### 2.3 ASSUMPTIONS — Placeholder Values Awaiting BA Confirmation

Research `assumptions` is empty. No **ASM-NN** entries are registered. Assumptions await BA
fill-in after GAP closure in §2.2.

### 2.4 Outstanding Questions for the BA Team (in priority order)

{outstanding_questions(gaps)}

### 2.5 BA Sign-Off (to be completed before "Ready for Build")

| Checklist Item | Status | BA Initials | Date |
| --- | --- | --- | --- |
| All P1 GAPs resolved or accepted with ASM | ☐ | | |
| §3 mapping matrix reviewed against MMIS layout | ☐ | | |
| §4 VVL code tables confirmed against T-MSIS {dv} | ☐ | | |
| Idempotency / natural key agreed (GAP-14) | ☐ | | |
| PHI / DLQ policy agreed (GAP-12) | ☐ | | |
| **Build-Readiness Gate:** Spec approved for implementation | ☐ | | |

---

## 3. Core Technical Mapping Matrix

One row per research `field_mappings` entry. Record length: **1473 bytes** (positions 1–1473).

| MMIS Field Name | COBOL PICTURE Clause | Position / Length | CMdS Target Attribute Name | Target Java Data Type | Target JSON Schema Constraints | Transformation & Business Rules | Provenance |
| --- | --- | --- | --- | --- | --- | --- | --- |
{mapping_table}

---

## 4. Data Engineering & Transformation Nuances

### A. String Normalization & Text Truncation

All alphanumeric source fields (`PIC X` equivalents) MUST be extracted from the raw byte array
using boundary-safe slicing (`Math.min(record.length, endPos)`). String instantiation MUST use
`new String(bytes, StandardCharsets.ISO_8859_1).trim()` to drop legacy trailing space padding
before MapStruct mapping.

Width mismatches between source PIC X(n) and OpenAPI maxLength are tracked as GAPs (e.g.
GAP-03 gender, GAP-10 phone numbers, GAP-17 level of care, GAP-18 marital status). Do not
silently truncate without BA-approved ASM.

### B. Date Parsing & High-Date Logic

Date fields (`PIC X(08)` → `LocalDate`) and `CTR-SRVC-DT` (`YearMonth`) MUST be parsed only after
ISO_8859_1 trim. Sentinel values (e.g. `00000000`, `99999999`) are not documented in source
artifacts — see **GAP-09**. High-date / open-ended period logic is not specified at the MES→CMdS
boundary — see **GAP-15** for cross-field ordering rules.

### C. Computational / Packed Decimals (COMP-3 Processing)

Fields `LTC-CURR-LIAB-AM`, `LTC-PREV-LIAB-AM`, `HPLN-RT-AMT`, and `TOT-RT-AMT` use
`PIC S9(7)V99 COMP-3` (5 bytes each). Decode with explicit nibble sign and scale 2 fractional
digits into `BigDecimal`. Byte order and sign-nibble rules are not documented — see **GAP-07**.

Field `HH-SIZE-NUM` uses `PIC 9(04) COMP` (2 bytes). Decode to `Integer` with platform-endian
assumption pending SME confirmation — see **GAP-08**.

### D. Code-to-Enum Normalization & Valid Value Lists

Full code tables from research `vvl_members` only. Each row tagged **Medicaid_Rule**.

{vvl_section(vvl_members)}

### E. Valid Value Lists Applied (Medicaid_Rule VVL Index)

{vvl_index(vvl_members)}

### F. Medicare.gov / T-MSIS Validation Rules Applied (Medicaid_Rule)

Consolidated rules from field mappings where `t_msis_rule` is set (dictionary **{dv}**):

{t_msis_rules_section(mappings)}

**Note:** `MBR-RACE-CD` maps to **Medicaid_Rule (ELG.016.213)** but no CONFIRMED race VVL CSV
exists in research — see **GAP-04**.
""")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("research_yaml", type=Path)
    parser.add_argument("output_md", type=Path)
    args = parser.parse_args()
    data = yaml.safe_load(args.research_yaml.read_text(encoding="utf-8"))
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(generate(data), encoding="utf-8")
    print(f"Wrote {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
