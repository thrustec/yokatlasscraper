-- URAP RAW 2025-2026 / PostgreSQL 17
-- Apply ONLY after review against current_schema.sql / current live DDL.
-- Creates only new objects under raw; does not change staging/core/analytics/api.
BEGIN;
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'raw') THEN
    RAISE EXCEPTION 'raw schema missing: first apply the project baseline migrations';
  END IF;
END $$;
CREATE TABLE raw.urap_artifacts (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  sha256 char(64) NOT NULL UNIQUE CHECK (sha256 ~ '^[0-9a-f]{64}$'),
  source_url text NOT NULL,
  storage_uri text NOT NULL,
  content_type text NOT NULL,
  byte_size bigint NOT NULL CHECK (byte_size > 0),
  captured_at timestamptz NOT NULL DEFAULT now(),
  published_on date,
  parser_version text NOT NULL
);
CREATE TABLE raw.urap_editions (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  edition text NOT NULL UNIQUE CHECK (edition ~ '^[0-9]{4}-[0-9]{4}$'),
  publication_date date,
  source_artifact_id bigint NOT NULL REFERENCES raw.urap_artifacts(id),
  imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE raw.urap_ranking_groups (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code text NOT NULL UNIQUE,
  label text NOT NULL
);
CREATE TABLE raw.urap_ranking_rows (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  edition_id bigint NOT NULL REFERENCES raw.urap_editions(id),
  group_id bigint NOT NULL REFERENCES raw.urap_ranking_groups(id),
  source_artifact_id bigint NOT NULL REFERENCES raw.urap_artifacts(id),
  source_page integer NOT NULL CHECK (source_page > 0),
  source_rank integer NOT NULL CHECK (source_rank > 0),
  university_name text NOT NULL CHECK (length(trim(university_name)) > 0),
  city text NOT NULL CHECK (length(trim(city)) > 0),
  total_score numeric(10,2) NOT NULL CHECK (total_score >= 0),
  extraction_score_delta numeric(7,2),
  CONSTRAINT urap_rows_unique_rank UNIQUE (edition_id, group_id, source_rank),
  CONSTRAINT urap_rows_unique_artifact_rank UNIQUE (source_artifact_id, group_id, source_rank)
);
CREATE INDEX urap_rows_source_name_idx ON raw.urap_ranking_rows (university_name);
CREATE TABLE raw.urap_metric_definitions (
  metric_code text PRIMARY KEY,
  name_tr text NOT NULL,
  value_kind text NOT NULL DEFAULT 'SCORE' CHECK (value_kind = 'SCORE'),
  unit text NOT NULL DEFAULT 'URAP_SCORE' CHECK (unit = 'URAP_SCORE'),
  display_order smallint NOT NULL UNIQUE CHECK (display_order BETWEEN 1 AND 8)
);
CREATE TABLE raw.urap_metric_scores (
  ranking_row_id bigint NOT NULL REFERENCES raw.urap_ranking_rows(id) ON DELETE RESTRICT,
  metric_code text NOT NULL REFERENCES raw.urap_metric_definitions(metric_code),
  score numeric(10,2) NOT NULL CHECK (score >= 0),
  PRIMARY KEY (ranking_row_id, metric_code)
);
INSERT INTO raw.urap_ranking_groups (code,label) VALUES ('GENERAL','Türkiye genel sıralaması');
INSERT INTO raw.urap_metric_definitions (metric_code,name_tr,display_order) VALUES
('article_score','Makale Puanı',1),
('citation_score','Atıf Puanı',2),
('scientific_document_score','Bilimsel Doküman Puanı',3),
('doctoral_score','Doktora Puanı',4),
('faculty_student_score','Öğretim Üyesi / Öğrenci Puanı',5),
('international_collaboration_score','Uluslararası İşbirliği Puanı',6),
('domestic_collaboration_score','Yurtiçi İşbirliği Puanı',7),
('tubitak_project_score','TÜBİTAK Proje Puanı',8);
COMMIT;
