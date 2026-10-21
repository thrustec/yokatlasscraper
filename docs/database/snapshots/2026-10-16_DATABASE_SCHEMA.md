# YÖK Atlas Intelligence — PostgreSQL Şema Envanteri

> Bu belge canlı PostgreSQL kataloglarından otomatik üretilmiştir. Veri kayıtları, parolalar ve bağlantı sırları dışa aktarılmaz.

- **Tarih:** 2026-10-16 22:31 UTC
- **Database:** `yokatlas_intelligence`
- **Docker container:** `yokatlas-intelligence-postgres-1`
- **Şema sayısı (kullanıcı tabloları/görünümleri olan):** 5
- **Tablo/görünüm sayısı:** 34

## Genel envanter

| Şema | Tablolar / görünümler |
|---|---:|
| `api` | 8 |
| `core` | 7 |
| `quality` | 2 |
| `raw` | 12 |
| `staging` | 5 |

## `api` şeması

### `api.cities`

**Tür:** VIEW

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `il_kodu` | `bigint` | Evet |  |
| `il_adi` | `text` | Evet |  |

**Görünüm tanımı**

```sql
SELECT il_kodu,
    il_adi
   FROM core.cities;
```

### `api.data_coverage`

**Tür:** VIEW

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `entity` | `text` | Evet |  |
| `row_count` | `bigint` | Evet |  |

**Görünüm tanımı**

```sql
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
```

### `api.net_results`

**Tür:** VIEW

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `net_result_id` | `bigint` | Evet |  |
| `kilavuz_kodu` | `bigint` | Evet |  |
| `yil` | `integer` | Evet |  |
| `puan_turu` | `text` | Evet |  |
| `program_version_id` | `bigint` | Evet |  |
| `universite_id` | `bigint` | Evet |  |
| `birim_grup_id` | `bigint` | Evet |  |
| `taban_puan` | `double precision` | Evet |  |
| `katsayi` | `double precision` | Evet |  |
| `obp` | `double precision` | Evet |  |
| `tyt_trk_net` | `double precision` | Evet |  |
| `tyt_sos_net` | `double precision` | Evet |  |
| `tyt_mat_net` | `double precision` | Evet |  |
| `tyt_fen_net` | `double precision` | Evet |  |
| `ayt_mat_net` | `double precision` | Evet |  |
| `ayt_fiz_net` | `double precision` | Evet |  |
| `ayt_kim_net` | `double precision` | Evet |  |
| `ayt_bio_net` | `double precision` | Evet |  |
| `ayt_tde_net` | `double precision` | Evet |  |
| `ayt_trh1_net` | `double precision` | Evet |  |
| `ayt_cog1_net` | `double precision` | Evet |  |
| `ayt_trh2_net` | `double precision` | Evet |  |
| `ayt_cog2_net` | `double precision` | Evet |  |
| `ayt_fel_net` | `double precision` | Evet |  |
| `ayt_din_net` | `double precision` | Evet |  |
| `ydt_ydil_net` | `double precision` | Evet |  |
| `ingested_at` | `timestamp with time zone` | Evet |  |

**Görünüm tanımı**

```sql
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
```

### `api.net_year_summary`

**Tür:** VIEW

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `yil` | `integer` | Evet |  |
| `puan_turu` | `text` | Evet |  |
| `net_records` | `bigint` | Evet |  |
| `avg_tyt_mat_net` | `double precision` | Evet |  |
| `avg_tyt_trk_net` | `double precision` | Evet |  |
| `avg_obp` | `double precision` | Evet |  |

**Görünüm tanımı**

```sql
SELECT yil,
    puan_turu,
    count(*) AS net_records,
    avg(tyt_mat_net) AS avg_tyt_mat_net,
    avg(tyt_trk_net) AS avg_tyt_trk_net,
    avg(obp) AS avg_obp
   FROM core.net_results
  GROUP BY yil, puan_turu;
```

### `api.program_catalog`

**Tür:** VIEW

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `program_version_id` | `bigint` | Evet |  |
| `kilavuz_kodu` | `bigint` | Evet |  |
| `yil` | `integer` | Evet |  |
| `puan_turu` | `text` | Evet |  |
| `birim_id` | `bigint` | Evet |  |
| `birim_adi` | `text` | Evet |  |
| `fymk_id` | `bigint` | Evet |  |
| `universite_id` | `bigint` | Evet |  |
| `universite_adi` | `text` | Evet |  |
| `birim_grup_id` | `bigint` | Evet |  |
| `birim_grup_adi` | `text` | Evet |  |
| `il_kodu` | `bigint` | Evet |  |
| `il_adi` | `text` | Evet |  |
| `min_puan` | `double precision` | Evet |  |
| `basari_sirasi` | `bigint` | Evet |  |
| `kontenjan` | `bigint` | Evet |  |
| `ingested_at` | `timestamp with time zone` | Evet |  |

**Görünüm tanımı**

```sql
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
   FROM core.program_versions p
     JOIN core.universities u ON u.universite_id = p.universite_id
     LEFT JOIN core.program_groups g ON g.birim_grup_id = p.birim_grup_id AND g.puan_turu = p.puan_turu
     LEFT JOIN core.cities c ON c.il_kodu = p.il_kodu;
```

### `api.program_groups`

**Tür:** VIEW

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `birim_grup_id` | `bigint` | Evet |  |
| `puan_turu` | `text` | Evet |  |
| `birim_grup_adi` | `text` | Evet |  |

**Görünüm tanımı**

```sql
SELECT birim_grup_id,
    puan_turu,
    birim_grup_adi
   FROM core.program_groups;
```

### `api.program_year_summary`

