#!/usr/bin/env python3
"""Generate Integration Spec Markdown from approved research YAML (Writer phase)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


def fmt_pos(m: dict) -> str:
    sp, ep, ln = m.get("start_pos"), m.get("end_pos"), m.get("length")
    if sp and ep:
        return f"{sp}–{ep} ({ln})" if ln else f"{sp}–{ep}"
    return str(ln or "—")


def json_constraints(java_type: str, t_msis: str | None, vvl_file: str | None) -> str:
    parts = [java_type]
    if t_msis:
        parts.append(f"**Medicaid_Rule ({t_msis})**")
    if vvl_file:
        parts.append(f"VVL: {vvl_file} (see §4.D)")
    return "; ".join(parts)


def transform_rules(m: dict) -> str:
    parts = [
        f"Slice raw `byte[]` at positions {fmt_pos(m)}; decode per `picture` ({m.get('picture', '—')}).",
        "Alphanumeric: `new String(slice, StandardCharsets.ISO_8859_1).trim()`.",
        f"MapStruct → `{m['target_attribute']}` (`{m['java_type']}`).",
        f"Derivation: {m.get('derivation', 'INFERRED')}.",
    ]
    if m.get("t_msis_rule"):
        parts.append(f"Validate against **Medicaid_Rule ({m['t_msis_rule']})**.")
    if m.get("vvl_file"):
        parts.append(f"Code normalization per §4.D ({m['vvl_file']}).")
    parts.append(f"Provenance: `{m['source_ref']}` → `{m['target_ref']}`.")
    return " ".join(parts)


def section1(meta: dict) -> str:
    flow = meta["flow"]
    dv = meta["dictionary_version"]
    return f"""# Integration Specification: MES to CMdS ({flow})

**T-MSIS Dictionary Version:** {dv}

## 1. Document Header & Executive Summary

### Business Objective

Migrate Member Eligibility records from the legacy MES fixed-width mainframe extract into the CMdS cloud-native relational domain model. The integration enables typed persistence of member demographics, eligibility spans, Medicare coordination, LTC, health-home, lock-in, and related attributes to support core claims, financials, and external T-MSIS validations.

### Target Architectural Pattern

The implementation team SHALL build a deterministic pipeline:

1. **Raw Byte Extract Ingestion** — Read the legacy fixed-width file as `byte[]` per record (1473-byte layout per `MEMBERELIGIBILITY.csv`) to avoid mixed-mode corruption from COMP-3 and binary COMP fields.
2. **Boundary-Safe Parsing** — Slice fields using explicit start/end positions with `Math.min` upper-bound guards against `ArrayIndexOutOfBoundsException` when records are truncated.
3. **Text Normalization** — Every `PIC X` field: `new String(slice, StandardCharsets.ISO_8859_1).trim()` at ingestion (see **GAP-01** for charset confirmation).
4. **MapStruct Conversion** — Map parsed values into `MemberEligibilityVO` intermediate types.
5. **T-MSIS Validation** — Apply tagged **Medicaid_Rule (ELG.xxx.xxx)** constraints from dictionary {dv} (see §4.F).
6. **Canonical JSON Serialization** — Emit JSON aligned to the target VO schema.
7. **Idempotent CMdS REST API Delivery** — POST to CMdS for PostgreSQL persistence (see **GAP-13** for API contract).

### Source Artifacts (Research Provenance)

| Artifact | SHA-256 |
|----------|---------|
| `source/MEMBERELIGIBILITY.csv` | `{meta['sources'][0]['sha256']}` |
| `target/MemberEligibilityVO.md` | `{meta['sources'][1]['sha256']}` |
| `source/MEMBERELIGIBILITY.CPY` | `{meta['sources'][2]['sha256']}` |
"""


def section2(gaps: list, assumptions: list) -> str:
    gap_rows = []
    for g in gaps:
        gap_rows.append(
            f"| {g['id']} | {g['topic']} | {g['evidence']} | Blocks correct decode, validation, or operational handoff until resolved. | {g['owner']} | {g['priority']} |"
        )

    p1 = [g["id"] for g in gaps if g.get("priority") == "P1"]
    p2 = [g["id"] for g in gaps if g.get("priority") == "P2"]

    questions = []
    for g in sorted(gaps, key=lambda x: (x.get("priority", "P9"), x["id"])):
        questions.append(f"- **[{g['id']}]** ({g['priority']}) {g['topic']} — Owner: {g['owner']}")

    asm_block = (
        "No assumptions are recorded in the approved research artifact. Placeholder values (`ASM-NN`) await BA confirmation after gap resolution."
        if not assumptions
        else "\n".join(
            f"| {a['id']} | {a.get('gap_id', '—')} | {a.get('placeholder', '—')} | {a.get('usage', '—')} |"
            for a in assumptions
        )
    )

    return f"""## 2. Gaps & Assumptions (Human-in-the-Loop Handoff)

