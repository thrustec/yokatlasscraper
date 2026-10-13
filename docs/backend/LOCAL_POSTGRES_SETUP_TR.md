# Yerel PostgreSQL kurulumu — Windows / E: sürücüsü

Kurulum tarihi: 13 Ekim 2026. Başlangıç referansı: `origin/main`,
`0d09f20804f0efb1ac1d64c63f3c9f9ef96dc1b7`.

Bu aşama, repodaki mevcut veritabanı sözleşmesini boş bir yerel PostgreSQL
veritabanında kurar. Kaynak verilerin aktarılması ve backend geliştirmesi ayrı
aşamalardır. Mevcut migration dosyalarının şema ve yetki tanımları korunmuştur.

## Kurulan ortam

| Ayar | Değer |
|---|---|
| Checkout | `E:\YÖKAtlas\yokatlas-intelligence` |
| Feature branch | `feat/backend-local-postgres-20261013` |
| Compose projesi | `yokatlas-local-backend` |
| Servis | `postgres` |
| Container | `yokatlas-local-backend-postgres-1` |
| Image | `postgres:17` |
| Doğrulanan PostgreSQL | `17.11` |
| Veritabanı | `yokatlas_intelligence` |
| Host bağlantısı | `127.0.0.1:5433` |
| Container portu | `5432` |
| Kalıcı veri klasörü | `E:\YÖKAtlas\postgres-data` |
| Container veri klasörü | `/var/lib/postgresql/data` |

`compose.local.yaml`, temel Compose dosyasındaki veri volume'unu aynı container
hedefinde bir bind mount ile değiştirir. Mount'un E: üzerindeki klasöre işaret
ettiği `docker inspect` ile doğrulanmıştır. Veri klasörü checkout dışındadır.
`.gitattributes`, Linux bootstrap scriptlerinin Windows'ta LF satır sonuyla
checkout edilmesini sağlar.

PostgreSQL veri dosyaları E: üzerindedir. Docker Desktop'ın image ve diğer
volume'ları tutan WSL sanal diski halen kendi C: konumundadır. Bind mount, Docker
Desktop'ın genel depolama konumunu değiştirmez.

## Yerel yapılandırma

Önkoşullar: Docker Desktop'ın Linux/WSL2 motoru çalışmalı ve host portu boş olmalı.
Yeni checkout ve boş veri klasörü için:

```powershell
Set-Location 'E:\YÖKAtlas\yokatlas-intelligence'
.\scripts\database\setup.ps1
New-Item -ItemType Directory -Path 'E:\YÖKAtlas\postgres-data'
```

`setup.ps1` dört rastgele parola üretir. `.env` Git tarafından ignore edilir ve
mevcut bir `.env` dosyasındaki parolalar script tarafından değiştirilmez.
Windows'ta `.env` dosyasına aşağıdaki gizli olmayan yerel ayarlar eklenmiştir:

```dotenv
COMPOSE_FILE=compose.yaml;compose.local.yaml
COMPOSE_PROJECT_NAME=yokatlas-local-backend
POSTGRES_DATA_DIR=E:/YÖKAtlas/postgres-data
```

Windows'ta `COMPOSE_FILE` ayıracı `;` işaretidir. Bu değişkenler sayesinde reponun
mevcut PowerShell kontrol scriptleri de aynı yerel Compose projesini kullanır.
Linux'ta çoklu Compose dosyaları `-f` seçenekleriyle seçilebilir:

```text
docker compose -p yokatlas-local-backend -f compose.yaml -f compose.local.yaml up -d
```

Yerel başlangıç ve kontrol:

```powershell
docker compose config --quiet
docker compose --progress quiet up -d --wait --wait-timeout 180 postgres
.\scripts\database\verify.ps1
```

## Uygulanan şema

Yeni veri klasöründe `database/init/10-bootstrap.sh`, tek transaction içinde
`000_roles.sql` ile `004_archive_idempotency.sql` arasındaki beş dosyayı ve
`database/checks/smoke.sql` kontrolünü yürütür. İlk kurulum sonrası envanter:

| Şema | Fiziksel tablo | View |
|---|---:|---:|
| `raw` | 3 | 0 |
| `staging` | 5 | 0 |
| `core` | 7 | 0 |
| `quality` | 2 | 0 |
| `analytics` | 0 | 0 |
| `api` | 0 | 8 |
| Toplam | 17 | 8 |

PostgreSQL'in standart `public` şeması ayrıca vardır. STAGING tablolarında
124 tipli kaynak alanı doğrulanmıştır. Kaynak tablolarındaki kayıt sayıları 0'dır.
Dokümanlarda belirtilen başka ortama ait veri snapshot'ı bu kurulumla taşınmaz.

Roller: `atlas_owner`, `atlas_ingest`, `atlas_api`, `atlas_analytics`.
`atlas_owner` mevcut Docker bootstrap tanımı nedeniyle superuser'dır; uygulama
bağlantılarında kullanılmamalıdır. Diğer üç rol superuser değildir.

**Mevcut yetki farkı:** `003_privileges.sql`, `atlas_ingest` rolüne RAW yanında
STAGING/CORE/QUALITY yazma yetkileri de verir. Bu davranış yerel DB'de doğrulandı.
Backend brief'indeki scraper ve ETL servis hesaplarını ayırma gereksinimi,
sonraki güvenlik tasarımı ve onaylı migration aşamasında ele alınmalıdır.

## Doğrulama sonuçları