**Tür:** VIEW

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `yil` | `integer` | Evet |  |
| `puan_turu` | `text` | Evet |  |
| `programs` | `bigint` | Evet |  |
| `with_min_puan` | `bigint` | Evet |  |
| `avg_min_puan` | `double precision` | Evet |  |
| `total_kontenjan` | `bigint` | Evet |  |

**Görünüm tanımı**

```sql
SELECT yil,
    puan_turu,
    count(*) AS programs,
    count(*) FILTER (WHERE min_puan IS NOT NULL) AS with_min_puan,
    avg(min_puan) AS avg_min_puan,
    sum(kontenjan)::bigint AS total_kontenjan
   FROM core.program_versions
  GROUP BY yil, puan_turu;
```

### `api.universities`

**Tür:** VIEW

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `universite_id` | `bigint` | Evet |  |
| `universite_adi` | `text` | Evet |  |

**Görünüm tanımı**

```sql
SELECT universite_id,
    universite_adi
   FROM core.universities;
```


## `core` şeması

### `core.cities`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `il_kodu` | `bigint` | Hayır |  |
| `il_adi` | `text` | Hayır |  |
| `source_record_id` | `bigint` | Evet |  |
| `updated_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `cities_pkey` | PRIMARY KEY | `PRIMARY KEY (il_kodu)` |
| `cities_source_record_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id)` |

**İndeksler**

- `cities_pkey` — `CREATE UNIQUE INDEX cities_pkey ON core.cities USING btree (il_kodu)`

### `core.conditions`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `condition_code` | `text` | Hayır |  |
| `description` | `text` | Evet |  |
| `raw_details` | `jsonb` | Hayır | '{}'::jsonb |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `conditions_pkey` | PRIMARY KEY | `PRIMARY KEY (condition_code)` |

**İndeksler**

- `conditions_pkey` — `CREATE UNIQUE INDEX conditions_pkey ON core.conditions USING btree (condition_code)`

### `core.net_results`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `net_result_id` | `bigint` | Hayır | IDENTITY a |
| `kilavuz_kodu` | `bigint` | Hayır |  |
| `yil` | `integer` | Hayır |  |
| `puan_turu` | `text` | Hayır |  |
| `program_version_id` | `bigint` | Evet |  |
| `universite_id` | `bigint` | Evet |  |
| `birim_grup_id` | `bigint` | Evet |  |
| `taban_puan` | `double precision` | Evet |  |
| `katsayi` | `double precision` | Evet |  |
| `obp` | `double precision` | Evet |  |
| `tyt_trk_net` | `double precision` | Evet |  |
| `tyt_sos_net` | `double precision` | Evet |  |
| `tyt_mat_net` | `double precision` | Evet |  |
| `tyt_fen_net` | `double precision` | Evet |  |
| `ayt_mat_net` | `double precision` | Evet |  |
| `ayt_fiz_net` | `double precision` | Evet |  |
| `ayt_kim_net` | `double precision` | Evet |  |
| `ayt_bio_net` | `double precision` | Evet |  |
| `ayt_tde_net` | `double precision` | Evet |  |
| `ayt_trh1_net` | `double precision` | Evet |  |
| `ayt_cog1_net` | `double precision` | Evet |  |
| `ayt_trh2_net` | `double precision` | Evet |  |
| `ayt_cog2_net` | `double precision` | Evet |  |
| `ayt_fel_net` | `double precision` | Evet |  |
| `ayt_din_net` | `double precision` | Evet |  |
| `ydt_ydil_net` | `double precision` | Evet |  |
| `source_record_id` | `bigint` | Evet |  |
| `remaining_fields` | `jsonb` | Hayır | '{}'::jsonb |
| `ingested_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `net_results_kilavuz_kodu_yil_puan_turu_key` | UNIQUE | `UNIQUE (kilavuz_kodu, yil, puan_turu)` |
| `net_results_pkey` | PRIMARY KEY | `PRIMARY KEY (net_result_id)` |
| `net_results_program_version_id_fkey` | FOREIGN KEY | `FOREIGN KEY (program_version_id) REFERENCES core.program_versions(program_version_id)` |
| `net_results_source_record_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id)` |

**İndeksler**

- `idx_nets_university` — `CREATE INDEX idx_nets_university ON core.net_results USING btree (universite_id)`
- `idx_nets_year_type` — `CREATE INDEX idx_nets_year_type ON core.net_results USING btree (yil, puan_turu)`
- `net_results_kilavuz_kodu_yil_puan_turu_key` — `CREATE UNIQUE INDEX net_results_kilavuz_kodu_yil_puan_turu_key ON core.net_results USING btree (kilavuz_kodu, yil, puan_turu)`
- `net_results_pkey` — `CREATE UNIQUE INDEX net_results_pkey ON core.net_results USING btree (net_result_id)`

### `core.program_conditions`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `program_version_id` | `bigint` | Hayır |  |
| `condition_code` | `text` | Hayır |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `program_conditions_condition_code_fkey` | FOREIGN KEY | `FOREIGN KEY (condition_code) REFERENCES core.conditions(condition_code)` |
| `program_conditions_pkey` | PRIMARY KEY | `PRIMARY KEY (program_version_id, condition_code)` |
| `program_conditions_program_version_id_fkey` | FOREIGN KEY | `FOREIGN KEY (program_version_id) REFERENCES core.program_versions(program_version_id)` |

**İndeksler**

- `program_conditions_pkey` — `CREATE UNIQUE INDEX program_conditions_pkey ON core.program_conditions USING btree (program_version_id, condition_code)`

### `core.program_groups`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `birim_grup_id` | `bigint` | Hayır |  |
| `puan_turu` | `text` | Hayır |  |
| `birim_grup_adi` | `text` | Hayır |  |
| `source_record_id` | `bigint` | Evet |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `program_groups_pkey` | PRIMARY KEY | `PRIMARY KEY (birim_grup_id, puan_turu)` |
| `program_groups_source_record_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id)` |

