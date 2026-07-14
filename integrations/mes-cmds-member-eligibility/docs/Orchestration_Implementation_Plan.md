# Gated Orchestration — Implementation Plan

**Document purpose:** Define the complete scope, phased rollout, and operational gates for producing MES-to-CMdS Integration Specifications using Cursor (Research + Writer), Python validators, and a future orchestrator script.

**Audience:** Business Analysts, MMIS SMEs, integration leads, and engineers implementing the workflow.

**Companion:** [Integration_Spec_Creation_Architecture.md](Integration_Spec_Creation_Architecture.md) describes system architecture; this document describes **how to roll out and operate** the gated pipeline.

---

## 1. Vision

Business Analysts produce Integration Specifications through a **gated pipeline**:

1. Collect minimum inputs at the start of each stage.
2. **Research** (Cursor Turn 1) produces structured `research/*.yaml`.
3. Machine validation plus **human approval** of research.
4. **Writer** (new Cursor chat, Turn 2) produces `spec/*.md` from research only.
5. Drift validation and Word export.

**Orchestration** is primarily a **PowerShell script + runbook** (and optionally a Cursor Skill), not one supervisor agent calling Research and Writer sub-agents. **Cursor Task** is optional inside Turn 1 for read-only exploration only.

---

## 2. Current state vs target

| Capability | Status | Location |
|------------|--------|----------|
| Research / Writer prompts | Done | `medicare-validation-rules/prompts/` |
| Phase + always-on Cursor rules | Done | `medicare-validation-rules/.cursor/rules/` |
| Research JSON Schema | Done | `medicare-validation-rules/schemas/integration-research.schema.json` |
| `validate_research.py` | Done | `medicare-validation-rules/tools/validate_research.py` |
| `validate_spec_against_research.py` | Done | `medicare-validation-rules/tools/validate_spec_against_research.py` |
| `md_to_docx.py` | Done | `medicare-validation-rules/tools/md_to_docx.py` |
| Member Eligibility README (two-turn manual) | Done | `mes-cmds-member-eligibility/README.md` |
| Architecture documentation | Done | `docs/Integration_Spec_Creation_Architecture.md` |
| **Orchestrator script (gates + prompts)** | **Done** | `scripts/run-integration-spec-workflow.ps1` |
| **Workflow Cursor Skill** | **Done (optional)** | `.cursor/skills/integration-spec-workflow/` |
| **CMS / Medicaid.gov snapshot ingest** | **Planned (v2)** | `references/` |
| **CI validation on PR** | **Planned (v2)** | GitHub Actions |
| **Cursor SDK headless runs** | **Future** | — |

---

## 3. Complete scope

### 3.1 In scope

**Process and gates**

- Stage 0: Workspace and dependency checks.
- Stage 1: Research minimum inputs (flow, source, target, rules, value lists).
- Stage 1b: `validate_research.py` (blocking).
- Stage 2: Human approval of research YAML (explicit Y/n; optional reviewer metadata).
- Stage 3: Writer minimum input (research YAML path only; **new chat** reminder).
- Stage 3b: `validate_spec_against_research.py` (blocking).
- Stage 4: `md_to_docx.py` (blocking unless Pandoc missing with clear message).
- Optional audit log per stage (timestamp, stage, pass/fail).

**Orchestrator (primary Phase 1 deliverable)**

- PowerShell script (Windows-first; aligns with `export-spec-docx.ps1`).
- Resolves `medicare-validation-rules` relative to integration root.
- Prints or copies Turn 1 / Turn 2 prompts.
- Waits for file existence (`research/*.yaml`, `spec/*.md`).
- Invokes validators with correct exit-code handling.
- Config file: flow name, file names, library path.

**Cursor integration**

- Document when to use **Task** (`explore`, `readonly`) in Turn 1 only.
- Enforce separate Writer chat in script, README, and architecture doc.
- Optional Workflow Skill mirroring script gates.

**Documentation and testing**

- This plan and architecture doc; README cross-links.
- Orchestrator smoke test with validator fixtures.

### 3.2 Out of scope (v1)

| Item | Reason |
|------|--------|
| Single parent agent orchestrating Research + Writer via Task | Weak Writer context isolation |
| Agent writing into `medicare-validation-rules` | SME governance; read-only library |
| Live Medicaid.gov fetch during Research | Requires snapshot ingest pipeline |
| Full Markdown AST spec linter | High effort; validators are subset parity only |
| Auto-approve on validator pass without human Y/n | Process decision |
| CMdS deployment or PR automation | Different product |

### 3.3 Future scope (v2+)

