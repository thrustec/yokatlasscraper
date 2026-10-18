-- DRAFT ONLY. Review existing migrations, ownership, privileges, locks, backups before applying.
-- This migration creates source-faithful TÜİK SDMX metadata entities only; no observations are imported.
BEGIN;
CREATE SCHEMA IF NOT EXISTS raw;
CREATE TABLE IF NOT EXISTS raw.tuik_dsd (
 agency_id text NOT NULL, dsd_id text NOT NULL, dsd_version text NOT NULL,
 metadata_status text NOT NULL DEFAULT 'ok', source_sha256 char(64), discovered_at timestamptz,
 PRIMARY KEY (agency_id,dsd_id,dsd_version)
);
CREATE TABLE IF NOT EXISTS raw.tuik_dataflow (
 agency_id text NOT NULL, flow_id text NOT NULL, flow_version text NOT NULL,
 name_tr text, name_en text, description_tr text,
 dsd_agency_id text NOT NULL, dsd_id text NOT NULL, dsd_version text NOT NULL,
 PRIMARY KEY (agency_id,flow_id,flow_version),
 FOREIGN KEY (dsd_agency_id,dsd_id,dsd_version) REFERENCES raw.tuik_dsd(agency_id,dsd_id,dsd_version)
);
CREATE TABLE IF NOT EXISTS raw.tuik_codelist (
 agency_id text NOT NULL, codelist_id text NOT NULL, codelist_version text NOT NULL,
 PRIMARY KEY (agency_id,codelist_id,codelist_version)
);
CREATE TABLE IF NOT EXISTS raw.tuik_codelist_code (
 agency_id text NOT NULL, codelist_id text NOT NULL, codelist_version text NOT NULL,
 code text NOT NULL, parent_code text, label_tr text, label_en text,
 PRIMARY KEY (agency_id,codelist_id,codelist_version,code),
 FOREIGN KEY (agency_id,codelist_id,codelist_version) REFERENCES raw.tuik_codelist(agency_id,codelist_id,codelist_version)
);
CREATE TABLE IF NOT EXISTS raw.tuik_dsd_dimension (
 dsd_agency text NOT NULL, dsd_id text NOT NULL, dsd_version text NOT NULL,
 dimension_id text NOT NULL, dimension_kind text NOT NULL,
 source_position integer, key_position integer, concept_id text,
 codelist_agency text, codelist_id text, codelist_version text,
 PRIMARY KEY (dsd_agency,dsd_id,dsd_version,dimension_id),
 FOREIGN KEY (dsd_agency,dsd_id,dsd_version) REFERENCES raw.tuik_dsd(agency_id,dsd_id,dsd_version),
 FOREIGN KEY (codelist_agency,codelist_id,codelist_version) REFERENCES raw.tuik_codelist(agency_id,codelist_id,codelist_version),
 CHECK (key_position IS NULL OR key_position > 0)
);
CREATE UNIQUE INDEX IF NOT EXISTS tuik_dsd_dimension_key_pos_uq
 ON raw.tuik_dsd_dimension(dsd_agency,dsd_id,dsd_version,key_position) WHERE key_position IS NOT NULL;
CREATE TABLE IF NOT EXISTS raw.tuik_dsd_attribute (
 dsd_agency text NOT NULL, dsd_id text NOT NULL, dsd_version text NOT NULL,
 attribute_id text NOT NULL, attribute_kind text, concept_id text,
 codelist_agency text, codelist_id text, codelist_version text,
 PRIMARY KEY (dsd_agency,dsd_id,dsd_version,attribute_id),
 FOREIGN KEY (dsd_agency,dsd_id,dsd_version) REFERENCES raw.tuik_dsd(agency_id,dsd_id,dsd_version),
 FOREIGN KEY (codelist_agency,codelist_id,codelist_version) REFERENCES raw.tuik_codelist(agency_id,codelist_id,codelist_version)
);
CREATE TABLE IF NOT EXISTS raw.tuik_dsd_codelist (
 dsd_agency text NOT NULL, dsd_id text NOT NULL, dsd_version text NOT NULL,
 codelist_agency text NOT NULL, codelist_id text NOT NULL, codelist_version text NOT NULL,
 PRIMARY KEY (dsd_agency,dsd_id,dsd_version,codelist_agency,codelist_id,codelist_version),
 FOREIGN KEY (dsd_agency,dsd_id,dsd_version) REFERENCES raw.tuik_dsd(agency_id,dsd_id,dsd_version),
 FOREIGN KEY (codelist_agency,codelist_id,codelist_version) REFERENCES raw.tuik_codelist(agency_id,codelist_id,codelist_version)
);
CREATE TABLE IF NOT EXISTS raw.tuik_key_template (
 dsd_agency text NOT NULL, dsd_id text NOT NULL, dsd_version text NOT NULL,
 dimension_order text NOT NULL, query_key_template text NOT NULL,
 template_kind text NOT NULL DEFAULT 'structural_only', notes text,
 PRIMARY KEY (dsd_agency,dsd_id,dsd_version),
 FOREIGN KEY (dsd_agency,dsd_id,dsd_version) REFERENCES raw.tuik_dsd(agency_id,dsd_id,dsd_version),
 CHECK (template_kind = 'structural_only')
);
-- Reserve a separate, explicit status for observed/validated keys. No records inserted at this stage.
CREATE TABLE IF NOT EXISTS raw.tuik_observed_series_key (
 agency_id text NOT NULL, flow_id text NOT NULL, flow_version text NOT NULL,
 series_key text NOT NULL, observed_at timestamptz NOT NULL,
 evidence_sha256 char(64) NOT NULL,
 PRIMARY KEY (agency_id,flow_id,flow_version,series_key),
 FOREIGN KEY (agency_id,flow_id,flow_version) REFERENCES raw.tuik_dataflow(agency_id,flow_id,flow_version)
);
COMMIT;
