# API geliştirmeleri — 14 Ekim 2026

Branch: `feat/api-demo-tr-20261014`

Bu çalışma, mevcut PostgreSQL şemasına bağlanan ve hocaya canlı olarak
gösterilebilen küçük bir backend demosu oluşturur. FastAPI ile Python kaynak
kodu yazıldı; Swagger dokümantasyonu bu koddan otomatik üretilir.

## Yapılan geliştirmeler

- Üniversite, program ve net verileri için JSON döndüren okuma endpoint'leri eklendi.
- Üniversite ve program adına göre arama, yıl/puan türü/üniversite filtreleri ve
  `limit`/`offset` ile sayfalama eklendi.
- Üniversite demo kayıtları için ekleme, okuma, güncelleme ve silme akışı eklendi.
- Yazma işlemleri `X-API-Key` ile korundu; okuma endpoint'leri anonim erişime açık.
- Pydantic modelleriyle istek ve cevap alanları tanımlandı; hatalı girdiler kontrol edildi.
- PostgreSQL sorguları Psycopg ile parametreli olarak yazıldı. Her yazma isteği
  bir transaction içinde tamamlanır; hata halinde geri alınır.
- Endpoint yolları Türkçeleştirildi. İlk bağlantı kontrolü `/health`, sonra
  `/durum` olarak adlandırılmıştı; son adı kullanıcının tercihiyle **`/status`** oldu.
- Başlatma scripti, demo yazma kurulumu, testler ve kısa sunum notu eklendi.

## Kaynak kodu ve dosyalar

| Dosya | Görevi |
|---|---|
| [backend/main.py](../../backend/main.py) | Endpoint'ler, veri modelleri, DB bağlantıları, SQL ve anahtar kontrolü |
| [backend/run-demo.ps1](../../backend/run-demo.ps1) | PostgreSQL'i hazırlar, demo yazma kurulumunu ve API'yi başlatır |
| [backend/setup-demo-write.py](../../backend/setup-demo-write.py) | Yerel anahtar/parola üretimi ve sınırlı yazma rolünün kurulumu |
| [backend/demo-write.sql](../../backend/demo-write.sql) | Demo üniversitesi görünümü ve yazma rolünün yetkileri |
| [backend/requirements.txt](../../backend/requirements.txt) | FastAPI, Uvicorn, Psycopg ve python-dotenv bağımlılıkları |
| [backend/requirements-dev.txt](../../backend/requirements-dev.txt) | HTTP test istemcisi ve veri toplama bağımlılıkları |
| [tests/backend/test_demo.py](../../tests/backend/test_demo.py) | 9 API/DB entegrasyon testi |
| [DEMO_TR.md](DEMO_TR.md) | Canlı gösterim sırası ve hocaya anlatım metni |

## Mevcut endpoint'ler

API, yedi okuma ve üç yazma olmak üzere **10 işlem** sunar.

| Metot | Yol | İşlev | Anahtar |
|---|---|---|---|
| GET | `/status` | API ve PostgreSQL bağlantı kontrolü | Gerekmez |
| GET | `/api/veri-kapsami` | Yereldeki kayıt sayıları | Gerekmez |
| GET | `/api/universiteler` | Üniversite listeleme ve adla arama | Gerekmez |
| GET | `/api/universiteler/{universite_id}` | Tek üniversiteyi okuma | Gerekmez |
| POST | `/api/universiteler` | Demo üniversitesi oluşturma | Gerekir |
| PUT | `/api/universiteler/{universite_id}` | Demo üniversitesinin adını güncelleme | Gerekir |
| DELETE | `/api/universiteler/{universite_id}` | Demo üniversitesini silme | Gerekir |
| GET | `/api/programlar` | Program arama ve filtreleme | Gerekmez |
| GET | `/api/programlar/{kilavuz_kodu}` | Tek programı okuma; yıl verilmezse en güncel kayıt | Gerekmez |
| GET | `/api/net-sonuclari` | Net sonuçlarını yıl, puan türü ve program koduyla filtreleme | Gerekmez |

