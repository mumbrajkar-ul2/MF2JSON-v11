# Integration Specification:  MES to CMdS ( Member Eligibility )

## 1. Document Header & Executive Summary

| Item | Value |
|---|---|
| **Title** | Integration Specification: MES to CMdS (Member Eligibility) |
| **Flow** | Member Eligibility |
| **T-MSIS Dictionary Version** | 4.0.33 |
| **Research Artifact** | `research/Integration_Research_MemberEligibility.yaml` |
| **Source Layout** | `source/MEMBERELIGIBILITY.CPY` / `source/MEMBERELIGIBILITY_generated.csv` (1473-byte fixed record) |
| **Target VO** | `target/MemberEligibilityVO.md` |

### Business Objective

Migrate flat, fixed-width MES Member Eligibility extract records into a typed, cloud-native CMdS domain model so claims, financials, and external (T-MSIS) validations operate on a canonical relational payload rather than mainframe copybook layouts.

### Target Architectural Pattern

The implementation team must build a deterministic pipeline:

1. **Ingestion** — Read the fixed-width legacy extract as raw `byte[]` to protect mixed-mode data (e.g. COMP-3 that may mimic line breaks). Record framing/terminator is unresolved (**GAP-11**); source charset is unresolved (**GAP-01**).
2. **Parsing & Slicing** — Extract alphanumeric and binary blocks using explicit array boundaries with `Math.min` upper-bound checks against the instantiated record length to eliminate `ArrayIndexOutOfBoundsException` from trailing truncation.
3. **Mapping & Conversion** — Map parsed properties into a type-safe intermediate Java Value Object (`MemberEligibilityVO`) via MapStruct.
4. **T-MSIS Validation** — Apply tagged **`Medicaid_Rule (ELG.xxx.xxx)`** checks and CONFIRMED VVLs from §4.D/E/F (dictionary **4.0.33**).
5. **Canonical JSON Serialization** — Emit canonical JSON from the VO.
6. **Idempotent CMdS REST Delivery** — POST to CMdS REST APIs for PostgreSQL persistence (API contract/SLA per **GAP-13**; natural key per **GAP-14**).

---

## 2. Gaps & Assumptions (Human-in-the-Loop Handoff)

### 2.1 Document Conventions for This Section

| Marker | Meaning |
|---|---|
| **GAP-NN** | Information missing from source/target/rule artifacts; requires BA/SME resolution before build treats the topic as confirmed. |
| **ASM-NN** | Placeholder assumption awaiting BA confirmation; each ASM traces to exactly one GAP and forward to ≥1 in-spec usage location. Research `assumptions` is empty — no ASM-NN entries invented in this Writer run. |
| **Medicaid_Rule (ELG.xxx.xxx)** | Applied T-MSIS data-element rule citation from research (`t_msis_rule` / VVL `de`). |
| **P1 / P2 / P3** | Priority: P1 blocks safe ingest/decode; P2 blocks complete validation/ops; P3 polish/character-class clarity. |
| **Owner roles** | MMIS SME, Sec/Compliance, CMdS API — as assigned in research `gaps[]`. |

### 2.2 GAPS — Information Missing from Source/Target Artifacts

| ID | Topic | What is missing from the inputs | Why it matters | Owner | Priority |
|---|---|---|---|---|---|
| GAP-01 | Source character encoding | MEMBERELIGIBILITY_generated.csv, MEMBERELIGIBILITY.CPY, and MemberEligibilityVO.md do not specify charset (e.g. ISO-8859-1 vs EBCDIC). | Blocks build-ready transformation rules until confirmed (Source character encoding). | MMIS SME | P1 |
| GAP-02 | CTR-SRVC-DT to serviceDate (YearMonth) | Source PIC X(08) at positions 9-16 (MEMBERELIGIBILITY_generated.csv:L3); VO serviceDate uses pattern yyyyMM (MemberEligibilityVO.md:L8-L10). Truncation/padding rules not stated in artifacts. | Blocks build-ready transformation rules until confirmed (CTR-SRVC-DT to serviceDate (YearMonth)). | MMIS SME | P1 |
| GAP-03 | MBR-GNDR-CD width and code normalization | Source PIC X(04) at 435-438 (MEMBERELIGIBILITY_generated.csv:L30); VO gender @Size(max=1) with pattern [MFU]? (MemberEligibilityVO.md:L126-L129); T-MSIS Sex is X(1) per ELG.002.023. | Blocks build-ready transformation rules until confirmed (MBR-GNDR-CD width and code normalization). | MMIS SME | P1 |
| GAP-04 | Race valid value list | MBR-RACE-CD mapped to race (ELG.016.213 per data-elements.csv) but no CONFIRMED race VVL CSV under rules/eligibility/value-lists/. | Blocks build-ready transformation rules until confirmed (Race valid value list). | MMIS SME | P1 |
| GAP-05 | Eligibility termination reason code | MBR-TERM-RSN-CD mapped to eligibilityTerminationReasonCode with t_msis_rule ELG.005.095 (MEMBERELIGIBILITY_generated.csv:L37; MemberEligibilityVO.md:L157); Eligibility Termination Reason List is not present as a CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks build-ready transformation rules until confirmed (Eligibility termination reason code). | MMIS SME | P2 |
| GAP-06 | Federal match code | MBR-FED-MCH-CD present in layout (MEMBERELIGIBILITY_generated.csv:L38); no CONFIRMED VVL CSV in value-lists/ for federalMatchCode. | Blocks build-ready transformation rules until confirmed (Federal match code). | MMIS SME | P2 |
| GAP-07 | COMP-3 packed decimal decode | LTC liability and rate amount fields use PIC S9(7)V99 COMP-3; VO uses @Digits(integer=7, fraction=2) but byte order/sign nibble rules not documented in copybook or VO. | Blocks build-ready transformation rules until confirmed (COMP-3 packed decimal decode). | MMIS SME | P1 |
| GAP-08 | HH-SIZE-NUM binary COMP | Source PIC 9(04) COMP (2 bytes) at 1422-1423 (MEMBERELIGIBILITY_generated.csv:L110); VO householdSize is Integer (MemberEligibilityVO.md:L461-L462); COMP endianness not stated in MEMBERELIGIBILITY.CPY. | Blocks build-ready transformation rules until confirmed (HH-SIZE-NUM binary COMP). | MMIS SME | P2 |
| GAP-09 | Sentinel / default dates | Multiple PIC X(08) date fields in layout; VO @JsonFormat yyyyMMdd on date fields without documented sentinel handling (e.g. 00000000, 99999999) in artifacts. | Blocks build-ready transformation rules until confirmed (Sentinel / default dates). | MMIS SME | P2 |
| GAP-10 | Phone number formatting | MBR-PHN-NUM and related fields PIC X(12) in source; VO memberContactNumber @Size(max=10) (MemberEligibilityVO.md:L105-L107). Strip/pad rules not stated. | Blocks build-ready transformation rules until confirmed (Phone number formatting). | MMIS SME | P2 |
| GAP-11 | Record framing and file terminator | MEMBERELIGIBILITY_generated.csv defines a 1473-byte fixed layout (SRC-FILE-NM ends at 1473); no LF/CRLF, RDW, or block descriptor documented in .CPY or VO. | Blocks build-ready transformation rules until confirmed (Record framing and file terminator). | MMIS SME | P1 |
| GAP-12 | HIPAA / PHI handling for DLQ records | MEMBERELIGIBILITY layout and MemberEligibilityVO.md contain SSN and demographic PHI; no dead-letter redaction or retention policy in provided artifacts. | Blocks build-ready transformation rules until confirmed (HIPAA / PHI handling for DLQ records). | Sec/Compliance | P1 |
| GAP-13 | CMdS operations (API contract, file arrival, SLA, observability) | Integration project provides MemberEligibilityVO.md only; no OpenAPI contract, batch file arrival, SLA, or observability artifacts. | Blocks build-ready transformation rules until confirmed (CMdS operations (API contract, file arrival, SLA, observability)). | CMdS API | P2 |
| GAP-14 | Natural-key format and validation | No composite ingest key (e.g. medicaidCardId + serviceDate + providerId) documented in MEMBERELIGIBILITY_generated.csv, .CPY, or MemberEligibilityVO.md. | Blocks build-ready transformation rules until confirmed (Natural-key format and validation). | MMIS SME | P2 |
| GAP-15 | Cross-field date ordering rules | T-MSIS data-elements.md documents period ordering for many date pairs; integration artifacts do not state which pairs apply at the MES→CMdS boundary. | Blocks build-ready transformation rules until confirmed (Cross-field date ordering rules). | MMIS SME | P2 |
| GAP-16 | Veterans indicator code normalization | T-MSIS Veteran Indicator List uses codes 0/1 (veteran-indicator.csv); VO veteransIndicator pattern [YN]? (MemberEligibilityVO.md:L448-L451). Mapping not stated in artifacts. | Blocks build-ready transformation rules until confirmed (Veterans indicator code normalization). | MMIS SME | P2 |
| GAP-17 | Level of care code width | Source LTC-LVL-CARE-CD PIC X(04) at 531-534 (MEMBERELIGIBILITY_generated.csv:L45); VO levelOfCare @Size(max=2) (MemberEligibilityVO.md:L191-L193); T-MSIS ELG.005.088 is X(3). Truncation/padding rules not stated. | Blocks build-ready transformation rules until confirmed (Level of care code width). | MMIS SME | P2 |
| GAP-18 | Marital status code width | Source MRTL-STAT-CD PIC X(04) at 1380-1383 (MEMBERELIGIBILITY_generated.csv:L106); VO maritalStatus @Size(max=1) (MemberEligibilityVO.md:L444-L446); T-MSIS ELG.003.034 uses 2-character codes (marital-status.csv). Normalization not stated. | Blocks build-ready transformation rules until confirmed (Marital status code width). | MMIS SME | P2 |
| GAP-19 | Disability type code list | MBR-DSBL-TYP mapped to diabilityType with t_msis_rule ELG.017.224 (MEMBERELIGIBILITY_generated.csv:L33; MemberEligibilityVO.md:L139); Disability Type Code List is not present as a CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks build-ready transformation rules until confirmed (Disability type code list). | MMIS SME | P2 |
| GAP-20 | Health home level code list | HH-LVL-CD present in layout (MEMBERELIGIBILITY_generated.csv:L42) mapped to healthHomeLevelCode (MemberEligibilityVO.md:L178); no CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks build-ready transformation rules until confirmed (Health home level code list). | MMIS SME | P2 |
| GAP-21 | Part D opt-out indicator legal values | MCR-PTD-OPT-IND present in layout (MEMBERELIGIBILITY_generated.csv:L65) mapped to partDOptOutIndex (MemberEligibilityVO.md:L273); Boolean/indicator legal values (Y/N, 1/0, blank) not stated in MEMBERELIGIBILITY_generated.csv, .CPY, or VO. | Blocks build-ready transformation rules until confirmed (Part D opt-out indicator legal values). | MMIS SME | P2 |
| GAP-22 | Lock-in assignment reason code list | LCK-ASGN-RSN present in layout (MEMBERELIGIBILITY_generated.csv:L98) mapped to lockinAssignmentReasonCode (MemberEligibilityVO.md:L409); no CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks build-ready transformation rules until confirmed (Lock-in assignment reason code list). | MMIS SME | P2 |
| GAP-23 | Lock-in change reason code list | LCK-CHG-RSN present in layout (MEMBERELIGIBILITY_generated.csv:L99) mapped to lockinChangeReasonCode (MemberEligibilityVO.md:L413); no CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks build-ready transformation rules until confirmed (Lock-in change reason code list). | MMIS SME | P2 |
| GAP-24 | Immigrant admission status code list | IMM-ADMS-STAT mapped to immigrantAdmissionStatus with t_msis_rule ELG.003.042 (MEMBERELIGIBILITY_generated.csv:L111; MemberEligibilityVO.md:L464); Immigration Status List is not present as a CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks build-ready transformation rules until confirmed (Immigrant admission status code list). | MMIS SME | P2 |
| GAP-25 | Per-field nullability / mandatory rules | VO has sparse nullability comments (e.g. medicareIdNumber, healthHomeNPIId); T-MSIS Necessity in data-elements.md is not aligned field-by-field to MES layout or JSR-380 constraints in MemberEligibilityVO.md. | Blocks build-ready transformation rules until confirmed (Per-field nullability / mandatory rules). | MMIS SME | P2 |
| GAP-26 | Name / free-text character class | Name and address PIC X fields (e.g. MBR-LAST-NM, MBR-FRST-NM) have no allowed character class documented in MEMBERELIGIBILITY_generated.csv, .CPY, or MemberEligibilityVO.md beyond @Size. | Blocks build-ready transformation rules until confirmed (Name / free-text character class). | MMIS SME | P3 |

