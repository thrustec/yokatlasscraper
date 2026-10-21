# YÖK Atlas botu

SEGE/URAP PDF botları için [kurulum, CLI ve panel rehberini](../docs/backend/SEGE_URAP_BOTS_TR.md)
kullan. Komutlar `python -m scraper.report_bot sege` ve `python -m scraper.report_bot urap`;
ilk denemede `--archive-only` eklenebilir. Panel girişleri `scraper.panel_sege` ve
`scraper.panel_urap` modülleridir.

Merve'nin sunucudaki ortak admin paneli için
[iki botun kurulum ve ayar rehberini](../docs/backend/ADMIN_PANEL_BOTS_TR.md)
kullan. Panel girişleri `scraper.panel_yokatlas` ve `scraper.panel_tuik`
modülleridir. Aşağıdaki komutlar panelden bağımsız CLI kullanımı içindir.

Bot bütün veri gruplarını sırayla toplar: üniversiteler, program grupları, konumlar, beş puan türündeki programlar ve netler. Tablo seçme arayüzü gerekmez. `status` komutu hangi grupta/sayfada olduğunu gösterir. Koşullar, program yanıtından ilgili ilişki tablolarına ayrıştırılır; `api.*` görünümlerine ayrıca veri yazılmaz.

HTTP toplama ve veritabanına dağıtım ayrı fazlardır. Her başarılı HTTP sayfası **orijinal JSON yanıtı** olarak diske yazılır; istek, çekim zamanı ve SHA-256 ayrı bir `.meta.json` dosyasına kaydedilir. Tam indirme bittikten sonra RAW → STAGING → CORE aktarımı başlar. Bir HTTP veya DB kesintisi diğer fazın arşivini kaybettirmez.

Katalog yılı ve sonuç açıklanma durumu yardımcı servislerden ayrıca okunur; snapshot manifestinde ve DB koşusunun `details.source_parameters` alanında saklanır. Böylece geçmiş dönem alanlarını yorumlamak için kullanılan kaynak bağlamı da korunur.

CSV ana arşiv olarak kullanılmaz: `kosulList` ve bilinmeyen iç içe alanlar ile `null`, boş değer, sayı/metin ayrımı JSON'da korunur. Excel veya başka bir sistem için CSV gerekiyorsa sonradan bu arşivden ya da veritabanından üretilebilir. CSV dışa aktarma bu sürüme eklenmedi.

## Kurulum

Python 3.10+ gerekir. Komutları depo kökünden çalıştır.

```sh
python -m venv .venv
```

Linux/macOS:

```sh
.venv/bin/python -m pip install -r scraper/requirements.txt
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r scraper/requirements.txt
```

Aşağıdaki örneklerde `python`, bu sanal ortamın Python çalıştırıcısını ifade eder. Etkinleştirme yerine yukarıdaki tam çalıştırıcı yolunu da kullanabilirsin.

## Önce yalnızca dosyalara kaydet

```sh
python -m scraper.bot run --archive-only
python -m scraper.bot status
```

Varsayılan arşiv dizini `outputs/yokatlas_bot`. `--root` ile değiştirilebilir. Varsayılan sayfa boyutu 20, istek aralığı en az 2 saniyedir. `--page-size` için 1–100 sınırı botun yerel korumasıdır, YÖK'ün resmî kotası değildir. Tam tarama binlerce istek ve saatler sürebilir.

Küçük ve **bilerek eksik bırakılan** bir bağlantı kontrolü:

```sh
python -m scraper.bot run --archive-only --root outputs/bot_connection_check --max-requests 4
```

İstek bütçesi dolunca çıkış kodu 2 olur, tamamlandı sayılmaz. Aynı komutu yeniden çalıştırmak kaydedilmiş sayfaları doğrular ve sonraki eksik sayfadan devam eder. Yeniden başlatırken aynı `--root` kullanılmalı. Yarım kalmış koşunun sayfa boyutu arşivden alınır; sayfa boyutu ancak yeni bir koşuda değişir.

## PostgreSQL'e otomatik dağıt

Hedef, mevcut `yokatlas_intelligence` şemasıdır. Gerekli tablolar ve `004_archive_idempotency.sql` indeksi hazır olmalı. Bot **kendiliğinden migration uygulamaz**.

Mevcut kurulumda **`005_bot_condition_sync.sql`** bir kez şema sahibiyle uygulanmalı. Bu migration yalnızca `core.program_conditions` ilişkilerini güncellerken gereken DELETE yetkisini `atlas_ingest` rolüne verir. RAW veya program tablolarında DELETE izni vermez; kolon veya tablo eklemez. Yeni Docker kurulumunun bootstrap akışına da eklenmiştir.

