# Medicare Validation Rules — Shared Library

A version-controlled, **text-first** library of Medicare / Medicaid (T-MSIS) data-element
definitions and validation rules, shared across all Business Analysts so they can generate
**Integration Specification & Mapping Documents** with Cursor in a consistent, reviewable way.

> This repository is **read-only rule data + prompts + conventions**. It does **not** contain
> any single integration's source layout or target VO — those live in their own per-integration
> project (see [Per-integration projects](#per-integration-projects)).

---

## Why text-first?

Cursor's fast tools (Grep, semantic search, Read) operate on **text**, not binary. The original
rules ship as `.xlsx` (binary), which Cursor cannot read without a script. So for every rule set
we keep:

- `source.xlsx` — the binary **record of truth** (never edited by hand), and
- `data-elements.csv` / `data-elements.md` — **generated** text renderings that Cursor reads, greps, and cites.

The generated text is produced deterministically by [`tools/xlsx_to_text.py`](tools/xlsx_to_text.py).
Never hand-edit the generated files; re-run the converter instead.

---

## Layout

```text
medicare-validation-rules/
├── README.md                 ← you are here
├── AGENTS.md                 ← repo-wide agent guidance (auto-read by Cursor)
├── MANIFEST.yaml             ← provenance: source, dictionary version, validators
├── requirements.txt          ← Python deps for validators (pyyaml, jsonschema, openpyxl)
├── schemas/
│   └── integration-research.schema.json
├── .cursor/rules/
│   ├── medicaid-spec-conventions.mdc      ← always-on shared guardrails
│   ├── integration-spec-research.mdc      ← Turn 1 (invoke via @)
│   └── integration-spec-writer.mdc        ← Turn 2 (invoke via @)
├── prompts/
│   ├── integration-spec-research.md       ← Turn 1 procedure
│   ├── integration-spec-write.md          ← Turn 2 procedure
│   └── integration-spec-generation.md   ← deprecated redirect
├── tools/
│   ├── xlsx_to_text.py       ← deterministic xlsx → csv + md converter
│   ├── md_to_docx.py         ← integration spec .md → Word .docx (via Pandoc)
│   ├── validate_research.py  ← JSON Schema + semantic gate for research YAML
│   └── validate_spec_against_research.py  ← spec must not drift from research
└── rules/
    └── eligibility/
        ├── source.xlsx       ← record of truth (T-MSIS Eligibility dictionary)
        ├── data-elements.csv ← generated (VO-length-aligned for MES→CMdS)
        ├── data-elements.md  ← generated, human + Cursor readable
        └── value-lists/      ← VVL members (CONFIRMED from CMS VVL workbook; cite in specs)
```

For **MES → CMdS** Member Eligibility, `rules/eligibility/data-elements.md` has **Size**
rules aligned to CMdS `MemberEligibilityVO` `@Size(max)`. Refresh from `source.xlsx` with
`tools/xlsx_to_text.py`, then re-apply VO lengths with `tools/align_data_elements_to_vo.py`
(write to `rules/eligibility/`).

Add new rule domains as sibling folders under `rules/` (e.g. `rules/claims/`, `rules/provider/`,
`rules/managed-care/`), each following the same `source.xlsx` + generated-text + `value-lists/` shape.

---

## How a BA uses this with Cursor (two-phase workflow)

Integration specs use **Research → review → Write** to cut hallucination surface.

1. Open **both** this library **and** your per-integration project in one Cursor workspace
   (multi-root: `File > Add Folder to Workspace`). The `.cursor/rules/` here auto-applies shared
   conventions; invoke phase rules via `@` in each turn's prompt.

2. Install validator dependencies (once per machine):

   ```bash
   pip install -r requirements.txt
   ```

3. **Turn 1 — Research** (separate chat):

   ```text
   Run Integration Spec Research per @prompts/integration-spec-research.md.
   - Flow: Member Eligibility
   - Source layout: @source/MEMBERELIGIBILITY.CPY
   - Target VO: @target/MemberEligibilityVO.md
   - Validation rules: @rules/eligibility/data-elements.md
   - Value lists: @rules/eligibility/value-lists/

   Write research/Integration_Research_MemberEligibility.yaml only. Do not write the spec.
   ```

   Validate:

   ```bash
   python tools/validate_research.py path/to/research/Integration_Research_MemberEligibility.yaml
   ```

4. **Human review** — BA/SME approves the research YAML before writing the spec.

5. **Turn 2 — Writer** (new chat; research YAML only):

   ```text
   Write Integration Specification per @prompts/integration-spec-write.md from
   @research/Integration_Research_MemberEligibility.yaml only.

   Deliver spec/*.md and run tools/md_to_docx.py for .docx.
   ```

   Validate, then export Word:

   ```bash
   python tools/validate_spec_against_research.py research.yaml spec/Integration_Spec_....md
   python tools/md_to_docx.py spec/Integration_Spec_....md
   ```

The deprecated one-shot prompt [`integration-spec-generation.md`](prompts/integration-spec-generation.md)
redirects to this workflow.

Per-integration projects may ship a wrapper (e.g. `export-spec-docx.ps1`) for manual re-export after hand-edits to the `.md`.

---

## Per-integration projects

The source layout (`.CPY` / `.csv`) and target VO (`.md`) for a specific flow are **inputs to one
build** and belong in their own project, not here. Example in this workspace:
`integrations/mes-cmds-member-eligibility/`.

Each integration project holds:

- `research/Integration_Research_<Flow>.yaml` — Turn 1 structured artifact
- `spec/Integration_Spec_....md` + `.docx` — Turn 2 deliverables
- `docs/Orchestration_Implementation_Plan.md` + `.docx` — gated workflow scope and phased rollout (example: Member Eligibility integration project)

If your MES copybooks or CMdS canonical VOs become reused enterprise-wide, promote them to their own
shared catalogs (`mes-source-layouts/`, `cmds-canonical-vos/`) — still separate from this rules library.

---

## Regenerating the text renderings

```bash
python tools/xlsx_to_text.py rules/eligibility/source.xlsx
```

This writes `data-elements.csv` and `data-elements.md` next to the `.xlsx`. Run it (or a pre-commit
hook / CI step) whenever a `source.xlsx` changes so the text never drifts from the binary.

---

## Governance

- **Owner / CODEOWNERS:** the MMIS SME / data-steward owns `rules/`. Changes go through pull request.
- **Versioning:** [`MANIFEST.yaml`](MANIFEST.yaml) pins the exact dictionary version each rule set was
  built from, so a generated spec can state "validated against T-MSIS vX.Y.Z" and you get a clean diff
  when CMS publishes a new dictionary.
- **BAs consume, they don't hand-edit** rule data; they branch/clone and reference it.