### 2.3 ASSUMPTIONS — Placeholder Values Awaiting BA Confirmation

Research `assumptions: []` is empty. No **ASM-NN** placeholders are documented in this specification. Assumptions await BA fill-in after GAP resolution (do not invent ASM identifiers).

### 2.4 Outstanding Questions for the BA Team (in priority order)

**P1**

- **GAP-01** — Source character encoding: Confirm resolution of missing artifact detail (owner: MMIS SME).
- **GAP-02** — CTR-SRVC-DT to serviceDate (YearMonth): Confirm resolution of missing artifact detail (owner: MMIS SME).
- **GAP-03** — MBR-GNDR-CD width and code normalization: Confirm resolution of missing artifact detail (owner: MMIS SME).
- **GAP-04** — Race valid value list: Confirm resolution of missing artifact detail (owner: MMIS SME).
- **GAP-07** — COMP-3 packed decimal decode: Confirm resolution of missing artifact detail (owner: MMIS SME).
- **GAP-11** — Record framing and file terminator: Confirm resolution of missing artifact detail (owner: MMIS SME).
- **GAP-12** — HIPAA / PHI handling for DLQ records: Confirm resolution of missing artifact detail (owner: Sec/Compliance).

**P2**

- **GAP-05** — Eligibility termination reason code (owner: MMIS SME).
- **GAP-06** — Federal match code (owner: MMIS SME).
- **GAP-08** — HH-SIZE-NUM binary COMP (owner: MMIS SME).
- **GAP-09** — Sentinel / default dates (owner: MMIS SME).
- **GAP-10** — Phone number formatting (owner: MMIS SME).
- **GAP-13** — CMdS operations (API contract, file arrival, SLA, observability) (owner: CMdS API).
- **GAP-14** — Natural-key format and validation (owner: MMIS SME).
- **GAP-15** — Cross-field date ordering rules (owner: MMIS SME).
- **GAP-16** — Veterans indicator code normalization (owner: MMIS SME).
- **GAP-17** — Level of care code width (owner: MMIS SME).
- **GAP-18** — Marital status code width (owner: MMIS SME).
- **GAP-19** — Disability type code list (owner: MMIS SME).
- **GAP-20** — Health home level code list (owner: MMIS SME).
- **GAP-21** — Part D opt-out indicator legal values (owner: MMIS SME).
- **GAP-22** — Lock-in assignment reason code list (owner: MMIS SME).
- **GAP-23** — Lock-in change reason code list (owner: MMIS SME).
- **GAP-24** — Immigrant admission status code list (owner: MMIS SME).
- **GAP-25** — Per-field nullability / mandatory rules (owner: MMIS SME).

**P3**

- **GAP-26** — Name / free-text character class (owner: MMIS SME).

### 2.5 BA Sign-Off (to be completed before "Ready for Build")

| Checkpoint | Status | Approver | Date |
|---|---|---|---|
| All P1 GAPs resolved or explicitly deferred with signed risk acceptance | ☐ | | |
| All P2 GAPs resolved or scheduled with owners | ☐ | | |
| §3 field mappings reviewed against `MEMBERELIGIBILITY_generated.csv` / VO | ☐ | | |
| §4.D CONFIRMED VVL tables accepted for pipeline enforcement | ☐ | | |
| No unresolved invented values outside §2 | ☐ | | |
| **Build-Readiness Gate** — Ready for Build | ☐ | | |

---

## 3. Core Technical Mapping Matrix

One row per research `field_mappings[]` entry. Positions are 1-based inclusive from `MEMBERELIGIBILITY_generated.csv`. All mappings are research derivation **INFERRED**.

