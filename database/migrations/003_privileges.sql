-- Re-applicable grants; application/frontend only sees curated API views.
GRANT USAGE ON SCHEMA api TO atlas_api, atlas_analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA api TO atlas_api, atlas_analytics;
ALTER DEFAULT PRIVILEGES FOR ROLE atlas_owner IN SCHEMA api GRANT SELECT ON TABLES TO atlas_api, atlas_analytics;

-- Collector / ETL: raw is append-only except ingestion run status.
GRANT USAGE ON SCHEMA raw, staging, core, quality TO atlas_ingest;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA raw TO atlas_ingest;
GRANT UPDATE (status, completed_at, details) ON raw.ingestion_runs TO atlas_ingest;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA staging, core, quality TO atlas_ingest;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA raw, staging, core, quality TO atlas_ingest;
ALTER DEFAULT PRIVILEGES FOR ROLE atlas_owner IN SCHEMA raw GRANT SELECT, INSERT ON TABLES TO atlas_ingest;
ALTER DEFAULT PRIVILEGES FOR ROLE atlas_owner IN SCHEMA staging, core, quality GRANT SELECT, INSERT, UPDATE ON TABLES TO atlas_ingest;
ALTER DEFAULT PRIVILEGES FOR ROLE atlas_owner IN SCHEMA raw, staging, core, quality GRANT USAGE, SELECT ON SEQUENCES TO atlas_ingest;

-- Analytics job can read canonical data but not raw personally identifying/internal payloads.
GRANT USAGE ON SCHEMA core, analytics TO atlas_analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA core TO atlas_analytics;
GRANT CREATE ON SCHEMA analytics TO atlas_analytics;
-- For controlled downstream consumption, publish analytics via api views (owner-created).
