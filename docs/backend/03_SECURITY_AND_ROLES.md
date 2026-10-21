# Faz 1 — Kimlik, scopes ve PostgreSQL yetkileri

**Durum:** Öneri; hiçbir rol/grant/RLS veya secret bu fazda değiştirilmedi.
Mevcut geniş `atlas_ingest` yetkileri [Faz 0](00_CURRENT_STATE.md)'da kayıtlıdır.

## 1. Aktörler ve kimlik doğrulama

| Aktör | Kimlik | Policy |
|---|---|---|
| Anonim frontend/okuyucu | Yok | Yalnız `/v1` + temel health; publication gate ve rate-limit |
| Scraper | `X-Service-Key: key_id.secret` | `ingest:*` altındaki açık scopes + izinli source; run sahibi |
| ETL worker | Ayrı service key + özel DB hesabı | `jobs:claim/start/heartbeat/complete`, assigned lease/source; doğrudan DB istisnası pending |
| Monitoring servisi | Ayrı service key | Yalnız `metrics:read` |
| Operasyon otomasyonu | Ayrı service key | Yalnız verilmiş `ops:*`, `jobs:*` veya `publications:*`; source sınırı |
| İnsan operator/admin | Konfigüre provider'ın doğrulanmış Bearer JWT'si | Issuer + audience + signature + expiry + server allowlist scope mapping |

Service key bir kullanıcı parolası değildir. En az 32 random byte'lık secret,
kararlı key ID ile ayrılır; HMAC-SHA256 + ENV/secret-store pepper ile doğrulanır,
constant-time compare kullanılır. Faz 2 env registry server config'idir; secret
değerler kaynak koda/örneklere yazılmaz. Faz 3 DB registry yalnız digest/ID,
expiry, principal ve revocation metadata'sı tutar. Pepper plaintext key'lerle
aynı DB'de tutulmaz. DB-only registry geçişi önce mapping/rotation testi ister.

Prod insan operator JWT'si için provider belirlenmemiştir. Issuer/JWKS/audience
konfigüre edilmezse bu auth yolu kapalıdır. İstemcinin yolladığı `role` veya
`source_system` yetki kaynağı değildir. JWT yalnız allowlist algoritma ve server'ın
sabit issuer/JWKS adresiyle kontrol edilir; token'ın gösterdiği key URL'si fetch
edilmez. Cookie/session auth ilk sürümde yok; CSRF yaklaşımı auth değişirse tekrar
tasarlanır. Lokal CLI operator key'i insan login olmuş gibi raporlanmaz; aktör
`operator_service` olarak audit edilir.

Rotation: yeni key aç → consumer deploy → doğrulama → eski key revoke. Credential
oluşturma/rotation ilk sürümde owner-controlled CLI/secret-store prosedürüdür;
public veya genel CRUD endpoint değildir. Revocation sonraki request'i durdurur;
önceden doğrulanmış ve kısa transaction'a girmiş request için anlık iptal
garantisi verilmez. Eksik/expired/revoked key 401, scope eksikliği 403'tür.

## 2. Scope kataloğu ve nesne yetkisi

| Scope | Kullanım |
|---|---|
| `ingest:create`, `ingest:read`, `ingest:write`, `ingest:complete` | Source allowlist içinde yalnız kendi run'ı |
| `raw:manifest:read` | Kendi run'ı veya canlı assigned job'ın izinli input run'ı |
| `jobs:create`, `jobs:read`, `jobs:retry` | Ops principal'ın izinli source/run kapsamı |
| `jobs:claim`, `jobs:start`, `jobs:heartbeat`, `jobs:complete` | Kayıtlı worker/pipeline; lease ve principal eşleşmesi |
| `ops:ingestions:read`, `ops:quality:read`, `ops:lineage:read` | İzinli source metadata'sı; RAW/candidate payload hariç |
| `publications:read`, `publications:publish` | Release metadata / dry-run + apply |
| `metrics:read` | Auth gerektiren metrics |

Server, principal ID ve kaynak izinlerini doğrulamadan run/job sorgusu yapmaz.
Başkasının run'ı veya görünmeyen nesne 404 ile gizlenir; kaynak erişimine açık
olması mutasyon scope'u yerine geçmez. Bir worker, başka worker'ın fencing token'ı
ile çalışamaz. Fencing token random, DB'de digest saklanan ve loglanmayan bir
lease secret'ıdır; version ID ile karıştırılmaz.

M2M route'ları browser akışı olarak tasarlanmamıştır: `Origin` içeren service-key
isteği reddedilir; internal network/ingress kuralı ve credential ayrımı da gerekir.
CORS yalnız public read origin allowlist'idir, auth yerine geçmez. Default liste
boştur; `*` + credentials açılmaz. Prod HTTPS ve private DB network gerekir.
Production DB bağlantısı trusted CA/hostname doğrulamasıyla `sslmode=verify-full`
veya aynı doğrulamayı sağlayan platform bağlantı politikası kullanmalıdır;
yalnız encryption açmak kimlik doğrulayan TLS sayılmaz. Yerel `trust` HBA ve SSL
off ayarları production profiline taşınmaz. TLS reverse proxy'de sonlanırsa
forwarded headers yalnız konfigüre proxy'den kabul edilir.

## 3. Önerilen DB hesap matrisi

