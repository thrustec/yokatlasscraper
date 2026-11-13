-- Dedicated data API roles. Existing collector, ETL and demo grants are untouched.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='atlas_raw_writer') THEN
        CREATE ROLE atlas_raw_writer LOGIN NOINHERIT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='atlas_analytics_reader') THEN
        CREATE ROLE atlas_analytics_reader LOGIN NOINHERIT;
    END IF;
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO atlas_raw_writer, atlas_analytics_reader', current_database());
END $$;

GRANT USAGE ON SCHEMA raw TO atlas_raw_writer;
GRANT INSERT ON ALL TABLES IN SCHEMA raw TO atlas_raw_writer;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA raw TO atlas_raw_writer;

-- RETURNING needs SELECT only on the returned primary-key columns.
DO $$
DECLARE item record;
BEGIN
    FOR item IN
        SELECT c.relname,
               string_agg(format('%I', a.attname), ', ' ORDER BY k.ordinality) AS key_columns
        FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace
        JOIN pg_index i ON i.indrelid=c.oid AND i.indisprimary
        CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum, ordinality)
        JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=k.attnum
        WHERE n.nspname='raw' AND c.relkind IN ('r','p') AND k.ordinality<=i.indnkeyatts
        GROUP BY c.oid, c.relname
    LOOP
        EXECUTE format('GRANT SELECT (%s) ON raw.%I TO atlas_raw_writer', item.key_columns, item.relname);
    END LOOP;
END $$;

GRANT USAGE ON SCHEMA analytics TO atlas_analytics_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO atlas_analytics_reader;
ALTER ROLE atlas_analytics_reader SET default_transaction_read_only=on;

ALTER DEFAULT PRIVILEGES FOR ROLE atlas_owner IN SCHEMA raw
    GRANT INSERT ON TABLES TO atlas_raw_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE atlas_owner IN SCHEMA raw
    GRANT USAGE ON SEQUENCES TO atlas_raw_writer;
ALTER DEFAULT PRIVILEGES FOR ROLE atlas_owner, atlas_analytics IN SCHEMA analytics
    GRANT SELECT ON TABLES TO atlas_analytics_reader;