| MMIS Field Name | COBOL PICTURE Clause | Position / Length | CMdS Target Attribute Name | Target Java Data Type | Target JSON Schema Constraints | Transformation & Business Rules |
|---|---|---|---|---|---|---|
| CTR-INTF-DT | PIC X(08) | 1-8 / 8 | interfaceDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 1-8 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L2 → MemberEligibilityVO.md:L4. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| CTR-SRVC-DT | PIC X(08) | 9-16 / 8 | serviceDate | YearMonth | string; pattern yyyyMM | Boundary-safe slice bytes 9-16 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L3 → MemberEligibilityVO.md:L8. Map to YearMonth (yyyyMM); truncation/padding per GAP-02 / §4.B. |
| CTR-PROV-ID | PIC X(12) | 17-28 / 12 | providerId | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 17-28 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L4 → MemberEligibilityVO.md:L12. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CTR-PLAN-NM | PIC X(30) | 29-58 / 30 | planName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 29-58 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L5 → MemberEligibilityVO.md:L16. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CTR-MED-CRD-ID | PIC X(12) | 59-70 / 12 | medicaidCardId | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 59-70 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L6 → MemberEligibilityVO.md:L21. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CTR-MCILD-NUM | PIC X(12) | 71-82 / 12 | mciId | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 71-82 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L7 → MemberEligibilityVO.md:L25. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CTR-SSN-TXT | PIC X(12) | 83-94 / 12 | ssn | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 83-94 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L8 → MemberEligibilityVO.md:L29. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CTR-MCR-ID-NUM | PIC X(12) | 95-106 / 12 | medicareIdNumber | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 95-106 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L9 → MemberEligibilityVO.md:L34. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-LAST-NM | PIC X(30) | 107-136 / 30 | memberLastName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 107-136 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L10 → MemberEligibilityVO.md:L39. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-FRST-NM | PIC X(30) | 137-166 / 30 | memberFirstName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 137-166 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L11 → MemberEligibilityVO.md:L43. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-MID-NM | PIC X(30) | 167-196 / 30 | memberMiddleName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 167-196 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L12 → MemberEligibilityVO.md:L47. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-ML-ADR-LN1 | PIC X(30) | 197-226 / 30 | mailingAdressLine1 | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 197-226 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L13 → MemberEligibilityVO.md:L52. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-ML-ADR-LN2 | PIC X(30) | 227-256 / 30 | mailingAddressLine2 | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 227-256 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L14 → MemberEligibilityVO.md:L56. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-ML-CITY-NM | PIC X(30) | 257-286 / 30 | mailingAddressCity | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 257-286 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L15 → MemberEligibilityVO.md:L60. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-ML-ST-CD | PIC X(02) | 287-288 / 2 | mailingState | String | string; maxLength ≈ 2 (source PIC); VO @Size where stated | Boundary-safe slice bytes 287-288 (len 2); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L16 → MemberEligibilityVO.md:L64. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-ML-ZIP-5 | PIC X(05) | 289-293 / 5 | mailingZip5 | String | string; maxLength ≈ 5 (source PIC); VO @Size where stated | Boundary-safe slice bytes 289-293 (len 5); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L17 → MemberEligibilityVO.md:L68. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-ML-ZIP-4 | PIC X(04) | 294-297 / 4 | mailingZip4 | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 294-297 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L18 → MemberEligibilityVO.md:L73. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-RS-ADR-LN1 | PIC X(30) | 298-327 / 30 | residenceAdressLine1 | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 298-327 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L19 → MemberEligibilityVO.md:L79. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-RS-ADR-LN2 | PIC X(30) | 328-357 / 30 | residenceAddressLine2 | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 328-357 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L20 → MemberEligibilityVO.md:L83. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-RS-CITY-NM | PIC X(30) | 358-387 / 30 | residenceAddressCity | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 358-387 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L21 → MemberEligibilityVO.md:L87. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-RS-ST-CD | PIC X(02) | 388-389 / 2 | residenceState | String | string; maxLength ≈ 2 (source PIC); VO @Size where stated | Boundary-safe slice bytes 388-389 (len 2); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L22 → MemberEligibilityVO.md:L91. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-RS-ZIP-5 | PIC X(05) | 390-394 / 5 | residenceZip5 | String | string; maxLength ≈ 5 (source PIC); VO @Size where stated | Boundary-safe slice bytes 390-394 (len 5); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L23 → MemberEligibilityVO.md:L95. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-RS-ZIP-4 | PIC X(04) | 395-398 / 4 | residenceZip4 | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 395-398 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L24 → MemberEligibilityVO.md:L100. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-PHN-NUM | PIC X(12) | 399-410 / 12 | memberContactNumber | String | @Size(max=10) | Boundary-safe slice bytes 399-410 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L25 → MemberEligibilityVO.md:L105. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). Phone width/normalization per GAP-10. |
| MBR-GEO-CNTY-CD | PIC X(04) | 411-414 / 4 | geoCountyCode | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 411-414 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L26 → MemberEligibilityVO.md:L109. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-ADM-OFF-CD | PIC X(04) | 415-418 / 4 | adminOfficeCode | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 415-418 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L27 → MemberEligibilityVO.md:L113. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-DOB-DT | PIC X(08) | 419-426 / 8 | dateOfBirth | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 419-426 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L28 → MemberEligibilityVO.md:L118. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MBR-DOD-DT | PIC X(08) | 427-434 / 8 | dateOfDeath | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 427-434 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L29 → MemberEligibilityVO.md:L122. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MBR-GNDR-CD | PIC X(04) | 435-438 / 4 | gender | String | @Size(max=1); pattern [MFU]? | Boundary-safe slice bytes 435-438 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L30 → MemberEligibilityVO.md:L126. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). Normalize PIC X(04) to VO @Size(max=1) pattern [MFU]?; see GAP-03 / §4.D.1. **Medicaid_Rule (ELG.002.023)**. Validate against §4.D (sex.csv). |
| MBR-RACE-CD | PIC X(04) | 439-442 / 4 | race | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 439-442 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L31 → MemberEligibilityVO.md:L131. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). VVL members missing — GAP-04. **Medicaid_Rule (ELG.016.213)**. |
| MBR-LANG-CD | PIC X(04) | 443-446 / 4 | languageCode | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 443-446 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L32 → MemberEligibilityVO.md:L135. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). **Medicaid_Rule (ELG.003.046)**. Validate against §4.D (preferred-language.csv). |
| MBR-DSBL-TYP | PIC X(04) | 447-450 / 4 | diabilityType | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 447-450 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L33 → MemberEligibilityVO.md:L139. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). VVL members missing — GAP-19. **Medicaid_Rule (ELG.017.224)**. |
| MBR-PREG-DUE-DT | PIC X(08) | 451-458 / 8 | pregnancyDueDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 451-458 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L34 → MemberEligibilityVO.md:L143. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MBR-NPI-ID | PIC X(12) | 459-470 / 12 | npiId | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 459-470 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L35 → MemberEligibilityVO.md:L147. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MBR-ELIG-CAT | PIC X(04) | 471-474 / 4 | categoryOfEligibility | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 471-474 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L36 → MemberEligibilityVO.md:L153. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). **Medicaid_Rule (ELG.005.087)**. Validate against §4.D (eligibility-group.csv). |
| MBR-TERM-RSN-CD | PIC X(04) | 475-478 / 4 | eligibilityTerminationReasonCode | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 475-478 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L37 → MemberEligibilityVO.md:L157. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). VVL members missing — GAP-05. **Medicaid_Rule (ELG.005.095)**. |
| MBR-FED-MCH-CD | PIC X(04) | 479-482 / 4 | federalMatchCode | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 479-482 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L38 → MemberEligibilityVO.md:L161. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). VVL members missing — GAP-06. |
| HH-NPI-ID | PIC X(12) | 483-494 / 12 | healthHomeNPIId | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 483-494 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L39 → MemberEligibilityVO.md:L166. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| HH-BEG-DT | PIC X(08) | 495-502 / 8 | healthHomeBeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 495-502 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L40 → MemberEligibilityVO.md:L170. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| HH-END-DT | PIC X(08) | 503-510 / 8 | healthHomeEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 503-510 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L41 → MemberEligibilityVO.md:L174. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| HH-LVL-CD | PIC X(04) | 511-514 / 4 | healthHomeLevelCode | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 511-514 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L42 → MemberEligibilityVO.md:L178. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). VVL members missing — GAP-20. |
| LTC-BEG-DT | PIC X(08) | 515-522 / 8 | ltcBeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 515-522 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L43 → MemberEligibilityVO.md:L183. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| LTC-END-DT | PIC X(08) | 523-530 / 8 | ltcEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 523-530 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L44 → MemberEligibilityVO.md:L187. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| LTC-LVL-CARE-CD | PIC X(04) | 531-534 / 4 | levelOfCare | String | @Size(max=2) | Boundary-safe slice bytes 531-534 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L45 → MemberEligibilityVO.md:L191. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). Width normalize PIC X(04) vs VO @Size(max=2) / T-MSIS X(3); see GAP-17 / §4.D. **Medicaid_Rule (ELG.005.088)**. Validate against §4.D (level-of-care-status.csv). |
| LTC-CURR-BEG-DT | PIC X(08) | 535-542 / 8 | ltcPatientLiabilityCurrentBeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 535-542 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L46 → MemberEligibilityVO.md:L195. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| LTC-CURR-END-DT | PIC X(08) | 543-550 / 8 | ltcPatientLiabilityCurrentEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 543-550 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L47 → MemberEligibilityVO.md:L199. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| LTC-CURR-LIAB-AM | PIC S9(7)V99 COMP-3 | 551-555 / 5 | ltcPatientLiabilityCurrentAmount | BigDecimal | @Digits(integer=7, fraction=2) | Boundary-safe slice bytes 551-555 (len 5); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L48 → MemberEligibilityVO.md:L203. Unpack COMP-3 to BigDecimal; see §4.C / GAP-07. |
| LTC-PREV-BEG-DT | PIC X(08) | 556-563 / 8 | ltcPatientLiabilityPreviousBeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 556-563 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L49 → MemberEligibilityVO.md:L207. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| LTC-PREV-END-DT | PIC X(08) | 564-571 / 8 | ltcPatientLiabilityPreviousEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 564-571 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L50 → MemberEligibilityVO.md:L211. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| LTC-PREV-LIAB-AM | PIC S9(7)V99 COMP-3 | 572-576 / 5 | ltcPatientLiabilityPreviousAmount | BigDecimal | @Digits(integer=7, fraction=2) | Boundary-safe slice bytes 572-576 (len 5); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L51 → MemberEligibilityVO.md:L215. Unpack COMP-3 to BigDecimal; see §4.C / GAP-07. |
| DSBL-BEG-DT | PIC X(08) | 577-584 / 8 | disabilityBeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 577-584 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L52 → MemberEligibilityVO.md:L220. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| DSBL-END-DT | PIC X(08) | 585-592 / 8 | disabilityEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 585-592 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L53 → MemberEligibilityVO.md:L224. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MCR-PTA-BEG-DT | PIC X(08) | 593-600 / 8 | partABeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 593-600 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L54 → MemberEligibilityVO.md:L229. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MCR-PTA-END-DT | PIC X(08) | 601-608 / 8 | partAEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 601-608 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L55 → MemberEligibilityVO.md:L233. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MCR-PTB-BEG-DT | PIC X(08) | 609-616 / 8 | partBBeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 609-616 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L56 → MemberEligibilityVO.md:L237. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MCR-PTB-END-DT | PIC X(08) | 617-624 / 8 | partBEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 617-624 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L57 → MemberEligibilityVO.md:L241. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MCR-PTC-BEG-DT | PIC X(08) | 625-632 / 8 | partCBeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 625-632 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L58 → MemberEligibilityVO.md:L245. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MCR-PTC-END-DT | PIC X(08) | 633-640 / 8 | partCEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 633-640 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L59 → MemberEligibilityVO.md:L249. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MCR-PTC-CNTR-ID | PIC X(12) | 641-652 / 12 | partCPBPContractId | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 641-652 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L60 → MemberEligibilityVO.md:L253. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MCR-PBP-ORG-NM | PIC X(30) | 653-682 / 30 | pbpOrganizationName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 653-682 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L61 → MemberEligibilityVO.md:L257. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MCR-PTC-PLAN-NM | PIC X(30) | 683-712 / 30 | partCPBPPlanName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 683-712 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L62 → MemberEligibilityVO.md:L261. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MCR-PTD-BEG-DT | PIC X(08) | 713-720 / 8 | partDBeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 713-720 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L63 → MemberEligibilityVO.md:L265. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MCR-PTD-END-DT | PIC X(08) | 721-728 / 8 | partDEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 721-728 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L64 → MemberEligibilityVO.md:L269. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MCR-PTD-OPT-IND | PIC X(04) | 729-732 / 4 | partDOptOutIndex | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 729-732 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L65 → MemberEligibilityVO.md:L273. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). Legal values undefined — GAP-21. |
| MCR-PTD-CNTR-ID | PIC X(12) | 733-744 / 12 | partDPBPContractId | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 733-744 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L66 → MemberEligibilityVO.md:L277. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| MCR-PTD-PLAN-ID | PIC X(12) | 745-756 / 12 | partDPBPPlanID | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 745-756 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L67 → MemberEligibilityVO.md:L281. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CS-MGMT-NM | PIC X(30) | 757-786 / 30 | caseMgmtName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 757-786 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L68 → MemberEligibilityVO.md:L286. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CS-ADR-LN1 | PIC X(30) | 787-816 / 30 | caseMgmtAdressLine1 | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 787-816 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L69 → MemberEligibilityVO.md:L290. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CS-ADR-LN2 | PIC X(30) | 817-846 / 30 | caseMgmtAddressLine2 | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 817-846 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L70 → MemberEligibilityVO.md:L294. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CS-CITY-NM | PIC X(30) | 847-876 / 30 | caseMgmtAddressCity | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 847-876 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L71 → MemberEligibilityVO.md:L298. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CS-ST-CD | PIC X(02) | 877-878 / 2 | caseMgmtState | String | string; maxLength ≈ 2 (source PIC); VO @Size where stated | Boundary-safe slice bytes 877-878 (len 2); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L72 → MemberEligibilityVO.md:L302. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CS-ZIP-5 | PIC X(05) | 879-883 / 5 | caseMgmtZip5 | String | string; maxLength ≈ 5 (source PIC); VO @Size where stated | Boundary-safe slice bytes 879-883 (len 5); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L73 → MemberEligibilityVO.md:L306. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CS-ZIP-4 | PIC X(04) | 884-887 / 4 | caseMgmtZip4 | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 884-887 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L74 → MemberEligibilityVO.md:L310. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| CS-PHN-NUM | PIC X(12) | 888-899 / 12 | caseMgmtPhoneNum | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 888-899 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L75 → MemberEligibilityVO.md:L314. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). Phone width/normalization per GAP-10. |
| REP-LAST-NM | PIC X(30) | 900-929 / 30 | authRepLastName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 900-929 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L76 → MemberEligibilityVO.md:L319. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| REP-FRST-NM | PIC X(30) | 930-959 / 30 | authRepFirstName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 930-959 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L77 → MemberEligibilityVO.md:L323. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| REP-MID-NM | PIC X(30) | 960-989 / 30 | authRepMiddleName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 960-989 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L78 → MemberEligibilityVO.md:L327. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| REP-ADR-LN1 | PIC X(30) | 990-1019 / 30 | authRepAdressLine1 | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 990-1019 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L79 → MemberEligibilityVO.md:L331. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| REP-ADR-LN2 | PIC X(30) | 1020-1049 / 30 | authRepAddressLine2 | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1020-1049 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L80 → MemberEligibilityVO.md:L335. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| REP-CITY-NM | PIC X(30) | 1050-1079 / 30 | authRepAddressCity | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1050-1079 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L81 → MemberEligibilityVO.md:L339. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| REP-ST-CD | PIC X(02) | 1080-1081 / 2 | authRepState | String | string; maxLength ≈ 2 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1080-1081 (len 2); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L82 → MemberEligibilityVO.md:L343. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| REP-ZIP-5 | PIC X(05) | 1082-1086 / 5 | authRepZip5 | String | string; maxLength ≈ 5 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1082-1086 (len 5); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L83 → MemberEligibilityVO.md:L347. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| REP-ZIP-4 | PIC X(04) | 1087-1090 / 4 | authRepZip4 | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1087-1090 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L84 → MemberEligibilityVO.md:L351. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| REP-PHN-NUM | PIC X(12) | 1091-1102 / 12 | authRepPhoneNum | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1091-1102 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L85 → MemberEligibilityVO.md:L355. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). Phone width/normalization per GAP-10. |
| PY-LAST-NM | PIC X(30) | 1103-1132 / 30 | payeeLastName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1103-1132 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L86 → MemberEligibilityVO.md:L360. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| PY-FRST-NM | PIC X(30) | 1133-1162 / 30 | payeeFirstName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1133-1162 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L87 → MemberEligibilityVO.md:L364. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| PY-MID-NM | PIC X(30) | 1163-1192 / 30 | payeeMiddleName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1163-1192 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L88 → MemberEligibilityVO.md:L368. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| PY-ADR-LN1 | PIC X(30) | 1193-1222 / 30 | payeeAdressLine1 | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1193-1222 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L89 → MemberEligibilityVO.md:L372. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| PY-ADR-LN2 | PIC X(30) | 1223-1252 / 30 | payeeAddressLine2 | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1223-1252 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L90 → MemberEligibilityVO.md:L376. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| PY-CITY-NM | PIC X(30) | 1253-1282 / 30 | payeeAddressCity | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1253-1282 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L91 → MemberEligibilityVO.md:L380. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| PY-ST-CD | PIC X(02) | 1283-1284 / 2 | payeeState | String | string; maxLength ≈ 2 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1283-1284 (len 2); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L92 → MemberEligibilityVO.md:L384. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| PY-ZIP-5 | PIC X(05) | 1285-1289 / 5 | payeeZip5 | String | string; maxLength ≈ 5 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1285-1289 (len 5); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L93 → MemberEligibilityVO.md:L388. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| PY-ZIP-4 | PIC X(04) | 1290-1293 / 4 | payeeZip4 | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1290-1293 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L94 → MemberEligibilityVO.md:L392. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| PY-PHN-NUM | PIC X(12) | 1294-1305 / 12 | payeePhoneNum | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1294-1305 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L95 → MemberEligibilityVO.md:L396. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). Phone width/normalization per GAP-10. |
| LCK-BEG-DT | PIC X(08) | 1306-1313 / 8 | lockinBeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 1306-1313 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L96 → MemberEligibilityVO.md:L401. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| LCK-END-DT | PIC X(08) | 1314-1321 / 8 | lockinEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 1314-1321 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L97 → MemberEligibilityVO.md:L405. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| LCK-ASGN-RSN | PIC X(04) | 1322-1325 / 4 | lockinAssignmentReasonCode | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1322-1325 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L98 → MemberEligibilityVO.md:L409. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). VVL members missing — GAP-22. |
| LCK-CHG-RSN | PIC X(04) | 1326-1329 / 4 | lockinChangeReasonCode | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1326-1329 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L99 → MemberEligibilityVO.md:L413. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). VVL members missing — GAP-23. |
| HPLN-RT-AMT | PIC S9(7)V99 COMP-3 | 1330-1334 / 5 | hplanRateAmount | BigDecimal | @Digits(integer=7, fraction=2) | Boundary-safe slice bytes 1330-1334 (len 5); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L100 → MemberEligibilityVO.md:L418. Unpack COMP-3 to BigDecimal; see §4.C / GAP-07. |
| TOT-RT-AMT | PIC S9(7)V99 COMP-3 | 1335-1339 / 5 | totalRateAmount | BigDecimal | @Digits(integer=7, fraction=2) | Boundary-safe slice bytes 1335-1339 (len 5); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L101 → MemberEligibilityVO.md:L422. Unpack COMP-3 to BigDecimal; see §4.C / GAP-07. |
| XFER-PLN-ID | PIC X(12) | 1340-1351 / 12 | transferPlanId | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1340-1351 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L102 → MemberEligibilityVO.md:L427. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| FCLTY-ID | PIC X(12) | 1352-1363 / 12 | facilityId | String | string; maxLength ≈ 12 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1352-1363 (len 12); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L103 → MemberEligibilityVO.md:L431. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| BKG-DT | PIC X(08) | 1364-1371 / 8 | bookingDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 1364-1371 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L104 → MemberEligibilityVO.md:L435. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| RLSE-DT | PIC X(08) | 1372-1379 / 8 | releaseDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 1372-1379 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L105 → MemberEligibilityVO.md:L439. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MRTL-STAT-CD | PIC X(04) | 1380-1383 / 4 | maritalStatus | String | @Size(max=1) | Boundary-safe slice bytes 1380-1383 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L106 → MemberEligibilityVO.md:L444. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). Width normalize PIC X(04) vs VO @Size(max=1) / 2-char VVL; see GAP-18 / §4.D. **Medicaid_Rule (ELG.003.034)**. Validate against §4.D (marital-status.csv). |
| VET-IND-CD | PIC X(04) | 1384-1387 / 4 | veteransIndicator | String | pattern [YN]? | Boundary-safe slice bytes 1384-1387 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L107 → MemberEligibilityVO.md:L448. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). T-MSIS 0/1 vs VO [YN]? mapping per GAP-16 / §4.D. **Medicaid_Rule (ELG.003.039)**. Validate against §4.D (veteran-indicator.csv). |
| EMAIL-ADR-TXT | PIC X(30) | 1388-1417 / 30 | emailAddress | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1388-1417 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L108 → MemberEligibilityVO.md:L453. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |
| ENG-PRFCY-CD | PIC X(04) | 1418-1421 / 4 | primaryLanguageEnglishProficiencyCode | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1418-1421 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L109 → MemberEligibilityVO.md:L457. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). **Medicaid_Rule (ELG.003.045)**. Validate against §4.D (english-proficiency.csv). |
| HH-SIZE-NUM | PIC 9(04) COMP | 1422-1423 / 2 | householdSize | Integer | integer | Boundary-safe slice bytes 1422-1423 (len 2); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L110 → MemberEligibilityVO.md:L461. Decode binary COMP to Integer; see GAP-08. **Medicaid_Rule (ELG.003.047)**. Validate against §4.D (household-size.csv). |
| IMM-ADMS-STAT | PIC X(04) | 1424-1427 / 4 | immigrantAdmissionStatus | String | string; maxLength ≈ 4 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1424-1427 (len 4); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L111 → MemberEligibilityVO.md:L464. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). VVL members missing — GAP-24. **Medicaid_Rule (ELG.003.042)**. |
| MC-END-DT | PIC X(08) | 1428-1435 / 8 | mcEndDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 1428-1435 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L112 → MemberEligibilityVO.md:L468. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| MC-BEG-DT | PIC X(08) | 1436-1443 / 8 | mcBeginDate | LocalDate | string; @JsonFormat yyyyMMdd | Boundary-safe slice bytes 1436-1443 (len 8); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L113 → MemberEligibilityVO.md:L472. Parse PIC X(08) to LocalDate (yyyyMMdd); sentinel/high-date handling per GAP-09 / §4.B. |
| SRC-FILE-NM | PIC X(30) | 1444-1473 / 30 | fileName | String | string; maxLength ≈ 30 (source PIC); VO @Size where stated | Boundary-safe slice bytes 1444-1473 (len 30); decode ISO_8859_1 when alphanumeric; provenance MEMBERELIGIBILITY_generated.csv:L114 → MemberEligibilityVO.md:L476. Instantiate String with StandardCharsets.ISO_8859_1 then .trim() (§4.A). |

