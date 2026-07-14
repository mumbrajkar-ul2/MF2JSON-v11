public class Member_EligibilityVO {

    // ---- Interface / control ---------------------------------------------
    @JsonProperty("interfaceDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate interfaceDate;

    @JsonProperty("serviceDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMM")
    private YearMonth serviceDate;

    @JsonProperty("providerId")
    @Size(max = 12)
    private String providerId;

    @JsonProperty("planName")
    @Size(max = 30)
    private String planName;

    // ---- Member identifiers ----------------------------------------------
    @JsonProperty("medicaidCardId")
    @Size(max = 12)                       // Medicaid CIN / recipient id
    private String medicaidCardId;

    @JsonProperty("mciId")
    @Size(max = 12)                       // Master Client Index
    private String mciId;

    @JsonProperty("ssn")
    @Size(max = 9)
    @Pattern(regexp = "\\d{0,9}", message = "SSN must be up to 9 digits")
    private String ssn;

    @JsonProperty("medicareIdNumber")
    @Size(max = 11)                       // Medicare Beneficiary Identifier (MBI)
    private String medicareIdNumber;      // nullable in source

    // ---- Member name (X12 834 NM1) ---------------------------------------
    @JsonProperty("memberLastName")
    @Size(max = 35)
    private String memberLastName;

    @JsonProperty("memberFirstName")
    @Size(max = 25)
    private String memberFirstName;

    @JsonProperty("memberMiddleName")
    @Size(max = 25)
    private String memberMiddleName;

    // ---- Mailing address (X12 834 N3/N4) ---------------------------------
    @JsonProperty("mailingAdressLine1")
    @Size(max = 30)
    private String mailingAdressLine1;

    @JsonProperty("mailingAddressLine2")
    @Size(max = 30)
    private String mailingAddressLine2;

    @JsonProperty("mailingAddressCity")
    @Size(max = 30)
    private String mailingAddressCity;

    @JsonProperty("mailingState")
    @Size(max = 2)
    private String mailingState;

    @JsonProperty("mailingZip5")
    @Size(max = 5)
    @Pattern(regexp = "\\d{0,5}", message = "ZIP5 must be numeric")
    private String mailingZip5;

    @JsonProperty("mailingZip4")
    @Size(max = 4)
    @Pattern(regexp = "\\d{0,4}", message = "ZIP4 must be numeric")
    private String mailingZip4;

    // ---- Residence address -----------------------------------------------
    @JsonProperty("residenceAdressLine1")
    @Size(max = 30)
    private String residenceAdressLine1;

    @JsonProperty("residenceAddressLine2")
    @Size(max = 30)
    private String residenceAddressLine2;

    @JsonProperty("residenceAddressCity")
    @Size(max = 30)
    private String residenceAddressCity;

    @JsonProperty("residenceState")
    @Size(max = 2)
    private String residenceState;

    @JsonProperty("residenceZip5")
    @Size(max = 5)
    @Pattern(regexp = "\\d{0,5}")
    private String residenceZip5;

    @JsonProperty("residenceZip4")
    @Size(max = 4)
    @Pattern(regexp = "\\d{0,4}")
    private String residenceZip4;

    @JsonProperty("memberContactNumber")
    @Size(max = 10)                       // NANP phone, 10 digits
    private String memberContactNumber;

    @JsonProperty("geoCountyCode")
    @Size(max = 3)                        // FIPS county
    private String geoCountyCode;

    @JsonProperty("adminOfficeCode")
    @Size(max = 3)
    private String adminOfficeCode;

    // ---- Demographics ----------------------------------------------------
    @JsonProperty("dateOfBirth")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate dateOfBirth;

    @JsonProperty("dateOfDeath")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate dateOfDeath;

    @JsonProperty("gender")
    @Size(max = 1)
    @Pattern(regexp = "[MFU]?", message = "gender must be M, F or U")
    private String gender;

    @JsonProperty("race")
    @Size(max = 1)
    private String race;

    @JsonProperty("languageCode")
    @Size(max = 3)                        // ISO-639-2
    private String languageCode;

    @JsonProperty("diabilityType")
    @Size(max = 2)
    private String diabilityType;

    @JsonProperty("pregnancyDueDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate pregnancyDueDate;

    @JsonProperty("npiId")
    @Size(max = 10)                       // NPI is 10 digits
    @Pattern(regexp = "\\d{0,10}")
    private String npiId;

    // ---- Eligibility -----------------------------------------------------
    @JsonProperty("categoryOfEligibility")
    @Size(max = 2)
    private String categoryOfEligibility;

    @JsonProperty("eligibilityTerminationReasonCode")
    @Size(max = 3)
    private String eligibilityTerminationReasonCode;

    @JsonProperty("federalMatchCode")
    @Size(max = 2)
    private String federalMatchCode;

    // ---- Health Home -----------------------------------------------------
    @JsonProperty("healthHomeNPIId")
    @Size(max = 10)                       // NPI
    private String healthHomeNPIId;       // nullable in source

    @JsonProperty("healthHomeBeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate healthHomeBeginDate;

    @JsonProperty("healthHomeEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate healthHomeEndDate;

    @JsonProperty("healthHomeLevelCode")
    @Size(max = 1)
    private String healthHomeLevelCode;

    // ---- Long Term Care --------------------------------------------------
    @JsonProperty("ltcBeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate ltcBeginDate;

    @JsonProperty("ltcEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate ltcEndDate;

    @JsonProperty("levelOfCare")
    @Size(max = 2)
    private String levelOfCare;

    @JsonProperty("ltcPatientLiabilityCurrentBeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate ltcPatientLiabilityCurrentBeginDate;

    @JsonProperty("ltcPatientLiabilityCurrentEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate ltcPatientLiabilityCurrentEndDate;

    @JsonProperty("ltcPatientLiabilityCurrentAmount")
    @Digits(integer = 7, fraction = 2)
    private BigDecimal ltcPatientLiabilityCurrentAmount;

    @JsonProperty("ltcPatientLiabilityPreviousBeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate ltcPatientLiabilityPreviousBeginDate;

    @JsonProperty("ltcPatientLiabilityPreviousEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate ltcPatientLiabilityPreviousEndDate;

    @JsonProperty("ltcPatientLiabilityPreviousAmount")
    @Digits(integer = 7, fraction = 2)
    private BigDecimal ltcPatientLiabilityPreviousAmount;

    // ---- Disability ------------------------------------------------------
    @JsonProperty("disabilityBeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate disabilityBeginDate;

    @JsonProperty("disabilityEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate disabilityEndDate;

    // ---- Medicare Part A/B/C/D -------------------------------------------
    @JsonProperty("partABeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate partABeginDate;

    @JsonProperty("partAEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate partAEndDate;

    @JsonProperty("partBBeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate partBBeginDate;

    @JsonProperty("partBEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate partBEndDate;

    @JsonProperty("partCBeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate partCBeginDate;

    @JsonProperty("partCEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate partCEndDate;

    @JsonProperty("partCPBPContractId")
    @Size(max = 5)                        // Medicare contract id (H####/R####)
    private String partCPBPContractId;

    @JsonProperty("pbpOrganizationName")
    @Size(max = 30)
    private String pbpOrganizationName;

    @JsonProperty("partCPBPPlanName")
    @Size(max = 30)
    private String partCPBPPlanName;

    @JsonProperty("partDBeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate partDBeginDate;

    @JsonProperty("partDEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate partDEndDate;

    @JsonProperty("partDOptOutIndex")
    @Size(max = 1)
    private String partDOptOutIndex;

    @JsonProperty("partDPBPContractId")
    @Size(max = 5)                        // Medicare contract id (S####/H####)
    private String partDPBPContractId;

    @JsonProperty("partDPBPPlanID")
    @Size(max = 3)                        // PBP plan id (e.g. 001)
    private String partDPBPPlanID;

    // ---- Case Management contact -----------------------------------------
    @JsonProperty("caseMgmtName")
    @Size(max = 40)
    private String caseMgmtName;

    @JsonProperty("caseMgmtAdressLine1")
    @Size(max = 25)
    private String caseMgmtAdressLine1;

    @JsonProperty("caseMgmtAddressLine2")
    @Size(max = 25)
    private String caseMgmtAddressLine2;

    @JsonProperty("caseMgmtAddressCity")
    @Size(max = 20)
    private String caseMgmtAddressCity;

    @JsonProperty("caseMgmtState")
    @Size(max = 2)
    private String caseMgmtState;

    @JsonProperty("caseMgmtZip5")
    @Size(max = 5)
    private String caseMgmtZip5;

    @JsonProperty("caseMgmtZip4")
    @Size(max = 4)
    private String caseMgmtZip4;

    @JsonProperty("caseMgmtPhoneNum")
    @Size(max = 10)
    private String caseMgmtPhoneNum;

    // ---- Authorized Representative ---------------------------------------
    @JsonProperty("authRepLastName")
    @Size(max = 21)
    private String authRepLastName;

    @JsonProperty("authRepFirstName")
    @Size(max = 15)
    private String authRepFirstName;

    @JsonProperty("authRepMiddleName")
    @Size(max = 1)
    private String authRepMiddleName;

    @JsonProperty("authRepAdressLine1")
    @Size(max = 25)
    private String authRepAdressLine1;

    @JsonProperty("authRepAddressLine2")
    @Size(max = 25)
    private String authRepAddressLine2;

    @JsonProperty("authRepAddressCity")
    @Size(max = 20)
    private String authRepAddressCity;

    @JsonProperty("authRepState")
    @Size(max = 2)
    private String authRepState;

    @JsonProperty("authRepZip5")
    @Size(max = 5)
    private String authRepZip5;

    @JsonProperty("authRepZip4")
    @Size(max = 4)
    private String authRepZip4;

    @JsonProperty("authRepPhoneNum")
    @Size(max = 10)
    private String authRepPhoneNum;

    // ---- Payee -----------------------------------------------------------
    @JsonProperty("payeeLastName")
    @Size(max = 21)
    private String payeeLastName;

    @JsonProperty("payeeFirstName")
    @Size(max = 15)
    private String payeeFirstName;

    @JsonProperty("payeeMiddleName")
    @Size(max = 1)
    private String payeeMiddleName;

    @JsonProperty("payeeAdressLine1")
    @Size(max = 25)
    private String payeeAdressLine1;

    @JsonProperty("payeeAddressLine2")
    @Size(max = 25)
    private String payeeAddressLine2;

    @JsonProperty("payeeAddressCity")
    @Size(max = 20)
    private String payeeAddressCity;

    @JsonProperty("payeeState")
    @Size(max = 2)
    private String payeeState;

    @JsonProperty("payeeZip5")
    @Size(max = 5)
    private String payeeZip5;

    @JsonProperty("payeeZip4")
    @Size(max = 4)
    private String payeeZip4;

    @JsonProperty("payeePhoneNum")
    @Size(max = 10)
    private String payeePhoneNum;

    // ---- Lock-in ---------------------------------------------------------
    @JsonProperty("lockinBeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate lockinBeginDate;

    @JsonProperty("lockinEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate lockinEndDate;

    @JsonProperty("lockinAssignmentReasonCode")
    @Size(max = 2)
    private String lockinAssignmentReasonCode;

    @JsonProperty("lockinChangeReasonCode")
    @Size(max = 2)
    private String lockinChangeReasonCode;

    // ---- Rate amounts ----------------------------------------------------
    @JsonProperty("hplanRateAmount")
    @Digits(integer = 9, fraction = 2)
    private BigDecimal hplanRateAmount;

    @JsonProperty("totalRateAmount")
    @Digits(integer = 9, fraction = 2)
    private BigDecimal totalRateAmount;

    // ---- Transfer / facility / booking -----------------------------------
    @JsonProperty("transferPlanId")
    @Size(max = 8)
    private String transferPlanId;

    @JsonProperty("facilityId")
    @Size(max = 4)
    private String facilityId;

    @JsonProperty("bookingDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate bookingDate;

    @JsonProperty("releaseDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate releaseDate;

    // ---- Misc demographics -----------------------------------------------
    @JsonProperty("maritalStatus")
    @Size(max = 1)
    private String maritalStatus;

    @JsonProperty("veteransIndicator")
    @Size(max = 1)
    @Pattern(regexp = "[YN]?", message = "veteransIndicator must be Y or N")
    private String veteransIndicator;

    @JsonProperty("emailAddress")
    @Size(max = 50)
    private String emailAddress;

    @JsonProperty("primaryLanguageEnglishProficiencyCode")
    @Size(max = 1)
    private String primaryLanguageEnglishProficiencyCode;

    @JsonProperty("householdSize")
    private Integer householdSize;

    @JsonProperty("immigrantAdmissionStatus")
    @Size(max = 1)
    private String immigrantAdmissionStatus;

    @JsonProperty("mcEndDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate mcEndDate;

    @JsonProperty("mcBeginDate")
    @JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyyMMdd")
    private LocalDate mcBeginDate;

    @JsonProperty("fileName")
    @Size(max = 30)
    private String fileName;
}