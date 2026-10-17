# ÜniRota admin paneli

Veri toplayan botları tek yerden izlemek ve yönetmek için ekip içi panel. Sunucuda çalışır, tarayıcıdan açılır.

## Neler yapabiliyor?

- **Genel bakış:** her bot için bir kart. Kartta botun durumu (çalışıyor, sırada, hazır, hata verdi, kapalı), son çalışması, kaç kayıt yazdığı, zamanlaması ve son 12 çalışmanın küçük grafiği görünür. Sayfada sunucunun diski, belleği, işlemcisi ve veritabanı boyutu da var.
- **Her bot için ayrı sayfa:**
  - Şimdi çalıştır, Durdur, Hatalıları yeniden dene, Aç/Kapat düğmeleri
  - Canlı ilerleme ("120 / 285 sayfa")
  - Çalışma geçmişi. Bir çalışmaya tıklanınca istenen, başarılı ve başarısız sayfa sayısı, yazılan kayıt, uyarı ve hata sayısı görünür (şartname §21).
  - Canlı loglar: çalışmaya, seviyeye (uyarı/hata) ve kelimeye göre filtrelenebilir
  - Başarısız istekler listesi
  - Ayarlar: komut, zamanlama, zaman aşımı, botun kendi ayarları
  - O botla ilgili işlem kaydı
- **Yeni bot ekle:** panelden form ile eklenir. Panelin koduna dokunmak gerekmez.
- **Veri kalitesi:** `quality.data_quality_checks` tablosundaki kontrol sonuçlarını ve `quality.quarantined_records` tablosundaki karantina kayıtlarını gösterir. Karantinadaki kayıt "çözüldü" diye işaretlenip not düşülebilir.
- **Veri kapsamı:** hangi tabloda kaç satır olduğunu ve her kaynağın en son ne zaman yüklendiğini gösterir.
- **E-posta bildirimleri:** şu durumlarda ekibe e-posta gider:
  - bot hata verince
  - bot takılınca
  - planlı bot çalışmayınca
  - beklenenden az kayıt gelince
  - disk dolunca

  Her kural açılıp kapatılabilir ve sınırları değiştirilebilir. Aynı sorun için tekrar tekrar e-posta gitmez.
- **Ekip ve işlem kaydı:** 4 kişinin hepsi bütün botları yönetebilir. Kimin hangi botu başlattığı, durdurduğu ya da ayarını değiştirdiği kayıtlıdır.

## Nasıl çalışıyor?

```
Tarayıcı ──► web (panel + API) ──► PostgreSQL  ◄── runner (çalıştırıcı) ──► botlar
                "başlat" deyince          ops.runs           kuyruğu okur,
                kuyruğa yazar                                 botu başlatır, logları yazar
```

- **web:** panelin kendisi (FastAPI). Botları doğrudan çalıştırmaz; veritabanına "bu bot çalışsın" diye bir istek yazar.
- **runner:** sunucuda sürekli açık duran program. Kuyruğa düşen istekleri ve zamanı gelen botları başlatır, botun çıktısını satır satır log olarak kaydeder, durdurma isteklerini ve zaman aşımlarını uygular, e-posta kurallarını kontrol eder. Panel kapansa da botlar çalışmaya devam eder.
- **ops şeması:** panelin tabloları (`ops.bots`, `ops.runs`, `ops.run_logs`, `ops.failed_requests`, `ops.users`, `ops.audit_log`, `ops.alert_rules`, `ops.alerts_sent`). Mevcut `raw / staging / core / quality / api` şemalarına dokunmaz. Panel ilk açıldığında bu şemayı kendisi kurar (`adminpanel/sql/001_ops_schema.sql`).
- **botkit:** botların panelle konuşması için küçük yardımcı (aşağıda).

## Klasörler

