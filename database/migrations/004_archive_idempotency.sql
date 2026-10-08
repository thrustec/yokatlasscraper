-- Supports safe replay of the same locally archived API response files.
ALTER TABLE raw.api_responses ADD COLUMN IF NOT EXISTS source_path TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS ux_api_response_identity
ON raw.api_responses (endpoint, coalesce(score_type, ''), coalesce(page_number, -1), source_hash_sha256)
WHERE source_hash_sha256 IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_source_records_hash ON raw.source_records(record_hash_sha256);
CREATE INDEX IF NOT EXISTS idx_program_version_year_score ON core.program_versions (yil, puan_turu);
