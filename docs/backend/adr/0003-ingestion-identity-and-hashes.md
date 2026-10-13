# ADR-0003 — RAW identity, hash ve tekrar gözlem

**Durum:** Öneri; metadata migration uygulaması onay bekliyor.

Mevcut unique index korunur. Endpoint/score/page/response hash üzerinden aynı
RAW response başka run'da yeniden görülebilir; run→response gözlemi ayrı
`platform.response_observations` kaydıdır. Request signature response kimliğinden
ayrıdır; farklı filtrelerin aynı body'yi getirmesi iki ayrı observation olabilir.

## Hash sözleşmesi

| Değer | Hesap |
|---|---|
| Yeni `raw.api_responses.source_hash_sha256` | Decompress edilmiş original HTTP body byte'larının SHA-256 lowercase hex'i |
| `record_hash_sha256` | Kayıt JSON'unun aşağıdaki `exact-json-v2` canonical UTF-8 byte'larının SHA-256'sı |
| `request_signature` | Source + registered endpoint + method + izinli query/body metadata'sının `exact-json-v2` hash'i |
| `command_fingerprint` | Route + canonical command; response için verified body hash ve captured_at dahil; auth secret/idempotency key hariç |

Response byte hash'i ile record hash'i aynı tür değildir. Body hash'ini server
yeniden hesaplar; mismatch 422 `BODY_HASH_MISMATCH`. Secret header/query alanları
source policy ile request identity'den çıkarılır; RAW response gövdesi kaynak
izinleri kapsamında tam korunur. Client hash'i veya filename'i yetki/kimlik
kanıtı sayılmaz.

`exact-json-v2` cross-language contract'tır; RFC 8785/JCS ile aynı algoritma olduğu
iddia edilmez. Kurallar:

- UTF-8, BOM varsa yalnız parser için ayrılır; byte hash BOM dahil original
  decompressed body'den alınır. Duplicate object keys, invalid Unicode ve
  NaN/Infinity reddedilir.
- Object key sırası Unicode scalar codepoint sırasıdır; array sırası korunur.
  String'ler UTF-8 JSON string encoding: quote/backslash/control karakter escape,
  diğer Unicode doğrudan; unnecessary slash escape yok. Whitespace yok.
- Sayılar binary float'a yuvarlanmadan exact lexical decimal olarak parse edilir.
  Canonical zero `0`; diğerleri signed significand digits + `e` + exponent'tir.
  Significand başında/sonunda gereksiz sıfır yok, exponent işareti `+` içermez.
  Örnekler: `1000`→`1e3`, `1.00`→`1e0`, `0.10`→`1e-1`, `-12.30`→`-123e-1`.
  Bu dönüşüm yalnız canonical hash/JSON serialize eşitliği içindir, kaynak iş
  alanları yorumlanmaz. Numeric digit/exponent bütçesi DB numeric sınırı ve body
  kaynak bütçesiyle validation'da sınırlandırılır; precision kaybı kabul edilmez.
- Boolean/null standart JSON token'larıdır. Canonical algoritma sürümü response
  metadata'sında saklanır; golden-vector tests DE/scraper contract kabulüne dahildir.

## Legacy koruma

Mevcut loader response hash'ini Python canonical JSON ile üretir. Eski hash'ler
yeniden hesaplanıp RAW üzerinde güncellenmez. `response_metadata` olmayan kayıt
`legacy_unknown` kabul edilir; loader/run kanıtı varsa sınıflandırma ayrı owner
onaylı işlemle yapılır. Yeni byte hash farklıysa eski JSONB eşit olsa da ayrı
response saklanabilir; böylece farklı original byte gözlemi korunur.

Yeni byte identity mevcut legacy hash ile aynı unique kimliğe çarparsa body,
metadata ve çocuk doğrulaması yapılır; hash türü/provenance doğrulanamazsa
409 `LEGACY_HASH_AMBIGUOUS` ile repair incelemesine bırakılır. Hash çakışmasında
sessiz overwrite yoktur.

## İdempotency ve atomik sonuç

Mutasyon key'i `(principal_id, route_key, Idempotency-Key)` kapsamındadır.
Header 12–128 ASCII karakter; yeni gözlem için yeni key gerekir. Aynı key + aynı
fingerprint kayıtlı status/body sonucunu tekrar verir, `Idempotency-Replayed:true`
header'ı taşır. Aynı key + farklı fingerprint 409 `IDEMPOTENCY_CONFLICT`.
Concurrent claim unique constraint/row lock ile tek commit olur; bekleme bütçesi
aşılırsa 409 `IDEMPOTENCY_IN_PROGRESS`, `Retry-After:1`.

Key en az 7 gün saklanır; cleanup politikası onaylanana kadar kayıt silinmez.
Süresi dolmuş kayıt hâlâ varsa key tekrar kullanılmaz, `IDEMPOTENCY_EXPIRED`
döner. Network ACK kaybında aynı command/key ile retry güvenlidir. 429/503
cevapları backoff + aynı key ile denenir; non-idempotent otomatik retry yoktur.

| Durum | Sonuç |
|---|---|
| Yeni verified response | 201 `stored`; tüm children + observation + result + audit aynı SQL commit |
| Aynı verified bytes, yeni run/request/capture | 200 `duplicate`; RAW/children değişmez, yeni observation saklanır |
| Aynı mutasyon key/fingerprint | İlk status/body replay; yeni observation yok |
| Existing response payload/metadata farklı | 409 conflict; eski kayıt ezilmez |
| Existing children eksik/farklı | 409 `RESPONSE_INCOMPLETE`; otomatik child repair yok |
| Hash NULL veya body bozuk | Yeni kabul yolu 422; legacy kayıt silinmez |
| JSON olmayan HTTP hata gövdesi | RAW JSON kabulü 422; run completion failure metadata'sı ile hata bildirilir |
| Batch/size aşımı | 413; hiçbir kayıt kırpılıp kısmi başarılı sayılmaz |

Body/artifact staging transaction öncesidir; artifact SQL rollback sonrası orphan
olabilir. Görünür SQL kayıtları ya tam commit olur ya rollback. Başarı body/hash,
stored/duplicate sonucu ve accepted record sayısı içerir. Request filters/body
observation'da private metadata'dır; public DTO'da yayımlanmaz.