**İndeksler**

- `program_groups_pkey` — `CREATE UNIQUE INDEX program_groups_pkey ON core.program_groups USING btree (birim_grup_id, puan_turu)`

### `core.program_versions`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `program_version_id` | `bigint` | Hayır | IDENTITY a |
| `kilavuz_kodu` | `bigint` | Hayır |  |
| `yil` | `integer` | Hayır |  |
| `universite_id` | `bigint` | Hayır |  |
| `il_kodu` | `bigint` | Evet |  |
| `birim_grup_id` | `bigint` | Evet |  |
| `puan_turu` | `text` | Hayır |  |
| `birim_id` | `bigint` | Evet |  |
| `birim_adi` | `text` | Hayır |  |
| `fymk_id` | `bigint` | Evet |  |
| `min_puan` | `double precision` | Evet |  |
| `basari_sirasi` | `bigint` | Evet |  |
| `kontenjan` | `bigint` | Evet |  |
| `source_record_id` | `bigint` | Evet |  |
| `remaining_fields` | `jsonb` | Hayır | '{}'::jsonb |
| `ingested_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `program_versions_birim_grup_id_puan_turu_fkey` | FOREIGN KEY | `FOREIGN KEY (birim_grup_id, puan_turu) REFERENCES core.program_groups(birim_grup_id, puan_turu)` |
| `program_versions_il_kodu_fkey` | FOREIGN KEY | `FOREIGN KEY (il_kodu) REFERENCES core.cities(il_kodu)` |
| `program_versions_kilavuz_kodu_yil_key` | UNIQUE | `UNIQUE (kilavuz_kodu, yil)` |
| `program_versions_pkey` | PRIMARY KEY | `PRIMARY KEY (program_version_id)` |
| `program_versions_source_record_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id)` |
| `program_versions_universite_id_fkey` | FOREIGN KEY | `FOREIGN KEY (universite_id) REFERENCES core.universities(universite_id)` |

**İndeksler**

- `idx_program_version_group` — `CREATE INDEX idx_program_version_group ON core.program_versions USING btree (birim_grup_id, puan_turu)`
- `idx_program_version_university` — `CREATE INDEX idx_program_version_university ON core.program_versions USING btree (universite_id, yil)`
- `idx_program_version_year_score` — `CREATE INDEX idx_program_version_year_score ON core.program_versions USING btree (yil, puan_turu)`
- `program_versions_kilavuz_kodu_yil_key` — `CREATE UNIQUE INDEX program_versions_kilavuz_kodu_yil_key ON core.program_versions USING btree (kilavuz_kodu, yil)`
- `program_versions_pkey` — `CREATE UNIQUE INDEX program_versions_pkey ON core.program_versions USING btree (program_version_id)`

### `core.universities`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `universite_id` | `bigint` | Hayır |  |
| `universite_adi` | `text` | Hayır |  |
| `source_record_id` | `bigint` | Evet |  |
| `updated_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `universities_pkey` | PRIMARY KEY | `PRIMARY KEY (universite_id)` |
| `universities_source_record_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id)` |

**İndeksler**

- `universities_pkey` — `CREATE UNIQUE INDEX universities_pkey ON core.universities USING btree (universite_id)`


## `quality` şeması