- Python orchestrator (cross-platform).
- `references/` + CMS snapshot tooling + `MANIFEST` web source entries.
- GitHub Actions on `research/*.yaml` and `spec/*.md`.
- Cursor SDK pipeline for scheduled re-research.
- Stronger spec validator (orphan GAPs, target_attribute parity).
- `meta.approval` block in research schema.

---

## 4. Target architecture

![End-to-end orchestration workflow](diagrams/diagram-02-workflow-stages.png)

The orchestrator sits **outside** Cursor. It does not run the LLM; it checks files, runs validators, collects approvals, and emits prompts for the BA to paste into Cursor chats.

**Actors**

| Actor | Responsibility |
|-------|----------------|
| BA | Runs orchestrator, pastes prompts, opens chats, approves YAML |
| Orchestrator script | File checks, validators, prompt emission, gates |
| Research agent (Chat 1) | Reads artifacts; writes `research/*.yaml`; optional Task |
| Writer agent (Chat 2) | Reads research YAML only; writes `spec/*.md` |
| MMIS SME | Updates T-MSIS library (`source.xlsx`, VVL CSVs) via PR |

---

## 5. Implementation plan (phased)

### Phase 0 — Baseline verification (0.5 day) — P0

**Goal:** Confirm two-phase assets work before orchestration.

| Task | Acceptance criteria |
|------|---------------------|
| Multi-root workspace | `@prompts`, `@rules` resolve |
| Install deps | `pip install -r ../../medicare-validation-rules/requirements.txt` succeeds |
| Validator fixtures | `valid_research.yaml` passes; `invalid_research.yaml` fails |
| Manual or fixture dry-run | Blockers documented |

### Phase 1 — Orchestrator script (2–3 days) — P0

**Goal:** One command drives gates and prompt emission.

| Task | Details |
|------|---------|
| 1.1 | Create `scripts/run-integration-spec-workflow.ps1` |
| 1.2 | Stage 0: check source/target, library folder, Python, validators |
| 1.3 | Stage 1: emit Research prompt; pause until YAML exists |
| 1.4 | Stage 1b: run `validate_research.py`; exit or retry on fail |
| 1.5 | Stage 2: `Read-Host` approval; exit on decline |
| 1.6 | Stage 3: remind **new chat**; emit Writer prompt (research only) |
| 1.7 | Stage 3b–4: wait for spec; `validate_spec_against_research.py`; `md_to_docx.py` |
| 1.8 | Optional `-LogFile` with stage timestamps |
| 1.9 | Optional `scripts/workflow.config.json` for Member Eligibility defaults |

**Acceptance:** Script exits non-zero on validator failure or user decline; never modifies `medicare-validation-rules/rules/`.

### Phase 2 — Documentation (1 day) — P0

| Task | Details |
|------|---------|
| 2.1 | This document (`Orchestration_Implementation_Plan.md`) |
| 2.2 | Link from integration README and architecture doc |
| 2.3 | Regenerate Word export as needed |

### Phase 3 — Workflow Cursor Skill (1–2 days) — P1

| Task | Details |
|------|---------|
| 3.1 | `.cursor/skills/integration-spec-workflow/SKILL.md` |
| 3.2 | Mirror Phase 1 stages; use structured approval questions |
| 3.3 | Invoke explicitly (not always-on) |

### Phase 4 — Validator and schema hardening (1–2 days) — P1

| Task | Value |
|------|-------|
| 4.1 | Flag GAP ids in spec not in research | Close orphan gap hole |
| 4.2 | Check `target_attribute` in §3 | Stronger parity |
| 4.3 | Optional `meta.approval` in research schema | Record HITL in YAML |
| 4.4 | Resolve library paths in `validate_research` for snapshots | CMS references |

### Phase 5 — CI and governance (1–2 days) — P2

| Task | Details |
|------|---------|
| 5.1 | GitHub Action: validate research YAML on PR |
| 5.2 | Validate spec when `spec/*.md` changes |
| 5.3 | CODEOWNERS for `rules/` |

### Phase 6 — First production run (ongoing) — P0

| Task | Details |
|------|---------|
| 6.1 | End-to-end run for Member Eligibility (113 fields) |
| 6.2 | BA/SME sign-off on research YAML |
| 6.3 | Writer pass + spec validator + docx |
| 6.4 | Capture false positives and prompt tweaks |

---

## 6. Effort summary

| Phase | Effort | Priority |
|-------|--------|----------|
| 0 Baseline | 0.5 day | P0 |
| 1 Orchestrator script | 2–3 days | P0 |
| 2 Documentation | 1 day | P0 |
| 3 Workflow Skill | 1–2 days | P1 |
| 4 Validator hardening | 1–2 days | P1 |
| 5 CI | 1–2 days | P2 |
| 6 Production run | 2–5 calendar days | P0 |

