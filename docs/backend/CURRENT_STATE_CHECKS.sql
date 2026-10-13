-- Backend Phase 0 discovery. Read-only metadata and counts; no payloads/secrets.
-- Run with psql -X -v ON_ERROR_STOP=1 against the intended local database.
\set ON_ERROR_STOP on
BEGIN READ ONLY;

SELECT current_database() AS database_name,
       current_setting('server_version') AS server_version,
       current_setting('TimeZone') AS session_timezone;

SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema IN ('raw', 'staging', 'core', 'quality', 'analytics', 'api')
ORDER BY table_schema, table_name;

-- Generate only safely quoted SELECT counts for the six known project schemas.
SELECT format('SELECT %L AS relation, count(*) AS row_count FROM %I.%I;',
              n.nspname || '.' || c.relname, n.nspname, c.relname)
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname IN ('raw', 'staging', 'core', 'quality', 'analytics', 'api')
ORDER BY n.nspname, c.relname
\gexec

SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolcanlogin, rolconnlimit
FROM pg_roles WHERE rolname LIKE 'atlas_%' ORDER BY rolname;

SELECT grantee, table_schema, privilege_type, count(*) AS object_count
FROM information_schema.role_table_grants
WHERE grantee IN ('atlas_api', 'atlas_ingest', 'atlas_analytics')
  AND table_schema IN ('raw', 'staging', 'core', 'quality', 'analytics', 'api')
GROUP BY grantee, table_schema, privilege_type
ORDER BY grantee, table_schema, privilege_type;

SELECT grantee, table_schema, table_name, column_name, privilege_type
FROM information_schema.column_privileges
WHERE grantee = 'atlas_ingest' AND table_schema = 'raw'
  AND privilege_type = 'UPDATE'
ORDER BY table_name, column_name;

SELECT defaclrole::regrole AS grant_owner, coalesce(n.nspname, 'GLOBAL') AS schema,
       defaclobjtype, defaclacl
FROM pg_default_acl a LEFT JOIN pg_namespace n ON n.oid = a.defaclnamespace
ORDER BY grant_owner, schema, defaclobjtype;

SELECT n.nspname AS schema, c.relname AS relation, con.conname,
       pg_get_constraintdef(con.oid) AS definition
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'raw'
   OR (n.nspname = 'core'
       AND c.relname IN ('program_groups', 'program_versions', 'net_results'))
ORDER BY schema, relation, con.conname;

SELECT pg_get_indexdef('raw.ux_api_response_identity'::regclass) AS response_identity;

SELECT table_schema, table_name, column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'raw'
   OR (table_schema = 'staging' AND column_name IN ('payload', 'source_payload'))
ORDER BY table_schema, table_name, ordinal_position;

SELECT n.nspname AS schema, c.relname, c.relrowsecurity, c.relforcerowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r'
  AND n.nspname IN ('raw', 'staging', 'core', 'quality', 'analytics', 'api')
ORDER BY schema, c.relname;

SELECT name, setting, unit FROM pg_settings
WHERE name IN ('statement_timeout', 'lock_timeout',
               'idle_in_transaction_session_timeout', 'max_connections',
               'ssl', 'TimeZone')
ORDER BY name;

SELECT type, database, user_name, address, auth_method, error
FROM pg_hba_file_rules ORDER BY rule_number;

COMMIT;