### `quality.data_quality_checks`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `check_id` | `bigint` | Hayır | IDENTITY a |
| `ingestion_run_id` | `bigint` | Evet |  |
| `check_name` | `text` | Hayır |  |
| `status` | `text` | Hayır |  |
| `observed_value` | `jsonb` | Evet |  |
| `executed_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `data_quality_checks_ingestion_run_id_fkey` | FOREIGN KEY | `FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id)` |
| `data_quality_checks_pkey` | PRIMARY KEY | `PRIMARY KEY (check_id)` |

**İndeksler**

- `data_quality_checks_pkey` — `CREATE UNIQUE INDEX data_quality_checks_pkey ON quality.data_quality_checks USING btree (check_id)`

### `quality.quarantined_records`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `quarantine_id` | `bigint` | Hayır | IDENTITY a |
| `ingestion_run_id` | `bigint` | Evet |  |
| `entity` | `text` | Hayır |  |
| `reason` | `text` | Hayır |  |
| `natural_key` | `jsonb` | Evet |  |
| `source_record_ids` | `jsonb` | Hayır | '[]'::jsonb |
| `candidate_payloads` | `jsonb` | Hayır | '[]'::jsonb |
| `created_at` | `timestamp with time zone` | Hayır | now() |
| `resolved_at` | `timestamp with time zone` | Evet |  |
| `resolution` | `text` | Evet |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `quarantined_records_ingestion_run_id_fkey` | FOREIGN KEY | `FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id)` |
| `quarantined_records_pkey` | PRIMARY KEY | `PRIMARY KEY (quarantine_id)` |

**İndeksler**

- `quarantined_records_pkey` — `CREATE UNIQUE INDEX quarantined_records_pkey ON quality.quarantined_records USING btree (quarantine_id)`


## `raw` şeması

### `raw.api_responses`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `api_response_id` | `bigint` | Hayır | IDENTITY a |
| `ingestion_run_id` | `bigint` | Hayır |  |
| `endpoint` | `text` | Hayır |  |
| `method` | `text` | Hayır |  |
| `score_type` | `text` | Evet |  |
| `page_number` | `integer` | Evet |  |
| `captured_at` | `timestamp with time zone` | Hayır | now() |
| `source_hash_sha256` | `text` | Evet |  |
| `http_status` | `integer` | Evet |  |
| `payload` | `jsonb` | Hayır |  |
| `source_path` | `text` | Evet |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `api_responses_ingestion_run_id_fkey` | FOREIGN KEY | `FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id)` |
| `api_responses_pkey` | PRIMARY KEY | `PRIMARY KEY (api_response_id)` |
| `api_responses_source_hash_sha256_check` | CHECK | `CHECK (source_hash_sha256 IS NULL OR length(source_hash_sha256) = 64)` |

**İndeksler**

- `api_responses_pkey` — `CREATE UNIQUE INDEX api_responses_pkey ON raw.api_responses USING btree (api_response_id)`
- `idx_api_response_endpoint` — `CREATE INDEX idx_api_response_endpoint ON raw.api_responses USING btree (endpoint, score_type, page_number)`
- `idx_api_response_run` — `CREATE INDEX idx_api_response_run ON raw.api_responses USING btree (ingestion_run_id)`
- `ux_api_response_identity` — `CREATE UNIQUE INDEX ux_api_response_identity ON raw.api_responses USING btree (endpoint, COALESCE(score_type, ''::text), COALESCE(page_number, '-1'::integer), source_hash_sha256) WHERE (source_hash_sha256 IS NOT NULL)`

### `raw.ingestion_runs`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `ingestion_run_id` | `bigint` | Hayır | IDENTITY a |
| `source_system` | `text` | Hayır | 'yokatlas'::text |
| `started_at` | `timestamp with time zone` | Hayır | now() |
| `completed_at` | `timestamp with time zone` | Evet |  |
| `status` | `text` | Hayır | 'running'::text |
| `scraper_version` | `text` | Evet |  |
| `details` | `jsonb` | Hayır | '{}'::jsonb |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `ingestion_runs_pkey` | PRIMARY KEY | `PRIMARY KEY (ingestion_run_id)` |

**İndeksler**

- `ingestion_runs_pkey` — `CREATE UNIQUE INDEX ingestion_runs_pkey ON raw.ingestion_runs USING btree (ingestion_run_id)`

### `raw.sege_artifacts`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `id` | `bigint` | Hayır | IDENTITY a |
| `sha256` | `character(64)` | Hayır |  |
| `source_url` | `text` | Hayır |  |
| `storage_uri` | `text` | Hayır |  |
| `content_type` | `text` | Hayır | 'application/pdf'::text |
| `byte_size` | `bigint` | Hayır |  |
| `captured_at` | `timestamp with time zone` | Hayır | now() |
| `parser_version` | `text` | Hayır |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `sege_artifacts_byte_size_check` | CHECK | `CHECK (byte_size > 0)` |
| `sege_artifacts_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `sege_artifacts_sha256_check` | CHECK | `CHECK (sha256 ~ '^[0-9a-f]{64}$'::text)` |
| `sege_artifacts_sha256_key` | UNIQUE | `UNIQUE (sha256)` |
| `sege_artifacts_storage_uri_check` | CHECK | `CHECK (length(btrim(storage_uri)) > 0)` |

**İndeksler**

- `sege_artifacts_pkey` — `CREATE UNIQUE INDEX sege_artifacts_pkey ON raw.sege_artifacts USING btree (id)`
- `sege_artifacts_sha256_key` — `CREATE UNIQUE INDEX sege_artifacts_sha256_key ON raw.sege_artifacts USING btree (sha256)`

### `raw.sege_editions`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `id` | `bigint` | Hayır | IDENTITY a |
| `edition_year` | `integer` | Hayır |  |
| `geography_level` | `text` | Hayır |  |
| `source_artifact_id` | `bigint` | Hayır |  |
| `tier_method` | `text` | Hayır |  |
| `source_method_note` | `text` | Hayır |  |
| `imported_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `sege_editions_geography_level_check` | CHECK | `CHECK (geography_level = ANY (ARRAY['PROVINCE'::text, 'DISTRICT'::text]))` |
| `sege_editions_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `sege_editions_source_artifact_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_artifact_id) REFERENCES raw.sege_artifacts(id)` |
| `sege_editions_tier_method_check` | CHECK | `CHECK (tier_method = ANY (ARRAY['EXTRACTED_FROM_SOURCE'::text, 'DERIVED_FROM_PUBLISHED_RANK_COUNTS'::text]))` |
| `sege_editions_unique` | UNIQUE | `UNIQUE (edition_year, geography_level)` |
| `sege_editions_unique_artifact` | UNIQUE | `UNIQUE (source_artifact_id, edition_year, geography_level)` |

**İndeksler**

- `sege_editions_pkey` — `CREATE UNIQUE INDEX sege_editions_pkey ON raw.sege_editions USING btree (id)`
- `sege_editions_unique` — `CREATE UNIQUE INDEX sege_editions_unique ON raw.sege_editions USING btree (edition_year, geography_level)`
- `sege_editions_unique_artifact` — `CREATE UNIQUE INDEX sege_editions_unique_artifact ON raw.sege_editions USING btree (source_artifact_id, edition_year, geography_level)`

### `raw.sege_ranking_rows`

