-- YOK Atlas Intelligence read-only schema/data audit
-- Run: docker exec -i yokatlas-intelligence-postgres-1 psql -U atlas_owner -d yokatlas_intelligence -f /dev/stdin < yokatlas_db_audit.sql
\pset null '[NULL]'
\echo '=== 1. Data counts per layer ==='
SELECT 'raw.source_records' table_name, COUNT(*) n FROM raw.source_records UNION ALL
SELECT 'staging.universities', COUNT(*) FROM staging.universities UNION ALL
SELECT 'staging.cities', COUNT(*) FROM staging.cities UNION ALL
SELECT 'staging.program_groups', COUNT(*) FROM staging.program_groups UNION ALL
SELECT 'staging.programs', COUNT(*) FROM staging.programs UNION ALL
SELECT 'staging.net_results', COUNT(*) FROM staging.net_results UNION ALL
SELECT 'core.universities', COUNT(*) FROM core.universities UNION ALL
SELECT 'core.cities', COUNT(*) FROM core.cities UNION ALL
SELECT 'core.program_groups', COUNT(*) FROM core.program_groups UNION ALL
SELECT 'core.program_versions', COUNT(*) FROM core.program_versions UNION ALL
SELECT 'core.net_results', COUNT(*) FROM core.net_results UNION ALL
SELECT 'core.conditions', COUNT(*) FROM core.conditions UNION ALL
SELECT 'core.program_conditions', COUNT(*) FROM core.program_conditions ORDER BY 1;
\echo '=== 2. Raw source entities / endpoints ==='
SELECT source_entity, COUNT(*) records FROM raw.source_records GROUP BY 1 ORDER BY records DESC;
SELECT endpoint, method, COUNT(*) responses, MIN(captured_at) first_seen, MAX(captured_at) last_seen FROM raw.api_responses GROUP BY 1,2 ORDER BY 1,2;
\echo '=== 3. Primary/unique/foreign key definitions ==='
SELECT n.nspname schema_name, c.relname table_name, con.conname constraint_name, con.contype constraint_type, pg_get_constraintdef(con.oid) definition
FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname IN ('raw','staging','core','quality') AND con.contype IN ('p','u','f') ORDER BY 1,2,4,3;
\echo '=== 4. Duplicate natural keys ==='
SELECT 'programs (code,year)' entity, COUNT(*) total_rows, COUNT(DISTINCT (kilavuz_kodu,yil)) distinct_keys, COUNT(*)-COUNT(DISTINCT (kilavuz_kodu,yil)) extra_rows FROM staging.programs
UNION ALL SELECT 'net_results (code,year,score)', COUNT(*),COUNT(DISTINCT (kilavuz_kodu,yil,puan_turu)),COUNT(*)-COUNT(DISTINCT (kilavuz_kodu,yil,puan_turu)) FROM staging.net_results
UNION ALL SELECT 'program_groups (group,score)', COUNT(*),COUNT(DISTINCT (birim_grup_id,puan_turu)),COUNT(*)-COUNT(DISTINCT (birim_grup_id,puan_turu)) FROM staging.program_groups;
\echo '=== 5. Duplicate net payload conflicts ==='
SELECT COUNT(*) duplicated_key_groups, COALESCE(SUM(total-1),0) extra_rows, COUNT(*) FILTER (WHERE payload_variants>1) conflicting_key_groups
FROM (SELECT kilavuz_kodu,yil,puan_turu,COUNT(*) total,COUNT(DISTINCT source_payload) payload_variants FROM staging.net_results GROUP BY 1,2,3 HAVING COUNT(*)>1) q;
\echo '=== 6. Referential coverage and lineage ==='
SELECT COUNT(*) programs,
 COUNT(*) FILTER (WHERE p.source_record_id IS NULL) missing_source,
 COUNT(*) FILTER (WHERE u.universite_id IS NULL) missing_university,
 COUNT(*) FILTER (WHERE p.il_kodu IS NOT NULL AND c.il_kodu IS NULL) missing_city,
 COUNT(*) FILTER (WHERE p.birim_grup_id IS NOT NULL AND g.birim_grup_id IS NULL) missing_group
FROM core.program_versions p LEFT JOIN core.universities u ON u.universite_id=p.universite_id
LEFT JOIN core.cities c ON c.il_kodu=p.il_kodu
LEFT JOIN core.program_groups g ON g.birim_grup_id=p.birim_grup_id AND g.puan_turu=p.puan_turu;
SELECT COUNT(*) nets, COUNT(*) FILTER (WHERE source_record_id IS NULL) missing_source,
COUNT(*) FILTER (WHERE program_version_id IS NULL) no_program_version_link,
COUNT(*) FILTER (WHERE universite_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM core.universities u WHERE u.universite_id=n.universite_id)) no_university_lookup
FROM core.net_results n;
\echo '=== 7. Raw-staging integrity ==='
SELECT 'programs' entity, COUNT(*) checked, COUNT(*) FILTER (WHERE r.source_record_id IS NULL) no_raw_record, COUNT(*) FILTER (WHERE s.source_payload IS DISTINCT FROM r.record) different_payload
FROM staging.programs s LEFT JOIN raw.source_records r ON r.source_record_id=s.source_record_id
UNION ALL SELECT 'net_results',COUNT(*),COUNT(*) FILTER (WHERE r.source_record_id IS NULL),COUNT(*) FILTER (WHERE s.source_payload IS DISTINCT FROM r.record)
FROM staging.net_results s LEFT JOIN raw.source_records r ON r.source_record_id=s.source_record_id;
\echo '=== 8. Source fields absent from typed staging columns (sample across all rows) ==='
WITH source_keys AS (
 SELECT 'programs' entity, k.key key FROM staging.programs s CROSS JOIN LATERAL jsonb_object_keys(s.source_payload) k(key)
 UNION ALL SELECT 'net_results',k.key FROM staging.net_results s CROSS JOIN LATERAL jsonb_object_keys(s.source_payload) k(key)
), normalized AS (SELECT DISTINCT entity,key FROM source_keys)
SELECT n.entity,n.key FROM normalized n
WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns c WHERE c.table_schema='staging' AND c.table_name=n.entity AND regexp_replace(lower(n.key),'([a-z0-9])([A-Z])','\1_\2','g')=c.column_name)
ORDER BY 1,2;
-- Column naming includes non-mechanical aliases (gkY->gk_y etc.). Inspect findings, not automatic failures.
\echo '=== 9. Snapshot year coverage ==='
SELECT 'staging.programs' entity, yil, COUNT(*) FROM staging.programs GROUP BY yil
UNION ALL SELECT 'staging.net_results',yil,COUNT(*) FROM staging.net_results GROUP BY yil ORDER BY 1,2;
