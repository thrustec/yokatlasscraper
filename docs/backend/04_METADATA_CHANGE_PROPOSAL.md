# Faz 1 — Owner onayı bekleyen metadata ve rol değişiklikleri

**Durum:** Tasarım önerisi; executable migration hazırlanmadı/uygulanmadı.
Mevcut 17 tablo, 8 view ve RAW unique index korunacaktır. CORE/STAGING/ANALYTICS
semantik alan, FK veya dönüşüm değişikliği bu önerinin kapsamı değildir.

## 1. Onay grupları

| Grup | Öneri | Etki / onay |
|---|---|---|
| A — servis rolleri | `atlas_ingest` daraltma + default grants; yeni `atlas_etl`, `atlas_platform`; API için sanitized publication SELECT | Mevcut loader geniş hesaba bağımlı. Scraper/DE/DB owner koordinasyonu ve ayrı uygulama onayı |
| B — kabul metadata'sı | Yeni `platform` şemasında kimlik/source grant, run ownership, response metadata/observations, artifact, idempotency, audit | RAW yazımına eşlik eden additive metadata. Legacy RAW'a toplu rewrite/backfill yok |
| C — iş/yayın metadata'sı | Jobs/attempts, publications/read_model_state, migration ledger; operator/worker/public status view'ları | Job/gate adapter ve yayın protokolü DE kabulü ister |

Faz 2 iskeleti bu grupları uygulamadan geliştirilebilir. Enabled ingestion/job/
gated catalog özellikleri için ilgili gruplar uygulandıktan sonra gerçek integration
testleri gerekir. Onaylanan grup dışında otomatik schema create yoktur.

## 2. Platform tablo taslakları

Adlar/kolonlar final migration review'da sabitlenecek; aşağıdakiler önerilen
mantıksal sözleşmedir. UUID metadata kimlikleri, BIGINT RAW referansları ve
`timestamptz` zamanlar; immutable body JSON ve mutable lifecycle alanları ayrılır.

| Tablo | Anahtar / temel kolonlar | Kısıt ve erişim |
|---|---|---|
| `principals` | `principal_id UUID PK`, kind, display_key, enabled, created_at; human issuer/subject nullable | Unique service key / `(issuer,subject)`; scopes kullanıcı body'sinden alınmaz |
| `service_credentials` | key_id PK, principal FK, secret_digest, digest_algorithm, expires_at, revoked_at | Plaintext secret/pepper yok. Yalnız control auth reader ve owner rotation |
| `principal_source_grants` | `(principal_id,source_system,scope) PK` | Scope/source allowlist server registry ile doğrulanır; runtime credential yönetimi CRUD değildir |
| `ingestion_ownership` | ingestion_run_id PK/FK `raw.ingestion_runs`, principal FK, source_policy_revision | Creator immutable; legacy run otomatik bir principal'a mal edilmez |
| `response_metadata` | api_response_id PK/FK, response_hash_kind, record_hash_algorithm, source_policy_revision, expected_record_count | Yeni hash semantiği explicit; legacy metadata yoksa unknown; append-only |
| `response_observations` | observation_id UUID PK, run/response FK, request_signature, redacted request JSON, captured_at, reference_year nullable, artifact FK | Run→response tekrarları ayrı. Source entity/record count ve verified byte hash taşır; immutable |
| `artifacts` | artifact_id UUID PK, storage_key, byte_sha256, byte_count, content_type, state, created_at | Server-generated key; staged/committed/orphaned. Host absolute path public değildir |
| `request_idempotency` | `(principal_id,route_key,key) PK`, command_fingerprint, response_status/body, created_at, expires_at | Unique claim; success result aynı transaction'da; stored response secret içermez |
| `jobs` | job_id UUID PK, pipeline_key/revision, execution_lane, input_signature, run_ids, status, creator, created_at | Active `(pipeline_revision,input_signature)` tekil; CORE lane'de leased/running tekil; queued işleri seri claim et |
| `job_attempts` | `(job_id,attempt_no) PK`, worker principal, lease_digest, fencing_epoch, lease_expires_at, backend_pid, progress/result, timestamps | Assigned worker/lease; secret token saklanmaz; terminal sonuç immutable |
| `publications` | publication_id UUID PK, job/attempt FK, validation attestation, coverage JSON, status, actor/published_at | Candidate bağlamı ve DTO contract revision; published veri özeti immutable |
| `read_model_state` | singleton `model_key PK` (`catalog`), state, epoch, current_publication FK nullable, active_job nullable | Durum/epoch update compare-and-set; empty/ready/updating/awaiting_publication/failed |
| `audit_events` | event_id BIGINT identity PK, request_id, principal, operation, target key, outcome/code, created_at | Append-only; key secret, RAW body, request credentials/SQL parametreleri yok |
| `schema_migrations` | version PK, checksum, applied_at, applied_by, deployment_revision | Owner migration işlemi yazar; runtime yalnız beklenen sürümü kontrol eder |

