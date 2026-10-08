$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$envFile = Join-Path $root '.env'
if (Test-Path $envFile) {
    Write-Host '.env already exists; leaving passwords unchanged.' -ForegroundColor Yellow
    exit 0
}
function New-Secret {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}
$data = @(
    'POSTGRES_PORT=5433'
    ('POSTGRES_ADMIN_PASSWORD=' + (New-Secret))
    ('ATLAS_INGEST_PASSWORD=' + (New-Secret))
    ('ATLAS_API_PASSWORD=' + (New-Secret))
    ('ATLAS_ANALYTICS_PASSWORD=' + (New-Secret))
) -join "`n"
[System.IO.File]::WriteAllText($envFile, $data + "`n", (New-Object System.Text.UTF8Encoding($false)))
Write-Host 'Created .env with four cryptographically random local development passwords.' -ForegroundColor Green
Write-Host "Path: $envFile"
Write-Host 'WARNING: Do not commit .env; environment passwords are only applied on first DB initialization.'
