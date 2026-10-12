# Gated Integration Specification workflow orchestrator.
# Drives file checks, prompt emission, Python validators, and human approval gates.
# Does not invoke Cursor or modify medicare-validation-rules/rules/.
#
# Usage (run from PowerShell, not cmd.exe — or use run-integration-spec-workflow.cmd):
#   .\scripts\run-integration-spec-workflow.ps1
#   .\scripts\run-integration-spec-workflow.ps1 -LogFile workflow.log
#   .\scripts\run-integration-spec-workflow.ps1 -SmokeTest
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run-integration-spec-workflow.ps1 -SmokeTest

[CmdletBinding()]
param(
    [string] $ConfigPath,
    [string] $LogFile,
    [switch] $SmokeTest,
    [switch] $NonInteractive
)

$ErrorActionPreference = "Stop"

function Write-StageLog {
    param(
        [string] $StageId,
        [string] $Message,
        [ValidateSet("INFO", "PASS", "FAIL")]
        [string] $Level = "INFO"
    )
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$StageId] [$Level] $Message"
    switch ($Level) {
        "PASS" { Write-Host $line -ForegroundColor Green }
        "FAIL" { Write-Host $line -ForegroundColor Red }
        default { Write-Host $line }
    }
    if ($script:LogFilePath) {
        Add-Content -Path $script:LogFilePath -Value $line -Encoding UTF8
    }
}

