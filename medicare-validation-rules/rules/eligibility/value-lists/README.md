# Eligibility Valid-Value Lists (VVL)

The T-MSIS data dictionary (`../data-elements.md`) **references** these valid-value lists by name
(column `Valid Values`, e.g. "Sex List", "Eligibility Group List") but does **not** contain their
members. This directory is where those members are recorded so that Integration Specifications stop
emitting them as placeholders.

This directly resolves the recurring **GAP-28** ("T-MSIS valid-value-list constants not in workbook")
seen in generated specs.

## Status

All nine lists below are populated with `status = CONFIRMED` from the official CMS workbook
[T-MSIS Valid Value List](https://www.medicaid.gov/medicaid/data-systems/downloads/tmsis-data-dictionary-valid-value-list.xlsx)
(sheet `Valid Value List`). Re-run `_populate_vvl.py` at the workspace root (or refresh from that
URL) when CMS publishes an updated VVL.

**Note:** `preferred-language.csv` — populated from **Appendix G: ISO 639 Language Codes Reference**
in `authoritative-source-registry/Medicare Documents/2b-TMSIS_V2.4.0_Appendix.docx` (483 ISO 639-2
codes, uppercased for T-MSIS `X(3)`). Re-run `python tools/appendix_g_to_preferred_language.py`
when CMS publishes an updated appendices bundle.

## File format

Each `<list>.csv` has columns:

```
code,description,t_msis_data_element,valid_value_list_name,status
```

- `code` — the literal value as it appears in the source/extract (e.g. `M`, `01`).
- `description` — human-readable meaning.
- `t_msis_data_element` — the owning DE id (e.g. `ELG.002.023`).
- `valid_value_list_name` — the list name as cited in the dictionary.
- `status` — `TODO` until confirmed, then `CONFIRMED` with the supplying SME/date in the PR.

Until a row's `status` is `CONFIRMED`, treat the code set as a GAP in generated specs.

## Lists tracked here

| File | T-MSIS DE | List name | Maps to CMdS attribute |
|---|---|---|---|
| `sex.csv` | ELG.002.023 | Sex List | `gender` |
| `eligibility-group.csv` | ELG.005.087 | Eligibility Group List | `categoryOfEligibility` |
| `level-of-care-status.csv` | ELG.005.088 | Level of Care Status List | `levelOfCare` |
| `marital-status.csv` | ELG.003.034 | Marital Status List | `maritalStatus` |
| `veteran-indicator.csv` | ELG.003.039 | Veteran Indicator List | `veteransIndicator` |
| `preferred-language.csv` | ELG.003.046 | Preferred Language Code List (VVL → Appendix G ISO 639-2) | `languageCode` |
| `english-proficiency.csv` | ELG.003.045 | Primary Language Engl Prof List (dictionary name: Primary Language English Proficiency Code List) | `primaryLanguageEnglishProficiencyCode` |
| `household-size.csv` | ELG.003.047 | Household Size List | `householdSize` |
| `income-code.csv` | ELG.003.038 | Income Code List | (income, if mapped) |