**Tür:** TABLE
**Açıklama:** Publication specific SEGE rows. No automatic YOK Atlas geographic ID mapping.

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `id` | `bigint` | Hayır | IDENTITY a |
| `edition_id` | `bigint` | Hayır |  |
| `source_artifact_id` | `bigint` | Hayır |  |
| `source_page` | `integer` | Hayır |  |
| `source_rank` | `integer` | Hayır |  |
| `province_name` | `text` | Hayır |  |
| `district_name` | `text` | Evet |  |
| `sege_score` | `numeric(12,3)` | Hayır |  |
| `development_tier` | `smallint` | Hayır |  |
| `tier_method` | `text` | Hayır |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `sege_ranking_rows_development_tier_check` | CHECK | `CHECK (development_tier >= 1 AND development_tier <= 6)` |
| `sege_ranking_rows_district_name_check` | CHECK | `CHECK (district_name IS NULL OR length(btrim(district_name)) > 0)` |
| `sege_ranking_rows_edition_id_fkey` | FOREIGN KEY | `FOREIGN KEY (edition_id) REFERENCES raw.sege_editions(id)` |
| `sege_ranking_rows_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `sege_ranking_rows_province_name_check` | CHECK | `CHECK (length(btrim(province_name)) > 0)` |
| `sege_ranking_rows_source_artifact_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_artifact_id) REFERENCES raw.sege_artifacts(id)` |
| `sege_ranking_rows_source_page_check` | CHECK | `CHECK (source_page > 0)` |
| `sege_ranking_rows_source_rank_check` | CHECK | `CHECK (source_rank > 0)` |
| `sege_ranking_rows_tier_method_check` | CHECK | `CHECK (tier_method = ANY (ARRAY['EXTRACTED_FROM_SOURCE'::text, 'DERIVED_FROM_PUBLISHED_RANK_COUNTS'::text]))` |
| `sege_rows_unique_rank` | UNIQUE | `UNIQUE (edition_id, source_rank)` |

**İndeksler**

- `sege_ranking_rows_pkey` — `CREATE UNIQUE INDEX sege_ranking_rows_pkey ON raw.sege_ranking_rows USING btree (id)`
- `sege_rows_place_idx` — `CREATE INDEX sege_rows_place_idx ON raw.sege_ranking_rows USING btree (province_name, district_name)`
- `sege_rows_unique_rank` — `CREATE UNIQUE INDEX sege_rows_unique_rank ON raw.sege_ranking_rows USING btree (edition_id, source_rank)`

### `raw.source_records`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `source_record_id` | `bigint` | Hayır | IDENTITY a |
| `api_response_id` | `bigint` | Hayır |  |
| `source_entity` | `text` | Hayır |  |
| `source_array_index` | `integer` | Hayır |  |
| `record` | `jsonb` | Hayır |  |
| `record_hash_sha256` | `text` | Evet |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `source_records_api_response_id_fkey` | FOREIGN KEY | `FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id)` |
| `source_records_api_response_id_source_entity_source_array_i_key` | UNIQUE | `UNIQUE (api_response_id, source_entity, source_array_index)` |
| `source_records_pkey` | PRIMARY KEY | `PRIMARY KEY (source_record_id)` |
| `source_records_source_array_index_check` | CHECK | `CHECK (source_array_index >= 0)` |

**İndeksler**

- `idx_source_record_entity` — `CREATE INDEX idx_source_record_entity ON raw.source_records USING btree (source_entity)`
- `idx_source_records_hash` — `CREATE INDEX idx_source_records_hash ON raw.source_records USING btree (record_hash_sha256)`
- `source_records_api_response_id_source_entity_source_array_i_key` — `CREATE UNIQUE INDEX source_records_api_response_id_source_entity_source_array_i_key ON raw.source_records USING btree (api_response_id, source_entity, source_array_index)`
- `source_records_pkey` — `CREATE UNIQUE INDEX source_records_pkey ON raw.source_records USING btree (source_record_id)`

### `raw.urap_artifacts`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `id` | `bigint` | Hayır | IDENTITY a |
| `sha256` | `character(64)` | Hayır |  |
| `source_url` | `text` | Hayır |  |
| `storage_uri` | `text` | Hayır |  |
| `content_type` | `text` | Hayır |  |
| `byte_size` | `bigint` | Hayır |  |
| `captured_at` | `timestamp with time zone` | Hayır | now() |
| `published_on` | `date` | Evet |  |
| `parser_version` | `text` | Hayır |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `urap_artifacts_byte_size_check` | CHECK | `CHECK (byte_size > 0)` |
| `urap_artifacts_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `urap_artifacts_sha256_check` | CHECK | `CHECK (sha256 ~ '^[0-9a-f]{64}$'::text)` |
| `urap_artifacts_sha256_key` | UNIQUE | `UNIQUE (sha256)` |

**İndeksler**

- `urap_artifacts_pkey` — `CREATE UNIQUE INDEX urap_artifacts_pkey ON raw.urap_artifacts USING btree (id)`
- `urap_artifacts_sha256_key` — `CREATE UNIQUE INDEX urap_artifacts_sha256_key ON raw.urap_artifacts USING btree (sha256)`

### `raw.urap_editions`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `id` | `bigint` | Hayır | IDENTITY a |
| `edition` | `text` | Hayır |  |
| `publication_date` | `date` | Evet |  |
| `source_artifact_id` | `bigint` | Hayır |  |
| `imported_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `urap_editions_edition_check` | CHECK | `CHECK (edition ~ '^[0-9]{4}-[0-9]{4}$'::text)` |
| `urap_editions_edition_key` | UNIQUE | `UNIQUE (edition)` |
| `urap_editions_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `urap_editions_source_artifact_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_artifact_id) REFERENCES raw.urap_artifacts(id)` |

**İndeksler**

- `urap_editions_edition_key` — `CREATE UNIQUE INDEX urap_editions_edition_key ON raw.urap_editions USING btree (edition)`
- `urap_editions_pkey` — `CREATE UNIQUE INDEX urap_editions_pkey ON raw.urap_editions USING btree (id)`

