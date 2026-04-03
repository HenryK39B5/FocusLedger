$ErrorActionPreference = "Stop"

Write-Host "Stopping TTS worker..."

$existing = Get-NetTCPConnection -LocalPort 8010 -ErrorAction SilentlyContinue
if ($existing) {
    $processIds = $existing.OwningProcess | Sort-Object -Unique
    if ($processIds) {
        foreach ($processId in $processIds) {
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
        Write-Host "TTS worker stopped."
    } else {
        Write-Host "No process found on port 8010."
    }
} else {
    Write-Host "TTS worker is not running."
}