| Klasör / dosya | Ne var |
|---|---|
| `adminpanel/web.py` | API ve giriş |
| `adminpanel/runner.py` | Çalıştırıcı |
| `adminpanel/alerts.py`, `mailer.py` | E-posta kuralları ve gönderim |
| `adminpanel/static/` | Panelin arayüzü (derleme adımı yok) |
| `adminpanel/sql/` | Veritabanı ekleri |
| `botkit/` | Botların kullanacağı yardımcı |
| `bots/ornek_bot.py` | Örnek bot ve şablon |
| `compose.admin.yaml`, `Dockerfile` | Sunucuya kurulum |
| `.env.example` | Ayar şablonu |

## Sunucuya kurulum

Bu klasör repoya `admin-panel/` adıyla konur. Komutlar sunucuda, repo kökünde çalıştırılır.

Panel repodan ayrı bir klasöre de kurulabilir (ör. `/opt/yokatlas-admin/admin-panel`). Bu durumda botların kodunun bulunduğu repo klasörünü `.env` dosyasındaki `ADMIN_REPO_HOST_DIR` satırına yazın; o zaman komutlarda `admin-panel/` yerine bulunduğunuz klasörü kullanın.

1. **Ayar dosyası:**
   ```bash
   cp admin-panel/.env.example admin-panel/.env
   nano admin-panel/.env
   ```
   - `ADMIN_DATABASE_URL` satırındaki parolayı, sunucudaki PostgreSQL parolasıyla değiştirin.
   - E-posta ayarlarını da buraya girin (aşağıdaki "E-posta ayarı" bölümü).
   - `.env` dosyası repoya **girmez**.

2. **Panel için ayrı bir veritabanı kullanıcısı açın** (önerilir; mevcut kullanıcılara dokunmaz). Sunucuda, admin-panel klasöründe:
   ```bash
   PANEL_PW=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))")
   docker exec -i yokatlas-intelligence-postgres-1 sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d yokatlas_intelligence' <<EOF
   CREATE ROLE atlas_admin_panel LOGIN PASSWORD '$PANEL_PW';
   GRANT CONNECT, CREATE ON DATABASE yokatlas_intelligence TO atlas_admin_panel;
   GRANT USAGE ON SCHEMA raw, staging, core, quality, api TO atlas_admin_panel;
   GRANT SELECT ON ALL TABLES IN SCHEMA raw, staging, core, quality, api TO atlas_admin_panel;
   GRANT INSERT, UPDATE ON raw.ingestion_runs, quality.data_quality_checks, quality.quarantined_records TO atlas_admin_panel;
   GRANT REFERENCES ON raw.ingestion_runs TO atlas_admin_panel;
   GRANT USAGE ON ALL SEQUENCES IN SCHEMA raw, quality TO atlas_admin_panel;
   ALTER DEFAULT PRIVILEGES FOR ROLE atlas_owner IN SCHEMA raw, staging, core, quality, api GRANT SELECT ON TABLES TO atlas_admin_panel;
   EOF
   sed -i "s#^ADMIN_DATABASE_URL=.*#ADMIN_DATABASE_URL=postgresql://db_user:REPLACE_ME@postgres:5432/yokatlas_intelligence#" .env
   unset PANEL_PW
   ```

3. **Veritabanının Docker ağını kontrol edin:**
   ```bash
   docker network ls | grep yokatlas
   docker inspect yokatlas-intelligence-postgres-1 --format '{{json .Config.Labels}}' | tr ',' '\n' | grep service
   ```
   - İlk komut ağın adını gösterir; ağ `yokatlas-intelligence_default` değilse adını `.env` dosyasındaki `ADMIN_DB_NETWORK` satırına yazın.
   - İkinci komut PostgreSQL servisinin adını gösterir. Servisin adı `postgres` değilse `ADMIN_DATABASE_URL` içindeki `@postgres:` kısmını o adla değiştirin.

4. **Başlatın:**
   ```bash
   docker compose -f admin-panel/compose.admin.yaml up -d --build
   docker compose -f admin-panel/compose.admin.yaml ps
   ```
   İki servis görünmeli: `web` ve `runner`.

