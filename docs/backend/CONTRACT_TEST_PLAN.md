# Runtime contract kabul planı — Faz 1

Bunlar yürütülmüş endpoint testleri değildir. Faz 3/4 için operation bazlı acceptance senaryolarıdır.
Public read: anonim, null/yıl/coverage ve secret dışlama; private: invalid key, scope, source/owner/lease reddi.
Concurrent read gate altında tutarlı rows/count; mutation unique/idempotency veya state kontrolü. Her test gerçek PostgreSQL kullanan test ortamında çalıştırılır.

| Operation | Normal | Invalid | Auth / owner | Repeat | Concurrent |
|---|---|---|---|---|---|
| live | live-normal | live-invalid | live-anonymous-and-no-sensitive-fields | live-repeat-read-or-claim | live-concurrent |
| ready | ready-normal | ready-invalid | ready-anonymous-and-no-sensitive-fields | ready-repeat-read-or-claim | ready-concurrent |
| listUniversities | listUniversities-normal | listUniversities-invalid | listUniversities-anonymous-and-no-sensitive-fields | listUniversities-repeat-read-or-claim | listUniversities-concurrent |
| listCities | listCities-normal | listCities-invalid | listCities-anonymous-and-no-sensitive-fields | listCities-repeat-read-or-claim | listCities-concurrent |
| listProgramGroups | listProgramGroups-normal | listProgramGroups-invalid | listProgramGroups-anonymous-and-no-sensitive-fields | listProgramGroups-repeat-read-or-claim | listProgramGroups-concurrent |
| listPrograms | listPrograms-normal | listPrograms-invalid | listPrograms-anonymous-and-no-sensitive-fields | listPrograms-repeat-read-or-claim | listPrograms-concurrent |
| listNetResults | listNetResults-normal | listNetResults-invalid | listNetResults-anonymous-and-no-sensitive-fields | listNetResults-repeat-read-or-claim | listNetResults-concurrent |
| programSummary | programSummary-normal | programSummary-invalid | programSummary-anonymous-and-no-sensitive-fields | programSummary-repeat-read-or-claim | programSummary-concurrent |
| netSummary | netSummary-normal | netSummary-invalid | netSummary-anonymous-and-no-sensitive-fields | netSummary-repeat-read-or-claim | netSummary-concurrent |
| getProgram | getProgram-normal | getProgram-invalid | getProgram-anonymous-and-no-sensitive-fields | getProgram-repeat-read-or-claim | getProgram-concurrent |
| coverage | coverage-normal | coverage-invalid | coverage-anonymous-and-no-sensitive-fields | coverage-repeat-read-or-claim | coverage-concurrent |
| createIngestion | createIngestion-normal | createIngestion-invalid | createIngestion-missing-or-denied-identity | createIngestion-same-key-replay | createIngestion-concurrent |
| getIngestion | getIngestion-normal | getIngestion-invalid | getIngestion-missing-or-denied-identity | getIngestion-repeat-read-or-claim | getIngestion-concurrent |
| storeResponse | storeResponse-normal | storeResponse-invalid | storeResponse-missing-or-denied-identity | storeResponse-same-key-replay | storeResponse-concurrent |
| completeIngestion | completeIngestion-normal | completeIngestion-invalid | completeIngestion-missing-or-denied-identity | completeIngestion-same-key-replay | completeIngestion-concurrent |
| getManifest | getManifest-normal | getManifest-invalid | getManifest-missing-or-denied-identity | getManifest-repeat-read-or-claim | getManifest-concurrent |
| createJob | createJob-normal | createJob-invalid | createJob-missing-or-denied-identity | createJob-same-key-replay | createJob-concurrent |
| listJobs | listJobs-normal | listJobs-invalid | listJobs-missing-or-denied-identity | listJobs-repeat-read-or-claim | listJobs-concurrent |
| getJob | getJob-normal | getJob-invalid | getJob-missing-or-denied-identity | getJob-repeat-read-or-claim | getJob-concurrent |
| retryJob | retryJob-normal | retryJob-invalid | retryJob-missing-or-denied-identity | retryJob-same-key-replay | retryJob-concurrent |
| claimJob | claimJob-normal | claimJob-invalid | claimJob-missing-or-denied-identity | claimJob-repeat-read-or-claim | claimJob-concurrent |
| startJob | startJob-normal | startJob-invalid | startJob-missing-or-denied-identity | startJob-same-key-replay | startJob-concurrent |
| heartbeatJob | heartbeatJob-normal | heartbeatJob-invalid | heartbeatJob-missing-or-denied-identity | heartbeatJob-same-key-replay | heartbeatJob-concurrent |
| completeJob | completeJob-normal | completeJob-invalid | completeJob-missing-or-denied-identity | completeJob-same-key-replay | completeJob-concurrent |
| listIngestions | listIngestions-normal | listIngestions-invalid | listIngestions-missing-or-denied-identity | listIngestions-repeat-read-or-claim | listIngestions-concurrent |
| qualitySummary | qualitySummary-normal | qualitySummary-invalid | qualitySummary-missing-or-denied-identity | qualitySummary-repeat-read-or-claim | qualitySummary-concurrent |
| lineage | lineage-normal | lineage-invalid | lineage-missing-or-denied-identity | lineage-repeat-read-or-claim | lineage-concurrent |
| listPublications | listPublications-normal | listPublications-invalid | listPublications-missing-or-denied-identity | listPublications-repeat-read-or-claim | listPublications-concurrent |
| publish | publish-normal | publish-invalid | publish-missing-or-denied-identity | publish-same-key-replay | publish-concurrent |
| metrics | metrics-normal | metrics-invalid | metrics-missing-or-denied-identity | metrics-repeat-read-or-claim | metrics-concurrent |

Ek kritik senaryolar: legacy hash ambiguity; original byte/golden canonical hash; incomplete children; atomic rollback;
schema/grants/default ACL negatives; unknown pipeline; claim ACK loss; expired CORE lease requires registered recovery;
gate bypass prevention in approved runner; no 304 on closed gate; publish stale plan/epoch; old cursor restart;
artifact orphan/reconciliation, traversal, byte/depth/records limits; no source values/secret in errors or logs.
