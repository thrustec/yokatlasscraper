#!/bin/bash
set -Eeuo pipefail

# Official postgres entrypoint invokes this only when the data directory is new.
# A single psql transaction makes roles/schema/views/grants atomic.
psql -X -1 -v ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v ingest_password="$ATLAS_INGEST_PASSWORD" \
  -v api_password="$ATLAS_API_PASSWORD" \
  -v analytics_password="$ATLAS_ANALYTICS_PASSWORD" \
  -f /opt/atlas/migrations/000_roles.sql \
  -f /opt/atlas/migrations/001_data_contract_v1.sql \
  -f /opt/atlas/migrations/002_api_views.sql \
  -f /opt/atlas/migrations/003_privileges.sql \
  -f /opt/atlas/migrations/004_archive_idempotency.sql \
  -f /opt/atlas/migrations/005_bot_condition_sync.sql \
  -f /opt/atlas/migrations/006_tuik_population_by_province.sql \
  -f /opt/atlas/migrations/007_sege_urap_reports.sql \
  -f /opt/atlas/checks/smoke.sql
