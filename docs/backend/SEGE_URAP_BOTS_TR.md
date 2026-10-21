# SEGE ve URAP PDF botları

İlk sürüm, SEGE 2025 il/bölge sonuçlarını, sekiz il alt boyut sırasını, SEGE 2022 ilçe sonuçlarını ve URAP 2025-2026 Türkiye genel sıralamasını toplar. İndirilen PDF orijinal haliyle saklanır, kontrolleri geçen tam rapor PostgreSQL API görünümlerine yayımlanır. İlçe raporunun il içi sıraları ve kademeleri Ek-2 ile çapraz kontrol edilir. URAP puanları ham yayın/atıf/proje sayısı değildir.

## Kurulum

Python 3.10+ ve mevcut ingest bağlantısı gerekir. Proje kökünden:

```sh
python -m pip install -r scraper/requirements.txt
```

Bu komut `pdfplumber` bağımlılığını da kurar. Panel için paketin runner ortamına/imajına kurulması gerekir; sadece geliştirme bilgisayarına kurmak yeterli değildir. `botkit` mevcut panel tarafından sağlanır; bağımsız CLI için gerekli değildir.

Mevcut şemaya `007_sege_urap_reports.sql` bir kez şema sahibiyle uygulanmalı. Botlar migration çalıştırmaz. Yeni Docker kurulumunun bootstrap listesine ve Windows migration komutuna eklenmiştir. Mevcut Docker veritabanında:

```sh
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U atlas_owner -d yokatlas_intelligence -f /opt/atlas/migrations/007_sege_urap_reports.sql
```

`ATLAS_INGEST_PASSWORD` proje kökündeki özel `.env` dosyasından veya ortamdan okunur. `PGHOST`, `PGPORT` / `POSTGRES_PORT`, `PGDATABASE`, `PGSSLMODE`, `PGSSLROOTCERT` desteklenir. Yazma rolü her zaman `atlas_ingest` olur. `ADMIN_DATABASE_URL` ve `PGPASSWORD` veri aktarımında kullanılmaz. SEGE/URAP kaynakları API anahtarı istemez.

`core.cities` ve URAP için `core.universities` daha önce YÖKAtlas verisiyle doldurulmuş olmalı. Kaynakta bulunmayan üniversite/il bot tarafından uydurularak oluşturulmaz.

## Önce yalnızca arşivle

```sh
python -m scraper.report_bot sege --archive-only
python -m scraper.report_bot urap --archive-only
```

SEGE varsayılan olarak iki raporu da alır. Tek rapor seçmek için:

```sh
python -m scraper.report_bot sege --report sege-il-2025 --archive-only
python -m scraper.report_bot sege --report sege-ilce-2022 --archive-only
python -m scraper.report_bot urap --report urap-tr-2025-2026 --archive-only
```

Kaynak erişilemiyorsa resmî PDF'i proje içindeki bir dosyadan verebilirsin. Yerel PDF için tek rapor seçilmeli:

```sh
python -m scraper.report_bot sege --report sege-ilce-2022 --pdf inputs/2022-ilce-sege.pdf --archive-only
```

PDF yolu ve `--root` arşiv yolu proje içinde göreli olmalı; `..`, mutlak yol ve proje dışına çıkan symlink reddedilir. İndirilen dosyada PDF imzası ve 40 MB sınırı kontrol edilir. Kaynağın hata HTML'i PDF olarak kabul edilmez; TLS doğrulaması kapatılmaz, resmî alan adı dışına yönlendirme izlenmez. Kaynak erişim hatalarında panelde başarısız HTTP isteği kaydedilir; sınırsız otomatik tekrar yapılmaz.

Arşiv:

```text
outputs/sege_bot/                         # URAP: outputs/urap_bot/
  sege-il-2025/
    latest.json
    <pdf-sha256>/
      source.pdf
      source.meta.json
      reports-pdf-1/
        manifest.json
        extraction.json
```

`latest.json` son alınan yerel PDF'i gösterir; siteye yayımlanmış rapor anlamına gelmez. Kaynak ve çıkarım SHA-256 değerleri her yeniden yüklemede doğrulanır. Ayrıştırma hata verse bile PDF ve indirme makbuzu korunur. Aynı PDF tekrar geldiğinde doğrulanmış çıkarım önbellekten okunur. Arşiv dosyaları Git dışında tutulur; PDF, makbuz ve JSON dosyaları birlikte yedeklenmeli.

## Veritabanına aktar

Kaynağı yeniden indirerek çalıştırmak için `--archive-only` bayrağını kaldır. DB/ağ kesintisinden sonra, indirme yapmadan mevcut arşivden devam etmek için:

```sh
python -m scraper.report_bot sege --offline
python -m scraper.report_bot urap --offline
```

SEGE'de `--offline` varsayılan iki raporu da bekler; yalnızca birini arşivlediysen `--report` ile seç. `--offline --archive-only` dosyaların bütünlüğünü ve çıkarımını DB olmadan denetler.

