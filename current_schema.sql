--
-- PostgreSQL database dump
--

\restrict 2kzhQSARH8KfN4oMKYVREA0sNPb6WTbSdUZagWdizXGlW2XAbFKbfu1hYZeXyc5

-- Dumped from database version 17.11 (Debian 17.11-1.pgdg13+2)
-- Dumped by pg_dump version 17.11 (Debian 17.11-1.pgdg13+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: analytics; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA analytics;


--
-- Name: api; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA api;


--
-- Name: core; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA core;


--
-- Name: quality; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA quality;


--
-- Name: raw; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA raw;


--
-- Name: staging; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA staging;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: cities; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.cities (
    il_kodu bigint NOT NULL,
    il_adi text NOT NULL,
    source_record_id bigint,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: cities; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.cities AS
 SELECT il_kodu,
    il_adi
   FROM core.cities;


--
-- Name: net_results; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.net_results (
    net_result_id bigint NOT NULL,
    kilavuz_kodu bigint NOT NULL,
    yil integer NOT NULL,
    puan_turu text NOT NULL,
    program_version_id bigint,
    universite_id bigint,
    birim_grup_id bigint,
    taban_puan double precision,
    katsayi double precision,
    obp double precision,
    tyt_trk_net double precision,
    tyt_sos_net double precision,
    tyt_mat_net double precision,
    tyt_fen_net double precision,
    ayt_mat_net double precision,
    ayt_fiz_net double precision,
    ayt_kim_net double precision,
    ayt_bio_net double precision,
    ayt_tde_net double precision,
    ayt_trh1_net double precision,
    ayt_cog1_net double precision,
    ayt_trh2_net double precision,
    ayt_cog2_net double precision,
    ayt_fel_net double precision,
    ayt_din_net double precision,
    ydt_ydil_net double precision,
    source_record_id bigint,
    remaining_fields jsonb DEFAULT '{}'::jsonb NOT NULL,
    ingested_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: program_groups; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.program_groups (
    birim_grup_id bigint NOT NULL,
    puan_turu text NOT NULL,
    birim_grup_adi text NOT NULL,
    source_record_id bigint
);


--
-- Name: program_versions; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.program_versions (
    program_version_id bigint NOT NULL,
    kilavuz_kodu bigint NOT NULL,
    yil integer NOT NULL,
    universite_id bigint NOT NULL,
    il_kodu bigint,
    birim_grup_id bigint,
    puan_turu text NOT NULL,
    birim_id bigint,
    birim_adi text NOT NULL,
    fymk_id bigint,
    min_puan double precision,
    basari_sirasi bigint,
    kontenjan bigint,
    source_record_id bigint,
    remaining_fields jsonb DEFAULT '{}'::jsonb NOT NULL,
    ingested_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: universities; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.universities (
    universite_id bigint NOT NULL,
    universite_adi text NOT NULL,
    source_record_id bigint,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: data_coverage; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.data_coverage AS
 SELECT 'universities'::text AS entity,
    count(*) AS row_count
   FROM core.universities
UNION ALL
 SELECT 'cities'::text AS entity,
    count(*) AS row_count
   FROM core.cities
UNION ALL
 SELECT 'program_groups'::text AS entity,
    count(*) AS row_count
   FROM core.program_groups
UNION ALL
 SELECT 'program_versions'::text AS entity,
    count(*) AS row_count
   FROM core.program_versions
UNION ALL
 SELECT 'net_results'::text AS entity,
    count(*) AS row_count
   FROM core.net_results;


--
-- Name: net_results; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.net_results AS
 SELECT net_result_id,
    kilavuz_kodu,
    yil,
    puan_turu,
    program_version_id,
    universite_id,
    birim_grup_id,
    taban_puan,
    katsayi,
    obp,
    tyt_trk_net,
    tyt_sos_net,
    tyt_mat_net,
    tyt_fen_net,
    ayt_mat_net,
    ayt_fiz_net,
    ayt_kim_net,
    ayt_bio_net,
    ayt_tde_net,
    ayt_trh1_net,
    ayt_cog1_net,
    ayt_trh2_net,
    ayt_cog2_net,
    ayt_fel_net,
    ayt_din_net,
    ydt_ydil_net,
    ingested_at
   FROM core.net_results n;


--
-- Name: net_year_summary; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.net_year_summary AS
 SELECT yil,
    puan_turu,
    count(*) AS net_records,
    avg(tyt_mat_net) AS avg_tyt_mat_net,
    avg(tyt_trk_net) AS avg_tyt_trk_net,
    avg(obp) AS avg_obp
   FROM core.net_results
  GROUP BY yil, puan_turu;


--
-- Name: program_catalog; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.program_catalog AS
 SELECT p.program_version_id,
    p.kilavuz_kodu,
    p.yil,
    p.puan_turu,
    p.birim_id,
    p.birim_adi,
    p.fymk_id,
    p.universite_id,
    u.universite_adi,
    p.birim_grup_id,
    g.birim_grup_adi,
    p.il_kodu,
    c.il_adi,
    p.min_puan,
    p.basari_sirasi,
    p.kontenjan,
    p.ingested_at
   FROM (((core.program_versions p
     JOIN core.universities u ON ((u.universite_id = p.universite_id)))
     LEFT JOIN core.program_groups g ON (((g.birim_grup_id = p.birim_grup_id) AND (g.puan_turu = p.puan_turu))))
     LEFT JOIN core.cities c ON ((c.il_kodu = p.il_kodu)));


--
-- Name: program_groups; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.program_groups AS
 SELECT birim_grup_id,
    puan_turu,
    birim_grup_adi
   FROM core.program_groups;


--
-- Name: program_year_summary; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.program_year_summary AS
 SELECT yil,
    puan_turu,
    count(*) AS programs,
    count(*) FILTER (WHERE (min_puan IS NOT NULL)) AS with_min_puan,
    avg(min_puan) AS avg_min_puan,
    (sum(kontenjan))::bigint AS total_kontenjan
   FROM core.program_versions
  GROUP BY yil, puan_turu;


--
-- Name: universities; Type: VIEW; Schema: api; Owner: -
--

CREATE VIEW api.universities AS
 SELECT universite_id,
    universite_adi
   FROM core.universities;


--
-- Name: conditions; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.conditions (
    condition_code text NOT NULL,
    description text,
    raw_details jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: net_results_net_result_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.net_results ALTER COLUMN net_result_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.net_results_net_result_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: program_conditions; Type: TABLE; Schema: core; Owner: -
--

CREATE TABLE core.program_conditions (
    program_version_id bigint NOT NULL,
    condition_code text NOT NULL
);


--
-- Name: program_versions_program_version_id_seq; Type: SEQUENCE; Schema: core; Owner: -
--

ALTER TABLE core.program_versions ALTER COLUMN program_version_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME core.program_versions_program_version_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: data_quality_checks; Type: TABLE; Schema: quality; Owner: -
--

CREATE TABLE quality.data_quality_checks (
    check_id bigint NOT NULL,
    ingestion_run_id bigint,
    check_name text NOT NULL,
    status text NOT NULL,
    observed_value jsonb,
    executed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: data_quality_checks_check_id_seq; Type: SEQUENCE; Schema: quality; Owner: -
--

ALTER TABLE quality.data_quality_checks ALTER COLUMN check_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME quality.data_quality_checks_check_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: quarantined_records; Type: TABLE; Schema: quality; Owner: -
--

CREATE TABLE quality.quarantined_records (
    quarantine_id bigint NOT NULL,
    ingestion_run_id bigint,
    entity text NOT NULL,
    reason text NOT NULL,
    natural_key jsonb,
    source_record_ids jsonb DEFAULT '[]'::jsonb NOT NULL,
    candidate_payloads jsonb DEFAULT '[]'::jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    resolved_at timestamp with time zone,
    resolution text
);


--
-- Name: quarantined_records_quarantine_id_seq; Type: SEQUENCE; Schema: quality; Owner: -
--

ALTER TABLE quality.quarantined_records ALTER COLUMN quarantine_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME quality.quarantined_records_quarantine_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: api_responses; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.api_responses (
    api_response_id bigint NOT NULL,
    ingestion_run_id bigint NOT NULL,
    endpoint text NOT NULL,
    method text NOT NULL,
    score_type text,
    page_number integer,
    captured_at timestamp with time zone DEFAULT now() NOT NULL,
    source_hash_sha256 text,
    http_status integer,
    payload jsonb NOT NULL,
    source_path text,
    CONSTRAINT api_responses_source_hash_sha256_check CHECK (((source_hash_sha256 IS NULL) OR (length(source_hash_sha256) = 64)))
);


--
-- Name: api_responses_api_response_id_seq; Type: SEQUENCE; Schema: raw; Owner: -
--

ALTER TABLE raw.api_responses ALTER COLUMN api_response_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME raw.api_responses_api_response_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: ingestion_runs; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.ingestion_runs (
    ingestion_run_id bigint NOT NULL,
    source_system text DEFAULT 'yokatlas'::text NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    completed_at timestamp with time zone,
    status text DEFAULT 'running'::text NOT NULL,
    scraper_version text,
    details jsonb DEFAULT '{}'::jsonb NOT NULL
);


--
-- Name: ingestion_runs_ingestion_run_id_seq; Type: SEQUENCE; Schema: raw; Owner: -
--

ALTER TABLE raw.ingestion_runs ALTER COLUMN ingestion_run_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME raw.ingestion_runs_ingestion_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: source_records; Type: TABLE; Schema: raw; Owner: -
--

CREATE TABLE raw.source_records (
    source_record_id bigint NOT NULL,
    api_response_id bigint NOT NULL,
    source_entity text NOT NULL,
    source_array_index integer NOT NULL,
    record jsonb NOT NULL,
    record_hash_sha256 text,
    CONSTRAINT source_records_source_array_index_check CHECK ((source_array_index >= 0))
);


--
-- Name: source_records_source_record_id_seq; Type: SEQUENCE; Schema: raw; Owner: -
--

ALTER TABLE raw.source_records ALTER COLUMN source_record_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME raw.source_records_source_record_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: cities; Type: TABLE; Schema: staging; Owner: -
--

CREATE TABLE staging.cities (
    staging_id bigint NOT NULL,
    source_record_id bigint NOT NULL,
    il_adi text,
    il_kodu bigint,
    source_payload jsonb NOT NULL,
    staged_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: cities_staging_id_seq; Type: SEQUENCE; Schema: staging; Owner: -
--

ALTER TABLE staging.cities ALTER COLUMN staging_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME staging.cities_staging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: net_results; Type: TABLE; Schema: staging; Owner: -
--

CREATE TABLE staging.net_results (
    staging_id bigint NOT NULL,
    source_record_id bigint NOT NULL,
    ayt_bio_net double precision,
    ayt_cog1_net double precision,
    ayt_cog2_net double precision,
    ayt_din_net double precision,
    ayt_fel_net double precision,
    ayt_fiz_net double precision,
    ayt_kim_net double precision,
    ayt_mat_net double precision,
    ayt_tde_net double precision,
    ayt_trh1_net double precision,
    ayt_trh2_net double precision,
    birim_adi text,
    birim_grup_adi text,
    birim_grup_id bigint,
    birim_id bigint,
    birim_turu_adi text,
    birim_turu_id bigint,
    katsayi double precision,
    kilavuz_kodu bigint,
    obp double precision,
    puan_turu text,
    taban_puan double precision,
    tyt_fen_net double precision,
    tyt_mat_net double precision,
    tyt_sos_net double precision,
    tyt_trk_net double precision,
    universite_adi text,
    universite_id bigint,
    universite_turu text,
    ydt_ydil_net double precision,
    yil bigint,
    source_payload jsonb NOT NULL,
    staged_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: net_results_staging_id_seq; Type: SEQUENCE; Schema: staging; Owner: -
--

ALTER TABLE staging.net_results ALTER COLUMN staging_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME staging.net_results_staging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: program_groups; Type: TABLE; Schema: staging; Owner: -
--

CREATE TABLE staging.program_groups (
    staging_id bigint NOT NULL,
    source_record_id bigint NOT NULL,
    birim_grup_adi text,
    birim_grup_id bigint,
    puan_turu text,
    source_payload jsonb NOT NULL,
    staged_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: program_groups_staging_id_seq; Type: SEQUENCE; Schema: staging; Owner: -
--

ALTER TABLE staging.program_groups ALTER COLUMN staging_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME staging.program_groups_staging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: programs; Type: TABLE; Schema: staging; Owner: -
--

CREATE TABLE staging.programs (
    staging_id bigint NOT NULL,
    source_record_id bigint NOT NULL,
    abayp text,
    akreditasyon text,
    akreditasyon_ack text,
    ar_gor bigint,
    basari_sirasi bigint,
    basari_sirasi1 bigint,
    basari_sirasi2 bigint,
    basari_sirasi3 bigint,
    birim_adi text,
    birim_ek_turu text,
    birim_grup_adi text,
    birim_grup_id bigint,
    birim_hiyerarsi text,
    birim_id bigint,
    birim_turu_adi text,
    birim_turu_id bigint,
    burs_orani_adi text,
    burs_orani_id bigint,
    doc bigint,
    donem text,
    dou bigint,
    dprm_y bigint,
    dus text,
    eski_birim_id bigint,
    eski_kilavuz_kodu bigint,
    fymk_adi text,
    fymk_id bigint,
    fymk_il_adi text,
    fymk_il_kodu bigint,
    fymk_ilce_adi text,
    fymk_ilce_kodu bigint,
    gk1 bigint,
    gk2 bigint,
    gk3 bigint,
    gk_y bigint,
    il_adi text,
    il_kodu bigint,
    ilce_adi text,
    ilce_kodu bigint,
    kil_aciklama text,
    kilavuz_kodu bigint,
    kontenjan bigint,
    kontenjan_meb bigint,
    kontenjan_obs bigint,
    kontenjan_sgy bigint,
    kontenjan_y34 bigint,
    kosul text,
    kosul_list jsonb,
    kpss1 text,
    min_basari_sirasi text,
    min_basari_sirasi_kosul text,
    min_puan double precision,
    min_puan1 text,
    min_puan2 text,
    min_puan3 text,
    obk_y bigint,
    ogr_gor bigint,
    ogrenim_dili_adi text,
    ogrenim_dili_id bigint,
    ogrenim_suresi bigint,
    ogrenim_turu_adi text,
    ogrenim_turu_id bigint,
    osym_kilavuz_id bigint,
    prof bigint,
    puan_turu text,
    sgy_y bigint,
    sinav text,
    tablo_turu text,
    tam_burs_birim_id bigint,
    tusktp text,
    tustt1 text,
    tustt2 text,
    tyc text,
    ucret bigint,
    uni_akreditasyon text,
    uni_il_adi text,
    uni_il_kodu bigint,
    uni_ilce_adi text,
    uni_ilce_kodu bigint,
    uni_kil_aciklama text,
    universite_adi text,
    universite_id bigint,
    universite_turu text,
    uygulamali_egitim_modeli text,
    y34 bigint,
    yil bigint,
    source_payload jsonb NOT NULL,
    staged_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: programs_staging_id_seq; Type: SEQUENCE; Schema: staging; Owner: -
--

ALTER TABLE staging.programs ALTER COLUMN staging_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME staging.programs_staging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: universities; Type: TABLE; Schema: staging; Owner: -
--

CREATE TABLE staging.universities (
    staging_id bigint NOT NULL,
    source_record_id bigint NOT NULL,
    universite_adi text,
    universite_id bigint,
    source_payload jsonb NOT NULL,
    staged_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: universities_staging_id_seq; Type: SEQUENCE; Schema: staging; Owner: -
--

ALTER TABLE staging.universities ALTER COLUMN staging_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME staging.universities_staging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: cities cities_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.cities
    ADD CONSTRAINT cities_pkey PRIMARY KEY (il_kodu);


--
-- Name: conditions conditions_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.conditions
    ADD CONSTRAINT conditions_pkey PRIMARY KEY (condition_code);


--
-- Name: net_results net_results_kilavuz_kodu_yil_puan_turu_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.net_results
    ADD CONSTRAINT net_results_kilavuz_kodu_yil_puan_turu_key UNIQUE (kilavuz_kodu, yil, puan_turu);


--
-- Name: net_results net_results_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.net_results
    ADD CONSTRAINT net_results_pkey PRIMARY KEY (net_result_id);


--
-- Name: program_conditions program_conditions_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_conditions
    ADD CONSTRAINT program_conditions_pkey PRIMARY KEY (program_version_id, condition_code);


--
-- Name: program_groups program_groups_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_groups
    ADD CONSTRAINT program_groups_pkey PRIMARY KEY (birim_grup_id, puan_turu);


--
-- Name: program_versions program_versions_kilavuz_kodu_yil_key; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_versions
    ADD CONSTRAINT program_versions_kilavuz_kodu_yil_key UNIQUE (kilavuz_kodu, yil);


--
-- Name: program_versions program_versions_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_versions
    ADD CONSTRAINT program_versions_pkey PRIMARY KEY (program_version_id);


--
-- Name: universities universities_pkey; Type: CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.universities
    ADD CONSTRAINT universities_pkey PRIMARY KEY (universite_id);


--
-- Name: data_quality_checks data_quality_checks_pkey; Type: CONSTRAINT; Schema: quality; Owner: -
--

ALTER TABLE ONLY quality.data_quality_checks
    ADD CONSTRAINT data_quality_checks_pkey PRIMARY KEY (check_id);


--
-- Name: quarantined_records quarantined_records_pkey; Type: CONSTRAINT; Schema: quality; Owner: -
--

ALTER TABLE ONLY quality.quarantined_records
    ADD CONSTRAINT quarantined_records_pkey PRIMARY KEY (quarantine_id);


--
-- Name: api_responses api_responses_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.api_responses
    ADD CONSTRAINT api_responses_pkey PRIMARY KEY (api_response_id);


--
-- Name: ingestion_runs ingestion_runs_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.ingestion_runs
    ADD CONSTRAINT ingestion_runs_pkey PRIMARY KEY (ingestion_run_id);


--
-- Name: source_records source_records_api_response_id_source_entity_source_array_i_key; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.source_records
    ADD CONSTRAINT source_records_api_response_id_source_entity_source_array_i_key UNIQUE (api_response_id, source_entity, source_array_index);


--
-- Name: source_records source_records_pkey; Type: CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.source_records
    ADD CONSTRAINT source_records_pkey PRIMARY KEY (source_record_id);


--
-- Name: cities cities_pkey; Type: CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.cities
    ADD CONSTRAINT cities_pkey PRIMARY KEY (staging_id);


--
-- Name: cities cities_source_record_id_key; Type: CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.cities
    ADD CONSTRAINT cities_source_record_id_key UNIQUE (source_record_id);


--
-- Name: net_results net_results_pkey; Type: CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.net_results
    ADD CONSTRAINT net_results_pkey PRIMARY KEY (staging_id);


--
-- Name: net_results net_results_source_record_id_key; Type: CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.net_results
    ADD CONSTRAINT net_results_source_record_id_key UNIQUE (source_record_id);


--
-- Name: program_groups program_groups_pkey; Type: CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.program_groups
    ADD CONSTRAINT program_groups_pkey PRIMARY KEY (staging_id);


--
-- Name: program_groups program_groups_source_record_id_key; Type: CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.program_groups
    ADD CONSTRAINT program_groups_source_record_id_key UNIQUE (source_record_id);


--
-- Name: programs programs_pkey; Type: CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.programs
    ADD CONSTRAINT programs_pkey PRIMARY KEY (staging_id);


--
-- Name: programs programs_source_record_id_key; Type: CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.programs
    ADD CONSTRAINT programs_source_record_id_key UNIQUE (source_record_id);


--
-- Name: universities universities_pkey; Type: CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.universities
    ADD CONSTRAINT universities_pkey PRIMARY KEY (staging_id);


--
-- Name: universities universities_source_record_id_key; Type: CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.universities
    ADD CONSTRAINT universities_source_record_id_key UNIQUE (source_record_id);


--
-- Name: idx_nets_university; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_nets_university ON core.net_results USING btree (universite_id);


--
-- Name: idx_nets_year_type; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_nets_year_type ON core.net_results USING btree (yil, puan_turu);


--
-- Name: idx_program_version_group; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_program_version_group ON core.program_versions USING btree (birim_grup_id, puan_turu);


--
-- Name: idx_program_version_university; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_program_version_university ON core.program_versions USING btree (universite_id, yil);


--
-- Name: idx_program_version_year_score; Type: INDEX; Schema: core; Owner: -
--

CREATE INDEX idx_program_version_year_score ON core.program_versions USING btree (yil, puan_turu);


--
-- Name: idx_api_response_endpoint; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX idx_api_response_endpoint ON raw.api_responses USING btree (endpoint, score_type, page_number);


--
-- Name: idx_api_response_run; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX idx_api_response_run ON raw.api_responses USING btree (ingestion_run_id);


--
-- Name: idx_source_record_entity; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX idx_source_record_entity ON raw.source_records USING btree (source_entity);


--
-- Name: idx_source_records_hash; Type: INDEX; Schema: raw; Owner: -
--

CREATE INDEX idx_source_records_hash ON raw.source_records USING btree (record_hash_sha256);


--
-- Name: ux_api_response_identity; Type: INDEX; Schema: raw; Owner: -
--

CREATE UNIQUE INDEX ux_api_response_identity ON raw.api_responses USING btree (endpoint, COALESCE(score_type, ''::text), COALESCE(page_number, '-1'::integer), source_hash_sha256) WHERE (source_hash_sha256 IS NOT NULL);


--
-- Name: cities cities_source_record_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.cities
    ADD CONSTRAINT cities_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id);


--
-- Name: net_results net_results_program_version_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.net_results
    ADD CONSTRAINT net_results_program_version_id_fkey FOREIGN KEY (program_version_id) REFERENCES core.program_versions(program_version_id);


--
-- Name: net_results net_results_source_record_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.net_results
    ADD CONSTRAINT net_results_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id);


--
-- Name: program_conditions program_conditions_condition_code_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_conditions
    ADD CONSTRAINT program_conditions_condition_code_fkey FOREIGN KEY (condition_code) REFERENCES core.conditions(condition_code);


--
-- Name: program_conditions program_conditions_program_version_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_conditions
    ADD CONSTRAINT program_conditions_program_version_id_fkey FOREIGN KEY (program_version_id) REFERENCES core.program_versions(program_version_id);


--
-- Name: program_groups program_groups_source_record_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_groups
    ADD CONSTRAINT program_groups_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id);


--
-- Name: program_versions program_versions_birim_grup_id_puan_turu_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_versions
    ADD CONSTRAINT program_versions_birim_grup_id_puan_turu_fkey FOREIGN KEY (birim_grup_id, puan_turu) REFERENCES core.program_groups(birim_grup_id, puan_turu);


--
-- Name: program_versions program_versions_il_kodu_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_versions
    ADD CONSTRAINT program_versions_il_kodu_fkey FOREIGN KEY (il_kodu) REFERENCES core.cities(il_kodu);


--
-- Name: program_versions program_versions_source_record_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_versions
    ADD CONSTRAINT program_versions_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id);


--
-- Name: program_versions program_versions_universite_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.program_versions
    ADD CONSTRAINT program_versions_universite_id_fkey FOREIGN KEY (universite_id) REFERENCES core.universities(universite_id);


--
-- Name: universities universities_source_record_id_fkey; Type: FK CONSTRAINT; Schema: core; Owner: -
--

ALTER TABLE ONLY core.universities
    ADD CONSTRAINT universities_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id);


--
-- Name: data_quality_checks data_quality_checks_ingestion_run_id_fkey; Type: FK CONSTRAINT; Schema: quality; Owner: -
--

ALTER TABLE ONLY quality.data_quality_checks
    ADD CONSTRAINT data_quality_checks_ingestion_run_id_fkey FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id);


--
-- Name: quarantined_records quarantined_records_ingestion_run_id_fkey; Type: FK CONSTRAINT; Schema: quality; Owner: -
--

ALTER TABLE ONLY quality.quarantined_records
    ADD CONSTRAINT quarantined_records_ingestion_run_id_fkey FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id);


--
-- Name: api_responses api_responses_ingestion_run_id_fkey; Type: FK CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.api_responses
    ADD CONSTRAINT api_responses_ingestion_run_id_fkey FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id);


--
-- Name: source_records source_records_api_response_id_fkey; Type: FK CONSTRAINT; Schema: raw; Owner: -
--

ALTER TABLE ONLY raw.source_records
    ADD CONSTRAINT source_records_api_response_id_fkey FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id);


--
-- Name: cities cities_source_record_id_fkey; Type: FK CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.cities
    ADD CONSTRAINT cities_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id);


--
-- Name: net_results net_results_source_record_id_fkey; Type: FK CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.net_results
    ADD CONSTRAINT net_results_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id);


--
-- Name: program_groups program_groups_source_record_id_fkey; Type: FK CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.program_groups
    ADD CONSTRAINT program_groups_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id);


--
-- Name: programs programs_source_record_id_fkey; Type: FK CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.programs
    ADD CONSTRAINT programs_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id);


--
-- Name: universities universities_source_record_id_fkey; Type: FK CONSTRAINT; Schema: staging; Owner: -
--

ALTER TABLE ONLY staging.universities
    ADD CONSTRAINT universities_source_record_id_fkey FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id);


--
-- PostgreSQL database dump complete
--

\unrestrict 2kzhQSARH8KfN4oMKYVREA0sNPb6WTbSdUZagWdizXGlW2XAbFKbfu1hYZeXyc5

