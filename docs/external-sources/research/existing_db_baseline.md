# Existing repository/database baseline

**Checked:** 13 October 2026. **Evidence:** private repository `thrustec/yokatlas-intelligence`, default branch `main`; `current_schema.sql` (PostgreSQL 17.11), `database/migrations/001_data_contract_v1.sql`, `docs/SCRAPER_POSTGRES_INTEGRATION_GUIDE.md`, `docs/YOKATLAS_DATABASE_REFERENCE.md`, and `docs/database/data_contract_v1.json`.

## What exists in the repo snapshot

- PostgreSQL 17 schema dump with `raw`, `staging`, `core`, `quality`, `analytics`, and `api` schemas.
- Existing YÖK ingestion uses `raw.api_responses`, `raw.ingestion_runs`, and `raw.source_records`. `api_responses` stores JSONB and a source hash.
- Core identity references include `core.universities.universite_id`, `core.cities.il_kodu`, program groups keyed by `(birim_grup_id, puan_turu)`, and program versions with natural uniqueness `(kilavuz_kodu, yil)`.
- The existing response uniqueness expression uses endpoint, score type, page number, and response hash; it is not a general external-source identity including source, request parameters, or run.
- JSONB is not byte-preserving for original CSV/XLSX/PDF/HTML payloads.
- Existing YÖK ingestion contract covers five discovered endpoint/entity families and historical collection counts. It instructs the scraper to write only to `raw.*`; it does not claim full endpoint discovery.

## Live database availability check

At 2026-10-13T16:26Z, the current workspace had no `psql` executable, TCP connection to `127.0.0.1:5433` failed, and Docker could not connect to the Docker Desktop Linux engine named pipe. Therefore no live `pg_catalog`, current grants, or running migrations could be inspected. The checked-in dump and guides are the only verified schema evidence; they may have drifted from the current DB.

Before migration work, restore/connect the intended development database and compare a fresh live DDL export and current grants against the repo snapshot. Do not infer that the database is absent or that the checked-in dump is current solely from this failed local connection attempt.

## Compatibility conclusion

External source RAW tables should be source-oriented and retain source-local IDs and observed codes. Do not treat a university-name match, city-name match, OpenAlex/ROR identity, or YÖK ID prefix heuristic as a confirmed FK. Keep candidate crosswalks separate until evidence and owner/data-engineering review exist.

The contract calls for immutable source capture with source URL, request parameters, release/version, retrieval timestamp, content type, HTTP status, byte hash, storage path, and parser version. The current inspected schema does not demonstrate a generic byte-exact artifact store. Design that storage before claiming that original binary artifacts are archived.

No schema was changed in this phase.
