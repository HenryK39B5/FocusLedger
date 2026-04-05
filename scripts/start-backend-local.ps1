$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$logs = Join-Path $root "logs"

New-Item -ItemType Directory -Path $logs -Force | Out-Null

$stdout = Join-Path $logs "backend.log"
$stderr = Join-Path $logs "backend.err.log"

$process = Start-Process `
  -FilePath (Join-Path $backend ".venv\\Scripts\\python.exe") `
  -ArgumentList "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8100" `
  -WorkingDirectory $backend `
  -RedirectStandardOutput $stdout `
  -RedirectStandardError $stderr `
  -PassThru

Write-Output ("Backend started on http://127.0.0.1:8100 with PID {0}" -f $process.Id)
