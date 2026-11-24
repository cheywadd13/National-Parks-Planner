# Run after installing requirements. Secrets stay outside version control.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskParentConnection = Join-Path (Split-Path -Parent $PSScriptRoot) 'SupabaseStringWeek5.txt'
if (-not $env:DATABASE_URL -and (Test-Path -LiteralPath $taskParentConnection)) {
    $env:DATABASE_URL = [System.IO.File]::ReadAllText($taskParentConnection).Trim()
}
if ($env:DATABASE_URL) {
    Remove-Item Env:PARKS_CSV_DIR -ErrorAction SilentlyContinue
}
$taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $taskPython) {
    & $taskPython -m streamlit run app.py
} else {
    python -m streamlit run app.py
}