---

## 4. Data Engineering & Transformation Nuances

**A. String Normalization & Text Truncation**

Every alphanumeric field (`PIC X` equivalent) extracted via byte-array copy MUST invoke `.trim()` after instantiation with `StandardCharsets.ISO_8859_1`. Legacy trailing whitespace must be dropped at the ingestion threshold so padded widths do not pollute JSON or PostgreSQL columns. Source charset confirmation remains **GAP-01**. Name/address character-class rules remain **GAP-26**. Phone fields (`MBR-PHN-NUM` and related) have source PIC X(12) vs VO `@Size(max=10)` — **GAP-10**.

**B. Date Parsing & High-Date Logic**

Date fields are PIC X(08) mapped to `LocalDate` with VO `@JsonFormat yyyyMMdd`, except `CTR-SRVC-DT` → `serviceDate` (`YearMonth`, pattern `yyyyMM`) — truncation/padding rules are **GAP-02**. Sentinel/default dates (e.g. `00000000`, `99999999`) are not documented in artifacts — **GAP-09**. Cross-field period ordering at the MES→CMdS boundary is **GAP-15**. No ASM placeholders are asserted for high-date behavior until BA confirmation.

**C. Computational / Packed Decimals (COMP-3 Processing)**

The following fields use `PIC S9(7)V99 COMP-3` (5 bytes) → `BigDecimal` with `@Digits(integer=7, fraction=2)`: `LTC-CURR-LIAB-AM`, `LTC-PREV-LIAB-AM`, `HPLN-RT-AMT`, `TOT-RT-AMT`. Byte order and sign-nibble decode rules are not documented — **GAP-07**. `HH-SIZE-NUM` uses `PIC 9(04) COMP` (2 bytes) → `Integer`; endianness is **GAP-08**. Do not invent decode algorithms; implement only after SME confirmation of those GAPs.

