<#
.SYNOPSIS
  Live API smoke across JV-OMS phases (auth -> sync -> domain hubs).
.PARAMETER BaseUrl
  API root, e.g. http://127.0.0.1:8080
.PARAMETER UserId
  Login user (default owner)
.PARAMETER Password
  Login password
#>
param(
  [string]$BaseUrl = "http://127.0.0.1:8080",
  [string]$UserId = "owner",
  [string]$Password = "Owner@123"
)

$ErrorActionPreference = "Stop"
$failed = New-Object System.Collections.Generic.List[string]

function Step {
  param([string]$Name, [scriptblock]$Block)
  try {
    & $Block
    Write-Output "OK  $Name"
  } catch {
    [void]$failed.Add($Name)
    Write-Output ("FAIL {0} - {1}" -f $Name, $_.Exception.Message)
  }
}

Write-Output ("SMOKE base={0}" -f $BaseUrl)

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

Step "me" {
  $me = Invoke-RestMethod -Uri "$BaseUrl/api/v1/auth/me" -Headers $headers
  if (-not $me.user_code) { throw "no user" }
}

Step "dashboard" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/dashboard/summary" -Headers $headers
}

Step "geofence-check" {
  $body = '{"lat":13.0827,"lon":80.2707,"accuracy_m":8}'
  $null = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/geofence/check" `
    -Headers $headers -ContentType "application/json" -Body $body
}

Step "sync-policy" {
  $p = Invoke-RestMethod -Uri "$BaseUrl/api/v1/sync/policy" -Headers $headers
  if ($p.policy -notmatch "server_authoritative") { throw "unexpected policy" }
}

$cid = [guid]::NewGuid().ToString()
Step "sync-push" {
  $body = '{"drafts":[{"client_transaction_id":"' + $cid + '","type":"OTHER_MOVEMENT","notes":"smoke-live"}]}'
  $r = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sync/push" `
    -Headers $headers -ContentType "application/json" -Body $body
  if ($r.results[0].outcome -ne "CREATED") { throw "outcome=$($r.results[0].outcome)" }
}

Step "sync-idempotent" {
  $body = '{"drafts":[{"client_transaction_id":"' + $cid + '","type":"OTHER_MOVEMENT"}]}'
  $r = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/sync/push" `
    -Headers $headers -ContentType "application/json" -Body $body
  if ($r.results[0].outcome -ne "IDEMPOTENT") { throw "outcome=$($r.results[0].outcome)" }
}

Step "products" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/products" -Headers $headers
}

Step "storage-units" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/storage/units" -Headers $headers
}

Step "stock-balances" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/stock/balances" -Headers $headers
}

Step "equipment-list" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/equipment" -Headers $headers
}

Step "canteen-items" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/canteen/items" -Headers $headers
}

Step "reports-summary" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/reports/summary?period=daily" -Headers $headers
}

Step "notifications" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/notifications" -Headers $headers
}

Step "geofence-config" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/geofence/config" -Headers $headers
}

Step "users-seeded" {
  $users = Invoke-RestMethod -Uri "$BaseUrl/api/v1/users" -Headers $headers
  $codes = @($users | ForEach-Object { $_.user_code })
  if ($codes -notcontains "owner") { throw "owner missing" }
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

if ($failed.Count -eq 0) {
  Write-Output "SMOKE_OK"
  exit 0
}

Write-Output ("SMOKE_FAIL ({0}): {1}" -f $failed.Count, ($failed -join ", "))
exit 1