### `raw.urap_metric_definitions`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `metric_code` | `text` | Hayır |  |
| `name_tr` | `text` | Hayır |  |
| `value_kind` | `text` | Hayır | 'SCORE'::text |
| `unit` | `text` | Hayır | 'URAP_SCORE'::text |
| `display_order` | `smallint` | Hayır |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `urap_metric_definitions_display_order_check` | CHECK | `CHECK (display_order >= 1 AND display_order <= 8)` |
| `urap_metric_definitions_display_order_key` | UNIQUE | `UNIQUE (display_order)` |
| `urap_metric_definitions_pkey` | PRIMARY KEY | `PRIMARY KEY (metric_code)` |
| `urap_metric_definitions_unit_check` | CHECK | `CHECK (unit = 'URAP_SCORE'::text)` |
| `urap_metric_definitions_value_kind_check` | CHECK | `CHECK (value_kind = 'SCORE'::text)` |

**İndeksler**

- `urap_metric_definitions_display_order_key` — `CREATE UNIQUE INDEX urap_metric_definitions_display_order_key ON raw.urap_metric_definitions USING btree (display_order)`
- `urap_metric_definitions_pkey` — `CREATE UNIQUE INDEX urap_metric_definitions_pkey ON raw.urap_metric_definitions USING btree (metric_code)`

### `raw.urap_metric_scores`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `ranking_row_id` | `bigint` | Hayır |  |
| `metric_code` | `text` | Hayır |  |
| `score` | `numeric(10,2)` | Hayır |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `urap_metric_scores_metric_code_fkey` | FOREIGN KEY | `FOREIGN KEY (metric_code) REFERENCES raw.urap_metric_definitions(metric_code)` |
| `urap_metric_scores_pkey` | PRIMARY KEY | `PRIMARY KEY (ranking_row_id, metric_code)` |
| `urap_metric_scores_ranking_row_id_fkey` | FOREIGN KEY | `FOREIGN KEY (ranking_row_id) REFERENCES raw.urap_ranking_rows(id) ON DELETE RESTRICT` |
| `urap_metric_scores_score_check` | CHECK | `CHECK (score >= 0::numeric)` |

**İndeksler**

- `urap_metric_scores_pkey` — `CREATE UNIQUE INDEX urap_metric_scores_pkey ON raw.urap_metric_scores USING btree (ranking_row_id, metric_code)`

### `raw.urap_ranking_groups`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `id` | `bigint` | Hayır | IDENTITY a |
| `code` | `text` | Hayır |  |
| `label` | `text` | Hayır |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `urap_ranking_groups_code_key` | UNIQUE | `UNIQUE (code)` |
| `urap_ranking_groups_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |

**İndeksler**

- `urap_ranking_groups_code_key` — `CREATE UNIQUE INDEX urap_ranking_groups_code_key ON raw.urap_ranking_groups USING btree (code)`
- `urap_ranking_groups_pkey` — `CREATE UNIQUE INDEX urap_ranking_groups_pkey ON raw.urap_ranking_groups USING btree (id)`

### `raw.urap_ranking_rows`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `id` | `bigint` | Hayır | IDENTITY a |
| `edition_id` | `bigint` | Hayır |  |
| `group_id` | `bigint` | Hayır |  |
| `source_artifact_id` | `bigint` | Hayır |  |
| `source_page` | `integer` | Hayır |  |
| `source_rank` | `integer` | Hayır |  |
| `university_name` | `text` | Hayır |  |
| `city` | `text` | Hayır |  |
| `total_score` | `numeric(10,2)` | Hayır |  |
| `extraction_score_delta` | `numeric(7,2)` | Evet |  |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `urap_ranking_rows_city_check` | CHECK | `CHECK (length(TRIM(BOTH FROM city)) > 0)` |
| `urap_ranking_rows_edition_id_fkey` | FOREIGN KEY | `FOREIGN KEY (edition_id) REFERENCES raw.urap_editions(id)` |
| `urap_ranking_rows_group_id_fkey` | FOREIGN KEY | `FOREIGN KEY (group_id) REFERENCES raw.urap_ranking_groups(id)` |
| `urap_ranking_rows_pkey` | PRIMARY KEY | `PRIMARY KEY (id)` |
| `urap_ranking_rows_source_artifact_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_artifact_id) REFERENCES raw.urap_artifacts(id)` |
| `urap_ranking_rows_source_page_check` | CHECK | `CHECK (source_page > 0)` |
| `urap_ranking_rows_source_rank_check` | CHECK | `CHECK (source_rank > 0)` |
| `urap_ranking_rows_total_score_check` | CHECK | `CHECK (total_score >= 0::numeric)` |
| `urap_ranking_rows_university_name_check` | CHECK | `CHECK (length(TRIM(BOTH FROM university_name)) > 0)` |
| `urap_rows_unique_artifact_rank` | UNIQUE | `UNIQUE (source_artifact_id, group_id, source_rank)` |
| `urap_rows_unique_rank` | UNIQUE | `UNIQUE (edition_id, group_id, source_rank)` |

**İndeksler**

- `urap_ranking_rows_pkey` — `CREATE UNIQUE INDEX urap_ranking_rows_pkey ON raw.urap_ranking_rows USING btree (id)`
- `urap_rows_source_name_idx` — `CREATE INDEX urap_rows_source_name_idx ON raw.urap_ranking_rows USING btree (university_name)`
- `urap_rows_unique_artifact_rank` — `CREATE UNIQUE INDEX urap_rows_unique_artifact_rank ON raw.urap_ranking_rows USING btree (source_artifact_id, group_id, source_rank)`
- `urap_rows_unique_rank` — `CREATE UNIQUE INDEX urap_rows_unique_rank ON raw.urap_ranking_rows USING btree (edition_id, group_id, source_rank)`


## `staging` şeması

### `staging.cities`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `staging_id` | `bigint` | Hayır | IDENTITY a |
| `source_record_id` | `bigint` | Hayır |  |
| `il_adi` | `text` | Evet |  |
| `il_kodu` | `bigint` | Evet |  |
| `source_payload` | `jsonb` | Hayır |  |
| `staged_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `cities_pkey` | PRIMARY KEY | `PRIMARY KEY (staging_id)` |
| `cities_source_record_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id)` |
| `cities_source_record_id_key` | UNIQUE | `UNIQUE (source_record_id)` |

