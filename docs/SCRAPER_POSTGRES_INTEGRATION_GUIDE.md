# YÖK Atlas Intelligence — Scraper → PostgreSQL RAW Entegrasyon Sözleşmesi

> **Hedef kitle:** Scraper geliştiren ekip üyesi ve kod üreten yapay zekâ.
> **Durum:** Mevcut çalışan PostgreSQL 17 şemasına dayanır (`current_schema.sql`).
> **Temel görev:** Kamuya açık YÖK Atlas API'sinden alınan HTTP JSON yanıtlarını **önce RAW katmanına güvenilir, izlenebilir ve tekrar çalıştırılabilir** biçimde yazmak. Scraper, `staging` ve `core` tablolarına doğrudan veri yazmamalı.
> **Kapsam sınırı:** Bu belge mevcut keşfedilmiş API kümesini anlatır; YÖK Atlas'ın bütün olası endpoint'lerinin bulunduğunu iddia etmez.

## 0. Mevcut ortam ve sabitler

- Veritabanı: PostgreSQL **17**, DB: `yokatlas_intelligence`.
- Docker konteyneri: `yokatlas-intelligence-postgres-1`.
- Windows host erişimi: `127.0.0.1:5433` → container `5432`.
- Veritabanı sahibi: `atlas_owner` (scraper için tercihen **ayrı `atlas_ingest` rolü**; yetkisini doğrula).
- **Gerçek şifreyi repoya, bu belgeye veya koda yazma.** `.env` / ortam değişkeni kullan.
- Bu bilgiler mevcut yerel geliştirme ortamı içindir; başka geliştiricide `DB_HOST`, `DB_PORT` değişebilir.
- Kaynak API kökü: `https://yokatlas.yok.gov.tr/api`
- Tarihsel mevcut yük: 2026 program kataloğu (21.491 kayıt), 2023–2025 net sonuçları (63.063 staging → 62.992 tekil core). Bunlar **mevcut snapshot kapsamı**, gelecek yüklerin sabit beklenen sayıları değildir.

## 1. Keşfedilmiş API endpoint sözleşmesi

| HTTP | Endpoint | RAW içindeki `source_entity` | Not |
|---|---|---|---|
| GET | `/api/tercih-kilavuz/universiteler` | `universities` | Üniversite listesi |
| GET | `/api/tercih-kilavuz/universite-programlar` | `program_groups` | Program grubu / üniversite-program verisi; **yanıtı inceleyerek mapping'i doğrula** |
| GET | `/api/tercih-kilavuz/universite-iller` | `cities` | İl verisi; **yanıtı inceleyerek mapping'i doğrula** |
| POST | `/api/tercih-kilavuz/search` | `programs` | Filtreli, sayfalı 2026 program katalog sonuçları |
| POST | `/api/netler/search` | `net_results` | Net sonuçları; geçmiş snapshot'ta 2023–2025 |

**Önemli:** Yukarıdaki `source_entity` dizeleri, **mevcut RAW kayıtlarında kullanılan** beş değerdir; endpoint ve entity eşleştirmesini scraper'ın gözlediği yanıt yapısıyla teyit et. `/api/netler/search` yanıtı program kataloğuna benzer alanlar da içerebilir. Endpoint adından sonuç tipi çıkarma; **yanıt içeriğini ve uygulama isteğini test et.**

Örnek POST filtre parametreleri (örnek, tüm parametreler için kesin sözleşme değildir):
```json
{
  "filters": {
    "puanTuru": null,
    "universiteId": [],
    "birimGrupId": [],
    "ilKodu": [],
    "birimTuruId": null,
    "bursOraniId": null,
    "kilavuzKodu": null,
    "maxBasariSirasi": null,
    "minBasariSirasi": null,
    "ogrenimTuruId": null,
    "universiteTuru": null
  },
  "page": 0,
  "size": 10,
  "sortBy": "basariSirasi",
  "direction": "ASC"
}
```
Bu payload kullanıcı tarafından **bir program arama yanıtıyla** paylaşılmıştır. Yıl / puan türü / net araması için doğru payload'ı ilgili scraper keşfinden veya uygulamanın isteklerinden teyit et; **yukarıdaki örneği körü körüne bütün endpoint'lere uygulama.**

## 2. Gerçekte var olan RAW tabloları — birebir kolon sözleşmesi

