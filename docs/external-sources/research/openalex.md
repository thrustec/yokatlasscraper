# OpenAlex Institutions and Works

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** official API documentation and pricing read; live response not captured because no project API key was available in this workspace.

## Access and actual data

OpenAlex documents a REST API at `https://api.openalex.org`. Institution singleton path is `GET /institutions/{openalex_id}`; list and works endpoints support query filters, field selection, grouping, and cursor paging (the query conventions should be fixed to the current docs in implementation). The institution ID format is `I...`; institution records include `id`, `ids` (including ROR and legacy IDs when present), `display_name`, acronyms/alternatives, `country_code`, `type`, `lineage`, `associated_institutions`, `works_count`, `cited_by_count`, `summary_stats`, and `counts_by_year`. Work data links to institutions through authorship/affiliation metadata.

Authentication is not required for casual API use, but the current official docs recommend a free API key for meaningful scale. Keyless: 10 requests/second; free-key/prepaid: 30 requests/second; annual: 50 requests/second. `per_page` max is 100 and basic paging is limited to 10,000 results; cursor pagination is needed beyond that. Daily usage budget: $1 free per account; prepaid/annual service costs apply above the free budget. A 429 may reflect a per-second or daily budget limit.

No authenticated request, response content type/body, observed pagination run, response hash, or actual project query cost was verified. Do not put a personal key in the repo; use environment/secret storage.

## Grain, keys, temporal meaning

- Institution grain: OpenAlex institution ID; external ROR is a canonical identifier where present, but source identity remains OpenAlex ID.
- Counts by year grain: `(openalex_id, year)`, preserving exact fields supplied by the source.
- Works grain: OpenAlex work ID. Work-level import can be much larger and requires its own approval/cost estimate.
- `counts_by_year` and current `works_count` are source measurements, not a historical immutable time series unless each API snapshot is retained.
- Institution hierarchy/lineage can cause parent/child double counting. Define whether parent totals include descendants before comparing.

## Rights, risks, value

OpenAlex states metadata is CC0; usage of API service is budgeted. The data license is permissive, but request volume still has current usage pricing. Risks: affiliation matching errors, incomplete ROR lineage, changed counts between snapshots, source curation, and double counting subsidiaries/parent institutions. Value: research output, citations, yearly trends and institution identity enrichment; works records enable deeper analysis but increase scope.

## RAW design candidate (not implemented)

Keep institution entities, source identifiers/lineage, query/run provenance, and yearly count observations separate. Preserve raw API response bytes or a byte-faithful artifact and hash; version the selection/query because API results and counts can change. For work-level scope, store work IDs and authorship links source-locally. Crosswalk from YÖK university ID is a separate reviewed assertion; the claimed “first four YÖK digits” mapping has no source documentation.

**API status:** `API_REQUIRES_AUTH` for scale; basic API exists in docs but this review did not capture a live response. **Rights:** `CC0` for data; usage budgets apply.  
**Recommendation:** `RECOMMEND_APPROVE` for institution/yearly aggregate scope; `CONDITIONAL` for full Works ingestion.  
**Owner decision:** `PENDING`.

Sources: [Institutions data dictionary](https://help.openalex.org/data/institutions/), [Authentication and limits](https://help.openalex.org/api/authentication/), [Pricing](https://help.openalex.org/access/pricing/).
