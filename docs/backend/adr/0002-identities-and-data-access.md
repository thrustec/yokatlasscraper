# ADR-0002 — Kimlikler ve denetlenebilir veri erişimi

**Durum:** Tasarım önerisi; ETL doğrudan DB istisnası ve grants için açık owner
onayı gerekir. **Tarih:** 13 Ekim 2026.

Kullanıcı anonim katalog/net okumasını seçti. Internal/ops işlemlerinde kimlik,
scope, source ve run/job sahipliği doğrulanacak. API-first control plane temel
tercihtir. Scraper kendisine PostgreSQL credential'ı verilmeden response/manifest
teslim eder.

İlk M2M yöntem: ayrı principal/key ID, random secret, server-defined scopes ve
izinli sources. Faz 2 env provider'ı, Faz 3 digest-only DB credential provider'ı.
Operator insan kimliği, konfigüre OIDC provider'ın doğrulanmış JWT'sinden gelir;
provider eksikliği insecure admin fallback ile giderilmez. Lokal CLI automation
key'i ayrı service actor olarak audit edilir. [Rol/scope matrisi](../03_SECURITY_AND_ROLES.md).

**Önerilen doğrudan DB istisnası:** Data Engineer'ın güvenilen worker'ı RAW'ı
okur, kendi STAGING/CORE/QUALITY batch transaction'larını `atlas_etl` ile yazar.
Her kayıt için HTTP çağrısı zorunlu tutulmaz. API job input, lease, start,
completion, publication ve audit'i yönetir. Pipeline executable/SQL server-side
registry'den seçilir; kullanıcı komutu çalıştırılmaz.

İstisnanın koşulları:

1. `atlas_etl` superuser/table owner/DDL hesabı değildir; explicit tablo grants'i
   ve RAW read-only sınırı vardır. Parolası yalnız onaylı runner'dadır.
2. Runner [ADR-0004](0004-jobs-and-publication-gate.md) lock/start/lease/recovery
   protokolünü sağlar ve kabul testini geçer. Eski loader bu hesabı otomatik almaz.
3. DB bağlantısı private network/TLS politikası, UTC/application_name/timeouts ve
   kısa batch transaction'larıyla konfigüre edilir.
4. Scraper'ın geniş mevcut `atlas_ingest` hesabı ve default grants daraltılır;
   read, RAW write ve control API pool'ları ayrılır.
5. Backend ETL mapping/kalite/KPI SQL'ini geliştirmez. Worker adapter'ı ve read
   model anlamları Data Engineer tarafından doğrulanır.

Least privilege DB rol sınırını zorlar; paylaşılan trusted backend login'inin
HTTP principal/source sahipliği API policy'sinde uygulanır. RLS ile müşteri başına
DB erişimi bu ilk modelin garantisi değildir. Advisory gate'e uymayan yetkili
DB yazarına karşı tam izolasyon da bu modelin garantisi değildir; credential ve
runner kontrolü bu nedenle istisna onayının koşuludur.

Onay olmadan Faz 2 yalnız read bağlantısı/health/auth abstraction kurar;
CORE writer, otomatik importer, yeni ETL credential dağıtımı yapılmaz.
