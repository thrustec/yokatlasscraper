# Backend / Frontend integration agreement

## Connection
Backend user `atlas_api` (password: `ATLAS_API_PASSWORD`) reads **only `api` schema**. On the host: `127.0.0.1:5433`, DB `yokatlas_intelligence`. In Compose same network: host `postgres`, port `5432`. Never expose DB secrets in React/Next.js browser code.

## Published SQL interface
`api.universities`, `api.cities`, `api.program_groups`, `api.program_catalog`, `api.net_results`, `api.program_year_summary`, `api.net_year_summary`, `api.data_coverage`, `api.tuik_population_by_province`.

Sample backend SQL: `SELECT * FROM api.program_catalog WHERE yil=$1 AND puan_turu=$2 ORDER BY basari_sirasi NULLS LAST LIMIT $3`.

TÜİK population context: `SELECT il_kodu, il_adi, yas_grubu, cinsiyet, nufus FROM api.tuik_population_by_province WHERE yil=$1 AND yas_grubu_kodu=$2 AND cinsiyet_kodu=$3 ORDER BY il_kodu`. The 2025 sample uses five-year age groups and maps TÜİK's İBBS-3 province codes to `core.cities.il_kodu`.

## Contract caveats
- Program data year 2026 in current archive; net data years 2023–2025. Joining on `(kilavuz_kodu,yil)` in a future year is valid only after same-year program records are ingested and verified.
- `program_groups` has composite key `(birim_grup_id, puan_turu)`; `net_results` natural key `(kilavuz_kodu,yil,puan_turu)` after dedup.
- `api.program_catalog` intentionally only exposes a safe core projection; raw and all other source attributes remain in `staging.programs.source_payload`. Ask the schema owner to add versioned views when needed.
- Views will return empty sets until data is loaded by the archive importer or a future ETL bot.
