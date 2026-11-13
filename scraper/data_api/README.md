# RAW API botları

Bu paket, YÖK Atlas ve rapor botlarının oluşturduğu arşivleri RAW API'ye aktarır. Komutları depo kökünden çalıştır.

Panelden çalıştırmak için [geçiş rehberine](ADMIN_PANEL_GECIS_TR.md) bak.

## Yapılanlar

- `POST /api/db/write`: yalnız `raw` tablosuna tek satır `INSERT`, `X-API-Key`, `201/key` kontrolü.
- SQLite **write-ahead checkpoint**: işlemi isteğin öncesinde kaydeder; 201/PK gelirse committed; 409/4xx reddedilirse rejected; timeout veya belirsiz sonuçta **uncertain** ve manuel uzlaştırma ister.
- **YÖK Atlas:** zaten yazılmış botu `--archive-only` modunda koşturur veya tamamlanmış mevcut arşivi doğrular. `ingestion_runs` -> `api_responses` -> `source_records` sırasıyla yazar; sayfa checksum ve manifest tamlığını yazmadan önce doğrular.
- **SEGE/URAP:** var olan PDF indirme/parse kodunu değiştirmeden yalnız arşiv modunda kullanır; sonrasında `ingestion_runs` -> `report_documents` yazar. **Staging/publikasyon yapmaz**.
- **OpenAlex:** resmî HTTPS API'den kontrollü, filtreli cursor sayfalama; ham JSON arşivi; `api_responses` ve (önceden mevcut tip sözlüğü şartıyla) `openalex_object_snapshots` INSERT. Varsayılan 5 sayfa, en çok 50; ücretsiz API key, sonraki cursor sayfaları için gereklidir. Tam OpenAlex veri tabanı/normalized nesne upsert'i yapılmaz.
- **TÜİK:** resmî HTTPS kaynaktan JSON olursa arşivleme ve `api_responses`; yalnız doğrulanmış legacy `tuik_df_adnks_t16` tipindeki **JSON** kayıtları için opsiyonel `source_records`. TÜİK'in gerçek SDMX CSV/XML veri modeli ve `raw.tuik_*` tablolarını doldurma bu sürümde yoktur.
- 21 yerel unit test; **gerçek uzak API / DB entegrasyon testi değil**.

## Kurulum

```bash
python -m pip install -r scraper/requirements.txt
python -m unittest discover -s tests/scraper -p 'test_raw_data_api.py' -v
```

Gizli dosya (örnek; değerler temsilidir):

```dotenv
DATA_API_BASE_URL=https://YOUR-REAL-API-BASE-URL
DB_WRITE_API_KEY=YOUR-REAL-API-KEY
```

Bunu repoya commit etme. `.env.example` örnekleri dışında gerçek anahtar koyma. `--env-file` global argümandır, **komuttan önce** verilir. Ortam değişkeni dosyadaki değeri geçersiz kılar.

## Komutlar

Arşivin tutarlılığını DB'ye yazmadan kontrol et:

```bash
python -m scraper.data_api.cli yokatlas --snapshot outputs/yokatlas_bot/snapshots/SNAPSHOT_ADI --verify-only
```

Çalışan YÖK botunu sadece JSON arşivi almak için çalıştır:

```bash
python -m scraper.data_api.cli yokatlas-live --max-requests 100 --archive-only
```

Tamamlanan mevcut YÖK arşivini API'ye yaz:

```bash
python -m scraper.data_api.cli --env-file /guvenli/atlas-api.env yokatlas --snapshot outputs/yokatlas_bot/snapshots/SNAPSHOT_ADI
```

YÖK botunu tam arşiv oluşturacak şekilde çalıştır **ve** ardından API'ye yaz (tamamlanmamış/yarım arşiv gönderilmez):

```bash
python -m scraper.data_api.cli --env-file /guvenli/atlas-api.env yokatlas-live --max-requests 5000
```

SEGE veya URAP, sadece arşivle:

```bash
python -m scraper.data_api.cli report-live --source sege --archive-only
python -m scraper.data_api.cli report-live --source urap --archive-only
```

SEGE/URAP, PDF arşivle ve sonra API'ye RAW olarak kaydet:

```bash
python -m scraper.data_api.cli --env-file /guvenli/atlas-api.env report-live --source sege
python -m scraper.data_api.cli --env-file /guvenli/atlas-api.env report-live --source urap
```

Mevcut rapor arşivini kullan (örnek):

```bash
python -m scraper.data_api.cli --env-file /guvenli/atlas-api.env report --archive outputs/sege_bot/sege-il-2025/PDF_SHA256/reports-pdf-1
```