Üniversite listesinde `q`; program listesinde `q`, `yil`, `puan_turu`,
`universite_id`; net listesinde `yil`, `puan_turu`, `kilavuz_kodu` kullanılabilir.
Liste uçlarında `limit` varsayılan 10, en fazla 100; `offset` varsayılan 0'dır.
Puan türleri: `SAY`, `EA`, `SÖZ`, `DİL`, `TYT`.

Swagger: `http://127.0.0.1:8000/docs`. Çalışan sözleşme: `/openapi.json`.
Ana adres `/` kullanıcıyı Swagger'a yönlendirir.

## Veritabanı bağlantısı ve yazma kapsamı

Mevcut veritabanı şeması repodaki `database/migrations` dosyalarından gelir.
HTTP yolları uygulamada tanımlandı; JSON alanları mevcut DB sütun adlarını kullanır.

| API'nin kullandığı görünüm | Dayandığı ana tablo |
|---|---|
| `api.universities` | `core.universities` |
| `api.program_catalog` | `core.program_versions` ve üniversite/şehir/program grubu ilişkileri |
| `api.net_results` | `core.net_results` |
| `api.data_coverage` | Beş ana veri tablosunun kayıt sayıları |
| `api.demo_universities` | `core.universities` içindeki `source_record_id IS NULL` kayıtları |

Okuma bağlantısı mevcut `atlas_api` rolünü ve salt okunur transaction'ları
kullanır. Demo yazma bağlantısı `atlas_demo_writer` rolünü kullanır; bu rolün
CRUD yetkisi yalnız `api.demo_universities` görünümündedir. YÖK Atlas'tan alınan
kaynak kayıtları bu görünümde yer almaz ve demo uçlarıyla değiştirilmez.

Yerel demo kurulumu bir ek görünüm ve bir sınırlı rol oluşturur. SQL tanımı
`backend/demo-write.sql` içindedir; genel migration akışına eklenmemiştir.
Veritabanında 17 tablo ve bu demo görünümü dahil 9 API görünümü bulunur.

`core.net_results` tablosunda TYT/AYT/YDT netleri, OBP, taban puan, yıl ve
program kodu alanları vardır. Mevcut net endpoint'i program kodu, yıl, puan türü,
taban puan, OBP ve dört TYT net alanını döndürür.

Program ve net verileri mevcut toplama/yükleme araçlarıyla DB'ye aktarılır.
`atlas_ingest` rolünün bu tablolarda `INSERT/UPDATE` yetkisi vardır.
Program/net CRUD endpoint'leri ve botun API'ye veri göndereceği ingestion
endpoint'i bu demoda henüz uygulanmadı.

## Kurulum ve çalıştırma

Python 3.13, Docker Desktop ve mevcut yerel PostgreSQL kurulumu gerekir.
Veritabanı kurulumu için [LOCAL_POSTGRES_SETUP_TR.md](LOCAL_POSTGRES_SETUP_TR.md),
gerçek veri örneğinin toplanması/yüklenmesi için [DEMO_TR.md](DEMO_TR.md) kullanılır.

Repo kökünde ilk Python kurulumu:

```powershell
python -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
```

API'yi başlatma:

```powershell
powershell -ExecutionPolicy Bypass -File .\backend\run-demo.ps1
```

API `127.0.0.1:8000`, PostgreSQL `127.0.0.1:5433` üzerinde çalışır.
`run-demo.ps1 -Port 8001` ile API portu değiştirilebilir.
PostgreSQL'in E diskinde kalıcı saklanması `compose.local.yaml` ile sağlanır;
başka bilgisayarda yerel veri dizini kurulum notuna göre ayarlanmalıdır.

