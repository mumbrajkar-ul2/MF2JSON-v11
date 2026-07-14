# Reference — Output Templates & Source Metadata

## Lookup report template

```markdown
# Authoritative Source Research: [Topic]

**Query:** [user request]
**Jurisdiction:** [federal | virginia | both]
**Retrieved:** [YYYY-MM-DD]

## Sources consulted

| Source | Tier | URL | Notes |
|--------|------|-----|-------|
| ... | tier_1 | ... | ... |

## Findings

### [Finding title]
- **Summary:** ...
- **Effective date:** ... (or GAP if not stated)
- **Source:** [Source name](URL) — retrieved YYYY-MM-DD
- **Local library comparison:** [matches | differs | not in library] — MANIFEST dictionary vX.Y.Z

## GAPs
- GAP-01: ...

## Spec impact (if applicable)
| Impacted artifact | Change type | Proposed action |
|-------------------|-------------|-----------------|
| Integration_Spec_... | LOV addition | Research phase update |
```

## Change-detection template

```markdown
# Change Detection Report

**Scan date:** YYYY-MM-DD
**Change feed sources:** [list entry URLs checked]

## Changes detected

### CHANGE-01: [title]
- **Detected at:** [source URL]
- **Published / effective:** ...
- **Domain:** provider | member | claims | plan | ...
- **Artifact type:** manual | bulletin | value-list | regulation | standard | file_layout
- **Rule/LOV detail:** ...
- **Impacted specs:** [integration spec names or rule paths]
- **Recommended action:** Route to BA/SME for approval
```

## Entity → source quick map

| Entity / topic | Federal (start here) | Virginia (start here) |
|----------------|----------------------|------------------------|
| Member / eligibility | T-MSIS, Medicaid.gov, eCFR | DMAS State Plan, SPAs, memos |
| Provider | T-MSIS, NPPES, NUCC | Provider Manuals, MES portal, downloads |
| Claims | T-MSIS, NCCI, X12 (limited) | Provider Manuals, memos, rates |
| Plan / managed care | Medicaid.gov waivers | Cardinal Care, MCO manuals |
| Pharmacy / PBM | MDRP, NCPDP | PDL/formulary, pharmacy bulletins |
| LOV / VVL | T-MSIS dictionary + VVL xlsx | Provider downloads (taxonomy etc.) |
| File layouts | T-MSIS Data Guide | MCO technical manuals |

## Crawlability notes

| Source | Constraint |
|--------|------------|
| X12 / WPC | Licensed; public summaries only |
| AMA CPT | Licensed; document GAP for code detail |
| NCPDP | Some content member-gated |
| CMS NCCI production files | RISSNET secure; use public reference pages only |

## Registry maintenance fields

When extending `source-url-registry.yaml`, include:

```yaml
- id: unique-id
  name: # matches CSV Source column
  jurisdiction: federal | virginia
  tier: tier_1 | tier_2 | tier_3 | tier_4
  domains: [hostname-only]
  entry_urls: [https://...]
  use_for: [entity tags]
  crawlable: true | limited
  priority_for: [optional high-priority tags]
  notes: optional
```

After adding a source, append new hostnames to `allowed_domains`.