OpenAlex Türkiye'deki kurumları 2 sayfa arşivle (API key ortam değişkeninden):

```bash
python -m scraper.data_api.cli openalex-crawl --entity-type institutions --filter 'country_code:TR' --pages 2 --archive-only
```

Aynı akışı RAW'a yaz:

```bash
python -m scraper.data_api.cli --env-file /guvenli/atlas-api.env openalex-crawl --entity-type institutions --filter 'country_code:TR' --pages 2
```

Resmî kaynaktan **JSON** endpoint arşivle ve sonra kayıt aktar (dönen dizini kullan):

```bash
python -m scraper.data_api.cli fetch-json --source openalex --url 'https://api.openalex.org/institutions?filter=country_code:TR&per_page=1'
python -m scraper.data_api.cli --env-file /guvenli/atlas-api.env capture --directory outputs/source_json/openalex/CAPTURE_ADI --openalex-type institutions
```

TÜİK için yalnız gerçekten JSON yanıt veren ve kaynak sözleşmesine uyan endpoint kullanılabilir. SDMX CSV/XML yanıtını bu komuta verirsen hata verir; CSV/XML'i JSON diye dönüştürmez. Legacy TÜİK verisinin kanıtlanmış `DATAFLOW`, `TIME_PERIOD` alanlı JSON satır dizisi için `capture --directory ... --tuik-legacy` kullanılabilir.

## Checkpoint / 409 / bilinmeyen commit

```bash
python -m scraper.data_api.cli status
python -m scraper.data_api.cli status --operation-id 'yokatlas/SNAPSHOT_ADI/run'
```

`uncertain` veya `rejected` kaydı **asla körlemesine tekrar gönderilmez**. Celal gerçek DB'de işlemi doğrulayıp PK verirse:

```bash
python -m scraper.data_api.cli reconcile --operation-id 'yokatlas/SNAPSHOT_ADI/run' --verified-by-db --committed-key '{"ingestion_run_id":123}'
```

DB'de kesin olarak **commit olmadığı** doğrulandıysa:

```bash
python -m scraper.data_api.cli reconcile --operation-id 'yokatlas/SNAPSHOT_ADI/run' --verified-by-db --not-committed
```

`--verified-by-db`, sistemin DB'yi otomatik doğruladığı anlamına gelmez; **operatörün manuel doğrulama beyanıdır**. `outputs/data_api/checkpoint.sqlite3` dosyasını ve beraberindeki WAL dosyalarını koru, yedekle. Birden fazla process aynı arşivi aynı anda yazmasın.

## Mevcut API ile mümkün olmayanlar

1. `ingestion_runs` kaydının `completed` / `failed` yapılması (API yalnız INSERT). Döndürülen `local_publication=complete` sadece **yerel aktarımın bittiğini** ifade eder, DB run durumu `running` kalır.
2. Tek transaction ile parent+child rollback; her satır ayrı request.
3. DB'den mevcut RAW anahtarını sorgulama, upsert, tekrar eden kaynak içeriği/409 otomatik çözümü.
4. `bytea` tabanlı kaynak artifact gövdesi aktarımı.
5. SEGE/URAP staging/core yayınlama; bunu ETL üstlenecek.
6. TÜİK native SDMX DSD/codelist/observation akışı, tüm RAW `tuik_*` tabloları.
7. OpenAlex normalize nesne tablolarında tam upsert, ilişki çözümleme, tüm evrenin indirilmesi.
8. Canlı HTTPS API host, gerçek `DB_WRITE_API_KEY`, hedef DB şeması ve izinleri doğrulanmadan canlı entegrasyon garanti edilmez.

### Önemli teknik not

`raw.api_responses` için aynı sayfa/hash üzerinde UNIQUE constraint bulunabilir. **Aynı içeriği yeni snapshot'ta yeniden yazınca 409** beklenebilir. Bu sürüm bunu başarılı saymaz. Elle reconciliation veya API/idempotency geliştirmesi beklenir; veriler sessizce çoğaltılmaz.

## Yerleşim

```text
scraper/data_api/__init__.py
scraper/data_api/client.py
scraper/data_api/ledger.py
scraper/data_api/publish.py
scraper/data_api/collect.py
scraper/data_api/cli.py
scraper/data_api/README.md
tests/scraper/test_raw_data_api.py
```

**Not:** Bu paket, çalışan branch üzerinde test edilmiş bir PR değildir. Herhangi bir mevcut modül veya canlı veritabanı bu çalışma sırasında değiştirilmedi.
