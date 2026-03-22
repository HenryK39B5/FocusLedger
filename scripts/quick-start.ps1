$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

docker compose up -d --build postgres redis backend frontend

Write-Host ""
Write-Host "FocusLedger is starting."
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://localhost:8000"
Write-Host "Health:   http://localhost:8000/api/v1/health"