**İndeksler**

- `cities_pkey` — `CREATE UNIQUE INDEX cities_pkey ON staging.cities USING btree (staging_id)`
- `cities_source_record_id_key` — `CREATE UNIQUE INDEX cities_source_record_id_key ON staging.cities USING btree (source_record_id)`

### `staging.net_results`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `staging_id` | `bigint` | Hayır | IDENTITY a |
| `source_record_id` | `bigint` | Hayır |  |
| `ayt_bio_net` | `double precision` | Evet |  |
| `ayt_cog1_net` | `double precision` | Evet |  |
| `ayt_cog2_net` | `double precision` | Evet |  |
| `ayt_din_net` | `double precision` | Evet |  |
| `ayt_fel_net` | `double precision` | Evet |  |
| `ayt_fiz_net` | `double precision` | Evet |  |
| `ayt_kim_net` | `double precision` | Evet |  |
| `ayt_mat_net` | `double precision` | Evet |  |
| `ayt_tde_net` | `double precision` | Evet |  |
| `ayt_trh1_net` | `double precision` | Evet |  |
| `ayt_trh2_net` | `double precision` | Evet |  |
| `birim_adi` | `text` | Evet |  |
| `birim_grup_adi` | `text` | Evet |  |
| `birim_grup_id` | `bigint` | Evet |  |
| `birim_id` | `bigint` | Evet |  |
| `birim_turu_adi` | `text` | Evet |  |
| `birim_turu_id` | `bigint` | Evet |  |
| `katsayi` | `double precision` | Evet |  |
| `kilavuz_kodu` | `bigint` | Evet |  |
| `obp` | `double precision` | Evet |  |
| `puan_turu` | `text` | Evet |  |
| `taban_puan` | `double precision` | Evet |  |
| `tyt_fen_net` | `double precision` | Evet |  |
| `tyt_mat_net` | `double precision` | Evet |  |
| `tyt_sos_net` | `double precision` | Evet |  |
| `tyt_trk_net` | `double precision` | Evet |  |
| `universite_adi` | `text` | Evet |  |
| `universite_id` | `bigint` | Evet |  |
| `universite_turu` | `text` | Evet |  |
| `ydt_ydil_net` | `double precision` | Evet |  |
| `yil` | `bigint` | Evet |  |
| `source_payload` | `jsonb` | Hayır |  |
| `staged_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `net_results_pkey` | PRIMARY KEY | `PRIMARY KEY (staging_id)` |
| `net_results_source_record_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id)` |
| `net_results_source_record_id_key` | UNIQUE | `UNIQUE (source_record_id)` |

**İndeksler**

- `net_results_pkey` — `CREATE UNIQUE INDEX net_results_pkey ON staging.net_results USING btree (staging_id)`
- `net_results_source_record_id_key` — `CREATE UNIQUE INDEX net_results_source_record_id_key ON staging.net_results USING btree (source_record_id)`

### `staging.program_groups`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `staging_id` | `bigint` | Hayır | IDENTITY a |
| `source_record_id` | `bigint` | Hayır |  |
| `birim_grup_adi` | `text` | Evet |  |
| `birim_grup_id` | `bigint` | Evet |  |
| `puan_turu` | `text` | Evet |  |
| `source_payload` | `jsonb` | Hayır |  |
| `staged_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `program_groups_pkey` | PRIMARY KEY | `PRIMARY KEY (staging_id)` |
| `program_groups_source_record_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id)` |
| `program_groups_source_record_id_key` | UNIQUE | `UNIQUE (source_record_id)` |

**İndeksler**

- `program_groups_pkey` — `CREATE UNIQUE INDEX program_groups_pkey ON staging.program_groups USING btree (staging_id)`
- `program_groups_source_record_id_key` — `CREATE UNIQUE INDEX program_groups_source_record_id_key ON staging.program_groups USING btree (source_record_id)`

