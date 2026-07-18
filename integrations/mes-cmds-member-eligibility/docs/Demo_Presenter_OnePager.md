# Integration Spec Generation — Demo Presenter One-Pager

**Flow:** MES → CMdS Member Eligibility  
**Duration:** 25–40 min (full live) · 15 min (pre-built artifacts) · 5 min (smoke test only)  
**Audience:** BAs, MMIS SMEs, integration leads  

**Companion docs:** [Architecture](Integration_Spec_Creation_Architecture.md) · [Orchestration plan](Orchestration_Implementation_Plan.md) · [README](../README.md)

---

## Pre-demo checklist (5 min before)

- [ ] Open `mes-cmds-member-eligibility.code-workspace` (integration + `medicare-validation-rules`)
- [ ] PowerShell terminal in Cursor (not cmd.exe double-click on `.ps1`)
- [ ] `pip install -r ../../medicare-validation-rules/requirements.txt`
- [ ] Optional: Pandoc on `PATH` for Word export
- [ ] Decide mode: **Full live** / **Artifact walkthrough** / **Smoke only**

```powershell
cd integrations\mes-cmds-member-eligibility
.\scripts\run-integration-spec-workflow.ps1 -SmokeTest   # warm-up (optional)
```

---

## Slide outline (aligned to architecture diagrams)

Use one slide per diagram in `docs/diagrams/` (render PNGs: `python docs/diagrams/render_diagrams_png.py`).

| Slide | Visual | Title | Key bullets |
|-------|--------|-------|-------------|
| 1 | `diagram-01-system-architecture` | Three-layer design | Rule library (shared) · Integration project (flow I/O) · Cursor orchestration (prompts + gates) |
| 2 | Problem | Why not one-shot? | 113 fields · dozens of VVL/rules · 800+ line spec · hard to review · hallucination risk |
| 3 | `diagram-02-workflow-stages` | Gated pipeline | Research → validate → **human review** → Writer (new chat) → validate → Word |
| 4 | Inputs | What we start with | `MEMBERELIGIBILITY.CPY/.csv` (1473 B, 113 fields) · `MemberEligibilityVO.md` · T-MSIS v4.0.33 rules |
| 5 | Turn 1 | Research artifact | YAML only · `source_ref` on every fact · `gaps[]` · `assumptions: []` · no spec prose |
| 6 | Gate 1 | `validate_research.py` | Schema · DE ids · VVL parity · dictionary version · blocking |
| 7 | HITL | Human review | Mappings · gaps · VVL members · semantic correctness |
| 8 | Turn 2 | Writer (new chat) | **Research YAML only** — no CSV/VO/rules in context |
| 9 | Gate 2 | `validate_spec_against_research.py` | §3 fields · §4 VVL ⊆ research · §2 GAP ids · blocking |
| 10 | Deliverables | Outputs | `research/*.yaml` · `spec/*.md` · `spec/*.docx` |
| 11 | `diagram-03-cursor-control-plane` | How Cursor enforces it | Prompts · phase rules · separate chats · validators |
| 12 | Roadmap | v1 vs future | Script + validators today · CI + CMS ingest (v2) · SDK headless (future) |

---

## Demo script (narration + actions)

### Open (2 min)

> We generate Integration Specifications for **Member Eligibility** — mainframe COBOL to CMdS Java — with every rule traceable to **T-MSIS v4.0.33**. We split work into **Research** (structured YAML) and **Writer** (prose from YAML only). Python validators and a human gate sit between phases.

**Show:** Slide 1 or `docs/Integration_Spec_Creation_Architecture.md` §1.

---

### Act 1 — Inputs & rule library (5 min)

| Show | Say |
|------|-----|
| `source/MEMBERELIGIBILITY.CPY` | Original copybook — BA / Research input (record of truth) |
| `source/MEMBERELIGIBILITY_generated.csv` | Tabular layout via `tools/cpy_to_csv.py` (113 fields) |
| `source/MEMBERELIGIBILITY.csv` | Optional golden for `--compare` only |
| `target/MemberEligibilityVO.md` | CMdS canonical VO |
| `medicare-validation-rules/rules/eligibility/` | Shared read-only T-MSIS rules + VVL CSVs |
| `MANIFEST.yaml` | Dictionary version pinned to **4.0.33** |

> Rules are **text-first** so Cursor can grep and cite. Every applied rule is tagged **`Medicaid_Rule (ELG.xxx.xxx)`**. We **cite, never invent**.

**Optional:** One field drill-down — e.g. `MBR-GNDR-CD` in CSV → gender property in VO.

---

### Act 2 — Orchestrator & smoke (3 min)

```powershell
.\scripts\run-integration-spec-workflow.ps1 -SmokeTest
.\scripts\run-integration-spec-workflow.ps1
```

> The script is the **runbook**: checks deps, prints Cursor prompts, waits for files, runs validators, blocks on approval. It does **not** call the LLM.

**Show:** `scripts/workflow.config.json`

---

### Act 3 — Turn 1 Research (8–15 min live)

**Chat 1** — paste prompt from script output (or below):

