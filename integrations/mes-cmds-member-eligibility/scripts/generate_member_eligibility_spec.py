#!/usr/bin/env python3
"""Transcribe research YAML into Integration Spec Markdown (Writer phase)."""
from __future__ import annotations

from pathlib import Path

import yaml

INTEGRATION_ROOT = Path(__file__).resolve().parent.parent
RESEARCH_PATH = INTEGRATION_ROOT / "research/Integration_Research_MemberEligibility.yaml"
OUT_PATH = INTEGRATION_ROOT / "spec/Integration_Spec_MES_to_CMdS_MemberEligibility.md"

VVL_DISPLAY_NAMES: dict[str, str] = {
    "sex.csv": "Sex List",
    "marital-status.csv": "Marital Status List",
    "veteran-indicator.csv": "Veteran Indicator List",
    "english-proficiency.csv": "English Proficiency List",
    "household-size.csv": "Household Size List",
    "eligibility-group.csv": "Eligibility Group List",
    "level-of-care-status.csv": "Level of Care Status List",
    "preferred-language.csv": "Preferred Language List",
}


def json_constraint(java_type: str) -> str:
    if java_type == "LocalDate":
        return "string date (ISO-8601 after parse)"
    if java_type == "YearMonth":
        return "string yyyy-MM (YearMonth)"
    if java_type == "BigDecimal":
        return "number (decimal)"
    if java_type == "Integer":
        return "integer"
    return "string"


def transform_rules(m: dict) -> str:
    parts: list[str] = []
    sp, ep, ln = m.get("start_pos"), m.get("end_pos"), m.get("length")
    pic = m.get("picture") or ""
    if sp and ep:
        parts.append(
            f"Slice bytes {sp}-{ep} (length {ln}) with `Math.min` upper bound; "
            f"decode `StandardCharsets.ISO_8859_1` and `.trim()` for alphanumeric."
        )
    if "COMP-3" in pic.upper():
        parts.append("COMP-3 packed decimal decode — see §4.C and GAP-07.")
    if "COMP" in pic.upper() and "COMP-3" not in pic.upper():
        parts.append("Binary COMP integer decode — see §4.C and GAP-08.")
    jt = m.get("java_type") or "String"
    if jt == "LocalDate":
        parts.append("Parse PIC X(08) to LocalDate; sentinel handling — see §4.B and GAP-09.")
    if jt == "YearMonth":
        parts.append("Parse PIC X(08) to YearMonth — see GAP-02.")
    rule = m.get("t_msis_rule")
    if rule:
        parts.append(f"Apply **Medicaid_Rule ({rule})**.")
    vvl = m.get("vvl_file")
    if vvl:
        parts.append(f"Validate against VVL `{vvl}` — see §4.D.")
    if m.get("source_field") == "MBR-RACE-CD":
        parts.append("Race VVL not CONFIRMED in research — see GAP-04.")
    deriv = m.get("derivation") or ""
    if deriv:
        parts.append(f"Derivation: {deriv}.")
    return " ".join(parts) if parts else "MapStruct pass-through from parsed slice."


def gap_row(g: dict) -> str:
    gid = g["id"]
    topic = g.get("topic", "")
    evidence = (g.get("evidence") or "").replace("\n", " ").strip()
    owner = g.get("owner", "")
    priority = g.get("priority", "")
    why = f"Blocks correct ingest/mapping for: {topic}." if topic else ""
    return (
        f"| {gid} | {topic} | {evidence} | {why} | {owner} | {priority} |"
    )


