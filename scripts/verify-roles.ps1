<#
.SYNOPSIS
  Day-0 role smoke - login owner / security / weighbridge / store and hit role hubs.
#>
param(
  [string]$BaseUrl = "http://127.0.0.1:8080",
  [hashtable]$Passwords = @{
    owner = "Owner@123"
    security = "Security@123"
    weighbridge = "Weigh@123"
    store = "Store@123"
  }
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

function Login([string]$UserId) {
  $pw = $Passwords[$UserId]
  if (-not $pw) { throw "No password configured for $UserId" }
  $body = '{"user_id":"' + $UserId + '","password":"' + $pw + '"}'
  $login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/auth/login" `
    -ContentType "application/json" -Body $body
  if (-not $login.access_token) { throw "no token" }
  return $login
}

Write-Output ("ROLES verify base={0}" -f $BaseUrl)

$owner = $null
Step "owner-login" {
  $script:owner = Login "owner"
  if ($script:owner.user.roles -notcontains "OWNER_ADMIN") { throw "missing OWNER_ADMIN" }
}
$ownerHeaders = @{ Authorization = ("Bearer {0}" -f $owner.access_token) }

Step "owner-dashboard" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/dashboard/summary" -Headers $ownerHeaders
}

Step "owner-users" {
  $users = Invoke-RestMethod -Uri "$BaseUrl/api/v1/users" -Headers $ownerHeaders
  $codes = @($users | ForEach-Object { $_.user_code })
  foreach ($need in @("owner", "security", "weighbridge", "store")) {
    if ($codes -notcontains $need) { throw "missing user $need" }
  }
}

$sec = $null
Step "security-login" {
  $script:sec = Login "security"
}
$secHeaders = @{ Authorization = ("Bearer {0}" -f $sec.access_token) }

Step "security-entry-start" {
  $body = '{"type":"OTHER_MOVEMENT","gps":{"lat":13.0827,"lon":80.2707,"accuracy_m":8}}'
  $r = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/vehicles/entry/start" `
    -Headers $secHeaders -ContentType "application/json" -Body $body
  if (-not $r.id) { throw "no txn" }
}

$wb = $null
Step "weighbridge-login" {
  $script:wb = Login "weighbridge"
}
$wbHeaders = @{ Authorization = ("Bearer {0}" -f $wb.access_token) }

Step "weighbridge-calibration" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/calibration/active" -Headers $wbHeaders
}

$st = $null
Step "store-login" {
  $script:st = Login "store"
}
$stHeaders = @{ Authorization = ("Bearer {0}" -f $st.access_token) }

Step "store-stock" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/stock/balances" -Headers $stHeaders
}

Step "health-seed-passwords-flag" {
  $h = Invoke-RestMethod "$BaseUrl/health"
  $codes = @($h.readiness | ForEach-Object { $_.code })
  if ($codes -notcontains "DEFAULT_SEED_PASSWORDS") {
    Write-Output "     NOTE: no DEFAULT_SEED_PASSWORDS flag (passwords already rotated or probe skipped)"
  } else {
    Write-Output "     readiness flags seed passwords - rotate via /change-password before production"
  }
}

if ($failed.Count -eq 0) {
  Write-Output "ROLES_OK"
  exit 0
}
Write-Output ("ROLES_FAIL ({0}): {1}" -f $failed.Count, ($failed -join ", "))
exit 1