Beklenen kapsam: 81 il ve her ilde sekiz boyut sırası; 26 Düzey-2 bölgesi ve 81 il kapsamı; 973 ilçe ve 81 il içindeki eksiksiz sıralar; URAP'ta 198 üniversite. Yinelenen sıralar, eksik/ters puan sırası, uyuşmayan ilçe ekleri, yanlış kademe veya URAP toplam/bileşen uyuşmazlığı aktarımı durdurur. Yuvarlanmış eşit skorlar yeniden sıralanmaz. PDF'deki sıralar korunur.

İller ad üzerinden mevcut `core.cities` kimliklerine bağlanır. Üniversiteler Türkçe karakter ve boşluk/noktalama farkları normalize edilerek eşlenir; benzer ada bakılarak tahmin yapılmaz. Eksik/çakışan eşlemeler çalışma özetinin `issues` alanında görünür. Bütün kaynak satırları RAW/STAGING'de korunur, fakat hatalı rapor yeni yayın olarak etkinleşmez. Daha önce yayımlanmış aynı raporun hatalı yeniden eşlemesi de görünür veriyi değiştirmez.

Adı farklı bir üniversite için açık eşleme JSON'u kullanılabilir:

```sh
python -m scraper.report_bot urap --offline --university-map inputs/urap-universite-eslemeleri.json
```

Dosya biçimi `{ "PDF'teki üniversite adı": 12345 }` şeklindedir; `12345` yalnızca örnektir. Gerçek `core.universities.universite_id` kullanılmalı. Eşleme hedefi mevcut olmak zorundadır. Aynı ID'ye bağlanan iki kaynak üniversitesi yayın kontrolünden geçmez. İlçe için bu sürümde kaynak il+ilçe kimliği kullanılır; doğrulanmamış kampüs/ilçe kodu eşlemesi yapılmaz.

Her raporun RAW, STAGING ve yayın güncellemesi tek transaction içindedir. Başarısız veya durdurulan DB işlemi geri alınır; önceden yayımlanmış sürüm görünür kalır. Eşleme uyarılarında kaynak ve staging kaydedilir, yayın kapısı kapalı kalır. Aynı raporu tekrar çalıştırmak belge/satır çoğaltmaz; aynı PDF yeni eşlemeyle tekrar işlenebilir. Daha eski bir arşiv yeni yayımlanmış revizyonun üzerine etkinleştirilemez. Aynı arşiv kökü için dosya kilidi, aynı raporun DB aktarımı için PostgreSQL advisory lock kullanılır.

CLI çıkışları: `0` arşivlendi/tamamlandı, `3` erişim/yapılandırma/ayrıştırma/DB hatası, `4` eşleme uyarıları nedeniyle yayımlanmadı, `130` kullanıcı durdurdu.

## Ortak admin paneli

| Alan | SEGE | URAP |
|---|---|---|
| Kısa ad | `sege` | `urap` |
| Komut | `python -m scraper.panel_sege` | `python -m scraper.panel_urap` |
| Çalışma klasörü | `.` | `.` |
| İlk zamanlama | Elle | Elle |
| Önerilen zaman aşımı | 30 dakika | 30 dakika |

Panelde bu iki komut yeni bot olarak kaydedilmeli. Mevcut panel runner'ı `/repo` çalışma klasörü ve `botkit` import yolunu sağlar. **Şimdi çalıştır**, **Durdur**, **Loglar** ve **Hatalıları yeniden dene** mevcut panel sözleşmesini kullanır. Retry, ayarlar sonradan değiştirilmiş olsa da başarısız isteğin önceki raporunu seçer. Eşleme hataları HTTP hatası olmadığından düzeltildikten sonra **Şimdi çalıştır** kullanılmalı.

SEGE örnek ayarlar:

```json
{
  "rapor": "tum",
  "arsiv_dizini": "outputs/sege_bot",
  "sadece_arsiv": false,
  "cevrimdisi": false
}
```

URAP örnek ayarlar:

```json
{
  "rapor": "urap-tr-2025-2026",
  "arsiv_dizini": "outputs/urap_bot",
  "sadece_arsiv": false,
  "cevrimdisi": false,
  "universite_eslemeleri": {}
}
```

Yerel dosya seçmek için `pdf_dosyasi` eklenebilir. Bu durumda tek rapor seçilmeli ve `cevrimdisi` kapalı olmalı. Parola panel ayarlarına yazılmaz. Panel çalışmaları veri bağlantısında `postgres:5432` ve `yokatlas_intelligence` kullanır; sayaçlar/çalışma geçmişi `botkit` üzerinden aktarılır. Eşleme uyarısı veya yarım aktarım başarılı gösterilmez.

Yerel demo `/ops/v1/bots` kataloğu yeni botların komutlarını `cli_only` olarak listeler. Yerel demo HTTP `POST runs` hâlâ TÜİK'e aittir; SEGE/URAP çalıştırması ortak runner veya CLI üzerinden yapılır.

## Site API'si

- `GET /api/rapor-yayinlari`: Kontrolleri geçen güncel rapor revizyonları, kaynak dönemi/URL/hash ve kapsam.
- `GET /api/sege?duzey=il`: Son yayımlanmış il raporu; `ilce` veya `bolge` seçilebilir. `yil`, `il_kodu`, `kademe`, `q`, `limit`, `offset` filtreleri vardır.
- `GET /api/urap`: Son yayımlanmış Türkiye genel sıralaması. `donem=2025-2026`, `universite_id`, `il_kodu`, `q`, `limit`, `offset` filtreleri vardır.

