# Operation kataloğu — Faz 1

Tüm operasyonlar planlanmıştır; bu envanter OpenAPI ile aynı sözleşmeyi taşır.
Ortak input/error/limit/temporal/version/observability kuralları [API](02_API_DESIGN.md) ve [OpenAPI](openapi.yaml) içinde normatiftir.

| Operation | Aktör / scope | Input / başarı | Nesne / transaction |
|---|---|---|---|
| `GET /health/live` (live) | anonymous | path; 200 | No protected object. No SQL writes. |
| `GET /health/ready` (ready) | anonymous | path; 200 | No protected object. No SQL writes. |
| `GET /v1/universities` (listUniversities) | anonymous | path; 200, 304 | No protected object. READ COMMITTED + nonblocking shared transaction publication gate; state, rows and count under the same gate. |
| `GET /v1/cities` (listCities) | anonymous | path; 200, 304 | No protected object. READ COMMITTED + nonblocking shared transaction publication gate; state, rows and count under the same gate. |
| `GET /v1/program-groups` (listProgramGroups) | anonymous | path; 200, 304 | No protected object. READ COMMITTED + nonblocking shared transaction publication gate; state, rows and count under the same gate. |
| `GET /v1/programs` (listPrograms) | anonymous | path; 200, 304 | No protected object. READ COMMITTED + nonblocking shared transaction publication gate; state, rows and count under the same gate. |
| `GET /v1/net-results` (listNetResults) | anonymous | path; 200, 304 | No protected object. READ COMMITTED + nonblocking shared transaction publication gate; state, rows and count under the same gate. |
| `GET /v1/summaries/programs` (programSummary) | anonymous | path; 200, 304 | No protected object. READ COMMITTED + nonblocking shared transaction publication gate; state, rows and count under the same gate. |
| `GET /v1/summaries/net-results` (netSummary) | anonymous | path; 200, 304 | No protected object. READ COMMITTED + nonblocking shared transaction publication gate; state, rows and count under the same gate. |
| `GET /v1/programs/{kilavuz_kodu}/{yil}` (getProgram) | anonymous | path; 200, 304 | No protected object. READ COMMITTED + nonblocking shared transaction publication gate; state, rows and count under the same gate. |
| `GET /v1/coverage` (coverage) | anonymous | path; 200 | No protected object. Read sanitized publication status. No data counts are computed while gate is unavailable. |
| `POST /internal/v1/ingestions` (createIngestion) | ingest:create | CreateIngestion; 201 | Allowed source; creator assigned server-side. RAW run + ownership + idempotency receipt + audit on one ingest connection. |
| `GET /internal/v1/ingestions/{run_id}` (getIngestion) | ingest:read | path; 200 | Creator principal + permitted source only. No SQL writes. |
| `POST /internal/v1/ingestions/{run_id}/responses` (storeResponse) | ingest:write | StoreResponse; 201, 200 | Own running run + source/method/endpoint policy. One RAW + children + response metadata + observation + artifact link + idempotency + audit SQL transaction. |
| `POST /internal/v1/ingestions/{run_id}/complete` (completeIngestion) | ingest:complete | CompleteIngestion; 200 | Own running run; immutable terminal outcome, identical command replay allowed. Validate server observation counts; update allowed run lifecycle columns + idempotency + audit. |
| `GET /internal/v1/ingestions/{run_id}/manifest` (getManifest) | raw:manifest:read | path; 200 | Own run, or permitted input of currently assigned live worker job (job_id required for worker). No SQL writes. |
| `POST /ops/v1/jobs` (createJob) | jobs:create | CreateJob; 202 | All input runs in allowed source scope and completed; registered pipeline/revision only. Active input uniqueness + queue metadata + idempotency + audit. |
| `GET /ops/v1/jobs` (listJobs) | jobs:read | path; 200 | Allowed sources only. No SQL writes. |
| `GET /ops/v1/jobs/{job_id}` (getJob) | jobs:read | path; 200 | Allowed job input sources. No SQL writes. |
| `POST /ops/v1/jobs/{job_id}/retry` (retryJob) | jobs:retry | RetryJob; 200, 202 | Allowed failed/partial/expired job; CORE recovery policy approved and old session released. Dry-run changes no job/domain state; it may persist idempotency/audit receipt. Apply checks plan/state/epoch under gate. |
| `POST /internal/v1/jobs/claim` (claimJob) | jobs:claim | ClaimJob; 200, 204 | Server worker principal/source/pipeline capability mapping. Short control transaction with FOR UPDATE SKIP LOCKED; active CORE lane uniqueness. |
| `POST /internal/v1/jobs/{job_id}/start` (startJob) | jobs:start | StartJob; 200 | Assigned principal + current secret lease + epoch + permitted source. Control metadata + idempotency + audit; start/complete verifies stored worker gate PID and job state. |
| `POST /internal/v1/jobs/{job_id}/heartbeat` (heartbeatJob) | jobs:heartbeat | HeartbeatJob; 200 | Assigned principal + current secret lease + epoch + permitted source. Control metadata + idempotency + audit; start/complete verifies stored worker gate PID and job state. |
| `POST /internal/v1/jobs/{job_id}/complete` (completeJob) | jobs:complete | CompleteJob; 200 | Assigned principal + current secret lease + epoch + permitted source. Control metadata + idempotency + audit; start/complete verifies stored worker gate PID and job state. |
| `GET /ops/v1/ingestions` (listIngestions) | ops:ingestions:read | path; 200 | Server allowed source filter; no unrestricted caller scope. No SQL writes. |
| `GET /ops/v1/quality` (qualitySummary) | ops:quality:read | path; 200 | Allowed source only; DE owns quality rules. No SQL writes. |
| `GET /ops/v1/lineage/{run_id}` (lineage) | ops:lineage:read | path; 200 | Allowed run source; metadata projection only. No SQL writes. |
| `GET /ops/v1/publications` (listPublications) | publications:read | path; 200 | Authorized operator publication source scope. No SQL writes. |
| `POST /ops/v1/publications` (publish) | publications:publish | Publish; 200 | Allowed candidate sources + succeeded job + DE attestation + current epoch/plan token. Short exclusive transaction gate + publication/current epoch + idempotency + audit; no CORE writes. |
| `GET /ops/v1/metrics` (metrics) | metrics:read | path; 200 | No protected object. No SQL writes. |
