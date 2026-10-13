param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Önce Python ile backend/.venv oluşturun ve backend/requirements.txt kurun. README adımlarını izleyin.'
}
Push-Location $repoRoot
try {
    docker compose up -d --wait postgres
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL başlatılamadı. Docker Desktop açık olmalı.' }
    Write-Host "Demo: http://127.0.0.1:$Port/docs"
    & $pythonPath -m uvicorn backend.main:app --host 127.0.0.1 --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'API başlatılamadı. Port kullanımını kontrol edin.' }
} finally {
    Pop-Location
}