### `staging.programs`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `staging_id` | `bigint` | Hayır | IDENTITY a |
| `source_record_id` | `bigint` | Hayır |  |
| `abayp` | `text` | Evet |  |
| `akreditasyon` | `text` | Evet |  |
| `akreditasyon_ack` | `text` | Evet |  |
| `ar_gor` | `bigint` | Evet |  |
| `basari_sirasi` | `bigint` | Evet |  |
| `basari_sirasi1` | `bigint` | Evet |  |
| `basari_sirasi2` | `bigint` | Evet |  |
| `basari_sirasi3` | `bigint` | Evet |  |
| `birim_adi` | `text` | Evet |  |
| `birim_ek_turu` | `text` | Evet |  |
| `birim_grup_adi` | `text` | Evet |  |
| `birim_grup_id` | `bigint` | Evet |  |
| `birim_hiyerarsi` | `text` | Evet |  |
| `birim_id` | `bigint` | Evet |  |
| `birim_turu_adi` | `text` | Evet |  |
| `birim_turu_id` | `bigint` | Evet |  |
| `burs_orani_adi` | `text` | Evet |  |
| `burs_orani_id` | `bigint` | Evet |  |
| `doc` | `bigint` | Evet |  |
| `donem` | `text` | Evet |  |
| `dou` | `bigint` | Evet |  |
| `dprm_y` | `bigint` | Evet |  |
| `dus` | `text` | Evet |  |
| `eski_birim_id` | `bigint` | Evet |  |
| `eski_kilavuz_kodu` | `bigint` | Evet |  |
| `fymk_adi` | `text` | Evet |  |
| `fymk_id` | `bigint` | Evet |  |
| `fymk_il_adi` | `text` | Evet |  |
| `fymk_il_kodu` | `bigint` | Evet |  |
| `fymk_ilce_adi` | `text` | Evet |  |
| `fymk_ilce_kodu` | `bigint` | Evet |  |
| `gk1` | `bigint` | Evet |  |
| `gk2` | `bigint` | Evet |  |
| `gk3` | `bigint` | Evet |  |
| `gk_y` | `bigint` | Evet |  |
| `il_adi` | `text` | Evet |  |
| `il_kodu` | `bigint` | Evet |  |
| `ilce_adi` | `text` | Evet |  |
| `ilce_kodu` | `bigint` | Evet |  |
| `kil_aciklama` | `text` | Evet |  |
| `kilavuz_kodu` | `bigint` | Evet |  |
| `kontenjan` | `bigint` | Evet |  |
| `kontenjan_meb` | `bigint` | Evet |  |
| `kontenjan_obs` | `bigint` | Evet |  |
| `kontenjan_sgy` | `bigint` | Evet |  |
| `kontenjan_y34` | `bigint` | Evet |  |
| `kosul` | `text` | Evet |  |
| `kosul_list` | `jsonb` | Evet |  |
| `kpss1` | `text` | Evet |  |
| `min_basari_sirasi` | `text` | Evet |  |
| `min_basari_sirasi_kosul` | `text` | Evet |  |
| `min_puan` | `double precision` | Evet |  |
| `min_puan1` | `text` | Evet |  |
| `min_puan2` | `text` | Evet |  |
| `min_puan3` | `text` | Evet |  |
| `obk_y` | `bigint` | Evet |  |
| `ogr_gor` | `bigint` | Evet |  |
| `ogrenim_dili_adi` | `text` | Evet |  |
| `ogrenim_dili_id` | `bigint` | Evet |  |
| `ogrenim_suresi` | `bigint` | Evet |  |
| `ogrenim_turu_adi` | `text` | Evet |  |
| `ogrenim_turu_id` | `bigint` | Evet |  |
| `osym_kilavuz_id` | `bigint` | Evet |  |
| `prof` | `bigint` | Evet |  |
| `puan_turu` | `text` | Evet |  |
| `sgy_y` | `bigint` | Evet |  |
| `sinav` | `text` | Evet |  |
| `tablo_turu` | `text` | Evet |  |
| `tam_burs_birim_id` | `bigint` | Evet |  |
| `tusktp` | `text` | Evet |  |
| `tustt1` | `text` | Evet |  |
| `tustt2` | `text` | Evet |  |
| `tyc` | `text` | Evet |  |
| `ucret` | `bigint` | Evet |  |
| `uni_akreditasyon` | `text` | Evet |  |
| `uni_il_adi` | `text` | Evet |  |
| `uni_il_kodu` | `bigint` | Evet |  |
| `uni_ilce_adi` | `text` | Evet |  |
| `uni_ilce_kodu` | `bigint` | Evet |  |
| `uni_kil_aciklama` | `text` | Evet |  |
| `universite_adi` | `text` | Evet |  |
| `universite_id` | `bigint` | Evet |  |
| `universite_turu` | `text` | Evet |  |
| `uygulamali_egitim_modeli` | `text` | Evet |  |
| `y34` | `bigint` | Evet |  |
| `yil` | `bigint` | Evet |  |
| `source_payload` | `jsonb` | Hayır |  |
| `staged_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `programs_pkey` | PRIMARY KEY | `PRIMARY KEY (staging_id)` |
| `programs_source_record_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id)` |
| `programs_source_record_id_key` | UNIQUE | `UNIQUE (source_record_id)` |

**İndeksler**

- `programs_pkey` — `CREATE UNIQUE INDEX programs_pkey ON staging.programs USING btree (staging_id)`
- `programs_source_record_id_key` — `CREATE UNIQUE INDEX programs_source_record_id_key ON staging.programs USING btree (source_record_id)`

### `staging.universities`

**Tür:** TABLE

| Kolon | PostgreSQL veri tipi | Null olabilir | Varsayılan / Kimlik |
|---|---|---|---|
| `staging_id` | `bigint` | Hayır | IDENTITY a |
| `source_record_id` | `bigint` | Hayır |  |
| `universite_adi` | `text` | Evet |  |
| `universite_id` | `bigint` | Evet |  |
| `source_payload` | `jsonb` | Hayır |  |
| `staged_at` | `timestamp with time zone` | Hayır | now() |

**Kısıtlar ve ilişkiler**

| Kısıt | Tür | Tanım |
|---|---|---|
| `universities_pkey` | PRIMARY KEY | `PRIMARY KEY (staging_id)` |
| `universities_source_record_id_fkey` | FOREIGN KEY | `FOREIGN KEY (source_record_id) REFERENCES raw.source_records(source_record_id)` |
| `universities_source_record_id_key` | UNIQUE | `UNIQUE (source_record_id)` |

**İndeksler**

- `universities_pkey` — `CREATE UNIQUE INDEX universities_pkey ON staging.universities USING btree (staging_id)`
- `universities_source_record_id_key` — `CREATE UNIQUE INDEX universities_source_record_id_key ON staging.universities USING btree (source_record_id)`


## Notlar

- Bu çıktı **şema envanteridir**; tablo kayıtlarını ve satır sayısını içermez.
- İleri düzey nesneler (fonksiyonlar, trigger gövdeleri, roller, grants, extension kurulumları vb.) bu rapora dahil değildir.
- Tam yeniden oluşturulabilir bir şema yedeği için ayrıca `pg_dump --schema-only` kullanılmalıdır.
