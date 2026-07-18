# Integration Specification — Research Phase

This is **Turn 1** of the two-phase Integration Specification workflow. Produce a structured,
version-controlled **research artifact** (YAML). Do **not** write spec prose, MapStruct
interfaces, or Word export.

Also invoke `@.cursor/rules/integration-spec-research.mdc` for phase guardrails. Shared cite-never-invent
rules live in `@.cursor/rules/medicaid-spec-conventions.mdc`.

## How a BA invokes this (short prompt)

```text
Run Integration Spec Research per @prompts/integration-spec-research.md.
- Flow: Member Eligibility
- Source layout: @source/MEMBERELIGIBILITY.CPY
- Target VO: @target/MemberEligibilityVO.md
- Validation rules: @rules/eligibility/data-elements.md
- Value lists: @rules/eligibility/value-lists/

Write research/Integration_Research_MemberEligibility.yaml only. Do not write the spec.
```

Use a **separate chat** from the Writer phase so raw artifact reads do not bleed into Turn 2.

## Configuration Tokens (fill from the invoking prompt)

- **{{flowName}}** — Integration Flow Name (e.g. "Member Eligibility").
- **{{businessEntity}}** — Business Domain Entity (often same as flow name).
- **{{sourceLayout}}** — Source mainframe MES layout: COBOL copybook **`.CPY`** (record of truth).
- **{{targetVO}}** — Target CMdS Java VO canonical structure (`.md`).
- **{{validationRules}}** — Medicare/T-MSIS validation rules text rendering (`rules/<domain>/data-elements.md`).
- **{{valueLists}}** — T-MSIS valid-value-list members (`rules/<domain>/value-lists/*.csv`).

Record the dictionary version from `MANIFEST.yaml` in `meta.dictionary_version`.

---

# Role and Context

You are an expert Medicare Business Analyst performing **research** on integration artifacts.
Your primary deliverable is `research/Integration_Research_<Flow>.yaml` in the per-integration project,
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

# Step 0 — Derive tabular layout from copybook (required)

The BA attaches the **`.CPY`**. Before mapping fields:

1. From the **integration project root**, run:
   ```bash
   python tools/cpy_to_csv.py <path-to-copybook>
   ```
   Example: `python tools/cpy_to_csv.py source/MEMBERELIGIBILITY.CPY`
2. This writes `source/<stem>_generated.csv` (e.g. `MEMBERELIGIBILITY_generated.csv`).
3. If the converter exits non-zero, **stop** Turn 1 and report the error.
4. Use the generated CSV for PIC / positions / length / storage and for `field_mappings` coverage.
5. Do **not** hand-edit the generated CSV. Do **not** treat a golden/hand-maintained
   `MEMBERELIGIBILITY.csv` as the Research source layout (optional `--compare` only).

Allowed write exception: only `source/<stem>_generated.csv` via `cpy_to_csv.py` (plus the research YAML).

---

# Research Agent Rules (Critical)

1. **Inputs:** Read `.CPY`, target VO, rules, and VVLs. Regenerate `*_generated.csv` as Step 0; do not
   modify `.CPY`, golden layout CSVs, rules, or VVL CSVs.
2. **Every fact needs `source_ref`:** Prefer `<stem>_generated.csv:Lnn` for layout fields. Cite `.CPY`
   in gap evidence for COMP/USAGE / framing nuance when relevant.
3. **`gaps` only — no assumptions:** Leave `assumptions: []`. Register missing facts as `gaps[]` with evidence.
   Do **not** create `ASM-NN` entries in research.
4. **`derivation` values:**
   - `DIRECT` — explicit mapping documented in artifacts (name match, documented link).
   - `INFERRED` — positional or name-based mapping not explicitly documented.
   - `UNMAPPED` — source field with no target (or vice versa); explain in gap if unexpected.
5. **VVL members:** Copy **verbatim** from CONFIRMED CSV rows only (`status = CONFIRMED`). Each row needs
   `source_ref` pointing to the CSV line. Stubbed lists (`status = TODO`) → register a GAP; do not invent codes.
6. **Provenance checksums:** `meta.sources[]` must include the `.CPY` and the `*_generated.csv`
   (and the target VO). Compute SHA-256 of each at research time.
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

Write the research YAML to the integration project's `research/` folder. Filename example:
`research/Integration_Research_MemberEligibility.yaml`.

Schema: `@schemas/integration-research.schema.json` (in `medicare-validation-rules`).

Example shape (illustrative — produce complete coverage for the flow):

```yaml
meta:
  flow: Member Eligibility
  dictionary_version: "4.0.33"
  sources:
    - path: source/MEMBERELIGIBILITY.CPY
      sha256: "..."
    - path: source/MEMBERELIGIBILITY_generated.csv
      sha256: "..."
    - path: target/MemberEligibilityVO.md
      sha256: "..."

field_mappings:
  - source_field: MBR-GNDR-CD
    source_ref: "MEMBERELIGIBILITY_generated.csv:L30"
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
    evidence: "Not stated in MEMBERELIGIBILITY.CPY, MEMBERELIGIBILITY_generated.csv, or VO"
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

Include **every** field from the generated layout CSV in `field_mappings` (Member Eligibility: 113 rows).

---

# Research Self-Check Before Returning

1. Did Step 0 succeed (`cpy_to_csv.py` exit 0) and does `*_generated.csv` exist?
2. Does `field_mappings` cover **every** row in the generated layout CSV?
3. Does every mapping row have non-empty `source_ref` and `target_ref`?
4. Are there no duplicate `source_field` or `target_attribute` values?
5. Is `assumptions` an **empty array**?
6. Do all `vvl_members` rows match CONFIRMED CSV content verbatim (code + description)?
7. Does `meta.dictionary_version` match `MANIFEST.yaml`?
8. Does `meta.sources` include both the `.CPY` and the `*_generated.csv`?
9. Did you run the validator before finishing?

```bash
python tools/validate_research.py <path-to-research.yaml> [--integration-root <integration-project>]
```

Fix all validator errors before returning. Do **not** write the Integration Specification.

---

# Deliverable

**Primary:** `research/Integration_Research_<Flow>.yaml` in the per-integration project.

**Derived (Step 0):** `source/<stem>_generated.csv` via `tools/cpy_to_csv.py`.

Do not write `spec/*.md`, do not run `md_to_docx.py`.