```text
Run Integration Spec Research per @prompts/integration-spec-research.md.
- Flow: Member Eligibility
- Source layout: @source/MEMBERELIGIBILITY.CPY
- Target VO: @target/MemberEligibilityVO.md
- Validation rules: @rules/eligibility/data-elements.md
- Value lists: @rules/eligibility/value-lists/

Write research/Integration_Research_MemberEligibility.yaml only. Do not write the spec.
```

> Output is **YAML only**: `field_mappings[]` (DIRECT / INFERRED / UNMAPPED), `gaps[]`, `vvl_members[]` with citations, `assumptions: []`.

Press **Enter** in terminal when `research/Integration_Research_MemberEligibility.yaml` exists.

**Gate 1** (script runs automatically):

```powershell
python ..\..\medicare-validation-rules\tools\validate_research.py research\Integration_Research_MemberEligibility.yaml --integration-root .
```

**Show in YAML:** `meta.dictionary_version` · sample mapping with `source_ref` · a `gaps[]` row · a `vvl_members[]` row.

---

### Act 4 — Human review (5 min)

Script asks: `Approve research and proceed to Writer? (Y/n)`

**Review checklist:**

1. All 113 source fields covered?
2. High-risk fields (SSN, DOB, gender, eligibility) — correct rule refs?
3. `GAP-NN` items honest (stubbed VVL, missing VO field)?
4. VVL codes match library CSVs verbatim?
5. `assumptions` still empty?

> Validators catch structure, not semantic mapping errors — this gate is where SMEs add judgment.

Type **Y** to continue.

---

### Act 5 — Turn 2 Writer (8–15 min live)

**Start a NEW Cursor chat** (do not continue Chat 1).

```text
Write Integration Specification per @prompts/integration-spec-write.md from
@research/Integration_Research_MemberEligibility.yaml only.

Deliver spec/*.md and run tools/md_to_docx.py for .docx.
```

> Writer **transcribes** research — §1 summary, §2 gaps, §3 matrix, §4 rules/VVL. Cannot add mappings, codes, or GAP ids beyond research.

Press **Enter** when `spec/Integration_Spec_MES_to_CMdS_MemberEligibility.md` exists.

**Gate 2 + Word** (script):

```powershell
python ..\..\medicare-validation-rules\tools\validate_spec_against_research.py research\Integration_Research_MemberEligibility.yaml spec\Integration_Spec_MES_to_CMdS_MemberEligibility.md
python ..\..\medicare-validation-rules\tools\md_to_docx.py spec\Integration_Spec_MES_to_CMdS_MemberEligibility.md
```

---

### Act 6 — Deliverables tour (5 min)

| File | For whom |
|------|----------|
| `research/Integration_Research_MemberEligibility.yaml` | Engineers, QA — diff-friendly contract |
| `spec/Integration_Spec_MES_to_CMdS_MemberEligibility.md` | Dev team — canonical in repo |
| `spec/Integration_Spec_MES_to_CMdS_MemberEligibility.docx` | SMEs, PMs — sign-off |

**Walk spec sections:** §2 gaps · §3 mapping matrix · §4.D/E VVL with `Medicaid_Rule (ELG.xxx.xxx)` tags.

---

### Close (2 min)

> **v1:** script + prompts + validators + human gate. **v2:** CI on PRs, CMS snapshot ingest. **Future:** Cursor SDK for headless two-turn runs. Each new flow is a thin integration project reusing the same library.

**Show:** Slide 12 or `docs/Orchestration_Implementation_Plan.md` §2.

---

## Short demo (15 min — pre-built artifacts)

Skip Acts 3 & 5 generation. Run smoke test → open existing YAML → review checklist → open spec §2/§3/§4 → run both validators manually → open `.docx`.

---

## Five messages to repeat

1. **Two phases, one truth** — research YAML is the contract.
2. **Cite, never invent** — rules and VVL from library only.
3. **Gates, not hope** — validators fail the pipeline on drift.
4. **Human review where it matters** — YAML before 800 lines of prose.
5. **New chat for Writer** — context isolation prevents invented mappings.

---

## Troubleshooting (live)

| Issue | Response |
|-------|----------|
| `.ps1` opens in Notepad | Use PowerShell or `scripts\run-integration-spec-workflow.cmd` |
| Research validation fails | Fix YAML, re-run Stage 1b — do not proceed to Writer |
| Spec drift validation fails | Writer exceeded research — trim spec or fix research |
| Pandoc missing | Markdown is complete; run `.\export-spec-docx.ps1` after install |
| Turn 1 too slow | Use pre-built YAML; narrate live Research as optional |

---

## Quick reference — copy/paste

**Orchestrator:**

```powershell
.\scripts\run-integration-spec-workflow.ps1
.\scripts\run-integration-spec-workflow.ps1 -LogFile workflow.log
```

**Manual validators:**

```powershell
python ..\..\medicare-validation-rules\tools\validate_research.py research\Integration_Research_MemberEligibility.yaml
python ..\..\medicare-validation-rules\tools\validate_spec_against_research.py research\Integration_Research_MemberEligibility.yaml spec\Integration_Spec_MES_to_CMdS_MemberEligibility.md
python ..\..\medicare-validation-rules\tools\md_to_docx.py spec\Integration_Spec_MES_to_CMdS_MemberEligibility.md
```

---

*Presenter one-pager for MES-to-CMdS Member Eligibility Integration Specification generation.*
