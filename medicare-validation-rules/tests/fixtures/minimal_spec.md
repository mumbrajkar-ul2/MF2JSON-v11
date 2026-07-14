# Integration Specification: MES to CMdS (Member Eligibility)

## 1. Document Header & Executive Summary

T-MSIS dictionary version 4.0.33.

## 2. Gaps & Assumptions (Human-in-the-Loop Handoff)

### 2.2 GAPS — Information Missing from Source/Target Artifacts

| ID | Topic | What is missing from the inputs | Why it matters | Owner | Priority |
|---|---|---|---|---|---|
| GAP-01 | Source character encoding | Not stated in artifacts | Boundary decode | MMIS SME | P1 |

## 3. Core Technical Mapping Matrix

| MMIS Field Name | COBOL PICTURE Clause | Position / Length | CMdS Target Attribute Name | Target Java Data Type | Target JSON Schema Constraints | Transformation & Business Rules |
|---|---|---|---|---|---|---|
| CTR-INTF-DT | PIC X(08) | 1-8 / 8 | interfaceDate | LocalDate | string yyyyMMdd | slice bytes 1-8 |
| MBR-GNDR-CD | PIC X(04) | 435-438 / 4 | gender | String | max 4 | validate VVL — see §4.D |

## 4. Data Engineering & Transformation Nuances

**D. Code-to-Enum Normalization & Valid Value Lists**

| VVL Code | VVL Description | Target Enum / Canonical Value | Medicaid_Rule |
|---|---|---|---|
| F | Female | pass-through String | **Medicaid_Rule (ELG.002.023)** |
| M | Male | pass-through String | **Medicaid_Rule (ELG.002.023)** |
| U | Unknown | pass-through String | **Medicaid_Rule (ELG.002.023)** |

**E. Valid Value Lists Applied**

| CMdS Attribute | Source Field | T-MSIS DE | VVL Name | Value-List File | # Codes | §4.D Subsection | Status |
|---|---|---|---|---|---|---|---|
| gender | MBR-GNDR-CD | ELG.002.023 | Sex List | sex.csv | 3 | §4.D.1 | CONFIRMED |
