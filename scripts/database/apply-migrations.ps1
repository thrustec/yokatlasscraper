$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Push-Location $root
try {
    foreach ($migration in @('001_data_contract_v1.sql','002_api_views.sql','003_privileges.sql','004_archive_idempotency.sql','005_bot_condition_sync.sql','006_tuik_population_by_province.sql','007_sege_urap_reports.sql')) {
        Write-Host "Applying $migration ..."
        docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U atlas_owner -d yokatlas_intelligence -f "/opt/atlas/migrations/$migration"
        if ($LASTEXITCODE -ne 0) { throw "Migration failed: $migration" }
    }
    Write-Host 'Idempotent migrations applied.' -ForegroundColor Green
} finally { Pop-Location }
