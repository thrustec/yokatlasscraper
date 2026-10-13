# Faz 1 teslim ve tasarım incelemesi

**Tarih:** 13 Ekim 2026. **Başlangıç HEAD:** `a059a45`.
**Branch:** `feat/backend-local-postgres-20261013`, güncel `origin/main` tabanlı.
Bu aşamada uygulama, migration, PostgreSQL role/grants veya source dataset
değiştirilmedi. Yalnız tasarım/contract ve bunların doğrulama araçları hazırlandı.

## 1. Teslimler

| Dosya | İncelenecek karar |
|---|---|
| [01_ARCHITECTURE.md](01_ARCHITECTURE.md) | Python/FastAPI modüler API + ayrı worker; pool/transaction ve yayın gate'i |
| [02_API_DESIGN.md](02_API_DESIGN.md) | Public/internal/ops sürümleri, DTO, null/yıl/cursor/error/idempotency ve ekip entegrasyonu |
| [03_SECURITY_AND_ROLES.md](03_SECURITY_AND_ROLES.md) | M2M/operator kimlikleri, source/run/job scopes ve ayrı DB hesapları |
| [04_METADATA_CHANGE_PROPOSAL.md](04_METADATA_CHANGE_PROPOSAL.md) | Owner onayı bekleyen A/B/C rol/metadata/deploy kapsamı |
| [ADR envanteri](adr/README.md) | Framework, DB istisnası, hash/replay ve worker/publication karar gerekçeleri |
| [openapi.yaml](openapi.yaml) | OpenAPI 3.1.0; 28 path, 30 operation, 68 schema; hepsi planned |
| [ENDPOINT_CATALOG.md](ENDPOINT_CATALOG.md) | Her operation aktörü/scopes, input/success, object policy ve transaction |
| [CONTRACT_TEST_PLAN.md](CONTRACT_TEST_PLAN.md) | Her operation için beş acceptance senaryosu kategorisi; runtime'da henüz çalıştırılmadı |
| [contract_fixtures.json](contract_fixtures.json) | 18 synthetic positive/negative schema örneği; gerçek kaynak verisi değil |
| [canonical_hash_vectors.json](canonical_hash_vectors.json) | 7 exact numeric/Unicode canonical golden vector ve reject girdileri |
| [validate_design.py](validate_design.py) | Endpoint çağırmadan/DB yazmadan OpenAPI, fixture, policy ve link kontrolü |
| [validation_requirements.lock.txt](validation_requirements.lock.txt) | Kullanılan validator ortamının sabitlenmiş bağımlılıkları |
| [Validation kanıtı](evidence/2026-10-13_design_validation.json) | Yapılan kontroller ve test edilmemiş runtime sınırı |

## 2. Kullanıcı tercihi ve önerilen ana kararlar

**Kullanıcı tarafından seçildi:** Katalog, üniversite ve net sonuçları okumaları
anonim. Ingestion/ops/worker her durumda auth + scope/nesne kontrolü gerektirir.

Uygulama için öneriler:

1. Python 3.13 + FastAPI/Pydantic/Psycopg, ayrı API/worker process, ilk ortam tek
   API process. Redis/Kafka/Celery eklemeye ihtiyaç kanıtlanmadı.
2. Scraper API-first RAW teslimi; yalnız DE runner için ayrı `atlas_etl` DB
   istisnası. Backend ETL/mapping/KPI mantığını yazmaz.
3. Original HTTP byte hash'i, sürümlü record canonical hash'i, request signature
   ve run→response observations ayrı. Legacy RAW/index korunur.
4. Mevcut CORE snapshot'lı olmadığı için update/partial failure boyunca public
   read kapalıdır; DE validation adayı operator dry-run/apply ile yayınlar.
   Kesintisiz tarihsel snapshot veya otomatik rollback iddiası yoktur.