**D. Code-to-Enum Normalization & Valid Value Lists**

CONFIRMED VVL members below are transcribed exclusively from research `vvl_members[]`. Pass-through `String` targets unless noted. Missing VVLs are listed as gaps in §2.2 (GAP-04, GAP-05, GAP-06, GAP-19, GAP-20, GAP-22, GAP-23, GAP-24).

#### 4.D.1 Sex List — **Medicaid_Rule (ELG.002.023)**

Source field `MBR-GNDR-CD` → target `gender`. Value-list file: `sex.csv`.

Note: Source PIC X(04) vs VO `@Size(max=1)` / T-MSIS X(1) — **GAP-03**.

| VVL Code | VVL Description | Target Enum / Canonical Value | Medicaid_Rule | Source Ref |
|---|---|---|---|---|
| F | Female | pass-through String | **Medicaid_Rule (ELG.002.023)** | sex.csv:L2 |
| M | Male | pass-through String | **Medicaid_Rule (ELG.002.023)** | sex.csv:L3 |
| U | Unknown | pass-through String | **Medicaid_Rule (ELG.002.023)** | sex.csv:L4 |

#### 4.D.2 Preferred Language List — **Medicaid_Rule (ELG.003.046)**

Source field `MBR-LANG-CD` → target `languageCode`. Value-list file: `preferred-language.csv`.

