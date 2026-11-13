# RAW API admin panel geçiş hazırlığı (9 Kasım 2026)

Bu dosya **hazırlıktır; deployment/DB yazma yapılmamıştır.** Eski `ops.bots` komutları ve çalışan admin paneli değiştirilmemiştir.

## Mevcut topoloji
- Bot konteyneri: `yokatlas-admin-runner-1`; proje bind mount: `/home/celal/yokatlas -> /repo`.
- DB: `yokatlas-intelligence-postgres-1`.
- API için beklenen Docker DNS: `http://yokatlas-data-api:8000` (aynı Docker ağı gerekli).
- Emre'nin 9 Kasım notunda API image build edilmiş ama DB bağlantısı başarısız: API **henüz hazır değil**.
- Admin paneli bot komutlarını `ops.bots.command` alanından okuyor; `runner.py` değiştirilmez.

## Hazırlanan değişiklikler
- `scraper/data_api/client.py`: HTTP sadece loopback veya *tam olarak* `yokatlas-data-api:8000` için kabul edilir; diğer açık HTTP adresleri reddedilir.
- `scraper/data_api/panel.py`: `python -m scraper.data_api.panel {yokatlas|sege|urap}` şeklinde tek çalışma akışı. `botkit.Bot.from_env()` ile mevcut panelin run ID'sine bağlanır.
- Bu giriş noktası, API `/status` yanıtında `status=ok` ve `database=connected` doğrulanmadan kaynak toplamaz. Sırf health yanıtı INSERT yetkisini kanıtlamaz.
- YÖK Atlas arşiv toplama -> doğrulama -> `POST /api/db/write`; SEGE/URAP PDF arşiv -> RAW `report_documents`. Eski direkt DB importer çağrılmaz.
- `sadece_arsiv=true` için API sağlıklıysa yalnız arşivler. Eski rapor ayarlarındaki özel arşiv dizini, yerel PDF ve üniversite eşlemesi bu adaptörde desteklenmiyor; sessizce yok sayılmak yerine hata verir.
- TÜİK mevcut SDMX akışı henüz bu adaptöre alınmadı: mevcut `tuik-sdmx` komutu **değiştirilmemeli**.

## API/Celal tamamladıktan sonra işlem sırası
1. Emre + Celal: API DB erişimi/RAW INSERT yetkilerini doğrular. Bot runner ile API aynı Docker ağına dahil edilir.
2. Bot konteynerinde `DATA_API_BASE_URL=http://yokatlas-data-api:8000` ve **API'nin gerçekten kullandığı** `DB_WRITE_API_KEY` tanımlanır. Bunun için admin Compose environment/env_file düzenlenip runner yeniden oluşturulmalıdır; çalışan konteyner içindeki `export` kalıcı olmaz. Başka bir .env dosyasındaki anahtarın eşit olduğu varsayılmaz.
3. Botun API erişimi ve `/status` doğrulaması yapılır:
   `sudo docker exec yokatlas-admin-runner-1 python -c "import urllib.request; print(urllib.request.urlopen('http://yokatlas-data-api:8000/status', timeout=5).read().decode())"`
4. **Önce ayrı test ortamında** küçük bir `ingestion_runs -> api_responses -> source_records` yazma testi yapılır; aynı kaydın tekrar denenmesi/idempotency ve checkpoint kontrol edilir. Üretimde körlemesine INSERT yapılmaz.
5. Bot dosyaları güncel checkout'tan `/home/celal/yokatlas/scraper/data_api/` altına kontrollü aktarılır. `--help` veya Python import ile giriş noktası doğrulanır.
6. Admin panelinde **mevcut bot kayıtlarının** komutları yedeklendikten ve panel ayarları uyumluluğu doğrulandıktan sonra yalnız şu üç kayıt değiştirilir:
   - `yokatlas`: `python -m scraper.data_api.panel yokatlas`
   - `sege`: `python -m scraper.data_api.panel sege`
   - `urap`: `python -m scraper.data_api.panel urap`
   - `tuik-sdmx` ve `ornek-bot` aynı kalır.
7. Canlıda ilk çalışma yalnız yetkili ekibin onayıyla ve gözlem altında. Eski komutlara dönüş için önceki `ops.bots.command` değerleri korunur.

## Üretim için açık maddeler
- Mevcut RAW API yalnız INSERT destekler: run completion, atomik parent-child yazma, 409/timeout uzlaştırma hâlâ çözülmeli.
- `outputs/data_api/checkpoint.sqlite3` ve WAL dosyaları kaybolmamalı.
- Admin bot ayarları, durdurma/cancel semantiği ve zamanlanmış çalıştırmalar canlı geçiş öncesinde doğrulanmalı. Yeni adaptör panelin stop isteğini kaynak toplama sırasında eski `botkit` kadar ayrıntılı işlemez.
- SEGE/URAP staging/core yayınlaması yeni adaptörde yoktur; bunu ayrı ETL yapmalıdır.

## Geri dönüş
API botu devreye alındıktan sonra problem çıkarsa `ops.bots.command` alanındaki yedek eski komutlar geri yüklenir; hiçbir arşiv/checkpoint silinmez. Veritabanı INSERT'leri geri alınmış sayılmaz.
