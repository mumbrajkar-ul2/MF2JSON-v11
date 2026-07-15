# Integration Specification: MES to CMdS ( Member Eligibility )

**T-MSIS Dictionary Version:** `4.0.33` (from research `meta.dictionary_version`)

**Research Artifact:** `research/Integration_Research_MemberEligibility.yaml`

---

## 1. Document Header & Executive Summary

### Business Objective

Migrate MES Member Eligibility fixed-width / mixed-mode mainframe extracts into a typed, cloud-native CMdS domain model so eligibility demographics, coverage periods, LTC liability, Medicare parts, lock-in, and related attributes support claims, financials, and external T-MSIS validations.

### Target Architectural Pattern

Pipeline (deterministic):

1. **Ingestion** — Read the fixed-width legacy extract as raw `byte[]` (never as a charset-decoded line) to protect COMP-3 / COMP bytes that may resemble line breaks.
2. **Boundary-safe parsing** — Slice fields with explicit start/end from research layout; validate indices with `Math.min` against the actual record length to prevent `ArrayIndexOutOfBoundsException` when trailing pads are truncated.
3. **Text normalization** — For alphanumeric (`PIC X`) fields, decode with `StandardCharsets.ISO_8859_1` and invoke `.trim()` at the ingestion threshold (source charset confirmation: GAP-01).
4. **MapStruct conversion** — Map parsed properties into `MemberEligibilityVO` via MapStruct; `@Named` / `qualifiedByName` names must match character-for-character wherever used.
5. **T-MSIS validation** — Apply tagged **`Medicaid_Rule (ELG.xxx.xxx)`** checks from dictionary **4.0.33** where research linked a data element.
6. **Canonical JSON** — Serialize the VO to the CMdS canonical JSON payload.
7. **Idempotent REST delivery** — POST to CMdS eligibility APIs for PostgreSQL persistence (API contract / SLA: GAP-13).

This specification transcribes research for flow **Member Eligibility** only. No field mappings, VVL codes, GAP IDs, or assumptions beyond the research artifact are introduced.

---

## 2. Gaps & Assumptions (Human-in-the-Loop Handoff)

### 2.1 Document Conventions for This Section

| Marker | Meaning |
|--------|---------|
| `GAP-NN` | Information missing from source layout, target VO, or rule artifacts; blocks confident build until resolved or assumed. |
| `ASM-NN` | Explicit BA-confirmed placeholder behavior. Research `assumptions` is empty on this pass — no ASM IDs are invented. |
| **`Medicaid_Rule (ELG.xxx.xxx)`** | Citation of a T-MSIS data-element rule id from dictionary 4.0.33. |
| P1 / P2 / P3 | Priority (blocking / important / nice-to-have). |
| Owner | Role accountable for closing the gap (e.g. MMIS SME, Sec/Compliance, CMdS API). |

### 2.2 GAPS — Information Missing from Source/Target Artifacts

| ID | Topic | What is missing | Why it matters | Owner | Priority |
|----|-------|-----------------|----------------|-------|----------|
| GAP-01 | Source character encoding | MEMBERELIGIBILITY.csv, MEMBERELIGIBILITY.CPY, and MemberEligibilityVO.md do not specify charset (e.g. ISO-8859-1 vs EBCDIC). | Blocks accurate ingest/mapping until resolved. | MMIS SME | P1 |
| GAP-02 | CTR-SRVC-DT to serviceDate (YearMonth) | Source PIC X(08) at positions 9-16 (MEMBERELIGIBILITY.csv:L3); VO serviceDate uses pattern yyyyMM (MemberEligibilityVO.md:L8-L10). Truncation/padding rules not stated in artifacts. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P1 |
| GAP-03 | MBR-GNDR-CD width and code normalization | Source PIC X(04) at 435-438 (MEMBERELIGIBILITY.csv:L30); VO gender @Size(max=1) with pattern [MFU]? (MemberEligibilityVO.md:L126-L129); T-MSIS Sex is X(1) per ELG.002.023. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P1 |
| GAP-04 | Race valid value list | MBR-RACE-CD mapped to race (ELG.016.213 per data-elements.csv) but no CONFIRMED race VVL CSV under rules/eligibility/value-lists/. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P1 |
| GAP-05 | Eligibility termination reason code | MBR-TERM-RSN-CD present in layout (MEMBERELIGIBILITY.csv:L37); no matching CONFIRMED VVL CSV in value-lists/ and no decode table in MemberEligibilityVO.md. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-06 | Federal match code | MBR-FED-MCH-CD present in layout (MEMBERELIGIBILITY.csv:L38); no CONFIRMED VVL CSV in value-lists/ for federalMatchCode. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-07 | COMP-3 packed decimal decode | LTC liability and rate amount fields use PIC S9(7)V99 COMP-3; VO uses @Digits(integer=7, fraction=2) but byte order/sign nibble rules not documented in copybook or VO. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P1 |
| GAP-08 | HH-SIZE-NUM binary COMP | Source PIC 9(04) COMP (2 bytes) at 1422-1423 (MEMBERELIGIBILITY.csv:L110); VO householdSize is Integer (MemberEligibilityVO.md:L461-L462); COMP endianness not stated in MEMBERELIGIBILITY.CPY. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-09 | Sentinel / default dates | Multiple PIC X(08) date fields in layout; VO @JsonFormat yyyyMMdd on date fields without documented sentinel handling (e.g. 00000000, 99999999) in artifacts. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-10 | Phone number formatting | MBR-PHN-NUM and related fields PIC X(12) in source; VO memberContactNumber @Size(max=10) (MemberEligibilityVO.md:L105-L107). Strip/pad rules not stated. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-11 | Record framing and file terminator | MEMBERELIGIBILITY.csv defines a 1473-byte fixed layout (SRC-FILE-NM ends at 1473); no LF/CRLF, RDW, or block descriptor documented in .CPY or VO. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P1 |
| GAP-12 | HIPAA / PHI handling for DLQ records | MEMBERELIGIBILITY layout and MemberEligibilityVO.md contain SSN and demographic PHI; no dead-letter redaction or retention policy in provided artifacts. | Blocks accurate ingest/mapping until resolved. | Sec/Compliance | P1 |
| GAP-13 | CMdS operations (API contract, file arrival, SLA, observability) | Integration project provides MemberEligibilityVO.md only; no OpenAPI contract, batch file arrival, SLA, or observability artifacts. | Blocks accurate ingest/mapping until resolved. | CMdS API | P2 |
| GAP-14 | Natural-key format and validation | No composite ingest key (e.g. medicaidCardId + serviceDate + providerId) documented in MEMBERELIGIBILITY.csv, .CPY, or MemberEligibilityVO.md. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-15 | Cross-field date ordering rules | T-MSIS data-elements.md documents period ordering for many date pairs; integration artifacts do not state which pairs apply at the MES→CMdS boundary. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-16 | Veterans indicator code normalization | T-MSIS Veteran Indicator List uses codes 0/1 (veteran-indicator.csv); VO veteransIndicator pattern [YN]? (MemberEligibilityVO.md:L448-L451). Mapping not stated in artifacts. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-17 | Level of care code width | Source LTC-LVL-CARE-CD PIC X(04) at 531-534 (MEMBERELIGIBILITY.csv:L45); VO levelOfCare @Size(max=2) (MemberEligibilityVO.md:L191-L193); T-MSIS ELG.005.088 is X(3). Truncation/padding rules not stated. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-18 | Marital status code width | Source MRTL-STAT-CD PIC X(04) at 1380-1383 (MEMBERELIGIBILITY.csv:L106); VO maritalStatus @Size(max=1) (MemberEligibilityVO.md:L444-L446); T-MSIS ELG.003.034 uses 2-character codes (marital-status.csv). Normalization not stated. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-19 | Disability type code list | MBR-DSBL-TYP present in layout (MEMBERELIGIBILITY.csv:L33) mapped to diabilityType (MemberEligibilityVO.md:L139); no CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-20 | Health home level code list | HH-LVL-CD present in layout (MEMBERELIGIBILITY.csv:L42) mapped to healthHomeLevelCode (MemberEligibilityVO.md:L178); no CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-21 | Part D opt-out indicator legal values | MCR-PTD-OPT-IND present in layout (MEMBERELIGIBILITY.csv:L65) mapped to partDOptOutIndex (MemberEligibilityVO.md:L273); Boolean/indicator legal values (Y/N, 1/0, blank) not stated in MEMBERELIGIBILITY.csv, .CPY, or VO. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-22 | Lock-in assignment reason code list | LCK-ASGN-RSN present in layout (MEMBERELIGIBILITY.csv:L98) mapped to lockinAssignmentReasonCode (MemberEligibilityVO.md:L409); no CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-23 | Lock-in change reason code list | LCK-CHG-RSN present in layout (MEMBERELIGIBILITY.csv:L99) mapped to lockinChangeReasonCode (MemberEligibilityVO.md:L413); no CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-24 | Immigrant admission status code list | IMM-ADMS-STAT present in layout (MEMBERELIGIBILITY.csv:L111) mapped to immigrantAdmissionStatus (MemberEligibilityVO.md:L464); no CONFIRMED VVL CSV under rules/eligibility/value-lists/. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-25 | Per-field nullability / mandatory rules | VO has sparse nullability comments (e.g. medicareIdNumber, healthHomeNPIId); T-MSIS Necessity in data-elements.md is not aligned field-by-field to MES layout or JSR-380 constraints in MemberEligibilityVO.md. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P2 |
| GAP-26 | Name / free-text character class | Name and address PIC X fields (e.g. MBR-LAST-NM, MBR-FRST-NM) have no allowed character class documented in MEMBERELIGIBILITY.csv, .CPY, or MemberEligibilityVO.md beyond @Size. | Blocks accurate ingest/mapping until resolved. | MMIS SME | P3 |