### `raw.ingestion_runs`
```sql
ingestion_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
source_system TEXT NOT NULL DEFAULT 'yokatlas',
started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
completed_at TIMESTAMPTZ,
status TEXT NOT NULL DEFAULT 'running',
scraper_version TEXT,
details JSONB NOT NULL DEFAULT '{}'::jsonb
```
Her scraper işinin/partisinin kaydı. **`status` için DB CHECK/ENUM yok:** uygulamada tutarlı `running`, `completed`, `failed`, `partial` dizelerini kullan; mevcut pipeline'ın beklediği durum değerleriyle uyumlu ol.

### `raw.api_responses`
```sql
api_response_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
ingestion_run_id BIGINT NOT NULL REFERENCES raw.ingestion_runs(ingestion_run_id),
endpoint TEXT NOT NULL,
method TEXT NOT NULL,
score_type TEXT NULL,
page_number INTEGER NULL,
captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
source_hash_sha256 TEXT NULL CHECK (source_hash_sha256 IS NULL OR length(source_hash_sha256)=64),
http_status INTEGER NULL,
payload JSONB NOT NULL,
source_path TEXT NULL
```
İndeksler:
- `idx_api_response_endpoint(endpoint, score_type, page_number)`
- `idx_api_response_run(ingestion_run_id)`
- **Unique partial expression index `ux_api_response_identity`:**
```sql
CREATE UNIQUE INDEX ux_api_response_identity
  ON raw.api_responses (
    endpoint,
    COALESCE(score_type, ''),
    COALESCE(page_number, -1),
    source_hash_sha256
  )
  WHERE source_hash_sha256 IS NOT NULL;
```
**Tuzak:** Bu unique kuralı **`ingestion_run_id` veya istek gövdesini içermiyor**. Aynı endpoint + score_type + sayfa + hash başka çalışmada tekrar indirilirse **yeni api_response satırı oluşturulamaz**. Ayrıca farklı filtreler aynı sayfa numarasını kullanabilir; istek parametreleri indekste yoktur. Bu davranış şema güncellemesi için ayrıca değerlendirilmelidir. Scraper bunu sessizce başka veriyle ezmemeli.

### `raw.source_records`
```sql
source_record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
api_response_id BIGINT NOT NULL REFERENCES raw.api_responses(api_response_id),
source_entity TEXT NOT NULL,
source_array_index INTEGER NOT NULL CHECK (source_array_index >= 0),
record JSONB NOT NULL,
record_hash_sha256 TEXT NULL,
UNIQUE (api_response_id, source_entity, source_array_index)
```
Yanıttaki mantıksal kayıtlar, **dizi indeksleriyle** arşivlenir. `source_array_index` her yanıt için sıfırdan başlar. Aynı `api_response_id` + `source_entity` + indeks ikinci kez yazılmamalı. `record_hash_sha256` için fiziksel şemada 64 karakter CHECK yok; kodda SHA-256 doğruluğunu yine kontrol et.

### RAW dışındaki katmanlar
- `staging.{universities,cities,program_groups,programs,net_results}`: tipli alanlar + `payload JSONB`, her satır `source_record_id` FK ile RAW'a bağlı.
- `core.{universities,cities,program_groups,program_versions,net_results,conditions,program_conditions}`: normalleştirme, FK/PK, tekilleştirme ve iş anlamları.
- `quality.{data_quality_checks,quarantined_records}`: kalite kontrol/karantina.

**Scraper bu tablolara doğrudan `INSERT` yapmasın.** Bunları mevcut / ayrı ETL adımı yönetsin. `raw.api_responses.payload` JSONB olduğu için orijinal HTTP dosyasının baytlarını, boşluklarını, alan sırasını korumaz; birebir dosya arşivi isteniyorsa ayrıca dosya deposu gereklidir.

## 3. Yazma iş akışı (önerilen uygulama sözleşmesi)

