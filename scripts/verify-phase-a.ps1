<#
.SYNOPSIS
  Go-Live Phase A verification — API smoke + geofence + users + PDFs + readiness tests.
#>
param(
  [string]$BaseUrl = "http://127.0.0.1:8080",
  [string]$UserId = "owner",
  [string]$Password = "Owner@123"
)

$ErrorActionPreference = "Stop"
$failed = New-Object System.Collections.Generic.List[string]

function Step([string]$Name, [scriptblock]$Block) {
  try {
    & $Block
    Write-Output ("OK  {0}" -f $Name)
  } catch {
    [void]$failed.Add($Name)
    Write-Output ("FAIL {0} - {1}" -f $Name, $_.Exception.Message)
  }
}

Write-Output ("PHASE_A verify base={0}" -f $BaseUrl)

Step "health" {
  $h = Invoke-RestMethod "$BaseUrl/health"
  if ($h.status -ne "ok") { throw "status=$($h.status)" }
}

$login = $null
Step "login" {
  $body = '{"user_id":"' + $UserId + '","password":"' + $Password + '"}'
  $script:login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/auth/login" `
    -ContentType "application/json" -Body $body
  if (-not $script:login.access_token) { throw "no token" }
}

$headers = @{ Authorization = ("Bearer {0}" -f $login.access_token) }

Step "dashboard" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/dashboard/summary" -Headers $headers
}

Step "geofence-config-get" {
  $c = Invoke-RestMethod -Uri "$BaseUrl/api/v1/geofence/config" -Headers $headers
  if ($null -eq $c.lat) { throw "missing lat" }
}

Step "geofence-config-put" {
  $body = '{"lat":13.0827,"lon":80.2707,"radius_m":300,"max_accuracy_m":50}'
  $c = Invoke-RestMethod -Method Put -Uri "$BaseUrl/api/v1/geofence/config" `
    -Headers $headers -ContentType "application/json" -Body $body
  if ($c.source -ne "database") { throw "expected database source" }
}

Step "geofence-check-inside" {
  $body = '{"lat":13.0827,"lon":80.2707,"accuracy_m":8}'
  $r = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/geofence/check" `
    -Headers $headers -ContentType "application/json" -Body $body
  if (-not $r.authorized) { throw $r.message }
}

Step "users-roles" {
  $roles = Invoke-RestMethod -Uri "$BaseUrl/api/v1/users/roles" -Headers $headers
  if ($roles -notcontains "SECURITY") { throw "SECURITY role missing" }
}

Step "users-list" {
  $users = Invoke-RestMethod -Uri "$BaseUrl/api/v1/users" -Headers $headers
  $codes = @($users | ForEach-Object { $_.user_code })
  foreach ($need in @("owner", "security", "weighbridge", "store")) {
    if ($codes -notcontains $need) { throw "missing user $need" }
  }
}

Step "products-storage" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/products" -Headers $headers
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/storage/units" -Headers $headers
}

$cid = [guid]::NewGuid().ToString()
$txnPk = $null
Step "sync-create" {
  $body = '{"drafts":[{"client_transaction_id":"' + $cid + '","type":"OTHER_MOVEMENT","notes":"phase-a"}]}'
  $r = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sync/push" `
    -Headers $headers -ContentType "application/json" -Body $body
  if ($r.results[0].outcome -ne "CREATED") { throw $r.results[0].outcome }
  $script:txnPk = $r.results[0].transaction_pk
}

Step "pdf-customer" {
  $resp = Invoke-WebRequest -Uri "$BaseUrl/api/v1/pdfs/transaction/$txnPk`?variant=customer" `
    -Headers $headers -UseBasicParsing
  if ($resp.StatusCode -ne 200) { throw "status $($resp.StatusCode)" }
  if ($resp.RawContentLength -lt 100) { throw "pdf too small" }
}

Step "pdf-internal" {
  $resp = Invoke-WebRequest -Uri "$BaseUrl/api/v1/pdfs/transaction/$txnPk`?variant=internal" `
    -Headers $headers -UseBasicParsing
  if ($resp.StatusCode -ne 200) { throw "status $($resp.StatusCode)" }
}

Step "sync-policy" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/sync/policy" -Headers $headers
}

Step "unauth-401" {
  try {
    Invoke-WebRequest -Uri "$BaseUrl/api/v1/dashboard/summary" -UseBasicParsing | Out-Null
    throw "expected 401"
  } catch {
    $code = $_.Exception.Response.StatusCode.value__
    if ($code -ne 401) { throw "got $code" }
  }
}

# Unit readiness (no MySQL required)
$backend = Join-Path $PSScriptRoot "..\backend"
Step "pytest-readiness" {
  Push-Location $backend
  try {
    & .\.venv\Scripts\python.exe -m pytest tests/test_production_readiness.py tests/test_sync_policy.py -q --tb=line
    if ($LASTEXITCODE -ne 0) { throw "pytest exit $LASTEXITCODE" }
  } finally {
    Pop-Location
  }
}

Step "evidence-dir" {
  $root = Join-Path $backend "evidence_store"
  if (-not (Test-Path $root)) {
    New-Item -ItemType Directory -Force -Path $root | Out-Null
  }
  $probe = Join-Path $root ".phase_a_write_probe"
  Set-Content -Path $probe -Value "ok" -Encoding utf8
  if (-not (Test-Path $probe)) { throw "cannot write evidence_store" }
  Remove-Item $probe -Force
}

if ($failed.Count -eq 0) {
  Write-Output "PHASE_A_OK"
  exit 0
}

Write-Output ("PHASE_A_FAIL ({0}): {1}" -f $failed.Count, ($failed -join ", "))
exit 1
