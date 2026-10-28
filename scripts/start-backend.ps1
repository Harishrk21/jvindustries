# Start JV-OMS API on port 8080 (MySQL required)
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend"
if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    python -m venv .venv
    .\.venv\Scripts\python -m pip install -r requirements.txt
}
Write-Host "JV-OMS uses MySQL only. Ensure DATABASE_URL in .env points to jvoms."
Write-Host "Starting JV-OMS on http://0.0.0.0:8080 ..."
Write-Host "Open http://127.0.0.1:8080/health  and  http://127.0.0.1:8080/docs"
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