function Invoke-PythonTool {
    param(
        [string] $ToolPath,
        [string[]] $Arguments
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & python $ToolPath @Arguments 2>&1
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if ($output) {
        $output | ForEach-Object { Write-Host $_ }
    }
    return $code
}

function Wait-ForFile {
    param(
        [string] $Path,
        [string] $Prompt
    )
    if (Test-Path $Path) {
        return
    }
    if ($NonInteractive) {
        throw "Required file not found (NonInteractive): $Path"
    }
    Write-Host ""
    Write-Host $Prompt -ForegroundColor Yellow
    Write-Host "Expected: $Path" -ForegroundColor DarkGray
    do {
        [void](Read-Host "Press Enter when the file exists (or Ctrl+C to abort)")
        if (-not (Test-Path $Path)) {
            Write-Host "File still missing. Try again or Ctrl+C to abort." -ForegroundColor Yellow
        }
    } while (-not (Test-Path $Path))
}

function Get-Approval {
    param([string] $ResearchPath)
    if ($NonInteractive) {
        throw "Human approval required but -NonInteractive was set."
    }
    Write-Host ""
    Write-Host "=== Stage 2 - Human review (HITL) ===" -ForegroundColor Cyan
    Write-Host "Review validated research YAML before Writer phase:"
    Write-Host "  $ResearchPath"
    Write-Host ""
    $answer = Read-Host "Approve research and proceed to Writer? (Y/n)"
    if ($answer -match '^(n|no)$') {
        return $false
    }
    return $true
}

function Invoke-SmokeTest {
    param(
        [string] $LibraryRoot
    )
    Write-StageLog -StageId "smoke" -Message "Running validator fixture smoke test"
    $validateResearch = Join-Path $LibraryRoot "tools\validate_research.py"
    $validateSpec = Join-Path $LibraryRoot "tools\validate_spec_against_research.py"
    $fixtures = Join-Path $LibraryRoot "tests\fixtures"

    $validYaml = Join-Path $fixtures "valid_research.yaml"
    $invalidYaml = Join-Path $fixtures "invalid_research.yaml"
    $minimalSpec = Join-Path $fixtures "minimal_spec.md"

    $code = Invoke-PythonTool -ToolPath $validateResearch -Arguments @($validYaml, "--skip-sha256")
    if ($code -ne 0) {
        Write-StageLog -StageId "smoke" -Message "valid_research.yaml should pass" -Level "FAIL"
        exit 1
    }
    Write-StageLog -StageId "smoke" -Message "valid_research.yaml passed" -Level "PASS"

    $code = Invoke-PythonTool -ToolPath $validateResearch -Arguments @($invalidYaml, "--skip-sha256")
    if ($code -eq 0) {
        Write-StageLog -StageId "smoke" -Message "invalid_research.yaml should fail" -Level "FAIL"
        exit 1
    }
    Write-StageLog -StageId "smoke" -Message "invalid_research.yaml failed as expected" -Level "PASS"

    $code = Invoke-PythonTool -ToolPath $validateSpec -Arguments @($validYaml, $minimalSpec)
    if ($code -ne 0) {
        Write-StageLog -StageId "smoke" -Message "minimal_spec.md should pass against valid_research.yaml" -Level "FAIL"
        exit 1
    }
    Write-StageLog -StageId "smoke" -Message "minimal_spec.md passed spec drift check" -Level "PASS"

    Write-StageLog -StageId "smoke" -Message "Smoke test complete" -Level "PASS"
    exit 0
}

# --- Resolve paths ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$IntegrationRoot = Split-Path -Parent $ScriptDir

if ($LogFile) {
    $script:LogFilePath = if ([System.IO.Path]::IsPathRooted($LogFile)) {
        $LogFile
    } else {
        Join-Path $IntegrationRoot $LogFile
    }
    New-Item -ItemType File -Path $script:LogFilePath -Force | Out-Null
}

if (-not $ConfigPath) {
    $ConfigPath = Join-Path $ScriptDir "workflow.config.json"
}
if (-not (Test-Path $ConfigPath)) {
    Write-Error "Config not found: $ConfigPath"
}
$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

$LibraryRoot = Resolve-Path (Join-Path $IntegrationRoot $config.libraryRelativePath)
$ResearchPath = Join-Path $IntegrationRoot $config.researchYaml
$SpecPath = Join-Path $IntegrationRoot $config.specMd
$SourceLayout = Join-Path $IntegrationRoot $config.sourceLayout
$TargetVO = Join-Path $IntegrationRoot $config.targetVO
$CpyToCsv = Join-Path $IntegrationRoot "tools\cpy_to_csv.py"
$GeneratedLayoutCsv = if ($config.PSObject.Properties.Name -contains "generatedLayoutCsv") {
    Join-Path $IntegrationRoot $config.generatedLayoutCsv
} else {
    $null
}

$ValidateResearch = Join-Path $LibraryRoot "tools\validate_research.py"
$ValidateSpec = Join-Path $LibraryRoot "tools\validate_spec_against_research.py"
$MdToDocx = Join-Path $LibraryRoot "tools\md_to_docx.py"
$Requirements = Join-Path $LibraryRoot "requirements.txt"

if ($SmokeTest) {
    Invoke-SmokeTest -LibraryRoot $LibraryRoot
}

Write-StageLog -StageId "0" -Message "Integration Spec workflow - $($config.flowName)"

# --- Stage 0: Setup ---
Write-StageLog -StageId "0" -Message "Checking workspace and dependencies"

foreach ($path in @($SourceLayout, $TargetVO)) {
    if (-not (Test-Path $path)) {
        Write-StageLog -StageId "0" -Message "Missing required input: $path" -Level "FAIL"
        exit 1
    }
}

$rulesMd = Join-Path $LibraryRoot (($config.validationRules -replace "/", "\"))
$vvlDir = Join-Path $LibraryRoot "rules\eligibility\value-lists"
if (-not (Test-Path $rulesMd)) {
    Write-StageLog -StageId "0" -Message "Library rules not found: $rulesMd" -Level "FAIL"
    exit 1
}
if (-not (Test-Path $vvlDir)) {
    Write-StageLog -StageId "0" -Message "Library value-lists not found: $vvlDir" -Level "FAIL"
    exit 1
}

foreach ($tool in @($ValidateResearch, $ValidateSpec, $MdToDocx)) {
    if (-not (Test-Path $tool)) {
        Write-StageLog -StageId "0" -Message "Missing validator tool: $tool" -Level "FAIL"
        exit 1
    }
}

try {
    $null = Get-Command python -ErrorAction Stop
} catch {
    Write-StageLog -StageId "0" -Message "Python not found on PATH" -Level "FAIL"
    exit 1
}

if (Test-Path $Requirements) {
    # pip writes notices to stderr; with $ErrorActionPreference=Stop, 2>&1 turns
    # those into terminating NativeCommandError even when exit code is 0.
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $pipOutput = & python -m pip install -r $Requirements -q 2>&1
        $pipCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if ($pipOutput) { $pipOutput | ForEach-Object { Write-Host $_ } }
    if ($pipCode -ne 0) {
        Write-StageLog -StageId "0" -Message "pip install -r requirements.txt failed" -Level "FAIL"
        exit 1
    }
}

if (-not (Test-Path $CpyToCsv)) {
    Write-StageLog -StageId "0" -Message "Missing layout converter: $CpyToCsv" -Level "FAIL"
    exit 1
}

# Pre-generate tabular layout from copybook when BA input is a .CPY
if ($SourceLayout -match '\.(CPY|cpy)$') {
    Write-StageLog -StageId "0" -Message "Generating layout CSV from copybook via cpy_to_csv.py"
    $convertArgs = @($SourceLayout)
    $goldenCsv = Join-Path $IntegrationRoot "source\MEMBERELIGIBILITY.csv"
    if (Test-Path $goldenCsv) {
        $convertArgs += @("--compare", $goldenCsv)
    }
    $code = Invoke-PythonTool -ToolPath $CpyToCsv -Arguments $convertArgs
    if ($code -ne 0) {
        Write-StageLog -StageId "0" -Message "cpy_to_csv.py failed (exit $code)" -Level "FAIL"
        exit $code
    }
    if ($GeneratedLayoutCsv -and -not (Test-Path $GeneratedLayoutCsv)) {
        Write-StageLog -StageId "0" -Message "Expected generated layout missing: $GeneratedLayoutCsv" -Level "FAIL"
        exit 1
    }
    Write-StageLog -StageId "0" -Message "Layout CSV generated" -Level "PASS"
}

Write-StageLog -StageId "0" -Message "Setup OK (library: $LibraryRoot)" -Level "PASS"

# --- Stage 1: Research prompt ---
Write-StageLog -StageId "1" -Message "Emit Turn 1 - Research prompt"
$researchPrompt = @(
    'Run Integration Spec Research per @prompts/integration-spec-research.md.'
    "- Flow: $($config.flowName)"
    ('- Source layout: @' + $config.sourceLayout)
    ('- Target VO: @' + $config.targetVO)
    ('- Validation rules: @' + $config.validationRules)
    ('- Value lists: @' + $config.valueLists.TrimEnd('/'))
    ""
    "Write $($config.researchYaml) only. Do not write the spec."
    ""
    'Optional: use Cursor Task (explore, readonly) inside this chat for large artifact scans only.'
) -join "`n"

Write-Host ""
Write-Host "========== TURN 1 - Paste into Cursor Chat 1 (Research) ==========" -ForegroundColor Cyan
Write-Host $researchPrompt
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host ""

Wait-ForFile -Path $ResearchPath -Prompt "Run Chat 1 (Research) in Cursor, then save the research YAML."

# --- Stage 1b: Validate research ---
Write-StageLog -StageId "1b" -Message "Validating research YAML"
$code = Invoke-PythonTool -ToolPath $ValidateResearch -Arguments @(
    $ResearchPath,
    "--integration-root",
    $IntegrationRoot
)
if ($code -ne 0) {
    Write-StageLog -StageId "1b" -Message "validate_research.py failed - fix YAML and re-run from Stage 1b" -Level "FAIL"
    exit 1
}
Write-StageLog -StageId "1b" -Message "Research YAML validated" -Level "PASS"

# --- Stage 2: Human approval ---
if (-not (Get-Approval -ResearchPath $ResearchPath)) {
    Write-StageLog -StageId "2" -Message "Research not approved - workflow stopped" -Level "FAIL"
    exit 1
}
Write-StageLog -StageId "2" -Message "Research approved" -Level "PASS"

# --- Stage 3: Writer prompt ---
Write-StageLog -StageId "3" -Message "Emit Turn 2 - Writer prompt (new chat required)"
$writerPrompt = @(
    'Write Integration Specification per @prompts/integration-spec-write.md from'
    ('@' + $config.researchYaml + ' only.')
    ""
    "Deliver $($config.specMd) and run tools/md_to_docx.py for .docx."
) -join "`n"

Write-Host ""
Write-Host "========== TURN 2 - NEW CURSOR CHAT (Writer) =====================" -ForegroundColor Magenta
Write-Host "IMPORTANT: Start a NEW chat. Do not continue the Research chat." -ForegroundColor Magenta
Write-Host $writerPrompt
Write-Host "====================================================================" -ForegroundColor Magenta
Write-Host ""

Wait-ForFile -Path $SpecPath -Prompt "Run Chat 2 (Writer) in a new Cursor chat, then save the spec Markdown."

# --- Stage 3b: Validate spec ---
Write-StageLog -StageId "3b" -Message "Validating spec against research"
$code = Invoke-PythonTool -ToolPath $ValidateSpec -Arguments @($ResearchPath, $SpecPath)
if ($code -ne 0) {
    Write-StageLog -StageId "3b" -Message "validate_spec_against_research.py failed" -Level "FAIL"
    exit 1
}
Write-StageLog -StageId "3b" -Message "Spec matches research" -Level "PASS"

# --- Stage 4: Word export ---
Write-StageLog -StageId "4" -Message "Exporting Word (.docx)"
$code = Invoke-PythonTool -ToolPath $MdToDocx -Arguments @($SpecPath)
if ($code -ne 0) {
    Write-StageLog -StageId "4" -Message "md_to_docx.py failed (is Pandoc installed?)" -Level "FAIL"
    Write-Host "Fallback: .\export-spec-docx.ps1" -ForegroundColor Yellow
    exit 1
}
$docxPath = [System.IO.Path]::ChangeExtension($SpecPath, ".docx")
Write-StageLog -StageId "4" -Message "Word export: $docxPath" -Level "PASS"

# --- Done ---
Write-Host ""
Write-StageLog -StageId "end" -Message "Workflow complete" -Level "PASS"
Write-Host "Deliverables:"
Write-Host "  Research: $ResearchPath"
Write-Host "  Spec MD:  $SpecPath"
Write-Host "  Spec DOCX: $docxPath"