1. Scraper başında **bir adet `raw.ingestion_runs`** satırı aç; dönen `ingestion_run_id`'yi sakla.
2. API çağrısı yap. **Yalnızca izinli/açık endpoint'leri**, makul hız sınırı, backoff ve timeout ile çağır. Sunucuyu zorlamadan ilerle; kullanım şartlarını dikkate al.
3. Her HTTP yanıtını diskte dosyaya arşivlemen isteniyorsa `utf-8` bytes olarak yaz; `sha256(raw_response_bytes)` üret. JSON parse et, beklenen şekli doğrula. HTTP hata yanıtları ayrı hata günlüğüyle korunabilir; mevcut RAW tablo yapısında `payload JSONB NOT NULL` olduğundan JSON olmayan hata gövdesini **zorla JSON gibi kaydetme**.
4. Yanıt için `raw.api_responses` satırı kaydet; `endpoint` **tam path**, örn. `/api/tercih-kilavuz/search`, `method` `GET`/`POST`, `score_type` istek filtresindeki gerçek puan türü ise yaz, yoksa `NULL`; `page_number` **0 tabanlıysa öyle kaydet**; `http_status`, `captured_at`, `source_hash_sha256` (birebir yanıt bayt hash'i), `payload`, `source_path` (varsa gerçek arşiv yolu) yaz.
5. Liste yanıtlarında kayıt dizisini belirle. **Örneğin sayfalı yanıtta `content` array** kullanılıyor; sayfa metadata (`totalElements`, `totalPages`, `number`, `size`, `yil`, `source`) `api_responses.payload` içinde kalmalı. Farklı endpoint'ler farklı JSON şekilleri döndürür; dizi yolunu endpoint bazında açıkça tanımla.
6. Yanıttaki **her dizi elemanını** `raw.source_records` içine `(api_response_id, source_entity, source_array_index, record, record_hash_sha256)` olarak yaz. `record` ilgili kaydın bütün JSON içeriğini kapsamalı, alanları ayıklama.
7. Yanıt ve alt kayıt eklemelerini **tek transaction** içinde yap. İşlem ortasında hata olursa kısmi source_records kalmamalı.
8. Her sayfa için kayıt sayısını ve toplam kayıt / sayfa metadatasını kontrol et. Boş son sayfa normal olabilir; beklenmeyen eksik sayfa durumunu `details` veya run hata durumunda raporla.
9. Çalışma sonunda `ingestion_runs.status`, `completed_at`, `details` güncelle; başarısızlıkta `failed`/`partial` olarak kapat, exception'ı logla.
10. RAW kalıcı olduktan sonra **ayrı ETL süreci** staging/core dönüşümünü yürütür. Scraper başarılı oldu diye ETL başarılı kabul edilmez.

## 4. SQL örnekleri

### İş başlat
```sql
INSERT INTO raw.ingestion_runs (source_system, status, scraper_version, details)
VALUES ('yokatlas', 'running', $1, $2::jsonb)
RETURNING ingestion_run_id;
```

### Yanıt ve kayıtları transaction'da ekle
```sql
BEGIN;
INSERT INTO raw.api_responses
  (ingestion_run_id, endpoint, method, score_type, page_number,
   captured_at, source_hash_sha256, http_status, payload, source_path)
VALUES
  ($1, $2, $3, $4, $5, now(), $6, $7, $8::jsonb, $9)
RETURNING api_response_id;

-- Her eleman için (veya toplu parametrik INSERT/COPY):
INSERT INTO raw.source_records
  (api_response_id, source_entity, source_array_index, record, record_hash_sha256)
VALUES ($1, $2, $3, $4::jsonb, $5);

COMMIT;
```
`$1` vb. PostgreSQL parametrik SQL gösterimidir; Python sürücüsünde placeholder biçimi değişebilir. **String birleştirerek SQL üretme.** `RETURNING` sonucundan alınan ID'yi ikinci eklemede kullan.

### İş bitir
```sql
UPDATE raw.ingestion_runs
SET status = $2,
    completed_at = now(),
    details = $3::jsonb
WHERE ingestion_run_id = $1;
```

### İdempotency / tekrar çalıştırma: uygulanması gereken açık politika

Mevcut unique index yüzünden aynı yanıt ikinci çalışmada `23505 unique_violation` üretebilir. **`ON CONFLICT DO NOTHING RETURNING` kullanıp hiçbir satır dönmezse bunu veri kaybı veya yeni kayıt olarak yorumlama.** İlgili mevcut yanıtı aşağıdaki tam indeks kimliğine göre sorgula:
```sql
SELECT api_response_id, ingestion_run_id, method, payload, source_path
FROM raw.api_responses
WHERE endpoint = $1
  AND COALESCE(score_type, '') = COALESCE($2, '')
  AND COALESCE(page_number, -1) = COALESCE($3, -1)
  AND source_hash_sha256 = $4;
```
Sonra aynı içerik / metadata uygunluğunu kontrol et. **Var olan response'a ait `source_records` zaten yazılmışsa yeniden yazma.** Eğer eşleşen response'un child kayıtları eksikse ayrı onarım süreci işlet veya açık hata ver. `source_hash_sha256` `NULL` ise unique index koruması devrede değildir: hash üretmeyi varsayılan zorunluluk say.

**Önemli mimari açık:** Aynı yanıtın farklı günlerde yeniden görülmesini `raw.api_responses` tek başına temsil edemiyor; `ingestion_run_id` yalnızca ilk eklenen run'a ait kalır. Eski snapshot gözlemlerini kaybetmeden her koşuyu izlemek gerekiyorsa (önerilir) DB ekibiyle **`raw.api_response_observations` gibi ayrı run→response gözlem tablosu veya migration** üzerinde anlaş. Scraper kendiliğinden şemayı değiştirmesin.

**Diğer açık:** Aynı endpoint'in farklı filtre kombinasyonları için `page=0` olabilir. Hash farklıysa farklı cevaplar saklanabilir; ama `request_payload` veya `request_signature` için fiziksel kolon yok. `details` ve HTTP istek logu / ayrı manifestte filtreleri eksiksiz sakla; kalıcı sorgu izlenebilirliği için migration öner.

## 5. Hash, JSON ve veri kaybını önleme

- `source_hash_sha256`: sunucudan gelen **orijinal HTTP body bytes** üzerinden SHA-256 hex (64 karakter, lowercase) üret. Sıkıştırma açıldıktan sonraki byte stream kullanılıyorsa bunu açıkça belgele; standart tek olsun.
- `record_hash_sha256`: JSON nesnesi için `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))` ile deterministik UTF-8 oluşturup hashle (normalizasyon kuralını sabitle). Bu hash **response byte hash'iyle aynı tür değildir**.
- `payload` ve `record` alanlarına JSON'un **tam nesnesini** yaz. Yalnızca analizde lazım diye anahtar azaltma.
- JSON `null` → SQL `NULL` ayrımına dikkat: `payload` JSON nesnesi olmalı; `[]`, `{}` gibi boş gerçek yanıtlar geçerli olabilir. Eksik sayısal değerleri 0'a dönüştürme.
- API'de `minPuan1`, `basariSirasi1`, `gk1` vb. alanların hangi tarihsel yıla karşılık geldiğini **tahmin etme**. Scraper bu alanları ham olarak korur; semantik eşleme ETL'de kanıtlandığında yapılır.
- Kaydedilen HTTP hata response'larını JSONB'ye almak isteniyorsa sözleşmesini ayrıca belirle; parse olmayan byte'ları `payload` kolonuna sahte JSON olarak koyma.

## 6. Önceden bilinen kayıt türleri, doğal anahtarlar ve tuzaklar

Aşağıdakiler **STAGING/CORE ETL** için referanstır; scraper bunlara göre kaynak kayıtlarını elememelidir.

| Varlık | CORE anahtar | Not |
|---|---|---|
| Universities | `universite_id` | Şu snapshot 228 |
| Cities | `il_kodu` | Şu snapshot 83 |
| Program groups | `(birim_grup_id, puan_turu)` | `birim_grup_id` tek başına yeterli değildir; 611 kayıt |
| Program versions | `(kilavuz_kodu, yil)` | Şu snapshot yalnızca 2026 |
| Net results | `(kilavuz_kodu, yil, puan_turu)` | 2023–2025 kaynaklarında 71 **birebir payload tekrarı** vardı |
| Conditions | `condition_code` | Program JSON içindeki `kosulList` ve eşlemelerden türetiliyor |

**Kritik:** 2023–2025 net verilerini sırf `kilavuz_kodu` benzediği için 2026 program sürümlerine bağlama. Şu an bütün `core.net_results.program_version_id` değerleri boş (62.992 kayıt), ayrıca üniversite lookup eşleşmesi olmayan 278 net var. RAW'da bunları **asla filtreleme/silme**.

## 7. Somut kontroller ve kabul kriterleri

Scraper teslimi şu testleri sağlamalı:

1. Sağlıklı test koşusunda `ingestion_runs` açılır ve `completed` ile kapanır.
2. Başarılı her JSON yanıtının `api_responses` kaydı oluşturulur veya mevcut eşdeğer yanıt **bilinçli idempotent** olarak bulunur.
3. Liste içeren yanıt için `source_records` sayısı gerçekten alınan eleman sayısına eşittir.
4. `source_records.record`, yanıt dizisindeki orijinal JSON kaydına eşittir (anahtar ve değerler aynı).
5. Tekrar çalıştırmada kontrolsüz benzersizlik hatası/çift kayıt ya da sessiz veri kaybı olmaz.
6. HTTP 429/5xx, timeout, bağlantı kopması ve bozuk JSON durumları hata olarak loglanır; backoff uygulanır, eksik koşu başarılı sayılmaz.
7. Bir sayfanın source kayıtları yarım kalırsa transaction rollback gerçekleşir.
8. Her run için hangi endpoint, filtre, yıl, sayfa ve hash'lerin işlendiği raporlanabilir.
9. DB bağlantı parametreleri env üzerinden gelir; gizli bilgiler çıktı/log/commit içine girmez.
10. 2023–2025 net kayıtlarının 2026 programlarıyla otomatik/yanlış eşleştirilmesi yapılmaz.

Örnek doğrulama sorguları:
```sql
-- Endpoint bazında ham yanıt sayısı
SELECT endpoint, method, COUNT(*)
FROM raw.api_responses
GROUP BY endpoint, method
ORDER BY endpoint;

-- Kaynak varlık adetleri
SELECT source_entity, COUNT(*)
FROM raw.source_records
GROUP BY source_entity ORDER BY source_entity;

-- Kaynak kaydı olmayan yanıtlar (boş liste yanıtları meşru olabilir)
SELECT r.api_response_id, r.endpoint, r.page_number
FROM raw.api_responses r
LEFT JOIN raw.source_records s ON s.api_response_id = r.api_response_id
GROUP BY r.api_response_id, r.endpoint, r.page_number
HAVING COUNT(s.source_record_id) = 0;

-- İş koşuları
SELECT ingestion_run_id, status, started_at, completed_at, details
FROM raw.ingestion_runs ORDER BY ingestion_run_id DESC LIMIT 20;
```

Yerel test bağlantısı:
```powershell
docker exec -it yokatlas-intelligence-postgres-1 `
  psql -U atlas_owner -d yokatlas_intelligence
```
Container dışından çalışan scraper için örnek env:
```dotenv
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=yokatlas_intelligence
DB_USER=atlas_ingest
DB_PASSWORD=<LOCAL_SECRET>
```
> `atlas_ingest` rolü gerçekten varsa ve RAW için gerekli `INSERT/SELECT/UPDATE`, identity sequence yetkileri verilmişse kullan. Aksi durumda **önce yetkileri test et**; rolü/veritabanını scraper kodunda otomatik oluşturma. `atlas_owner` yalnızca yetkilendirilmiş geliştirme ortamında kullanılmalıdır.

## 8. Kod üreten yapay zekâya direkt verilecek görev

> Bu Markdown belgesindeki **mevcut PostgreSQL RAW şemasını değiştirmeden** Python tabanlı, tipli ve test edilebilir bir YÖK Atlas API scraper + RAW writer modülü oluştur. HTTP için `httpx`, PostgreSQL için `psycopg` (v3) veya ekipteki mevcut uyumlu istemciyi kullan. `DbWriter` sınıfı, run yaşam döngüsü, parametrik SQL, yanıt + kayıtları atomik transaction'la ekleme, SHA-256, retry/backoff, idempotency handling, detaylı manifest/loglar ve pytest testleri içersin. Endpoint eşleştirmesini sabit konfigürasyonda tut; yanıt şeması doğrulanmadan `source_records` türetme. `staging` ve `core` tablolarına yazma. Başlangıçta bir `--dry-run`, bir `--limit-pages` seçeneği ve bir entegrasyon testi sağla. Mevcut unique index'in tekrar gözlem sorununu kodda gizleme; belgede işaretle ve gerekiyorsa migration önerisini **ayrı** dosyada hazırla, otomatik uygulama.

## 9. Tasarımın açık soruları / teslimden önce teyit

- Scraper **doğrudan DB'ye mi yazacak**, yoksa arşiv JSON dosyalarından **ayrı importer** mı besleyecek? Her ikisinde de aynı `DbWriter` kullanılabilir.
- JSON olmayan yanıtlar ve API erişim/hız politikaları için beklenti nedir?
- `source_path` konteyner içi mi, repo göreli mi, paylaşımlı storage URI mı olacak? Taşınabilir biçim belirle.
- İstek parametrelerinin kalıcı saklanması ve **farklı günlerde aynı yanıtın tekrar gözlenmesi** için ek migration kabul edilecek mi?
- POST endpoint'leri için puan türü ve yıllara göre gerçek payload sözleşmeleri scraper keşfiyle teyit edildi mi?

---

### Dayanak
- Gerçek çalışan fiziksel PostgreSQL DDL: `current_schema.sql`.
- Gerçek DB denetim çıktısı: beş RAW entity; beş API endpoint; programlarda 0 kaynak/FK eksikliği; 71 aynı payload net tekrarı; RAW→staging JSON karşılaştırmasında 0 fark.
- 2026 program JSON örneği ve kullanıcı tarafından kaydedilmiş DevTools/network çıktısı.