| Hesap | İzin verilen erişim | Verilmeyecek yetki |
|---|---|---|
| `atlas_api` (mevcut) | 9 mevcut `api.*` view SELECT (TÜİK il nüfusu dahil); yeni sanitized publication status view SELECT | RAW, CORE/STAGING doğrudan erişim, platform credential/audit, yazma, DDL |
| `atlas_ingest` (daraltılacak) | RAW SELECT/INSERT; run status/completed_at/details UPDATE; gerekli ownership/response/observation/artifact/idempotency metadata; audit INSERT; identity sequence USAGE | STAGING/CORE/QUALITY yazma/okuma, genel DELETE/TRUNCATE/DDL, credential digest erişimi |
| `atlas_platform` (yeni) | Açık platform tablo/grants listesi; auth registry SELECT; job/publication/idempotency/audit işlemleri; sanitized ingestion/quality ops view SELECT | CORE/STAGING/RAW payload yazma, app-time DDL, genel kalite çözümü |
| `atlas_etl` (yeni) | RAW SELECT; onaylı STAGING/CORE/QUALITY SELECT/INSERT/UPDATE ve sequences; gate/lease metadata'nın dar görünümü | RAW body değiştirme, credential erişimi, platform grants/DDL, genel DELETE/TRUNCATE |
| `atlas_analytics` (mevcut) | Mevcut CORE/API read + analytics CREATE; bağımsız DE işi | RAW/secret metadata; ingest/admin credential |
| `atlas_owner` (mevcut) | Owner-controlled migration/bootstrap/restore | API veya worker runtime kimliği olarak kullanım |

`atlas_ingest`'in STAGING/CORE/QUALITY mevcut grants'i **ve** `atlas_owner` default
grants'i daraltılmalıdır. `atlas_etl` grants'i yalnız açık tablo listesine verilir.
Platform tablolarına `GRANT ALL ON ALL TABLES` önerilmez; role membership ile
superuser/broad account miras alınmaz. Application rolü table owner veya
`BYPASSRLS` olmaz.

Ingest'e kendi SQL transaction'ında yazdığı operational tablolar için gereken
kolon/işlem izinleri verilir; control pool'da audit yazıp RAW'ın başka pool'da
commit edilmesi kullanılmaz. Public read hesabı platform secret tablolarını
okumaz; status/coverage yalnız owner-created sanitized view'dan gelir.

Least privilege DB katmanında read/write/DDL sınırını zorlar. Bir API DB login'i
birçok HTTP principal adına çalışacağı için source/run sahipliği ilk sürümde API
repository policy'sinde uygulanır. DB parolası yalnız trusted backend/worker'a
verilir. Müşteri başına DB erişimi gerekiyorsa ayrı role/RLS tasarımı gerekir;
bu sürüm çok kiracılı doğrudan DB güvenliği sunduğunu iddia etmez.

CORE gate cooperative protokoldür. ETL credential'ını eski loader'a veya gate'i
atlayan manuel SQL'e vermek publication güvenliğini bozar. İstisna onayı,
runner'ın start-before-write ve lock/lease/recovery kabul testlerine bağlıdır.

## 4. Validator, SQL ve secret koruması

- Metadata DTO'larında bilinmeyen alanlar reddedilir; kaynak JSON gövdesindeki
  bilinmeyen alanlar korunur. Raw UTF-8 JSON duplicate key/non-finite sayılarını
  kabul etmez; sayı parse/serialize işleminde precision kaybı olmamalıdır.
- Method/endpoint/source/entity, server registry'ye bağlıdır. URL/path kullanıcıdan
  gelip fetch edilmez. Kaynak secret/header/cookie body metadata'sına alınmaz.
- SQL değerleri parametriktir; sort/filter/identifier server allowlist'inden gelir.
  Error cevabı SQL, credentials, RAW field değeri veya stacktrace içermez.
- Artifact ID server üretir. Traversal, absolute path, symbolic link kaçışı ve
  unbounded dosya gövdesi reddedilir. Private dosya content'ine public route yok.
- CORS, proxy allowlist, body/depth/batch/rate/pool/time limits [mimaride](01_ARCHITECTURE.md)
  yazılıdır. Config'de secret veya required DSN eksikliği boot'u başarısız yapar.
- Runtime'da admin DB hesabı verilmişse uygulama fail closed olur; otomatik
  migration, role yaratma veya superuser fallback yoktur.

## 5. Zorunlu güvenlik kabul kontrolleri

Service key yanlış/expired/revoked, wrong source, wrong run owner, wrong worker,
stale lease, operator JWT issuer/audience/expiry/algorithm ve browser M2M denemesi
reddedilmeli. Public read credentials istememeli ve RAW/secret taşımamalı.
Gerçek DB hesabıyla API/ingest CORE yazma ve DDL girişimleri reddedilmeli;
ETL RAW UPDATE/DELETE yapamamalı. Default grants testi yeni bir test tablosu ile
yalnız izole test DB'de çalıştırılmalı. Metadata secret/audit grants'i ve log
redaction negatif senaryolarla doğrulanmalı.

DB ve auth değişiklikleri [04_METADATA_CHANGE_PROPOSAL.md](04_METADATA_CHANGE_PROPOSAL.md)
owner onayına tabidir; bu güvenlik belgesi uygulanmış güvenlik testi yerine geçmez.
