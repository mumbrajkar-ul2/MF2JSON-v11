#!/usr/bin/env python3
"""Generate research/Integration_Research_MemberEligibility.yaml from layout + VO."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import yaml

INTEGRATION_ROOT = Path(__file__).resolve().parent.parent
LIBRARY_ROOT = INTEGRATION_ROOT / "../../medicare-validation-rules"
VVL_DIR = LIBRARY_ROOT / "rules/eligibility/value-lists"
CSV_PATH = INTEGRATION_ROOT / "source/MEMBERELIGIBILITY.csv"
VO_PATH = INTEGRATION_ROOT / "target/MemberEligibilityVO.md"
OUT_PATH = INTEGRATION_ROOT / "research/Integration_Research_MemberEligibility.yaml"

# source_field -> (target_attribute, vo_line, java_type, t_msis_rule, vvl_file)
MAPPING: dict[str, tuple[str, int, str, str | None, str | None]] = {
    "CTR-INTF-DT": ("interfaceDate", 4, "LocalDate", None, None),
    "CTR-SRVC-DT": ("serviceDate", 8, "YearMonth", None, None),
    "CTR-PROV-ID": ("providerId", 12, "String", None, None),
    "CTR-PLAN-NM": ("planName", 16, "String", None, None),
    "CTR-MED-CRD-ID": ("medicaidCardId", 21, "String", None, None),
    "CTR-MCILD-NUM": ("mciId", 25, "String", None, None),
    "CTR-SSN-TXT": ("ssn", 29, "String", None, None),
    "CTR-MCR-ID-NUM": ("medicareIdNumber", 34, "String", None, None),
    "MBR-LAST-NM": ("memberLastName", 39, "String", None, None),
    "MBR-FRST-NM": ("memberFirstName", 43, "String", None, None),
    "MBR-MID-NM": ("memberMiddleName", 47, "String", None, None),
    "MBR-ML-ADR-LN1": ("mailingAdressLine1", 52, "String", None, None),
    "MBR-ML-ADR-LN2": ("mailingAddressLine2", 56, "String", None, None),
    "MBR-ML-CITY-NM": ("mailingAddressCity", 60, "String", None, None),
    "MBR-ML-ST-CD": ("mailingState", 64, "String", None, None),
    "MBR-ML-ZIP-5": ("mailingZip5", 68, "String", None, None),
    "MBR-ML-ZIP-4": ("mailingZip4", 73, "String", None, None),
    "MBR-RS-ADR-LN1": ("residenceAdressLine1", 79, "String", None, None),
    "MBR-RS-ADR-LN2": ("residenceAddressLine2", 83, "String", None, None),
    "MBR-RS-CITY-NM": ("residenceAddressCity", 87, "String", None, None),
    "MBR-RS-ST-CD": ("residenceState", 91, "String", None, None),
    "MBR-RS-ZIP-5": ("residenceZip5", 95, "String", None, None),
    "MBR-RS-ZIP-4": ("residenceZip4", 100, "String", None, None),
    "MBR-PHN-NUM": ("memberContactNumber", 105, "String", None, None),
    "MBR-GEO-CNTY-CD": ("geoCountyCode", 109, "String", None, None),
    "MBR-ADM-OFF-CD": ("adminOfficeCode", 113, "String", None, None),
    "MBR-DOB-DT": ("dateOfBirth", 118, "LocalDate", None, None),
    "MBR-DOD-DT": ("dateOfDeath", 122, "LocalDate", None, None),
    "MBR-GNDR-CD": ("gender", 126, "String", "ELG.002.023", "sex.csv"),
    "MBR-RACE-CD": ("race", 131, "String", "ELG.016.213", None),
    "MBR-LANG-CD": ("languageCode", 135, "String", "ELG.003.046", "preferred-language.csv"),
    "MBR-DSBL-TYP": ("diabilityType", 139, "String", None, None),
    "MBR-PREG-DUE-DT": ("pregnancyDueDate", 143, "LocalDate", None, None),
    "MBR-NPI-ID": ("npiId", 147, "String", None, None),
    "MBR-ELIG-CAT": ("categoryOfEligibility", 153, "String", "ELG.005.087", "eligibility-group.csv"),
    "MBR-TERM-RSN-CD": ("eligibilityTerminationReasonCode", 157, "String", None, None),
    "MBR-FED-MCH-CD": ("federalMatchCode", 161, "String", None, None),
    "HH-NPI-ID": ("healthHomeNPIId", 166, "String", None, None),
    "HH-BEG-DT": ("healthHomeBeginDate", 170, "LocalDate", None, None),
    "HH-END-DT": ("healthHomeEndDate", 174, "LocalDate", None, None),
    "HH-LVL-CD": ("healthHomeLevelCode", 178, "String", None, None),
    "LTC-BEG-DT": ("ltcBeginDate", 183, "LocalDate", None, None),
    "LTC-END-DT": ("ltcEndDate", 187, "LocalDate", None, None),
    "LTC-LVL-CARE-CD": ("levelOfCare", 191, "String", "ELG.005.088", "level-of-care-status.csv"),
    "LTC-CURR-BEG-DT": ("ltcPatientLiabilityCurrentBeginDate", 195, "LocalDate", None, None),
    "LTC-CURR-END-DT": ("ltcPatientLiabilityCurrentEndDate", 199, "LocalDate", None, None),
    "LTC-CURR-LIAB-AM": ("ltcPatientLiabilityCurrentAmount", 203, "BigDecimal", None, None),
    "LTC-PREV-BEG-DT": ("ltcPatientLiabilityPreviousBeginDate", 207, "LocalDate", None, None),
    "LTC-PREV-END-DT": ("ltcPatientLiabilityPreviousEndDate", 211, "LocalDate", None, None),
    "LTC-PREV-LIAB-AM": ("ltcPatientLiabilityPreviousAmount", 215, "BigDecimal", None, None),
    "DSBL-BEG-DT": ("disabilityBeginDate", 220, "LocalDate", None, None),
    "DSBL-END-DT": ("disabilityEndDate", 224, "LocalDate", None, None),
    "MCR-PTA-BEG-DT": ("partABeginDate", 229, "LocalDate", None, None),
    "MCR-PTA-END-DT": ("partAEndDate", 233, "LocalDate", None, None),
    "MCR-PTB-BEG-DT": ("partBBeginDate", 237, "LocalDate", None, None),
    "MCR-PTB-END-DT": ("partBEndDate", 241, "LocalDate", None, None),
    "MCR-PTC-BEG-DT": ("partCBeginDate", 245, "LocalDate", None, None),
    "MCR-PTC-END-DT": ("partCEndDate", 249, "LocalDate", None, None),
    "MCR-PTC-CNTR-ID": ("partCPBPContractId", 253, "String", None, None),
    "MCR-PBP-ORG-NM": ("pbpOrganizationName", 257, "String", None, None),
    "MCR-PTC-PLAN-NM": ("partCPBPPlanName", 261, "String", None, None),
    "MCR-PTD-BEG-DT": ("partDBeginDate", 265, "LocalDate", None, None),
    "MCR-PTD-END-DT": ("partDEndDate", 269, "LocalDate", None, None),
    "MCR-PTD-OPT-IND": ("partDOptOutIndex", 273, "String", None, None),
    "MCR-PTD-CNTR-ID": ("partDPBPContractId", 277, "String", None, None),
    "MCR-PTD-PLAN-ID": ("partDPBPPlanID", 281, "String", None, None),
    "CS-MGMT-NM": ("caseMgmtName", 287, "String", None, None),
    "CS-ADR-LN1": ("caseMgmtAdressLine1", 290, "String", None, None),
    "CS-ADR-LN2": ("caseMgmtAddressLine2", 294, "String", None, None),
    "CS-CITY-NM": ("caseMgmtAddressCity", 298, "String", None, None),
    "CS-ST-CD": ("caseMgmtState", 302, "String", None, None),
    "CS-ZIP-5": ("caseMgmtZip5", 306, "String", None, None),
    "CS-ZIP-4": ("caseMgmtZip4", 310, "String", None, None),
    "CS-PHN-NUM": ("caseMgmtPhoneNum", 314, "String", None, None),
    "REP-LAST-NM": ("authRepLastName", 319, "String", None, None),
    "REP-FRST-NM": ("authRepFirstName", 323, "String", None, None),
    "REP-MID-NM": ("authRepMiddleName", 327, "String", None, None),
    "REP-ADR-LN1": ("authRepAdressLine1", 331, "String", None, None),
    "REP-ADR-LN2": ("authRepAddressLine2", 335, "String", None, None),
    "REP-CITY-NM": ("authRepAddressCity", 339, "String", None, None),
    "REP-ST-CD": ("authRepState", 343, "String", None, None),
    "REP-ZIP-5": ("authRepZip5", 347, "String", None, None),
    "REP-ZIP-4": ("authRepZip4", 351, "String", None, None),
    "REP-PHN-NUM": ("authRepPhoneNum", 355, "String", None, None),
    "PY-LAST-NM": ("payeeLastName", 360, "String", None, None),
    "PY-FRST-NM": ("payeeFirstName", 364, "String", None, None),
    "PY-MID-NM": ("payeeMiddleName", 368, "String", None, None),
    "PY-ADR-LN1": ("payeeAdressLine1", 372, "String", None, None),
    "PY-ADR-LN2": ("payeeAddressLine2", 376, "String", None, None),
    "PY-CITY-NM": ("payeeAddressCity", 380, "String", None, None),
    "PY-ST-CD": ("payeeState", 384, "String", None, None),
    "PY-ZIP-5": ("payeeZip5", 388, "String", None, None),
    "PY-ZIP-4": ("payeeZip4", 392, "String", None, None),
    "PY-PHN-NUM": ("payeePhoneNum", 396, "String", None, None),
    "LCK-BEG-DT": ("lockinBeginDate", 401, "LocalDate", None, None),
    "LCK-END-DT": ("lockinEndDate", 405, "LocalDate", None, None),
    "LCK-ASGN-RSN": ("lockinAssignmentReasonCode", 409, "String", None, None),
    "LCK-CHG-RSN": ("lockinChangeReasonCode", 413, "String", None, None),
    "HPLN-RT-AMT": ("hplanRateAmount", 418, "BigDecimal", None, None),
    "TOT-RT-AMT": ("totalRateAmount", 422, "BigDecimal", None, None),
    "XFER-PLN-ID": ("transferPlanId", 427, "String", None, None),
    "FCLTY-ID": ("facilityId", 431, "String", None, None),
    "BKG-DT": ("bookingDate", 435, "LocalDate", None, None),
    "RLSE-DT": ("releaseDate", 439, "LocalDate", None, None),
    "MRTL-STAT-CD": ("maritalStatus", 444, "String", "ELG.003.034", "marital-status.csv"),
    "VET-IND-CD": ("veteransIndicator", 448, "String", "ELG.003.039", "veteran-indicator.csv"),
    "EMAIL-ADR-TXT": ("emailAddress", 453, "String", None, None),
    "ENG-PRFCY-CD": (
        "primaryLanguageEnglishProficiencyCode",
        457,
        "String",
        "ELG.003.045",
        "english-proficiency.csv",
    ),
    "HH-SIZE-NUM": ("householdSize", 461, "Integer", "ELG.003.047", "household-size.csv"),
    "IMM-ADMS-STAT": ("immigrantAdmissionStatus", 464, "String", None, None),
    "MC-END-DT": ("mcEndDate", 468, "LocalDate", None, None),
    "MC-BEG-DT": ("mcBeginDate", 472, "LocalDate", None, None),
    "SRC-FILE-NM": ("fileName", 476, "String", None, None),
}

VVL_FILES = [
    "sex.csv",
    "marital-status.csv",
    "veteran-indicator.csv",
    "english-proficiency.csv",
    "household-size.csv",
    "eligibility-group.csv",
    "level-of-care-status.csv",
    "preferred-language.csv",
]

GAPS = [
    {
        "id": "GAP-01",
        "topic": "Source character encoding",
        "evidence": "MEMBERELIGIBILITY.csv, MEMBERELIGIBILITY.CPY, and MemberEligibilityVO.md do not specify charset (e.g. ISO-8859-1 vs EBCDIC).",
        "owner": "MMIS SME",
        "priority": "P1",
    },
    {
        "id": "GAP-02",
        "topic": "CTR-SRVC-DT to serviceDate (YearMonth)",
        "evidence": "Source PIC X(08) at positions 9-16 (MEMBERELIGIBILITY.csv:L3); VO serviceDate uses pattern yyyyMM (MemberEligibilityVO.md:L8-L10). Truncation/padding rules not stated in artifacts.",
        "owner": "MMIS SME",
        "priority": "P1",
    },
    {
        "id": "GAP-03",
        "topic": "MBR-GNDR-CD width and code normalization",
        "evidence": "Source PIC X(04) at 435-438 (MEMBERELIGIBILITY.csv:L30); VO gender @Size(max=1) with pattern [MFU]? (MemberEligibilityVO.md:L126-L129); T-MSIS Sex is X(1) per ELG.002.023.",
        "owner": "MMIS SME",
        "priority": "P1",
    },
    {
        "id": "GAP-04",
        "topic": "Race valid value list",
        "evidence": "MBR-RACE-CD mapped to race (ELG.016.213 per data-elements.csv) but no CONFIRMED race VVL CSV under rules/eligibility/value-lists/.",
        "owner": "MMIS SME",
        "priority": "P1",
    },
    {
        "id": "GAP-05",
        "topic": "Eligibility termination reason code",
        "evidence": "MBR-TERM-RSN-CD present in layout (MEMBERELIGIBILITY.csv:L37); no matching CONFIRMED VVL CSV in value-lists/ and no decode table in MemberEligibilityVO.md.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-06",
        "topic": "Federal match code",
        "evidence": "MBR-FED-MCH-CD present in layout (MEMBERELIGIBILITY.csv:L38); no CONFIRMED VVL CSV in value-lists/ for federalMatchCode.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-07",
        "topic": "COMP-3 packed decimal decode",
        "evidence": "LTC liability and rate amount fields use PIC S9(7)V99 COMP-3; VO uses @Digits(integer=7, fraction=2) but byte order/sign nibble rules not documented in copybook or VO.",
        "owner": "MMIS SME",
        "priority": "P1",
    },
    {
        "id": "GAP-08",
        "topic": "HH-SIZE-NUM binary COMP",
        "evidence": "Source PIC 9(04) COMP (2 bytes) at 1422-1423 (MEMBERELIGIBILITY.csv:L110); VO householdSize is Integer (MemberEligibilityVO.md:L461-L462); COMP endianness not stated in MEMBERELIGIBILITY.CPY.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-09",
        "topic": "Sentinel / default dates",
        "evidence": "Multiple PIC X(08) date fields in layout; VO @JsonFormat yyyyMMdd on date fields without documented sentinel handling (e.g. 00000000, 99999999) in artifacts.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-10",
        "topic": "Phone number formatting",
        "evidence": "MBR-PHN-NUM and related fields PIC X(12) in source; VO memberContactNumber @Size(max=10) (MemberEligibilityVO.md:L105-L107). Strip/pad rules not stated.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-11",
        "topic": "Record framing and file terminator",
        "evidence": "MEMBERELIGIBILITY.csv defines a 1473-byte fixed layout (SRC-FILE-NM ends at 1473); no LF/CRLF, RDW, or block descriptor documented in .CPY or VO.",
        "owner": "MMIS SME",
        "priority": "P1",
    },
    {
        "id": "GAP-12",
        "topic": "HIPAA / PHI handling for DLQ records",
        "evidence": "MEMBERELIGIBILITY layout and MemberEligibilityVO.md contain SSN and demographic PHI; no dead-letter redaction or retention policy in provided artifacts.",
        "owner": "Sec/Compliance",
        "priority": "P1",
    },
    {
        "id": "GAP-13",
        "topic": "CMdS operations (API contract, file arrival, SLA, observability)",
        "evidence": "Integration project provides MemberEligibilityVO.md only; no OpenAPI contract, batch file arrival, SLA, or observability artifacts.",
        "owner": "CMdS API",
        "priority": "P2",
    },
    {
        "id": "GAP-14",
        "topic": "Natural-key format and validation",
        "evidence": "No composite ingest key (e.g. medicaidCardId + serviceDate + providerId) documented in MEMBERELIGIBILITY.csv, .CPY, or MemberEligibilityVO.md.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-15",
        "topic": "Cross-field date ordering rules",
        "evidence": "T-MSIS data-elements.md documents period ordering for many date pairs; integration artifacts do not state which pairs apply at the MES→CMdS boundary.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-16",
        "topic": "Veterans indicator code normalization",
        "evidence": "T-MSIS Veteran Indicator List uses codes 0/1 (veteran-indicator.csv); VO veteransIndicator pattern [YN]? (MemberEligibilityVO.md:L448-L451). Mapping not stated in artifacts.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-17",
        "topic": "Level of care code width",
        "evidence": "Source LTC-LVL-CARE-CD PIC X(04) at 531-534 (MEMBERELIGIBILITY.csv:L45); VO levelOfCare @Size(max=2) (MemberEligibilityVO.md:L191-L193); T-MSIS ELG.005.088 is X(3). Truncation/padding rules not stated.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-18",
        "topic": "Marital status code width",
        "evidence": "Source MRTL-STAT-CD PIC X(04) at 1380-1383 (MEMBERELIGIBILITY.csv:L106); VO maritalStatus @Size(max=1) (MemberEligibilityVO.md:L444-L446); T-MSIS ELG.003.034 uses 2-character codes (marital-status.csv). Normalization not stated.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-19",
        "topic": "Disability type code list",
        "evidence": "MBR-DSBL-TYP present in layout (MEMBERELIGIBILITY.csv:L33) mapped to diabilityType (MemberEligibilityVO.md:L139); no CONFIRMED VVL CSV under rules/eligibility/value-lists/.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-20",
        "topic": "Health home level code list",
        "evidence": "HH-LVL-CD present in layout (MEMBERELIGIBILITY.csv:L42) mapped to healthHomeLevelCode (MemberEligibilityVO.md:L178); no CONFIRMED VVL CSV under rules/eligibility/value-lists/.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-21",
        "topic": "Part D opt-out indicator legal values",
        "evidence": "MCR-PTD-OPT-IND present in layout (MEMBERELIGIBILITY.csv:L65) mapped to partDOptOutIndex (MemberEligibilityVO.md:L273); Boolean/indicator legal values (Y/N, 1/0, blank) not stated in MEMBERELIGIBILITY.csv, .CPY, or VO.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-22",
        "topic": "Lock-in assignment reason code list",
        "evidence": "LCK-ASGN-RSN present in layout (MEMBERELIGIBILITY.csv:L98) mapped to lockinAssignmentReasonCode (MemberEligibilityVO.md:L409); no CONFIRMED VVL CSV under rules/eligibility/value-lists/.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-23",
        "topic": "Lock-in change reason code list",
        "evidence": "LCK-CHG-RSN present in layout (MEMBERELIGIBILITY.csv:L99) mapped to lockinChangeReasonCode (MemberEligibilityVO.md:L413); no CONFIRMED VVL CSV under rules/eligibility/value-lists/.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-24",
        "topic": "Immigrant admission status code list",
        "evidence": "IMM-ADMS-STAT present in layout (MEMBERELIGIBILITY.csv:L111) mapped to immigrantAdmissionStatus (MemberEligibilityVO.md:L464); no CONFIRMED VVL CSV under rules/eligibility/value-lists/.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-25",
        "topic": "Per-field nullability / mandatory rules",
        "evidence": "VO has sparse nullability comments (e.g. medicareIdNumber, healthHomeNPIId); T-MSIS Necessity in data-elements.md is not aligned field-by-field to MES layout or JSR-380 constraints in MemberEligibilityVO.md.",
        "owner": "MMIS SME",
        "priority": "P2",
    },
    {
        "id": "GAP-26",
        "topic": "Name / free-text character class",
        "evidence": "Name and address PIC X fields (e.g. MBR-LAST-NM, MBR-FRST-NM) have no allowed character class documented in MEMBERELIGIBILITY.csv, .CPY, or MemberEligibilityVO.md beyond @Size.",
        "owner": "MMIS SME",
        "priority": "P3",
    },
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_vvl_members() -> list[dict]:
    members: list[dict] = []
    for filename in VVL_FILES:
        path = VVL_DIR / filename
        with path.open(newline="", encoding="utf-8") as fh:
            rows_csv = list(csv.DictReader(fh))
        confirmed = [
            (idx, row)
            for idx, row in enumerate(rows_csv)
            if (row.get("status") or "").strip() == "CONFIRMED"
        ]
        if not confirmed:
            continue
        de = (confirmed[0][1].get("t_msis_data_element") or "").strip()
        members.append(
            {
                "de": de,
                "file": filename,
                "rows": [
                    {
                        "code": row["code"],
                        "description": row["description"],
                        "source_ref": f"{filename}:L{idx + 2}",
                    }
                    for idx, row in confirmed
                ],
            }
        )
    return members


def main() -> None:
    field_mappings: list[dict] = []
    with CSV_PATH.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for line_no, row in enumerate(reader, start=2):
            name = row["field_name"]
            if name not in MAPPING:
                raise KeyError(f"Missing MAPPING entry for {name!r}")
            target, vo_line, java_type, rule, vvl = MAPPING[name]
            entry: dict = {
                "source_field": name,
                "source_ref": f"MEMBERELIGIBILITY.csv:L{line_no}",
                "target_attribute": target,
                "target_ref": f"MemberEligibilityVO.md:L{vo_line}",
                "derivation": "INFERRED",
                "java_type": java_type,
                "picture": row["picture"],
                "start_pos": int(row["start_pos"]),
                "end_pos": int(row["end_pos"]),
                "length": int(row["length"]),
                "t_msis_rule": rule,
                "vvl_file": vvl,
            }
            field_mappings.append(entry)

    data = {
        "meta": {
            "flow": "Member Eligibility",
            "dictionary_version": "4.0.33",
            "sources": [
                {"path": "source/MEMBERELIGIBILITY.csv", "sha256": sha256_file(CSV_PATH)},
                {"path": "target/MemberEligibilityVO.md", "sha256": sha256_file(VO_PATH)},
                {
                    "path": "source/MEMBERELIGIBILITY.CPY",
                    "sha256": sha256_file(INTEGRATION_ROOT / "source/MEMBERELIGIBILITY.CPY"),
                },
            ],
        },
        "field_mappings": field_mappings,
        "gaps": GAPS,
        "assumptions": [],
        "vvl_members": load_vvl_members(),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, default_flow_style=False)

    print(f"Wrote {OUT_PATH} ({len(field_mappings)} field_mappings)")


if __name__ == "__main__":
    main()
