# Merve'nin admin panelinde veri botları

SEGE ve URAP için PDF runner komutları, ayarlar, bağımlılık kurulumu ve migration 007
[SEGE/URAP kurulum rehberinde](SEGE_URAP_BOTS_TR.md) bulunur. Yeni girişler
`python -m scraper.panel_sege` ve `python -m scraper.panel_urap` komutlarıdır.
Bu iki bot runner ortamında ek `pdfplumber` bağımlılığını gerektirir.

Bot kodları sunucuda `/home/deploy/yokatlas` altında bulunur. Panelin runner
konteynerinde aynı klasör `/repo` olarak görünür. İki bot da Python 3.12 ve
mevcut kütüphanelerle çalışır; tarayıcı veya ek paket gerekmez.

| Alan | YÖK Atlas | TÜİK |
|---|---|---|
| Ad | YÖK Atlas | TÜİK SDMX |
| Kısa ad | `yokatlas` | `tuik-sdmx` |
| Komut | `python -m scraper.panel_yokatlas` | `python -m scraper.panel_tuik` |
| Çalışma klasörü | `.` | `.` |
| İlk zamanlama | Sadece elle | Sadece elle |
| Zaman aşımı | 1440 dakika | 60 dakika |

Panelde **Şimdi çalıştır**, **Durdur**, **Loglar** ve **Hatalıları yeniden dene**
kullanılır. İlerleme, HTTP istekleri, yazılan kayıt sayısı ve çalışma özeti
`botkit` üzerinden panele aktarılır. Başarısız veya yarım aktarım sıfır olmayan
çıkış kodu döndürür. Zamanlamayı panel yönetir; bot komutuna `--continuous`
eklenmez. Otomatik zamanlama bu kurulumda açık değildir.

## YÖK Atlas ayarları

```json
{
  "bekleme_saniye": 2,
  "sayfa_boyutu": 100,
  "azami_istek": 10000,
  "arsiv_dizini": "outputs/yokatlas_bot",
  "sadece_arsiv": false
}
```

Tam toplama uzun sürebilir. Önce tüm HTTP yanıtları JSON arşivine kaydedilir,
sonra PostgreSQL aktarımı başlar. Bu nedenle indirme sırasında yazılan DB kaydı
sayısının sıfır olması normaldir. Durdurulursa aynı arşiv diziniyle sonraki
çalıştırma eksik sayfadan devam eder. İstek bütçesi dolması tamamlanma sayılmaz.
Kalite/karantina uyarıları da başarı olarak gizlenmez.

**Hatalıları yeniden dene**, arşivin kaldığı noktadan devam eder; gerekli sonraki
sayfaları da toplar. Tamamlanmış bir snapshot'ın arşiv dosyaları silinmez.

## TÜİK ayarları

```json
{
  "dataflow_id": "DF_ADNKS_T16",
  "version": "1.0",
  "yil": 2025
}
```

Veri akışı ve sürüm resmi katalogla doğrulanır. Farklı kategori/veri seti için
bu alanları değiştir. `sadece_katalog: true` eklenirse veri yazmadan katalog
alınır ve akış listesi çalışma özetine eklenir; veri çekmek için bu ayarı kaldır.

`DF_ADNKS_T16` sürüm `1.0`, RAW'a ek olarak
`staging.tuik_population_by_province` tablosuna il kodlarıyla eşlenir.
`api.tuik_population_by_province` görünümü son gözlemleri sunar. Diğer akışlar
mevcut kapsamda RAW'da saklanır. Aynı yanıtın tekrar yüklenmesi kayıtları
çoğaltmaz; paneldeki yazılan kayıt sayısı bu nedenle sıfır olabilir. Toplam
gözlem ve staging sayısı ayrıca çalışma özetindedir.

TÜİK durdurulursa devam eden veri transaction'ı geri alınır; önce tamamlanmış
veriler korunur. Tekrar çalıştırma seçilen akışı yeniden alır. Başarısız veri
isteğinin tekrarında eski akış/sürüm/yıl kullanılır. Token/katalog hatalarının
tekrarında güncel ayarlar kullanılır. Otomatik sınırsız ağ denemesi yapılmaz.

## Gizli bilgiler ve veritabanı

Veri yazma bağlantısı `postgres:5432`, veritabanı `yokatlas_intelligence`,
kullanıcı `atlas_ingest` olarak kurulur. Şifre proje kökündeki `.env` dosyasının
`ATLAS_INGEST_PASSWORD` alanından okunur. `TUIK_API_KEY` de aynı özel dosyada
tutulur. Bu dosya `0600` izinlidir; Git'e veya panel ayarlarına eklenmez.
`ADMIN_DATABASE_URL` yalnızca `botkit`'in panel sayaçları ve çalışma kayıtları
içindir; kaynak verilerini yazmak için kullanılmaz.

Mevcut sunucuya `005_bot_condition_sync.sql` yetkisi ve
`006_tuik_population_by_province.sql` şeması uygulanmıştır. Botlar kendileri
migration çalıştırmaz. Yeni bir sunucuda bu migration'lar şema sahibiyle
uygulanmalıdır.

## Docker içinde elle deneme

Konteynerde panel kodu `/app` altındadır. Elle `/repo` içinden çalıştırırken
`botkit` bulunabilmesi için `PYTHONPATH=/app` ekle. Panel runner'ı bu yolu
kendisi ekler.

```sh
docker exec -it -w /repo -e PYTHONPATH=/app yokatlas-admin-runner-1 python -m scraper.panel_tuik
docker exec -it -w /repo -e PYTHONPATH=/app yokatlas-admin-runner-1 python -m scraper.panel_yokatlas
```

İsteğe bağlı, bilerek eksik bırakılan ve üretim arşivinden ayrı bağlantı denemesi:

```sh
docker exec -it -w /repo -e PYTHONPATH=/app \
  -e BOT_SETTINGS='{"sadece_arsiv":true,"azami_istek":6,"arsiv_dizini":"outputs/panel_connection_check"}' \
  yokatlas-admin-runner-1 python -m scraper.panel_yokatlas
```

Bu deneme 6 HTTP isteğinden sonra **2** çıkış kodu verir; checkpoint korunur.
Bir botun paneldeki çalışması sürerken aynı işi terminalden başlatma.