5. Yeni platform metadata ve ayrı servis grants'i Faz 3 owner onayıyla uygulanır.
   Eski geniş loader hesabı geçişi yapılmadan sessizce daraltılmaz.

## 3. Doğrulananlar ve sınırlar

OpenAPI `openapi-spec-validator 0.8.5` ile geçti. 18 fixture JSON Schema 2020-12
ile beklenen accept/reject sonucunu verdi; malformed hash, unknown metadata,
missing failure code/plan/attestation, duplicate coverage entity ve numeric BIGINT
response gibi senaryolar kapsam içindedir. Byte-input fixture base64/SHA-256'sı
doğrulandı. Yedi golden vector exact `Decimal` değer eşitliği ve beklenen
canonical UTF-8 hash'i açısından kontrol edildi.

Private route security/scopes ve 401/403, public route anonim policy, mutation
idempotency header, required path input, unique operation ID, acceptance test
kategorileri ve relative Markdown linkleri kontrol edildi. Live schema dump'ı
Faz 0 dump'ıyla normalize edilerek yeniden karşılaştırıldı: aynı kaldı.

Bu sonuçlar gerçek HTTP endpoint, SQL mutasyon, concurrency, role migration veya
worker adapter çalıştırması değildir. Canonical runtime encoder henüz yazılmadı;
reject vector'ları/producer golden tests uygulama sırasında koşulacaktır. Human
OIDC provider, DE pipeline adapter, source onayları ve production ortamı henüz
harici bağımlılıktır. Public snapshot eski sürümünün kesintisiz sunulması bu
ilk gate modelinin sunduğu özellik değildir.

Validation ortamı E: üzerindeki ayrı lokal araç venv'inde kuruldu; uygulama
runtime dependency'leri yüklenmedi. Repo checkout'undan tekrar doğrulama:

```powershell
python -m venv .local-backups/design-validator
.\.local-backups\design-validator\Scripts\python.exe -m pip install -r docs/backend/validation_requirements.lock.txt
.\.local-backups\design-validator\Scripts\python.exe -X utf8 docs/backend/validate_design.py
```

## 4. Açık onay ve bağımlılık listesi

| Konu | Mevcut durum | Sonraki somut adım |
|---|---|---|
| Faz 2 backend iskeleti | Aşama onayı bekleniyor | Config/read pool/health/errors/auth abstraction ve test zemini |
| A/B/C metadata + roles | Uygulama onayı yok | Migration taslağı/preflight/grants testleri, owner review |
| ETL direct DB exception | Koşullu öneri | DE runner gate/start/lease/recovery contract kabulü + owner onayı |
| Human operator auth | Provider belirlenmedi | OIDC issuer/audience/JWKS ve scope mapping seçimi; kapalı provider yolu |
| DE pipeline | Adapter teslim edilmedi | Kayıtlı pipeline revision, validation attestation ve recovery policy |
| Test veri hacmi | Yerel DB boş | Owner/DE onaylı arşiv/snapshot, ayrı import/load-test aşaması |
| Dış kaynaklar | Taslak PR #2'de PENDING | Kaynak sahibi seçim/alan/erişim onayı; backend source-independent kalır |
| C: Docker depolama | Ayrı operasyon işi | Kullanıcı isterse yedekli taşıma/küçültme planı; bu fazda işlem yok |

**Önerilen bir sonraki aşama Faz 2'dir:** backend iskeletini mevcut read DB ile
kurmak. Gated catalog/ingestion/job metadata gerektiren capabilities, yeni
schema/grants onayı ve migration uygulanana kadar kapalı kalır. Kritik DB
değişiklikleri ve üretim deploy'u Faz 2 onayı içine örtülü olarak dahil edilmez.

Kullanıcının her aşamada onay isteği doğrultusunda tasarım belgeleri sunulup
Faz 2 onayı beklenir. Bu backend branch'i için push/PR teslimi henüz yapılmadı;
yerel commit kimliği aşama sonunda kullanıcıya raporlanır.
