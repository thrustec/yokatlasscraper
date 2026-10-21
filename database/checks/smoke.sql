\set ON_ERROR_STOP on
SELECT count(*) AS observed_staging_entities
FROM information_schema.tables
WHERE table_schema='staging' AND table_name IN ('universities', 'program_groups', 'cities', 'programs', 'net_results', 'tuik_population_by_province');
SELECT 'api_views' AS check, count(*) AS found
FROM information_schema.views WHERE table_schema='api';
SELECT * FROM api.data_coverage ORDER BY entity;
SELECT count(*) AS staging_source_columns
FROM information_schema.columns
WHERE table_schema='staging' AND column_name NOT IN ('staging_id','source_record_id','source_payload','staged_at');
DO $$
DECLARE n integer;
BEGIN
  SELECT count(*) INTO n FROM information_schema.tables
  WHERE table_schema='staging' AND table_name IN ('universities','program_groups','cities','programs','net_results','tuik_population_by_province');
  IF n <> 6 THEN RAISE EXCEPTION 'Expected 6 staging tables, got %', n; END IF;
  SELECT count(*) INTO n FROM information_schema.columns
  WHERE table_schema='staging' AND column_name NOT IN ('staging_id','source_record_id','source_payload','staged_at');
  IF n <> 134 THEN RAISE EXCEPTION 'Expected 134 typed API fields, got %', n; END IF;
  SELECT count(*) INTO n FROM information_schema.views WHERE table_schema='api';
  IF n < 9 THEN RAISE EXCEPTION 'Expected >=9 api views, got %', n; END IF;
  IF NOT has_table_privilege('atlas_api','api.program_catalog','SELECT') THEN
    RAISE EXCEPTION 'atlas_api lacks SELECT on api.program_catalog'; END IF;
  IF NOT has_table_privilege('atlas_api','api.tuik_population_by_province','SELECT') THEN
    RAISE EXCEPTION 'atlas_api lacks SELECT on api.tuik_population_by_province'; END IF;
  IF has_table_privilege('atlas_api','core.program_versions','SELECT') THEN
    RAISE EXCEPTION 'atlas_api unexpectedly has direct core SELECT'; END IF;
  IF NOT has_table_privilege('atlas_ingest','raw.api_responses','INSERT') THEN
    RAISE EXCEPTION 'atlas_ingest lacks raw INSERT'; END IF;
END $$;
SELECT 'SMOKE PASS: schemas, 134 columns, views, grants' AS result;
