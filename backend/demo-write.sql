-- Optional local demo views. Source-backed YOK Atlas rows are excluded.
CREATE OR REPLACE VIEW api.demo_universities AS
SELECT universite_id, universite_adi, updated_at
FROM core.universities
WHERE source_record_id IS NULL
WITH CASCADED CHECK OPTION;

CREATE OR REPLACE VIEW api.demo_programs AS
SELECT program_version_id, kilavuz_kodu, yil, puan_turu, birim_adi, universite_id,
       il_kodu, birim_grup_id, birim_id, fymk_id, min_puan, basari_sirasi, kontenjan,
       ingested_at
FROM core.program_versions
WHERE source_record_id IS NULL
WITH CASCADED CHECK OPTION;

GRANT CONNECT ON DATABASE yokatlas_intelligence TO atlas_demo_writer;
GRANT USAGE ON SCHEMA api TO atlas_demo_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON api.demo_universities TO atlas_demo_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON api.demo_programs TO atlas_demo_writer;
GRANT USAGE ON SEQUENCE core.program_versions_program_version_id_seq TO atlas_demo_writer;
