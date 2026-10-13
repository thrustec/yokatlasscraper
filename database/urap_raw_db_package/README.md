# URAP 2025–2026 RAW migration ve importer

## Kapsam ve karar
URAP 2025–2026 genel sıralaması, PDF Tablo 10, 198 üniversite, her biri 8 ölçüt puanı. Yalnızca `raw` şemasında 6 tablo yaratır. Mevcut `raw.ingestion_runs`, `raw.api_responses`, `raw.source_records` tablolarına dokunmaz. `staging/core/analytics/api` şemalarına dokunmaz. Kullanıcının bu konuşmadaki URAP tablo oluşturma talebi kaynak onayı olarak değerlendirilmiştir. Şema canlı DB'de görülmediğinden **DB'ye fiilen uygulanmış değildir**.

## Kaynak ve sınırlamalar
- PDF SHA-256: `8d7847e3d62c995b1e9e6156cddb4ee61f67eedfe6c17832a6b19477e5dc5095`
- PDF orijinali diskte korunmalıdır; importer PDF'yi DB içine koymaz, `file://` arşiv URI'sini kaydeder. Sunucuda kalıcı yedek/obje deposuna taşınmadan üretimde bu URI'ye güvenilmemeli.
- 15 ham gösterge 8 yayımlanmış ölçüt puanıyla eşit değildir. `metric_scores` yayımlanmış puanları tutar.
- YÖK üniversite ID eşleştirmesi yoktur; üniversite adları kaynak metnidir.
- `score_delta` PDF'de yayımlanmış ayrı ölçüt değil; extraction QA alanıdır. `extraction_score_delta` kolon adı bunu açıkça ayırt eder; asıl doğrulama importer'da yeniden hesaplanır. Sonraki migration'da bu alan çıkarılabilir.
- Başlangıç tarihi `2025-10-19`, rapor kapağındaki yayın tarihidir; `2025-2026` sıralama edisyonudur.

## Windows PowerShell örneği
Önce projenizin migration yönergesine göre canlı veritabanı şemasını kontrol edin ve `001_urap_raw.sql` dosyasını gözden geçirin. Projede kullanılan migration aracının dosya sırası ve yetkilerine uyun. PostgreSQL `psql` kuruluysa:

```powershell
psql "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f .\001_urap_raw.sql
python -m pip install "psycopg[binary]"
python .\import_urap.py --csv .\urap_2025_2026_extracted.csv --pdf .\urap_2025_2026.pdf
python .\import_urap.py --csv .\urap_2025_2026_extracted.csv --pdf .\urap_2025_2026.pdf --database-url "$env:DATABASE_URL" --write
psql "$env:DATABASE_URL" -v ON_ERROR_STOP=1 -f .\002_verify.sql
```

İlk `import_urap.py` çağrısı yalnızca doğrulama yapar. İkinci çağrı `--write` ile DB'ye yazar. Aynı veriyi tekrar çalıştırmak çoğaltmaz; mevcut veriler farklıysa işlem durur. Migration mevcut isimli tablolar varsa hata verir; bu kasıtlıdır, tabloyu sessizce farklı tanımla değiştirmeyin.

## Kabul kontrolü
- 198 adet `GENERAL` sıralama kaydı, sıra 1–198, benzersiz rank.
- 1584 adet ölçüt puanı (198 × 8).
- Toplam puan farkı en fazla 0.06.
- Orijinal PDF hash doğrulaması.
- İkinci importer çalıştırması `already_loaded_and_identical` sonucu.
- PDF dosyası ve DB snapshot yedeklenmeli. Uygulamadan önce erişim rolleri, yetkiler, üretim yedeği ve proje migration sırası ayrıca gözden geçirilmeli.