| VVL Code | VVL Description | Target Enum / Canonical Value | Medicaid_Rule | Source Ref |
|---|---|---|---|---|
| ABK | Abkhazian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L2 |
| KUT | Kutenai | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L3 |
| ACE | Achinese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L4 |
| LAD | Ladino | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L5 |
| ACH | Acoli | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L6 |
| LAH | Lahnda | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L7 |
| ADA | Adangme | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L8 |
| LAM | Lamba | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L9 |
| ADY | Adyghe; Adygei | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L10 |
| DAY | Land Dayak languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L11 |
| AAR | Afar | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L12 |
| LAO | Lao | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L13 |
| AFH | Afrihili | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L14 |
| LAT | Latin | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L15 |
| AFR | Afrikaans | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L16 |
| LAV | Latvian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L17 |
| AFA | Afro-Asiatic languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L18 |
| LEZ | Lezghian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L19 |
| AIN | Ainu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L20 |
| LIM | Limburgan; Limburger; Limburgish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L21 |
| AKA | Akan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L22 |
| LIN | Lingala | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L23 |
| AKK | Akkadian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L24 |
| LIT | Lithuanian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L25 |
| ALB | Albanian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L26 |
| JBO | Lojban | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L27 |
| NDS | Low German; Low Saxon; German, Low; Saxon, Low | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L28 |
| ALE | Aleut | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L29 |
| DSB | Lower Sorbian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L30 |
| ALG | Algonquian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L31 |
| LOZ | Lozi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L32 |
| TUT | Altaic languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L33 |
| LUB | Luba-Katanga | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L34 |
| AMH | Amharic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L35 |
| LUA | Luba-Lulua | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L36 |
| ANP | Angika | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L37 |
| LUI | Luiseno | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L38 |
| APA | Apache languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L39 |
| SMJ | Lule Sami | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L40 |
| ARA | Arabic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L41 |
| LUN | Lunda | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L42 |
| ARG | Aragonese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L43 |
| LUO | Luo (Kenya and Tanzania) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L44 |
| ARP | Arapaho | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L45 |
| LUS | Lushai | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L46 |
| ARW | Arawak | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L47 |
| LTZ | Luxembourgish; Letzeburgesch | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L48 |
| ARM | Armenian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L49 |
| MAC | Macedonian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L50 |
| RUP | Aromanian; Arumanian; Macedo-Romanian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L51 |
| MAD | Madurese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L52 |
| ART | Artificial languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L53 |
| MAG | Magahi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L54 |
| ASM | Assamese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L55 |
| MAI | Maithili | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L56 |
| AST | Asturian; Bable; Leonese; Asturleonese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L57 |
| MAK | Makasar | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L58 |
| ATH | Athapascan languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L59 |
| MLG | Malagasy | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L60 |
| AUS | Australian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L61 |
| MAY | Malay | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L62 |
| MAP | Austronesian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L63 |
| MAL | Malayalam | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L64 |
| AVA | Avaric | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L65 |
| MLT | Maltese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L66 |
| AVE | Avestan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L67 |
| MNC | Manchu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L68 |
| AWA | Awadhi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L69 |
| MDR | Mandar | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L70 |
| AYM | Aymara | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L71 |
| MAN | Mandingo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L72 |
| AZE | Azerbaijani | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L73 |
| MNI | Manipuri | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L74 |
| BAN | Balinese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L75 |
| MNO | Manobo languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L76 |
| BAT | Baltic languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L77 |
| GLV | Manx | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L78 |
| BAL | Baluchi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L79 |
| MAO | Maori | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L80 |
| BAM | Bambara | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L81 |
| ARN | Mapudungun; Mapuche | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L82 |
| BAI | Bamileke languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L83 |
| MAR | Marathi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L84 |
| BAD | Banda languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L85 |
| CHM | Mari | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L86 |
| BNT | Bantu languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L87 |
| MAH | Marshallese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L88 |
| BAS | Basa | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L89 |
| MWR | Marwari | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L90 |
| BAK | Bashkir | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L91 |
| MAS | Masai | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L92 |
| BAQ | Basque | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L93 |
| MYN | Mayan languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L94 |
| BTK | Batak languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L95 |
| MEN | Mende | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L96 |
| BEJ | Beja; Bedawiyet | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L97 |
| MIC | Mi'kmaq; Micmac | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L98 |
| BEL | Belarusian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L99 |
| MIN | Minangkabau | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L100 |
| BEM | Bemba | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L101 |
| MWL | Mirandese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L102 |
| BEN | Bengali | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L103 |
| MOH | Mohawk | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L104 |
| BER | Berber languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L105 |
| MDF | Moksha | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L106 |
| BHO | Bhojpuri | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L107 |
| LOL | Mongo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L108 |
| BIH | Bihari languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L109 |
| MON | Mongolian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L110 |
| BIK | Bikol | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L111 |
| MKH | Mon-Khmer languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L112 |
| BIN | Bini; Edo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L113 |
| MOS | Mossi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L114 |
| BIS | Bislama | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L115 |
| MUL | Multiple languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L116 |
| BYN | Blin; Bilin | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L117 |
| MUN | Munda languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L118 |
| ZBL | Blissymbols; Blissymbolics; Bliss | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L119 |
| NAH | Nahuatl languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L120 |
| NOB | Bokmål, Norwegian; Norwegian Bokmål | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L121 |
| NAU | Nauru | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L122 |
| BOS | Bosnian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L123 |
| NAV | Navajo; Navaho | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L124 |
| BRA | Braj | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L125 |
| NDE | Ndebele, North; North Ndebele | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L126 |
| BRE | Breton | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L127 |
| NBL | Ndebele, South; South Ndebele | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L128 |
| BUG | Buginese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L129 |
| NDO | Ndonga | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L130 |
| BUL | Bulgarian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L131 |
| NAP | Neapolitan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L132 |
| BUA | Buriat | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L133 |
| NEW | Nepal Bhasa; Newari | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L134 |
| BUR | Burmese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L135 |
| NEP | Nepali | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L136 |
| CAD | Caddo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L137 |
| NIA | Nias | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L138 |
| CAT | Catalan; Valencian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L139 |
| NIC | Niger-Kordofanian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L140 |
| CAU | Caucasian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L141 |
| SSA | Nilo-Saharan languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L142 |
| CEB | Cebuano | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L143 |
| NIU | Niuean | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L144 |
| CEL | Celtic languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L145 |
| NQO | N'Ko | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L146 |
| CAI | Central American Indian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L147 |
| NOG | Nogai | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L148 |
| KHM | Central Khmer | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L149 |
| NON | Norse, Old | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L150 |
| CHG | Chagatai | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L151 |
| NAI | North American Indian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L152 |
| CMC | Chamic languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L153 |
| FRR | Northern Frisian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L154 |
| CHA | Chamorro | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L155 |
| SME | Northern Sami | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L156 |
| CHE | Chechen | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L157 |
| NOR | Norwegian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L158 |
| CHR | Cherokee | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L159 |
| NNO | Norwegian Nynorsk; Nynorsk, Norwegian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L160 |
| CHY | Cheyenne | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L161 |
| NUB | Nubian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L162 |
| CHB | Chibcha | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L163 |
| NYM | Nyamwezi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L164 |
| NYA | Chichewa; Chewa; Nyanja | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L165 |
| NYN | Nyankole | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L166 |
| CHI | Chinese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L167 |
| NYO | Nyoro | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L168 |
| CHN | Chinook jargon | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L169 |
| NZI | Nzima | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L170 |
| CHP | Chipewyan; Dene Suline | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L171 |
| OCI | Occitan (post 1500) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L172 |
| CHO | Choctaw | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L173 |
| ARC | Official Aramaic (700-300 BCE); Imperial Aramaic (700-300 BCE) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L174 |
| CHU | Church Slavic; Old Slavonic; Church Slavonic; Old Bulgarian; Old Church Slavonic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L175 |
| OJI | Ojibwa | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L176 |
| CHK | Chuukese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L177 |
| ORI | Oriya | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L178 |
| CHV | Chuvash | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L179 |
| ORM | Oromo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L180 |
| NWC | Classical Newari; Old Newari; Classical Nepal Bhasa | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L181 |
| OSA | Osage | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L182 |
| SYC | Classical Syriac | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L183 |
| OSS | Ossetian; Ossetic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L184 |
| COP | Coptic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L185 |
| OTO | Otomian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L186 |
| COR | Cornish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L187 |
| PAL | Pahlavi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L188 |
| COS | Corsican | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L189 |
| PAU | Palauan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L190 |
| CRE | Cree | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L191 |
| PLI | Pali | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L192 |
| MUS | Creek | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L193 |
| PAM | Pampanga; Kapampangan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L194 |
| CRP | Creoles and pidgins | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L195 |
| PAG | Pangasinan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L196 |
| CPE | Creoles and pidgins, English based | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L197 |
| PAN | Panjabi; Punjabi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L198 |
| CPF | Creoles and pidgins, French-based | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L199 |
| PAP | Papiamento | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L200 |
| CPP | Creoles and pidgins, Portuguese-based | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L201 |
| PAA | Papuan languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L202 |
| CRH | Crimean Tatar; Crimean Turkish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L203 |
| NSO | Pedi; Sepedi; Northern Sotho | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L204 |
| HRV | Croatian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L205 |
| PER | Persian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L206 |
| CUS | Cushitic languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L207 |
| PEO | Persian, Old (ca.600-400 B.C.) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L208 |
| CZE | Czech | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L209 |
| PHI | Philippine languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L210 |
| DAK | Dakota | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L211 |
| PHN | Phoenician | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L212 |
| DAN | Danish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L213 |
| PON | Pohnpeian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L214 |
| DAR | Dargwa | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L215 |
| POL | Polish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L216 |
| DEL | Delaware | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L217 |
| POR | Portuguese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L218 |
| DIN | Dinka | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L219 |
| PRA | Prakrit languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L220 |
| DIV | Divehi; Dhivehi; Maldivian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L221 |
| PRO | Provençal, Old (to 1500);Occitan, Old (to 1500) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L222 |
| DOI | Dogri | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L223 |
| PUS | Pushto; Pashto | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L224 |
| DGR | Dogrib | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L225 |
| QUE | Quechua | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L226 |
| DRA | Dravidian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L227 |
| RAJ | Rajasthani | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L228 |
| DUA | Duala | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L229 |
| RAP | Rapanui | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L230 |
| DUM | Dutch, Middle (ca.1050-1350) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L231 |
| RAR | Rarotongan; Cook Islands Maori | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L232 |
| DUT | Dutch; Flemish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L233 |
| ROA | Romance languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L234 |
| DYU | Dyula | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L235 |
| RUM | Romanian; Moldavian; Moldovan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L236 |
| DZO | Dzongkha | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L237 |
| ROH | Romansh | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L238 |
| FRS | Eastern Frisian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L239 |
| ROM | Romany | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L240 |
| EFI | Efik | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L241 |
| RUN | Rundi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L242 |
| EGY | Egyptian (Ancient) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L243 |
| RUS | Russian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L244 |
| EKA | Ekajuk | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L245 |
| SAL | Salishan languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L246 |
| ELX | Elamite | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L247 |
| SAM | Samaritan Aramaic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L248 |
| ENG | English | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L249 |
| SMI | Sami languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L250 |
| ENM | English, Middle (1100-1500) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L251 |
| SMO | Samoan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L252 |
| ANG | English, Old (ca.450-1100) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L253 |
| SAD | Sandawe | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L254 |
| MYV | Erzya | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L255 |
| SAG | Sango | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L256 |
| EPO | Esperanto | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L257 |
| SAN | Sanskrit | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L258 |
| EST | Estonian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L259 |
| SAT | Santali | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L260 |
| EWE | Ewe | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L261 |
| SRD | Sardinian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L262 |
| EWO | Ewondo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L263 |
| SAS | Sasak | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L264 |
| FAN | Fang | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L265 |
| SCO | Scots | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L266 |
| FAT | Fanti | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L267 |
| SEL | Selkup | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L268 |
| FAO | Faroese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L269 |
| SEM | Semitic languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L270 |
| FIJ | Fijian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L271 |
| SRP | Serbian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L272 |
| FIL | Filipino; Pilipino | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L273 |
| SRR | Serer | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L274 |
| FIN | Finnish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L275 |
| SHN | Shan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L276 |
| FIU | Finno-Ugrian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L277 |
| SNA | Shona | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L278 |
| FON | Fon | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L279 |
| III | Sichuan Yi; Nuosu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L280 |
| FRE | French | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L281 |
| SCN | Sicilian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L282 |
| FRM | French, Middle (ca.1400-1600) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L283 |
| SID | Sidamo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L284 |
| FRO | French, Old (842-ca.1400) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L285 |
| SGN | Sign Languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L286 |
| FUR | Friulian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L287 |
| BLA | Siksika | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L288 |
| FUL | Fulah | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L289 |
| SND | Sindhi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L290 |
| GAA | Ga | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L291 |
| SIN | Sinhala; Sinhalese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L292 |
| GLA | Gaelic; Scottish Gaelic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L293 |
| SIT | Sino-Tibetan languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L294 |
| CAR | Galibi Carib | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L295 |
| SIO | Siouan languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L296 |
| GLG | Galician | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L297 |
| SMS | Skolt Sami | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L298 |
| LUG | Ganda | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L299 |
| DEN | Slave (Athapascan) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L300 |
| GAY | Gayo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L301 |
| SLA | Slavic languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L302 |
| GBA | Gbaya | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L303 |
| SLO | Slovak | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L304 |
| GEZ | Geez | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L305 |
| SLV | Slovenian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L306 |
| GEO | Georgian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L307 |
| SOG | Sogdian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L308 |
| GER | German | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L309 |
| SOM | Somali | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L310 |
| GMH | German, Middle High (ca.1050-1500) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L311 |
| SON | Songhai languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L312 |
| GOH | German, Old High (ca.750-1050) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L313 |
| SNK | Soninke | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L314 |
| GEM | Germanic languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L315 |
| WEN | Sorbian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L316 |
| GIL | Gilbertese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L317 |
| SOT | Sotho, Southern | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L318 |
| GON | Gondi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L319 |
| SAI | South American Indian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L320 |
| GOR | Gorontalo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L321 |
| ALT | Southern Altai | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L322 |
| GOT | Gothic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L323 |
| SMA | Southern Sami | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L324 |
| GRB | Grebo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L325 |
| SPA | Spanish; Castilian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L326 |
| GRC | Greek, Ancient (to 1453) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L327 |
| SRN | Sranan Tongo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L328 |
| GRE | Greek, Modern (1453-) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L329 |
| SUK | Sukuma | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L330 |
| GRN | Guarani | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L331 |
| SUX | Sumerian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L332 |
| GUJ | Gujarati | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L333 |
| SUN | Sundanese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L334 |
| GWI | Gwich'in | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L335 |
| SUS | Susu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L336 |
| HAI | Haida | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L337 |
| SWA | Swahili | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L338 |
| HAT | Haitian; Haitian Creole | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L339 |
| SSW | Swati | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L340 |
| HAU | Hausa | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L341 |
| SWE | Swedish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L342 |
| HAW | Hawaiian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L343 |
| GSW | Swiss German; Alemannic; Alsatian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L344 |
| HEB | Hebrew | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L345 |
| SYR | Syriac | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L346 |
| HER | Herero | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L347 |
| TGL | Tagalog | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L348 |
| HIL | Hiligaynon | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L349 |
| TAH | Tahitian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L350 |
| HIM | Himachali languages; Western Pahari languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L351 |
| TAI | Tai languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L352 |
| HIN | Hindi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L353 |
| TGK | Tajik | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L354 |
| HMO | Hiri Motu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L355 |
| TMH | Tamashek | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L356 |
| HIT | Hittite | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L357 |
| TAM | Tamil | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L358 |
| HMN | Hmong; Mong | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L359 |
| TAT | Tatar | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L360 |
| HUN | Hungarian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L361 |
| TEL | Telugu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L362 |
| HUP | Hupa | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L363 |
| TER | Tereno | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L364 |
| IBA | Iban | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L365 |
| TET | Tetum | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L366 |
| ICE | Icelandic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L367 |
| THA | Thai | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L368 |
| IDO | Ido | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L369 |
| TIB | Tibetan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L370 |
| IBO | Igbo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L371 |
| TIG | Tigre | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L372 |
| IJO | Ijo languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L373 |
| TIR | Tigrinya | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L374 |
| ILO | Iloko | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L375 |
| TEM | Timne | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L376 |
| SMN | Inari Sami | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L377 |
| TIV | Tiv | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L378 |
| INC | Indic languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L379 |
| TLI | Tlingit | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L380 |
| INE | Indo-European languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L381 |
| TPI | Tok Pisin | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L382 |
| IND | Indonesian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L383 |
| TKL | Tokelau | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L384 |
| INH | Ingush | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L385 |
| TOG | Tonga (Nyasa) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L386 |
| INA | Interlingua (International Auxiliary Language Association) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L387 |
| TON | Tonga (Tonga Islands) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L388 |
| ILE | Interlingue; Occidental | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L389 |
| TSI | Tsimshian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L390 |
| IKU | Inuktitut | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L391 |
| TSO | Tsonga | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L392 |
| IPK | Inupiaq | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L393 |
| TSN | Tswana | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L394 |
| IRA | Iranian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L395 |
| TUM | Tumbuka | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L396 |
| GLE | Irish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L397 |
| TUP | Tupi languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L398 |
| MGA | Irish, Middle (900-1200) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L399 |
| TUR | Turkish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L400 |
| SGA | Irish, Old (to 900) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L401 |
| OTA | Turkish, Ottoman (1500-1928) | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L402 |
| IRO | Iroquoian languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L403 |
| TUK | Turkmen | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L404 |
| ITA | Italian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L405 |
| TVL | Tuvalu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L406 |
| JPN | Japanese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L407 |
| TYV | Tuvinian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L408 |
| JAV | Javanese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L409 |
| TWI | Twi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L410 |
| JRB | Judeo-Arabic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L411 |
| UDM | Udmurt | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L412 |
| JPR | Judeo-Persian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L413 |
| UGA | Ugaritic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L414 |
| KBD | Kabardian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L415 |
| UIG | Uighur; Uyghur | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L416 |
| KAB | Kabyle | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L417 |
| UKR | Ukrainian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L418 |
| KAC | Kachin; Jingpho | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L419 |
| UMB | Umbundu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L420 |
| KAL | Kalaallisut; Greenlandic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L421 |
| MIS | Uncoded languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L422 |
| XAL | Kalmyk; Oirat | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L423 |
| UND | Undetermined | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L424 |
| KAM | Kamba | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L425 |
| HSB | Upper Sorbian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L426 |
| KAN | Kannada | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L427 |
| URD | Urdu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L428 |
| KAU | Kanuri | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L429 |
| UZB | Uzbek | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L430 |
| KRC | Karachay-Balkar | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L431 |
| VAI | Vai | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L432 |
| KAA | Kara-Kalpak | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L433 |
| VEN | Venda | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L434 |
| KRL | Karelian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L435 |
| VIE | Vietnamese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L436 |
| KAR | Karen languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L437 |
| VOL | Volapük | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L438 |
| KAS | Kashmiri | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L439 |
| VOT | Votic | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L440 |
| CSB | Kashubian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L441 |
| WAK | Wakashan languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L442 |
| KAW | Kawi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L443 |
| WLN | Walloon | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L444 |
| KAZ | Kazakh | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L445 |
| WAR | Waray | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L446 |
| KHA | Khasi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L447 |
| WAS | Washo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L448 |
| KHI | Khoisan languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L449 |
| WEL | Welsh | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L450 |
| KHO | Khotanese; Sakan | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L451 |
| FRY | Western Frisian | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L452 |
| KIK | Kikuyu; Gikuyu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L453 |
| WAL | Wolaitta; Wolaytta | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L454 |
| KMB | Kimbundu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L455 |
| WOL | Wolof | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L456 |
| KIN | Kinyarwanda | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L457 |
| XHO | Xhosa | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L458 |
| KIR | Kirghiz; Kyrgyz | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L459 |
| SAH | Yakut | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L460 |
| TLH | Klingon; tlhIngan-Hol | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L461 |
| YAO | Yao | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L462 |
| KOM | Komi | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L463 |
| YAP | Yapese | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L464 |
| KON | Kongo | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L465 |
| YID | Yiddish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L466 |
| KOK | Konkani | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L467 |
| YOR | Yoruba | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L468 |
| KOR | Korean | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L469 |
| YPK | Yupik languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L470 |
| KOS | Kosraean | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L471 |
| ZND | Zande languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L472 |
| KPE | Kpelle | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L473 |
| ZAP | Zapotec | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L474 |
| KRO | Kru languages | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L475 |
| ZZA | Zaza; Dimili; Dimli; Kirdki; Kirmanjki; Zazaki | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L476 |
| KUA | Kuanyama; Kwanyama | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L477 |
| ZEN | Zenaga | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L478 |
| KUM | Kumyk | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L479 |
| ZHA | Zhuang; Chuang | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L480 |
| KUR | Kurdish | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L481 |
| ZUL | Zulu | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L482 |
| KRU | Kurukh | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L483 |
| ZUN | Zuni | pass-through String | **Medicaid_Rule (ELG.003.046)** | preferred-language.csv:L484 |