- Compose yapılandırması geçerli; servis `healthy`.
- Host üzerindeki `127.0.0.1:5433` portuna TCP bağlantısı başarılı.
- Reponun smoke kontrolü geçti: şemalar, 124 alan, 8 view ve mevcut grants.
- `python -m unittest discover -s tests/database -v`: 4 test geçti.
- Dört rolün `.env` parolalarıyla TCP üzerinden kimlik doğrulaması başarılı.
- `atlas_api`, `api.data_coverage` view'ını okuyabiliyor.
- `atlas_api` ile RAW INSERT ve doğrudan CORE SELECT, DB tarafından reddediliyor.
- `atlas_ingest` ile RAW transaction açılıp yazıldı; ROLLBACK sonrası kayıt sayısı 0.
- `001`–`004` migration'ları mevcut scriptle tekrar uygulanabildi.
- Container `--force-recreate` ile yeniden oluşturuldu; yeni başlangıçta
  initialization atlandı ve aynı şema/rollerle smoke kontrolü tekrar geçti.

Kontrol komutları:

```powershell
docker compose ps
.\scripts\database\verify.ps1
python -m unittest discover -s tests/database -v
docker compose logs --no-color --tail 30 postgres
```

`000_roles.sql`, ilk kurulum dosyasıdır; mevcut rolleri olan DB'de tekrar
uygulanmamalıdır. Uygulama başlangıcında migration çalıştırma eklenmemiştir.

## Kullanım ve yedek

API rolüyle interaktif bağlantı; parola `.env` içindeki `ATLAS_API_PASSWORD`:

```powershell
docker compose exec postgres psql -h 127.0.0.1 -U atlas_api -W -d yokatlas_intelligence
```

Servisi durdurma ve başlatma:

```powershell
docker compose stop postgres
docker compose --progress quiet up -d --wait postgres
```

E: üzerindeki veri klasörü container yeniden oluşturulduğunda korunur. Bu klasörü
silmek veritabanını siler. Parolaları `.env` içinde değiştirmek mevcut DB rollerinin
parolasını otomatik olarak değiştirmez.

PowerShell'in binary yönlendirme davranışından bağımsız yedek örneği:

```powershell
New-Item -ItemType Directory -Path 'E:\YÖKAtlas\postgres-backups' -Force
docker compose exec -T postgres pg_dump -U atlas_owner -d yokatlas_intelligence -Fc -f /tmp/yokatlas.dump
docker cp yokatlas-local-backend-postgres-1:/tmp/yokatlas.dump E:\YÖKAtlas\postgres-backups\yokatlas.dump
```

Komutlar başarı kontrolüyle çalıştırılmalı; önceki yedeği ezmemek için tarihli dosya
adı seçilmelidir. Restore provası henüz yapılmamıştır; ayrı bir test DB'sinde
sonraki operasyon aşamasına aittir.

## Docker başlangıç sorunu ve KAI-Flow temizliği

Başlangıçta C: üzerinde yaklaşık 123 MiB boş alan vardı. Docker Desktop 4.81.0,
`dockerInference` ve ardından Secrets Engine socket dosyalarını kaldıramadığı
için açılmıyordu. Backend durmuşken aşağıdaki geçici iletişim klasörleri tarihli
kardeş klasörlere yeniden adlandırılıp korundu; yeni boş klasörlerle başlatma
başarılı oldu:

- `%LOCALAPPDATA%\Docker\run`
- `%LOCALAPPDATA%\docker-secrets-engine`

Bu işlem veritabanı volume'larını veya Docker sanal diskini değiştirmedi.
Benzer başlangıç hatası Docker'ın [issue #460](https://github.com/docker/desktop-feedback/issues/460)
kaydında raporlanmıştır. İkinci bir Docker Desktop başlatmasında aynı platform
hatasının tekrarlayıp tekrarlamayacağı henüz doğrulanmamıştır.

Kullanıcının KAI-Flow Docker kurulumlarını kaldırma izniyle:

- KAI-Flow'a ait 5 container kaldırıldı.
- KAI-Flow'a ait 3 named volume durdurulmuş DB'lerden yedeklendi ve kaldırıldı.
- Bu kurulumların 5 image referansı kaldırıldı.
- Builder geçmişindeki KAI-Flow, modelscan-demo ve ilgili client build'leri
  kontrol edildikten sonra 17,53 GB build cache temizlendi.
- KAI-Flow'un host bind mount'larındaki kaynak dosyaları korunmuştur.
- Diğer projelerin volume'ları korunmuştur; genel volume temizliği yapılmamıştır.

Yedekler: `E:\YÖKAtlas\.local-backups\kai-docker-20261013`.
Üç `.tar.gz` arşivi okunabilirlik kontrolünden geçti; `SHA256SUMS.txt` ve
`build-history.json` aynı klasördedir.

Build cache temizliği Docker'ın içindeki alanı geri kazandırdı. Windows'taki
`docker_data.vhdx` dosyası yaklaşık 22,9 GiB boyutunu korudu; C: üzerindeki
ölçülen boş alan yaklaşık 3,54 GiB'dir. VHDX küçültme veya Docker Desktop'ın genel
depolamasını E: üzerine taşıma bu aşamada yapılmamıştır.

## Sonraki aşama

Backend brief'i kapsamındaki mevcut durum raporu, mimari/API/RBAC tasarımı,
backend uygulaması ve PR teslimi için kullanıcı onayı beklenmektedir. Bu yerel
kurulum HTTP API veya ETL worker oluşturmaz.
