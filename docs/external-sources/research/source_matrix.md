# External source comparison matrix

**Checked:** 13 October 2026. This matrix is a Phase 1 research record; owner decisions are not recorded. Live request metadata and response hashes are included in URAP, OpenAlex, and KYGM reports.

| Source | Verified API | Alternative format | Bot/access | Rights/reuse | Observed grain/coverage | Key readiness | Project value | Recommendation | Owner |
|---|---|---|---|---|---|---|---|---|---|
| URAP | No documented API verified | Official PDF fetched: 200, 1,092,119 bytes, SHA-256 recorded; report confirms 198 universities | Public PDF; robots.txt 404, crawler/reuse terms unresolved | Review | University name, city, rank/group, total and indicator **scores**; edition-specific | Low/medium: no stable ID confirmed | Strong for annual research-ranking context | Conditional | PENDING |
| OpenAlex | Live unauthenticated REST request verified: 200 JSON, 606 TR institutions, cost $0.0001; response hash recorded | API and full-data snapshot options | No key needed for sample; free key advised for scale; 429 and daily budget limits apply | CC0 metadata; serving has usage budget/pricing | Institutions, works, yearly counts; global | High source IDs; crosswalk still manual | Strong for research output/trends | Approve institution aggregates; conditional works | PENDING |
| TÜİK employment | General SDMX API documented; 2024 department table code verified; no authenticated data response | Official 2025 release, browser tables, SDMX bulk CSV/XML/JSON | API key/token; 2025 dataflow query still needs verification | Review | Newest 2025 release identified; cohort bounds need primary-metadata verification; level/field/program; no university result | Medium after official field codes extracted | Useful field-level graduate outcomes | Conditional | PENDING |
| TÜİK provincial GDP | General SDMX API documented; specific GDP flow/query not verified | 2024 bulletin tables (2020–24), SDMX bulk download available | API key/token for SDMX | Review | Province/NUTS-2, year, NACE A10, measure/basis | Medium once official geo/activity codes captured | Local economic context | Conditional | PENDING |
| TÜİK ADNKS | General SDMX API documented; specific flow/query not verified | 2025 release/tables, SDMX bulk download available | API key/token for SDMX | Review | Annual; 31 Dec 2025; admin geographies, age/sex series; table-specific district detail pending | Medium after geo/age code list/version captured | Population context | Recommend approve | PENDING |
| SEGE | No API verified | Ministry HTML, report PDFs | Public reports; automated-use and redistribution terms to review | Review | İl 2025: 81/52 variables; İlçe 2022: 973/56; scores/ranks/tiers | Medium for scores, low for source geo codes/components | Local socioeconomic context | Conditional | PENDING |
| TCMB YKKE | Current EVDS3 docs identify REST and JSON/CSV/XML; exact authenticated YKKE query/response not captured | EVDS3 series group and method | EVDS3 beta; current endpoint/auth details and key availability unverified | Use/publication allowed with TCMB attribution, including commercial use; subject to terms | Monthly; 13 NUTS-2, 6 NUTS-1 strata, Türkiye/selected cities | Medium after series/geography codes confirmed | Housing-cost context | Conditional | PENDING |
| KYGM | No API verified | Live HTML snapshot: 200, 353 data rows; body hash recorded | Public HTML; robots request timed out; automated-use terms unresolved | Review | Snapshot of province/district/gender presence; Cyprus included | Low: names only, no IDs | Coarse dorm presence only | Conditional | PENDING |

## Evidence gaps before a source can enter implementation

- Acquire and hash real source artifacts/responses for each selected source.
- For authenticated sources, use project-owned API credentials supplied through a secret store; do not commit keys.
- Confirm source-specific licenses/terms and scheduled automation permission.
- For TÜİK and TCMB, establish exact dataflow/series IDs and metadata using their authenticated catalogs.
- Test full coverage and pagination on selected datasets; no displayed index result is treated as a complete source dump.
- Compare repository schema snapshot to live PostgreSQL DDL before designing migrations.

See each linked source report for evidence and limitations.