**Minimum viable orchestration:** Phases 0 + 1 + 2 + 6.

---

## 7. Stage specification (orchestrator contract)

| Stage | ID | Minimum inputs | Automated action | Human gate | Output |
|-------|-----|----------------|------------------|------------|--------|
| Setup | 0 | Workspace paths | File and deps check | — | Continue or stop |
| Research prompt | 1 | Source, target, rules, VVL | Emit Turn 1 prompt | User runs Chat 1 | `research/*.yaml` |
| Validate research | 1b | YAML path | `validate_research.py` | — | Pass or fail |
| HITL | 2 | Validated YAML | — | **Approve Y/n** | Proceed or stop |
| Writer prompt | 3 | Research path only | Emit Turn 2 prompt + new chat reminder | User runs Chat 2 | `spec/*.md` |
| Validate spec | 3b | research + spec paths | `validate_spec_against_research.py` | — | Pass or fail |
| Export | 4 | spec `.md` | `md_to_docx.py` | — | `.docx` |
| Done | End | — | Summary | — | Deliverables list |

---

## 8. Cursor Task placement

**Cursor Task** launches a read-only subagent inside **Chat 1 (Research)** when large artifact scans are needed (e.g. mapping 113 CSV rows to the VO).

| Use Task | Do not use Task |
|----------|-----------------|
| Turn 1: `explore`, `readonly: true` | Turn 2 Writer |
| Heavy grep/read of CSV, VO, rules | Replacing `validate_research.py` |
| Returning cited findings to parent | Writing into `medicare-validation-rules` |

**Writer isolation:** Turn 2 runs in a **new chat** with `@research/*.yaml` only—not as a Task subagent under the Research parent (parent context would weaken isolation).

---

## 9. Roles and RACI

| Activity | BA | Orchestrator | Research agent | Writer agent | MMIS SME |
|----------|:--:|:------------:|:--------------:|:------------:|:--------:|
| Provide source/target | A | I | I | — | C |
| Run Research chat | R | I | R | — | — |
| Validate research YAML | R | A | — | — | C |
| Approve research | A | I | — | — | C |
| Run Writer chat | R | I | — | R | — |
| Validate spec / export docx | R | A | — | — | — |
| Update T-MSIS library | I | — | — | — | A |

*R = Responsible, A = Accountable, C = Consulted, I = Informed*

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| BA skips orchestrator | README primary path; optional CI on PR |
| Writer in same chat as Research | Script + Skill stress **new chat** |
| Validator false positives on §3/§4 | Tune regex; standardize Writer headings |
| Pandoc missing | Stage 4 error; `export-spec-docx.ps1` fallback |
| Research agent edits library | Rules + orchestrator never writes to `rules/` |
| Task subagent invents mappings | Parent writes YAML; `validate_research.py` catches VVL/DE errors |

---

## 11. Definition of done (program level)

- [x] BA can run **one script** from the integration project through Start-to-End gates.
- [x] Research YAML is validated before the approval prompt.
- [x] Writer prompt is issued only after explicit approval.
- [x] Spec is validated against research before Word export.
- [x] Documentation includes orchestration flow and Task placement.
- [ ] Member Eligibility deliverables (`research/*.yaml`, `spec/*.md`, `spec/*.docx`) traceable to T-MSIS dictionary version in `MANIFEST.yaml` — verify on next production run (Phase 6).

---

## 12. Recommended next action

Run **Phase 6** end-to-end on Member Eligibility using the orchestrator. Defer CI (Phase 5) until the script is proven in practice.

**Orchestrator entry:**

```powershell
.\scripts\run-integration-spec-workflow.ps1
.\scripts\run-integration-spec-workflow.ps1 -SmokeTest
```

---

## 13. Related documents

| Document | Path |
|----------|------|
| Integration project README | `../README.md` |
| System architecture | `Integration_Spec_Creation_Architecture.md` |
| Research prompt | `medicare-validation-rules/prompts/integration-spec-research.md` |
| Writer prompt | `medicare-validation-rules/prompts/integration-spec-write.md` |
| Provenance manifest | `medicare-validation-rules/MANIFEST.yaml` |
| Agent guidance | `medicare-validation-rules/AGENTS.md` |

---

*Canonical Markdown: `docs/Orchestration_Implementation_Plan.md`. Regenerate Word:*

```powershell
python ..\..\..\medicare-validation-rules\tools\md_to_docx.py docs\Orchestration_Implementation_Plan.md
```
