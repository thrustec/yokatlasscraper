$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $root
try {
    docker compose ps
    if ($LASTEXITCODE -ne 0) { throw 'docker compose ps failed' }
    docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U atlas_owner -d yokatlas_intelligence -f /opt/atlas/checks/smoke.sql
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL smoke check failed' }
    Write-Host 'Smoke check completed.' -ForegroundColor Green
} finally { Pop-Location }