### 2.1 Document Conventions for This Section

| Symbol | Meaning |
|--------|---------|
| **GAP-NN** | Information missing from source/target artifacts; must be resolved before build. |
| **ASM-NN** | Placeholder assumption awaiting BA confirmation; traces to one GAP and forward to spec usage. |
| **Medicaid_Rule (ELG.xxx.xxx)** | T-MSIS data-element validation rule from dictionary 4.0.33. |
| **P1** | Critical — blocks ingestion, mapping, or compliance. |
| **P2** | Important — affects correctness or operations; may proceed with documented risk after BA review. |
| **MMIS SME** | Legacy source layout and code-decode authority. |
| **CMdS API** | Target REST contract and operational SLAs. |
| **Sec/Compliance** | HIPAA/PHI and retention policy authority. |

### 2.2 GAPS — Information Missing from Source/Target Artifacts

| ID | Topic | What is Missing | Why it Matters | Owner | Priority |
|----|-------|-----------------|----------------|-------|----------|
{chr(10).join(gap_rows)}

### 2.3 ASSUMPTIONS — Placeholder Values Awaiting BA Confirmation

{asm_block}

### 2.4 Outstanding Questions for the BA Team (in Priority Order)

**P1 gaps ({len(p1)}):** {', '.join(p1)}

**P2 gaps ({len(p2)}):** {', '.join(p2)}

{chr(10).join(questions)}

### 2.5 BA Sign-Off (to be completed before "Ready for Build")

| Gate | Status | Signatory | Date |
|------|--------|-----------|------|
| All P1 gaps resolved or accepted with documented risk | ☐ | | |
| ASM placeholders confirmed or replaced with authoritative rules | ☐ | | |
| §3 mapping matrix reviewed against source layout | ☐ | | |
| §4.D VVL tables confirmed for production code sets | ☐ | | |
| CMdS API contract and idempotency key agreed (**GAP-13**, **GAP-14**) | ☐ | | |
| Sec/Compliance DLQ redaction policy approved (**GAP-12**) | ☐ | | |
| **Ready for Build** | ☐ | | |
"""


def section3(mappings: list) -> str:
    rows = []
    for m in mappings:
        rows.append(
            "| "
            + " | ".join(
                [
                    m["source_field"],
                    m.get("picture", "—"),
                    fmt_pos(m),
                    m["target_attribute"],
                    m["java_type"],
                    json_constraints(m["java_type"], m.get("t_msis_rule"), m.get("vvl_file")),
                    transform_rules(m),
                ]
            )
            + " |"
        )
    return f"""## 3. Core Technical Mapping Matrix

One row per approved research `field_mappings` entry. Record length: **1473 bytes** (`SRC-FILE-NM` ends at position 1473).

| MMIS Field Name | COBOL PICTURE Clause | Position / Length | CMdS Target Attribute Name | Target Java Data Type | Target JSON Schema Constraints | Transformation & Business Rules |
|-----------------|----------------------|-------------------|----------------------------|----------------------|----------------------------------|--------------------------------|
{chr(10).join(rows)}
"""


def section4(mappings: list, vvls: list, gaps: list) -> str:
    gap_topics = {g["id"]: g["topic"] for g in gaps}

    # §4.A–C narrative
    a_c = """## 4. Data Engineering & Transformation Nuances

### A. String Normalization & Text Truncation

- All `PIC X` fields SHALL be extracted via boundary-safe `byte[]` slicing and instantiated with `StandardCharsets.ISO_8859_1`, then `.trim()` to drop legacy padding (**GAP-01** pending charset confirmation).
- Width mismatches between source `PIC X(04)` and target VO `@Size` constraints are flagged: **GAP-03** (gender), **GAP-17** (level of care), **GAP-18** (marital status).
- Phone fields (`MBR-PHN-NUM`, case-mgmt, auth-rep, payee): source `PIC X(12)` vs VO `@Size(max=10)` — see **GAP-10**.

