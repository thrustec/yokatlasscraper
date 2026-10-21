-- Original PDF files live in the archive; immutable extraction and receipts live in RAW.
CREATE TABLE IF NOT EXISTS raw.report_documents (
    document_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingestion_run_id BIGINT NOT NULL REFERENCES raw.ingestion_runs(ingestion_run_id),
    report_id TEXT NOT NULL,
    source_system TEXT NOT NULL CHECK (source_system IN ('sege', 'urap')),
    edition TEXT NOT NULL,
    source_url TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL,
    source_sha256 TEXT NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    parser_version TEXT NOT NULL,
    extracted_sha256 TEXT NOT NULL CHECK (extracted_sha256 ~ '^[0-9a-f]{64}$'),
    archive_path TEXT NOT NULL,
    payload JSONB NOT NULL,
    UNIQUE (report_id, source_sha256, parser_version),
    UNIQUE (document_id, report_id)
);

CREATE TABLE IF NOT EXISTS staging.sege_results (
    document_id BIGINT NOT NULL REFERENCES raw.report_documents(document_id),
    entity_key TEXT NOT NULL,
    yerlesim_duzeyi TEXT NOT NULL CHECK (yerlesim_duzeyi IN ('il', 'ilce', 'bolge')),
    yerlesim_adi TEXT NOT NULL,
    il_adi TEXT,
    il_kodu BIGINT REFERENCES core.cities(il_kodu),
    bolge_kodu TEXT,
    sira INTEGER NOT NULL CHECK (sira > 0),
    skor NUMERIC(12,3) NOT NULL,
    kademe INTEGER NOT NULL CHECK (kademe BETWEEN 1 AND 6),
    il_ici_sira INTEGER CHECK (il_ici_sira > 0),
    alt_boyut_siralari JSONB NOT NULL DEFAULT '{}'::jsonb,
    bolge_illeri JSONB NOT NULL DEFAULT '[]'::jsonb,
    source_page INTEGER NOT NULL CHECK (source_page > 0),
    source_table TEXT NOT NULL,
    PRIMARY KEY (document_id, yerlesim_duzeyi, entity_key),
    UNIQUE (document_id, yerlesim_duzeyi, sira),
    CHECK (yerlesim_duzeyi <> 'bolge' OR kademe <= 4)
);

CREATE TABLE IF NOT EXISTS staging.urap_rankings (
    document_id BIGINT NOT NULL REFERENCES raw.report_documents(document_id),
    source_key TEXT NOT NULL,
    universite_adi TEXT NOT NULL,
    universite_id BIGINT REFERENCES core.universities(universite_id),
    il_adi TEXT NOT NULL,
    il_kodu BIGINT REFERENCES core.cities(il_kodu),
    sira INTEGER NOT NULL CHECK (sira > 0),
    toplam_puan NUMERIC(12,2) NOT NULL CHECK (toplam_puan >= 0),
    puanlar JSONB NOT NULL,
    source_page INTEGER NOT NULL CHECK (source_page > 0),
    source_table TEXT NOT NULL,
    PRIMARY KEY (document_id, source_key),
    UNIQUE (document_id, sira)
);

-- One pointer switches a complete report revision into the public views atomically.
CREATE TABLE IF NOT EXISTS staging.report_publications (
    report_id TEXT PRIMARY KEY,
    document_id BIGINT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (document_id, report_id) REFERENCES raw.report_documents(document_id, report_id)
);

CREATE OR REPLACE VIEW api.report_publications AS
SELECT d.report_id, d.source_system, d.edition, d.source_url,
       d.source_sha256, d.parser_version, d.captured_at, p.published_at,
       d.payload->'counts' AS counts
FROM staging.report_publications p JOIN raw.report_documents d USING (document_id, report_id);

CREATE OR REPLACE VIEW api.sege_results AS
SELECT r.yerlesim_duzeyi, r.yerlesim_adi, r.il_adi, r.il_kodu, r.bolge_kodu,
       r.sira, r.skor, r.kademe, r.il_ici_sira, r.alt_boyut_siralari, r.bolge_illeri,
       CASE WHEN d.source_system='sege' THEN d.edition::integer END AS yil,
       d.report_id, d.source_url, d.source_sha256,
       r.source_page, r.source_table, d.captured_at AS source_captured_at
FROM staging.sege_results r
JOIN raw.report_documents d USING (document_id)
JOIN staging.report_publications p USING (document_id, report_id)
WHERE d.source_system='sege';

CREATE OR REPLACE VIEW api.urap_rankings AS
SELECT r.universite_id, r.universite_adi, r.il_kodu, r.il_adi, r.sira,
       r.toplam_puan, r.puanlar, d.edition AS donem, 'turkiye_genel'::text AS siralama_turu,
       d.report_id, d.source_url, d.source_sha256,
       r.source_page, r.source_table, d.captured_at AS source_captured_at
FROM staging.urap_rankings r
JOIN raw.report_documents d USING (document_id)
JOIN staging.report_publications p USING (document_id, report_id)
WHERE d.source_system='urap';

GRANT SELECT, INSERT ON raw.report_documents TO atlas_ingest;
GRANT SELECT, INSERT, UPDATE ON staging.sege_results, staging.urap_rankings,
    staging.report_publications TO atlas_ingest;
GRANT USAGE, SELECT ON SEQUENCE raw.report_documents_document_id_seq TO atlas_ingest;
GRANT SELECT ON api.report_publications, api.sege_results, api.urap_rankings
    TO atlas_api, atlas_analytics;