### 2.3 ASSUMPTIONS — Placeholder Values Awaiting BA Confirmation

Research `assumptions` is empty. No `ASM-NN` entries are recorded on this pass. Assumptions await BA confirmation after GAP review.

### 2.4 Outstanding Questions for the BA Team (in priority order)

**P1**

1. [GAP-01] Source character encoding — MEMBERELIGIBILITY.csv, MEMBERELIGIBILITY.CPY, and MemberEligibilityVO.md do not specify charset (e.g. ISO-8859-1 vs EBCDIC).
1. [GAP-02] CTR-SRVC-DT to serviceDate (YearMonth) — Source PIC X(08) at positions 9-16 (MEMBERELIGIBILITY.csv:L3); VO serviceDate uses pattern yyyyMM (MemberEligibilityVO.md:L8-L10). Truncation/padding rules not stated in artifacts.
1. [GAP-03] MBR-GNDR-CD width and code normalization — Source PIC X(04) at 435-438 (MEMBERELIGIBILITY.csv:L30); VO gender @Size(max=1) with pattern [MFU]? (MemberEligibilityVO.md:L126-L129); T-MSIS Sex is X(1) per ELG.002.023.
1. [GAP-04] Race valid value list — MBR-RACE-CD mapped to race (ELG.016.213 per data-elements.csv) but no CONFIRMED race VVL CSV under rules/eligibility/value-lists/.
1. [GAP-07] COMP-3 packed decimal decode — LTC liability and rate amount fields use PIC S9(7)V99 COMP-3; VO uses @Digits(integer=7, fraction=2) but byte order/sign nibble rules not documented in copybook or VO.
1. [GAP-11] Record framing and file terminator — MEMBERELIGIBILITY.csv defines a 1473-byte fixed layout (SRC-FILE-NM ends at 1473); no LF/CRLF, RDW, or block descriptor documented in .CPY or VO.
1. [GAP-12] HIPAA / PHI handling for DLQ records — MEMBERELIGIBILITY layout and MemberEligibilityVO.md contain SSN and demographic PHI; no dead-letter redaction or retention policy in provided artifacts.

**P2**

1. [GAP-05] Eligibility termination reason code — Owner: MMIS SME.
2. [GAP-06] Federal match code — Owner: MMIS SME.
3. [GAP-08] HH-SIZE-NUM binary COMP — Owner: MMIS SME.
4. [GAP-09] Sentinel / default dates — Owner: MMIS SME.
5. [GAP-10] Phone number formatting — Owner: MMIS SME.
6. [GAP-13] CMdS operations (API contract, file arrival, SLA, observability) — Owner: CMdS API.
7. [GAP-14] Natural-key format and validation — Owner: MMIS SME.
8. [GAP-15] Cross-field date ordering rules — Owner: MMIS SME.
9. [GAP-16] Veterans indicator code normalization — Owner: MMIS SME.
10. [GAP-17] Level of care code width — Owner: MMIS SME.
11. [GAP-18] Marital status code width — Owner: MMIS SME.
12. [GAP-19] Disability type code list — Owner: MMIS SME.
13. [GAP-20] Health home level code list — Owner: MMIS SME.
14. [GAP-21] Part D opt-out indicator legal values — Owner: MMIS SME.
15. [GAP-22] Lock-in assignment reason code list — Owner: MMIS SME.
16. [GAP-23] Lock-in change reason code list — Owner: MMIS SME.
17. [GAP-24] Immigrant admission status code list — Owner: MMIS SME.
18. [GAP-25] Per-field nullability / mandatory rules — Owner: MMIS SME.

**P3**

1. [GAP-26] Name / free-text character class — Owner: MMIS SME.

### 2.5 BA Sign-Off (to be completed before "Ready for Build")

| Check | Status | Signer / Date |
|-------|--------|---------------|
| All P1 gaps resolved or explicitly assumed (ASM with BA approval) | ☐ | |
| §3 mapping matrix reviewed for semantic correctness | ☐ | |
| §4.D / §4.E VVL membership confirmed against T-MSIS 4.0.33 | ☐ | |
| PHI / DLQ handling (GAP-12) approved by Sec/Compliance | ☐ | |
| CMdS API / ops concerns (GAP-13) accepted or deferred | ☐ | |
| **Build-Readiness Gate:** Ready for MapStruct / pipeline implementation | ☐ | |

---

## 3. Core Technical Mapping Matrix

One row per research `field_mappings` entry. Positions are 1-based inclusive from the MES fixed layout.

