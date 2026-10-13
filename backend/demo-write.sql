-- Optional local demo view. Source-backed YOK Atlas rows are excluded.
CREATE OR REPLACE VIEW api.demo_universities AS
SELECT universite_id, universite_adi, updated_at
FROM core.universities
WHERE source_record_id IS NULL
WITH CASCADED CHECK OPTION;

GRANT CONNECT ON DATABASE yokatlas_intelligence TO atlas_demo_writer;
GRANT USAGE ON SCHEMA api TO atlas_demo_writer;
GRANT SELECT, INSERT, UPDATE, DELETE ON api.demo_universities TO atlas_demo_writer;
