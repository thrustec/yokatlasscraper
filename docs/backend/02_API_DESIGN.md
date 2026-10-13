# Faz 1 — API sözleşmesi taslağı

**Durum:** Tasarım; endpoint'ler henüz uygulanmış değildir. Normatif makine
sözleşmesi [openapi.yaml](openapi.yaml), operation envanteri
[ENDPOINT_CATALOG.md](ENDPOINT_CATALOG.md), runtime kabul senaryoları
[CONTRACT_TEST_PLAN.md](CONTRACT_TEST_PLAN.md)'dir.

## 1. Yüzeyler, aktörler ve sürüm

- `/v1`: anonim katalog/read API. Kullanıcının 13 Ekim 2026 tercihidir.
- `/internal/v1`: scraper/worker M2M. Scope + source + owner/assigned lease.
- `/ops/v1`: yetkili operator/automation. OpenAPI'de service key veya doğrulanmış
  operator Bearer kabulü; publish/retry preview ve apply ayrılmıştır.
- `/health/live`, `/health/ready`: minimal servis health; credential/config açığa çıkmaz.

HTTP API revizyonu `v1`; read DTO revision publication metadata'sına bağlıdır.
Breaking değişiklik yeni major path/contract ister; additive alanların consumer
tarafından tolere edilmesi belgelenir. Deprecation/migration penceresi owner ile
kararlaştırılmadan endpoint kaldırılmaz. `localhost:8000` OpenAPI server URL'si
planlanan development adresidir, mevcut çalışan servis iddiası değildir.

## 2. Ortak biçimler ve validation

BIGINT DB kimlik/sayı/alanları decimal string; UUID metadata kimlikleri string;
`yil` integer, double alanlar number/null. DTO'lar yalnız allowlist field'ları
taşır. SQL/source isimleri korunur: `kilavuz_kodu`, `yil`, `puan_turu` gibi.
JSON `null` veri yokluğudur; `0` ile değiştirilmez. Program detay doğal kimliği
`/v1/programs/{kilavuz_kodu}/{yil}`; net DTO'da doğrulanmamış tarihsel ad join'i yoktur.

Metadata request'lerinde unknown field, type, duplicate key ve non-finite sayı
reddedilir. Raw JSON içindeki yeni source field'ları korunur. Array/JSON depth/body
sınırları [mimaride](01_ARCHITECTURE.md); base64 doğrulaması ve record sayısı server'da
yeniden yapılır. `yil` query'si dört haneli takvim yılıdır, sabit 2026 default'u yok.

Success response'ta request-specific correlation ID yerine `X-Request-ID` header'ı
kullanılır; cache body'leri request ID yüzünden değişmez. Error formatı:

```json
{"error":{"code":"VALIDATION_ERROR","message":"İstek alanları geçersiz.","request_id":"00000000-0000-4000-8000-000000000001","details":[{"field":"yil","reason":"required"}]}}
```

Örnekler contract fixture'dır; kaynak iş verisi veya çalıştırılmış endpoint sonucu
değildir. Error'da gönderilen secret/RAW değerleri, SQL veya stacktrace yer almaz.
401 auth, 403 scope, 404 görünmeyen/missing object, 409 conflict/stale state,
413 size, 422 body/query semantics, 429 rate-limit, 503 dependency/capability/gate
kategorileridir; her operation yalnız ilgili kodları belirtir. 500 güvenli genel
internal error'dur. Hata cevabı `no-store`, 429 ve geçici 503 `Retry-After` taşır.

## 3. Read API

Sekiz mevcut DB view'ı dokuz public read operasyonuna kaynak olur: üniversite,
il, program grubu, program liste/detay, net listesi, iki yıl özeti, coverage.
Koşullar view'ı veya doğrulanmış yerleşen/doluluk read modeli olmadığı için bunlar
ilk sözleşmeye eklenmez. `remaining_fields` ve RAW payload public değildir.

Sayfalama: default 50, max 100; signed cursor. Cursor publication/filter/sort'a
bağlıdır, son sort değerleri + stable ID taşır. `rank_asc`, `score_desc`,
`quota_desc`, `id_asc` server allowlist'ine karşılık gelir; nullable değerlerde
NULLS LAST ve stable tie-break uygulanır. Caller SQL kolon adı gönderemez.
Toplam sayım, aynı gated read içinde exact DB count; filtre/yıl sonuç vermiyorsa
200 empty items ve `YEAR_NOT_COVERED` uyarısı, detail için 404.

Stable default sıralar: üniversite `universite_id`, il `il_kodu`, program grubu
`(birim_grup_id,puan_turu)`, program `program_version_id`, net `net_result_id`,
özet `(yil,puan_turu)`, hepsi ascending. Business sort sonuna generated program
ID tie-break eklenir. Internal/ops metadata liste count + rows aynı request'te
repeatable read kullanır; cursor'ları immutable public publication garantisi
taşımaz. Manifest tamamlanmış run için sabittir; own running run'a yeni observation
eklenebilir. Lineage page yalnız observations'ı sayfalar; bounded related ID
listelerindeki eksiklik `truncated:true` ile açıkça gösterilir.

Response `meta`: publication UUID, published_at, requested_year nullable,
available_years, warnings; `page`: total_count string, limit ve next_cursor null/string.
Yayın değişiminde eski cursor 409 `SNAPSHOT_CHANGED`; filtre mismatch/expired
cursor 400. Her response referans yılını açık taşır; başka yıla fallback yapılmaz.

