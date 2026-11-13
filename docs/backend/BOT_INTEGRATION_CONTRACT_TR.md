# Bot Entegrasyon Sözleşmesi

**Güncel sunucu entegrasyonu:** Merve'nin Docker runner panelinde iki bot,
`botkit` kullanan Python komutlarıyla kayıtlıdır. Gerçek komutlar, ayarlar,
veritabanı erişimi ve durdurma/yeniden deneme davranışı için
[admin panel bot rehberini](ADMIN_PANEL_BOTS_TR.md) kullan. Aşağıdaki Ops API
tasarımı yerel TÜİK arayüzünün sözleşmesidir; çalışan ortak panel kendi
`/api/bots` ve `/api/runs` uçlarını ve kalıcı kuyruğunu kullanır.

**Yerel API durumu:** TÜİK botu için manuel uçlar çalışır; bu yerel API'nin
zamanlaması ve kalıcı job queue'su sonraki aşamadır.

## Mimari kararı

Akış **Admin panel → Ops API → worker → ingestion katmanı → PostgreSQL** olmalı.

- Tarayıcı TÜİK’e veya PostgreSQL’e doğrudan bağlanmaz. TÜİK anahtarı ve DB parolaları yalnızca sunucu tarafında kalır.
- Panel botu `bot_id` ile seçer, `ops` uçlarına komut verir ve run durumunu aynı API’den okur. Her bot için ayrı ve farklı biçimli yönetim API’si açmayız; botlar aynı sözleşmeye uyar.
- Verinin içeri alınması için üretim hedefi `/internal/v1/ingestions` gibi kimlik doğrulamalı ingestion API’sidir. Botlar `atlas_owner` kullanıcısını hiçbir zaman almaz.
- Bu yerel MVP’de worker, mevcut yükleyiciyle uyum için yalnızca kısıtlı `atlas_ingest` DB rolüyle çalışır. Bu erişim API sunucusunun arkasındadır; tarayıcıya veya bağımsız bot makinelerine verilmez. Worker ayrıldığında iç ingestion API’sine geçirilir.
- Katman sırası `raw → staging → core → api` olarak kalır. Eşlemesi bulunmayan yeni TÜİK akışları kaybolmadan `raw`’a yazılır; staging/model tamamlanana kadar `api` görünümüne açılmaz.

## Ortak bot kimliği ve çalışma kaydı

Her botun en az şu sabit alanları olur:

| Alan | Anlamı |
|---|---|
| `bot_id` | Sabit kimlik; ör. `tuik-sdmx`, `yokatlas` |
| `name` | Panelde gösterilecek ad |
| `datasets` | Botun desteklediği veri akışları ve kategori metaverisi |
| `run_id` | DB’deki `raw.ingestion_runs.ingestion_run_id` |
| `status` | `queued`, `running`, `completed`, `completed_with_issues`, `failed` |
| `started_at`, `completed_at` | UTC çalışma zamanları |
| `parameters` | Yıl, dataflow ve botun güvenli seçim alanları |
| `records`, `staged_records` | Ham ve eşlenmiş kayıt sayıları |
| `warnings`, `message` | Anahtar/ham payload içermeyen güvenli açıklamalar |

Kaynak yanıtı checksum, endpoint ve çekim zamanı ile saklanır. Aynı endpoint ve içerik tekrar gelirse RAW kayıtları çoğaltılmaz. Geçici hata yeniden denenebilir; kimlik doğrulama, şema ve veri doğrulama hataları sessizce tekrar edilmez.

## Yönetim endpoint’leri

Tüm botlar için ortak rota kalıbı:

| Method | Endpoint | Amaç |
|---|---|---|
| `GET` | `/ops/v1/bots` | Panelde kullanılabilir botları listeler |
| `GET` | `/ops/v1/bots/{bot_id}/datasets` | Botun kategori ve veri akışlarını listeler |
| `POST` | `/ops/v1/bots/{bot_id}/runs` | Manuel bir çalışma başlatır; `202` ve `run_id` döndürür |
| `GET` | `/ops/v1/bots/{bot_id}/runs?limit=20` | Son çalışmaların durumunu listeler |
| `GET` | `/ops/v1/bots/{bot_id}/runs/{run_id}` | Bir çalışmanın son durumunu verir |