`.env` DB bağlantı parolalarını, otomatik oluşturulan `.env.demo` ise
`DEMO_API_KEY` ve demo yazma rolünün parolasını tutar. Bu dosyalar, `.venv`,
loglar ve toplanan veri dosyaları Git'e eklenmez. Yazma için `.env.demo` içindeki
`DEMO_API_KEY` değeri Swagger'ın **Authorize** alanına girilir.

## Örnek istekler

```http
GET http://127.0.0.1:8000/status
GET http://127.0.0.1:8000/api/universiteler?q=ANKARA&limit=5
GET http://127.0.0.1:8000/api/programlar?puan_turu=SAY&yil=2026&limit=3
GET http://127.0.0.1:8000/api/net-sonuclari?puan_turu=SAY&yil=2025&limit=3
```

Yazma isteklerinde `<DEMO_API_KEY>` yerel anahtar ile değiştirilir:

```http
POST http://127.0.0.1:8000/api/universiteler
Content-Type: application/json
X-API-Key: <DEMO_API_KEY>

{"universite_id": 900000001, "universite_adi": "DEMO ÜNİVERSİTESİ"}
```

Eklenen kayıt `GET /api/universiteler/900000001` ile okunur. Ardından:

```http
PUT http://127.0.0.1:8000/api/universiteler/900000001
Content-Type: application/json
X-API-Key: <DEMO_API_KEY>

{"universite_adi": "DEMO ÜNİVERSİTESİ GÜNCELLENDİ"}
```

```http
DELETE http://127.0.0.1:8000/api/universiteler/900000001
X-API-Key: <DEMO_API_KEY>
```

Oluşturma `201`, silme `204`; hatalı anahtar `401`, bulunamayan kayıt `404`,
tekrarlanan ID veya korunan/ilişkili kayıt `409`, hatalı girdi `422`, DB erişim
hatası `503` döner. Kaynak kaydı koruması güncelleme/silme uçları için geçerlidir.

## Testler ve doğrulanan sonuçlar

```powershell
.\backend\.venv\Scripts\python.exe -m unittest discover -s tests/backend -v
```

Testlerden önce yerel DB, örnek veri ve demo yazma kurulumu hazır olmalıdır.
9 test; bağlantıyı, kayıt sayılarını, filtrelemeyi, sayfalamayı, program detayını,
üniversite CRUD işlemlerini, girdi/anahtar kontrollerini, kaynak kayıtlarının
korunmasını ve yazma rolünün sınırlarını doğrular. Test kayıtları temizlenir.
4 mevcut DB paket testi de kontrol edildi; toplam 13 test başarılıdır.
Canlı HTTP üzerinden ekle → oku → güncelle → sil → `404` akışı da doğrulandı.

Yerel gerçek veri örneği 13 Ekim'de toplandı: 228 üniversite, 83 şehir kaydı,
611 program grubu, 50 program ve 50 net kaydı. Program ve net aramalarında her
puan türünün yalnız ilk 10 satırı alındı. Kaynak programlarda yıl **2026**, net
örneğinde **2025** döndürdü; API bu değerleri değiştirmez veya farklı yılları
eşleştirmez. Güncel kayıt sayıları `/api/veri-kapsami` üzerinden görülür.

## Demo ve sonraki geliştirmeler

Bu sürüm çalışan ilk backend demosudur. Gösterim akışı:
`/status` → program/net sorgusu → demo üniversitesi ekle/oku/güncelle/sil.
Botun API üzerinden otomatik veri göndermesi ve veri kapsamının genişletilmesi
sonraki geliştirmelerdir. Önceki mimari, ADR ve `openapi.yaml` dosyaları ilerideki
geliştirmeler için taslaktır; çalışan demonun sözleşmesi `/openapi.json` çıktısıdır.

Bu branch mevcut API commitlerini, onları destekleyen yerel DB kurulumunu ve
önceki keşif/tasarım belgelerini içerir. API kaynak kodu ve bu özet birlikte
branch'e alınmıştır; `main` üzerinde bir commit veya push yapılmaz.
