# Integration: MES → CMdS — Member Eligibility

Per-integration project for the **Member Eligibility** flow. This holds only **this flow's**
inputs, research artifact, and generated output. The reusable Medicare/T-MSIS validation rules,
spec-generation procedures, validators, and always-on conventions live in the shared
**`medicare-validation-rules`** library (open it alongside this project).

## Contents

```text
mes-cmds-member-eligibility/
├── source/
│   ├── MEMBERELIGIBILITY.CPY              ← COBOL copybook (BA / Research input; record of truth)
│   ├── MEMBERELIGIBILITY_generated.csv    ← derived via tools/cpy_to_csv.py (Research maps from this)
│   └── MEMBERELIGIBILITY.csv              ← optional golden reference for --compare only
├── target/
│   └── MemberEligibilityVO.md   ← CMdS canonical Java VO
├── tools/
│   └── cpy_to_csv.py            ← copybook → *_generated.csv
├── research/
│   └── Integration_Research_MemberEligibility.yaml  ← Turn 1 output (review before Write)
├── spec/
│   ├── Integration_Spec_MES_to_CMdS_MemberEligibility.md  ← Turn 2 output (canonical)
│   └── Integration_Spec_MES_to_CMdS_MemberEligibility.docx ← Word stakeholder deliverable
└── docs/
    ├── Integration_Spec_Creation_Architecture.md / .docx  ← system architecture
    └── Orchestration_Implementation_Plan.md / .docx       ← gated workflow scope and rollout plan
```

- Computed record length: **1473 bytes**, **113 fields** (`COMP` = 2 bytes, each `COMP-3 S9(7)V99` = 5 bytes).
- Research attaches the **`.CPY`**, then regenerates `MEMBERELIGIBILITY_generated.csv` with
  `python tools/cpy_to_csv.py source/MEMBERELIGIBILITY.CPY` before field mapping.

## How to (re)generate the spec (two-phase workflow)

Integration specs are generated in **two gated phases** with human review between them. Use
**separate Cursor chats** for Research and Writer so the Writer does not retain raw artifact reads.

For the full **gated orchestration scope and phased implementation plan**, see
[`docs/Orchestration_Implementation_Plan.md`](docs/Orchestration_Implementation_Plan.md) (Word:
[`docs/Orchestration_Implementation_Plan.docx`](docs/Orchestration_Implementation_Plan.docx)).

**Prerequisites:** Open this project **and** `medicare-validation-rules` in one workspace
(`mes-cmds-member-eligibility.code-workspace` or `File > Add Folder to Workspace`). Install validator
deps once: `pip install -r ../../medicare-validation-rules/requirements.txt`.

### Orchestrated workflow (recommended)

From the integration project root, run the gated pipeline (prompts, validators, approval, Word export).

**Use a PowerShell terminal** (Cursor terminal set to PowerShell, or Windows Terminal → PowerShell). If
`.\scripts\run-integration-spec-workflow.ps1` opens the file in Notepad, you are in **cmd.exe** or the
`.ps1` association is set to an editor — use the `.cmd` wrapper or invoke PowerShell explicitly:

```powershell
# PowerShell (preferred)
.\scripts\run-integration-spec-workflow.ps1

# Validator smoke test only
.\scripts\run-integration-spec-workflow.ps1 -SmokeTest
```

```cmd
REM Command Prompt (cmd.exe) — use the wrapper
scripts\run-integration-spec-workflow.cmd -SmokeTest
```

```powershell
# Explicit (works from cmd.exe too)
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-integration-spec-workflow.ps1 -SmokeTest
```

Do **not** double-click the `.ps1` file in Explorer; that often opens it in an editor instead of running it.

Optional: audit log (`-LogFile workflow.log`). Configuration: `scripts/workflow.config.json`. Cursor Skill
(manual invoke): `.cursor/skills/integration-spec-workflow/SKILL.md`.

### Manual two-turn workflow

Use separate Cursor chats when not using the orchestrator.

#### Turn 1 — Research

Send:

```text
Run Integration Spec Research per @prompts/integration-spec-research.md.
- Flow: Member Eligibility
- Source layout: @source/MEMBERELIGIBILITY.CPY
- Target VO: @target/MemberEligibilityVO.md
- Validation rules: @rules/eligibility/data-elements.md
- Value lists: @rules/eligibility/value-lists/

Write research/Integration_Research_MemberEligibility.yaml only. Do not write the spec.
```

Validate before review:

```powershell
python ..\..\medicare-validation-rules\tools\validate_research.py research\Integration_Research_MemberEligibility.yaml
```

### Human review gate

Review `research/Integration_Research_MemberEligibility.yaml` — mappings, gaps, and VVL members —
before Turn 2. This artifact is much smaller than the full spec.

#### Turn 2 — Writer (new chat)

Send **only** the research file and writer prompt:

```text
Write Integration Specification per @prompts/integration-spec-write.md from
@research/Integration_Research_MemberEligibility.yaml only.

Deliver spec/*.md and run tools/md_to_docx.py for .docx.
```

Validate before Word export:

```powershell
python ..\..\medicare-validation-rules\tools\validate_spec_against_research.py research\Integration_Research_MemberEligibility.yaml spec\Integration_Spec_MES_to_CMdS_MemberEligibility.md
python ..\..\medicare-validation-rules\tools\md_to_docx.py spec\Integration_Spec_MES_to_CMdS_MemberEligibility.md
```

Applied rules are tagged `Medicaid_Rule (ELG.xxx.xxx)`; VVL codes come from research `vvl_members`;
gaps from research `gaps` appear in §2.

**Prerequisite for Word output:** [Pandoc](https://pandoc.org/installing.html) on `PATH`
(Windows: `winget install --id JohnMacFarlane.Pandoc`).

## Manual Word re-export

If you edit the `.md` by hand or Pandoc was unavailable during generation, re-export without regenerating the full spec:

```powershell
.\export-spec-docx.ps1
```

Or:

```powershell
python ..\..\medicare-validation-rules\tools\md_to_docx.py spec\Integration_Spec_MES_to_CMdS_MemberEligibility.md
```

> **Note:** Mermaid diagrams in the spec appear as code blocks in Word. For branded headings/fonts, pass `--reference-doc` (see `medicare-validation-rules/tools/md_to_docx.py --help`).

## Notes

- Validation rules pinned to T-MSIS dictionary **v4.0.33** (see the library `MANIFEST.yaml`).
  `rules/eligibility/data-elements.md` / `.csv` are VO-length-aligned for this MES→CMdS flow
  (regenerate via `tools/align_data_elements_to_vo.py` in the rules library after refreshing
  from `source.xlsx` when needed).
- Value lists under `medicare-validation-rules/rules/eligibility/value-lists/` are populated from the
  [CMS T-MSIS Valid Value List workbook](https://www.medicaid.gov/medicaid/data-systems/downloads/tmsis-data-dictionary-valid-value-list.xlsx).
  Stubbed lists (`status = TODO`) surface as gaps in research and §2 of the spec.
- All shared tooling (validators, Word export, prompts) lives in `medicare-validation-rules`.