`POST runs` gövdesi botun veri seçim parametrelerini taşır. TÜİK için:

```json
{
  "dataflow_id": "DF_ADNKS_T16",
  "version": "1.0",
  "year": 2025
}
```

Yönetim uçları `X-API-Key` ister. Şu anki admin ekranı anahtarı yalnızca sekme belleğinde tutar. Merve’nin panelinde bu kimlik doğrulama, kullanıcı oturumundan alınan yetkili token’a bağlanabilir; API sözleşmesi aynı kalır. `TUIK_API_KEY` ise ayrı bir TÜİK servis anahtarıdır ve hiçbir zaman tarayıcıya gönderilmez.

Bot listesinde YÖK Atlas bugün `cli_only` olarak görünür; bu ilk panel entegrasyonu yalnızca TÜİK çalıştırma uçlarını açar. YÖK Atlas botu aynı run sözleşmesine bağlandığında `manual_runs` etkinleştirilir.

## TÜİK veri seçimi ve destek kapsamı

Veri seti kataloğu [TÜİK SDMX `dataflow` listesinden](https://veriportali.tuik.gov.tr/en/sdmx-web-service-documentation) alınır ve başlığa göre kategorilere ayrılır. Kategori önerileri: nüfus/demografi, göç, fiyat/enflasyon, işgücü/ücret, ekonomi, eğitim, konut/inşaat, turizm, tarım, sağlık, dış ticaret ve diğer.

Panel kategori → dataflow → referans yılı seçtirir. Yıllık, aylık veya üç aylık akışlarda tek yıl seçimi o yılın tüm dönemlerini ister. İndirme, TÜİK’in SDMX-CSV servisini kullanır.

- `DF_ADNKS_T16` sürüm `1.0` ham veriye ek olarak `staging.tuik_population_by_province` tablosuna eşlenir ve `api.tuik_population_by_province` görünümünden sunulur.
- Diğer katalog akışları ilk aşamada tam kaynak yanıtı ve satırları `raw` katmanında saklar; bot geçmişinde `normalization=raw_only` olarak görünür. Her akış için alan/kod eşlemesi ve typed staging tablosu eklendikçe API görünümü açılır.
- Dataflow adlarının kategorilere ayrılması başlıklara dayalı bir sınıflandırmadır. Katalogda yanlış kategoride görünse bile TÜİK’in dataflow kimliği ve sürümü asıl kaynağı belirler.

## Otomatik çalışma ve worker aşaması

Zamanlama aynı bot sözleşmesine eklenir; tasarım detayları Merve’nin admin paneliyle eşleştirilecek:

- `PUT /ops/v1/bots/{bot_id}/schedule`: `enabled`, zaman dilimi, frekans ve sabit parametreleri kaydeder.
- Scheduler zamanı gelince manuel çalıştırmayla aynı run komutunu üretir; ayrı bir veri işleme yolu açmaz.
- Kalıcı kuyruk/worker claim, heartbeat/lease, retry ve tamamlanma davranışı mevcut backend tasarımındaki `/ops/v1/jobs` ve `/internal/v1/jobs/*` sözleşmeleriyle birleştirilir.
- Mevcut manuel MVP, FastAPI `BackgroundTasks` kullanır. Bu nedenle servis yeniden başlarsa aktif iş kaldığı yerden otomatik devam etmez; DB’deki run geçmişi korunur ve operatör yeniden başlatabilir. Otomatik zamanlama açılmadan önce kalıcı worker kuyruğu gerekir.

## Geliştirme yapılandırması

Değerleri yalnızca sunucunun kök `.env` dosyasına ekle:

```dotenv
TUIK_API_KEY=...        # TÜİK Portal API anahtarı
BOT_ADMIN_API_KEY=...   # yerel admin API erişimi
```

İkisi de `.env.example` içinde yalnızca yer tutucu olarak bulunur. Dolu `.env` Git’e eklenmez. TÜİK anahtarı paylaşılmışsa portaldan yenilenmelidir.

## Admin ekranı

Yerel API çalışırken TÜİK paneli `/admin/tuik` adresindedir. Ekran dataflow kategorisi, veri seti, yıl, manuel başlatma ve son çalışma durumlarını içerir. Zamanlama ayarı ve diğer botların yönetim ekranı bu ilk sürüme dahil değildir.
