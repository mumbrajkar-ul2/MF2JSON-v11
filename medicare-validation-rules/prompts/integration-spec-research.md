# Integration Specification — Research Phase

This is **Turn 1** of the two-phase Integration Specification workflow. Produce a structured,
version-controlled **research artifact** (YAML only). Do **not** write spec prose, MapStruct
interfaces, or Word export.

Also invoke `@.cursor/rules/integration-spec-research.mdc` for phase guardrails. Shared cite-never-invent
rules live in `@.cursor/rules/medicaid-spec-conventions.mdc`.

## How a BA invokes this (short prompt)

```text
Run Integration Spec Research per @prompts/integration-spec-research.md.
- Flow: Member Eligibility
- Source layout: @source/MEMBERELIGIBILITY.csv
- Target VO: @target/member-eligibility.openapi.yaml
- Validation rules: @rules/eligibility/data-elements.md
- Value lists: @rules/eligibility/value-lists/

Write research/Integration_Research_MemberEligibility.yaml only. Do not write the spec.
```

Use a **separate chat** from the Writer phase so raw artifact reads do not bleed into Turn 2.

## Configuration Tokens (fill from the invoking prompt)

- **{{flowName}}** — Integration Flow Name (e.g. "Member Eligibility").
- **{{businessEntity}}** — Business Domain Entity (often same as flow name).
- **{{sourceLayout}}** — Source mainframe MES file layout artifact (COBOL copybook `.CPY` or derived `.csv`).
- **{{targetVO}}** — Target CMdS Java VO canonical structure (`.md`).
- **{{validationRules}}** — Medicare/T-MSIS validation rules text rendering (`rules/<domain>/data-elements.md`).
- **{{valueLists}}** — T-MSIS valid-value-list members (`rules/<domain>/value-lists/*.csv`).

Record the dictionary version from `MANIFEST.yaml` in `meta.dictionary_version`.

---

# Role and Context

You are an expert Medicare Business Analyst performing **read-only research** on integration artifacts.
Your sole deliverable is `research/Integration_Research_<Flow>.yaml` in the per-integration project,
conforming to `schemas/integration-research.schema.json` in the `medicare-validation-rules` library.

You **cite facts** from provided artifacts. You **do not** invent assumptions, API endpoints, sentinel
date behavior, encoding decisions, or enum mappings unless explicitly stated in the artifacts.

---

# Flow-Specific Configuration Tokens

Use the tokens supplied in the invoking prompt:

- **Integration Flow Name:** {{flowName}}
- **Business Domain Entity:** {{businessEntity}}
- **Source Mainframe MES System file layout:** {{sourceLayout}}
- **Target CMdS System Java VO Canonical Structure:** {{targetVO}}
- **Medicare Validation Rules:** {{validationRules}}
- **T-MSIS Valid Value Lists:** {{valueLists}}

---

# Research Agent Rules (Critical)

1. **Read-only:** Read input artifacts only. Do not modify source files, rules, or VVL CSVs.
2. **Every fact needs `source_ref`:** Format `filename:Lnn` (1-based line) or `filename:Lrow` for CSV data rows.
3. **`gaps` only — no assumptions:** Leave `assumptions: []`. Register missing facts as `gaps[]` with evidence.
   Do **not** create `ASM-NN` entries in research.
4. **`derivation` values:**
   - `DIRECT` — explicit mapping documented in artifacts (name match, documented link).
   - `INFERRED` — positional or name-based mapping not explicitly documented.
   - `UNMAPPED` — source field with no target (or vice versa); explain in gap if unexpected.
5. **VVL members:** Copy **verbatim** from CONFIRMED CSV rows only (`status = CONFIRMED`). Each row needs
   `source_ref` pointing to the CSV line. Stubbed lists (`status = TODO`) → register a GAP; do not invent codes.
6. **Provenance checksums:** Compute SHA-256 of each file listed in `meta.sources[]` at research time.
7. **No spec sections:** No §1–§5, no MapStruct, no Word export, no narrative mapping document.

---

# Gap Category Checklist (Research Only)

