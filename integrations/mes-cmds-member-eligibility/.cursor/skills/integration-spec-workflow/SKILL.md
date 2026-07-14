---
name: integration-spec-workflow
description: >-
  Run the gated MES-to-CMdS Integration Specification pipeline (Research Turn 1,
  validate, human approve, Writer Turn 2 in a new chat, validate spec, Word export).
  Use when the user asks to run integration spec workflow, orchestration gates,
  or generate research/spec with validators.
disable-model-invocation: true
---

# Integration Spec Workflow (Gated)

Mirror the PowerShell orchestrator stages. **Do not** write into `medicare-validation-rules/rules/`.

## Prerequisites

- Multi-root workspace: integration project + `medicare-validation-rules`.
- `pip install -r medicare-validation-rules/requirements.txt`
- Optional: Pandoc for Word export.

Prefer the script when on Windows:

```powershell
.\scripts\run-integration-spec-workflow.ps1
```

## Stage 0 — Setup

Confirm paths exist:

- Integration `source/` layout and `target/` VO
- Library `rules/eligibility/data-elements.md` and `value-lists/`
- Python and validator tools on PATH

## Stage 1 — Research (Chat 1)

Emit this prompt (adjust paths from `scripts/workflow.config.json`):

```text
Run Integration Spec Research per @prompts/integration-spec-research.md.
- Flow: Member Eligibility
- Source layout: @source/MEMBERELIGIBILITY.csv
- Target VO: @target/MemberEligibilityVO.md
- Validation rules: @rules/eligibility/data-elements.md
- Value lists: @rules/eligibility/value-lists/

Write research/Integration_Research_MemberEligibility.yaml only. Do not write the spec.
```

**Cursor Task:** Only in Turn 1 — `explore`, `readonly: true` for heavy CSV/VO/rules scans. Parent writes the YAML.

## Stage 1b — Validate research (blocking)

```powershell
python ../../medicare-validation-rules/tools/validate_research.py research/Integration_Research_MemberEligibility.yaml --integration-root .
```

Stop on non-zero exit. Do not proceed to Writer until this passes.

## Stage 2 — Human approval (blocking)

Ask the user explicitly:

> Approve validated research YAML and proceed to Writer? (Y/n)

- **Y** (or Enter): continue.
- **n**: stop; do not emit Writer prompt.

Review focus: mappings, gaps, VVL members, `meta.dictionary_version`.

## Stage 3 — Writer (Chat 2 — **new chat**)

**Critical:** New chat only. Do not continue Research chat.

```text
Write Integration Specification per @prompts/integration-spec-write.md from
@research/Integration_Research_MemberEligibility.yaml only.

Deliver spec/*.md and run tools/md_to_docx.py for .docx.
```

Do **not** attach `@source/`, `@target/`, or `@rules/` in Writer.

## Stage 3b — Validate spec (blocking)

```powershell
python ../../medicare-validation-rules/tools/validate_spec_against_research.py research/Integration_Research_MemberEligibility.yaml spec/Integration_Spec_MES_to_CMdS_MemberEligibility.md
```

## Stage 4 — Word export (blocking)

```powershell
python ../../medicare-validation-rules/tools/md_to_docx.py spec/Integration_Spec_MES_to_CMdS_MemberEligibility.md
```

If Pandoc is missing, report clearly and suggest `.\export-spec-docx.ps1` after install.

## Done

List deliverables: `research/*.yaml`, `spec/*.md`, `spec/*.docx`.

## References

- `docs/Orchestration_Implementation_Plan.md`
- `docs/Integration_Spec_Creation_Architecture.md`
- `scripts/run-integration-spec-workflow.ps1`
