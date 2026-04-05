$ErrorActionPreference = "Stop"

$ports = 3300, 8100
$connections = Get-NetTCPConnection -LocalPort $ports -State Listen -ErrorAction SilentlyContinue

if (-not $connections) {
  Write-Output "No local FocusLedger_zip_20260404 services are listening on ports 3300 or 8100."
  exit 0
}

$processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($processId in $processIds) {
  try {
    Stop-Process -Id $processId -Force -ErrorAction Stop
    Write-Output ("Stopped process {0}" -f $processId)
  } catch {
    Write-Warning ("Failed to stop process {0}: {1}" -f $processId, $_.Exception.Message)
  }
}
