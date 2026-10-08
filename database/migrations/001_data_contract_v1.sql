-- YÖK Atlas Intelligence | PostgreSQL schema v1 (DRAFT)
-- Generated from collected API JSON and forensics reports. Run on a new database.
-- Exact payload duplicate rows must be removed from CORE inserts, not RAW.
-- No automatic net -> program/year FK: historical years do not overlap.
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS quality;
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS raw.ingestion_runs (
    ingestion_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_system TEXT NOT NULL DEFAULT 'yokatlas',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    scraper_version TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS raw.api_responses (
    api_response_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingestion_run_id BIGINT NOT NULL REFERENCES raw.ingestion_runs(ingestion_run_id),
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    score_type TEXT,
    page_number INTEGER,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_hash_sha256 TEXT,
    http_status INTEGER,
    payload JSONB NOT NULL,
    CHECK (source_hash_sha256 IS NULL OR length(source_hash_sha256) = 64)
);
CREATE INDEX IF NOT EXISTS idx_api_response_run ON raw.api_responses(ingestion_run_id);
CREATE INDEX IF NOT EXISTS idx_api_response_endpoint ON raw.api_responses(endpoint, score_type, page_number);

CREATE TABLE IF NOT EXISTS raw.source_records (
    source_record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    api_response_id BIGINT NOT NULL REFERENCES raw.api_responses(api_response_id),
    source_entity TEXT NOT NULL,
    source_array_index INTEGER NOT NULL,
    record JSONB NOT NULL,
    record_hash_sha256 TEXT,
    UNIQUE (api_response_id, source_entity, source_array_index),
    CHECK (source_array_index >= 0)
);
CREATE INDEX IF NOT EXISTS idx_source_record_entity ON raw.source_records(source_entity);

-- Typed staging for observed API resource universities (2 source fields).
CREATE TABLE IF NOT EXISTS staging.universities (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_record_id BIGINT NOT NULL UNIQUE REFERENCES raw.source_records(source_record_id),
    "universite_adi" TEXT,
    "universite_id" BIGINT,
    source_payload JSONB NOT NULL,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Typed staging for observed API resource program_groups (3 source fields).
CREATE TABLE IF NOT EXISTS staging.program_groups (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_record_id BIGINT NOT NULL UNIQUE REFERENCES raw.source_records(source_record_id),
    "birim_grup_adi" TEXT,
    "birim_grup_id" BIGINT,
    "puan_turu" TEXT,
    source_payload JSONB NOT NULL,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Typed staging for observed API resource cities (2 source fields).
CREATE TABLE IF NOT EXISTS staging.cities (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_record_id BIGINT NOT NULL UNIQUE REFERENCES raw.source_records(source_record_id),
    "il_adi" TEXT,
    "il_kodu" BIGINT,
    source_payload JSONB NOT NULL,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Typed staging for observed API resource programs (86 source fields).
CREATE TABLE IF NOT EXISTS staging.programs (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_record_id BIGINT NOT NULL UNIQUE REFERENCES raw.source_records(source_record_id),
    "abayp" TEXT,
    "akreditasyon" TEXT,
    "akreditasyon_ack" TEXT,
    "ar_gor" BIGINT,
    "basari_sirasi" BIGINT,
    "basari_sirasi1" BIGINT,
    "basari_sirasi2" BIGINT,
    "basari_sirasi3" BIGINT,
    "birim_adi" TEXT,
    "birim_ek_turu" TEXT,
    "birim_grup_adi" TEXT,
    "birim_grup_id" BIGINT,
    "birim_hiyerarsi" TEXT,
    "birim_id" BIGINT,
    "birim_turu_adi" TEXT,
    "birim_turu_id" BIGINT,
    "burs_orani_adi" TEXT,
    "burs_orani_id" BIGINT,
    "doc" BIGINT,
    "donem" TEXT,
    "dou" BIGINT,
    "dprm_y" BIGINT,
    "dus" TEXT,
    "eski_birim_id" BIGINT,
    "eski_kilavuz_kodu" BIGINT,
    "fymk_adi" TEXT,
    "fymk_id" BIGINT,
    "fymk_il_adi" TEXT,
    "fymk_il_kodu" BIGINT,
    "fymk_ilce_adi" TEXT,
    "fymk_ilce_kodu" BIGINT,
    "gk1" BIGINT,
    "gk2" BIGINT,
    "gk3" BIGINT,
    "gk_y" BIGINT,
    "il_adi" TEXT,
    "il_kodu" BIGINT,
    "ilce_adi" TEXT,
    "ilce_kodu" BIGINT,
    "kil_aciklama" TEXT,
    "kilavuz_kodu" BIGINT,
    "kontenjan" BIGINT,
    "kontenjan_meb" BIGINT,
    "kontenjan_obs" BIGINT,
    "kontenjan_sgy" BIGINT,
    "kontenjan_y34" BIGINT,
    "kosul" TEXT,
    "kosul_list" JSONB,
    "kpss1" TEXT,
    "min_basari_sirasi" TEXT,
    "min_basari_sirasi_kosul" TEXT,
    "min_puan" DOUBLE PRECISION,
    "min_puan1" TEXT,
    "min_puan2" TEXT,
    "min_puan3" TEXT,
    "obk_y" BIGINT,
    "ogr_gor" BIGINT,
    "ogrenim_dili_adi" TEXT,
    "ogrenim_dili_id" BIGINT,
    "ogrenim_suresi" BIGINT,
    "ogrenim_turu_adi" TEXT,
    "ogrenim_turu_id" BIGINT,
    "osym_kilavuz_id" BIGINT,
    "prof" BIGINT,
    "puan_turu" TEXT,
    "sgy_y" BIGINT,
    "sinav" TEXT,
    "tablo_turu" TEXT,
    "tam_burs_birim_id" BIGINT,
    "tusktp" TEXT,
    "tustt1" TEXT,
    "tustt2" TEXT,
    "tyc" TEXT,
    "ucret" BIGINT,
    "uni_akreditasyon" TEXT,
    "uni_il_adi" TEXT,
    "uni_il_kodu" BIGINT,
    "uni_ilce_adi" TEXT,
    "uni_ilce_kodu" BIGINT,
    "uni_kil_aciklama" TEXT,
    "universite_adi" TEXT,
    "universite_id" BIGINT,
    "universite_turu" TEXT,
    "uygulamali_egitim_modeli" TEXT,
    "y34" BIGINT,
    "yil" BIGINT,
    source_payload JSONB NOT NULL,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Typed staging for observed API resource net_results (31 source fields).
CREATE TABLE IF NOT EXISTS staging.net_results (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_record_id BIGINT NOT NULL UNIQUE REFERENCES raw.source_records(source_record_id),
    "ayt_bio_net" DOUBLE PRECISION,
    "ayt_cog1_net" DOUBLE PRECISION,
    "ayt_cog2_net" DOUBLE PRECISION,
    "ayt_din_net" DOUBLE PRECISION,
    "ayt_fel_net" DOUBLE PRECISION,
    "ayt_fiz_net" DOUBLE PRECISION,
    "ayt_kim_net" DOUBLE PRECISION,
    "ayt_mat_net" DOUBLE PRECISION,
    "ayt_tde_net" DOUBLE PRECISION,
    "ayt_trh1_net" DOUBLE PRECISION,
    "ayt_trh2_net" DOUBLE PRECISION,
    "birim_adi" TEXT,
    "birim_grup_adi" TEXT,
    "birim_grup_id" BIGINT,
    "birim_id" BIGINT,
    "birim_turu_adi" TEXT,
    "birim_turu_id" BIGINT,
    "katsayi" DOUBLE PRECISION,
    "kilavuz_kodu" BIGINT,
    "obp" DOUBLE PRECISION,
    "puan_turu" TEXT,
    "taban_puan" DOUBLE PRECISION,
    "tyt_fen_net" DOUBLE PRECISION,
    "tyt_mat_net" DOUBLE PRECISION,
    "tyt_sos_net" DOUBLE PRECISION,
    "tyt_trk_net" DOUBLE PRECISION,
    "universite_adi" TEXT,
    "universite_id" BIGINT,
    "universite_turu" TEXT,
    "ydt_ydil_net" DOUBLE PRECISION,
    "yil" BIGINT,
    source_payload JSONB NOT NULL,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.universities (
    universite_id BIGINT PRIMARY KEY,
    universite_adi TEXT NOT NULL,
    source_record_id BIGINT REFERENCES raw.source_records(source_record_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS core.cities (
    il_kodu BIGINT PRIMARY KEY,
    il_adi TEXT NOT NULL,
    source_record_id BIGINT REFERENCES raw.source_records(source_record_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS core.program_groups (
    birim_grup_id BIGINT NOT NULL,
    puan_turu TEXT NOT NULL,
    birim_grup_adi TEXT NOT NULL,
    source_record_id BIGINT REFERENCES raw.source_records(source_record_id),
    PRIMARY KEY (birim_grup_id, puan_turu)
);
CREATE TABLE IF NOT EXISTS core.program_versions (
    program_version_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kilavuz_kodu BIGINT NOT NULL,
    yil INTEGER NOT NULL,
    universite_id BIGINT NOT NULL REFERENCES core.universities(universite_id),
    il_kodu BIGINT REFERENCES core.cities(il_kodu),
    birim_grup_id BIGINT,
    puan_turu TEXT NOT NULL,
    birim_id BIGINT,
    birim_adi TEXT NOT NULL,
    fymk_id BIGINT,
    min_puan DOUBLE PRECISION,
    basari_sirasi BIGINT,
    kontenjan BIGINT,
    source_record_id BIGINT REFERENCES raw.source_records(source_record_id),
    remaining_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (kilavuz_kodu, yil),
    FOREIGN KEY (birim_grup_id, puan_turu)
      REFERENCES core.program_groups(birim_grup_id, puan_turu)
);
CREATE INDEX IF NOT EXISTS idx_program_version_university ON core.program_versions(universite_id, yil);
CREATE INDEX IF NOT EXISTS idx_program_version_group ON core.program_versions(birim_grup_id, puan_turu);

-- Score type is part of the natural key. Do not load the 71 exact duplicates twice.
-- program_version_id is nullable because available program versions are for 2026,
-- while net results are for 2023..2025. Only populate after validating a same-year match.
CREATE TABLE IF NOT EXISTS core.net_results (
    net_result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kilavuz_kodu BIGINT NOT NULL,
    yil INTEGER NOT NULL,
    puan_turu TEXT NOT NULL,
    program_version_id BIGINT REFERENCES core.program_versions(program_version_id),
    universite_id BIGINT,
    birim_grup_id BIGINT,
    taban_puan DOUBLE PRECISION,
    katsayi DOUBLE PRECISION,
    obp DOUBLE PRECISION,
    tyt_trk_net DOUBLE PRECISION,
    tyt_sos_net DOUBLE PRECISION,
    tyt_mat_net DOUBLE PRECISION,
    tyt_fen_net DOUBLE PRECISION,
    ayt_mat_net DOUBLE PRECISION,
    ayt_fiz_net DOUBLE PRECISION,
    ayt_kim_net DOUBLE PRECISION,
    ayt_bio_net DOUBLE PRECISION,
    ayt_tde_net DOUBLE PRECISION,
    ayt_trh1_net DOUBLE PRECISION,
    ayt_cog1_net DOUBLE PRECISION,
    ayt_trh2_net DOUBLE PRECISION,
    ayt_cog2_net DOUBLE PRECISION,
    ayt_fel_net DOUBLE PRECISION,
    ayt_din_net DOUBLE PRECISION,
    ydt_ydil_net DOUBLE PRECISION,
    source_record_id BIGINT REFERENCES raw.source_records(source_record_id),
    remaining_fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (kilavuz_kodu, yil, puan_turu)
);
CREATE INDEX IF NOT EXISTS idx_nets_year_type ON core.net_results(yil, puan_turu);
CREATE INDEX IF NOT EXISTS idx_nets_university ON core.net_results(universite_id);

CREATE TABLE IF NOT EXISTS core.conditions (
    condition_code TEXT PRIMARY KEY,
    description TEXT,
    raw_details JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE TABLE IF NOT EXISTS core.program_conditions (
    program_version_id BIGINT NOT NULL REFERENCES core.program_versions(program_version_id),
    condition_code TEXT NOT NULL REFERENCES core.conditions(condition_code),
    PRIMARY KEY (program_version_id, condition_code)
);

CREATE TABLE IF NOT EXISTS quality.quarantined_records (
    quarantine_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingestion_run_id BIGINT REFERENCES raw.ingestion_runs(ingestion_run_id),
    entity TEXT NOT NULL,
    reason TEXT NOT NULL,
    natural_key JSONB,
    source_record_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    candidate_payloads JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    resolution TEXT
);
CREATE TABLE IF NOT EXISTS quality.data_quality_checks (
    check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingestion_run_id BIGINT REFERENCES raw.ingestion_runs(ingestion_run_id),
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    observed_value JSONB,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Analytics schema deliberately empty until year mappings and business KPIs are validated.
-- No destructive DROP/DELETE operations in this migration.
