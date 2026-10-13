# External source comparison matrix

**Checked:** 13 October 2026. This matrix is a Phase 1 research record; owner decisions are not recorded.

| Source | Verified API | Alternative format | Bot/access | Rights/reuse | Observed grain/coverage | Key readiness | Project value | Recommendation | Owner |
|---|---|---|---|---|---|---|---|---|---|
| URAP | No documented API verified | Official 2025–26 PDF and ranking portal | Public PDF/page; terms for automated redistribution unverified | Review | University name, city, rank/group, total and indicator **scores**; edition-specific | Low/medium: no stable ID confirmed | Strong for annual research-ranking context | Conditional | PENDING |
| OpenAlex | Official REST documented; live authenticated response not captured | API and full-data snapshot options | Free key advised for scale; 429 and daily budget; rate limits documented | CC0 metadata; serving has usage budget/pricing | Institutions, works, yearly counts; global | High source IDs; crosswalk still manual | Strong for research output/trends | Approve institution aggregates; conditional works | PENDING |
| TÜİK employment | General SDMX exists; specific flow/query not verified | Official bulletin tables | Key/token flow; dataset auth needed | Review | Level/field/program and cohort/reference year; no university level established | Medium after official field codes extracted | Useful field-level graduate outcomes | Conditional | PENDING |
| TÜİK provincial GDP | General SDMX exists; GDP flow/query not verified | 2024 bulletin tables (2020–24) | Key/token flow | Review | Province/NUTS-2, year, NACE A10, measure/basis | Medium once official geo/activity codes captured | Local economic context | Conditional | PENDING |
| TÜİK ADNKS | General SDMX exists; ADNKS flow/query not verified | 2025 release/tables | Key/token flow | Review | Annual; 31 Dec 2025 release; admin geographies, age/sex series | Medium after geo/age code list/version captured | Population context | Recommend approve | PENDING |
| SEGE | No API verified | Ministry HTML, report PDFs | Public reports; automated-use and redistribution terms to review | Review | İl 2025: 81/52 variables; İlçe 2022: 973/56; scores/ranks/tiers | Medium for scores, low for source geo codes/components | Local socioeconomic context | Conditional | PENDING |
| TCMB YKKE | EVDS API documented; exact YKKE query/response not captured | EVDS series group and method | API key/account; current EVDS3 API contract needs confirm | Use/publication allowed with TCMB attribution | Monthly; 13 NUTS-2, 6 NUTS-1 strata, Türkiye/selected cities | Medium after series/geography codes confirmed | Housing-cost context | Conditional | PENDING |
| KYGM | No API verified | Official HTML table | Public HTML; robots/automated-use terms unverified | Review | Snapshot of province/district/gender presence; Cyprus included | Low: names only, no IDs | Coarse dorm presence only | Conditional | PENDING |

## Evidence gaps before a source can enter implementation

- Acquire and hash real source artifacts/responses for each selected source.
- For authenticated sources, use project-owned API credentials supplied through a secret store; do not commit keys.
- Confirm source-specific licenses/terms and scheduled automation permission.
- For TÜİK and TCMB, establish exact dataflow/series IDs and metadata using their authenticated catalogs.
- Test full coverage and pagination on selected datasets; no displayed index result is treated as a complete source dump.
- Compare repository schema snapshot to live PostgreSQL DDL before designing migrations.

See each linked source report for evidence and limitations.