`run_ids` ilişkisinin fiziksel modeli migration review'da FK'li job-input junction
table olabilir; JSON array ile FK bütünlüğü varmış gibi davranılmayacaktır. Eğer
junction table seçilirse tablo sayısı bu taslağın üstüne çıkar ve review'a açıkça
yazılır. Job input'ları immutable ve server normalize edilmiş sıralı/tekrarsız run
kümesi olur. General JSON SQL veya caller module adı job input değildir.

Önerilen sanitized view'lar:

- `platform.publication_status`: public/read hesabına yalnız state, epoch,
  publication_id, published_at ve onaylı coverage.
- `platform.ingestion_status`: ops'a run/source/status/count/timestamp; RAW JSON yok.
- `platform.quality_status`: ops'a check/quarantine metadata sayımı; candidate JSON yok.
- `platform.worker_job_guard`: worker'a yalnız kendi yürütme doğrulaması için
  gerekli job/attempt/expiry/state; credentials/audit yok.

## 3. İndeks ve preflight planı

Önce existing DDL/roles/default ACL ve migration sürümü tekrar alınır.
Metadata PK/FK referansları, job active/lane unique, idempotency unique ve queue
`(status,created_at,job_id)` erişimi tasarım kaynaklı indeks adaylarıdır. CORE
filtre/sort indeksleri gerçek veriyle EXPLAIN/latency ölçülmeden eklenmez.

Preflight: existing grants genişliği, bağımlı loader/servis hesapları, legacy run
ownership eksikliği, source/hash provenance sınıflandırılamayan response'lar ve
gate'i atlayan mevcut CORE writer'ları raporlanır. Eski RAW unique indexi silmek,
CORE FK/year constraints eklemek veya hash'leri rewrite etmek önerilmez.

## 4. Uygulama/deploy sırası

1. Owner, A/B/C kapsamını ve doğrudan worker DB istisnasını onaylar; DE runner
   job/gate contract'ını kabul eder. Mevcut loader kullanım geçişi duyurulur.
2. İzole PostgreSQL 17 test DB'sinde versiyonlu additive migration ve explicit
   grants hazırlanır. FK/unique/default grants, idempotency/concurrency ve
   eski read-only tüketici uyumu test edilir.
3. Mevcut/kalıcı DB için yedek + preflight alınır. Yeni schema/metadata/hesaplar
   eklenir; legacy kayıtlar değiştirilmez. `read_model_state` başlangıcı `empty`;
   mevcut CORE verisi kendiliğinden approved publication sayılmaz.
4. Uyumlu API/worker deploy edilir; route feature flag'leri ve source/pipeline
   registry önce kapalıdır. Yeni servis credentials ilgili secret store'a alınır.
5. Eski CORE writer durdurulup verified runner'a geçiş sağlandıktan sonra ingest
   grants/default grants daraltılır. DB hesabını boşa çıkarmak yerine geçiş
   bağımlılığı/test kanıtı kaydedilir.
6. Ingest/job/read features owner-approved ortamda açılır; ilk veri publication'ı
   dry-run/apply ile yapılır. Değişiklik current_schema/reference/OpenAPI/runbook'a
   yansıtılır; main hedefli PR üzerinden review edilir.

## 5. Geri dönüş ve forward-fix

İlk geri dönüş feature flag'leri kapatmak ve önceki read-only uygulamaya dönmektir;
metadata/RAW kayıtları korunur. Migration ledger/checksum ve deployment revision
birlikte kontrol edilir. Üretimde tablo drop/cascade veya geniş eski yetkileri
otomatik geri verme bir rollback prosedürü sayılmaz.

Eksik/yanlış grant forward-fix migration ile düzeltilir. Veri repair/restore DE ve
DB owner'ın onaylı prosedürüdür. Platform tablolarını kaldıracak down migration,
veri/bağımlılık etkisiyle ayrıca onay ister. İlk onay yalnız additive öneriyi
uygulamaya yetki verebilir; destructive işlem, production erişimi veya deploy
onayı içermez.

## 6. Kabul kanıtları

Migration up/reapply/checksum, test DB'de grant/default grant ve rollback/forward-fix
provası; dört ayrı runtime hesabıyla negatif yazma/DDL testleri; legacy RAW
unchanged; same-key/byte duplicate, incomplete children ve concurrent claim;
session kaybında fail-closed read; stale token/epoch/publish plan reddi;
secret redaction ve metadata view projections. Bu kanıtlar Faz 3/4'te üretilecektir.
