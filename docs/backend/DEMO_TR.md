# 14 Ekim — kısa API demosu

## Açılış

Docker Desktop'ı aç. `E:\YÖKAtlas\yokatlas-intelligence` klasöründe:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\run-demo.ps1
```

Swagger: http://127.0.0.1:8000/docs. Her uçta **Try it out → Execute**.
Terminalde `Ctrl+C` API'yi kapatır.

## 2–3 dakikalık gösterim

1. `/health`: API'nin PostgreSQL'e bağlandığını göster.
2. `/api/coverage`: yüklenen örneğin boyutunu göster.
3. `/api/universities`: `q=İSTANBUL` ile üniversite ara.
4. `/api/programs`: `puan_turu=SAY`, `limit=3` ile filtrele. Sonuçtaki bir
   `kilavuz_kodu` değerini `/api/programs/{kilavuz_kodu}` alanında kullan.
5. `/api/net-results`: `yil=2025`, `puan_turu=SAY`, `limit=3` ile netleri göster.

## Hocaya anlatım

“Bu aşamada repodaki veritabanı şemasını Docker üzerinde PostgreSQL'e kurduk.
Veriler E diskinde kalıcı olarak saklanıyor. Mevcut YÖK Atlas toplama ve yükleme
araçlarıyla küçük bir gerçek veri örneğini veritabanına aktardık.

Üzerine basit bir API ekledik. Üniversiteleri arayabiliyor, programları yıl ve
puan türüne göre filtreleyebiliyor, net sonuçlarını JSON olarak alabiliyoruz.
Swagger üzerinden istek gönderip cevabı anlık görebiliyoruz. Sonraki adım,
veri kapsamını genişletmek ve bu API'yi arayüze bağlamak.”

## Gösterimdeki veriler

13 Ekim 2026'da YÖK Atlas'ın repoda tanımlı herkese açık uçlarından alınan örnek:
228 üniversite, 83 şehir kaydı, 611 program grubu, 50 program, 50 ham net kaydı.
Program ve net aramalarında her puan türünün yalnız ilk 10 satırı alındı; tam veri
seti değildir. Yükleyici aynı anahtarlı netleri birleştirebildiği için kesin
veritabanı sayısı `/api/coverage` çıktısıdır.

Kaynağın `yil` alanı programlarda **2026**, bu net örneğinde **2025** geldi.
API bu değerleri değiştirmez; program ve netleri farklı yıllar üzerinden
eşleştirdiğimizi veya alanın anlamını resmî olarak doğruladığımızı söylemeyelim.

## İlk kez başka bilgisayarda kurulum

Python 3.13 ve çalışan yerel veritabanı gerekir. Veritabanı için
[mevcut kurulum notunu](LOCAL_POSTGRES_SETUP_TR.md) kullan.

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\backend\.venv\Scripts\python.exe scraper/yokatlas_api_explorer/yokatlas_full_validator.py --mode collect --out outputs/demo --size 10 --max-pages-per-score 1 --max-requests 13 --delay 1
.\backend\.venv\Scripts\python.exe scripts/database/load_archive.py --root outputs/demo
```

Örnek veriler `outputs/demo` altında yereldir, Git'e eklenmez. Sunum sırasında
API PostgreSQL'deki kopyayı okur; Swagger'ın arayüz dosyaları için internet gerekir.

Kontrol: `.\backend\.venv\Scripts\python.exe -m unittest discover -s tests/backend -v`.
