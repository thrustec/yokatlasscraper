# TÜİK RAW metadata — mevcut PostgreSQL'e uyarlama raporu

**İncelenen kaynaklar:** `database_schema.sql`, `raw_schema.sql`, `manifest.json`, `dataflow_dsd_map.csv`, `dsd_dimensions.csv`, `dsd_attributes.csv`, `dsd_codelist_codes.csv`, `dsd_key_templates.csv`, `tuik_full_catalog.csv`.

## Mevcut veritabanı

- PostgreSQL 17.11 şema dökümü.
- Şemalar: `analytics`, `api`, `core`, `ops`, `quality`, `raw`, `staging`.
- RAW içinde `ingestion_runs`, `api_responses`, `source_records`, SEGE ve URAP kaynak tabloları bulunuyor.
- `staging.tuik_population_by_province` zaten mevcut. Bu bir RAW metadata tablosu değildir; silinmemeli veya yeniden adlandırılmamalı.
- Mevcut RAW tablo adları ile önerilen dokuz `raw.tuik_*` metadata tablosu çakışmıyor.
- Yalnızca SQL dump üzerinden projenin migration aracını kesin olarak belirlemek mümkün değil. Migration dosyası adını ve yürütme sırasını backend sorumlusu belirlemeli.

## Doğrulanan metadata envanteri

| Varlık | Adet |
| --- | ---: |
| Dataflow | 508 |
| Benzersiz DSD kimliği | 61 |
| Sürümlü DSD | 65 |
| DSD boyut satırı | 750 |
| DSD attribute satırı | 379 |
| Benzersiz codelist sürümü | 366 |
| Benzersiz codelist-kod birleşimi | 64.709 |
| DSD-codelist bağlantısı | 1.032 |
| DSD anahtar şablonu | 65 |

Kaynak kod CSV'sinde 208.603 satır vardır. Aynı kodların farklı DSD'lerde tekrar kullanılması normaldir. Tekilleştirme anahtarı `(codelist_agency, codelist_id, codelist_version, code)` ve mevcut dosyada çelişkili etiket/üst kod gözlenmedi.

## Oluşturulan dosyalar

- `tuik_raw_metadata_compatible.sql`: `raw` içinde dokuz TÜİK metadata tablosu açan *öneri* migration. Kaynak veri indirmez. Mevcut tabloya DROP/ALTER uygulamaz. Repo migration standardı ve veritabanı yetkileri kontrolünden sonra uygulanmalı.
- `tuik_raw_metadata_loader.py`: 65/65 DSD tamamlanmadan yüklemeyen, dosya tutarlılığı kontrolü yapan, idempotent UPSERT kullanan ve tek işlemde tamamlayan yükleyici. Varsayılan çalıştırma gerçek bağlantı gerektirir; `--check-only` yalnızca dosyaları denetler.

## Uygulama sırası

1. Backend geliştiricisi yeni branch açar ve mevcut migration mekanizmasında `tuik_raw_metadata_compatible.sql` içeriğini ayrı migration olarak kaydeder.
2. Migration'ı staging/test veritabanında uygular.
3. Veri CSV'leri ve tam katalog aynı dizin düzeninde sunucuya aktarılır; API key/token aktarılmaz.
4. Yükleyiciyi önce `--check-only` ile çalıştırır.
5. Sonra test veritabanı bağlantısıyla gerçek metadata aktarımını yapar.
6. Sayıları ve foreign key bütünlüğünü doğrulayıp prod migration ve yüklemeyi kontrollü yürütür.

### Örnek çalıştırma (depo kökünden)

```bash
python scripts/database/tuik_raw_metadata_loader.py \
  --data-dir data/tuik_discovery/all_dsd \
  --catalog data/tuik_discovery/tuik_full_catalog.csv \
  --check-only
```

Bağlantı ve aktarım için `pip install 'psycopg[binary]'` gerekir. Parolayı komuta gömmek yerine PostgreSQL'in `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` ortam değişkenlerini veya güvenli secret yönetimini kullanın. Gerçek aktarım için `--check-only` kaldırılır.

### Post-load kontrol SQL'i

```sql
SELECT 'dataflow' AS entity, count(*) FROM raw.tuik_dataflow
UNION ALL SELECT 'dsd', count(*) FROM raw.tuik_dsd
UNION ALL SELECT 'dimension', count(*) FROM raw.tuik_dsd_dimension
UNION ALL SELECT 'attribute', count(*) FROM raw.tuik_dsd_attribute
UNION ALL SELECT 'codelist', count(*) FROM raw.tuik_codelist
UNION ALL SELECT 'code', count(*) FROM raw.tuik_codelist_code
UNION ALL SELECT 'dsd_codelist', count(*) FROM raw.tuik_dsd_codelist
UNION ALL SELECT 'key_template', count(*) FROM raw.tuik_key_template;
```

## Sınırlar

- Anahtar şablonları olası SDMX sorgu sözdizimidir; **doğrulanmış seriler değildir**.
- `raw.tuik_observed_series_key` şimdilik boş kalır. Buna scraper'ın gözlem kanıtı eklemesi gerekir.
- `raw.tuik_observations` bu migration'da oluşturulmaz; kullanıcının görevi veri indirmek veya analiz etmek değildir.
- Kod listesi açıklamaları source-faithful saklanır. Özel üniversite/program eşleştirmeleri sonraki ETL aşamasının işidir.
- Mevcut dump'ta veri satırları olmadığı için veri tabanının mevcut içerik hacmi veya migration geçmişi doğrulanamaz.
- SQL ve Python dosyaları **canlı PostgreSQL'e karşı test edilmedi**. Yalnızca Python sözdizimi ve dosya bazlı check-only çalıştırması doğrulandı.
