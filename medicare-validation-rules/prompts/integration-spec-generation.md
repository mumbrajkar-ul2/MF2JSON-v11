# Integration Specification Generation — Deprecated

This monolithic one-shot procedure has been **replaced** by a two-phase workflow that reduces
hallucination by separating research from prose generation.

## Use this instead

| Phase | Prompt | Output |
|-------|--------|--------|
| **Turn 1 — Research** | [`integration-spec-research.md`](integration-spec-research.md) | `research/Integration_Research_<Flow>.yaml` |
| **Turn 2 — Writer** | [`integration-spec-write.md`](integration-spec-write.md) | `spec/Integration_Spec_....md` + `.docx` |

Run Research and Writer in **separate chats**. The Writer must receive **only** the approved research
YAML — not raw CSV, VO, or rules.

## Quick prompts

**Research:**

```text
Run Integration Spec Research per @prompts/integration-spec-research.md.
- Flow: Member Eligibility
- Source layout: @source/MEMBERELIGIBILITY.CPY
- Target VO: @target/MemberEligibilityVO.md
- Validation rules: @rules/eligibility/data-elements.md
- Value lists: @rules/eligibility/value-lists/

Write research/Integration_Research_MemberEligibility.yaml only. Do not write the spec.
```

**Writer:**

```text
Write Integration Specification per @prompts/integration-spec-write.md from
@research/Integration_Research_MemberEligibility.yaml only.

Deliver spec/*.md and run tools/md_to_docx.py for .docx.
```

See the library [`README.md`](../README.md) and per-integration project README for validators and review gates.