Mevcut Docker kurulumu için:

```sh
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 -U atlas_owner -d yokatlas_intelligence -f /opt/atlas/migrations/005_bot_condition_sync.sql
```

Windows'ta mevcut `scripts/database/apply-migrations.ps1` de güncellenmiş migration sırasını uygular. Gerçek sunucunun mevcut şeması ve rol yetkileri ayrıca doğrulanmalı.

`scraper/.env.example` dosyasını depo dışındaki özel bir env dosyasına kopyala ve doldur. Desteklenen bağlantı alanları `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`; uzak sunucu için ayrıca `PGSSLMODE`, `PGSSLROOTCERT`. Dosya `KEY=value` satırları kullanır; değer etrafındaki eşleşen tek/çift tırnaklar kaldırılır, shell komutları veya değişken genişletme çalıştırılmaz. Dosyanın erişimini servis hesabıyla sınırla.

```sh
python -m scraper.bot run --env-file /private/path/yokatlas-bot.env
```

Ortam değişkenleri dosyadan önceliklidir. `--env-file` verilmezse mevcut kök `.env` okunur; eski `ATLAS_INGEST_PASSWORD` ve `POSTGRES_PORT` alanları da desteklenir. Şifre komut satırına veya GitHub'a yazılmamalı. TLS doğrulaması açık kalır; HTTPS için özel kurum CA'sı gerekiyorsa Requests'in `REQUESTS_CA_BUNDLE` ortam değişkeni kullanılabilir.

Veritabanı olmadan toplanmış bir arşivi daha sonra yüklemek için:

```sh
python scripts/database/load_archive.py --root outputs/yokatlas_bot/snapshots/SNAPSHOT_ADI --env-file /private/path/yokatlas-bot.env
```

Arşiv kökü, `manifest.json` ve `complete_data/` içeren tek bir snapshot dizinidir. Eksik snapshot veya checksum uyuşmazlığı aktarımı durdurur. DB'ye her sayfa **tek transaction** içinde yazılır; hata alan sayfa geri alınır. Aynı arşivi tekrar yüklemek RAW/STAGING kayıtlarını çoğaltmaz. Kaynak verisi yeni snapshot'ta daha önceki bir değere dönerse RAW tekrarlanmaz, CORE yeniden eşlenir. Her DB koşusunun gözlediği yanıt kimlikleri `raw.ingestion_runs.details.observed_response_ids` içinde tutulur.

Tipi hatalı kayıtlar ham haliyle korunur ve `quality.quarantined_records` içine alınır. Aynı net anahtarına farklı içerik gelirse sessizce üzerine yazılmaz; inceleme için karantinaya gider. Koşu `completed_with_issues` olarak işaretlenir. Bu durumda veri toplama bitmiştir fakat bazı verilerin CORE'a geçmesi inceleme gerektirir.

İsteğe bağlı il veya program grubu referansı çözülemezse kaynak değer JSON içinde korunur, CORE referansı boş bırakılır ve koşu kalite uyarısı üretir. Aktarım sayfa bazında atomiktir; koşunun tamamı tek transaction değildir. Aktarım sürerken mevcut API görünümleri kısmen güncellenmiş verileri görebilir. Bütün koşuyu tek seferde yayımlama kapısı bu ilk sürümün kapsamında değildir.

## Sürekli çalışma ve kesinti sonrası devam

```sh
python -m scraper.bot run --continuous --env-file /private/path/yokatlas-bot.env
```

Tamamlanan snapshot'tan 24 saat sonra yenisi başlar. `--interval` saniye cinsinden değiştirilebilir. Geçici HTTP ve DB erişim hataları kontrollü aralıklarla yeniden denenir. `429` için `Retry-After` dikkate alınır. `403`/`418`, TLS doğrulama hatası, bozuk arşiv ve şema uyuşmazlığı operatör incelemesi için servisi durdurur; engel aşılmaya çalışılmaz.

- İnternet kesintisinde aynı gruptaki ilk eksik **sayfadan** devam edilir.
- DB kesintisinde yeniden HTTP indirmesi yapılmaz; arşiv üzerinden aktarım sürer.
- Başarılı sayfa işlemleri tekrar kayıt üretmez; yarıda kalan sayfa transaction'ı yeniden çalışır.
- Bir arşiv dizini için OS dosya kilidi, DB aktarımı için PostgreSQL advisory lock kullanılır; aynı işi iki süreç eşzamanlı yürütemez.
- Kaynak toplamı veya katalog yılı tarama sırasında değişirse yarım snapshot `superseded` olur, saklanır ve sonraki deneme yeni snapshot açar. Eski dosyalar silinmez.