### B. Date Parsing & High-Date Logic

- `PIC X(08)` date fields map to `LocalDate` with VO `@JsonFormat(pattern = "yyyyMMdd")` unless noted (e.g. `CTR-SRVC-DT` → `YearMonth`, **GAP-02**).
- Sentinel handling for values such as `00000000` or `99999999` is not documented in artifacts — see **GAP-09**.
- Cross-field period ordering (begin ≤ end) is not specified for this integration boundary — see **GAP-15**.

### C. Computational / Packed Decimals (COMP-3 Processing)

- **LTC-CURR-LIAB-AM**, **LTC-PREV-LIAB-AM**, **HPLN-RT-AMT**, **TOT-RT-AMT**: `PIC S9(7)V99 COMP-3` (5 bytes each) → `BigDecimal` with `@Digits(integer=7, fraction=2)`. Byte order and sign-nibble rules are not documented — see **GAP-07**.
- **HH-SIZE-NUM**: `PIC 9(04) COMP` (2 bytes) → `Integer`; COMP endianness not stated — see **GAP-08**.

### D. Code-to-Enum Normalization & Valid Value Lists
"""

    vvl_sections = []
    for vvl in vvls:
        de = vvl["de"]
        fname = vvl["file"]
        header = f"""
#### D.{vvls.index(vvl) + 1}. {fname} — **Medicaid_Rule ({de})**

| VVL Code | Description | Medicaid_Rule |
|----------|-------------|---------------|
"""
        code_rows = []
        for row in vvl["rows"]:
            code_rows.append(
                f"| {row['code']} | {row['description']} | **Medicaid_Rule ({de})** (`{row['source_ref']}`) |"
            )
        vvl_sections.append(header + "\n".join(code_rows))

    # §4.E index
    e_rows = []
    for vvl in vvls:
        e_rows.append(
            f"| {vvl['file']} | **Medicaid_Rule ({vvl['de']})** | {len(vvl['rows'])} codes | §4.D.{vvls.index(vvl) + 1} |"
        )

    # §4.F rules from mappings
    rule_fields = [m for m in mappings if m.get("t_msis_rule")]
    f_rows = []
    for m in rule_fields:
        vvl_note = f" — VVL `{m['vvl_file']}` (§4.D)" if m.get("vvl_file") else ""
        f_rows.append(
            f"| **Medicaid_Rule ({m['t_msis_rule']})** | `{m['source_field']}` → `{m['target_attribute']}` | {m['source_ref']} → {m['target_ref']}{vvl_note} |"
        )
    # GAP-04 for race without vvl
    f_rows.append(
        "| **Medicaid_Rule (ELG.016.213)** | `MBR-RACE-CD` → `race` | MEMBERELIGIBILITY.csv:L31 → MemberEligibilityVO.md:L131 — **GAP-04**: no CONFIRMED race VVL CSV |"
    )

    return (
        a_c
        + "\n".join(vvl_sections)
        + f"""

### E. Valid Value Lists Applied (`Medicaid_Rule` VVL Index)

| VVL File | Medicaid_Rule | Member Count | Spec Section |
|----------|---------------|--------------|--------------|
{chr(10).join(e_rows)}

Fields referencing VVLs without CONFIRMED list members in research: `MBR-RACE-CD` (**GAP-04**), `MBR-TERM-RSN-CD` (**GAP-05**), `MBR-FED-MCH-CD` (**GAP-06**). Veterans indicator normalization **GAP-16** applies to `VET-IND-CD` despite confirmed VVL.

### F. Medicare.gov / T-MSIS Validation Rules Applied (`Medicaid_Rule`)

Consolidated rules from research `field_mappings` where `t_msis_rule` is set (dictionary 4.0.33):

| Medicaid_Rule | Field Mapping | Provenance |
|---------------|---------------|------------|
{chr(10).join(f_rows)}
"""
    )


def generate(data: dict) -> str:
    parts = [
        section1(data["meta"]),
        section2(data.get("gaps", []), data.get("assumptions") or []),
        section3(data["field_mappings"]),
        section4(data["field_mappings"], data.get("vvl_members", []), data.get("gaps", [])),
    ]
    return "\n\n".join(parts) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Integration Spec from research YAML")
    parser.add_argument("research_yaml", type=Path)
    parser.add_argument("output_md", type=Path)
    args = parser.parse_args()

    with args.research_yaml.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(generate(data), encoding="utf-8")
    print(f"Wrote {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
