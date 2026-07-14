# Agent Guidance — Medicare Validation Rules Library

This repository is a **read-only library** of Medicare / Medicaid (T-MSIS) validation rules,
prompt templates, and conventions used to generate Integration Specification documents.

## Two-phase Integration Specification workflow

Integration specs are generated in **two gated phases** with human review between them:

1. **Research (Turn 1)** — `@prompts/integration-spec-research.md`
   - Reads source layout, target VO, rules, and VVL CSVs.
   - Writes `research/Integration_Research_<Flow>.yaml` in the per-integration project.
   - Leaves `assumptions: []`; registers gaps only.
   - Validates: `python tools/validate_research.py <research.yaml> [--integration-root <path>]`

2. **Human review** — BA/SME approves the research YAML before writing the spec.

3. **Writer (Turn 2)** — `@prompts/integration-spec-write.md` in a **separate chat**
   - Input: research YAML only (not raw artifacts).
   - Writes `spec/Integration_Spec_....md`, then validates and exports Word.
   - Validates: `python tools/validate_spec_against_research.py <research.yaml> <spec.md>`
   - Exports: `python tools/md_to_docx.py <spec.md>`

The deprecated one-shot prompt `prompts/integration-spec-generation.md` redirects to this workflow.

## Operating rules for any agent working here

1. **Cite, never invent.** Every rule applied from this library MUST be tagged in the output as
   `Medicaid_Rule (ELG.xxx.xxx)` using the exact T-MSIS data-element id. Never fabricate enum
   constants, regex patterns, sentinel dates, business rules, timeouts, or character sets. Any value
   not derivable from a provided artifact must be declared as a `GAP-NN` / `ASM-NN` per the
   spec-generation conventions (see `.cursor/rules/medicaid-spec-conventions.mdc`).

2. **Read the generated text, not the binary.** For rule data, prefer `rules/**/data-elements.md`
   and `rules/**/data-elements.csv`. The `source.xlsx` is the record of truth but is binary; if you
   must re-derive text, run `tools/xlsx_to_text.py` rather than hand-typing values.

3. **Do not hand-edit generated files.** `data-elements.csv` / `data-elements.md` are produced by
   `tools/xlsx_to_text.py`. To change them, change `source.xlsx` and re-run the converter.

4. **Value lists.** When a rule references a named valid-value list (e.g. "Sex List"), the members
   live under `rules/<domain>/value-lists/`. If a list file is still a stub (members not filled in),
   treat the constants as a `GAP` (the T-MSIS workbook names the list but omits its members).

5. **Provenance.** When generating a spec, record the dictionary version from `MANIFEST.yaml`
   (currently T-MSIS `4.0.33`) so the output is traceable to a specific rule release.

6. **Scope.** Per-integration source layouts and target VOs do **not** belong in this repo; they
   live in their own integration project.

7. **Validators.** Install Python deps: `pip install -r requirements.txt`. Run validators before
   completing Research or Writer phases; fix all reported errors.
