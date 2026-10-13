# External source research — 13 October 2026

This branch records the Phase 0/1 research requested by `EXTERNAL_SOURCES_SCRAPER_RESEARCH_RAW_CONTRACT_TR.md`. It does not create a migration or collect/persist a data load. No source has an owner decision yet.

## How to read the results

- `API_VERIFIED` means a live machine-readable response was captured and checked. `API_REQUIRES_AUTH` means official docs describe an authenticated service, but this workspace did not have a source credential, so no authenticated response, pagination, or hash was captured.
- Direct live captures now include byte/entity sizes and SHA-256 for the URAP PDF, one public OpenAlex JSON response, and the KYGM HTML table. The reports distinguish those captures from authenticated endpoints not yet queried.
- Rights are marked `REVIEW` when a clear reuse license/redistribution permission was not verified. Access to a public page is not by itself a license.
- Source decisions remain `PENDING`. The contract requires a source-by-source owner decision before physical RAW tables or durable ingestion.

## Findings requiring care

1. The 2025–2026 URAP PDF confirms 198 universities and reports ranks and indicator **scores** in its tables. Its methodology describes underlying counts, but those counts are not the same as the displayed scores.
2. OpenAlex's live public API returned 606 Türkiye-filtered institution records in the captured query. Institution identifiers are its own `I...` IDs and ROR identifiers. No documented rule maps the first four digits of a YÖK ID to OpenAlex.
3. TÜİK's newest employment release as of this review is 2025 (published 23 July 2026), covering 2015–2024 cohorts as of 2025. It is published by level/field/program and graduate/reference year; the inspected release does not establish a university-level result.
4. TCMB YKKE is monthly, but the methodology describes 13 NUTS-2 and 6 NUTS-1 strata plus Türkiye and selected large-city reporting. It is not an 81-province series.
5. KYGM's inspected page is an HTML table of province, district, and gender (353 rows in the captured page). It does not provide dorm capacity or a complete facility catalog.

## Reports

- [Repository/database baseline](existing_db_baseline.md)
- [URAP](urap.md)
- [OpenAlex](openalex.md)
- [TÜİK employment](tuik_employment.md)
- [TÜİK provincial GDP](tuik_gdp.md)
- [TÜİK ADNKS](tuik_adnks.md)
- [SEGE](sege.md)
- [TCMB YKKE](tcmb_ykke.md)
- [KYGM](kygm.md)
- [Source matrix](source_matrix.md)
- [Owner decisions](../decisions/source_approvals.md)
