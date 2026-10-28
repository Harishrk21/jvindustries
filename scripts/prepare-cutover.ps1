<#
.SYNOPSIS
  Day-0 cutover helper - generate JWT secret, print checklist, run role smoke.
#>
param(
  [string]$BaseUrl = "http://127.0.0.1:8080",
  [switch]$SkipRoles
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Output "=== JV-OMS cutover prepare ==="
Write-Output ""
Write-Output "1) Generate a production JWT_SECRET (paste into host .env - never commit):"
$py = Join-Path $root "backend\.venv\Scripts\python.exe"
if (Test-Path $py) {
  $jwt = & $py -c "import secrets; print(secrets.token_hex(32))"
} else {
  $bytes = New-Object byte[] 32
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  $jwt = ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
}
Write-Output $jwt
Write-Output ""
Write-Output "2) Copy backend/.env.production.example to host .env and fill:"
Write-Output "   APP_ENV=production  DEBUG=false  JWT_SECRET=<above>"
Write-Output "   DATABASE_URL + MYSQL_SSL_*  CORS_ORIGINS  EVIDENCE_ROOT"
Write-Output "   WHATSAPP_* for live OTP (or accept mock only on staging)"
Write-Output ""
Write-Output "3) Owner sets real yard geofence in Settings (or PUT /api/v1/geofence/config)."
Write-Output "4) Each role changes seed password (forced on login when still default)."
Write-Output "   owner / security / weighbridge / store"
Write-Output "5) Build APK: cd web; npm run build; npx cap sync android; npx cap open android"
Write-Output "6) Verify:"
Write-Output "   .\scripts\smoke-live.ps1 -BaseUrl $BaseUrl"
Write-Output "   .\scripts\verify-phase-a.ps1"
Write-Output "   .\scripts\verify-phase-b.ps1"
Write-Output "   .\scripts\verify-roles.ps1"
Write-Output ""

if (-not $SkipRoles) {
  Write-Output "Running role smoke against $BaseUrl ..."
  & (Join-Path $PSScriptRoot "verify-roles.ps1") -BaseUrl $BaseUrl
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Output "CUTOVER_PREP_OK"
exit 0
