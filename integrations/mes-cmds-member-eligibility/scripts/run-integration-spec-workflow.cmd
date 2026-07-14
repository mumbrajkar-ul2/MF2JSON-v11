@echo off
REM Launches the PowerShell orchestrator (use this from cmd.exe or when .ps1 opens in Notepad).
setlocal
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run-integration-spec-workflow.ps1" %*
exit /b %ERRORLEVEL%
