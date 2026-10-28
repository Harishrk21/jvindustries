# Start JV-OMS Vite PWA on port 5173
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\web"
if (-not (Test-Path .\node_modules)) {
  npm install
}
Write-Host "Starting web on http://127.0.0.1:5173 ..."
Write-Host "API should already be on http://127.0.0.1:8080"
npm run dev -- --host 127.0.0.1 --port 5173