Varsayılan sayfa boyutu 100, üst sınır 100; 973 ilçe veya 198 üniversitenin tamamı için sayfalanmalı. API yalnızca `api.report_publications`, `api.sege_results`, `api.urap_rankings` görünümlerini okur. Yerel arşiv yolu ve tam RAW payload halka açık uçlarda yoktur. SEGE'de `yil`, URAP'ta `donem` ve kaynak PDF sayfası/tablosu yanıtta korunur. Raporda olmayan bir yıl için yapay gözlem oluşturulmaz.

## Doğrulama ve kapsam sınırı

```sh
python -m unittest discover -s tests/scraper -v
python -m unittest discover -s tests/backend -p test_reports_api.py -v
```

Resmî PDF testleri için `REPORT_BOT_PDF_DIR`, incelemedeki `sege_2025.pdf`, `sege_district_2022.pdf`, `urap_tr_2025_2026.pdf` dosyalarını içeren dizini gösterebilir. DB testleri `REPORT_BOT_TEST_DSN` ile yalnızca `test_yokatlas_` ön ekli, kendilerine ayrılmış veritabanında çalışır; test tablolarını temizler. Bunlar üretim DB'sinde çalıştırılmamalı.

Bu sürüm doğrulanan üç raporu destekler. Aynı URL'deki içerik değişikliği hash ile izlenir; yeni yıl/dönem bağlantılarının otomatik keşfi, OCR, URAP Dünya/alan/alt grup sıralamaları ve tarihsel raporlar kapsam dışındadır. Yeni bir rapor düzeni sessizce kabul edilmez; `report_parsers.py` içindeki kaynak ve ayrıştırıcı güncellenip gerçek dosyayla doğrulanmalı. Panel zamanlaması istenirse mevcut raporların yeniden kontrolü için haftalık ayarlanabilir; bu kurulum otomatik zamanlama açmaz.

## 19 Ekim 2026 sunucu kurulumu

Botlar `/home/deploy/yokatlas` dizinine kuruldu; migration 007 üretim veritabanına transaction içinde uygulandı. Panelde **SEGE** (`bot_id=4`) ve **URAP** (`bot_id=5`) açık, sadece elle çalışacak ve 30 dakika zaman aşımı kullanacak şekilde kayıtlıdır. İlk üretim çalışmaları panelden başlatıldı:

| Bot | Çalışma | Sonuç | Yayımlanan kayıt |
|---|---|---|---|
| SEGE | `#5` | Başarılı; 2 kaynak isteği, 0 hata | 81 il + 26 bölge + 973 ilçe = 1.080 |
| URAP | `#6` | Başarılı; 1 kaynak isteği, 0 hata | 198 üniversite |

Üç raporda da kimlik eşleme uyarısı yoktur. `atlas_api` rolünün yayımlanmış verileri okuyabildiği ayrıca doğrulandı. Kaynak PDF'ler sunucudaki `outputs/sege_bot` ve `outputs/urap_bot` dizinlerinde saklanır. Kurulum kanıtı [deployment JSON'unda](../evidence/2026-10-19_sege_urap_deployment.json) bulunur.

YÖKAtlas'ta 83 üniversitenin adında parantez içinde şehir eki vardır. [Üniversite eşlemeleri](../../inputs/urap-universite-eslemeleri.json), PDF'teki ad ve şehrin mevcut üniversite adıyla birebir karşılaştırılmasıyla oluşturuldu; benzerlik tahmini kullanılmadı. Bu dosyadaki kimlikler bu veritabanına aittir. URAP'ın panel ayarlarındaki `universite_eslemeleri` nesnesine de kaydedildi. Elle CLI çalıştırırken `--university-map inputs/urap-universite-eslemeleri.json` eklenmeli. Başka bir veritabanında mevcut kimliklerle tekrar doğrulanmalı.

Panelin ayrı kaynak dizini `/opt/yokatlas-admin/admin-panel` altındadır. `requirements-bots.txt` içine `pdfplumber>=0.11,<0.12` eklendi; runner imajı yeniden oluşturuldu ve `pdfplumber 0.11.10` doğrulandı. Panelin Kapsam ekranına `api.sege_results` ve `api.urap_rankings` sayaçları eklendi; [iki satırlık patch](patches/admin_panel_sege_urap_coverage.patch) ayrıca saklandı. Web imajı bu değişiklikle yeniden oluşturuldu.

Değiştirilen panel dosyalarının yedekleri aynı dizinlerde `requirements-bots.txt.pre-sege-urap-20261019` ve `adminpanel/web.py.pre-sege-urap-20261019` adlarıyla tutulur. Geri dönüş gerekirse önce yeni botları panelden kapatıp çalışan görev olmadığını doğrulayın; bu iki dosyayı geri yükleyerek web/runner imajlarını yeniden oluşturun. Veritabanındaki raporları veya mevcut botları silmek gerekmez.
