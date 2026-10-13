# ADR-0004 — Kalıcı jobs ve mutable CORE yayın gate'i

**Durum:** Öneri; DE adapter kabulü ve platform metadata onayı bekleniyor.

CORE'da snapshot_id yok; mevcut view'lar mutable veriyi okur. İlk sürüm eski
publication ID'sinden tarihsel veri sunamaz. Karar: güncelleme/partial failure
boyunca public katalog kapalı, successful validated candidate operator apply
ile açılır. Immutable/versioned read model gelecekte DE'nin ayrı işi olacaktır.

## Job claim ve execution

1. API kayıtlı `pipeline_key` + source/run input'larını doğrular; queued job'ı
   idempotent olarak yaratır. Aynı pipeline revision/input için bir active job
   unique kuralı duplicate active çalışmayı engeller.
2. Worker `claim` çağırır. Control transaction uygun satırı
   `FOR UPDATE SKIP LOCKED` ile claim eder; principal'a bağlı random lease token
   digest'i ve fencing epoch üretir. Claims yalnız queue için kullanılır; katalog
   okumalarında locked row atlama yapılmaz.
   Claim ACK kaybında aynı principal'ın hâlâ `leased`, henüz başlamamış assignment'ı
   bulunur; yeni token/epoch ile yeniden teslim edilir, ikinci job claim edilmez.
   Eski token geçersiz olur. Zaten `running` assignment için claim token'ı yeniden
   verilmez; worker mevcut token'ıyla heartbeat sürdürür veya recovery gerekir.
3. CORE writer worker dedicated `atlas_etl` session'ında sabit `(7488,1)` advisory
   exclusive gate'i alır. API `start` body'deki backend PID'nin ilgili kilidi
   taşıdığını ve rolün `atlas_etl` olduğunu kontrol eder; state `updating` olur.
   Start ACK gelmeden CORE yazılmaz.
4. DE adapter aynı dedicated session'da kısa batch transaction'ları kullanır.
   Heartbeat 20s, lease 60s öneridir; her batch öncesi lease kontrolü gerekir.
5. `complete(succeeded)` validation/coverage attestation taşır, candidate oluşturur
   ve state'i `awaiting_publication` yapar. Failed/partial sonucu `failed` yapar.
   Worker ACK sonrasında gate/session'ı finally içinde kapatır.

PostgreSQL queue locking ve advisory lock ömürleri resmî dokümanlarda açıklanır.
[SELECT](https://www.postgresql.org/docs/17/sql-select.html),
[Explicit locking](https://www.postgresql.org/docs/17/explicit-locking.html).

## Public read ve publish

Katalog request'i `READ COMMITTED` transaction'da
`pg_try_advisory_xact_lock_shared(7488,1)` alır. False ise hemen 503. Sonraki
statement publication state/epoch'u okur; `ready` değilse data sorgulanmaz.
Rows + exact count aynı shared gate altında tamamlanır. CORE yazarı aynı
exclusive gate'i zorunlu kullandığından bu transaction boyunca model değişmez.
Pool'a session kilidi bırakılmaz.

CORE execution lane'de yalnız bir `leased/running` job olabilir; çok sayıda
`queued` job bulunabilir. Claim, read-model state/active job bağını aynı control
transaction'da reserve eder. `awaiting_publication/failed` state'i yeni normal
CORE claim'e izin vermez; yalnız onaylı recovery retry ilerleyebilir.

Coverage endpoint state'i her durumda döndürebilir; ready değilken published
entity sayımları `null`, yıl listeleri boş ve DATA_NOT_PUBLISHED/UPDATING uyarısı
taşır. HTTP live/ready ile business-data publication availability ayrıdır.

Operator publication dry-run'ı candidate/job/state/epoch'a bağlı, 5 dakika
geçerli signed plan token üretir. Apply idempotency key + aynı token ile kısa
control transaction'da exclusive transaction gate alır; candidate succeeded,
validation passed ve beklenen epoch kontrolleri yeniden yapılır. Publication
metadata immutable olarak `published`, current state `ready`, epoch+1 olur.
Eski publication metadata'sı audit olarak `superseded` olabilir; eski CORE
verisinin tutulduğu anlamına gelmez.

## Failure/recovery

Stale/expired lease heartbeat/start/complete 409 döner. Expired CORE job otomatik
claim/retry edilmez; model failed/closed kalır. Aynı anda ikinci CORE writer
başlatmak için eski session gate'inin bırakıldığı doğrulanmalı ve DE recovery
planı operator tarafından onaylanmalıdır. Retry dry-run tek başına data repair
onayı değildir; registered adapter'ın recovery contract'ı da gerekir.

Crash, lease veya publisher failure önceki batch commit'lerini geri almaz. Failed
model için eski metadata pointer'ını geri çevirmek yasaktır; restore/backfill
DE tarafından gated recovery job'ı olarak yapılır. İlk sürümde public history
ve restore/delete endpoint'i yoktur. Operator/DB owner'ın gate'i atlayan manuel
CORE yazısı bu cooperative protokolün garantisini bozar; deployment runbook'unda
bu credential/işlem sınırı açık olmalıdır.

Kabul testleri: iki simultaneous claim tek job; write öncesi start zorunlu;
okuyucu varken writer gate bekler; writer/update/failed durumda data/304 verilmez;
lease kaybında ikinci writer otomatik açılmaz; candidate publish eski epoch/plan
token ile uygulanamaz; yeni publication eski cursor'u 409 yapar.
