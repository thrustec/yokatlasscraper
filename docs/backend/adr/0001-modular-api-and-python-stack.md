# ADR-0001 — Python ile modüler API ve ayrı worker

**Durum:** Önerilen. **Tarih:** 13 Ekim 2026.

Repo Python kaynak araçları, Psycopg kullanan loader ve PostgreSQL 17 sözleşmesi
içeriyor; backend framework'ü henüz yok. İlk ortamın pool/rate-limit bütçesi tek
API process'i için tasarlanıyor.

Karar: Python 3.13, FastAPI/Pydantic DTO ve dependency katmanı, Psycopg 3 +
`psycopg_pool`, ayrı worker process. API router → service → repository sınırı;
API payload/DTO, DB row ve domain komutu ayrı tipler olacak. Uzun pipeline
HTTP request veya FastAPI process'inin geçici background task'ında çalışmayacak.

FastAPI'nin OpenAPI/JSON Schema ve dependency yaklaşımı contract-first hedefe
uygundur. [FastAPI resmî özellikleri](https://fastapi.tiangolo.com/features/).
Psycopg pool ayrı paket/extras ile kurulmalı; lifespan'da explicit open/wait/close,
bağlantı context'inde commit/rollback uygulanmalı.
[Psycopg pool dokümanı](https://www.psycopg.org/psycopg3/docs/advanced/pool.html).

Django veya NestJS bir ekip tercihiyle mümkün alternatiflerdir; bu repo için
ayrı bir dil/admin platformu ihtiyacı kanıtlanmadı. ORM şart koşulmuyor;
mevcut view'lar için parametrik SQL, typed mapping ve kontrollü migrations yeterli
ilk yaklaşımdır. Kafka/Redis/Celery ekleme için iş hacmi veya bakım ihtiyacı henüz
ölçülmedi; kalıcı job metadata PostgreSQL'de tutulacak.

Sonuç: Aynı dil içinde contract/test paylaşımı kolaylaşır. Worker teslim, DE
adapter'ı ve production operator kimliği yine ayrı bağımlılıklardır. Pool/query
boyutları ölçülmeden kapasite veya latency SLA'sı iddia edilmeyecek. Runtime
paket sürümleri Faz 2 lock/CI denemesinde sabitlenecek.