#### 4.D.3 Eligibility Group List — **Medicaid_Rule (ELG.005.087)**

Source field `MBR-ELIG-CAT` → target `categoryOfEligibility`. Value-list file: `eligibility-group.csv`.

| VVL Code | VVL Description | Target Enum / Canonical Value | Medicaid_Rule | Source Ref |
|---|---|---|---|---|
| 01 | Parents and Other Caretaker Relatives | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L2 |
| 02 | Transitional Medical Assistance | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L3 |
| 03 | Extended Medicaid due to Earnings | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L4 |
| 04 | Extended Medicaid due to Spousal Support Collections | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L5 |
| 05 | Pregnant Women | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L6 |
| 06 | Deemed Newborns | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L7 |
| 07 | Infants and Children under Age 19 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L8 |
| 08 | Children with Title IV-E Adoption Assistance, Foster Care or Guardianship Care | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L9 |
| 09 | Former Foster Care Children | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L10 |
| 10 | Individuals at or below 133% FPL Age 19 through 64 / Non-pregnant individuals aged 19 through 64, not otherwise mandatorily eligible, with income at or below 133% FPL | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L11 |
| 11 | Individuals Receiving SSI | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L12 |
| 12 | Aged, Blind and Disabled Individuals in 209(b) States | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L13 |
| 13 | Individuals Receiving Mandatory State Supplements | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L14 |
| 14 | Individuals Who Are Essential Spouses | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L15 |
| 15 | Institutionalized Individuals Continuously Eligible Since 1973 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L16 |
| 16 | Blind or Disabled Individuals Eligible in 1973 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L17 |
| 17 | Individuals Who Lost Eligibility for SSI/SSP Due to an Increase in OASDI Benefits in 1972 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L18 |
| 18 | Individuals Who Would be Eligible for SSI/SSP but for OASDI COLA increases since April, 1977 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L19 |
| 19 | Disabled Widows and Widowers Ineligible for SSI due to Increase in OASDI | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L20 |
| 20 | Disabled Widows and Widowers Ineligible for SSI due to Early Receipt of Social Security | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L21 |
| 21 | Working Disabled under 1619(b) | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L22 |
| 22 | Disabled Adult Children | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L23 |
| 23 | Qualified Medicare Beneficiaries | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L24 |
| 24 | Qualified Disabled and Working Individuals | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L25 |
| 25 | Specified Low Income Medicare Beneficiaries | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L26 |
| 26 | Qualifying Individuals | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L27 |
| 27 | Optional Coverage of Parents and Other Caretaker Relatives | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L28 |
| 28 | Reasonable Classifications of Individuals under Age 21 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L29 |
| 29 | Children with Non-IV-E Adoption Assistance | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L30 |
| 30 | Independent Foster Care Adolescents | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L31 |
| 31 | Optional Targeted Low Income Children | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L32 |
| 32 | Individuals Electing COBRA Continuation Coverage | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L33 |
| 33 | Individuals above 133% FPL under Age 65 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L34 |
| 34 | Certain Individuals  Needing Treatment for Breast or Cervical Cancer | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L35 |
| 35 | Individuals Eligible for Family Planning Services | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L36 |
| 36 | Individuals with Tuberculosis | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L37 |
| 37 | Aged, Blind or Disabled Individuals Eligible for but Not Receiving Cash Assistance | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L38 |
| 38 | Individuals Eligible for Cash Assistance except for Institutionalization | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L39 |
| 39 | Individuals Receiving Home and Community Based Services under Institutional Rules | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L40 |
| 40 | Optional State Supplement Recipients - 1634 States, and SSI Criteria States with 1616 Agreements | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L41 |
| 41 | Optional State Supplement Recipients - 209(b) States, and SSI Criteria States without 1616 Agreements | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L42 |
| 42 | Institutionalized Individuals Eligible under a Special Income Level | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L43 |
| 43 | Individuals participating in a PACE Program under Institutional Rules | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L44 |
| 44 | Individuals Receiving Hospice Care | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L45 |
| 45 | Qualified Disabled Children under Age 19 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L46 |
| 46 | Poverty Level Aged or Disabled | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L47 |
| 47 | Work Incentives Eligibility Group | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L48 |
| 48 | Ticket to Work Basic Group | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L49 |
| 49 | Ticket to Work Medical Improvements Group | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L50 |
| 50 | Family Opportunity Act Children with Disabilities | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L51 |
| 51 | Individuals Eligible for Home and Community-Based Services | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L52 |
| 52 | Individuals Eligible for Home and Community-Based Services - Special Income Level | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L53 |
| 53 | Medically Needy Pregnant Women | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L54 |
| 54 | Medically Needy Children under Age 18 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L55 |
| 55 | Medically Needy Children Age 18 through 20 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L56 |
| 56 | Medically Needy Parents and Other Caretakers | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L57 |
| 59 | Medically Needy Aged, Blind or Disabled | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L58 |
| 60 | Medically Needy Blind or Disabled Individuals Eligible in 1973 | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L59 |
| 61 | Targeted Low-Income Children | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L60 |
| 62 | Deemed Newborn | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L61 |
| 63 | Children Ineligible for Medicaid Due to Loss of Income Disregards | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L62 |
| 64 | Coverage from Conception to Birth | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L63 |
| 65 | Children with Access to Public Employee Coverage | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L64 |
| 66 | Children Eligible for Dental Only Supplemental Coverage | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L65 |
| 67 | Targeted Low-Income Pregnant Women | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L66 |
| 68 | Pregnant Women with Access to Public Employee Coverage | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L67 |
| 69 | Individuals with Mental Health Conditions (expansion group) | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L68 |
| 70 | Family Planning Participants (expansion group) | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L69 |
| 71 | Other expansion group | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L70 |
| 72 | Adult Group - Individuals at or below 133% FPL Age 19 through 64 - newly eligible for all states | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L71 |
| 73 | Adult Group - Individuals at or below 133% FPL Age 19 through 64 - not newly eligible for non 1905z(3) states | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L72 |
| 74 | Adult Group - Individuals at or below 133% FPL Age 19 through 64 - not newly eligible parent/ caretaker-relative(s) in 1905z(3) states | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L73 |
| 75 | Adult Group - Individuals at or below 133% FPL Age 19 through 64 - not newly eligible non-parent/ caretaker-relative(s) in 1905z(3) states | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L74 |
| 76 | Uninsured Individual eligible for COVID-19 testing | pass-through String | **Medicaid_Rule (ELG.005.087)** | eligibility-group.csv:L75 |

#### 4.D.4 Level of Care Status List — **Medicaid_Rule (ELG.005.088)**

Source field `LTC-LVL-CARE-CD` → target `levelOfCare`. Value-list file: `level-of-care-status.csv`.

