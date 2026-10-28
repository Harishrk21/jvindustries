# Creates JV-OMS MySQL database + app user.
# Usage: .\scripts\setup-mysql.ps1 -RootPassword "YOUR_ROOT_PASSWORD"
param(
    [Parameter(Mandatory = $true)]
    [string]$RootPassword,
    [string]$MysqlExe = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
)

$ErrorActionPreference = "Stop"
$sqlFile = Join-Path $PSScriptRoot "..\database\setup_mysql.sql"
if (-not (Test-Path $MysqlExe)) {
    throw "mysql.exe not found at $MysqlExe"
}
Write-Host "Creating database jvoms and user jvoms ..."
& $MysqlExe -u root "-p$RootPassword" --default-character-set=utf8mb4 -e "source $($sqlFile -replace '\\','/')"
if ($LASTEXITCODE -ne 0) {
    # fallback pipe
    Get-Content $sqlFile -Raw | & $MysqlExe -u root "-p$RootPassword" --default-character-set=utf8mb4
}
Write-Host "Done. App connection string:"
Write-Host "mysql+pymysql://jvoms:JvOms%402026@127.0.0.1:3306/jvoms?charset=utf8mb4"
