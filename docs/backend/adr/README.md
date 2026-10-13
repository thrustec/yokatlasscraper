# Faz 1 ADR envanteri

Kararlar 13 Ekim 2026 tarihinde tasarım önerisi olarak hazırlanmıştır. Kullanıcının
Faz 1 onayı, DB istisna/migration uygulama onayı anlamına gelmez.

| ADR | Karar | Durum |
|---|---|---|
| [0001](0001-modular-api-and-python-stack.md) | Python/FastAPI modüler API, Psycopg pool, ayrı worker | Uygulama önerisi |
| [0002](0002-identities-and-data-access.md) | Anonim read; M2M scopes; ayrı DB hesapları; kontrollü ETL DB istisnası | Anonim read kullanıcı tarafından seçildi; DB istisnası/grants onay bekliyor |
| [0003](0003-ingestion-identity-and-hashes.md) | Byte hash + sürümlü record canonical hash; request identity/observations/idempotency | Additive metadata uygulaması onay bekliyor |
| [0004](0004-jobs-and-publication-gate.md) | PG job claim/lease ve mutable CORE için fail-closed yayın gate'i | DE adapter kabulü ve metadata onayı bekliyor |

Ana belgeler: [Mimari](../01_ARCHITECTURE.md), [API](../02_API_DESIGN.md),
[roller](../03_SECURITY_AND_ROLES.md), [metadata önerisi](../04_METADATA_CHANGE_PROPOSAL.md).