Publication `ready` değilken veri route'ları 503 döner. Coverage 200 ile state'i
gösterebilir; unpublished sayımlar `null`, available_years boş, uyarı vardır.
`api.program_year_summary.avg_min_puan` simple SQL average; `total_kontenjan`
yerleşen sayısı değildir. Net özetinin mean alanları kişi bazında türetilmiş
placement metriği gibi yeniden adlandırılmaz.

ETag release/query/DTO revision'a bağlıdır; `If-None-Match` desteği 304 döndürebilir.
Cache-Control public max-age=60 ilk öneridir. Önce publication gate kontrol edilir;
kapalı gate 304 vermez. Public payload'da secret/RAW/source request/actor kimliği yoktur.

## 4. Scraper kabul protokolü

1. `POST /internal/v1/ingestions`, source + scraper version ile own run açar.
2. `POST .../{run_id}/responses`, registered request metadata, capture timestamp,
   HTTP status, base64 response ve SHA-256 taşır. Kaynak entity/array path server
   policy'den gelir; caller parçalı records/body göndermez. Her response'ın bütün
   source_records satırları aynı SQL commit'te saklanır.
3. Yeni response 201 `stored`; verified existing response 200 `duplicate` ve yeni
   observation. Byte hash, record count, response/observation ID ve request signature
   receipt'te döner. Hash conflict/incomplete children 409; overwrite/repair yok.
4. `POST .../{run_id}/complete`, completed/partial/failed outcome'u ile run'ı kapatır.
   Completed demek ETL published demek değildir. Hata kodu ve beklenen response
   sayısı varsa server observation sayımıyla tutarlı olmalıdır; başka run kapatılamaz.
5. Own run veya assigned worker input manifest'i internal read ile sorgulanır.

Mutasyonlarda `Idempotency-Key` zorunlu; aynı key/command aynı result replay'i,
farklı command 409. Yeni capture için yeni key ve captured_at gerekir. Bounded
retry/backoff 429/503/ACK kaybında aynı key ile; validation/conflict düzeltilmeden
retry edilmez. [Hash/idempotency ADR](adr/0003-ingestion-identity-and-hashes.md).
`route_key`, method + normalize edilmiş tam resource path'idir. Auth/source/owner
kontrolü replay lookup'tan önce yapılır. Heartbeat'in her yeni uzatma komutu yeni
key kullanır; ACK kaybında yalnız o komutun key'i tekrar kullanılır.

## 5. Worker ve operasyon protokolü

Ops job create run'ların source/status ve pipeline registry'sini kontrol eder,
202 queued/Location döner. Partial run default reddedilir; ayrı allow-partial
scope/policy kararı olmadan ETL'ye gönderilmez. Worker claim 200 lease veya 204
no job; `start` exclusive gate PID + lease ile, heartbeat/complete aynı assigned
token ile çalışır. Header `X-Job-Lease` secret'tır ve loglanmaz.

Successful completion DE validation/coverage attestation'ı taşır, candidate
publication oluşturur. Gate/lease bütünlüğü, stale claim ve model state kuralları
[ADR-0004](adr/0004-jobs-and-publication-gate.md)'te normatiftir. Adapter yoksa job
fake success olmaz; `PIPELINE_NOT_CONFIGURED`/capability hatası döner.

Ops retry/publication request'lerinde `dry_run` default true. Apply `dry_run:false`
ve 5 dakika geçerli signed plan token ister; object/version/epoch tekrar
doğrulanır. Retry ayrı attempt üretir; aynı input otomatik çift çalıştırılmaz.
Preview ve apply farklı command olduğundan ayrı idempotency key kullanır. Plan
süresi geçse de zaten commit edilmiş apply'nin aynı key/body replay'i ilk receipt'i
döndürebilir; domain mutasyonu tekrar çalıştırılmaz. Dry-run domain state'i veya
queue'yu değiştirmez; private idempotency receipt/audit kaydı tutabilir.
Expired/partial CORE için DE recovery onayı yoksa `CORE_REPAIR_REQUIRED`.
Delete, restore, truncate ve metadata pointer rollback endpoint'i ilk sürümde yoktur.

Quality/lineage/ingestion ops route'ları payload içermeyen metadata döndürür.
Quarantine çözümü/kalite kararı Data Engineer kapsamıdır. Metrics private scope
ile Prometheus text formatı döndürür; request secrets ve keyfî run ID label'ı yoktur.

## 6. Entegrasyon ve kabul

| Tüketici | Teslim |
|---|---|
| Scraper | OpenAPI, size/rate/body-byte hash/record pointer policy, own-run scopes, receipt + retry örnekleri |
| DE worker | Typed job/lease/start/complete, dedicated DB istisnası, validation attestation ve gate/recovery kabul senaryoları |
| Frontend | Anonim read DTO, signed pagination, year/null/coverage/503 ve cursor restart kuralları; raw/secret içermez |
| Operator | Ops scopes, preview token ve idempotent apply, health/metrics/lineage, manual recovery sınırı |

OpenAPI shape/fixture doğrulaması, gerçek endpoint/DB/concurrency/security
testinin yerine geçmez. Runtime test matrisi her operation için normal,
bozuk giriş, ilgili auth/ownership, replay ve eşzamanlılık senaryolarını tanımlar.
Faz 2 health/auth zemini, Faz 3 iş uçları; schema/grants ve adapter kabulü ayrı
önkoşuldur. Doğrulama raporu [05_DESIGN_REVIEW.md](05_DESIGN_REVIEW.md)'te tutulacaktır.
