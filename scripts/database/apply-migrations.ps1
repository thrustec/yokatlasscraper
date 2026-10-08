$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $root
try {
    foreach ($migration in @('001_data_contract_v1.sql','002_api_views.sql','003_privileges.sql','004_archive_idempotency.sql')) {
        Write-Host "Applying $migration ..."
        docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U atlas_owner -d yokatlas_intelligence -f "/opt/atlas/migrations/$migration"
        if ($LASTEXITCODE -ne 0) { throw "Migration failed: $migration" }
    }
    Write-Host 'Idempotent migrations applied.' -ForegroundColor Green
} finally { Pop-Location }
