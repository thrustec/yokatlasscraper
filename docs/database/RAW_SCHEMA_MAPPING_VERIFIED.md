# CANLI DOĞRULANMIŞ RAW MAPPING — 22 Ekim 2026

**Durum: PostgreSQL üretim kataloğuyla karşılaştırıldı.** 59 tablo, 470 kolon, 271 constraint, 24 etkin trigger, 125 indeks. Önceki mapping ile aynı 470 kolon ve aynı 24 trigger bulunmaktadır. 14 salt gösterim farkı (9 `timestamptz` adı ve 4 metin DEFAULT cast'i dahil; ayrıntılar karşılaştırma raporunda) canlı katalogdaki gösterime uyarlanmıştır.

**Kesinlik sınırı:** Tablo/kolon/SQL tipi/nullable/default/identity, constraint, trigger ve indeksler canlı katalogdan doğrulanmıştır. Kolonların Türkçe iş açıklamaları önceki sözlükteki açıklamalardır; PostgreSQL'de yalnızca 3 kolonun COMMENT değeri vardır. Bu iş açıklamalarını verinin kaynak sözleşmesiyle kontrol edin. Trigger'lar otomatik ID üretmez; 24 adet `GENERATED ALWAYS AS IDENTITY` kolonunu INSERT'ten çıkarın. FK kimliklerini ilgili üst INSERT'in `RETURNING` sonucundan bağlayın. `DEFAULT` olan alanlara açıkça NULL göndermek DEFAULT'u çalıştırmaz.

**Veri güvenliği:** `raw.source_artifact` orijinal byte saklama noktasını oluşturur. `source_fetch` içinde hassas HTTP başlıklarını ve URL parametrelerini temizleyin. Append-only trigger'lı tablolarda UPDATE/DELETE yasaktır. PostgreSQL katalog kontrolü scraper'ın kaynak URL ve alan kapsamını doğrulamaz.

---

# RAW kolon sözlüğü (iş açıklamaları) 

**Kaynak anlık görüntüsü:** `yokatlas_schema_2.sql` + üretimde uygulandığı bildirilen `001–004` RAW migration’ları + `005` TÜİK migration’ı (22 Ekim 2026). Bu doküman canlı PostgreSQL kataloğuna doğrudan bağlanılarak alınmış bir dump **değildir**. Sunucuda sonradan elle yapılan DDL değişiklikleri için `LIVE_RAW_CATALOG_READONLY.sql` ile karşılaştırın.

**Kapsam:** 59 RAW tablo; 470 kolon. Yalnız `raw` şeması; `quality.tuik_dimension_code_issues` ayrıca anlatılmıştır.

## Scraper için kesin kurallar

1. **IDENTITY / GENERATED ALWAYS** alanına değer yazmayın. INSERT sırasında kolonu tamamen atlayın, gerekiyorsa `RETURNING` ile okuyun.
2. **DEFAULT** alanına uygulama açısından özel değer gerekmiyorsa değer vermeyin; `DEFAULT now()` kayıt zamanıdır, kaynakta yayımlanma zamanı değildir. `NULL` göndermek DEFAULT kullanımına eşdeğer değildir.
3. **PK/FK ve CHECK** kısıtlarını ihlal etmeyin. Özellikle composite FK’lerde ilgili kolonların tamamını aynı kaynak sürümünden kullanın. JSON alanlarının `jsonb` oluşu ham HTTP byte korunması anlamına gelmez.
4. **İlk olarak** `raw.source_fetch` ardından `raw.source_artifact` yazın; orijinal byte içeriği `body_bytes` veya güvenilir `storage_uri` ile saklayın (ikisi aynı anda değil). Hash/boyut uyumunu kontrol edin.
5. **Append-only** trigger’lı tablolarda UPDATE/DELETE çalıştırmayın. Yeni yayın ve revizyon için yeni kayıt ekleyin. Yeni ayrıştırma hatası görürseniz kaynak byte kaydını kaybetmeyin.
6. **TÜİK** için `tuik_observation` değerlerinin `agency_id, flow_id, flow_version` üçlüsü artifact’in fetch run kaydıyla eşleşmelidir; yanlış eşleşme `BEFORE INSERT/UPDATE` trigger’ıyla reddedilir. Beklenmeyen DSD kodlarını RAW’da koruyun; `quality.tuik_dimension_code_issues` üzerinden izleyin.
7. **Yazma izinleri:** Tercihen scraper üretim tablolarına doğrudan serbest INSERT/UPDATE yapmasın; backend tarafından belirlenmiş kontrollü yazma endpoint’leri / rolleri ile çalışsın. Bu sözlük, yetki bypass izni değildir.
8. **Mapping açıklamaları:** Tablo adı, kolon, tip, default ve identity SQL kaynaklarından çıkarılmıştır. Genel adlandırma üzerinden üretilen semantik açıklamalar kaynak/şema sahibince ayrıca doğrulanmalıdır; tanımda böyle alanlar açıkça işaretlidir.

## Kaynak → tablo özeti

- **OpenAlex** (21): `raw.openalex_authors`, `raw.openalex_authorship_institutions`, `raw.openalex_authorships`, `raw.openalex_entity_types`, `raw.openalex_funders`, `raw.openalex_institution_relationships`, `raw.openalex_institutions`, `raw.openalex_keywords`, `raw.openalex_object_snapshots`, `raw.openalex_reference_observations`, `raw.openalex_sources`, `raw.openalex_topics`, `raw.openalex_work_grants`, `raw.openalex_work_institutions`, `raw.openalex_work_keywords`, `raw.openalex_work_links`, `raw.openalex_work_locations`, `raw.openalex_work_observations`, `raw.openalex_work_sdgs`, `raw.openalex_work_topics`, `raw.openalex_works`
- **Ortak arşiv** (5): `raw.artifact_parse_events`, `raw.source_artifact`, `raw.source_artifact_verifications`, `raw.source_fetch`, `raw.source_records`
- **Ortak rapor** (1): `raw.report_documents`
- **SEGE** (7): `raw.sege_artifacts`, `raw.sege_editions`, `raw.sege_publication_releases`, `raw.sege_published_indicator_cells`, `raw.sege_ranking_observations`, `raw.sege_ranking_rows`, `raw.sege_release_artifacts`
- **TÜİK SDMX** (12): `raw.tuik_codelist`, `raw.tuik_codelist_code`, `raw.tuik_dataflow`, `raw.tuik_dsd`, `raw.tuik_dsd_attribute`, `raw.tuik_dsd_codelist`, `raw.tuik_dsd_dimension`, `raw.tuik_fetch_run`, `raw.tuik_key_template`, `raw.tuik_observation`, `raw.tuik_observed_series_key`, `raw.tuik_source_artifact`
- **URAP** (11): `raw.urap_artifacts`, `raw.urap_editions`, `raw.urap_metric_cells`, `raw.urap_metric_definitions`, `raw.urap_metric_scores`, `raw.urap_publication_releases`, `raw.urap_ranking_groups`, `raw.urap_ranking_observations`, `raw.urap_ranking_rows`, `raw.urap_release_artifacts`, `raw.urap_release_metrics`
- **YÖK Atlas/genel** (2): `raw.api_responses`, `raw.ingestion_runs`

## OpenAlex — 21 tablo

### `raw.openalex_authors`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 9.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `author_id` | `text` | Evet | — | PK/UNIQUE (tek kolon) | author kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `display_name` | `text` | Hayır | — | — | Kaynak/uygulama alanı: display name (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `orcid` | `text` | Hayır | — | — | Kaynak/uygulama alanı: orcid (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `works_count` | `bigint` | Hayır | — | — | Kaynak sayım değeri: works count; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `cited_by_count` | `bigint` | Hayır | — | — | Kaynak sayım değeri: cited by count; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_updated_date` | `timestamp with time zone` | Hayır | — | — | Kaynak/uygulama alanı: source updated date (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `api_response_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Kaynak API yanıtı kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_payload` | `jsonb` | Evet | — | — | Kaynağın ilgili nesneye ait JSON içeriği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `retrieved_at` | `timestamp with time zone` | Evet | `now()` | — | İçeriğin alındığı zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_authors_author_id_check CHECK ((author_id ~ '^https://openalex\.org/A[0-9]+$'::text))`
- `CONSTRAINT openalex_authors_source_payload_check CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- `openalex_authors_pkey: PRIMARY KEY (author_id)`
- `openalex_authors_api_response_id_fkey: FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_authors_orcid_idx`

### `raw.openalex_authorship_institutions`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 5.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `authorship_index` | `integer` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak/uygulama alanı: authorship index (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `institution_index` | `integer` | Evet | — | — | Kaynak/uygulama alanı: institution index (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `openalex_institution_id` | `text` | Hayır | — | — | openalex institution kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `raw_institution` | `jsonb` | Evet | — | — | Kaynak/uygulama alanı: raw institution (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_authorship_institutions_institution_index_check CHECK ((institution_index >= 0))`
- `CONSTRAINT openalex_authorship_institutions_raw_institution_check CHECK ((jsonb_typeof(raw_institution) = 'object'::text))`
- `openalex_authorship_institutions_pkey: PRIMARY KEY (work_id, authorship_index, institution_index)`
- `openalex_authorship_institutions_work_id_authorship_index_fkey: FOREIGN KEY (work_id, authorship_index) REFERENCES raw.openalex_authorships(work_id, authorship_index) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_authorship_inst_id_idx`

### `raw.openalex_authorships`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 7.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `authorship_index` | `integer` | Evet | — | — | Kaynak/uygulama alanı: authorship index (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `author_id` | `text` | Hayır | — | — | author kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `author_position` | `text` | Hayır | — | — | Kaynak/uygulama alanı: author position (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `is_corresponding` | `boolean` | Hayır | — | — | Kaynak/uygulama alanı: is corresponding (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `raw_author` | `jsonb` | Hayır | — | — | Kaynak/uygulama alanı: raw author (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `raw_authorship` | `jsonb` | Evet | — | — | Kaynak/uygulama alanı: raw authorship (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_authorships_authorship_index_check CHECK ((authorship_index >= 0))`
- `CONSTRAINT openalex_authorships_raw_authorship_check CHECK ((jsonb_typeof(raw_authorship) = 'object'::text))`
- `openalex_authorships_pkey: PRIMARY KEY (work_id, authorship_index)`
- `openalex_authorships_work_id_fkey: FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_authorships_author_idx`

### `raw.openalex_entity_types`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 3.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `entity_type` | `text` | Evet | — | PK | Kaynak/uygulama alanı: entity type (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `label` | `text` | Evet | — | — | Kaynak/uygulama alanı: label (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `added_at` | `timestamptz` | Evet | `now()` | — | added zaman damgası; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

### `raw.openalex_funders`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 8.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `funder_id` | `text` | Evet | — | PK/UNIQUE (tek kolon) | funder kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `display_name` | `text` | Hayır | — | — | Kaynak/uygulama alanı: display name (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `ror_id` | `text` | Hayır | — | — | ror kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `country_code` | `text` | Hayır | — | — | Kaynak kod alanı: country code; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_updated_date` | `timestamp with time zone` | Hayır | — | — | Kaynak/uygulama alanı: source updated date (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `api_response_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Kaynak API yanıtı kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_payload` | `jsonb` | Evet | — | — | Kaynağın ilgili nesneye ait JSON içeriği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `retrieved_at` | `timestamp with time zone` | Evet | `now()` | — | İçeriğin alındığı zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_funders_funder_id_check CHECK ((funder_id ~ '^https://openalex\.org/F[0-9]+$'::text))`
- `CONSTRAINT openalex_funders_source_payload_check CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- `openalex_funders_pkey: PRIMARY KEY (funder_id)`
- `openalex_funders_api_response_id_fkey: FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`

### `raw.openalex_institution_relationships`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 5.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `openalex_institution_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | openalex institution kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `relation_index` | `integer` | Evet | — | — | Kaynak/uygulama alanı: relation index (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `related_institution_id` | `text` | Hayır | — | — | related institution kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `relationship_type` | `text` | Hayır | — | — | Kaynak/uygulama alanı: relationship type (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `raw_relationship` | `jsonb` | Evet | — | — | Kaynak/uygulama alanı: raw relationship (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_institution_relationships_raw_relationship_check CHECK ((jsonb_typeof(raw_relationship) = 'object'::text))`
- `CONSTRAINT openalex_institution_relationships_relation_index_check CHECK ((relation_index >= 0))`
- `openalex_institution_relationships_pkey: PRIMARY KEY (openalex_institution_id, relation_index)`
- `openalex_institution_relationships_openalex_institution_id_fkey: FOREIGN KEY (openalex_institution_id) REFERENCES raw.openalex_institutions(openalex_institution_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_institution_relationships_related_idx`

### `raw.openalex_institutions`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 10.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `openalex_institution_id` | `text` | Evet | — | PK/UNIQUE (tek kolon) | openalex institution kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `display_name` | `text` | Evet | — | — | Kaynak/uygulama alanı: display name (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `ror_id` | `text` | Hayır | — | — | ror kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `country_code` | `text` | Hayır | — | — | Kaynak kod alanı: country code; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `institution_type` | `text` | Hayır | — | — | Kaynak/uygulama alanı: institution type (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `homepage_url` | `text` | Hayır | — | — | Kaynak/uygulama alanı: homepage url (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_updated_date` | `timestamp with time zone` | Hayır | — | — | Kaynak/uygulama alanı: source updated date (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `api_response_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Kaynak API yanıtı kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_payload` | `jsonb` | Evet | — | — | Kaynağın ilgili nesneye ait JSON içeriği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `retrieved_at` | `timestamp with time zone` | Evet | `now()` | — | İçeriğin alındığı zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_institutions_openalex_institution_id_check CHECK ((openalex_institution_id ~ '^https://openalex\.org/I[0-9]+$'::text))`
- `CONSTRAINT openalex_institutions_source_payload_check CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- `openalex_institutions_pkey: PRIMARY KEY (openalex_institution_id)`
- `openalex_institutions_api_response_id_fkey: FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_institutions_name_idx`, `openalex_institutions_ror_idx`

### `raw.openalex_keywords`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 6.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `keyword_id` | `text` | Evet | — | PK/UNIQUE (tek kolon) | keyword kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `display_name` | `text` | Evet | — | — | Kaynak/uygulama alanı: display name (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `description` | `text` | Hayır | — | — | Kaynak/uygulama alanı: description (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `api_response_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Kaynak API yanıtı kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_payload` | `jsonb` | Evet | — | — | Kaynağın ilgili nesneye ait JSON içeriği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `retrieved_at` | `timestamp with time zone` | Evet | `now()` | — | İçeriğin alındığı zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_keywords_source_payload_check CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- `openalex_keywords_pkey: PRIMARY KEY (keyword_id)`
- `openalex_keywords_api_response_id_fkey: FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`

### `raw.openalex_object_snapshots`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 8.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `snapshot_id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. OpenAlex kaynak nesne snapshot kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `entity_type` | `text` | Evet | — | — | Kaynak/uygulama alanı: entity type (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `openalex_id` | `text` | Evet | — | — | openalex kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `api_response_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak API yanıtı kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_array_index` | `integer` | Evet | `0` | — | Kaynak/uygulama alanı: source array index (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `captured_at` | `timestamp with time zone` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |
| `source_updated_date` | `timestamp with time zone` | Hayır | — | — | Kaynak/uygulama alanı: source updated date (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_payload` | `jsonb` | Evet | — | — | Kaynağın ilgili nesneye ait JSON içeriği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_object_snapshots_entity_type_check CHECK ((entity_type = ANY (ARRAY['institution'::text, 'work'::text, 'author'::text, 'source'::text, 'funder'::text, 'topic'::text, 'keyword'::text])))`
- `CONSTRAINT openalex_object_snapshots_source_array_index_check CHECK ((source_array_index >= 0))`
- `CONSTRAINT openalex_object_snapshots_source_payload_check CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- `openalex_object_snapshots_api_response_id_entity_type_sourc_key: UNIQUE (api_response_id, entity_type, source_array_index)`
- `openalex_object_snapshots_pkey: PRIMARY KEY (snapshot_id)`
- `openalex_object_snapshots_api_response_id_fkey: FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `openalex_object_snapshots_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

**Kaynak SQL indeksleri:** `openalex_object_snapshots_lookup_idx`

### `raw.openalex_reference_observations`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 8.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `reference_observation_id` | `bigint` | Evet | — | PK | **OTOMATİK ID — YAZMA**. reference observation kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **DB ÜRETİR — INSERT sırasında gönderme** |
| `snapshot_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | OpenAlex kaynak nesne snapshot kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `reference_path` | `text` | Evet | — | — | Kaynak nesnede referansın JSON yolu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `reference_index` | `integer` | Evet | `0` | — | Kaynak/uygulama alanı: reference index (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `target_type` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak/uygulama alanı: target type (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `target_openalex_id` | `text` | Hayır | — | — | target openalex kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_reference` | `jsonb` | Evet | — | — | Kaynak/uygulama alanı: source reference (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `captured_at` | `timestamptz` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `UNIQUE (snapshot_id,reference_path,reference_index)`
- `FOREIGN KEY (target_type) REFERENCES raw.openalex_entity_types(entity_type)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `openalex_reference_observations_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.openalex_sources`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 8.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `source_id` | `text` | Evet | — | PK/UNIQUE (tek kolon) | source kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `display_name` | `text` | Hayır | — | — | Kaynak/uygulama alanı: display name (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `issn_l` | `text` | Hayır | — | — | Kaynak/uygulama alanı: issn l (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_type` | `text` | Hayır | — | — | Kaynak/uygulama alanı: source type (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_updated_date` | `timestamp with time zone` | Hayır | — | — | Kaynak/uygulama alanı: source updated date (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `api_response_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Kaynak API yanıtı kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_payload` | `jsonb` | Evet | — | — | Kaynağın ilgili nesneye ait JSON içeriği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `retrieved_at` | `timestamp with time zone` | Evet | `now()` | — | İçeriğin alındığı zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_sources_source_id_check CHECK ((source_id ~ '^https://openalex\.org/S[0-9]+$'::text))`
- `CONSTRAINT openalex_sources_source_payload_check CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- `openalex_sources_pkey: PRIMARY KEY (source_id)`
- `openalex_sources_api_response_id_fkey: FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_sources_issn_l_idx`

### `raw.openalex_topics`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 11.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `topic_id` | `text` | Evet | — | PK/UNIQUE (tek kolon) | topic kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `display_name` | `text` | Evet | — | — | Kaynak/uygulama alanı: display name (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `subfield_id` | `text` | Hayır | — | — | subfield kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `subfield_name` | `text` | Hayır | — | — | Kaynak/uygulama alanı: subfield name (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `field_id` | `text` | Hayır | — | — | field kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `field_name` | `text` | Hayır | — | — | Kaynak/uygulama alanı: field name (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `domain_id` | `text` | Hayır | — | — | domain kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `domain_name` | `text` | Hayır | — | — | Kaynak/uygulama alanı: domain name (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `api_response_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Kaynak API yanıtı kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_payload` | `jsonb` | Evet | — | — | Kaynağın ilgili nesneye ait JSON içeriği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `retrieved_at` | `timestamp with time zone` | Evet | `now()` | — | İçeriğin alındığı zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_topics_source_payload_check CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- `CONSTRAINT openalex_topics_topic_id_check CHECK ((topic_id ~ '^https://openalex\.org/T[0-9]+$'::text))`
- `openalex_topics_pkey: PRIMARY KEY (topic_id)`
- `openalex_topics_api_response_id_fkey: FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_topics_field_idx`

### `raw.openalex_work_grants`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 6.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `grant_index` | `integer` | Evet | — | — | Kaynak/uygulama alanı: grant index (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `funder_id` | `text` | Hayır | — | — | funder kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `funder_display_name` | `text` | Hayır | — | — | Kaynak/uygulama alanı: funder display name (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `award_id` | `text` | Hayır | — | — | award kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `raw_grant` | `jsonb` | Evet | — | — | Kaynak/uygulama alanı: raw grant (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_work_grants_grant_index_check CHECK ((grant_index >= 0))`
- `CONSTRAINT openalex_work_grants_raw_grant_check CHECK ((jsonb_typeof(raw_grant) = 'object'::text))`
- `openalex_work_grants_pkey: PRIMARY KEY (work_id, grant_index)`
- `openalex_work_grants_work_id_fkey: FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_work_grants_funder_idx`

### `raw.openalex_work_institutions`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 2.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `openalex_institution_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | openalex institution kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `openalex_work_institutions_pkey: PRIMARY KEY (work_id, openalex_institution_id)`
- `openalex_work_institutions_openalex_institution_id_fkey: FOREIGN KEY (openalex_institution_id) REFERENCES raw.openalex_institutions(openalex_institution_id) ON DELETE RESTRICT`
- `openalex_work_institutions_work_id_fkey: FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_work_institutions_institution_idx`

### `raw.openalex_work_keywords`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 3.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `keyword_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | keyword kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `keyword_score` | `numeric` | Hayır | — | — | Kaynak/uygulama alanı: keyword score (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_work_keywords_keyword_score_check CHECK (((keyword_score IS NULL) OR ((keyword_score >= (0)::numeric) AND (keyword_score <= (1)::numeric))))`
- `openalex_work_keywords_pkey: PRIMARY KEY (work_id, keyword_id)`
- `openalex_work_keywords_keyword_id_fkey: FOREIGN KEY (keyword_id) REFERENCES raw.openalex_keywords(keyword_id) ON DELETE RESTRICT`
- `openalex_work_keywords_work_id_fkey: FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_work_keywords_keyword_idx`

### `raw.openalex_work_links`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 4.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `link_type` | `text` | Evet | — | — | Kaynak/uygulama alanı: link type (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `link_index` | `integer` | Evet | — | — | Kaynak/uygulama alanı: link index (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `linked_work_id` | `text` | Evet | — | — | linked work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_work_links_link_index_check CHECK ((link_index >= 0))`
- `CONSTRAINT openalex_work_links_link_type_check CHECK ((link_type = ANY (ARRAY['related_works'::text, 'referenced_works'::text])))`
- `openalex_work_links_pkey: PRIMARY KEY (work_id, link_type, link_index)`
- `openalex_work_links_work_id_fkey: FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_work_links_target_idx`

### `raw.openalex_work_locations`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 9.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `location_index` | `integer` | Evet | — | — | Kaynak/uygulama alanı: location index (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_id` | `text` | Hayır | — | — | source kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `landing_page_url` | `text` | Hayır | — | — | Kaynak/uygulama alanı: landing page url (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `pdf_url` | `text` | Hayır | — | — | Kaynak/uygulama alanı: pdf url (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `is_oa` | `boolean` | Hayır | — | — | Kaynak/uygulama alanı: is oa (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `is_accepted` | `boolean` | Hayır | — | — | Kaynak/uygulama alanı: is accepted (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `is_published` | `boolean` | Hayır | — | — | Kaynak/uygulama alanı: is published (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `raw_location` | `jsonb` | Evet | — | — | Kaynak/uygulama alanı: raw location (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_work_locations_location_index_check CHECK ((location_index >= 0))`
- `CONSTRAINT openalex_work_locations_raw_location_check CHECK ((jsonb_typeof(raw_location) = 'object'::text))`
- `openalex_work_locations_pkey: PRIMARY KEY (work_id, location_index)`
- `openalex_work_locations_work_id_fkey: FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_work_locations_source_idx`

### `raw.openalex_work_observations`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 8.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `observed_at` | `timestamp with time zone` | Evet | — | — | observed zaman damgası; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `ingestion_run_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Veri alma çalışması kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `cited_by_count` | `bigint` | Hayır | — | — | Kaynak sayım değeri: cited by count; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `fwci` | `numeric` | Hayır | — | — | Kaynak/uygulama alanı: fwci (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `top_10_percent` | `boolean` | Hayır | — | — | Kaynak/uygulama alanı: top 10 percent (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `is_oa` | `boolean` | Hayır | — | — | Kaynak/uygulama alanı: is oa (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `primary_topic_id` | `text` | Hayır | — | — | primary topic kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_work_observations_cited_by_count_check CHECK (((cited_by_count IS NULL) OR (cited_by_count >= 0)))`
- `openalex_work_observations_pkey: PRIMARY KEY (work_id, observed_at)`
- `openalex_work_observations_ingestion_run_id_fkey: FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id) ON DELETE RESTRICT`
- `openalex_work_observations_work_id_fkey: FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

### `raw.openalex_work_sdgs`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 5.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `sdg_index` | `integer` | Evet | — | — | Kaynak/uygulama alanı: sdg index (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `sdg_id` | `text` | Hayır | — | — | sdg kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `score` | `numeric` | Hayır | — | — | Kaynak/uygulama alanı: score (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `raw_sdg` | `jsonb` | Evet | — | — | Kaynak/uygulama alanı: raw sdg (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_work_sdgs_raw_sdg_check CHECK ((jsonb_typeof(raw_sdg) = 'object'::text))`
- `CONSTRAINT openalex_work_sdgs_sdg_index_check CHECK ((sdg_index >= 0))`
- `openalex_work_sdgs_pkey: PRIMARY KEY (work_id, sdg_index)`
- `openalex_work_sdgs_work_id_fkey: FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_work_sdgs_id_idx`

### `raw.openalex_work_topics`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 4.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `topic_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | topic kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `topic_score` | `numeric` | Hayır | — | — | Kaynak/uygulama alanı: topic score (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `is_primary` | `boolean` | Evet | `false` | — | Kaynak/uygulama alanı: is primary (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_work_topics_topic_score_check CHECK (((topic_score IS NULL) OR ((topic_score >= (0)::numeric) AND (topic_score <= (1)::numeric))))`
- `openalex_work_topics_pkey: PRIMARY KEY (work_id, topic_id)`
- `openalex_work_topics_topic_id_fkey: FOREIGN KEY (topic_id) REFERENCES raw.openalex_topics(topic_id) ON DELETE RESTRICT`
- `openalex_work_topics_work_id_fkey: FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_work_topics_topic_idx`

### `raw.openalex_works`

**Kullanım:** OpenAlex kaynak verisi. **Kolon sayısı:** 19.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `work_id` | `text` | Evet | — | PK/UNIQUE (tek kolon) | work kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `doi` | `text` | Hayır | — | — | Kaynak/uygulama alanı: doi (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `publication_year` | `integer` | Hayır | — | — | Kaynak/uygulama alanı: publication year (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `publication_date` | `date` | Hayır | — | — | Kaynak/uygulama alanı: publication date (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `work_type` | `text` | Hayır | — | — | Kaynak/uygulama alanı: work type (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `title` | `text` | Hayır | — | — | Kaynak/uygulama alanı: title (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `is_retracted` | `boolean` | Hayır | — | — | Kaynak/uygulama alanı: is retracted (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `is_oa` | `boolean` | Hayır | — | — | Kaynak/uygulama alanı: is oa (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `oa_status` | `text` | Hayır | — | — | Kaynak/uygulama alanı: oa status (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `oa_url` | `text` | Hayır | — | — | Kaynak/uygulama alanı: oa url (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `countries_distinct_count` | `integer` | Hayır | — | — | Kaynak sayım değeri: countries distinct count; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `cited_by_count` | `bigint` | Hayır | — | — | Kaynak sayım değeri: cited by count; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `fwci` | `numeric` | Hayır | — | — | Kaynak/uygulama alanı: fwci (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `top_10_percent` | `boolean` | Hayır | — | — | Kaynak/uygulama alanı: top 10 percent (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `primary_topic_id` | `text` | Hayır | — | — | primary topic kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_updated_date` | `timestamp with time zone` | Hayır | — | — | Kaynak/uygulama alanı: source updated date (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `api_response_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Kaynak API yanıtı kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_payload` | `jsonb` | Evet | — | — | Kaynağın ilgili nesneye ait JSON içeriği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `retrieved_at` | `timestamp with time zone` | Evet | `now()` | — | İçeriğin alındığı zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT openalex_works_cited_by_count_check CHECK (((cited_by_count IS NULL) OR (cited_by_count >= 0)))`
- `CONSTRAINT openalex_works_countries_distinct_count_check CHECK (((countries_distinct_count IS NULL) OR (countries_distinct_count >= 0)))`
- `CONSTRAINT openalex_works_publication_year_check CHECK (((publication_year IS NULL) OR ((publication_year >= 1000) AND (publication_year <= 2200))))`
- `CONSTRAINT openalex_works_source_payload_check CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- `CONSTRAINT openalex_works_work_id_check CHECK ((work_id ~ '^https://openalex\.org/W[0-9]+$'::text))`
- `openalex_works_pkey: PRIMARY KEY (work_id)`
- `openalex_works_api_response_id_fkey: FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`

**Kaynak SQL indeksleri:** `openalex_works_doi_idx`, `openalex_works_primary_topic_idx`, `openalex_works_year_type_idx`

## Ortak arşiv — 5 tablo

### `raw.artifact_parse_events`

**Kullanım:** Genel RAW kaynak arşivleme/izleme. **Kolon sayısı:** 8.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `parse_event_id` | `bigint` | Evet | — | PK | **OTOMATİK ID — YAZMA**. parse event kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **DB ÜRETİR — INSERT sırasında gönderme** |
| `artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak artifact kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `parser_name` | `text` | Evet | — | — | Kaynak/uygulama alanı: parser name (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `parser_version` | `text` | Evet | — | — | Ayrıştırıcı sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `parsed_at` | `timestamptz` | Evet | `now()` | — | parsed zaman damgası; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |
| `parse_status` | `text` | Evet | — | — | Kaynak/uygulama alanı: parse status (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `parsed_payload` | `jsonb` | Hayır | — | — | Kaynak/uygulama alanı: parsed payload (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `error_info` | `jsonb` | Evet | `'{}'::jsonb` | — | Kaynak/uygulama alanı: error info (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `artifact_parse_events_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.source_artifact`

**Kullanım:** Genel RAW kaynak arşivleme/izleme. **Kolon sayısı:** 10.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `artifact_id` | `bigint` | Evet | — | PK | **OTOMATİK ID — YAZMA**. Kaynak artifact kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `fetch_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak istek olayı kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `sha256_hex` | `text` | Evet | — | — | Orijinal byte içeriğinin SHA-256 özeti; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `byte_size` | `bigint` | Evet | — | — | İçerik uzunluğu, byte; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `mime_type` | `text` | Evet | — | — | Arşiv MIME türü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `content_encoding` | `text` | Hayır | — | — | Kaynak/uygulama alanı: content encoding (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `content_disposition_sanitized` | `text` | Hayır | — | — | Kaynak/uygulama alanı: content disposition sanitized (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `body_bytes` | `bytea` | Hayır | — | — | Orijinal HTTP/dosya byte içeriği; bytea; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `storage_uri` | `text` | Hayır | — | — | Orijinal byte içeriğinin harici değişmez depolama URI adresi; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `captured_at` | `timestamptz` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT source_artifact_exactly_one_storage_check CHECK ( (body_bytes IS NOT NULL) <> (storage_uri IS NOT NULL) )`
- `CONSTRAINT source_artifact_storage_uri_not_empty_check CHECK ( storage_uri IS NULL OR length(btrim(storage_uri)) > 0 )`
- `CONSTRAINT source_artifact_inline_integrity_check CHECK ( body_bytes IS NULL OR (octet_length(body_bytes) = byte_size AND encode(sha256(body_bytes),'hex') = sha256_hex) )`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `source_artifact_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.source_artifact_verifications`

**Kullanım:** Genel RAW kaynak arşivleme/izleme. **Kolon sayısı:** 8.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `verification_id` | `bigint` | Evet | — | PK | **OTOMATİK ID — YAZMA**. verification kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **DB ÜRETİR — INSERT sırasında gönderme** |
| `artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak artifact kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `verified_at` | `timestamptz` | Evet | `now()` | — | verified zaman damgası; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |
| `verifier_version` | `text` | Evet | — | — | Kaynak/uygulama alanı: verifier version (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `exists_at_storage` | `boolean` | Evet | — | — | Kaynak/uygulama alanı: exists at storage (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `observed_byte_size` | `bigint` | Hayır | — | — | Kaynak/uygulama alanı: observed byte size (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `observed_sha256_hex` | `text` | Hayır | — | — | Kaynak/uygulama alanı: observed sha256 hex (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `detail` | `jsonb` | Evet | `'{}'::jsonb` | — | Kaynak/uygulama alanı: detail (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `source_artifact_verifications_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.source_fetch`

**Kullanım:** Genel RAW kaynak arşivleme/izleme. **Kolon sayısı:** 13.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `fetch_id` | `bigint` | Evet | — | PK | **OTOMATİK ID — YAZMA**. Kaynak istek olayı kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `ingestion_run_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Veri alma çalışması kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_system` | `text` | Evet | — | — | Kaynak sistem kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `request_method` | `text` | Evet | — | — | Kaynak/uygulama alanı: request method (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `request_url_sanitized` | `text` | Evet | — | — | Gizli parametrelerden arındırılmış istek adresi; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `request_params_sanitized` | `jsonb` | Evet | `'{}'::jsonb` | — | Kaynak/uygulama alanı: request params sanitized (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `request_headers_sanitized` | `jsonb` | Evet | `'{}'::jsonb` | — | Gizli anahtarları çıkartılmış istek başlıkları; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `request_body_sha256` | `text` | Hayır | — | — | Kaynak/uygulama alanı: request body sha256 (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `response_status` | `integer` | Hayır | — | — | Kaynak/uygulama alanı: response status (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `response_headers_sanitized` | `jsonb` | Evet | `'{}'::jsonb` | — | Gizli başlıklardan arındırılmış yanıt başlıkları; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `captured_at` | `timestamptz` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |
| `source_release_hint` | `text` | Hayır | — | — | Kaynak/uygulama alanı: source release hint (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `error_metadata` | `jsonb` | Evet | `'{}'::jsonb` | — | Kaynak/uygulama alanı: error metadata (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT source_fetch_headers_secret_check CHECK ( NOT raw.has_sensitive_headers(request_headers_sanitized, ARRAY['authorization','cookie','x-api-key','proxy-authorization']) AND NOT raw.has_sensitive_headers(response_headers_sanitized, ARRAY['set-cookie','authorization','proxy-authenticate']) )`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `source_fetch_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.source_records`

**Kullanım:** Genel RAW kaynak arşivleme/izleme. **Kolon sayısı:** 6.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `source_record_id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. source record kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **DB ÜRETİR — INSERT sırasında gönderme** |
| `api_response_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak API yanıtı kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_entity` | `text` | Evet | — | — | Kaynak/uygulama alanı: source entity (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_array_index` | `integer` | Evet | — | — | Kaynak/uygulama alanı: source array index (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `record` | `jsonb` | Evet | — | — | Orijinal ayrıştırılmış kaynak kaydı JSON; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `record_hash_sha256` | `text` | Hayır | — | — | Kaynak/uygulama alanı: record hash sha256 (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT source_records_source_array_index_check CHECK ((source_array_index >= 0))`
- `source_records_api_response_id_source_entity_source_array_i_key: UNIQUE (api_response_id, source_entity, source_array_index)`
- `source_records_pkey: PRIMARY KEY (source_record_id)`
- `source_records_api_response_id_fkey: FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id)`

**Kaynak SQL indeksleri:** `idx_source_record_entity`, `idx_source_records_hash`

## Ortak rapor — 1 tablo

### `raw.report_documents`

**Kullanım:** Ortak rapor kaynak verisi. **Kolon sayısı:** 13.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `document_id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. document kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **DB ÜRETİR — INSERT sırasında gönderme** |
| `ingestion_run_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Veri alma çalışması kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `report_id` | `text` | Evet | — | — | report kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_system` | `text` | Evet | — | — | Kaynak sistem kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `edition` | `text` | Evet | — | — | Kaynak/uygulama alanı: edition (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_url` | `text` | Evet | — | — | Kaynak/uygulama alanı: source url (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `captured_at` | `timestamp with time zone` | Evet | — | — | Kaynağın arşivlendiği zaman; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_sha256` | `text` | Evet | — | — | Kaynak/uygulama alanı: source sha256 (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `parser_version` | `text` | Evet | — | — | Ayrıştırıcı sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `extracted_sha256` | `text` | Evet | — | — | Kaynak/uygulama alanı: extracted sha256 (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `archive_path` | `text` | Evet | — | — | Kaynak/uygulama alanı: archive path (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `payload` | `jsonb` | Evet | — | — | Kaynağın ayrıştırılmış JSON içeriği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_artifact_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Orijinal byte arşivi bağlantısı; **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT report_documents_extracted_sha256_check CHECK ((extracted_sha256 ~ '^[0-9a-f]{64}$'::text))`
- `CONSTRAINT report_documents_source_sha256_check CHECK ((source_sha256 ~ '^[0-9a-f]{64}$'::text))`
- `CONSTRAINT report_documents_source_system_check CHECK ((source_system = ANY (ARRAY['sege'::text, 'urap'::text])))`
- `report_documents_document_id_report_id_key: UNIQUE (document_id, report_id)`
- `report_documents_pkey: PRIMARY KEY (document_id)`
- `report_documents_report_id_source_sha256_parser_version_key: UNIQUE (report_id, source_sha256, parser_version)`
- `report_documents_ingestion_run_id_fkey: FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `report_artifact_source_check`: BEFORE INSERT OR UPDATE OF source_artifact_id → `raw.check_linked_artifact_source` — Yabancı kaynak/ilişki kontrolü; uyumsuz yazmayı reddeder.

## SEGE — 7 tablo

### `raw.sege_artifacts`

**Kullanım:** SEGE kaynak verisi. **Kolon sayısı:** 9.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Satır kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `sha256` | `character(64)` | Evet | — | PK/UNIQUE (tek kolon) | Artifact SHA-256 özeti; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_url` | `text` | Evet | — | — | Kaynak/uygulama alanı: source url (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `storage_uri` | `text` | Evet | — | — | Orijinal byte içeriğinin harici değişmez depolama URI adresi; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `content_type` | `text` | Evet | `'application/pdf'::text` | — | HTTP içerik türü; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `byte_size` | `bigint` | Evet | — | — | İçerik uzunluğu, byte; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `captured_at` | `timestamp with time zone` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |
| `parser_version` | `text` | Evet | — | — | Ayrıştırıcı sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_artifact_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Orijinal byte arşivi bağlantısı; **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT sege_artifacts_byte_size_check CHECK ((byte_size > 0))`
- `CONSTRAINT sege_artifacts_sha256_check CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text))`
- `CONSTRAINT sege_artifacts_storage_uri_check CHECK ((length(btrim(storage_uri)) > 0))`
- `sege_artifacts_pkey: PRIMARY KEY (id)`
- `sege_artifacts_sha256_key: UNIQUE (sha256)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `sege_artifact_source_check`: BEFORE INSERT OR UPDATE OF source_artifact_id → `raw.check_linked_artifact_source` — Yabancı kaynak/ilişki kontrolü; uyumsuz yazmayı reddeder.

### `raw.sege_editions`

**Kullanım:** SEGE kaynak verisi. **Kolon sayısı:** 7.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Satır kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `edition_year` | `integer` | Evet | — | — | Kaynak/uygulama alanı: edition year (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `geography_level` | `text` | Evet | — | — | Kaynak/uygulama alanı: geography level (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Orijinal byte arşivi bağlantısı; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `tier_method` | `text` | Evet | — | — | Kaynak/uygulama alanı: tier method (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_method_note` | `text` | Evet | — | — | Kaynak/uygulama alanı: source method note (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `imported_at` | `timestamp with time zone` | Evet | `now()` | — | imported zaman damgası; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT sege_editions_geography_level_check CHECK ((geography_level = ANY (ARRAY['PROVINCE'::text, 'DISTRICT'::text])))`
- `CONSTRAINT sege_editions_tier_method_check CHECK ((tier_method = ANY (ARRAY['EXTRACTED_FROM_SOURCE'::text, 'DERIVED_FROM_PUBLISHED_RANK_COUNTS'::text])))`
- `sege_editions_pkey: PRIMARY KEY (id)`
- `sege_editions_unique: UNIQUE (edition_year, geography_level)`
- `sege_editions_unique_artifact: UNIQUE (source_artifact_id, edition_year, geography_level)`
- `sege_editions_source_artifact_id_fkey: FOREIGN KEY (source_artifact_id) REFERENCES raw.sege_artifacts(id)`

### `raw.sege_publication_releases`

**Kullanım:** SEGE kaynak verisi. **Kolon sayısı:** 9.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `release_id` | `bigint` | Evet | — | PK | **OTOMATİK ID — YAZMA**. Yayımlanmış sürüm/revizyon kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `release_key` | `text` | Evet | — | — | Yayın sürümünün benzersiz anahtarı; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `edition_year` | `integer` | Evet | — | — | Kaynak/uygulama alanı: edition year (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `geography_level` | `text` | Evet | — | — | Kaynak/uygulama alanı: geography level (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `revision_label` | `text` | Evet | `'original'` | — | Kaynak/uygulama alanı: revision label (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `publication_date` | `date` | Hayır | — | — | Kaynak/uygulama alanı: publication date (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_method_note` | `text` | Hayır | — | — | Kaynak/uygulama alanı: source method note (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `release_metadata` | `jsonb` | Evet | `'{}'::jsonb` | — | Kaynak/uygulama alanı: release metadata (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `captured_at` | `timestamptz` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `sege_publication_releases_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.sege_published_indicator_cells`

**Kullanım:** SEGE kaynak verisi. **Kolon sayısı:** 6.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `observation_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak gözlem kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `indicator_code_raw` | `text` | Evet | — | — | Kaynak metni, dönüştürmeden koru: indicator code raw; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `indicator_label_raw` | `text` | Hayır | — | — | Kaynak metni, dönüştürmeden koru: indicator label raw; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `value_raw` | `text` | Hayır | — | — | Kaynak hücre değeri metni; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `value_numeric` | `numeric` | Hayır | — | — | Hücre değerinin sayısal karşılığı; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `unit_raw` | `text` | Hayır | — | — | Kaynak metni, dönüştürmeden koru: unit raw; **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `PRIMARY KEY (observation_id,indicator_code_raw)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `sege_published_indicator_cells_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.sege_ranking_observations`

**Kullanım:** SEGE kaynak verisi. **Kolon sayısı:** 17.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `observation_id` | `bigint` | Evet | — | PK | **OTOMATİK ID — YAZMA**. Kaynak gözlem kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `release_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Yayımlanmış sürüm/revizyon kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak artifact kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_table_key` | `text` | Evet | — | — | Kaynak anahtar/kod değeri: source table key; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_page` | `integer` | Hayır | — | — | Kaynak sayfa numarası; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `row_ordinal` | `integer` | Evet | — | — | Kaynak/uygulama alanı: row ordinal (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `geography_code_raw` | `text` | Hayır | — | — | Kaynak metni, dönüştürmeden koru: geography code raw; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `geography_name_raw` | `text` | Evet | — | — | Kaynak metni, dönüştürmeden koru: geography name raw; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `parent_geography_raw` | `text` | Hayır | — | — | Kaynak metni, dönüştürmeden koru: parent geography raw; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `rank_raw` | `text` | Hayır | — | — | Kaynak sıra değeri metni; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `rank_numeric` | `numeric` | Hayır | — | — | Sıra değerinin sayısal çıkarımı; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `score_raw` | `text` | Hayır | — | — | Kaynak metni, dönüştürmeden koru: score raw; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `score_numeric` | `numeric` | Hayır | — | — | Kaynak/uygulama alanı: score numeric (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `development_tier` | `smallint` | Hayır | — | — | Kaynak/uygulama alanı: development tier (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `tier_method` | `text` | Hayır | — | — | Kaynak/uygulama alanı: tier method (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `raw_row` | `jsonb` | Evet | — | — | Kaynak sıralama satırının tamamı JSON nesnesi; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `captured_at` | `timestamptz` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `UNIQUE (release_id,artifact_id,source_table_key,row_ordinal)`
- `FOREIGN KEY (release_id,artifact_id) REFERENCES raw.sege_release_artifacts(release_id,artifact_id) ON DELETE RESTRICT`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `sege_obs_tier_guard`: BEFORE INSERT OR UPDATE OF development_tier,release_id → `raw.check_sege_v2_tier` — Yabancı kaynak/ilişki kontrolü; uyumsuz yazmayı reddeder.
- `sege_ranking_observations_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.sege_ranking_rows`

**Kullanım:** SEGE kaynak verisi. **Kolon sayısı:** 10.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Satır kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `edition_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | edition kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Orijinal byte arşivi bağlantısı; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_page` | `integer` | Evet | — | — | Kaynak sayfa numarası; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_rank` | `integer` | Evet | — | — | Kaynak/uygulama alanı: source rank (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `province_name` | `text` | Evet | — | — | Kaynak/uygulama alanı: province name (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `district_name` | `text` | Hayır | — | — | Kaynak/uygulama alanı: district name (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `sege_score` | `numeric(12,3)` | Evet | — | — | Kaynak/uygulama alanı: sege score (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `development_tier` | `smallint` | Evet | — | — | Kaynak/uygulama alanı: development tier (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `tier_method` | `text` | Evet | — | — | Kaynak/uygulama alanı: tier method (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT sege_ranking_rows_development_tier_check CHECK (((development_tier >= 1) AND (development_tier <= 6)))`
- `CONSTRAINT sege_ranking_rows_district_name_check CHECK (((district_name IS NULL) OR (length(btrim(district_name)) > 0)))`
- `CONSTRAINT sege_ranking_rows_province_name_check CHECK ((length(btrim(province_name)) > 0))`
- `CONSTRAINT sege_ranking_rows_source_page_check CHECK ((source_page > 0))`
- `CONSTRAINT sege_ranking_rows_source_rank_check CHECK ((source_rank > 0))`
- `CONSTRAINT sege_ranking_rows_tier_method_check CHECK ((tier_method = ANY (ARRAY['EXTRACTED_FROM_SOURCE'::text, 'DERIVED_FROM_PUBLISHED_RANK_COUNTS'::text])))`
- `sege_ranking_rows_pkey: PRIMARY KEY (id)`
- `sege_rows_unique_rank: UNIQUE (edition_id, source_rank)`
- `sege_ranking_rows_edition_id_fkey: FOREIGN KEY (edition_id) REFERENCES raw.sege_editions(id)`
- `sege_ranking_rows_source_artifact_id_fkey: FOREIGN KEY (source_artifact_id) REFERENCES raw.sege_artifacts(id)`

**Kaynak SQL indeksleri:** `sege_rows_place_idx`

### `raw.sege_release_artifacts`

**Kullanım:** SEGE kaynak verisi. **Kolon sayısı:** 3.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `release_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Yayımlanmış sürüm/revizyon kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak artifact kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `artifact_role` | `text` | Evet | `'REPORT'` | — | Kaynak/uygulama alanı: artifact role (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `PRIMARY KEY (release_id,artifact_id)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `sege_release_artifact_source_guard`: BEFORE INSERT OR UPDATE OF artifact_id → `raw.guard_sege_release_artifact` — Yabancı kaynak/ilişki kontrolü; uyumsuz yazmayı reddeder.
- `sege_release_artifacts_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

## TÜİK SDMX — 12 tablo

### `raw.tuik_codelist`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 3.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `agency_id` | `text` | Evet | — | — | Veriyi yayımlayan kurum kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `codelist_id` | `text` | Evet | — | — | Kod listesi kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `codelist_version` | `text` | Evet | — | — | Kod listesi sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `tuik_codelist_pkey: PRIMARY KEY (agency_id, codelist_id, codelist_version)`

### `raw.tuik_codelist_code`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 7.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `agency_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Veriyi yayımlayan kurum kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `codelist_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kod listesi kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `codelist_version` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kod listesi sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `code` | `text` | Evet | — | — | Kod listesindeki kaynak kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `parent_code` | `text` | Hayır | — | — | Kaynak kod alanı: parent code; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `label_tr` | `text` | Hayır | — | — | Kaynak/uygulama alanı: label tr (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `label_en` | `text` | Hayır | — | — | Kaynak/uygulama alanı: label en (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `tuik_codelist_code_pkey: PRIMARY KEY (agency_id, codelist_id, codelist_version, code)`
- `tuik_codelist_code_agency_id_codelist_id_codelist_version_fkey: FOREIGN KEY (agency_id, codelist_id, codelist_version) REFERENCES raw.tuik_codelist(agency_id, codelist_id, codelist_version)`

### `raw.tuik_dataflow`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 9.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `agency_id` | `text` | Evet | — | — | Veriyi yayımlayan kurum kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `flow_id` | `text` | Evet | — | — | TÜİK SDMX dataflow kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `flow_version` | `text` | Evet | — | — | Dataflow sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `name_tr` | `text` | Hayır | — | — | Kaynak/uygulama alanı: name tr (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `name_en` | `text` | Hayır | — | — | Kaynak/uygulama alanı: name en (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `description_tr` | `text` | Hayır | — | — | Kaynak/uygulama alanı: description tr (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `dsd_agency_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | DSD kurum kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | SDMX veri yapısı kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_version` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | SDMX veri yapısı sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `tuik_dataflow_pkey: PRIMARY KEY (agency_id, flow_id, flow_version)`
- `tuik_dataflow_dsd_agency_id_dsd_id_dsd_version_fkey: FOREIGN KEY (dsd_agency_id, dsd_id, dsd_version) REFERENCES raw.tuik_dsd(agency_id, dsd_id, dsd_version)`

### `raw.tuik_dsd`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 6.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `agency_id` | `text` | Evet | — | — | Veriyi yayımlayan kurum kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_id` | `text` | Evet | — | — | SDMX veri yapısı kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_version` | `text` | Evet | — | — | SDMX veri yapısı sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `metadata_status` | `text` | Evet | `'ok'::text` | — | Kaynak/uygulama alanı: metadata status (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `source_sha256` | `character(64)` | Hayır | — | — | Kaynak/uygulama alanı: source sha256 (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `discovered_at` | `timestamp with time zone` | Hayır | — | — | discovered zaman damgası; **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `tuik_dsd_pkey: PRIMARY KEY (agency_id, dsd_id, dsd_version)`

### `raw.tuik_dsd_attribute`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 9.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `dsd_agency` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak/uygulama alanı: dsd agency (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | SDMX veri yapısı kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_version` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | SDMX veri yapısı sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `attribute_id` | `text` | Evet | — | — | attribute kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `attribute_kind` | `text` | Hayır | — | — | Kaynak/uygulama alanı: attribute kind (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `concept_id` | `text` | Hayır | — | — | concept kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `codelist_agency` | `text` | Hayır | — | FK (ayrıntı kısıtlarda) | Kaynak/uygulama alanı: codelist agency (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `codelist_id` | `text` | Hayır | — | FK (ayrıntı kısıtlarda) | Kod listesi kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `codelist_version` | `text` | Hayır | — | FK (ayrıntı kısıtlarda) | Kod listesi sürümü; **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `tuik_dsd_attribute_pkey: PRIMARY KEY (dsd_agency, dsd_id, dsd_version, attribute_id)`
- `tuik_dsd_attribute_codelist_agency_codelist_id_codelist_ve_fkey: FOREIGN KEY (codelist_agency, codelist_id, codelist_version) REFERENCES raw.tuik_codelist(agency_id, codelist_id, codelist_version)`
- `tuik_dsd_attribute_dsd_agency_dsd_id_dsd_version_fkey: FOREIGN KEY (dsd_agency, dsd_id, dsd_version) REFERENCES raw.tuik_dsd(agency_id, dsd_id, dsd_version)`

### `raw.tuik_dsd_codelist`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 6.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `dsd_agency` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak/uygulama alanı: dsd agency (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | SDMX veri yapısı kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_version` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | SDMX veri yapısı sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `codelist_agency` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak/uygulama alanı: codelist agency (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `codelist_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kod listesi kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `codelist_version` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kod listesi sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `tuik_dsd_codelist_pkey: PRIMARY KEY (dsd_agency, dsd_id, dsd_version, codelist_agency, codelist_id, codelist_version)`
- `tuik_dsd_codelist_codelist_agency_codelist_id_codelist_ver_fkey: FOREIGN KEY (codelist_agency, codelist_id, codelist_version) REFERENCES raw.tuik_codelist(agency_id, codelist_id, codelist_version)`
- `tuik_dsd_codelist_dsd_agency_dsd_id_dsd_version_fkey: FOREIGN KEY (dsd_agency, dsd_id, dsd_version) REFERENCES raw.tuik_dsd(agency_id, dsd_id, dsd_version)`

### `raw.tuik_dsd_dimension`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 11.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `dsd_agency` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak/uygulama alanı: dsd agency (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | SDMX veri yapısı kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_version` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | SDMX veri yapısı sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dimension_id` | `text` | Evet | — | — | dimension kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dimension_kind` | `text` | Evet | — | — | Kaynak/uygulama alanı: dimension kind (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_position` | `integer` | Hayır | — | — | Kaynak/uygulama alanı: source position (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `key_position` | `integer` | Hayır | — | — | Kaynak/uygulama alanı: key position (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `concept_id` | `text` | Hayır | — | — | concept kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `codelist_agency` | `text` | Hayır | — | FK (ayrıntı kısıtlarda) | Kaynak/uygulama alanı: codelist agency (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `codelist_id` | `text` | Hayır | — | FK (ayrıntı kısıtlarda) | Kod listesi kimliği; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `codelist_version` | `text` | Hayır | — | FK (ayrıntı kısıtlarda) | Kod listesi sürümü; **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT tuik_dsd_dimension_key_position_check CHECK (((key_position IS NULL) OR (key_position > 0)))`
- `tuik_dsd_dimension_pkey: PRIMARY KEY (dsd_agency, dsd_id, dsd_version, dimension_id)`
- `tuik_dsd_dimension_codelist_agency_codelist_id_codelist_ve_fkey: FOREIGN KEY (codelist_agency, codelist_id, codelist_version) REFERENCES raw.tuik_codelist(agency_id, codelist_id, codelist_version)`
- `tuik_dsd_dimension_dsd_agency_dsd_id_dsd_version_fkey: FOREIGN KEY (dsd_agency, dsd_id, dsd_version) REFERENCES raw.tuik_dsd(agency_id, dsd_id, dsd_version)`

**Kaynak SQL indeksleri:** `tuik_dsd_dimension_key_pos_uq`

### `raw.tuik_fetch_run`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 15.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `run_id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Toplama çalışması kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `agency_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Veriyi yayımlayan kurum kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `flow_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | TÜİK SDMX dataflow kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `flow_version` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Dataflow sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `request_url` | `text` | Evet | — | — | Kaynak/uygulama alanı: request url (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `requested_start_period` | `text` | Hayır | — | — | Kaynak/uygulama alanı: requested start period (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `requested_end_period` | `text` | Hayır | — | — | Kaynak/uygulama alanı: requested end period (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `requested_key` | `text` | Hayır | — | — | Kaynak anahtar/kod değeri: requested key; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `started_at` | `timestamp with time zone` | Evet | `now()` | — | started zaman damgası; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |
| `finished_at` | `timestamp with time zone` | Hayır | — | — | finished zaman damgası; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `status` | `text` | Evet | `'running'::text` | — | İşlem veya yayın durumu; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `http_status` | `integer` | Hayır | — | — | Kaynak/uygulama alanı: http status (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `error_code` | `text` | Hayır | — | — | Kaynak kod alanı: error code; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `error_message` | `text` | Hayır | — | — | Kaynak/uygulama alanı: error message (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `collector_version` | `text` | Hayır | — | — | Kaynak/uygulama alanı: collector version (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT tuik_fetch_run_check CHECK (((finished_at IS NULL) OR (finished_at >= started_at)))`
- `CONSTRAINT tuik_fetch_run_http_status_check CHECK (((http_status IS NULL) OR ((http_status >= 100) AND (http_status <= 599))))`
- `CONSTRAINT tuik_fetch_run_status_check CHECK ((status = ANY (ARRAY['running'::text, 'succeeded'::text, 'failed'::text, 'partial'::text, 'cancelled'::text])))`
- `tuik_fetch_run_pkey: PRIMARY KEY (run_id)`
- `tuik_fetch_run_dataflow_fk: FOREIGN KEY (agency_id, flow_id, flow_version) REFERENCES raw.tuik_dataflow(agency_id, flow_id, flow_version)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `tuik_fetch_flow_change_guard`: BEFORE UPDATE OF agency_id, flow_id, flow_version → `raw.tuik_guard_fetch_flow_change` — Yabancı kaynak/ilişki kontrolü; uyumsuz yazmayı reddeder.

**Kaynak SQL indeksleri:** `tuik_fetch_run_flow_started_idx`, `tuik_fetch_run_status_idx`

### `raw.tuik_key_template`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 7.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `dsd_agency` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak/uygulama alanı: dsd agency (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | SDMX veri yapısı kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dsd_version` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | SDMX veri yapısı sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `dimension_order` | `text` | Evet | — | — | Kaynak/uygulama alanı: dimension order (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `query_key_template` | `text` | Evet | — | — | Kaynak/uygulama alanı: query key template (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `template_kind` | `text` | Evet | `'structural_only'::text` | — | Kaynak/uygulama alanı: template kind (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `notes` | `text` | Hayır | — | — | Kaynak/uygulama alanı: notes (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT tuik_key_template_template_kind_check CHECK ((template_kind = 'structural_only'::text))`
- `tuik_key_template_pkey: PRIMARY KEY (dsd_agency, dsd_id, dsd_version)`
- `tuik_key_template_dsd_agency_dsd_id_dsd_version_fkey: FOREIGN KEY (dsd_agency, dsd_id, dsd_version) REFERENCES raw.tuik_dsd(agency_id, dsd_id, dsd_version)`

### `raw.tuik_observation`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 15.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `observation_id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Kaynak gözlem kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak artifact kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `agency_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Veriyi yayımlayan kurum kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `flow_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | TÜİK SDMX dataflow kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `flow_version` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Dataflow sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_ordinal` | `bigint` | Evet | — | — | Kaynak artifact içindeki gözlemin sıra numarası (1 tabanlı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `series_key` | `text` | Evet | — | — | Kaynağın seri anahtarı; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `time_period` | `text` | Evet | — | — | Kaynağın zaman dönemi metni; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `obs_value_raw` | `text` | Hayır | — | — | Kaynak gözlem değeri; dönüşüm yapmadan sakla; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `dimension_values` | `jsonb` | Evet | `'{}'::jsonb` | — | SDMX boyut kodlarının JSON nesnesi; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `observation_attributes` | `jsonb` | Evet | `'{}'::jsonb` | — | Gözleme ait SDMX özelliklerinin JSON nesnesi; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `series_attributes` | `jsonb` | Evet | `'{}'::jsonb` | — | Seriye ait SDMX özellikleri; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `dataset_attributes` | `jsonb` | Evet | `'{}'::jsonb` | — | Veri kümesi SDMX özellikleri; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `observation_status` | `text` | Hayır | — | — | Kaynak/uygulama alanı: observation status (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `ingested_at` | `timestamp with time zone` | Evet | `now()` | — | Gözlemin RAW’a yazıldığı zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT tuik_observation_dataset_attributes_check CHECK ((jsonb_typeof(dataset_attributes) = 'object'::text))`
- `CONSTRAINT tuik_observation_dimension_values_check CHECK ((jsonb_typeof(dimension_values) = 'object'::text))`
- `CONSTRAINT tuik_observation_observation_attributes_check CHECK ((jsonb_typeof(observation_attributes) = 'object'::text))`
- `CONSTRAINT tuik_observation_series_attributes_check CHECK ((jsonb_typeof(series_attributes) = 'object'::text))`
- `CONSTRAINT tuik_observation_series_key_check CHECK ((length(series_key) > 0))`
- `CONSTRAINT tuik_observation_source_ordinal_check CHECK ((source_ordinal > 0))`
- `CONSTRAINT tuik_observation_time_period_check CHECK ((length(time_period) > 0))`
- `tuik_observation_artifact_ordinal_uq: UNIQUE (artifact_id, source_ordinal)`
- `tuik_observation_pkey: PRIMARY KEY (observation_id)`
- `tuik_observation_artifact_id_fkey: FOREIGN KEY (artifact_id) REFERENCES raw.tuik_source_artifact(artifact_id)`
- `tuik_observation_dataflow_fk: FOREIGN KEY (agency_id, flow_id, flow_version) REFERENCES raw.tuik_dataflow(agency_id, flow_id, flow_version)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `tuik_observation_flow_guard`: BEFORE INSERT OR UPDATE OF artifact_id, agency_id, flow_id, flow_version → `raw.tuik_assert_observation_flow` — Yabancı kaynak/ilişki kontrolü; uyumsuz yazmayı reddeder.

**Kaynak SQL indeksleri:** `tuik_observation_artifact_idx`, `tuik_observation_flow_series_time_idx`

### `raw.tuik_observed_series_key`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 6.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `agency_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Veriyi yayımlayan kurum kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `flow_id` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | TÜİK SDMX dataflow kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `flow_version` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Dataflow sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `series_key` | `text` | Evet | — | — | Kaynağın seri anahtarı; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `observed_at` | `timestamp with time zone` | Evet | — | — | observed zaman damgası; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `evidence_sha256` | `character(64)` | Evet | — | — | Kaynak/uygulama alanı: evidence sha256 (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `tuik_observed_series_key_pkey: PRIMARY KEY (agency_id, flow_id, flow_version, series_key)`
- `tuik_observed_series_key_agency_id_flow_id_flow_version_fkey: FOREIGN KEY (agency_id, flow_id, flow_version) REFERENCES raw.tuik_dataflow(agency_id, flow_id, flow_version)`

### `raw.tuik_source_artifact`

**Kullanım:** TÜİK SDMX kaynak verisi. **Kolon sayısı:** 11.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `artifact_id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Kaynak artifact kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `run_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Toplama çalışması kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `artifact_kind` | `text` | Evet | `'sdmx_response'::text` | — | Kaynak/uygulama alanı: artifact kind (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `uri` | `text` | Hayır | — | — | Kaynak/uygulama alanı: uri (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `content_type` | `text` | Hayır | — | — | HTTP içerik türü; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `byte_size` | `bigint` | Hayır | — | — | İçerik uzunluğu, byte; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `sha256` | `character(64)` | Evet | — | — | Artifact SHA-256 özeti; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `retrieved_at` | `timestamp with time zone` | Evet | `now()` | — | İçeriğin alındığı zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |
| `source_etag` | `text` | Hayır | — | — | Kaynak/uygulama alanı: source etag (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_last_modified` | `text` | Hayır | — | — | Kaynak/uygulama alanı: source last modified (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `response_metadata` | `jsonb` | Evet | `'{}'::jsonb` | — | Kaynak/uygulama alanı: response metadata (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT tuik_source_artifact_artifact_kind_check CHECK ((artifact_kind = ANY (ARRAY['sdmx_response'::text, 'sdmx_chunk'::text, 'other'::text])))`
- `CONSTRAINT tuik_source_artifact_byte_size_check CHECK (((byte_size IS NULL) OR (byte_size >= 0)))`
- `CONSTRAINT tuik_source_artifact_response_metadata_check CHECK ((jsonb_typeof(response_metadata) = 'object'::text))`
- `CONSTRAINT tuik_source_artifact_sha256_check CHECK ((sha256 ~ '^[0-9a-fA-F]{64}$'::text))`
- `tuik_artifact_run_hash_uq: UNIQUE (run_id, sha256, artifact_kind)`
- `tuik_source_artifact_pkey: PRIMARY KEY (artifact_id)`
- `tuik_source_artifact_run_id_fkey: FOREIGN KEY (run_id) REFERENCES raw.tuik_fetch_run(run_id)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `tuik_artifact_reparent_guard`: BEFORE UPDATE OF run_id → `raw.tuik_guard_artifact_reparent` — Yabancı kaynak/ilişki kontrolü; uyumsuz yazmayı reddeder.

**Kaynak SQL indeksleri:** `tuik_source_artifact_sha_idx`

## URAP — 11 tablo

### `raw.urap_artifacts`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 10.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Satır kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `sha256` | `character(64)` | Evet | — | PK/UNIQUE (tek kolon) | Artifact SHA-256 özeti; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_url` | `text` | Evet | — | — | Kaynak/uygulama alanı: source url (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `storage_uri` | `text` | Evet | — | — | Orijinal byte içeriğinin harici değişmez depolama URI adresi; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `content_type` | `text` | Evet | — | — | HTTP içerik türü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `byte_size` | `bigint` | Evet | — | — | İçerik uzunluğu, byte; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `captured_at` | `timestamp with time zone` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |
| `published_on` | `date` | Hayır | — | — | published tarihi; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `parser_version` | `text` | Evet | — | — | Ayrıştırıcı sürümü; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_artifact_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Orijinal byte arşivi bağlantısı; **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT urap_artifacts_byte_size_check CHECK ((byte_size > 0))`
- `CONSTRAINT urap_artifacts_sha256_check CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text))`
- `urap_artifacts_pkey: PRIMARY KEY (id)`
- `urap_artifacts_sha256_key: UNIQUE (sha256)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `urap_artifact_source_check`: BEFORE INSERT OR UPDATE OF source_artifact_id → `raw.check_linked_artifact_source` — Yabancı kaynak/ilişki kontrolü; uyumsuz yazmayı reddeder.

### `raw.urap_editions`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 5.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Satır kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `edition` | `text` | Evet | — | PK/UNIQUE (tek kolon) | Kaynak/uygulama alanı: edition (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `publication_date` | `date` | Hayır | — | — | Kaynak/uygulama alanı: publication date (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Orijinal byte arşivi bağlantısı; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `imported_at` | `timestamp with time zone` | Evet | `now()` | — | imported zaman damgası; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT urap_editions_edition_check CHECK ((edition ~ '^[0-9]{4}-[0-9]{4}$'::text))`
- `urap_editions_edition_key: UNIQUE (edition)`
- `urap_editions_pkey: PRIMARY KEY (id)`
- `urap_editions_source_artifact_id_fkey: FOREIGN KEY (source_artifact_id) REFERENCES raw.urap_artifacts(id)`

### `raw.urap_metric_cells`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 7.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `observation_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak gözlem kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `release_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Yayımlanmış sürüm/revizyon kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_table_key` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak anahtar/kod değeri: source table key; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `metric_code` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak kod alanı: metric code; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `value_raw` | `text` | Hayır | — | — | Kaynak hücre değeri metni; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `value_numeric` | `numeric` | Hayır | — | — | Hücre değerinin sayısal karşılığı; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `cell_metadata` | `jsonb` | Evet | `'{}'::jsonb` | — | Kaynak/uygulama alanı: cell metadata (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `PRIMARY KEY (observation_id,metric_code)`
- `FOREIGN KEY (observation_id,release_id,source_table_key) REFERENCES raw.urap_ranking_observations(observation_id,release_id,source_table_key) ON DELETE RESTRICT`
- `FOREIGN KEY (release_id,source_table_key,metric_code) REFERENCES raw.urap_release_metrics(release_id,source_table_key,metric_code) ON DELETE RESTRICT`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `urap_metric_cells_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.urap_metric_definitions`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 5.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `metric_code` | `text` | Evet | — | PK/UNIQUE (tek kolon) | Kaynak kod alanı: metric code; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `name_tr` | `text` | Evet | — | — | Kaynak/uygulama alanı: name tr (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `value_kind` | `text` | Evet | `'SCORE'::text` | — | Kaynak/uygulama alanı: value kind (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `unit` | `text` | Evet | `'URAP_SCORE'::text` | — | Kaynak/uygulama alanı: unit (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `display_order` | `smallint` | Evet | — | PK/UNIQUE (tek kolon) | Kaynak/uygulama alanı: display order (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT urap_metric_definitions_display_order_check CHECK (((display_order >= 1) AND (display_order <= 8)))`
- `CONSTRAINT urap_metric_definitions_unit_check CHECK ((unit = 'URAP_SCORE'::text))`
- `CONSTRAINT urap_metric_definitions_value_kind_check CHECK ((value_kind = 'SCORE'::text))`
- `urap_metric_definitions_display_order_key: UNIQUE (display_order)`
- `urap_metric_definitions_pkey: PRIMARY KEY (metric_code)`

### `raw.urap_metric_scores`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 3.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `ranking_row_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | ranking row kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `metric_code` | `text` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak kod alanı: metric code; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `score` | `numeric(10,2)` | Evet | — | — | Kaynak/uygulama alanı: score (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT urap_metric_scores_score_check CHECK ((score >= (0)::numeric))`
- `urap_metric_scores_pkey: PRIMARY KEY (ranking_row_id, metric_code)`
- `urap_metric_scores_metric_code_fkey: FOREIGN KEY (metric_code) REFERENCES raw.urap_metric_definitions(metric_code)`
- `urap_metric_scores_ranking_row_id_fkey: FOREIGN KEY (ranking_row_id) REFERENCES raw.urap_ranking_rows(id) ON DELETE RESTRICT`

### `raw.urap_publication_releases`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 9.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `release_id` | `bigint` | Evet | — | PK | **OTOMATİK ID — YAZMA**. Yayımlanmış sürüm/revizyon kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `edition_label` | `text` | Evet | — | — | Kaynak/uygulama alanı: edition label (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `release_key` | `text` | Evet | — | — | Yayın sürümünün benzersiz anahtarı; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `release_revision` | `text` | Evet | `'original'` | — | Kaynak/uygulama alanı: release revision (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `ranking_scope` | `text` | Evet | — | — | Kaynak/uygulama alanı: ranking scope (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `published_on` | `date` | Hayır | — | — | published tarihi; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_method_note` | `text` | Hayır | — | — | Kaynak/uygulama alanı: source method note (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `metadata` | `jsonb` | Evet | `'{}'::jsonb` | — | Kaynağa özgü ek metaveri JSON nesnesi; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `captured_at` | `timestamptz` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `urap_publication_releases_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.urap_ranking_groups`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 3.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Satır kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `code` | `text` | Evet | — | PK/UNIQUE (tek kolon) | Kod listesindeki kaynak kodu; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `label` | `text` | Evet | — | — | Kaynak/uygulama alanı: label (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `urap_ranking_groups_code_key: UNIQUE (code)`
- `urap_ranking_groups_pkey: PRIMARY KEY (id)`

### `raw.urap_ranking_observations`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 16.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `observation_id` | `bigint` | Evet | — | PK | **OTOMATİK ID — YAZMA**. Kaynak gözlem kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `release_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Yayımlanmış sürüm/revizyon kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak artifact kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_table_key` | `text` | Evet | — | — | Kaynak anahtar/kod değeri: source table key; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_page` | `integer` | Hayır | — | — | Kaynak sayfa numarası; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `row_ordinal` | `integer` | Evet | — | — | Kaynak/uygulama alanı: row ordinal (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `group_key` | `text` | Hayır | — | — | Kaynak anahtar/kod değeri: group key; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `field_key` | `text` | Hayır | — | — | Kaynak anahtar/kod değeri: field key; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `country_code` | `text` | Hayır | — | — | Kaynak kod alanı: country code; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `university_name_raw` | `text` | Evet | — | — | Kaynakta yazan üniversite adı; normalize etme; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `rank_raw` | `text` | Hayır | — | — | Kaynak sıra değeri metni; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `rank_numeric` | `numeric` | Hayır | — | — | Sıra değerinin sayısal çıkarımı; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `total_score_raw` | `text` | Hayır | — | — | Kaynak metni, dönüştürmeden koru: total score raw; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `total_score_numeric` | `numeric` | Hayır | — | — | Kaynak/uygulama alanı: total score numeric (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `raw_row` | `jsonb` | Evet | — | — | Kaynak sıralama satırının tamamı JSON nesnesi; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `captured_at` | `timestamptz` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `UNIQUE (release_id,artifact_id,source_table_key,row_ordinal)`
- `UNIQUE (observation_id,release_id,source_table_key)`
- `FOREIGN KEY (release_id,artifact_id) REFERENCES raw.urap_release_artifacts(release_id,artifact_id) ON DELETE RESTRICT`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `urap_ranking_observations_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.urap_ranking_rows`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 10.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Satır kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `edition_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | edition kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `group_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | group kimliği / bağlantı anahtarı (anlamı FK ile doğrulanmalı); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Orijinal byte arşivi bağlantısı; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_page` | `integer` | Evet | — | — | Kaynak sayfa numarası; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_rank` | `integer` | Evet | — | — | Kaynak/uygulama alanı: source rank (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `university_name` | `text` | Evet | — | — | Kaynak/uygulama alanı: university name (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `city` | `text` | Evet | — | — | Kaynak/uygulama alanı: city (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `total_score` | `numeric(10,2)` | Evet | — | — | Kaynak/uygulama alanı: total score (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `extraction_score_delta` | `numeric(7,2)` | Hayır | — | — | Kaynak/uygulama alanı: extraction score delta (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT urap_ranking_rows_city_check CHECK ((length(TRIM(BOTH FROM city)) > 0))`
- `CONSTRAINT urap_ranking_rows_source_page_check CHECK ((source_page > 0))`
- `CONSTRAINT urap_ranking_rows_source_rank_check CHECK ((source_rank > 0))`
- `CONSTRAINT urap_ranking_rows_total_score_check CHECK ((total_score >= (0)::numeric))`
- `CONSTRAINT urap_ranking_rows_university_name_check CHECK ((length(TRIM(BOTH FROM university_name)) > 0))`
- `urap_ranking_rows_pkey: PRIMARY KEY (id)`
- `urap_rows_unique_artifact_rank: UNIQUE (source_artifact_id, group_id, source_rank)`
- `urap_rows_unique_rank: UNIQUE (edition_id, group_id, source_rank)`
- `urap_ranking_rows_edition_id_fkey: FOREIGN KEY (edition_id) REFERENCES raw.urap_editions(id)`
- `urap_ranking_rows_group_id_fkey: FOREIGN KEY (group_id) REFERENCES raw.urap_ranking_groups(id)`
- `urap_ranking_rows_source_artifact_id_fkey: FOREIGN KEY (source_artifact_id) REFERENCES raw.urap_artifacts(id)`

**Kaynak SQL indeksleri:** `urap_rows_source_name_idx`

### `raw.urap_release_artifacts`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 3.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `release_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Yayımlanmış sürüm/revizyon kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `artifact_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Kaynak artifact kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `artifact_role` | `text` | Evet | `'RANKING_SOURCE'` | — | Kaynak/uygulama alanı: artifact role (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `PRIMARY KEY (release_id,artifact_id)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `urap_release_artifact_source_guard`: BEFORE INSERT OR UPDATE OF artifact_id → `raw.guard_urap_release_artifact` — Yabancı kaynak/ilişki kontrolü; uyumsuz yazmayı reddeder.
- `urap_release_artifacts_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

### `raw.urap_release_metrics`

**Kullanım:** URAP kaynak verisi. **Kolon sayısı:** 8.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `release_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Yayımlanmış sürüm/revizyon kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_table_key` | `text` | Evet | — | — | Kaynak anahtar/kod değeri: source table key; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `metric_code` | `text` | Evet | — | — | Kaynak kod alanı: metric code; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_column_name` | `text` | Evet | — | — | Kaynak/uygulama alanı: source column name (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `display_order` | `integer` | Evet | — | — | Kaynak/uygulama alanı: display order (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `value_kind` | `text` | Evet | — | — | Kaynak/uygulama alanı: value kind (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `unit` | `text` | Hayır | — | — | Kaynak/uygulama alanı: unit (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `metadata` | `jsonb` | Evet | `'{}'::jsonb` | — | Kaynağa özgü ek metaveri JSON nesnesi; **OPSİYONEL — verilmezse DEFAULT çalışır** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `PRIMARY KEY (release_id,source_table_key,metric_code)`
- `UNIQUE (release_id,source_table_key,display_order)`

**Trigger davranışları (uygulama tarafından kolon yazan otomatik trigger saptanmadı; aşağıdakiler doğrulama/engelleme trigger’larıdır):**

- `urap_release_metrics_append_only`: BEFORE UPDATE OR DELETE → `raw.deny_mutation_immutable` — UPDATE/DELETE RED: değişmez kaynak verisi.

## YÖK Atlas/genel — 2 tablo

### `raw.api_responses`

**Kullanım:** YÖK Atlas/genel kaynak verisi. **Kolon sayısı:** 12.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `api_response_id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Kaynak API yanıtı kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `ingestion_run_id` | `bigint` | Evet | — | FK (ayrıntı kısıtlarda) | Veri alma çalışması kimliği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `endpoint` | `text` | Evet | — | — | Kaynak/uygulama alanı: endpoint (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `method` | `text` | Evet | — | — | Kaynak/uygulama alanı: method (semantik kaynağa göre teyit edilmeli); **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `score_type` | `text` | Hayır | — | — | Kaynak/uygulama alanı: score type (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `page_number` | `integer` | Hayır | — | — | Kaynak/uygulama alanı: page number (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `captured_at` | `timestamp with time zone` | Evet | `now()` | — | Kaynağın arşivlendiği zaman; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |
| `source_hash_sha256` | `text` | Hayır | — | — | Kaynak içeriğin SHA-256 özeti; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `http_status` | `integer` | Hayır | — | — | Kaynak/uygulama alanı: http status (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `payload` | `jsonb` | Evet | — | — | Kaynağın ayrıştırılmış JSON içeriği; **GEREKLİ — kaynak/ilişki verisiyle doldur** |
| `source_path` | `text` | Hayır | — | — | Kaynak/uygulama alanı: source path (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `source_artifact_id` | `bigint` | Hayır | — | FK (ayrıntı kısıtlarda) | Orijinal byte arşivi bağlantısı; **İsteğe bağlı — kaynaktaki karşılığını koru** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `CONSTRAINT api_responses_source_hash_sha256_check CHECK (((source_hash_sha256 IS NULL) OR (length(source_hash_sha256) = 64)))`
- `api_responses_pkey: PRIMARY KEY (api_response_id)`
- `api_responses_ingestion_run_id_fkey: FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id)`

**Kaynak SQL indeksleri:** `idx_api_response_endpoint`, `idx_api_response_run`, `ux_api_response_identity`

### `raw.ingestion_runs`

**Kullanım:** YÖK Atlas/genel kaynak verisi. **Kolon sayısı:** 7.

| Kolon | PostgreSQL tipi | Zorunlu | Varsayılan | Anahtar / ilişki | Açıklama ve scraper yazma kuralı |
|---|---|---|---|---|---|
| `ingestion_run_id` | `bigint` | Evet | — | PK/UNIQUE (tek kolon) | **OTOMATİK ID — YAZMA**. Veri alma çalışması kimliği; **DB ÜRETİR — INSERT sırasında gönderme** |
| `source_system` | `text` | Evet | `'yokatlas'::text` | — | Kaynak sistem kodu; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `started_at` | `timestamp with time zone` | Evet | `now()` | — | started zaman damgası; **DEFAULT ZAMAN — atlanabilir; kaynak zamanı ile karıştırma** |
| `completed_at` | `timestamp with time zone` | Hayır | — | — | completed zaman damgası; **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `status` | `text` | Evet | `'running'::text` | — | İşlem veya yayın durumu; **OPSİYONEL — verilmezse DEFAULT çalışır** |
| `scraper_version` | `text` | Hayır | — | — | Kaynak/uygulama alanı: scraper version (semantik kaynağa göre teyit edilmeli); **İsteğe bağlı — kaynaktaki karşılığını koru** |
| `details` | `jsonb` | Evet | `'{}'::jsonb` | — | Kaynak/uygulama alanı: details (semantik kaynağa göre teyit edilmeli); **OPSİYONEL — verilmezse DEFAULT çalışır** |

**Kısıtlar (SQL kaynaklarında görülen):**

- `ingestion_runs_pkey: PRIMARY KEY (ingestion_run_id)`

## RAW dışındaki otomatik kalite görünümü

`quality.tuik_dimension_code_issues`: Migration `005` ile tanımlanmış salt-okunur VIEW. **Scraper bu görünüme INSERT/UPDATE yapmamalı**; DSD/codelist uyuşmazlıklarını incelemek için `SELECT` kullanılmalı.

## Notlar ve sınırlamalar

- Baseline SQL’de tanımlı tüm `raw` tabloları ile bilinen 15 yeni tablo birleşti. Eski tabloların 15 adet identity dönüşümü de işlendi.
- PostgreSQL trigger’larının otomatik kolon yazdığına ilişkin kanıt yok; burada görülenler kontrol veya değişmezlik trigger’larıdır. Canlı DB’de başka trigger olabilir.
- `GENERATED ALWAYS` sütunları uygulama tarafından manuel doldurulmamalıdır. Identity olmayan PK ve kaynak kodları ise scraper tarafından sağlanır.
- `CREATE TABLE` içi CHECK, FK, UNIQUE ve daha sonra ALTER TABLE ile eklenen kısıtlar mümkün olduğu ölçüde aktarılmıştır. Canlı katalog üstün kaynaktır.


# Canlı veritabanından constraint ve trigger referansı

## `raw.api_responses` — kısıtlar ve triggerlar

- **api_responses_ingestion_run_id_fkey** (`f`): `FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id)`
- **api_responses_pkey** (`p`): `PRIMARY KEY (api_response_id)`
- **api_responses_source_artifact_id_fkey** (`f`): `FOREIGN KEY (source_artifact_id) REFERENCES raw.source_artifact(artifact_id) ON DELETE RESTRICT`
- **api_responses_source_hash_sha256_check** (`c`): `CHECK (((source_hash_sha256 IS NULL) OR (length(source_hash_sha256) = 64)))`

## `raw.artifact_parse_events` — kısıtlar ve triggerlar

- **artifact_parse_events_artifact_id_fkey** (`f`): `FOREIGN KEY (artifact_id) REFERENCES raw.source_artifact(artifact_id) ON DELETE RESTRICT`
- **artifact_parse_events_error_info_check** (`c`): `CHECK ((jsonb_typeof(error_info) = 'object'::text))`
- **artifact_parse_events_parse_status_check** (`c`): `CHECK ((parse_status = ANY (ARRAY['SUCCESS'::text, 'PARTIAL'::text, 'FAILED'::text])))`
- **artifact_parse_events_pkey** (`p`): `PRIMARY KEY (parse_event_id)`

**Aktif triggerlar:**
- `artifact_parse_events_append_only`: `CREATE TRIGGER artifact_parse_events_append_only BEFORE DELETE OR UPDATE ON raw.artifact_parse_events FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.ingestion_runs` — kısıtlar ve triggerlar

- **ingestion_runs_pkey** (`p`): `PRIMARY KEY (ingestion_run_id)`

## `raw.openalex_authors` — kısıtlar ve triggerlar

- **openalex_authors_api_response_id_fkey** (`f`): `FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`
- **openalex_authors_author_id_check** (`c`): `CHECK ((author_id ~ '^https://openalex\.org/A[0-9]+$'::text))`
- **openalex_authors_pkey** (`p`): `PRIMARY KEY (author_id)`
- **openalex_authors_source_payload_check** (`c`): `CHECK ((jsonb_typeof(source_payload) = 'object'::text))`

## `raw.openalex_authorship_institutions` — kısıtlar ve triggerlar

- **openalex_authorship_institutions_institution_index_check** (`c`): `CHECK ((institution_index >= 0))`
- **openalex_authorship_institutions_pkey** (`p`): `PRIMARY KEY (work_id, authorship_index, institution_index)`
- **openalex_authorship_institutions_raw_institution_check** (`c`): `CHECK ((jsonb_typeof(raw_institution) = 'object'::text))`
- **openalex_authorship_institutions_work_id_authorship_index_fkey** (`f`): `FOREIGN KEY (work_id, authorship_index) REFERENCES raw.openalex_authorships(work_id, authorship_index) ON DELETE RESTRICT`

## `raw.openalex_authorships` — kısıtlar ve triggerlar

- **openalex_authorships_authorship_index_check** (`c`): `CHECK ((authorship_index >= 0))`
- **openalex_authorships_pkey** (`p`): `PRIMARY KEY (work_id, authorship_index)`
- **openalex_authorships_raw_authorship_check** (`c`): `CHECK ((jsonb_typeof(raw_authorship) = 'object'::text))`
- **openalex_authorships_work_id_fkey** (`f`): `FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

## `raw.openalex_entity_types` — kısıtlar ve triggerlar

- **openalex_entity_types_entity_type_check** (`c`): `CHECK ((entity_type ~ '^[a-z][a-z0-9_]{0,63}$'::text))`
- **openalex_entity_types_pkey** (`p`): `PRIMARY KEY (entity_type)`

## `raw.openalex_funders` — kısıtlar ve triggerlar

- **openalex_funders_api_response_id_fkey** (`f`): `FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`
- **openalex_funders_funder_id_check** (`c`): `CHECK ((funder_id ~ '^https://openalex\.org/F[0-9]+$'::text))`
- **openalex_funders_pkey** (`p`): `PRIMARY KEY (funder_id)`
- **openalex_funders_source_payload_check** (`c`): `CHECK ((jsonb_typeof(source_payload) = 'object'::text))`

## `raw.openalex_institution_relationships` — kısıtlar ve triggerlar

- **openalex_institution_relationships_openalex_institution_id_fkey** (`f`): `FOREIGN KEY (openalex_institution_id) REFERENCES raw.openalex_institutions(openalex_institution_id) ON DELETE RESTRICT`
- **openalex_institution_relationships_pkey** (`p`): `PRIMARY KEY (openalex_institution_id, relation_index)`
- **openalex_institution_relationships_raw_relationship_check** (`c`): `CHECK ((jsonb_typeof(raw_relationship) = 'object'::text))`
- **openalex_institution_relationships_relation_index_check** (`c`): `CHECK ((relation_index >= 0))`

## `raw.openalex_institutions` — kısıtlar ve triggerlar

- **openalex_institutions_api_response_id_fkey** (`f`): `FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`
- **openalex_institutions_openalex_institution_id_check** (`c`): `CHECK ((openalex_institution_id ~ '^https://openalex\.org/I[0-9]+$'::text))`
- **openalex_institutions_pkey** (`p`): `PRIMARY KEY (openalex_institution_id)`
- **openalex_institutions_source_payload_check** (`c`): `CHECK ((jsonb_typeof(source_payload) = 'object'::text))`

## `raw.openalex_keywords` — kısıtlar ve triggerlar

- **openalex_keywords_api_response_id_fkey** (`f`): `FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`
- **openalex_keywords_pkey** (`p`): `PRIMARY KEY (keyword_id)`
- **openalex_keywords_source_payload_check** (`c`): `CHECK ((jsonb_typeof(source_payload) = 'object'::text))`

## `raw.openalex_object_snapshots` — kısıtlar ve triggerlar

- **openalex_object_snapshots_api_response_id_entity_type_sourc_key** (`u`): `UNIQUE (api_response_id, entity_type, source_array_index)`
- **openalex_object_snapshots_api_response_id_fkey** (`f`): `FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`
- **openalex_object_snapshots_pkey** (`p`): `PRIMARY KEY (snapshot_id)`
- **openalex_object_snapshots_source_array_index_check** (`c`): `CHECK ((source_array_index >= 0))`
- **openalex_object_snapshots_source_payload_check** (`c`): `CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- **openalex_snapshots_type_catalog_fk** (`f`): `FOREIGN KEY (entity_type) REFERENCES raw.openalex_entity_types(entity_type)`

**Aktif triggerlar:**
- `openalex_object_snapshots_append_only`: `CREATE TRIGGER openalex_object_snapshots_append_only BEFORE DELETE OR UPDATE ON raw.openalex_object_snapshots FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.openalex_reference_observations` — kısıtlar ve triggerlar

- **openalex_reference_observatio_snapshot_id_reference_path_re_key** (`u`): `UNIQUE (snapshot_id, reference_path, reference_index)`
- **openalex_reference_observations_pkey** (`p`): `PRIMARY KEY (reference_observation_id)`
- **openalex_reference_observations_reference_index_check** (`c`): `CHECK ((reference_index >= 0))`
- **openalex_reference_observations_snapshot_id_fkey** (`f`): `FOREIGN KEY (snapshot_id) REFERENCES raw.openalex_object_snapshots(snapshot_id) ON DELETE RESTRICT`
- **openalex_reference_observations_target_type_fkey** (`f`): `FOREIGN KEY (target_type) REFERENCES raw.openalex_entity_types(entity_type)`

**Aktif triggerlar:**
- `openalex_reference_observations_append_only`: `CREATE TRIGGER openalex_reference_observations_append_only BEFORE DELETE OR UPDATE ON raw.openalex_reference_observations FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.openalex_sources` — kısıtlar ve triggerlar

- **openalex_sources_api_response_id_fkey** (`f`): `FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`
- **openalex_sources_pkey** (`p`): `PRIMARY KEY (source_id)`
- **openalex_sources_source_id_check** (`c`): `CHECK ((source_id ~ '^https://openalex\.org/S[0-9]+$'::text))`
- **openalex_sources_source_payload_check** (`c`): `CHECK ((jsonb_typeof(source_payload) = 'object'::text))`

## `raw.openalex_topics` — kısıtlar ve triggerlar

- **openalex_topics_api_response_id_fkey** (`f`): `FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`
- **openalex_topics_pkey** (`p`): `PRIMARY KEY (topic_id)`
- **openalex_topics_source_payload_check** (`c`): `CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- **openalex_topics_topic_id_check** (`c`): `CHECK ((topic_id ~ '^https://openalex\.org/T[0-9]+$'::text))`

## `raw.openalex_work_grants` — kısıtlar ve triggerlar

- **openalex_work_grants_grant_index_check** (`c`): `CHECK ((grant_index >= 0))`
- **openalex_work_grants_pkey** (`p`): `PRIMARY KEY (work_id, grant_index)`
- **openalex_work_grants_raw_grant_check** (`c`): `CHECK ((jsonb_typeof(raw_grant) = 'object'::text))`
- **openalex_work_grants_work_id_fkey** (`f`): `FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

## `raw.openalex_work_institutions` — kısıtlar ve triggerlar

- **openalex_work_institutions_openalex_institution_id_fkey** (`f`): `FOREIGN KEY (openalex_institution_id) REFERENCES raw.openalex_institutions(openalex_institution_id) ON DELETE RESTRICT`
- **openalex_work_institutions_pkey** (`p`): `PRIMARY KEY (work_id, openalex_institution_id)`
- **openalex_work_institutions_work_id_fkey** (`f`): `FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

## `raw.openalex_work_keywords` — kısıtlar ve triggerlar

- **openalex_work_keywords_keyword_id_fkey** (`f`): `FOREIGN KEY (keyword_id) REFERENCES raw.openalex_keywords(keyword_id) ON DELETE RESTRICT`
- **openalex_work_keywords_keyword_score_check** (`c`): `CHECK (((keyword_score IS NULL) OR ((keyword_score >= (0)::numeric) AND (keyword_score <= (1)::numeric))))`
- **openalex_work_keywords_pkey** (`p`): `PRIMARY KEY (work_id, keyword_id)`
- **openalex_work_keywords_work_id_fkey** (`f`): `FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

## `raw.openalex_work_links` — kısıtlar ve triggerlar

- **openalex_work_links_link_index_check** (`c`): `CHECK ((link_index >= 0))`
- **openalex_work_links_link_type_check** (`c`): `CHECK ((link_type = ANY (ARRAY['related_works'::text, 'referenced_works'::text])))`
- **openalex_work_links_pkey** (`p`): `PRIMARY KEY (work_id, link_type, link_index)`
- **openalex_work_links_work_id_fkey** (`f`): `FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

## `raw.openalex_work_locations` — kısıtlar ve triggerlar

- **openalex_work_locations_location_index_check** (`c`): `CHECK ((location_index >= 0))`
- **openalex_work_locations_pkey** (`p`): `PRIMARY KEY (work_id, location_index)`
- **openalex_work_locations_raw_location_check** (`c`): `CHECK ((jsonb_typeof(raw_location) = 'object'::text))`
- **openalex_work_locations_work_id_fkey** (`f`): `FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

## `raw.openalex_work_observations` — kısıtlar ve triggerlar

- **openalex_work_observations_cited_by_count_check** (`c`): `CHECK (((cited_by_count IS NULL) OR (cited_by_count >= 0)))`
- **openalex_work_observations_ingestion_run_id_fkey** (`f`): `FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id) ON DELETE RESTRICT`
- **openalex_work_observations_pkey** (`p`): `PRIMARY KEY (work_id, observed_at)`
- **openalex_work_observations_work_id_fkey** (`f`): `FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

## `raw.openalex_work_sdgs` — kısıtlar ve triggerlar

- **openalex_work_sdgs_pkey** (`p`): `PRIMARY KEY (work_id, sdg_index)`
- **openalex_work_sdgs_raw_sdg_check** (`c`): `CHECK ((jsonb_typeof(raw_sdg) = 'object'::text))`
- **openalex_work_sdgs_sdg_index_check** (`c`): `CHECK ((sdg_index >= 0))`
- **openalex_work_sdgs_work_id_fkey** (`f`): `FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

## `raw.openalex_work_topics` — kısıtlar ve triggerlar

- **openalex_work_topics_pkey** (`p`): `PRIMARY KEY (work_id, topic_id)`
- **openalex_work_topics_topic_id_fkey** (`f`): `FOREIGN KEY (topic_id) REFERENCES raw.openalex_topics(topic_id) ON DELETE RESTRICT`
- **openalex_work_topics_topic_score_check** (`c`): `CHECK (((topic_score IS NULL) OR ((topic_score >= (0)::numeric) AND (topic_score <= (1)::numeric))))`
- **openalex_work_topics_work_id_fkey** (`f`): `FOREIGN KEY (work_id) REFERENCES raw.openalex_works(work_id) ON DELETE RESTRICT`

## `raw.openalex_works` — kısıtlar ve triggerlar

- **openalex_works_api_response_id_fkey** (`f`): `FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id) ON DELETE RESTRICT`
- **openalex_works_cited_by_count_check** (`c`): `CHECK (((cited_by_count IS NULL) OR (cited_by_count >= 0)))`
- **openalex_works_countries_distinct_count_check** (`c`): `CHECK (((countries_distinct_count IS NULL) OR (countries_distinct_count >= 0)))`
- **openalex_works_pkey** (`p`): `PRIMARY KEY (work_id)`
- **openalex_works_publication_year_check** (`c`): `CHECK (((publication_year IS NULL) OR ((publication_year >= 1000) AND (publication_year <= 2200))))`
- **openalex_works_source_payload_check** (`c`): `CHECK ((jsonb_typeof(source_payload) = 'object'::text))`
- **openalex_works_work_id_check** (`c`): `CHECK ((work_id ~ '^https://openalex\.org/W[0-9]+$'::text))`

## `raw.report_documents` — kısıtlar ve triggerlar

- **report_documents_document_id_report_id_key** (`u`): `UNIQUE (document_id, report_id)`
- **report_documents_extracted_sha256_check** (`c`): `CHECK ((extracted_sha256 ~ '^[0-9a-f]{64}$'::text))`
- **report_documents_ingestion_run_id_fkey** (`f`): `FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id)`
- **report_documents_pkey** (`p`): `PRIMARY KEY (document_id)`
- **report_documents_report_id_source_sha256_parser_version_key** (`u`): `UNIQUE (report_id, source_sha256, parser_version)`
- **report_documents_source_artifact_id_fkey** (`f`): `FOREIGN KEY (source_artifact_id) REFERENCES raw.source_artifact(artifact_id) ON DELETE RESTRICT`
- **report_documents_source_sha256_check** (`c`): `CHECK ((source_sha256 ~ '^[0-9a-f]{64}$'::text))`
- **report_documents_source_system_check** (`c`): `CHECK ((source_system = ANY (ARRAY['sege'::text, 'urap'::text])))`

**Aktif triggerlar:**
- `report_artifact_source_check`: `CREATE TRIGGER report_artifact_source_check BEFORE INSERT OR UPDATE OF source_artifact_id ON raw.report_documents FOR EACH ROW EXECUTE FUNCTION raw.check_linked_artifact_source()`

## `raw.sege_artifacts` — kısıtlar ve triggerlar

- **sege_artifacts_byte_size_check** (`c`): `CHECK ((byte_size > 0))`
- **sege_artifacts_pkey** (`p`): `PRIMARY KEY (id)`
- **sege_artifacts_sha256_check** (`c`): `CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text))`
- **sege_artifacts_sha256_key** (`u`): `UNIQUE (sha256)`
- **sege_artifacts_source_artifact_id_fkey** (`f`): `FOREIGN KEY (source_artifact_id) REFERENCES raw.source_artifact(artifact_id) ON DELETE RESTRICT`
- **sege_artifacts_storage_uri_check** (`c`): `CHECK ((length(btrim(storage_uri)) > 0))`

**Aktif triggerlar:**
- `sege_artifact_source_check`: `CREATE TRIGGER sege_artifact_source_check BEFORE INSERT OR UPDATE OF source_artifact_id ON raw.sege_artifacts FOR EACH ROW EXECUTE FUNCTION raw.check_linked_artifact_source()`

## `raw.sege_editions` — kısıtlar ve triggerlar

- **sege_editions_geography_level_check** (`c`): `CHECK ((geography_level = ANY (ARRAY['PROVINCE'::text, 'DISTRICT'::text])))`
- **sege_editions_pkey** (`p`): `PRIMARY KEY (id)`
- **sege_editions_source_artifact_id_fkey** (`f`): `FOREIGN KEY (source_artifact_id) REFERENCES raw.sege_artifacts(id)`
- **sege_editions_tier_method_check** (`c`): `CHECK ((tier_method = ANY (ARRAY['EXTRACTED_FROM_SOURCE'::text, 'DERIVED_FROM_PUBLISHED_RANK_COUNTS'::text])))`
- **sege_editions_unique** (`u`): `UNIQUE (edition_year, geography_level)`
- **sege_editions_unique_artifact** (`u`): `UNIQUE (source_artifact_id, edition_year, geography_level)`

## `raw.sege_publication_releases` — kısıtlar ve triggerlar

- **sege_publication_releases_edition_year_check** (`c`): `CHECK (((edition_year >= 1900) AND (edition_year <= 2200)))`
- **sege_publication_releases_geography_level_check** (`c`): `CHECK ((geography_level = ANY (ARRAY['PROVINCE'::text, 'DISTRICT'::text, 'REGION_NUTS2'::text])))`
- **sege_publication_releases_pkey** (`p`): `PRIMARY KEY (release_id)`
- **sege_publication_releases_release_key_check** (`c`): `CHECK ((length(btrim(release_key)) > 0))`
- **sege_publication_releases_release_key_key** (`u`): `UNIQUE (release_key)`
- **sege_publication_releases_release_metadata_check** (`c`): `CHECK ((jsonb_typeof(release_metadata) = 'object'::text))`

**Aktif triggerlar:**
- `sege_publication_releases_append_only`: `CREATE TRIGGER sege_publication_releases_append_only BEFORE DELETE OR UPDATE ON raw.sege_publication_releases FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.sege_published_indicator_cells` — kısıtlar ve triggerlar

- **sege_published_indicator_cells_observation_id_fkey** (`f`): `FOREIGN KEY (observation_id) REFERENCES raw.sege_ranking_observations(observation_id) ON DELETE RESTRICT`
- **sege_published_indicator_cells_pkey** (`p`): `PRIMARY KEY (observation_id, indicator_code_raw)`

**Aktif triggerlar:**
- `sege_published_indicator_cells_append_only`: `CREATE TRIGGER sege_published_indicator_cells_append_only BEFORE DELETE OR UPDATE ON raw.sege_published_indicator_cells FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.sege_ranking_observations` — kısıtlar ve triggerlar

- **sege_ranking_observations_development_tier_check** (`c`): `CHECK (((development_tier >= 1) AND (development_tier <= 6)))`
- **sege_ranking_observations_geography_name_raw_check** (`c`): `CHECK ((length(btrim(geography_name_raw)) > 0))`
- **sege_ranking_observations_pkey** (`p`): `PRIMARY KEY (observation_id)`
- **sege_ranking_observations_raw_row_check** (`c`): `CHECK ((jsonb_typeof(raw_row) = 'object'::text))`
- **sege_ranking_observations_release_id_artifact_id_fkey** (`f`): `FOREIGN KEY (release_id, artifact_id) REFERENCES raw.sege_release_artifacts(release_id, artifact_id) ON DELETE RESTRICT`
- **sege_ranking_observations_release_id_artifact_id_source_tab_key** (`u`): `UNIQUE (release_id, artifact_id, source_table_key, row_ordinal)`
- **sege_ranking_observations_row_ordinal_check** (`c`): `CHECK ((row_ordinal >= 0))`

**Aktif triggerlar:**
- `sege_obs_tier_guard`: `CREATE TRIGGER sege_obs_tier_guard BEFORE INSERT OR UPDATE OF development_tier, release_id ON raw.sege_ranking_observations FOR EACH ROW EXECUTE FUNCTION raw.check_sege_v2_tier()`
- `sege_ranking_observations_append_only`: `CREATE TRIGGER sege_ranking_observations_append_only BEFORE DELETE OR UPDATE ON raw.sege_ranking_observations FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.sege_ranking_rows` — kısıtlar ve triggerlar

- **sege_ranking_rows_development_tier_check** (`c`): `CHECK (((development_tier >= 1) AND (development_tier <= 6)))`
- **sege_ranking_rows_district_name_check** (`c`): `CHECK (((district_name IS NULL) OR (length(btrim(district_name)) > 0)))`
- **sege_ranking_rows_edition_id_fkey** (`f`): `FOREIGN KEY (edition_id) REFERENCES raw.sege_editions(id)`
- **sege_ranking_rows_pkey** (`p`): `PRIMARY KEY (id)`
- **sege_ranking_rows_province_name_check** (`c`): `CHECK ((length(btrim(province_name)) > 0))`
- **sege_ranking_rows_source_artifact_id_fkey** (`f`): `FOREIGN KEY (source_artifact_id) REFERENCES raw.sege_artifacts(id)`
- **sege_ranking_rows_source_page_check** (`c`): `CHECK ((source_page > 0))`
- **sege_ranking_rows_source_rank_check** (`c`): `CHECK ((source_rank > 0))`
- **sege_ranking_rows_tier_method_check** (`c`): `CHECK ((tier_method = ANY (ARRAY['EXTRACTED_FROM_SOURCE'::text, 'DERIVED_FROM_PUBLISHED_RANK_COUNTS'::text])))`
- **sege_rows_unique_rank** (`u`): `UNIQUE (edition_id, source_rank)`

## `raw.sege_release_artifacts` — kısıtlar ve triggerlar

- **sege_release_artifacts_artifact_id_fkey** (`f`): `FOREIGN KEY (artifact_id) REFERENCES raw.source_artifact(artifact_id) ON DELETE RESTRICT`
- **sege_release_artifacts_pkey** (`p`): `PRIMARY KEY (release_id, artifact_id)`
- **sege_release_artifacts_release_id_fkey** (`f`): `FOREIGN KEY (release_id) REFERENCES raw.sege_publication_releases(release_id) ON DELETE RESTRICT`

**Aktif triggerlar:**
- `sege_release_artifact_source_guard`: `CREATE TRIGGER sege_release_artifact_source_guard BEFORE INSERT OR UPDATE OF artifact_id ON raw.sege_release_artifacts FOR EACH ROW EXECUTE FUNCTION raw.guard_sege_release_artifact()`
- `sege_release_artifacts_append_only`: `CREATE TRIGGER sege_release_artifacts_append_only BEFORE DELETE OR UPDATE ON raw.sege_release_artifacts FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.source_artifact` — kısıtlar ve triggerlar

- **source_artifact_byte_size_check** (`c`): `CHECK ((byte_size >= 0))`
- **source_artifact_exactly_one_storage_check** (`c`): `CHECK (((body_bytes IS NOT NULL) <> (storage_uri IS NOT NULL)))`
- **source_artifact_fetch_id_fkey** (`f`): `FOREIGN KEY (fetch_id) REFERENCES raw.source_fetch(fetch_id) ON DELETE RESTRICT`
- **source_artifact_inline_integrity_check** (`c`): `CHECK (((body_bytes IS NULL) OR ((octet_length(body_bytes) = byte_size) AND (encode(sha256(body_bytes), 'hex'::text) = sha256_hex))))`
- **source_artifact_mime_type_check** (`c`): `CHECK ((length(btrim(mime_type)) > 0))`
- **source_artifact_pkey** (`p`): `PRIMARY KEY (artifact_id)`
- **source_artifact_sha256_hex_check** (`c`): `CHECK ((sha256_hex ~ '^[0-9a-f]{64}$'::text))`
- **source_artifact_storage_uri_not_empty_check** (`c`): `CHECK (((storage_uri IS NULL) OR (length(btrim(storage_uri)) > 0)))`

**Aktif triggerlar:**
- `source_artifact_append_only`: `CREATE TRIGGER source_artifact_append_only BEFORE DELETE OR UPDATE ON raw.source_artifact FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.source_artifact_verifications` — kısıtlar ve triggerlar

- **source_artifact_verifications_artifact_id_fkey** (`f`): `FOREIGN KEY (artifact_id) REFERENCES raw.source_artifact(artifact_id) ON DELETE RESTRICT`
- **source_artifact_verifications_detail_check** (`c`): `CHECK ((jsonb_typeof(detail) = 'object'::text))`
- **source_artifact_verifications_observed_byte_size_check** (`c`): `CHECK (((observed_byte_size IS NULL) OR (observed_byte_size >= 0)))`
- **source_artifact_verifications_observed_sha256_hex_check** (`c`): `CHECK (((observed_sha256_hex IS NULL) OR (observed_sha256_hex ~ '^[0-9a-f]{64}$'::text)))`
- **source_artifact_verifications_pkey** (`p`): `PRIMARY KEY (verification_id)`

**Aktif triggerlar:**
- `source_artifact_verifications_append_only`: `CREATE TRIGGER source_artifact_verifications_append_only BEFORE DELETE OR UPDATE ON raw.source_artifact_verifications FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.source_fetch` — kısıtlar ve triggerlar

- **source_fetch_error_metadata_check** (`c`): `CHECK ((jsonb_typeof(error_metadata) = 'object'::text))`
- **source_fetch_headers_secret_check** (`c`): `CHECK (((NOT raw.has_sensitive_headers(request_headers_sanitized, ARRAY['authorization'::text, 'cookie'::text, 'x-api-key'::text, 'proxy-authorization'::text])) AND (NOT raw.has_sensitive_headers(response_headers_sanitized, ARRAY['set-cookie'::text, 'authorization'::text, 'proxy-authenticate'::text]))))`
- **source_fetch_ingestion_run_id_fkey** (`f`): `FOREIGN KEY (ingestion_run_id) REFERENCES raw.ingestion_runs(ingestion_run_id) ON DELETE RESTRICT`
- **source_fetch_pkey** (`p`): `PRIMARY KEY (fetch_id)`
- **source_fetch_request_body_sha256_check** (`c`): `CHECK (((request_body_sha256 IS NULL) OR (request_body_sha256 ~ '^[0-9a-f]{64}$'::text)))`
- **source_fetch_request_headers_sanitized_check** (`c`): `CHECK ((jsonb_typeof(request_headers_sanitized) = 'object'::text))`
- **source_fetch_request_method_check** (`c`): `CHECK ((request_method ~ '^[A-Z]+$'::text))`
- **source_fetch_request_params_sanitized_check** (`c`): `CHECK ((jsonb_typeof(request_params_sanitized) = 'object'::text))`
- **source_fetch_request_url_sanitized_check** (`c`): `CHECK ((length(btrim(request_url_sanitized)) > 0))`
- **source_fetch_response_headers_sanitized_check** (`c`): `CHECK ((jsonb_typeof(response_headers_sanitized) = 'object'::text))`
- **source_fetch_response_status_check** (`c`): `CHECK (((response_status IS NULL) OR ((response_status >= 100) AND (response_status <= 599))))`
- **source_fetch_source_system_check** (`c`): `CHECK ((length(btrim(source_system)) > 0))`

**Aktif triggerlar:**
- `source_fetch_append_only`: `CREATE TRIGGER source_fetch_append_only BEFORE DELETE OR UPDATE ON raw.source_fetch FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.source_records` — kısıtlar ve triggerlar

- **source_records_api_response_id_fkey** (`f`): `FOREIGN KEY (api_response_id) REFERENCES raw.api_responses(api_response_id)`
- **source_records_api_response_id_source_entity_source_array_i_key** (`u`): `UNIQUE (api_response_id, source_entity, source_array_index)`
- **source_records_pkey** (`p`): `PRIMARY KEY (source_record_id)`
- **source_records_source_array_index_check** (`c`): `CHECK ((source_array_index >= 0))`

## `raw.tuik_codelist` — kısıtlar ve triggerlar

- **tuik_codelist_pkey** (`p`): `PRIMARY KEY (agency_id, codelist_id, codelist_version)`

## `raw.tuik_codelist_code` — kısıtlar ve triggerlar

- **tuik_codelist_code_agency_id_codelist_id_codelist_version_fkey** (`f`): `FOREIGN KEY (agency_id, codelist_id, codelist_version) REFERENCES raw.tuik_codelist(agency_id, codelist_id, codelist_version)`
- **tuik_codelist_code_pkey** (`p`): `PRIMARY KEY (agency_id, codelist_id, codelist_version, code)`

## `raw.tuik_dataflow` — kısıtlar ve triggerlar

- **tuik_dataflow_dsd_agency_id_dsd_id_dsd_version_fkey** (`f`): `FOREIGN KEY (dsd_agency_id, dsd_id, dsd_version) REFERENCES raw.tuik_dsd(agency_id, dsd_id, dsd_version)`
- **tuik_dataflow_pkey** (`p`): `PRIMARY KEY (agency_id, flow_id, flow_version)`

## `raw.tuik_dsd` — kısıtlar ve triggerlar

- **tuik_dsd_pkey** (`p`): `PRIMARY KEY (agency_id, dsd_id, dsd_version)`

## `raw.tuik_dsd_attribute` — kısıtlar ve triggerlar

- **tuik_dsd_attribute_codelist_agency_codelist_id_codelist_ve_fkey** (`f`): `FOREIGN KEY (codelist_agency, codelist_id, codelist_version) REFERENCES raw.tuik_codelist(agency_id, codelist_id, codelist_version)`
- **tuik_dsd_attribute_dsd_agency_dsd_id_dsd_version_fkey** (`f`): `FOREIGN KEY (dsd_agency, dsd_id, dsd_version) REFERENCES raw.tuik_dsd(agency_id, dsd_id, dsd_version)`
- **tuik_dsd_attribute_pkey** (`p`): `PRIMARY KEY (dsd_agency, dsd_id, dsd_version, attribute_id)`

## `raw.tuik_dsd_codelist` — kısıtlar ve triggerlar

- **tuik_dsd_codelist_codelist_agency_codelist_id_codelist_ver_fkey** (`f`): `FOREIGN KEY (codelist_agency, codelist_id, codelist_version) REFERENCES raw.tuik_codelist(agency_id, codelist_id, codelist_version)`
- **tuik_dsd_codelist_dsd_agency_dsd_id_dsd_version_fkey** (`f`): `FOREIGN KEY (dsd_agency, dsd_id, dsd_version) REFERENCES raw.tuik_dsd(agency_id, dsd_id, dsd_version)`
- **tuik_dsd_codelist_pkey** (`p`): `PRIMARY KEY (dsd_agency, dsd_id, dsd_version, codelist_agency, codelist_id, codelist_version)`

## `raw.tuik_dsd_dimension` — kısıtlar ve triggerlar

- **tuik_dsd_dimension_codelist_agency_codelist_id_codelist_ve_fkey** (`f`): `FOREIGN KEY (codelist_agency, codelist_id, codelist_version) REFERENCES raw.tuik_codelist(agency_id, codelist_id, codelist_version)`
- **tuik_dsd_dimension_dsd_agency_dsd_id_dsd_version_fkey** (`f`): `FOREIGN KEY (dsd_agency, dsd_id, dsd_version) REFERENCES raw.tuik_dsd(agency_id, dsd_id, dsd_version)`
- **tuik_dsd_dimension_key_position_check** (`c`): `CHECK (((key_position IS NULL) OR (key_position > 0)))`
- **tuik_dsd_dimension_pkey** (`p`): `PRIMARY KEY (dsd_agency, dsd_id, dsd_version, dimension_id)`

## `raw.tuik_fetch_run` — kısıtlar ve triggerlar

- **tuik_fetch_run_check** (`c`): `CHECK (((finished_at IS NULL) OR (finished_at >= started_at)))`
- **tuik_fetch_run_dataflow_fk** (`f`): `FOREIGN KEY (agency_id, flow_id, flow_version) REFERENCES raw.tuik_dataflow(agency_id, flow_id, flow_version)`
- **tuik_fetch_run_http_status_check** (`c`): `CHECK (((http_status IS NULL) OR ((http_status >= 100) AND (http_status <= 599))))`
- **tuik_fetch_run_pkey** (`p`): `PRIMARY KEY (run_id)`
- **tuik_fetch_run_status_check** (`c`): `CHECK ((status = ANY (ARRAY['running'::text, 'succeeded'::text, 'failed'::text, 'partial'::text, 'cancelled'::text])))`

**Aktif triggerlar:**
- `tuik_fetch_flow_change_guard`: `CREATE TRIGGER tuik_fetch_flow_change_guard BEFORE UPDATE OF agency_id, flow_id, flow_version ON raw.tuik_fetch_run FOR EACH ROW EXECUTE FUNCTION raw.tuik_guard_fetch_flow_change()`

## `raw.tuik_key_template` — kısıtlar ve triggerlar

- **tuik_key_template_dsd_agency_dsd_id_dsd_version_fkey** (`f`): `FOREIGN KEY (dsd_agency, dsd_id, dsd_version) REFERENCES raw.tuik_dsd(agency_id, dsd_id, dsd_version)`
- **tuik_key_template_pkey** (`p`): `PRIMARY KEY (dsd_agency, dsd_id, dsd_version)`
- **tuik_key_template_template_kind_check** (`c`): `CHECK ((template_kind = 'structural_only'::text))`

## `raw.tuik_observation` — kısıtlar ve triggerlar

- **tuik_observation_artifact_id_fkey** (`f`): `FOREIGN KEY (artifact_id) REFERENCES raw.tuik_source_artifact(artifact_id)`
- **tuik_observation_artifact_ordinal_uq** (`u`): `UNIQUE (artifact_id, source_ordinal)`
- **tuik_observation_dataflow_fk** (`f`): `FOREIGN KEY (agency_id, flow_id, flow_version) REFERENCES raw.tuik_dataflow(agency_id, flow_id, flow_version)`
- **tuik_observation_dataset_attributes_check** (`c`): `CHECK ((jsonb_typeof(dataset_attributes) = 'object'::text))`
- **tuik_observation_dimension_values_check** (`c`): `CHECK ((jsonb_typeof(dimension_values) = 'object'::text))`
- **tuik_observation_observation_attributes_check** (`c`): `CHECK ((jsonb_typeof(observation_attributes) = 'object'::text))`
- **tuik_observation_pkey** (`p`): `PRIMARY KEY (observation_id)`
- **tuik_observation_series_attributes_check** (`c`): `CHECK ((jsonb_typeof(series_attributes) = 'object'::text))`
- **tuik_observation_series_key_check** (`c`): `CHECK ((length(series_key) > 0))`
- **tuik_observation_source_ordinal_check** (`c`): `CHECK ((source_ordinal > 0))`
- **tuik_observation_time_period_check** (`c`): `CHECK ((length(time_period) > 0))`

**Aktif triggerlar:**
- `tuik_observation_flow_guard`: `CREATE TRIGGER tuik_observation_flow_guard BEFORE INSERT OR UPDATE OF artifact_id, agency_id, flow_id, flow_version ON raw.tuik_observation FOR EACH ROW EXECUTE FUNCTION raw.tuik_assert_observation_flow()`

## `raw.tuik_observed_series_key` — kısıtlar ve triggerlar

- **tuik_observed_series_key_agency_id_flow_id_flow_version_fkey** (`f`): `FOREIGN KEY (agency_id, flow_id, flow_version) REFERENCES raw.tuik_dataflow(agency_id, flow_id, flow_version)`
- **tuik_observed_series_key_pkey** (`p`): `PRIMARY KEY (agency_id, flow_id, flow_version, series_key)`

## `raw.tuik_source_artifact` — kısıtlar ve triggerlar

- **tuik_artifact_run_hash_uq** (`u`): `UNIQUE (run_id, sha256, artifact_kind)`
- **tuik_source_artifact_artifact_kind_check** (`c`): `CHECK ((artifact_kind = ANY (ARRAY['sdmx_response'::text, 'sdmx_chunk'::text, 'other'::text])))`
- **tuik_source_artifact_byte_size_check** (`c`): `CHECK (((byte_size IS NULL) OR (byte_size >= 0)))`
- **tuik_source_artifact_pkey** (`p`): `PRIMARY KEY (artifact_id)`
- **tuik_source_artifact_response_metadata_check** (`c`): `CHECK ((jsonb_typeof(response_metadata) = 'object'::text))`
- **tuik_source_artifact_run_id_fkey** (`f`): `FOREIGN KEY (run_id) REFERENCES raw.tuik_fetch_run(run_id)`
- **tuik_source_artifact_sha256_check** (`c`): `CHECK ((sha256 ~ '^[0-9a-fA-F]{64}$'::text))`

**Aktif triggerlar:**
- `tuik_artifact_reparent_guard`: `CREATE TRIGGER tuik_artifact_reparent_guard BEFORE UPDATE OF run_id ON raw.tuik_source_artifact FOR EACH ROW EXECUTE FUNCTION raw.tuik_guard_artifact_reparent()`

## `raw.urap_artifacts` — kısıtlar ve triggerlar

- **urap_artifacts_byte_size_check** (`c`): `CHECK ((byte_size > 0))`
- **urap_artifacts_pkey** (`p`): `PRIMARY KEY (id)`
- **urap_artifacts_sha256_check** (`c`): `CHECK ((sha256 ~ '^[0-9a-f]{64}$'::text))`
- **urap_artifacts_sha256_key** (`u`): `UNIQUE (sha256)`
- **urap_artifacts_source_artifact_id_fkey** (`f`): `FOREIGN KEY (source_artifact_id) REFERENCES raw.source_artifact(artifact_id) ON DELETE RESTRICT`

**Aktif triggerlar:**
- `urap_artifact_source_check`: `CREATE TRIGGER urap_artifact_source_check BEFORE INSERT OR UPDATE OF source_artifact_id ON raw.urap_artifacts FOR EACH ROW EXECUTE FUNCTION raw.check_linked_artifact_source()`

## `raw.urap_editions` — kısıtlar ve triggerlar

- **urap_editions_edition_check** (`c`): `CHECK ((edition ~ '^[0-9]{4}-[0-9]{4}$'::text))`
- **urap_editions_edition_key** (`u`): `UNIQUE (edition)`
- **urap_editions_pkey** (`p`): `PRIMARY KEY (id)`
- **urap_editions_source_artifact_id_fkey** (`f`): `FOREIGN KEY (source_artifact_id) REFERENCES raw.urap_artifacts(id)`

## `raw.urap_metric_cells` — kısıtlar ve triggerlar

- **urap_metric_cells_cell_metadata_check** (`c`): `CHECK ((jsonb_typeof(cell_metadata) = 'object'::text))`
- **urap_metric_cells_observation_id_release_id_source_table_k_fkey** (`f`): `FOREIGN KEY (observation_id, release_id, source_table_key) REFERENCES raw.urap_ranking_observations(observation_id, release_id, source_table_key) ON DELETE RESTRICT`
- **urap_metric_cells_pkey** (`p`): `PRIMARY KEY (observation_id, metric_code)`
- **urap_metric_cells_release_id_source_table_key_metric_code_fkey** (`f`): `FOREIGN KEY (release_id, source_table_key, metric_code) REFERENCES raw.urap_release_metrics(release_id, source_table_key, metric_code) ON DELETE RESTRICT`

**Aktif triggerlar:**
- `urap_metric_cells_append_only`: `CREATE TRIGGER urap_metric_cells_append_only BEFORE DELETE OR UPDATE ON raw.urap_metric_cells FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.urap_metric_definitions` — kısıtlar ve triggerlar

- **urap_metric_definitions_display_order_check** (`c`): `CHECK (((display_order >= 1) AND (display_order <= 8)))`
- **urap_metric_definitions_display_order_key** (`u`): `UNIQUE (display_order)`
- **urap_metric_definitions_pkey** (`p`): `PRIMARY KEY (metric_code)`
- **urap_metric_definitions_unit_check** (`c`): `CHECK ((unit = 'URAP_SCORE'::text))`
- **urap_metric_definitions_value_kind_check** (`c`): `CHECK ((value_kind = 'SCORE'::text))`

## `raw.urap_metric_scores` — kısıtlar ve triggerlar

- **urap_metric_scores_metric_code_fkey** (`f`): `FOREIGN KEY (metric_code) REFERENCES raw.urap_metric_definitions(metric_code)`
- **urap_metric_scores_pkey** (`p`): `PRIMARY KEY (ranking_row_id, metric_code)`
- **urap_metric_scores_ranking_row_id_fkey** (`f`): `FOREIGN KEY (ranking_row_id) REFERENCES raw.urap_ranking_rows(id) ON DELETE RESTRICT`
- **urap_metric_scores_score_check** (`c`): `CHECK ((score >= (0)::numeric))`

## `raw.urap_publication_releases` — kısıtlar ve triggerlar

- **urap_publication_releases_edition_label_check** (`c`): `CHECK ((length(btrim(edition_label)) > 0))`
- **urap_publication_releases_metadata_check** (`c`): `CHECK ((jsonb_typeof(metadata) = 'object'::text))`
- **urap_publication_releases_pkey** (`p`): `PRIMARY KEY (release_id)`
- **urap_publication_releases_ranking_scope_check** (`c`): `CHECK ((length(btrim(ranking_scope)) > 0))`
- **urap_publication_releases_release_key_check** (`c`): `CHECK ((length(btrim(release_key)) > 0))`
- **urap_publication_releases_release_key_key** (`u`): `UNIQUE (release_key)`

**Aktif triggerlar:**
- `urap_publication_releases_append_only`: `CREATE TRIGGER urap_publication_releases_append_only BEFORE DELETE OR UPDATE ON raw.urap_publication_releases FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.urap_ranking_groups` — kısıtlar ve triggerlar

- **urap_ranking_groups_code_key** (`u`): `UNIQUE (code)`
- **urap_ranking_groups_pkey** (`p`): `PRIMARY KEY (id)`

## `raw.urap_ranking_observations` — kısıtlar ve triggerlar

- **urap_ranking_observations_observation_id_release_id_source__key** (`u`): `UNIQUE (observation_id, release_id, source_table_key)`
- **urap_ranking_observations_pkey** (`p`): `PRIMARY KEY (observation_id)`
- **urap_ranking_observations_raw_row_check** (`c`): `CHECK ((jsonb_typeof(raw_row) = 'object'::text))`
- **urap_ranking_observations_release_id_artifact_id_fkey** (`f`): `FOREIGN KEY (release_id, artifact_id) REFERENCES raw.urap_release_artifacts(release_id, artifact_id) ON DELETE RESTRICT`
- **urap_ranking_observations_release_id_artifact_id_source_tab_key** (`u`): `UNIQUE (release_id, artifact_id, source_table_key, row_ordinal)`
- **urap_ranking_observations_row_ordinal_check** (`c`): `CHECK ((row_ordinal >= 0))`

**Aktif triggerlar:**
- `urap_ranking_observations_append_only`: `CREATE TRIGGER urap_ranking_observations_append_only BEFORE DELETE OR UPDATE ON raw.urap_ranking_observations FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.urap_ranking_rows` — kısıtlar ve triggerlar

- **urap_ranking_rows_city_check** (`c`): `CHECK ((length(TRIM(BOTH FROM city)) > 0))`
- **urap_ranking_rows_edition_id_fkey** (`f`): `FOREIGN KEY (edition_id) REFERENCES raw.urap_editions(id)`
- **urap_ranking_rows_group_id_fkey** (`f`): `FOREIGN KEY (group_id) REFERENCES raw.urap_ranking_groups(id)`
- **urap_ranking_rows_pkey** (`p`): `PRIMARY KEY (id)`
- **urap_ranking_rows_source_artifact_id_fkey** (`f`): `FOREIGN KEY (source_artifact_id) REFERENCES raw.urap_artifacts(id)`
- **urap_ranking_rows_source_page_check** (`c`): `CHECK ((source_page > 0))`
- **urap_ranking_rows_source_rank_check** (`c`): `CHECK ((source_rank > 0))`
- **urap_ranking_rows_total_score_check** (`c`): `CHECK ((total_score >= (0)::numeric))`
- **urap_ranking_rows_university_name_check** (`c`): `CHECK ((length(TRIM(BOTH FROM university_name)) > 0))`
- **urap_rows_unique_artifact_rank** (`u`): `UNIQUE (source_artifact_id, group_id, source_rank)`
- **urap_rows_unique_rank** (`u`): `UNIQUE (edition_id, group_id, source_rank)`

## `raw.urap_release_artifacts` — kısıtlar ve triggerlar

- **urap_release_artifacts_artifact_id_fkey** (`f`): `FOREIGN KEY (artifact_id) REFERENCES raw.source_artifact(artifact_id) ON DELETE RESTRICT`
- **urap_release_artifacts_pkey** (`p`): `PRIMARY KEY (release_id, artifact_id)`
- **urap_release_artifacts_release_id_fkey** (`f`): `FOREIGN KEY (release_id) REFERENCES raw.urap_publication_releases(release_id) ON DELETE RESTRICT`

**Aktif triggerlar:**
- `urap_release_artifact_source_guard`: `CREATE TRIGGER urap_release_artifact_source_guard BEFORE INSERT OR UPDATE OF artifact_id ON raw.urap_release_artifacts FOR EACH ROW EXECUTE FUNCTION raw.guard_urap_release_artifact()`
- `urap_release_artifacts_append_only`: `CREATE TRIGGER urap_release_artifacts_append_only BEFORE DELETE OR UPDATE ON raw.urap_release_artifacts FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`

## `raw.urap_release_metrics` — kısıtlar ve triggerlar

- **urap_release_metrics_display_order_check** (`c`): `CHECK ((display_order >= 1))`
- **urap_release_metrics_metadata_check** (`c`): `CHECK ((jsonb_typeof(metadata) = 'object'::text))`
- **urap_release_metrics_pkey** (`p`): `PRIMARY KEY (release_id, source_table_key, metric_code)`
- **urap_release_metrics_release_id_fkey** (`f`): `FOREIGN KEY (release_id) REFERENCES raw.urap_publication_releases(release_id) ON DELETE RESTRICT`
- **urap_release_metrics_release_id_source_table_key_display_or_key** (`u`): `UNIQUE (release_id, source_table_key, display_order)`

**Aktif triggerlar:**
- `urap_release_metrics_append_only`: `CREATE TRIGGER urap_release_metrics_append_only BEFORE DELETE OR UPDATE ON raw.urap_release_metrics FOR EACH ROW EXECUTE FUNCTION raw.deny_mutation_immutable()`
