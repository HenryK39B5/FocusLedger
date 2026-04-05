$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

# Ensure output directory exists
$audioDir = Join-Path $root "data\audio"
if (-not (Test-Path $audioDir)) {
    New-Item -ItemType Directory -Path $audioDir -Force | Out-Null
}

# Kill any process already using port 8010
$existing = Get-NetTCPConnection -LocalPort 8010 -ErrorAction SilentlyContinue
if ($existing) {
    $existing | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

$pythonPath = Join-Path $root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = "python"
}

Write-Host "Starting TTS worker (edge-tts / tencent optional)..."

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $pythonPath
$psi.Arguments = "-m uvicorn app:app --host 0.0.0.0 --port 8010"
$psi.WorkingDirectory = Join-Path $root "tools\tts-worker"
$psi.CreateNoWindow = $true
$psi.UseShellExecute = $false
$psi.EnvironmentVariables["TTS_OUTPUT_DIR"] = $audioDir
$psi.EnvironmentVariables["EDGE_TTS_VOICE"] = "zh-CN-XiaoxiaoNeural"
$psi.EnvironmentVariables["TTS_MAX_CONCURRENT_JOBS"] = "2"
$psi.EnvironmentVariables["TTS_DISABLE_PROXY"] = "false"

$proc = [System.Diagnostics.Process]::Start($psi)
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "TTS worker started (PID $($proc.Id))"
Write-Host "Health check: http://localhost:8010/health"
