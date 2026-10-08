-- Runs only during first DB initialization. Passwords are safely SQL-quoted by psql variables.
REVOKE ALL ON DATABASE yokatlas_intelligence FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE ROLE atlas_ingest LOGIN PASSWORD :'ingest_password';
CREATE ROLE atlas_api LOGIN PASSWORD :'api_password';
CREATE ROLE atlas_analytics LOGIN PASSWORD :'analytics_password';
GRANT CONNECT ON DATABASE yokatlas_intelligence TO atlas_ingest, atlas_api, atlas_analytics;