Çıkış kodları: `0` tamamlandı, `2` devam edilebilir kesinti/bütçe veya değişen snapshot, `3` yapılandırma/erişim/veri incelemesi gerekli, `4` tamamlandı ama karantinada kayıt var, `130` kullanıcı durdurdu. Sürekli modda geçici kesintiler ve karantina uyarıları sonraki çalışmaları engellemez. `status` dosyası süreç durduktan sonra da okunabilir; canlı süreç sağlık kontrolü yerine geçmez.

Arşiv düzeni:

```text
outputs/yokatlas_bot/
  state.json
  snapshots/20261017T010000Z-abc123/
    manifest.json
    complete_data/universities/all.json
    complete_data/universities/all.meta.json
    complete_data/programs/SAY/page_000000.json
    complete_data/programs/SAY/page_000000.meta.json
    complete_data/net_results/SAY/page_000000.json
    ...
```

JSON dosyaları ve makbuzları birlikte yedeklenmeli. Otomatik silme politikası yok; disk kapasitesi ve yedekleme sunucu işletiminde izlenmeli. Arşivler varsayılan olarak Git tarafından dışlanır.

## Linux / Windows sunucusu

Linux için [systemd örneği](deploy/yokatlas-bot.service) hazır. Depo yolu `/opt/yokatlas-intelligence`, servis kullanıcısı `atlas`, env dosyası `/etc/yokatlas-bot.env` olarak örneklenmiştir; kuruluma göre düzenlenmeli. systemd arşiv dizinini `/var/lib/yokatlas-bot` altında oluşturur. Servis dosyası, işletim sistemi hesabı ve env dosyası hazırlanıp servis yöneticisine kurulmalıdır; geliştirme sırasında servis etkinleştirilmez.

Windows'ta Görev Zamanlayıcı'ya sistem açılışında başlayan bir görev eklenebilir:

- Program: deponun `.venv\Scripts\python.exe` dosyasının tam yolu.
- Argümanlar: `-m scraper.bot run --continuous --root "D:\YOKAtlasData" --env-file "D:\Private\yokatlas-bot.env"`.
- Başlangıç dizini: deponun tam yolu. Kullanıcı oturum açmasa da çalışacak servis hesabı seçilmeli.
- Yeni örnek başlatmayı engelle, uzun görevleri süre doldu diye sonlandırma. Çıkış kodu 3 operatör incelemesi gerektirir; engellenen kaynağı sürekli yeniden başlatan bir kural ekleme.

## Testler ve mevcut sınırlar

```sh
python -m unittest discover -s tests/scraper -v
python -m unittest discover -s tests/database -v
```

Gerçek PostgreSQL testleri yalnızca `YOKATLAS_TEST_DSN` ayarlandığında çalışır ve hedef DB adının `test_yokatlas_` ile başlamasını zorunlu tutar. Bu testler kendilerine ayrılmış boş bir veritabanı ve yönetici rolü gerektirir; üretim veritabanında çalıştırılmaz. Testler mevcut örnek şemayı kurar ve test tablolarını temizler. PyYAML, eski `tests/database` paketinin ek test bağımlılığıdır.

Bu sürüm beş doğrulanmış kaynak grubunu ve API'nin sağladığı bütün puan türü/yıl kayıtlarını toplar; geçmişte mevcut olup güncel API'den kaldırılmış verileri üretemez. Geçmiş dönem göstergeleri orijinal program JSON'unda saklanır; doğrulanmamış yıl eşlemesiyle eski yılın tam program kaydı oluşturulmaz. Net–program ilişkisi yalnızca kod, yıl ve puan türü eşleşiyorsa kurulur.

API atomik bir snapshot kimliği sunmadığı için aynı sayıda kayıtla gerçekleşen tarama içi değişiklikler tamamen saptanamaz. Kaynaktan kaybolan programlar CORE'dan otomatik silinmez; snapshot arşivi o koşuda gerçekten görülen kapsamı gösterir. Aynı yıl içindeki tüm değişiklikler dosya/RAW geçmişinde korunur; CORE son işlenen program sürümünü sunar. Koşulların açıklamaları `core.conditions.raw_details.descriptions_by_year` içinde yıl bazında tutulur, programın koşul ilişkileri yenilenir.

Web yönetim arayüzü, CSV dışa aktarma, alarm entegrasyonu ve sunucuya otomatik kurulum eklenmedi. İlk sürümün amacı tüm veri gruplarını izlenebilir biçimde toplamak ve tekrar çalıştırılabilir şekilde mevcut PostgreSQL şemasına dağıtmaktır.