| MMIS Field Name | COBOL PICTURE Clause | Position / Length | CMdS Target Attribute Name | Target Java Data Type | Target JSON Schema Constraints | Transformation & Business Rules |
|----------------|----------------------|-------------------|---------------------------|----------------------|--------------------------------|---------------------------------|
| CTR-INTF-DT | `PIC X(08)` | 1-8 / 8 | `interfaceDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L2` → `MemberEligibilityVO.md:L4`. |
| CTR-SRVC-DT | `PIC X(08)` | 9-16 / 8 | `serviceDate` | `YearMonth` | Java type `YearMonth` | Derivation: INFERRED. Map to YearMonth (yyyyMM); truncation/padding per GAP-02. Provenance: `MEMBERELIGIBILITY.csv:L3` → `MemberEligibilityVO.md:L8`. |
| CTR-PROV-ID | `PIC X(12)` | 17-28 / 12 | `providerId` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L4` → `MemberEligibilityVO.md:L12`. |
| CTR-PLAN-NM | `PIC X(30)` | 29-58 / 30 | `planName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L5` → `MemberEligibilityVO.md:L16`. |
| CTR-MED-CRD-ID | `PIC X(12)` | 59-70 / 12 | `medicaidCardId` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L6` → `MemberEligibilityVO.md:L21`. |
| CTR-MCILD-NUM | `PIC X(12)` | 71-82 / 12 | `mciId` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L7` → `MemberEligibilityVO.md:L25`. |
| CTR-SSN-TXT | `PIC X(12)` | 83-94 / 12 | `ssn` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L8` → `MemberEligibilityVO.md:L29`. |
| CTR-MCR-ID-NUM | `PIC X(12)` | 95-106 / 12 | `medicareIdNumber` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L9` → `MemberEligibilityVO.md:L34`. |
| MBR-LAST-NM | `PIC X(30)` | 107-136 / 30 | `memberLastName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L10` → `MemberEligibilityVO.md:L39`. |
| MBR-FRST-NM | `PIC X(30)` | 137-166 / 30 | `memberFirstName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L11` → `MemberEligibilityVO.md:L43`. |
| MBR-MID-NM | `PIC X(30)` | 167-196 / 30 | `memberMiddleName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L12` → `MemberEligibilityVO.md:L47`. |
| MBR-ML-ADR-LN1 | `PIC X(30)` | 197-226 / 30 | `mailingAdressLine1` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L13` → `MemberEligibilityVO.md:L52`. |
| MBR-ML-ADR-LN2 | `PIC X(30)` | 227-256 / 30 | `mailingAddressLine2` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L14` → `MemberEligibilityVO.md:L56`. |
| MBR-ML-CITY-NM | `PIC X(30)` | 257-286 / 30 | `mailingAddressCity` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L15` → `MemberEligibilityVO.md:L60`. |
| MBR-ML-ST-CD | `PIC X(02)` | 287-288 / 2 | `mailingState` | `String` | Java type `String`; source length 2 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L16` → `MemberEligibilityVO.md:L64`. |
| MBR-ML-ZIP-5 | `PIC X(05)` | 289-293 / 5 | `mailingZip5` | `String` | Java type `String`; source length 5 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L17` → `MemberEligibilityVO.md:L68`. |
| MBR-ML-ZIP-4 | `PIC X(04)` | 294-297 / 4 | `mailingZip4` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L18` → `MemberEligibilityVO.md:L73`. |
| MBR-RS-ADR-LN1 | `PIC X(30)` | 298-327 / 30 | `residenceAdressLine1` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L19` → `MemberEligibilityVO.md:L79`. |
| MBR-RS-ADR-LN2 | `PIC X(30)` | 328-357 / 30 | `residenceAddressLine2` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L20` → `MemberEligibilityVO.md:L83`. |
| MBR-RS-CITY-NM | `PIC X(30)` | 358-387 / 30 | `residenceAddressCity` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L21` → `MemberEligibilityVO.md:L87`. |
| MBR-RS-ST-CD | `PIC X(02)` | 388-389 / 2 | `residenceState` | `String` | Java type `String`; source length 2 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L22` → `MemberEligibilityVO.md:L91`. |
| MBR-RS-ZIP-5 | `PIC X(05)` | 390-394 / 5 | `residenceZip5` | `String` | Java type `String`; source length 5 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L23` → `MemberEligibilityVO.md:L95`. |
| MBR-RS-ZIP-4 | `PIC X(04)` | 395-398 / 4 | `residenceZip4` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L24` → `MemberEligibilityVO.md:L100`. |
| MBR-PHN-NUM | `PIC X(12)` | 399-410 / 12 | `memberContactNumber` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L25` → `MemberEligibilityVO.md:L105`. |
| MBR-GEO-CNTY-CD | `PIC X(04)` | 411-414 / 4 | `geoCountyCode` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L26` → `MemberEligibilityVO.md:L109`. |
| MBR-ADM-OFF-CD | `PIC X(04)` | 415-418 / 4 | `adminOfficeCode` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L27` → `MemberEligibilityVO.md:L113`. |
| MBR-DOB-DT | `PIC X(08)` | 419-426 / 8 | `dateOfBirth` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L28` → `MemberEligibilityVO.md:L118`. |
| MBR-DOD-DT | `PIC X(08)` | 427-434 / 8 | `dateOfDeath` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L29` → `MemberEligibilityVO.md:L122`. |
| MBR-GNDR-CD | `PIC X(04)` | 435-438 / 4 | `gender` | `String` | Java type `String`; source length 4; rule ELG.002.023 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. **Medicaid_Rule (ELG.002.023)**. VVL: `sex.csv` — see §4.D. Provenance: `MEMBERELIGIBILITY.csv:L30` → `MemberEligibilityVO.md:L126`. |
| MBR-RACE-CD | `PIC X(04)` | 439-442 / 4 | `race` | `String` | Java type `String`; source length 4; rule ELG.016.213 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. **Medicaid_Rule (ELG.016.213)**. Provenance: `MEMBERELIGIBILITY.csv:L31` → `MemberEligibilityVO.md:L131`. |
| MBR-LANG-CD | `PIC X(04)` | 443-446 / 4 | `languageCode` | `String` | Java type `String`; source length 4; rule ELG.003.046 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. **Medicaid_Rule (ELG.003.046)**. VVL: `preferred-language.csv` — see §4.D. Provenance: `MEMBERELIGIBILITY.csv:L32` → `MemberEligibilityVO.md:L135`. |
| MBR-DSBL-TYP | `PIC X(04)` | 447-450 / 4 | `diabilityType` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L33` → `MemberEligibilityVO.md:L139`. |
| MBR-PREG-DUE-DT | `PIC X(08)` | 451-458 / 8 | `pregnancyDueDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L34` → `MemberEligibilityVO.md:L143`. |
| MBR-NPI-ID | `PIC X(12)` | 459-470 / 12 | `npiId` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L35` → `MemberEligibilityVO.md:L147`. |
| MBR-ELIG-CAT | `PIC X(04)` | 471-474 / 4 | `categoryOfEligibility` | `String` | Java type `String`; source length 4; rule ELG.005.087 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. **Medicaid_Rule (ELG.005.087)**. VVL: `eligibility-group.csv` — see §4.D. Provenance: `MEMBERELIGIBILITY.csv:L36` → `MemberEligibilityVO.md:L153`. |
| MBR-TERM-RSN-CD | `PIC X(04)` | 475-478 / 4 | `eligibilityTerminationReasonCode` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L37` → `MemberEligibilityVO.md:L157`. |
| MBR-FED-MCH-CD | `PIC X(04)` | 479-482 / 4 | `federalMatchCode` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L38` → `MemberEligibilityVO.md:L161`. |
| HH-NPI-ID | `PIC X(12)` | 483-494 / 12 | `healthHomeNPIId` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L39` → `MemberEligibilityVO.md:L166`. |
| HH-BEG-DT | `PIC X(08)` | 495-502 / 8 | `healthHomeBeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L40` → `MemberEligibilityVO.md:L170`. |
| HH-END-DT | `PIC X(08)` | 503-510 / 8 | `healthHomeEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L41` → `MemberEligibilityVO.md:L174`. |
| HH-LVL-CD | `PIC X(04)` | 511-514 / 4 | `healthHomeLevelCode` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L42` → `MemberEligibilityVO.md:L178`. |
| LTC-BEG-DT | `PIC X(08)` | 515-522 / 8 | `ltcBeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L43` → `MemberEligibilityVO.md:L183`. |
| LTC-END-DT | `PIC X(08)` | 523-530 / 8 | `ltcEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L44` → `MemberEligibilityVO.md:L187`. |
| LTC-LVL-CARE-CD | `PIC X(04)` | 531-534 / 4 | `levelOfCare` | `String` | Java type `String`; source length 4; rule ELG.005.088 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. **Medicaid_Rule (ELG.005.088)**. VVL: `level-of-care-status.csv` — see §4.D. Provenance: `MEMBERELIGIBILITY.csv:L45` → `MemberEligibilityVO.md:L191`. |
| LTC-CURR-BEG-DT | `PIC X(08)` | 535-542 / 8 | `ltcPatientLiabilityCurrentBeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L46` → `MemberEligibilityVO.md:L195`. |
| LTC-CURR-END-DT | `PIC X(08)` | 543-550 / 8 | `ltcPatientLiabilityCurrentEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L47` → `MemberEligibilityVO.md:L199`. |
| LTC-CURR-LIAB-AM | `PIC S9(7)V99 COMP-3` | 551-555 / 5 | `ltcPatientLiabilityCurrentAmount` | `BigDecimal` | Java type `BigDecimal` | Derivation: INFERRED. Packed decimal (COMP-3); see §4.C and GAP-07. Provenance: `MEMBERELIGIBILITY.csv:L48` → `MemberEligibilityVO.md:L203`. |
| LTC-PREV-BEG-DT | `PIC X(08)` | 556-563 / 8 | `ltcPatientLiabilityPreviousBeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L49` → `MemberEligibilityVO.md:L207`. |
| LTC-PREV-END-DT | `PIC X(08)` | 564-571 / 8 | `ltcPatientLiabilityPreviousEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L50` → `MemberEligibilityVO.md:L211`. |
| LTC-PREV-LIAB-AM | `PIC S9(7)V99 COMP-3` | 572-576 / 5 | `ltcPatientLiabilityPreviousAmount` | `BigDecimal` | Java type `BigDecimal` | Derivation: INFERRED. Packed decimal (COMP-3); see §4.C and GAP-07. Provenance: `MEMBERELIGIBILITY.csv:L51` → `MemberEligibilityVO.md:L215`. |
| DSBL-BEG-DT | `PIC X(08)` | 577-584 / 8 | `disabilityBeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L52` → `MemberEligibilityVO.md:L220`. |
| DSBL-END-DT | `PIC X(08)` | 585-592 / 8 | `disabilityEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L53` → `MemberEligibilityVO.md:L224`. |
| MCR-PTA-BEG-DT | `PIC X(08)` | 593-600 / 8 | `partABeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L54` → `MemberEligibilityVO.md:L229`. |
| MCR-PTA-END-DT | `PIC X(08)` | 601-608 / 8 | `partAEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L55` → `MemberEligibilityVO.md:L233`. |
| MCR-PTB-BEG-DT | `PIC X(08)` | 609-616 / 8 | `partBBeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L56` → `MemberEligibilityVO.md:L237`. |
| MCR-PTB-END-DT | `PIC X(08)` | 617-624 / 8 | `partBEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L57` → `MemberEligibilityVO.md:L241`. |
| MCR-PTC-BEG-DT | `PIC X(08)` | 625-632 / 8 | `partCBeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L58` → `MemberEligibilityVO.md:L245`. |
| MCR-PTC-END-DT | `PIC X(08)` | 633-640 / 8 | `partCEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L59` → `MemberEligibilityVO.md:L249`. |
| MCR-PTC-CNTR-ID | `PIC X(12)` | 641-652 / 12 | `partCPBPContractId` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L60` → `MemberEligibilityVO.md:L253`. |
| MCR-PBP-ORG-NM | `PIC X(30)` | 653-682 / 30 | `pbpOrganizationName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L61` → `MemberEligibilityVO.md:L257`. |
| MCR-PTC-PLAN-NM | `PIC X(30)` | 683-712 / 30 | `partCPBPPlanName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L62` → `MemberEligibilityVO.md:L261`. |
| MCR-PTD-BEG-DT | `PIC X(08)` | 713-720 / 8 | `partDBeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L63` → `MemberEligibilityVO.md:L265`. |
| MCR-PTD-END-DT | `PIC X(08)` | 721-728 / 8 | `partDEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L64` → `MemberEligibilityVO.md:L269`. |
| MCR-PTD-OPT-IND | `PIC X(04)` | 729-732 / 4 | `partDOptOutIndex` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L65` → `MemberEligibilityVO.md:L273`. |
| MCR-PTD-CNTR-ID | `PIC X(12)` | 733-744 / 12 | `partDPBPContractId` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L66` → `MemberEligibilityVO.md:L277`. |
| MCR-PTD-PLAN-ID | `PIC X(12)` | 745-756 / 12 | `partDPBPPlanID` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L67` → `MemberEligibilityVO.md:L281`. |
| CS-MGMT-NM | `PIC X(30)` | 757-786 / 30 | `caseMgmtName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L68` → `MemberEligibilityVO.md:L286`. |
| CS-ADR-LN1 | `PIC X(30)` | 787-816 / 30 | `caseMgmtAdressLine1` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L69` → `MemberEligibilityVO.md:L290`. |
| CS-ADR-LN2 | `PIC X(30)` | 817-846 / 30 | `caseMgmtAddressLine2` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L70` → `MemberEligibilityVO.md:L294`. |
| CS-CITY-NM | `PIC X(30)` | 847-876 / 30 | `caseMgmtAddressCity` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L71` → `MemberEligibilityVO.md:L298`. |
| CS-ST-CD | `PIC X(02)` | 877-878 / 2 | `caseMgmtState` | `String` | Java type `String`; source length 2 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L72` → `MemberEligibilityVO.md:L302`. |
| CS-ZIP-5 | `PIC X(05)` | 879-883 / 5 | `caseMgmtZip5` | `String` | Java type `String`; source length 5 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L73` → `MemberEligibilityVO.md:L306`. |
| CS-ZIP-4 | `PIC X(04)` | 884-887 / 4 | `caseMgmtZip4` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L74` → `MemberEligibilityVO.md:L310`. |
| CS-PHN-NUM | `PIC X(12)` | 888-899 / 12 | `caseMgmtPhoneNum` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L75` → `MemberEligibilityVO.md:L314`. |
| REP-LAST-NM | `PIC X(30)` | 900-929 / 30 | `authRepLastName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L76` → `MemberEligibilityVO.md:L319`. |
| REP-FRST-NM | `PIC X(30)` | 930-959 / 30 | `authRepFirstName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L77` → `MemberEligibilityVO.md:L323`. |
| REP-MID-NM | `PIC X(30)` | 960-989 / 30 | `authRepMiddleName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L78` → `MemberEligibilityVO.md:L327`. |
| REP-ADR-LN1 | `PIC X(30)` | 990-1019 / 30 | `authRepAdressLine1` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L79` → `MemberEligibilityVO.md:L331`. |
| REP-ADR-LN2 | `PIC X(30)` | 1020-1049 / 30 | `authRepAddressLine2` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L80` → `MemberEligibilityVO.md:L335`. |
| REP-CITY-NM | `PIC X(30)` | 1050-1079 / 30 | `authRepAddressCity` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L81` → `MemberEligibilityVO.md:L339`. |
| REP-ST-CD | `PIC X(02)` | 1080-1081 / 2 | `authRepState` | `String` | Java type `String`; source length 2 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L82` → `MemberEligibilityVO.md:L343`. |
| REP-ZIP-5 | `PIC X(05)` | 1082-1086 / 5 | `authRepZip5` | `String` | Java type `String`; source length 5 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L83` → `MemberEligibilityVO.md:L347`. |
| REP-ZIP-4 | `PIC X(04)` | 1087-1090 / 4 | `authRepZip4` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L84` → `MemberEligibilityVO.md:L351`. |
| REP-PHN-NUM | `PIC X(12)` | 1091-1102 / 12 | `authRepPhoneNum` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L85` → `MemberEligibilityVO.md:L355`. |
| PY-LAST-NM | `PIC X(30)` | 1103-1132 / 30 | `payeeLastName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L86` → `MemberEligibilityVO.md:L360`. |
| PY-FRST-NM | `PIC X(30)` | 1133-1162 / 30 | `payeeFirstName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L87` → `MemberEligibilityVO.md:L364`. |
| PY-MID-NM | `PIC X(30)` | 1163-1192 / 30 | `payeeMiddleName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L88` → `MemberEligibilityVO.md:L368`. |
| PY-ADR-LN1 | `PIC X(30)` | 1193-1222 / 30 | `payeeAdressLine1` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L89` → `MemberEligibilityVO.md:L372`. |
| PY-ADR-LN2 | `PIC X(30)` | 1223-1252 / 30 | `payeeAddressLine2` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L90` → `MemberEligibilityVO.md:L376`. |
| PY-CITY-NM | `PIC X(30)` | 1253-1282 / 30 | `payeeAddressCity` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L91` → `MemberEligibilityVO.md:L380`. |
| PY-ST-CD | `PIC X(02)` | 1283-1284 / 2 | `payeeState` | `String` | Java type `String`; source length 2 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L92` → `MemberEligibilityVO.md:L384`. |
| PY-ZIP-5 | `PIC X(05)` | 1285-1289 / 5 | `payeeZip5` | `String` | Java type `String`; source length 5 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L93` → `MemberEligibilityVO.md:L388`. |
| PY-ZIP-4 | `PIC X(04)` | 1290-1293 / 4 | `payeeZip4` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L94` → `MemberEligibilityVO.md:L392`. |
| PY-PHN-NUM | `PIC X(12)` | 1294-1305 / 12 | `payeePhoneNum` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L95` → `MemberEligibilityVO.md:L396`. |
| LCK-BEG-DT | `PIC X(08)` | 1306-1313 / 8 | `lockinBeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L96` → `MemberEligibilityVO.md:L401`. |
| LCK-END-DT | `PIC X(08)` | 1314-1321 / 8 | `lockinEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L97` → `MemberEligibilityVO.md:L405`. |
| LCK-ASGN-RSN | `PIC X(04)` | 1322-1325 / 4 | `lockinAssignmentReasonCode` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L98` → `MemberEligibilityVO.md:L409`. |
| LCK-CHG-RSN | `PIC X(04)` | 1326-1329 / 4 | `lockinChangeReasonCode` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L99` → `MemberEligibilityVO.md:L413`. |
| HPLN-RT-AMT | `PIC S9(7)V99 COMP-3` | 1330-1334 / 5 | `hplanRateAmount` | `BigDecimal` | Java type `BigDecimal` | Derivation: INFERRED. Packed decimal (COMP-3); see §4.C and GAP-07. Provenance: `MEMBERELIGIBILITY.csv:L100` → `MemberEligibilityVO.md:L418`. |
| TOT-RT-AMT | `PIC S9(7)V99 COMP-3` | 1335-1339 / 5 | `totalRateAmount` | `BigDecimal` | Java type `BigDecimal` | Derivation: INFERRED. Packed decimal (COMP-3); see §4.C and GAP-07. Provenance: `MEMBERELIGIBILITY.csv:L101` → `MemberEligibilityVO.md:L422`. |
| XFER-PLN-ID | `PIC X(12)` | 1340-1351 / 12 | `transferPlanId` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L102` → `MemberEligibilityVO.md:L427`. |
| FCLTY-ID | `PIC X(12)` | 1352-1363 / 12 | `facilityId` | `String` | Java type `String`; source length 12 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L103` → `MemberEligibilityVO.md:L431`. |
| BKG-DT | `PIC X(08)` | 1364-1371 / 8 | `bookingDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L104` → `MemberEligibilityVO.md:L435`. |
| RLSE-DT | `PIC X(08)` | 1372-1379 / 8 | `releaseDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L105` → `MemberEligibilityVO.md:L439`. |
| MRTL-STAT-CD | `PIC X(04)` | 1380-1383 / 4 | `maritalStatus` | `String` | Java type `String`; source length 4; rule ELG.003.034 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. **Medicaid_Rule (ELG.003.034)**. VVL: `marital-status.csv` — see §4.D. Provenance: `MEMBERELIGIBILITY.csv:L106` → `MemberEligibilityVO.md:L444`. |
| VET-IND-CD | `PIC X(04)` | 1384-1387 / 4 | `veteransIndicator` | `String` | Java type `String`; source length 4; rule ELG.003.039 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. **Medicaid_Rule (ELG.003.039)**. VVL: `veteran-indicator.csv` — see §4.D. Provenance: `MEMBERELIGIBILITY.csv:L107` → `MemberEligibilityVO.md:L448`. |
| EMAIL-ADR-TXT | `PIC X(30)` | 1388-1417 / 30 | `emailAddress` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L108` → `MemberEligibilityVO.md:L453`. |
| ENG-PRFCY-CD | `PIC X(04)` | 1418-1421 / 4 | `primaryLanguageEnglishProficiencyCode` | `String` | Java type `String`; source length 4; rule ELG.003.045 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. **Medicaid_Rule (ELG.003.045)**. VVL: `english-proficiency.csv` — see §4.D. Provenance: `MEMBERELIGIBILITY.csv:L109` → `MemberEligibilityVO.md:L457`. |
| HH-SIZE-NUM | `PIC 9(04) COMP` | 1422-1423 / 2 | `householdSize` | `Integer` | Java type `Integer`; rule ELG.003.047 | Derivation: INFERRED. Binary COMP field; see §4.C and GAP-08. **Medicaid_Rule (ELG.003.047)**. VVL: `household-size.csv` — see §4.D. Provenance: `MEMBERELIGIBILITY.csv:L110` → `MemberEligibilityVO.md:L461`. |
| IMM-ADMS-STAT | `PIC X(04)` | 1424-1427 / 4 | `immigrantAdmissionStatus` | `String` | Java type `String`; source length 4 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L111` → `MemberEligibilityVO.md:L464`. |
| MC-END-DT | `PIC X(08)` | 1428-1435 / 8 | `mcEndDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L112` → `MemberEligibilityVO.md:L468`. |
| MC-BEG-DT | `PIC X(08)` | 1436-1443 / 8 | `mcBeginDate` | `LocalDate` | Java type `LocalDate` | Derivation: INFERRED. Parse trimmed PIC X(08) as yyyyMMdd LocalDate; sentinel handling per GAP-09. Provenance: `MEMBERELIGIBILITY.csv:L113` → `MemberEligibilityVO.md:L472`. |
| SRC-FILE-NM | `PIC X(30)` | 1444-1473 / 30 | `fileName` | `String` | Java type `String`; source length 30 | Derivation: INFERRED. ISO_8859_1 decode + .trim(); see §4.A. Provenance: `MEMBERELIGIBILITY.csv:L114` → `MemberEligibilityVO.md:L476`. |

---

## 4. Data Engineering & Transformation Nuances

### A. String Normalization & Text Truncation

- Ingest raw `byte[]`; slice with research start/end; upper-bound with `Math.min` against record length (record framing: GAP-11).
- Alphanumeric fields: `new String(bytes, StandardCharsets.ISO_8859_1).trim()` (charset: GAP-01).
- Width mismatches (e.g. source PIC longer than VO `@Size`) remain open: GAP-03, GAP-10, GAP-17, GAP-18, GAP-26.
- Name/address character class not defined beyond `@Size`: GAP-26.

### B. Date Parsing & High-Date Logic

- `LocalDate` fields: interpret trimmed `PIC X(08)` as `yyyyMMdd` per VO `@JsonFormat` referenced in research.
- `serviceDate` is `YearMonth` from `CTR-SRVC-DT` `PIC X(08)`: GAP-02.
- Sentinel / high-date handling (e.g. `00000000`, `99999999`) not documented: GAP-09.
- Cross-field date ordering at MES→CMdS boundary not stated: GAP-15.

### C. Computational / Packed Decimals (COMP-3 Processing)

- Amount fields (`LTC-CURR-LIAB-AM`, `LTC-PREV-LIAB-AM`, `HPLN-RT-AMT`, `TOT-RT-AMT`) use `PIC S9(7)V99 COMP-3` (5 bytes) → `BigDecimal`; sign nibble / byte-order rules: GAP-07.
- `HH-SIZE-NUM` uses `PIC 9(04) COMP` (2 bytes) → `Integer`; endianness: GAP-08. VVL membership for household size is under **`Medicaid_Rule (ELG.003.047)`** in §4.D.

### D. Code-to-Enum Normalization & Valid Value Lists

Full code tables transcribed from research `vvl_members` only. Each row cites the owning data element.

#### ELG.002.023 — Sex (MBR-GNDR-CD → gender)

Source VVL file: `sex.csv`.

Note: source width / VO max length mismatch — GAP-03.

| VVL Code | Description | Rule Citation |
|----------|-------------|---------------|
| `F` | Female | **Medicaid_Rule (ELG.002.023)** (sex.csv:L2) |
| `M` | Male | **Medicaid_Rule (ELG.002.023)** (sex.csv:L3) |
| `U` | Unknown | **Medicaid_Rule (ELG.002.023)** (sex.csv:L4) |

#### ELG.003.034 — Marital Status (MRTL-STAT-CD → maritalStatus)

Source VVL file: `marital-status.csv`.

Note: source PIC X(04) vs VO `@Size(max=1)` vs 2-character T-MSIS codes — GAP-18.

| VVL Code | Description | Rule Citation |
|----------|-------------|---------------|
| `01` | Legally Married (to opposite sex), spouse present | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L2) |
| `02` | Legally Married (to opposite sex), spouse absent | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L3) |
| `03` | Legally Married (to same sex), spouse present | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L4) |
| `04` | Legally Married (to same sex), spouse absent | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L5) |
| `05` | Partnered or in Civil Union (to opposite sex), spouse present | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L6) |
| `06` | Partnered or in Civil Union (to opposite sex), spouse absent | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L7) |
| `07` | Partnered or in Civil Union (to same sex), spouse present | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L8) |
| `08` | Partnered or in Civil Union (to same sex), spouse absent | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L9) |
| `09` | Legally separated (and not married or partnered) | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L10) |
| `10` | Divorced (and not currently married or partnered) | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L11) |
| `11` | Separated (and not currently married or partnered) | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L12) |
| `12` | Widower/Widow (and not currently married or partnered) | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L13) |
| `13` | Never married/partnered | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L14) |
| `14` | Other | **Medicaid_Rule (ELG.003.034)** (marital-status.csv:L15) |

#### ELG.003.039 — Veteran Indicator (VET-IND-CD → veteransIndicator)

Source VVL file: `veteran-indicator.csv`.

Note: T-MSIS codes 0/1 vs VO pattern `[YN]?` — GAP-16.

| VVL Code | Description | Rule Citation |
|----------|-------------|---------------|
| `0` | No | **Medicaid_Rule (ELG.003.039)** (veteran-indicator.csv:L2) |
| `1` | Yes | **Medicaid_Rule (ELG.003.039)** (veteran-indicator.csv:L3) |

#### ELG.003.045 — English Proficiency (ENG-PRFCY-CD → primaryLanguageEnglishProficiencyCode)

Source VVL file: `english-proficiency.csv`.

| VVL Code | Description | Rule Citation |
|----------|-------------|---------------|
| `0` | Very Well | **Medicaid_Rule (ELG.003.045)** (english-proficiency.csv:L2) |
| `1` | Well | **Medicaid_Rule (ELG.003.045)** (english-proficiency.csv:L3) |
| `2` | Not well | **Medicaid_Rule (ELG.003.045)** (english-proficiency.csv:L4) |
| `3` | No spoken proficiency | **Medicaid_Rule (ELG.003.045)** (english-proficiency.csv:L5) |

#### ELG.003.047 — Household Size (HH-SIZE-NUM → householdSize)

Source VVL file: `household-size.csv`.

| VVL Code | Description | Rule Citation |
|----------|-------------|---------------|
| `01` | 1 person | **Medicaid_Rule (ELG.003.047)** (household-size.csv:L2) |
| `02` | 2 people | **Medicaid_Rule (ELG.003.047)** (household-size.csv:L3) |
| `03` | 3 people | **Medicaid_Rule (ELG.003.047)** (household-size.csv:L4) |
| `04` | 4 people | **Medicaid_Rule (ELG.003.047)** (household-size.csv:L5) |
| `05` | 5 people | **Medicaid_Rule (ELG.003.047)** (household-size.csv:L6) |
| `06` | 6 people | **Medicaid_Rule (ELG.003.047)** (household-size.csv:L7) |
| `07` | 7 people | **Medicaid_Rule (ELG.003.047)** (household-size.csv:L8) |
| `08` | 8 or more people | **Medicaid_Rule (ELG.003.047)** (household-size.csv:L9) |

#### ELG.005.087 — Eligibility Group (MBR-ELIG-CAT → categoryOfEligibility)

Source VVL file: `eligibility-group.csv`.

| VVL Code | Description | Rule Citation |
|----------|-------------|---------------|
| `01` | Parents and Other Caretaker Relatives | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L2) |
| `02` | Transitional Medical Assistance | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L3) |
| `03` | Extended Medicaid due to Earnings | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L4) |
| `04` | Extended Medicaid due to Spousal Support Collections | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L5) |
| `05` | Pregnant Women | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L6) |
| `06` | Deemed Newborns | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L7) |
| `07` | Infants and Children under Age 19 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L8) |
| `08` | Children with Title IV-E Adoption Assistance, Foster Care or Guardianship Care | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L9) |
| `09` | Former Foster Care Children | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L10) |
| `10` | Individuals at or below 133% FPL Age 19 through 64 / Non-pregnant individuals aged 19 through 64, not otherwise mandatorily eligible, with income at or below 133% FPL | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L11) |
| `11` | Individuals Receiving SSI | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L12) |
| `12` | Aged, Blind and Disabled Individuals in 209(b) States | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L13) |
| `13` | Individuals Receiving Mandatory State Supplements | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L14) |
| `14` | Individuals Who Are Essential Spouses | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L15) |
| `15` | Institutionalized Individuals Continuously Eligible Since 1973 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L16) |
| `16` | Blind or Disabled Individuals Eligible in 1973 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L17) |
| `17` | Individuals Who Lost Eligibility for SSI/SSP Due to an Increase in OASDI Benefits in 1972 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L18) |
| `18` | Individuals Who Would be Eligible for SSI/SSP but for OASDI COLA increases since April, 1977 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L19) |
| `19` | Disabled Widows and Widowers Ineligible for SSI due to Increase in OASDI | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L20) |
| `20` | Disabled Widows and Widowers Ineligible for SSI due to Early Receipt of Social Security | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L21) |
| `21` | Working Disabled under 1619(b) | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L22) |
| `22` | Disabled Adult Children | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L23) |
| `23` | Qualified Medicare Beneficiaries | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L24) |
| `24` | Qualified Disabled and Working Individuals | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L25) |
| `25` | Specified Low Income Medicare Beneficiaries | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L26) |
| `26` | Qualifying Individuals | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L27) |
| `27` | Optional Coverage of Parents and Other Caretaker Relatives | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L28) |
| `28` | Reasonable Classifications of Individuals under Age 21 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L29) |
| `29` | Children with Non-IV-E Adoption Assistance | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L30) |
| `30` | Independent Foster Care Adolescents | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L31) |
| `31` | Optional Targeted Low Income Children | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L32) |
| `32` | Individuals Electing COBRA Continuation Coverage | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L33) |
| `33` | Individuals above 133% FPL under Age 65 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L34) |
| `34` | Certain Individuals  Needing Treatment for Breast or Cervical Cancer | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L35) |
| `35` | Individuals Eligible for Family Planning Services | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L36) |
| `36` | Individuals with Tuberculosis | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L37) |
| `37` | Aged, Blind or Disabled Individuals Eligible for but Not Receiving Cash Assistance | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L38) |
| `38` | Individuals Eligible for Cash Assistance except for Institutionalization | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L39) |
| `39` | Individuals Receiving Home and Community Based Services under Institutional Rules | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L40) |
| `40` | Optional State Supplement Recipients - 1634 States, and SSI Criteria States with 1616 Agreements | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L41) |
| `41` | Optional State Supplement Recipients - 209(b) States, and SSI Criteria States without 1616 Agreements | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L42) |
| `42` | Institutionalized Individuals Eligible under a Special Income Level | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L43) |
| `43` | Individuals participating in a PACE Program under Institutional Rules | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L44) |
| `44` | Individuals Receiving Hospice Care | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L45) |
| `45` | Qualified Disabled Children under Age 19 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L46) |
| `46` | Poverty Level Aged or Disabled | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L47) |
| `47` | Work Incentives Eligibility Group | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L48) |
| `48` | Ticket to Work Basic Group | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L49) |
| `49` | Ticket to Work Medical Improvements Group | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L50) |
| `50` | Family Opportunity Act Children with Disabilities | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L51) |
| `51` | Individuals Eligible for Home and Community-Based Services | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L52) |
| `52` | Individuals Eligible for Home and Community-Based Services - Special Income Level | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L53) |
| `53` | Medically Needy Pregnant Women | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L54) |
| `54` | Medically Needy Children under Age 18 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L55) |
| `55` | Medically Needy Children Age 18 through 20 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L56) |
| `56` | Medically Needy Parents and Other Caretakers | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L57) |
| `59` | Medically Needy Aged, Blind or Disabled | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L58) |
| `60` | Medically Needy Blind or Disabled Individuals Eligible in 1973 | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L59) |
| `61` | Targeted Low-Income Children | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L60) |
| `62` | Deemed Newborn | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L61) |
| `63` | Children Ineligible for Medicaid Due to Loss of Income Disregards | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L62) |
| `64` | Coverage from Conception to Birth | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L63) |
| `65` | Children with Access to Public Employee Coverage | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L64) |
| `66` | Children Eligible for Dental Only Supplemental Coverage | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L65) |
| `67` | Targeted Low-Income Pregnant Women | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L66) |
| `68` | Pregnant Women with Access to Public Employee Coverage | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L67) |
| `69` | Individuals with Mental Health Conditions (expansion group) | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L68) |
| `70` | Family Planning Participants (expansion group) | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L69) |
| `71` | Other expansion group | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L70) |
| `72` | Adult Group - Individuals at or below 133% FPL Age 19 through 64 - newly eligible for all states | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L71) |
| `73` | Adult Group - Individuals at or below 133% FPL Age 19 through 64 - not newly eligible for non 1905z(3) states | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L72) |
| `74` | Adult Group - Individuals at or below 133% FPL Age 19 through 64 - not newly eligible parent/ caretaker-relative(s) in 1905z(3) states | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L73) |
| `75` | Adult Group - Individuals at or below 133% FPL Age 19 through 64 - not newly eligible non-parent/ caretaker-relative(s) in 1905z(3) states | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L74) |
| `76` | Uninsured Individual eligible for COVID-19 testing | **Medicaid_Rule (ELG.005.087)** (eligibility-group.csv:L75) |

#### ELG.005.088 — Level of Care Status (LTC-LVL-CARE-CD → levelOfCare)

Source VVL file: `level-of-care-status.csv`.

Note: source PIC X(04) vs VO `@Size(max=2)` vs T-MSIS X(3) — GAP-17.

| VVL Code | Description | Rule Citation |
|----------|-------------|---------------|
| `001` | Hospital as defined in 42 CFR 440.10 | **Medicaid_Rule (ELG.005.088)** (level-of-care-status.csv:L2) |
| `002` | Inpatient psychiatric facility for individuals under age 21 as provided in 42 CFR  440.160 | **Medicaid_Rule (ELG.005.088)** (level-of-care-status.csv:L3) |
| `003` | Nursing Facility | **Medicaid_Rule (ELG.005.088)** (level-of-care-status.csv:L4) |
| `004` | ICF/IDD | **Medicaid_Rule (ELG.005.088)** (level-of-care-status.csv:L5) |
| `005` | Other Type of Facility | **Medicaid_Rule (ELG.005.088)** (level-of-care-status.csv:L6) |
| `888` | Not Applicable (Not in LTSS program) | **Medicaid_Rule (ELG.005.088)** (level-of-care-status.csv:L7) |

#### ELG.003.046 — Preferred Language (MBR-LANG-CD → languageCode)

Source VVL file: `preferred-language.csv`.

| VVL Code | Description | Rule Citation |
|----------|-------------|---------------|
| `ABK` | Abkhazian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L2) |
| `KUT` | Kutenai | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L3) |
| `ACE` | Achinese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L4) |
| `LAD` | Ladino | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L5) |
| `ACH` | Acoli | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L6) |
| `LAH` | Lahnda | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L7) |
| `ADA` | Adangme | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L8) |
| `LAM` | Lamba | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L9) |
| `ADY` | Adyghe; Adygei | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L10) |
| `DAY` | Land Dayak languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L11) |
| `AAR` | Afar | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L12) |
| `LAO` | Lao | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L13) |
| `AFH` | Afrihili | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L14) |
| `LAT` | Latin | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L15) |
| `AFR` | Afrikaans | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L16) |
| `LAV` | Latvian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L17) |
| `AFA` | Afro-Asiatic languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L18) |
| `LEZ` | Lezghian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L19) |
| `AIN` | Ainu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L20) |
| `LIM` | Limburgan; Limburger; Limburgish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L21) |
| `AKA` | Akan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L22) |
| `LIN` | Lingala | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L23) |
| `AKK` | Akkadian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L24) |
| `LIT` | Lithuanian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L25) |
| `ALB` | Albanian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L26) |
| `JBO` | Lojban | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L27) |
| `NDS` | Low German; Low Saxon; German, Low; Saxon, Low | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L28) |
| `ALE` | Aleut | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L29) |
| `DSB` | Lower Sorbian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L30) |
| `ALG` | Algonquian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L31) |
| `LOZ` | Lozi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L32) |
| `TUT` | Altaic languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L33) |
| `LUB` | Luba-Katanga | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L34) |
| `AMH` | Amharic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L35) |
| `LUA` | Luba-Lulua | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L36) |
| `ANP` | Angika | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L37) |
| `LUI` | Luiseno | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L38) |
| `APA` | Apache languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L39) |
| `SMJ` | Lule Sami | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L40) |
| `ARA` | Arabic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L41) |
| `LUN` | Lunda | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L42) |
| `ARG` | Aragonese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L43) |
| `LUO` | Luo (Kenya and Tanzania) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L44) |
| `ARP` | Arapaho | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L45) |
| `LUS` | Lushai | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L46) |
| `ARW` | Arawak | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L47) |
| `LTZ` | Luxembourgish; Letzeburgesch | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L48) |
| `ARM` | Armenian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L49) |
| `MAC` | Macedonian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L50) |
| `RUP` | Aromanian; Arumanian; Macedo-Romanian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L51) |
| `MAD` | Madurese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L52) |
| `ART` | Artificial languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L53) |
| `MAG` | Magahi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L54) |
| `ASM` | Assamese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L55) |
| `MAI` | Maithili | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L56) |
| `AST` | Asturian; Bable; Leonese; Asturleonese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L57) |
| `MAK` | Makasar | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L58) |
| `ATH` | Athapascan languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L59) |
| `MLG` | Malagasy | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L60) |
| `AUS` | Australian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L61) |
| `MAY` | Malay | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L62) |
| `MAP` | Austronesian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L63) |
| `MAL` | Malayalam | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L64) |
| `AVA` | Avaric | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L65) |
| `MLT` | Maltese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L66) |
| `AVE` | Avestan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L67) |
| `MNC` | Manchu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L68) |
| `AWA` | Awadhi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L69) |
| `MDR` | Mandar | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L70) |
| `AYM` | Aymara | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L71) |
| `MAN` | Mandingo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L72) |
| `AZE` | Azerbaijani | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L73) |
| `MNI` | Manipuri | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L74) |
| `BAN` | Balinese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L75) |
| `MNO` | Manobo languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L76) |
| `BAT` | Baltic languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L77) |
| `GLV` | Manx | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L78) |
| `BAL` | Baluchi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L79) |
| `MAO` | Maori | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L80) |
| `BAM` | Bambara | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L81) |
| `ARN` | Mapudungun; Mapuche | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L82) |
| `BAI` | Bamileke languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L83) |
| `MAR` | Marathi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L84) |
| `BAD` | Banda languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L85) |
| `CHM` | Mari | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L86) |
| `BNT` | Bantu languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L87) |
| `MAH` | Marshallese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L88) |
| `BAS` | Basa | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L89) |
| `MWR` | Marwari | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L90) |
| `BAK` | Bashkir | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L91) |
| `MAS` | Masai | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L92) |
| `BAQ` | Basque | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L93) |
| `MYN` | Mayan languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L94) |
| `BTK` | Batak languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L95) |
| `MEN` | Mende | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L96) |
| `BEJ` | Beja; Bedawiyet | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L97) |
| `MIC` | Mi'kmaq; Micmac | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L98) |
| `BEL` | Belarusian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L99) |
| `MIN` | Minangkabau | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L100) |
| `BEM` | Bemba | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L101) |
| `MWL` | Mirandese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L102) |
| `BEN` | Bengali | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L103) |
| `MOH` | Mohawk | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L104) |
| `BER` | Berber languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L105) |
| `MDF` | Moksha | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L106) |
| `BHO` | Bhojpuri | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L107) |
| `LOL` | Mongo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L108) |
| `BIH` | Bihari languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L109) |
| `MON` | Mongolian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L110) |
| `BIK` | Bikol | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L111) |
| `MKH` | Mon-Khmer languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L112) |
| `BIN` | Bini; Edo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L113) |
| `MOS` | Mossi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L114) |
| `BIS` | Bislama | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L115) |
| `MUL` | Multiple languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L116) |
| `BYN` | Blin; Bilin | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L117) |
| `MUN` | Munda languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L118) |
| `ZBL` | Blissymbols; Blissymbolics; Bliss | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L119) |
| `NAH` | Nahuatl languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L120) |
| `NOB` | Bokmål, Norwegian; Norwegian Bokmål | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L121) |
| `NAU` | Nauru | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L122) |
| `BOS` | Bosnian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L123) |
| `NAV` | Navajo; Navaho | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L124) |
| `BRA` | Braj | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L125) |
| `NDE` | Ndebele, North; North Ndebele | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L126) |
| `BRE` | Breton | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L127) |
| `NBL` | Ndebele, South; South Ndebele | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L128) |
| `BUG` | Buginese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L129) |
| `NDO` | Ndonga | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L130) |
| `BUL` | Bulgarian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L131) |
| `NAP` | Neapolitan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L132) |
| `BUA` | Buriat | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L133) |
| `NEW` | Nepal Bhasa; Newari | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L134) |
| `BUR` | Burmese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L135) |
| `NEP` | Nepali | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L136) |
| `CAD` | Caddo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L137) |
| `NIA` | Nias | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L138) |
| `CAT` | Catalan; Valencian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L139) |
| `NIC` | Niger-Kordofanian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L140) |
| `CAU` | Caucasian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L141) |
| `SSA` | Nilo-Saharan languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L142) |
| `CEB` | Cebuano | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L143) |
| `NIU` | Niuean | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L144) |
| `CEL` | Celtic languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L145) |
| `NQO` | N'Ko | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L146) |
| `CAI` | Central American Indian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L147) |
| `NOG` | Nogai | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L148) |
| `KHM` | Central Khmer | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L149) |
| `NON` | Norse, Old | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L150) |
| `CHG` | Chagatai | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L151) |
| `NAI` | North American Indian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L152) |
| `CMC` | Chamic languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L153) |
| `FRR` | Northern Frisian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L154) |
| `CHA` | Chamorro | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L155) |
| `SME` | Northern Sami | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L156) |
| `CHE` | Chechen | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L157) |
| `NOR` | Norwegian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L158) |
| `CHR` | Cherokee | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L159) |
| `NNO` | Norwegian Nynorsk; Nynorsk, Norwegian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L160) |
| `CHY` | Cheyenne | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L161) |
| `NUB` | Nubian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L162) |
| `CHB` | Chibcha | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L163) |
| `NYM` | Nyamwezi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L164) |
| `NYA` | Chichewa; Chewa; Nyanja | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L165) |
| `NYN` | Nyankole | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L166) |
| `CHI` | Chinese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L167) |
| `NYO` | Nyoro | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L168) |
| `CHN` | Chinook jargon | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L169) |
| `NZI` | Nzima | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L170) |
| `CHP` | Chipewyan; Dene Suline | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L171) |
| `OCI` | Occitan (post 1500) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L172) |
| `CHO` | Choctaw | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L173) |
| `ARC` | Official Aramaic (700-300 BCE); Imperial Aramaic (700-300 BCE) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L174) |
| `CHU` | Church Slavic; Old Slavonic; Church Slavonic; Old Bulgarian; Old Church Slavonic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L175) |
| `OJI` | Ojibwa | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L176) |
| `CHK` | Chuukese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L177) |
| `ORI` | Oriya | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L178) |
| `CHV` | Chuvash | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L179) |
| `ORM` | Oromo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L180) |
| `NWC` | Classical Newari; Old Newari; Classical Nepal Bhasa | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L181) |
| `OSA` | Osage | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L182) |
| `SYC` | Classical Syriac | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L183) |
| `OSS` | Ossetian; Ossetic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L184) |
| `COP` | Coptic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L185) |
| `OTO` | Otomian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L186) |
| `COR` | Cornish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L187) |
| `PAL` | Pahlavi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L188) |
| `COS` | Corsican | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L189) |
| `PAU` | Palauan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L190) |
| `CRE` | Cree | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L191) |
| `PLI` | Pali | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L192) |
| `MUS` | Creek | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L193) |
| `PAM` | Pampanga; Kapampangan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L194) |
| `CRP` | Creoles and pidgins | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L195) |
| `PAG` | Pangasinan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L196) |
| `CPE` | Creoles and pidgins, English based | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L197) |
| `PAN` | Panjabi; Punjabi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L198) |
| `CPF` | Creoles and pidgins, French-based | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L199) |
| `PAP` | Papiamento | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L200) |
| `CPP` | Creoles and pidgins, Portuguese-based | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L201) |
| `PAA` | Papuan languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L202) |
| `CRH` | Crimean Tatar; Crimean Turkish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L203) |
| `NSO` | Pedi; Sepedi; Northern Sotho | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L204) |
| `HRV` | Croatian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L205) |
| `PER` | Persian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L206) |
| `CUS` | Cushitic languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L207) |
| `PEO` | Persian, Old (ca.600-400 B.C.) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L208) |
| `CZE` | Czech | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L209) |
| `PHI` | Philippine languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L210) |
| `DAK` | Dakota | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L211) |
| `PHN` | Phoenician | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L212) |
| `DAN` | Danish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L213) |
| `PON` | Pohnpeian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L214) |
| `DAR` | Dargwa | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L215) |
| `POL` | Polish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L216) |
| `DEL` | Delaware | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L217) |
| `POR` | Portuguese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L218) |
| `DIN` | Dinka | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L219) |
| `PRA` | Prakrit languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L220) |
| `DIV` | Divehi; Dhivehi; Maldivian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L221) |
| `PRO` | Provençal, Old (to 1500);Occitan, Old (to 1500) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L222) |
| `DOI` | Dogri | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L223) |
| `PUS` | Pushto; Pashto | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L224) |
| `DGR` | Dogrib | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L225) |
| `QUE` | Quechua | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L226) |
| `DRA` | Dravidian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L227) |
| `RAJ` | Rajasthani | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L228) |
| `DUA` | Duala | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L229) |
| `RAP` | Rapanui | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L230) |
| `DUM` | Dutch, Middle (ca.1050-1350) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L231) |
| `RAR` | Rarotongan; Cook Islands Maori | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L232) |
| `DUT` | Dutch; Flemish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L233) |
| `ROA` | Romance languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L234) |
| `DYU` | Dyula | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L235) |
| `RUM` | Romanian; Moldavian; Moldovan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L236) |
| `DZO` | Dzongkha | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L237) |
| `ROH` | Romansh | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L238) |
| `FRS` | Eastern Frisian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L239) |
| `ROM` | Romany | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L240) |
| `EFI` | Efik | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L241) |
| `RUN` | Rundi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L242) |
| `EGY` | Egyptian (Ancient) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L243) |
| `RUS` | Russian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L244) |
| `EKA` | Ekajuk | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L245) |
| `SAL` | Salishan languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L246) |
| `ELX` | Elamite | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L247) |
| `SAM` | Samaritan Aramaic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L248) |
| `ENG` | English | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L249) |
| `SMI` | Sami languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L250) |
| `ENM` | English, Middle (1100-1500) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L251) |
| `SMO` | Samoan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L252) |
| `ANG` | English, Old (ca.450-1100) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L253) |
| `SAD` | Sandawe | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L254) |
| `MYV` | Erzya | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L255) |
| `SAG` | Sango | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L256) |
| `EPO` | Esperanto | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L257) |
| `SAN` | Sanskrit | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L258) |
| `EST` | Estonian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L259) |
| `SAT` | Santali | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L260) |
| `EWE` | Ewe | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L261) |
| `SRD` | Sardinian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L262) |
| `EWO` | Ewondo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L263) |
| `SAS` | Sasak | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L264) |
| `FAN` | Fang | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L265) |
| `SCO` | Scots | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L266) |
| `FAT` | Fanti | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L267) |
| `SEL` | Selkup | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L268) |
| `FAO` | Faroese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L269) |
| `SEM` | Semitic languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L270) |
| `FIJ` | Fijian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L271) |
| `SRP` | Serbian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L272) |
| `FIL` | Filipino; Pilipino | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L273) |
| `SRR` | Serer | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L274) |
| `FIN` | Finnish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L275) |
| `SHN` | Shan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L276) |
| `FIU` | Finno-Ugrian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L277) |
| `SNA` | Shona | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L278) |
| `FON` | Fon | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L279) |
| `III` | Sichuan Yi; Nuosu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L280) |
| `FRE` | French | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L281) |
| `SCN` | Sicilian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L282) |
| `FRM` | French, Middle (ca.1400-1600) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L283) |
| `SID` | Sidamo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L284) |
| `FRO` | French, Old (842-ca.1400) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L285) |
| `SGN` | Sign Languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L286) |
| `FUR` | Friulian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L287) |
| `BLA` | Siksika | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L288) |
| `FUL` | Fulah | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L289) |
| `SND` | Sindhi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L290) |
| `GAA` | Ga | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L291) |
| `SIN` | Sinhala; Sinhalese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L292) |
| `GLA` | Gaelic; Scottish Gaelic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L293) |
| `SIT` | Sino-Tibetan languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L294) |
| `CAR` | Galibi Carib | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L295) |
| `SIO` | Siouan languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L296) |
| `GLG` | Galician | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L297) |
| `SMS` | Skolt Sami | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L298) |
| `LUG` | Ganda | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L299) |
| `DEN` | Slave (Athapascan) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L300) |
| `GAY` | Gayo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L301) |
| `SLA` | Slavic languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L302) |
| `GBA` | Gbaya | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L303) |
| `SLO` | Slovak | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L304) |
| `GEZ` | Geez | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L305) |
| `SLV` | Slovenian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L306) |
| `GEO` | Georgian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L307) |
| `SOG` | Sogdian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L308) |
| `GER` | German | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L309) |
| `SOM` | Somali | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L310) |
| `GMH` | German, Middle High (ca.1050-1500) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L311) |
| `SON` | Songhai languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L312) |
| `GOH` | German, Old High (ca.750-1050) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L313) |
| `SNK` | Soninke | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L314) |
| `GEM` | Germanic languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L315) |
| `WEN` | Sorbian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L316) |
| `GIL` | Gilbertese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L317) |
| `SOT` | Sotho, Southern | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L318) |
| `GON` | Gondi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L319) |
| `SAI` | South American Indian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L320) |
| `GOR` | Gorontalo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L321) |
| `ALT` | Southern Altai | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L322) |
| `GOT` | Gothic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L323) |
| `SMA` | Southern Sami | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L324) |
| `GRB` | Grebo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L325) |
| `SPA` | Spanish; Castilian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L326) |
| `GRC` | Greek, Ancient (to 1453) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L327) |
| `SRN` | Sranan Tongo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L328) |
| `GRE` | Greek, Modern (1453-) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L329) |
| `SUK` | Sukuma | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L330) |
| `GRN` | Guarani | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L331) |
| `SUX` | Sumerian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L332) |
| `GUJ` | Gujarati | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L333) |
| `SUN` | Sundanese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L334) |
| `GWI` | Gwich'in | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L335) |
| `SUS` | Susu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L336) |
| `HAI` | Haida | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L337) |
| `SWA` | Swahili | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L338) |
| `HAT` | Haitian; Haitian Creole | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L339) |
| `SSW` | Swati | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L340) |
| `HAU` | Hausa | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L341) |
| `SWE` | Swedish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L342) |
| `HAW` | Hawaiian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L343) |
| `GSW` | Swiss German; Alemannic; Alsatian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L344) |
| `HEB` | Hebrew | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L345) |
| `SYR` | Syriac | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L346) |
| `HER` | Herero | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L347) |
| `TGL` | Tagalog | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L348) |
| `HIL` | Hiligaynon | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L349) |
| `TAH` | Tahitian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L350) |
| `HIM` | Himachali languages; Western Pahari languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L351) |
| `TAI` | Tai languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L352) |
| `HIN` | Hindi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L353) |
| `TGK` | Tajik | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L354) |
| `HMO` | Hiri Motu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L355) |
| `TMH` | Tamashek | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L356) |
| `HIT` | Hittite | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L357) |
| `TAM` | Tamil | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L358) |
| `HMN` | Hmong; Mong | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L359) |
| `TAT` | Tatar | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L360) |
| `HUN` | Hungarian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L361) |
| `TEL` | Telugu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L362) |
| `HUP` | Hupa | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L363) |
| `TER` | Tereno | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L364) |
| `IBA` | Iban | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L365) |
| `TET` | Tetum | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L366) |
| `ICE` | Icelandic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L367) |
| `THA` | Thai | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L368) |
| `IDO` | Ido | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L369) |
| `TIB` | Tibetan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L370) |
| `IBO` | Igbo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L371) |
| `TIG` | Tigre | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L372) |
| `IJO` | Ijo languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L373) |
| `TIR` | Tigrinya | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L374) |
| `ILO` | Iloko | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L375) |
| `TEM` | Timne | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L376) |
| `SMN` | Inari Sami | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L377) |
| `TIV` | Tiv | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L378) |
| `INC` | Indic languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L379) |
| `TLI` | Tlingit | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L380) |
| `INE` | Indo-European languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L381) |
| `TPI` | Tok Pisin | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L382) |
| `IND` | Indonesian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L383) |
| `TKL` | Tokelau | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L384) |
| `INH` | Ingush | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L385) |
| `TOG` | Tonga (Nyasa) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L386) |
| `INA` | Interlingua (International Auxiliary Language Association) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L387) |
| `TON` | Tonga (Tonga Islands) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L388) |
| `ILE` | Interlingue; Occidental | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L389) |
| `TSI` | Tsimshian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L390) |
| `IKU` | Inuktitut | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L391) |
| `TSO` | Tsonga | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L392) |
| `IPK` | Inupiaq | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L393) |
| `TSN` | Tswana | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L394) |
| `IRA` | Iranian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L395) |
| `TUM` | Tumbuka | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L396) |
| `GLE` | Irish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L397) |
| `TUP` | Tupi languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L398) |
| `MGA` | Irish, Middle (900-1200) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L399) |
| `TUR` | Turkish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L400) |
| `SGA` | Irish, Old (to 900) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L401) |
| `OTA` | Turkish, Ottoman (1500-1928) | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L402) |
| `IRO` | Iroquoian languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L403) |
| `TUK` | Turkmen | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L404) |
| `ITA` | Italian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L405) |
| `TVL` | Tuvalu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L406) |
| `JPN` | Japanese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L407) |
| `TYV` | Tuvinian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L408) |
| `JAV` | Javanese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L409) |
| `TWI` | Twi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L410) |
| `JRB` | Judeo-Arabic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L411) |
| `UDM` | Udmurt | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L412) |
| `JPR` | Judeo-Persian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L413) |
| `UGA` | Ugaritic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L414) |
| `KBD` | Kabardian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L415) |
| `UIG` | Uighur; Uyghur | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L416) |
| `KAB` | Kabyle | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L417) |
| `UKR` | Ukrainian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L418) |
| `KAC` | Kachin; Jingpho | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L419) |
| `UMB` | Umbundu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L420) |
| `KAL` | Kalaallisut; Greenlandic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L421) |
| `MIS` | Uncoded languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L422) |
| `XAL` | Kalmyk; Oirat | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L423) |
| `UND` | Undetermined | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L424) |
| `KAM` | Kamba | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L425) |
| `HSB` | Upper Sorbian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L426) |
| `KAN` | Kannada | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L427) |
| `URD` | Urdu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L428) |
| `KAU` | Kanuri | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L429) |
| `UZB` | Uzbek | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L430) |
| `KRC` | Karachay-Balkar | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L431) |
| `VAI` | Vai | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L432) |
| `KAA` | Kara-Kalpak | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L433) |
| `VEN` | Venda | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L434) |
| `KRL` | Karelian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L435) |
| `VIE` | Vietnamese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L436) |
| `KAR` | Karen languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L437) |
| `VOL` | Volapük | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L438) |
| `KAS` | Kashmiri | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L439) |
| `VOT` | Votic | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L440) |
| `CSB` | Kashubian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L441) |
| `WAK` | Wakashan languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L442) |
| `KAW` | Kawi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L443) |
| `WLN` | Walloon | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L444) |
| `KAZ` | Kazakh | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L445) |
| `WAR` | Waray | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L446) |
| `KHA` | Khasi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L447) |
| `WAS` | Washo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L448) |
| `KHI` | Khoisan languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L449) |
| `WEL` | Welsh | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L450) |
| `KHO` | Khotanese; Sakan | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L451) |
| `FRY` | Western Frisian | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L452) |
| `KIK` | Kikuyu; Gikuyu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L453) |
| `WAL` | Wolaitta; Wolaytta | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L454) |
| `KMB` | Kimbundu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L455) |
| `WOL` | Wolof | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L456) |
| `KIN` | Kinyarwanda | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L457) |
| `XHO` | Xhosa | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L458) |
| `KIR` | Kirghiz; Kyrgyz | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L459) |
| `SAH` | Yakut | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L460) |
| `TLH` | Klingon; tlhIngan-Hol | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L461) |
| `YAO` | Yao | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L462) |
| `KOM` | Komi | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L463) |
| `YAP` | Yapese | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L464) |
| `KON` | Kongo | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L465) |
| `YID` | Yiddish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L466) |
| `KOK` | Konkani | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L467) |
| `YOR` | Yoruba | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L468) |
| `KOR` | Korean | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L469) |
| `YPK` | Yupik languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L470) |
| `KOS` | Kosraean | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L471) |
| `ZND` | Zande languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L472) |
| `KPE` | Kpelle | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L473) |
| `ZAP` | Zapotec | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L474) |
| `KRO` | Kru languages | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L475) |
| `ZZA` | Zaza; Dimili; Dimli; Kirdki; Kirmanjki; Zazaki | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L476) |
| `KUA` | Kuanyama; Kwanyama | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L477) |
| `ZEN` | Zenaga | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L478) |
| `KUM` | Kumyk | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L479) |
| `ZHA` | Zhuang; Chuang | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L480) |
| `KUR` | Kurdish | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L481) |
| `ZUL` | Zulu | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L482) |
| `KRU` | Kurukh | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L483) |
| `ZUN` | Zuni | **Medicaid_Rule (ELG.003.046)** (preferred-language.csv:L484) |

### E. Valid Value Lists Applied (`Medicaid_Rule` VVL Index)

| Data Element | VVL File | Row Count | Mapping Context |
|--------------|----------|-----------|-----------------|
| **Medicaid_Rule (ELG.002.023)** | `sex.csv` | 3 | Sex (MBR-GNDR-CD → gender) |
| **Medicaid_Rule (ELG.003.034)** | `marital-status.csv` | 14 | Marital Status (MRTL-STAT-CD → maritalStatus) |
| **Medicaid_Rule (ELG.003.039)** | `veteran-indicator.csv` | 2 | Veteran Indicator (VET-IND-CD → veteransIndicator) |
| **Medicaid_Rule (ELG.003.045)** | `english-proficiency.csv` | 4 | English Proficiency (ENG-PRFCY-CD → primaryLanguageEnglishProficiencyCode) |
| **Medicaid_Rule (ELG.003.047)** | `household-size.csv` | 8 | Household Size (HH-SIZE-NUM → householdSize) |
| **Medicaid_Rule (ELG.005.087)** | `eligibility-group.csv` | 74 | Eligibility Group (MBR-ELIG-CAT → categoryOfEligibility) |
| **Medicaid_Rule (ELG.005.088)** | `level-of-care-status.csv` | 6 | Level of Care Status (LTC-LVL-CARE-CD → levelOfCare) |
| **Medicaid_Rule (ELG.003.046)** | `preferred-language.csv` | 483 | Preferred Language (MBR-LANG-CD → languageCode) |

### F. Medicare.gov / T-MSIS Validation Rules Applied (`Medicaid_Rule`)

Rules linked from research `field_mappings` where `t_msis_rule` is set (dictionary 4.0.33):

| Data Element | Source Field | Target Attribute | VVL File |
|--------------|--------------|------------------|----------|
| **Medicaid_Rule (ELG.002.023)** | `MBR-GNDR-CD` | `gender` | sex.csv |
| **Medicaid_Rule (ELG.016.213)** | `MBR-RACE-CD` | `race` | — (no CONFIRMED VVL in research; see gaps) |
| **Medicaid_Rule (ELG.003.046)** | `MBR-LANG-CD` | `languageCode` | preferred-language.csv |
| **Medicaid_Rule (ELG.005.087)** | `MBR-ELIG-CAT` | `categoryOfEligibility` | eligibility-group.csv |
| **Medicaid_Rule (ELG.005.088)** | `LTC-LVL-CARE-CD` | `levelOfCare` | level-of-care-status.csv |
| **Medicaid_Rule (ELG.003.034)** | `MRTL-STAT-CD` | `maritalStatus` | marital-status.csv |
| **Medicaid_Rule (ELG.003.039)** | `VET-IND-CD` | `veteransIndicator` | veteran-indicator.csv |
| **Medicaid_Rule (ELG.003.045)** | `ENG-PRFCY-CD` | `primaryLanguageEnglishProficiencyCode` | english-proficiency.csv |
| **Medicaid_Rule (ELG.003.047)** | `HH-SIZE-NUM` | `householdSize` | household-size.csv |

Additional noted open lists without CONFIRMED VVL members in research: race (ELG.016.213 / GAP-04), termination reason (GAP-05), federal match (GAP-06), disability type (GAP-19), health home level (GAP-20), Part D opt-out (GAP-21), lock-in reasons (GAP-22/GAP-23), immigrant admission (GAP-24).

