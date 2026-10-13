# Existing repository/database baseline

**Checked:** 13 October 2026. **Evidence:** private repository `thrustec/yokatlas-intelligence`, default branch `main`; `current_schema.sql`, `database/migrations/001_data_contract_v1.sql`, and `docs/SCRAPER_POSTGRES_INTEGRATION_GUIDE.md`.

## What exists in the repo snapshot

- PostgreSQL 17 schema dump with `raw`, `staging`, `core`, `quality`, `analytics`, and `api` schemas.
- Existing YÖK ingestion uses `raw.api_responses`, `raw.ingestion_runs`, and `raw.source_records`. `api_responses` stores JSONB and a source hash.
- Core identity references include `core.universities.universite_id`, `core.cities.il_kodu`, program groups keyed by `(birim_grup_id, puan_turu)`, and program versions with natural uniqueness `(kilavuz_kodu, yil)`.
- The existing response uniqueness expression uses endpoint, score type, page number, and response hash; it is not a general external-source identity including source, request parameters, or run.
- JSONB is not byte-preserving for original CSV/XLSX/PDF/HTML payloads.

## Limits of this baseline

This was a repository artifact review, not a live connection to PostgreSQL. No live `pg_catalog`/DDL or permissions check was possible from the current workspace. The repo snapshot is the only verified schema evidence and may have drifted from the running DB. Before migration work, compare it with a fresh live DDL export and inspect current grants.

## Compatibility conclusion

External source RAW tables should be source-oriented and retain source-local IDs and observed codes. Do not treat a university-name match, city-name match, OpenAlex/ROR identity, or YÖK ID prefix heuristic as a confirmed FK. Keep candidate crosswalks separate until evidence and owner/data-engineering review exist.

The contract calls for immutable source capture with source URL, request parameters, release/version, retrieval timestamp, content type, HTTP status, byte hash, storage path, and parser version. The current inspected schema does not demonstrate a generic byte-exact artifact store. Design that storage before claiming that original binary artifacts are archived.

No schema was changed in this phase.
