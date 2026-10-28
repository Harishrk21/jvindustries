<#
.SYNOPSIS
  Go-Live Phase B - evidence writable + WhatsApp OTP/alert path (mock OK in development).
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
    Write-Output ("OK  {0}" -f $Name)
  } catch {
    [void]$failed.Add($Name)
    Write-Output ("FAIL {0} - {1}" -f $Name, $_.Exception.Message)
  }
}

Write-Output ("PHASE_B verify base={0}" -f $BaseUrl)

$health = $null
Step "health-evidence-whatsapp" {
  $script:health = Invoke-RestMethod "$BaseUrl/health"
  if (-not $script:health.evidence.writable) { throw "evidence not writable" }
  if (-not $script:health.whatsapp.provider) { throw "whatsapp provider missing" }
  Write-Output ("     whatsapp={0} live={1}" -f $script:health.whatsapp.provider, $script:health.whatsapp.live)
  Write-Output ("     evidence={0}" -f $script:health.evidence.root)
}

$login = $null
Step "login" {
  $body = '{"user_id":"' + $UserId + '","password":"' + $Password + '"}'
  $script:login = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/auth/login" `
    -ContentType "application/json" -Body $body
  if (-not $script:login.access_token) { throw "no token" }
}
$headers = @{ Authorization = ("Bearer {0}" -f $login.access_token) }

$txnPk = $null
Step "vehicle-entry-start" {
  $body = '{"type":"MATERIAL_LOADING_OUTWARD","gps":{"lat":13.0827,"lon":80.2707,"accuracy_m":8}}'
  $r = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/vehicles/entry/start" `
    -Headers $headers -ContentType "application/json" -Body $body
  if (-not $r.id) { throw "no txn id" }
  $script:txnPk = $r.id
}

$otpId = $null
$otpPreview = $null
Step "otp-send" {
  $body = '{"transaction_pk":"' + $txnPk + '","customer_mobile":"9876543210","customer_name":"Phase B Test","gps":{"lat":13.0827,"lon":80.2707,"accuracy_m":8}}'
  $r = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/otp/send" `
    -Headers $headers -ContentType "application/json" -Body $body
  if ($r.status -ne "SENT") { throw ("status={0}" -f $r.status) }
  if (-not $r.otp_id) { throw "no otp_id" }
  $script:otpId = $r.otp_id
  $script:otpPreview = $r.otp_preview
  if ($health.whatsapp.provider -eq "mock_whatsapp" -and -not $r.otp_preview) {
    throw "mock mode must return otp_preview for yard verification"
  }
}

Step "otp-verify" {
  if (-not $otpPreview) { throw "no preview code (official WhatsApp requires manual verify)" }
  $body = '{"transaction_pk":"' + $txnPk + '","otp_id":"' + $otpId + '","otp_code":"' + $otpPreview + '","gps":{"lat":13.0827,"lon":80.2707,"accuracy_m":8}}'
  $r = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/otp/verify" `
    -Headers $headers -ContentType "application/json" -Body $body
  if (-not $r.verified) { throw ("verified=false status={0}" -f $r.otp_status) }
}

Step "management-alert" {
  $body = '{"title":"Phase B","body":"Go-live alert smoke","severity":"WARN","send_whatsapp":true}'
  $r = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/notifications/alert" `
    -Headers $headers -ContentType "application/json" -Body $body
  if (-not $r.id) { throw "no notification id" }
}

Step "whatsapp-log" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/whatsapp/messages" -Headers $headers
}

Step "notifications-list" {
  $null = Invoke-RestMethod -Uri "$BaseUrl/api/v1/notifications" -Headers $headers
}

if ($failed.Count -eq 0) {
  Write-Output "PHASE_B_OK"
  if ($health.whatsapp.provider -eq "mock_whatsapp") {
    Write-Output "NOTE: WhatsApp is MOCK - set Meta credentials before production day-1 OTP."
  }
  exit 0
}

Write-Output ("PHASE_B_FAIL ({0}): {1}" -f $failed.Count, ($failed -join ", "))
exit 1