def build_section3(mappings: list[dict]) -> list[str]:
    lines = [
        "## 3. Core Technical Mapping Matrix",
        "",
        "One row per approved research `field_mappings` entry. Provenance: `source_ref` / `target_ref`.",
        "",
        "| MMIS Field Name | COBOL PICTURE Clause | Position / Length | "
        "CMdS Target Attribute Name | Target Java Data Type | "
        "Target JSON Schema Constraints | Transformation & Business Rules |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in mappings:
        sf = m["source_field"]
        pos = f"{m.get('start_pos')}-{m.get('end_pos')} / {m.get('length')}"
        lines.append(
            f"| {sf} | {m.get('picture', '')} | {pos} | "
            f"{m.get('target_attribute', '')} | {m.get('java_type', '')} | "
            f"{json_constraint(m.get('java_type', 'String'))} | "
            f"{transform_rules(m)} "
            f"Provenance: `{m.get('source_ref', '')}` → `{m.get('target_ref', '')}`. |"
        )
    return lines


def build_section4_d(vvl_members: list[dict]) -> list[str]:
    lines = [
        "## 4. Data Engineering & Transformation Nuances",
        "",
        "### A. String Normalization & Text Truncation",
        "",
        "All alphanumeric (`PIC X`) slices MUST use boundary-safe copy (`Math.min` against record "
        "length), `StandardCharsets.ISO_8859_1` decoding, and `.trim()` at ingestion. Charset "
        "confirmation pending — **GAP-01**.",
        "",
        "### B. Date Parsing & High-Date Logic",
        "",
        "`LocalDate` and `YearMonth` fields follow VO typing; sentinel and high-date rules are not "
        "documented in source artifacts — **GAP-09**, **GAP-02**.",
        "",
        "### C. Computational / Packed Decimals (COMP-3 Processing)",
        "",
        "LTC liability amount fields (`PIC S9(7)V99 COMP-3`) map to `BigDecimal`. Sign nibble and "
        "byte order are not documented — **GAP-07**. `HH-SIZE-NUM` (`PIC 9(04) COMP`) maps to "
        "`Integer` — **GAP-08**.",
        "",
        "**D. Code-to-Enum Normalization & Valid Value Lists**",
        "",
    ]
    for idx, vvl in enumerate(vvl_members, start=1):
        de = vvl["de"]
        fname = vvl.get("file", "")
        display = VVL_DISPLAY_NAMES.get(fname, fname)
        lines.append(f"#### §4.D.{idx} — {display} (`{fname}`, **Medicaid_Rule ({de})**)")
        lines.append("")
        lines.append(
            "| VVL Code | VVL Description | Target Enum / Canonical Value | Medicaid_Rule |"
        )
        lines.append("|---|---|---|---|")
        for row in vvl.get("rows", []):
            code = str(row.get("code", ""))
            desc = (row.get("description") or "").replace("|", "\\|")
            lines.append(
                f"| {code} | {desc} | pass-through String | "
                f"**Medicaid_Rule ({de})** |"
            )
        lines.append("")
    return lines


def build_section4_e(mappings: list[dict], vvl_members: list[dict]) -> list[str]:
    de_by_file = {v["file"]: v["de"] for v in vvl_members}
    subsection_by_file: dict[str, int] = {}
    for idx, v in enumerate(vvl_members, start=1):
        subsection_by_file[v["file"]] = idx

    lines = [
        "**E. Valid Value Lists Applied (`Medicaid_Rule` VVL Index)**",
        "",
        "| CMdS Attribute | Source Field | T-MSIS DE | VVL Name | Value-List File | "
        "# Codes | §4.D Subsection | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for m in mappings:
        vvl_file = m.get("vvl_file")
        rule = m.get("t_msis_rule")
        if not vvl_file and not rule:
            continue
        de = rule or de_by_file.get(vvl_file or "", "")
        fname = vvl_file or "—"
        display = VVL_DISPLAY_NAMES.get(fname, fname) if vvl_file else "—"
        n_codes = "—"
        sub = "—"
        status = "GAP" if m.get("source_field") == "MBR-RACE-CD" else "CONFIRMED"
        if vvl_file:
            for v in vvl_members:
                if v["file"] == vvl_file:
                    n_codes = str(len(v.get("rows", [])))
                    sub = f"§4.D.{subsection_by_file[vvl_file]}"
                    break
        lines.append(
            f"| {m.get('target_attribute', '')} | {m.get('source_field', '')} | {de} | "
            f"{display} | {fname} | {n_codes} | {sub} | {status} |"
        )
    return lines


def build_section4_f(mappings: list[dict]) -> list[str]:
    rules: dict[str, list[str]] = {}
    for m in mappings:
        rule = m.get("t_msis_rule")
        if rule:
            rules.setdefault(rule, []).append(
                f"{m.get('source_field')} → {m.get('target_attribute')}"
            )
    lines = [
        "**F. Medicare.gov / T-MSIS Validation Rules Applied (`Medicaid_Rule`)**",
        "",
    ]
    for de in sorted(rules):
        fields = "; ".join(rules[de])
        lines.append(f"- **Medicaid_Rule ({de})**: {fields}")
    lines.append("")
    return lines


def build_spec(data: dict) -> str:
    meta = data.get("meta", {})
    flow = meta.get("flow", "Member Eligibility")
    dict_ver = meta.get("dictionary_version", "")
    mappings = data.get("field_mappings", [])
    gaps = data.get("gaps", [])
    vvl_members = data.get("vvl_members", [])

    lines: list[str] = [
        f"# Integration Specification: MES to CMdS ({flow})",
        "",
        "## 1. Document Header & Executive Summary",
        "",
        "**Business Objective:** Migrate the MES Member Eligibility fixed-width extract (1473-byte "
        "records, 113 fields) into the CMdS cloud-native `MemberEligibilityVO` domain model for "
        "claims, financials, and external validation.",
        "",
        "**Target Architectural Pattern:**",
        "",
        "1. **Ingestion** — Read legacy extract as raw `byte[]` per record.",
        "2. **Parsing & Slicing** — Boundary-safe field extraction (`Math.min` vs record length).",
        "3. **Normalization** — `ISO_8859_1` decode and `.trim()` on alphanumeric slices.",
        "4. **Mapping** — MapStruct conversion to `MemberEligibilityVO` Java types.",
        "5. **Validation** — T-MSIS rules tagged **Medicaid_Rule (ELG.xxx.xxx)** where cited.",
        "6. **Serialization** — Canonical JSON payload.",
        "7. **Delivery** — Idempotent CMdS REST POST (contract details — **GAP-13**).",
        "",
        f"**T-MSIS dictionary version:** {dict_ver}",
        "",
        "**Research provenance:**",
    ]
    for src in meta.get("sources", []):
        lines.append(f"- `{src.get('path', '')}` (sha256: `{src.get('sha256', '')}`)")
    lines.extend(
        [
            "",
            "## 2. Gaps & Assumptions (Human-in-the-Loop Handoff)",
            "",
            "### 2.1 Document Conventions for This Section",
            "",
            "| Symbol | Meaning |",
            "|---|---|",
            "| GAP-NN | Information missing from source/target artifacts |",
            "| ASM-NN | BA-confirmed placeholder (research `assumptions` only) |",
            "| Medicaid_Rule (ELG.xxx.xxx) | T-MSIS data-element validation citation |",
            "| P1 / P2 / P3 | Priority (P1 highest) |",
            "",
            "### 2.2 GAPS — Information Missing from Source/Target Artifacts",
            "",
            "| ID | Topic | What is missing from the inputs | Why it matters | Owner | Priority |",
            "|---|---|---|---|---|---|",
        ]
    )
    for g in gaps:
        lines.append(gap_row(g))

    lines.extend(
        [
            "",
            "### 2.3 ASSUMPTIONS — Placeholder Values Awaiting BA Confirmation",
            "",
            "Research `assumptions` is empty. No ASM-NN entries are documented; assumptions await "
            "BA confirmation after gap resolution.",
            "",
            "### 2.4 Outstanding Questions for the BA Team (in priority order)",
            "",
        ]
    )
    for g in sorted(gaps, key=lambda x: (x.get("priority", "P9"), x.get("id", ""))):
        lines.append(
            f"- **{g.get('id', '')}** ({g.get('priority', '')}): {g.get('topic', '')}"
        )

    lines.extend(
        [
            "",
            "### 2.5 BA Sign-Off (to be completed before \"Ready for Build\")",
            "",
            "- [ ] All P1 gaps reviewed and disposition recorded",
            "- [ ] VVL and encoding decisions signed off by MMIS SME",
            "- [ ] CMdS API contract confirmed (**GAP-13**)",
            "- [ ] Security/PHI handling confirmed (**GAP-12**)",
            "- [ ] Build-Readiness Gate: Spec validated against research YAML",
            "",
        ]
    )
    lines.extend(build_section3(mappings))
    lines.append("")
    lines.extend(build_section4_d(vvl_members))
    lines.extend(build_section4_e(mappings, vvl_members))
    lines.extend(build_section4_f(mappings))
    return "\n".join(lines) + "\n"


def main() -> None:
    with RESEARCH_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(build_spec(data), encoding="utf-8")
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
