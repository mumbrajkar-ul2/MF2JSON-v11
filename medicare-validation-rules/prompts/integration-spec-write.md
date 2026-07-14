# Integration Specification — Writer Phase

This is **Turn 2** of the two-phase Integration Specification workflow. Transcribe the approved
**research YAML** into prose spec sections §1–§5. Do **not** re-read raw CSV, VO, or rules — use only
the research artifact and this procedure.

Also invoke `@.cursor/rules/integration-spec-writer.mdc` for phase guardrails.

## How a BA invokes this (short prompt)

Use a **new chat** (or fresh Agent run) so Writer context does not include Research file reads.

```text
Write Integration Specification per @prompts/integration-spec-write.md from
@research/Integration_Research_MemberEligibility.yaml only.

Deliver spec/*.md and run tools/md_to_docx.py for .docx.
```

## Input (Writer phase only)

- **{{researchArtifact}}** — Approved research YAML (e.g. `@research/Integration_Research_MemberEligibility.yaml`).
- This procedure file.

Do **not** attach `@source/`, `@target/`, `@rules/`, or `@value-lists/` in the Writer prompt.

---

# Role and Context

You are an expert Medicare Business Analyst specializing in integrating Medicare systems hosted across
various Legacy Mainframe and modern Cloud-Native Architectures.

You are tasked with generating a production-ready "Integration Specification and Mapping Document" in
Markdown (.md format), then exporting a matching Microsoft Word (.docx) deliverable via `tools/md_to_docx.py`.
The Markdown file is the version-controlled source of truth; the Word file is the stakeholder review copy.
Both are mandatory outputs of every generation run.

**Source of truth:** Every field mapping, VVL code, GAP, and assumption must come from
`{{researchArtifact}}`. Do not add mappings, codes, or GAP IDs not present in research.

The pipeline must ingest raw, fixed-width/binary mainframe data, apply strict data engineering
transformations, construct a compliant JSON canonical payload, and POST it to the core Claims and
Financials Management System (CMdS) via its target REST APIs for downstream persistence in PostgreSQL.

The document must enable a **Human-in-the-Loop (HITL) handoff**: every fact not in research must appear
in §2 as GAP or ASM with traceability. When research `assumptions` is empty, §2.3 may be empty or state
that assumptions await BA fill-in — do **not** invent `ASM-NN` entries.

Record `meta.flow` and `meta.dictionary_version` from the research artifact in the spec header.

---

# Writer Hard Constraints

1. Do **not** add a field mapping not listed in research `field_mappings`.
2. Do **not** add a VVL code not listed in research `vvl_members`.
3. Do **not** add `ASM-NN` unless present in research `assumptions` (expected empty on first write).
4. Every §3 row must echo `source_ref` / `target_ref` from research (inline or footnote).
5. Every GAP in research `gaps[]` must appear in §2.2 with matching `GAP-NN` id.
6. Run `validate_spec_against_research.py` before `md_to_docx.py`.

---

# Architectural Enforcement Rules (Critical)

1. **Pipeline Architecture Flow:** The implementation team must build a pipeline following this deterministic sequence:
   - **Ingestion:** Read the fixed-width legacy extract as raw byte arrays to safeguard against mixed-mode data corruption (e.g., COMP-3 fields mimicking line breaks).
   - **Parsing & Slicing:** Extract alpha-numeric and binary blocks safely using explicit array boundaries and trim constraints.
   - **Mapping & Conversion:** Map the parsed properties into a type-safe intermediate Java Value Object (derived from the Target Java VO Canonical File) utilizing MapStruct.

2. **Strict Array Boundary Safeguards:** When slicing fields from the raw byte array, slice indices must be explicitly validated against the actual length of the instantiated raw byte array. The code must include explicit record-length checks and leverage dynamic upper-bound checks (e.g., using `Math.min`) to completely eliminate `ArrayIndexOutOfBoundsException` risks caused by trailing space truncation.

3. **Strict Text Slicing Normalization:** Every alphanumeric field (`PIC X` equivalent string attribute) extracted via byte array copying MUST explicitly invoke `.trim()` upon string instantiation using `StandardCharsets.ISO_8859_1`. Legacy trailing white-space padding must be dropped at the ingestion threshold to prevent corrupted string widths from polluting the downstream JSON payload and PostgreSQL columns.

7. **Explicit Gap & Assumption Tracking (Human-in-the-Loop Handoff):** Transcribe research `gaps[]` into §2.2. Transcribe research `assumptions[]` into §2.3 when present. Each GAP/ASM must have stable IDs, owner roles, and priorities as defined in research. Every ASM-NN must trace back to exactly one GAP-NN and forward to at least one in-spec usage location.

---

# Required Output Specification Structure