Note: Source PIC X(04) / VO `@Size(max=2)` / T-MSIS X(3) — **GAP-17**.

| VVL Code | VVL Description | Target Enum / Canonical Value | Medicaid_Rule | Source Ref |
|---|---|---|---|---|
| 001 | Hospital as defined in 42 CFR 440.10 | pass-through String | **Medicaid_Rule (ELG.005.088)** | level-of-care-status.csv:L2 |
| 002 | Inpatient psychiatric facility for individuals under age 21 as provided in 42 CFR  440.160 | pass-through String | **Medicaid_Rule (ELG.005.088)** | level-of-care-status.csv:L3 |
| 003 | Nursing Facility | pass-through String | **Medicaid_Rule (ELG.005.088)** | level-of-care-status.csv:L4 |
| 004 | ICF/IDD | pass-through String | **Medicaid_Rule (ELG.005.088)** | level-of-care-status.csv:L5 |
| 005 | Other Type of Facility | pass-through String | **Medicaid_Rule (ELG.005.088)** | level-of-care-status.csv:L6 |
| 888 | Not Applicable (Not in LTSS program) | pass-through String | **Medicaid_Rule (ELG.005.088)** | level-of-care-status.csv:L7 |

#### 4.D.5 Marital Status List — **Medicaid_Rule (ELG.003.034)**

Source field `MRTL-STAT-CD` → target `maritalStatus`. Value-list file: `marital-status.csv`.

Note: Source PIC X(04) / VO `@Size(max=1)` / VVL 2-character codes — **GAP-18**.

| VVL Code | VVL Description | Target Enum / Canonical Value | Medicaid_Rule | Source Ref |
|---|---|---|---|---|
| 01 | Legally Married (to opposite sex), spouse present | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L2 |
| 02 | Legally Married (to opposite sex), spouse absent | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L3 |
| 03 | Legally Married (to same sex), spouse present | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L4 |
| 04 | Legally Married (to same sex), spouse absent | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L5 |
| 05 | Partnered or in Civil Union (to opposite sex), spouse present | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L6 |
| 06 | Partnered or in Civil Union (to opposite sex), spouse absent | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L7 |
| 07 | Partnered or in Civil Union (to same sex), spouse present | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L8 |
| 08 | Partnered or in Civil Union (to same sex), spouse absent | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L9 |
| 09 | Legally separated (and not married or partnered) | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L10 |
| 10 | Divorced (and not currently married or partnered) | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L11 |
| 11 | Separated (and not currently married or partnered) | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L12 |
| 12 | Widower/Widow (and not currently married or partnered) | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L13 |
| 13 | Never married/partnered | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L14 |
| 14 | Other | pass-through String | **Medicaid_Rule (ELG.003.034)** | marital-status.csv:L15 |

#### 4.D.6 Veteran Indicator List — **Medicaid_Rule (ELG.003.039)**

Source field `VET-IND-CD` → target `veteransIndicator`. Value-list file: `veteran-indicator.csv`.

Note: T-MSIS codes are `0`/`1` while VO `veteransIndicator` pattern is `[YN]?` — normalization mapping is **GAP-16**; do not invent Y/N conversion until BA confirms.

| VVL Code | VVL Description | Target Enum / Canonical Value | Medicaid_Rule | Source Ref |
|---|---|---|---|---|
| 0 | No | pass-through String | **Medicaid_Rule (ELG.003.039)** | veteran-indicator.csv:L2 |
| 1 | Yes | pass-through String | **Medicaid_Rule (ELG.003.039)** | veteran-indicator.csv:L3 |

#### 4.D.7 English Proficiency List — **Medicaid_Rule (ELG.003.045)**

Source field `ENG-PRFCY-CD` → target `primaryLanguageEnglishProficiencyCode`. Value-list file: `english-proficiency.csv`.

| VVL Code | VVL Description | Target Enum / Canonical Value | Medicaid_Rule | Source Ref |
|---|---|---|---|---|
| 0 | Very Well | pass-through String | **Medicaid_Rule (ELG.003.045)** | english-proficiency.csv:L2 |
| 1 | Well | pass-through String | **Medicaid_Rule (ELG.003.045)** | english-proficiency.csv:L3 |
| 2 | Not well | pass-through String | **Medicaid_Rule (ELG.003.045)** | english-proficiency.csv:L4 |
| 3 | No spoken proficiency | pass-through String | **Medicaid_Rule (ELG.003.045)** | english-proficiency.csv:L5 |

#### 4.D.8 Household Size List — **Medicaid_Rule (ELG.003.047)**

Source field `HH-SIZE-NUM` → target `householdSize`. Value-list file: `household-size.csv`.

| VVL Code | VVL Description | Target Enum / Canonical Value | Medicaid_Rule | Source Ref |
|---|---|---|---|---|
| 01 | 1 person | pass-through String | **Medicaid_Rule (ELG.003.047)** | household-size.csv:L2 |
| 02 | 2 people | pass-through String | **Medicaid_Rule (ELG.003.047)** | household-size.csv:L3 |
| 03 | 3 people | pass-through String | **Medicaid_Rule (ELG.003.047)** | household-size.csv:L4 |
| 04 | 4 people | pass-through String | **Medicaid_Rule (ELG.003.047)** | household-size.csv:L5 |
| 05 | 5 people | pass-through String | **Medicaid_Rule (ELG.003.047)** | household-size.csv:L6 |
| 06 | 6 people | pass-through String | **Medicaid_Rule (ELG.003.047)** | household-size.csv:L7 |
| 07 | 7 people | pass-through String | **Medicaid_Rule (ELG.003.047)** | household-size.csv:L8 |
| 08 | 8 or more people | pass-through String | **Medicaid_Rule (ELG.003.047)** | household-size.csv:L9 |

**E. Valid Value Lists Applied (`Medicaid_Rule` VVL Index)**

| CMdS Attribute | Source Field | T-MSIS DE | VVL Name | Value-List File | # Codes | §4.D Subsection | Status |
|---|---|---|---|---|---|---|---|
| gender | MBR-GNDR-CD | ELG.002.023 | Sex List | sex.csv | 3 | §4.D.1 | CONFIRMED |
| languageCode | MBR-LANG-CD | ELG.003.046 | Preferred Language List | preferred-language.csv | 483 | §4.D.2 | CONFIRMED |
| categoryOfEligibility | MBR-ELIG-CAT | ELG.005.087 | Eligibility Group List | eligibility-group.csv | 74 | §4.D.3 | CONFIRMED |
| levelOfCare | LTC-LVL-CARE-CD | ELG.005.088 | Level of Care Status List | level-of-care-status.csv | 6 | §4.D.4 | CONFIRMED |
| maritalStatus | MRTL-STAT-CD | ELG.003.034 | Marital Status List | marital-status.csv | 14 | §4.D.5 | CONFIRMED |
| veteransIndicator | VET-IND-CD | ELG.003.039 | Veteran Indicator List | veteran-indicator.csv | 2 | §4.D.6 | CONFIRMED |
| primaryLanguageEnglishProficiencyCode | ENG-PRFCY-CD | ELG.003.045 | English Proficiency List | english-proficiency.csv | 4 | §4.D.7 | CONFIRMED |
| householdSize | HH-SIZE-NUM | ELG.003.047 | Household Size List | household-size.csv | 8 | §4.D.8 | CONFIRMED |

Additional mapped code fields without CONFIRMED VVL members in research: `race` (**Medicaid_Rule (ELG.016.213)** / GAP-04), `eligibilityTerminationReasonCode` (**Medicaid_Rule (ELG.005.095)** / GAP-05), `federalMatchCode` (GAP-06), `diabilityType` (**Medicaid_Rule (ELG.017.224)** / GAP-19), `healthHomeLevelCode` (GAP-20), `lockinAssignmentReasonCode` (GAP-22), `lockinChangeReasonCode` (GAP-23), `immigrantAdmissionStatus` (**Medicaid_Rule (ELG.003.042)** / GAP-24).

**F. Medicare.gov / T-MSIS Validation Rules Applied (`Medicaid_Rule`)**

Dictionary version **4.0.33**. Rules below are consolidated from research `field_mappings` where `t_msis_rule` is set.

| T-MSIS DE | Source Field | Target Attribute | VVL File | Spec Cross-Ref |
|---|---|---|---|---|
| **Medicaid_Rule (ELG.002.023)** | MBR-GNDR-CD | gender | sex.csv | §3 matrix |
| **Medicaid_Rule (ELG.016.213)** | MBR-RACE-CD | race | —(GAP / no CONFIRMED list) | §3 matrix |
| **Medicaid_Rule (ELG.003.046)** | MBR-LANG-CD | languageCode | preferred-language.csv | §3 matrix |
| **Medicaid_Rule (ELG.017.224)** | MBR-DSBL-TYP | diabilityType | —(GAP / no CONFIRMED list) | §3 matrix |
| **Medicaid_Rule (ELG.005.087)** | MBR-ELIG-CAT | categoryOfEligibility | eligibility-group.csv | §3 matrix |
| **Medicaid_Rule (ELG.005.095)** | MBR-TERM-RSN-CD | eligibilityTerminationReasonCode | —(GAP / no CONFIRMED list) | §3 matrix |
| **Medicaid_Rule (ELG.005.088)** | LTC-LVL-CARE-CD | levelOfCare | level-of-care-status.csv | §3 matrix |
| **Medicaid_Rule (ELG.003.034)** | MRTL-STAT-CD | maritalStatus | marital-status.csv | §3 matrix |
| **Medicaid_Rule (ELG.003.039)** | VET-IND-CD | veteransIndicator | veteran-indicator.csv | §3 matrix |
| **Medicaid_Rule (ELG.003.045)** | ENG-PRFCY-CD | primaryLanguageEnglishProficiencyCode | english-proficiency.csv | §3 matrix |
| **Medicaid_Rule (ELG.003.047)** | HH-SIZE-NUM | householdSize | household-size.csv | §3 matrix |
| **Medicaid_Rule (ELG.003.042)** | IMM-ADMS-STAT | immigrantAdmissionStatus | —(GAP / no CONFIRMED list) | §3 matrix |

---

*End of Integration Specification. Generated from research YAML only; Markdown is the canonical source of truth. Word export via `tools/md_to_docx.py`.*
