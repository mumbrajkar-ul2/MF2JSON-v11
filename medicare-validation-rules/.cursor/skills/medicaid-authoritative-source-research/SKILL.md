---
name: medicaid-authoritative-source-research
description: >-
  Researches Medicaid/Medicare entities, rules, value-lists (LOVs), and standards
  updates from the Federal and Virginia authoritative source registry only.
  Use when the user asks to look up provider, member, claims, plan, eligibility,
  waiver, or PBM information; find T-MSIS rule or LOV changes; check standard
  updates; or keep integration/application specs current from official sources.
---

# Medicaid Authoritative Source Research

Research **only** from sources registered in this repository. Never fetch from
sites outside the registry allowlist.

## Registry files (read first)

| File | Purpose |
|------|---------|
| `authoritative-source-registry/Medicare-Authoritative-Source-Registry.csv` | Human catalog — source names and "Use it for" |
| `authoritative-source-registry/source-url-registry.yaml` | Entry URLs, domains, tiers, crawlability |
| `authoritative-source-registry/scripts/lookup_sources.py` | Filter sources by entity/jurisdiction/artifact |

## Hard constraints

1. **Allowlist only** — Before any `WebFetch`, validate the URL hostname:
   ```bash
   python authoritative-source-registry/scripts/lookup_sources.py --validate-url "https://example.com/page"
   ```
   Must return `ALLOWED`. If `DENIED`, stop and tell the user the URL is not in the registry.

2. **No invented facts** — Cite exact source name, URL, and retrieval date. Tag T-MSIS
   rules as `Medicaid_Rule (ELG.xxx.xxx)` when comparing to local library rules.

3. **Licensed / limited sources** — X12/WPC and AMA CPT are not fully crawlable.
   Document `GAP` when content requires a license.

4. **Tier 4 is interpretive** — ResDAC/MACPAC may support analysis but are not primary
   authority. Prefer Tier 1–3 when available.

5. **Do not use** KFF, vendor blogs, health-plan sites, or general web search results
   unless their hostname appears in `allowed_domains` in the YAML registry.

## Workflow

### Step 1 — Parse the request

Classify the user query:

| Dimension | Examples |
|-----------|----------|
| **Entity** | provider, member, claims, plan, eligibility, waiver, pharmacy, managed_care |
| **Artifact** | rule, LOV/VVL, standard, manual, bulletin, regulation, file_layout |
| **Jurisdiction** | federal, virginia, or both |
| **Intent** | lookup, change_detection, spec_impact |

### Step 2 — Select sources

Run lookup (from repo root `medicare-validation-rules/`):

```bash
python authoritative-source-registry/scripts/lookup_sources.py \
  --entity member --jurisdiction federal --artifact lov
```

Apply **source priority** from the CSV tier model:

1. **Tier 1** — Binding: CFR, Federal Register, CMS/CMCS guidance, approved SPAs/waivers
2. **Tier 2** — Operational: DMAS manuals, memos/bulletins, MCO contracts, fee schedules
3. **Tier 3** — Standards: T-MSIS, X12, NCPDP, HL7/FHIR, NUCC, NPPES, HCPCS, ICD
4. **Tier 4** — Interpretive: ResDAC, MACPAC (secondary only)

**High-priority starting sources** (from registry): T-MSIS Data Guide, CMS/CMCS policy
guidance, CMS NCCI Medicaid, Virginia DMAS Memos/Bulletins, Virginia Provider Manuals,
Virginia SPAs/Waivers, Cardinal Care resources, Virginia provider downloads/fee schedules.

### Step 3 — Fetch and extract

For each selected source:

1. Start at `entry_urls` from the YAML (not arbitrary search-engine links).
2. Fetch with `WebFetch`; follow in-site links only if the linked hostname stays on the allowlist.
3. Extract: definition, effective date, code values, file layout changes, bulletin references.
4. Record provenance for every fact.

If a page links off-registry (e.g., external vendor), note the link but do not fetch it.

### Step 4 — Compare to local library (when updating specs)

When the user asks about rules/LOVs for integration or application specs:

1. Read local artifacts: `rules/**/data-elements.md`, `rules/**/value-lists/*.csv`, `MANIFEST.yaml`
2. Diff authoritative findings against local dictionary version (e.g., T-MSIS `4.0.33`)
3. Flag additions, retirements, regex changes, new VVL members

Do **not** hand-edit generated rule files; propose changes for data steward review.

### Step 5 — Report

Use [reference.md](reference.md) output templates. Always include:

- Sources consulted (name, tier, URL, date accessed)
- Findings with direct quotes or paraphrase + citation
- GAPs where registry sources were insufficient or crawl-limited
- Spec impact summary when relevant

## Trigger examples

| User says | Action |
|-----------|--------|
| "Find T-MSIS rules for ELG00002 sex field" | `--entity member --artifact rule`; start T-MSIS Data Guide |
| "Any Virginia bulletin changes for provider enrollment?" | `--jurisdiction virginia --entity provider`; memos/bulletins + MES portal |
| "Update LOV for eligibility group" | `--artifact lov`; T-MSIS + local `value-lists/eligibility-group.csv` diff |
| "What's new in Medicaid NCCI edits?" | `--entity claims`; federal NCCI source |
| "Check if DMAS fee schedule changed" | `--jurisdiction virginia --entity provider`; rates + provider downloads |

## Change-detection mode

When asked to monitor or detect updates:

1. Note `last_checked` in your report (today's date).
2. Scan change feeds first: Virginia Memos/Bulletins, CMS/CMCS guidance index, T-MSIS dictionary release notes.
3. For each change, classify: domain → rule/LOV/schema → impacted specs → BA/SME approval route.

## Additional resources

- Output templates and tier details: [reference.md](reference.md)
- Integration spec conventions: `AGENTS.md`, `.cursor/rules/medicaid-spec-conventions.mdc`