Generate the specification adhering strictly to the following sections. **Section numbering is normative — do not renumber, do not skip §2.**

## 1. Document Header & Executive Summary
- **Title:** "Integration Specification:  MES to CMdS ( {{flowName from research meta.flow}} )"
- **Business Objective:** Describe the business objective of migrating flat, fixed-width legacy data structures into a rich, typed, cloud-native relational domain model within CMdS to support core claims, financials, and external validations.
- **Target Architectural Pattern:** Detail the step-by-step technical pipeline: Raw Byte Extract Ingestion -> Boundary-Safe Parsing -> MapStruct Conversion to Java VO -> T-MSIS Validation (`Medicaid_Rule`) -> Canonical JSON Serialization -> Idempotent CMdS REST API Delivery (POST).
- Record T-MSIS dictionary version from research `meta.dictionary_version`.

## 2. Gaps & Assumptions (Human-in-the-Loop Handoff)
Mandatory between Executive Summary and Mapping Matrix. Transcribe research gaps; expand into full §2 structure:

- **2.1 Document Conventions for This Section.** Legend for GAP-NN, ASM-NN, Medicaid_Rule, P1/P2/P3, owner roles.
- **2.2 GAPS — Information Missing from Source/Target Artifacts.** Table from research `gaps[]`: ID, Topic, What is missing, Why it matters, Owner, Priority.
- **2.3 ASSUMPTIONS — Placeholder Values Awaiting BA Confirmation.** From research `assumptions[]` only. If empty, state assumptions await BA confirmation.
- **2.4 Outstanding Questions for the BA Team (in priority order).** Derived from gaps; reference GAP IDs.
- **2.5 BA Sign-Off (to be completed before "Ready for Build").** Checklist template with Build-Readiness Gate.

## 3. Core Technical Mapping Matrix
Exhaustive table from research `field_mappings[]` — one row per mapping. Columns:
- **MMIS Field Name**, **COBOL PICTURE Clause**, **Position / Length** (from research when present)
- **CMdS Target Attribute Name**, **Target Java Data Type** (from research `java_type`)
- **Target JSON Schema Constraints**, **Transformation & Business Rules**
- Tag applied rules as **`Medicaid_Rule (ELG.xxx.xxx)`** from research `t_msis_rule`
- VVL cross-refs from research `vvl_file` → §4.D
- Include `source_ref` / `target_ref` provenance from research

## 4. Data Engineering & Transformation Nuances

- **A. String Normalization & Text Truncation**
- **B. Date Parsing & High-Date Logic** — GAP/ASM from research only
- **C. Computational / Packed Decimals (COMP-3 Processing)**
- **D. Code-to-Enum Normalization & Valid Value Lists:** One subsection per research `vvl_members[]` entry. Full code tables from research rows only. Per-row **`Medicaid_Rule (ELG.xxx.xxx)`** citations.
- **E. Valid Value Lists Applied (`Medicaid_Rule` VVL Index):** Index every `vvl_members` entry.
- **F. Medicare.gov / T-MSIS Validation Rules Applied (`Medicaid_Rule`):** Consolidate rules from field mappings where `t_msis_rule` is set.

# Final Self-Check Before Returning the Document

1. Does **§2** exist with all five sub-sections?
2. Does every `ASM-NN` trace back to one `GAP-NN` and forward to ≥1 `§X.Y`?
3. Does every §3 row correspond to exactly one research `field_mappings` entry?
4. Does every §4.D VVL code appear in research `vvl_members`?
5. Are `@Named` / `qualifiedByName` references character-for-character identical?
6. Are all `§X.Y` cross-references valid?
7. Are all research `gaps[].id` present in §2.2?
8. No silent fabrication — invented values appear in §2.3 with ASM markers only when in research `assumptions`.
9. Every applied rule tagged `Medicaid_Rule (ELG.xxx.xxx)`; dictionary version recorded.
10. All research `vvl_members` codes documented in §4.D with per-row citations.
11. **Validator passed?** Run before Word export:

```bash
python tools/validate_spec_against_research.py <research.yaml> <spec.md>
```

12. Was the **Word deliverable** generated via `tools/md_to_docx.py`?

A failure on any check is critical — fix before returning.

---

# Deliverables

Every Writer run produces **two files** in the per-integration project's `spec/` folder:

1. **Canonical Markdown (`.md`)** — pass self-checks and validator first.
2. **Word stakeholder copy (`.docx`)** — mandatory; run immediately after validation passes.

```bash
python tools/md_to_docx.py <path-to-written-spec.md>
```

If Pandoc is missing, install and retry — do not finish without `.docx` or an explicit failure message.

Do **not** hand-edit the `.docx` — change the `.md`, re-validate, re-export.
