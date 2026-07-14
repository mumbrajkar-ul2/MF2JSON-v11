# Export the Member Eligibility integration spec to Microsoft Word (.docx).
# Markdown in spec/ remains the canonical source; re-run after every spec regeneration.
#
# Requires: Pandoc — winget install --id JohnMacFarlane.Pandoc

$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$md = Join-Path $here "spec\Integration_Spec_MES_to_CMdS_MemberEligibility.md"
$tool = Join-Path $here "..\..\medicare-validation-rules\tools\md_to_docx.py"

if (-not (Test-Path $md)) {
    Write-Error "Spec not found: $md"
}

python $tool $md
