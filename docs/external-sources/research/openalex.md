# OpenAlex Institutions and Works

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** public live API sample captured on 13 October 2026; API key not required for this low-volume request.

## Access and actual data

OpenAlex documents a REST API at `https://api.openalex.org`. Institution singleton path is `GET /institutions/{openalex_id}`; list and works endpoints support query filters, field selection, grouping, and cursor paging. A real unauthenticated request succeeded: `GET https://api.openalex.org/institutions?filter=country_code:TR&per_page=1&select=id,display_name,ids,ror,country_code,type,lineage,works_count,cited_by_count,counts_by_year` returned HTTP 200 and JSON (`application/json`). The response reported 606 institutions matching the filter and `meta.cost_usd=0.0001`; the first result was Istanbul University (`https://openalex.org/I67581229`, ROR `https://ror.org/03a5qrr21`, type `education`, current `works_count=88709`, `cited_by_count=3711317`). Its `counts_by_year` included 2024 `works_count=5990`, `oa_works_count=4328`, `cited_by_count=26909`. These figures are a dated source snapshot, not fixed totals.

The official institution schema documents `id`, `ids` (including ROR, legacy GRID, Wikidata/Wikipedia/MAG where present), `display_name`, `display_name_acronyms`, `display_name_alternatives`, country/type, `lineage`, `associated_institutions`, `works_count`, `cited_by_count`, `summary_stats`, `counts_by_year`, `created_date`, `updated_date`, and `works_api_url`. Institution `summary_stats.h_index` is an attribute on the institution record itself; the documentation does not describe a separate institution h-index endpoint. The response sample's `select` did not request `summary_stats`, so no sample h-index value was captured. `works_count` counts works affiliated with the institution itself, excluding child units/predecessors; lineage filtering of works is required to include descendants. Counts by year cover roughly the last ten years, are returned newest-first for institutions, and should be sorted by year before use.

Authentication is not required for casual API use, but the current official docs recommend a free API key for meaningful scale. Keyless: 10 requests/second; free-key/prepaid: 30 requests/second; annual: 50 requests/second. `per_page` max is 100 and basic paging is limited to 10,000 results; cursor pagination is needed beyond that. Daily usage budget: $1 free per account; prepaid/annual service costs apply above the free budget. A 429 may reflect a per-second or daily budget limit. No explicit Retry-After or API error body was captured; implement conservative backoff only after checking current response headers.

A response body of 2,356 bytes was captured at 2026-10-13T16:14:39Z; content type `application/json`; SHA-256 of that same HTTP entity body: `8259b3449b3dd16a73aaf5a33f261e9e7b0426d081ee2c9448ed5d1f8897d6bc`. The response excerpt above is not a substitute for preserving the complete body in the eventual artifact store. Pagination, Works endpoint response, retry behavior, and a full Turkey export were not tested. Do not put a personal key in the repo; use environment/secret storage.

## Grain, keys, temporal meaning

- Institution grain: OpenAlex institution ID; external ROR is an identifier from ROR where present, but source identity remains OpenAlex ID.
- Counts by year grain: `(openalex_id, year)`, preserving exact fields supplied by the source.
- Works grain: OpenAlex work ID. Work-level import can be much larger and requires its own approval/cost estimate.
- Institution h-index is the `summary_stats.h_index` attribute of a dated institution record, not a separate standalone endpoint. Preserve the record snapshot date because it is precomputed and can change.
- `counts_by_year` and current `works_count` are source measurements, not an immutable historical time series unless each API snapshot is retained.
- Institution hierarchy/lineage can cause parent/child double counting. Define whether parent totals include descendants before comparing.

## Rights, risks, value

OpenAlex states metadata is CC0; usage of API service is budgeted. The data license is permissive, but request volume still has current usage pricing. Risks: affiliation matching errors, incomplete ROR lineage, changed counts between snapshots, source curation, and double counting subsidiaries/parent institutions. Value: research output, citations, yearly trends, h-index and institution identity enrichment; works records enable deeper analysis but increase scope.

## RAW design candidate (not implemented)

Keep institution entities, source identifiers/lineage, query/run provenance, and yearly count observations separate. Preserve raw API response bytes or a byte-faithful artifact and hash; version the selection/query because API results and counts can change. For work-level scope, store work IDs and authorship links source-locally. Crosswalk from YÖK university ID is a separate reviewed assertion; the claimed “first four YÖK digits” mapping has no source documentation.

**API status:** `API_VERIFIED` for public low-volume API; a free key is documented for higher limits/usage tracking. **Rights:** `CC0` for data; usage budgets apply.  
**Recommendation:** `RECOMMEND_APPROVE` for institution/yearly aggregate scope; `CONDITIONAL` for full Works ingestion.  
**Owner decision:** `PENDING`.

Sources: [Institutions data dictionary](https://help.openalex.org/data/institutions/), [Common attributes](https://help.openalex.org/data/common-attributes/), [Authentication and limits](https://help.openalex.org/api/authentication/), [Pricing](https://help.openalex.org/access/pricing/).