Systematically walk these categories. For each that applies, add a `gaps[]` row with `id`, `topic`,
`evidence` (cite files searched), `owner`, and `priority` (P1/P2/P3). Do **not** propose placeholder
values — gaps only.

- Enum / lookup code lists on source side (MMIS dictionary) AND target side (Java enum constants in VO).
  For T-MSIS VVLs: CONFIRMED CSV → document in `vvl_members`; stubbed/missing → GAP.
- Boolean indicator legal values (`Y/N`, `1/0`, `T/F`, blank-as-unknown).
- Date sentinel conventions and per-field translation rules.
- Source file character encoding at the integration boundary.
- Record framing / terminator (fixed-block vs LF/CRLF vs RDW).
- COBOL storage discrepancies (COMP-3 byte width vs standard packing math).
- Per-field nullability / mandatory rules (JSR-380 vs T-MSIS Necessity).
- Cross-field business rules (date ordering, overlapping periods).
- HIPAA / PHI handling for DLQ records.
- Natural-key format and validation.
- Name / free-text field character class.
- CMdS OpenAPI contract, authentication, file arrival, SLA, observability (when not in artifacts).

---

# VVL Matching Logic

1. Match integrated categorical fields to VVL CSVs by `t_msis_data_element` or `valid_value_list_name`
   from `data-elements.md` / `data-elements.csv`.
2. When `status = CONFIRMED`, populate `vvl_members[]` with every code row from the matching CSV.
3. When `status = TODO` or file missing, add a GAP — do not invent codes.
4. Set `field_mappings[].vvl_file` and `field_mappings[].t_msis_rule` when a VVL applies.

---

# Required Output: `research/Integration_Research_<Flow>.yaml`

Write **one file** to the integration project's `research/` folder. Filename example:
`research/Integration_Research_MemberEligibility.yaml`.

Schema: `@schemas/integration-research.schema.json` (in `medicare-validation-rules`).

Example shape (illustrative — produce complete coverage for the flow):

```yaml
meta:
  flow: Member Eligibility
  dictionary_version: "4.0.33"
  sources:
    - path: source/MEMBERELIGIBILITY.csv
      sha256: "..."
    - path: target/MemberEligibilityVO.md
      sha256: "..."

field_mappings:
  - source_field: MBR-GNDR-CD
    source_ref: "MEMBERELIGIBILITY.csv:L30"
    target_attribute: gender
    target_ref: "MemberEligibilityVO.md:L126"
    derivation: DIRECT
    java_type: String
    picture: "PIC X(04)"
    start_pos: 435
    end_pos: 438
    length: 4
    t_msis_rule: ELG.002.023
    vvl_file: sex.csv

gaps:
  - id: GAP-01
    topic: Source character encoding
    evidence: "Not stated in MEMBERELIGIBILITY.csv, .CPY, or VO"
    owner: MMIS SME
    priority: P1

assumptions: []

vvl_members:
  - de: ELG.002.023
    file: sex.csv
    rows:
      - code: F
        description: Female
        source_ref: "sex.csv:L2"
      - code: M
        description: Male
        source_ref: "sex.csv:L3"
      - code: U
        description: Unknown
        source_ref: "sex.csv:L4"
```

Include **every** source layout field in `field_mappings` (Member Eligibility: 113 rows).

---

# Research Self-Check Before Returning

1. Does `field_mappings` cover **every** row in the source layout CSV?
2. Does every mapping row have non-empty `source_ref` and `target_ref`?
3. Are there no duplicate `source_field` or `target_attribute` values?
4. Is `assumptions` an **empty array**?
5. Do all `vvl_members` rows match CONFIRMED CSV content verbatim (code + description)?
6. Does `meta.dictionary_version` match `MANIFEST.yaml`?
7. Did you run the validator before finishing?

```bash
python tools/validate_research.py <path-to-research.yaml> [--integration-root <integration-project>]
```

Fix all validator errors before returning. Do **not** write the Integration Specification.

---

# Deliverable

**One file only:** `research/Integration_Research_<Flow>.yaml` in the per-integration project.

Do not write `spec/*.md`, do not run `md_to_docx.py`.