5. **Panele girin.** Panel güvenlik için yalnızca sunucunun içinden açılır. Kendi bilgisayarınızdan SSH tüneliyle girersiniz (DBeaver'daki gibi):
   ```powershell
   ssh -N -L 8090:localhost:8090 KULLANICI@SUNUCU_ADRESI
   ```
   Tünel açıkken tarayıcıda **http://localhost:8090** adresini açın. İlk açılışta "ilk yönetici hesabını oluştur" ekranı gelir.

6. **Ekibi ekleyin:**
   - Panelde **Ekip** sayfasından diğer 3 kişiyi ekleyin, e-posta adreslerini girin.
   - Parolayı kişiye güvenli bir yoldan iletin; kişi ilk girişten sonra kendi parolasını Ekip sayfasından değiştirebilir.

7. **Denemek için:**
   ```bash
   docker compose -f admin-panel/compose.admin.yaml exec web python -m adminpanel.cli add-example-bot
   ```
   Bu komut panele "Örnek bot" ekler. Bot gerçek bir siteye gitmez, sadece sayfa indiriyormuş gibi yapar. Panelden başlatıp durdurmayı, logları ve yeniden denemeyi bununla deneyebilirsiniz. İşiniz bitince Ayarlar sekmesinden silebilirsiniz.

Güncelleme (kod değişince): sunucuda `admin-panel` klasöründe `sudo bash guncelle.sh`. Betik main'deki son kodu çeker (`git pull`) ve paneli yeniden kurar; çalışan bot varsa önce sorar.

## Yeni bot ekleme

1. Botun kodu repoda olmalı (ör. `scraper/yokatlas_netler.py`). Sunucuda repo güncel olsun (`git pull`).
2. Bot ek kütüphane kullanıyorsa `admin-panel/requirements-bots.txt` dosyasına ekleyin ve imajı yeniden kurun (`up -d --build`).
3. Panelde **Yeni bot ekle** formunu doldurun:
   - **Kısa ad:** küçük harf ve tire, ör. `yokatlas-netler`.
   - **Komut:** ör. `python -m scraper.yokatlas_netler` ya da `python scraper/yokatlas_netler.py`. Komut repo kökünden çalışır.
   - **Zamanlama:** ör. "Her gece 03:00" ya da özel bir cron ifadesi (Türkiye saati).
   - **Beklenen en az kayıt:** bundan az kayıt gelirse e-posta uyarısı gider (site yapısı değişmiş olabilir).
   - **Bot ayarları:** botun kendi ayarları, ör. `bekleme_saniye = 1.5`.

### Botun içinde botkit kullanımı

`botkit` kullanmayan bot da çalışır: çıktısı log olarak görünür, çıkış kodu 0 ise başarılı sayılır. İlerleme, kayıt sayısı, başarısız istekler, yeniden deneme ve düzgün durdurma için botkit kullanın:

```python
from botkit import Bot

with Bot.from_env() as bot:
    bekle = bot.settings.get("bekleme_saniye", 1.5)      # panelden değiştirilebilir

    # "Hatalıları yeniden dene" ile başlatıldıysa sadece önceki başarısız istekler gelir
    hedefler = [(r["request_key"], r["failed_id"]) for r in bot.retry_requests] \
               or [(f"sayfa:{i}", None) for i in range(1, 286)]

    for i, (anahtar, failed_id) in enumerate(hedefler, 1):
        if bot.should_stop():            # panelden "Durdur" basıldı
            break
        bot.progress(i, len(hedefler), "TYT sayfaları")
        try:
            veri = indir(anahtar)
            bot.request_ok(failed_id=failed_id)
            bot.records(kaydet(veri))    # kaç satır yazıldı
        except Exception as e:
            bot.request_failed(anahtar, url="...", http_status=getattr(e, "status", None),
                               error=str(e), failed_id=failed_id)
        bot.sleep(bekle)                 # durdurma gelirse hemen uyanır

    bot.check("Program sayısı geçen yıla yakın mı?", toplam > 20000, {"toplam": toplam})
```

- `bot.log / warning / error` ya da düz `print` loglara düşer. Satır `WARNING:` ya da `ERROR:` ile başlarsa o seviyede görünür.
- Her çalışma için `raw.ingestion_runs` tablosuna da bir satır açılır (`source_system` = botun kısa adı). Bot ham veriyi `raw.api_responses` tablosuna yazarken `bot.ingestion_run_id` değerini kullanabilir. `bot.check` sonuçları `quality.data_quality_checks` tablosuna, `bot.quarantine` sonuçları `quality.quarantined_records` tablosuna yazılır.
- Bot panel olmadan da çalışır (ör. `python scraper/x.py`). O zaman botkit sadece ekrana yazar, veritabanına bir şey yazmaz.

## E-posta ayarı (Gmail ile)

1. Ekip için bir Gmail hesabı seçin ve hesapta 2 adımlı doğrulamayı açın.
2. https://myaccount.google.com/apppasswords adresinden bir "uygulama şifresi" oluşturun.
3. `.env` dosyasında şu satırları doldurun:
   - `ADMIN_SMTP_USER`: Gmail adresi
   - `ADMIN_SMTP_PASSWORD`: uygulama şifresi
   - `ADMIN_SMTP_FROM`: gönderen olarak görünecek ad ve adres
4. `docker compose -f admin-panel/compose.admin.yaml up -d` ile yeniden başlatın.
5. Panelde **Bildirimler → Deneme e-postası gönder** düğmesine basın.

## Güvenlik

- Panel sadece `127.0.0.1:8090` adresinde dinler, yani internetten açılmaz; SSH tüneliyle girilir. İleride internete açılacaksa önüne HTTPS'li bir ters vekil (ör. Caddy) koyun ve `.env` dosyasında `ADMIN_COOKIE_SECURE=1` yapın.
- Bot komutları sunucuda çalıştığı için panele giren herkes sunucuda komut çalıştırabilir. Bu yüzden herkes güçlü bir parola kullansın ve hesaplar paylaşılmasın.
- Parolalar scrypt ile özetlenmiş saklanır. Oturum çerezi HttpOnly ve SameSite=Strict, değiştiren her istek ayrıca özel bir başlık ister.
- Veritabanı parolası `.env` içindedir; bu dosyayı kimseyle paylaşmayın, repoya koymayın.

## Kendi bilgisayarında denemek

Python 3.11+ ve erişilebilir bir PostgreSQL (veritabanı yedeği yüklenmiş olabilir) gerekir:

```bash
cd admin-panel
pip install -r requirements.txt
export ADMIN_DATABASE_URL=postgresql://db_user:REPLACE_ME@localhost:5432/yokatlas_intelligence
uvicorn adminpanel.web:app --port 8090        # bir terminalde
python -m adminpanel.runner                    # ikinci terminalde
python -m adminpanel.cli add-example-bot
```

Testler: `python -m pytest tests`

## Sorun giderme

| Belirti | Ne yapmalı |
|---|---|
| Panelde "Çalıştırıcı kapalı" | `docker compose -f admin-panel/compose.admin.yaml logs runner` |
| Bot hemen "hata" ile bitiyor | Botun Loglar sekmesine bakın. Komut ya da klasör yanlışsa ilk satırda yazar. |
| `network ... not found` | 2. adımdaki ağ adını `.env` dosyasına yazın |
| E-posta "Gönderilemedi" | Bildirimler sayfasında hatanın kendisi yazar; `.env` dosyasındaki SMTP satırlarını kontrol edin |
| Parolayı unuttum | `docker compose -f admin-panel/compose.admin.yaml exec web python -m adminpanel.cli set-password KULLANICI` |
