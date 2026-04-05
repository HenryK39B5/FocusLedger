$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"
$logs = Join-Path $root "logs"
$envFile = Join-Path $root ".env"
$nextCache = Join-Path $frontend ".next"
$apiBaseUrl = "http://127.0.0.1:8100"

if (Test-Path -LiteralPath $envFile) {
  foreach ($line in Get-Content -LiteralPath $envFile) {
    if ($line -match '^\s*NEXT_PUBLIC_API_BASE_URL\s*=\s*(.+?)\s*$') {
      $apiBaseUrl = $matches[1].Trim().Trim('"')
      break
    }
  }
}

New-Item -ItemType Directory -Path $logs -Force | Out-Null

if (Test-Path -LiteralPath $nextCache) {
  Remove-Item -LiteralPath $nextCache -Recurse -Force
}

$stdout = Join-Path $logs "frontend.log"
$stderr = Join-Path $logs "frontend.err.log"
$command = "set NEXT_PUBLIC_API_BASE_URL=$apiBaseUrl&& npm run dev:3300"

$process = Start-Process `
  -FilePath "cmd.exe" `
  -ArgumentList "/c", $command `
  -WorkingDirectory $frontend `
  -RedirectStandardOutput $stdout `
  -RedirectStandardError $stderr `
  -PassThru

Write-Output ("Frontend started on http://127.0.0.1:3300 with PID {0}" -f $process.Id)
