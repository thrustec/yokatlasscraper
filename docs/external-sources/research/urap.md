# URAP Türkiye rankings

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** official PDF fetched and inspected; its table sample, response metadata, and SHA-256 were captured.

## Access and actual data

Official report: [URAP Türkiye 2025–2026 PDF](https://newtr.urapcenter.org/cdn/storage/PDFs/tQbaMj9JihCHaaNuE/original/tQbaMj9JihCHaaNuE.pdf), 31 pages, dated 19 October 2025. Direct retrieval on 2026-10-13T16:05:20Z returned HTTP 200, `application/pdf`, 1,092,119 bytes; SHA-256 `8d7847e3d62c995b1e9e6156cddb4ee61f67eedfe6c17832a6b19477e5dc5095`. It says it uses Clarivate/InCites and YÖK-published data. The report describes 15 indicators, including papers, citations, total documents, doctoral graduates/students, student-to-faculty ratio, domestic/international collaboration, and TÜBİTAK project counts. Indicator reference windows differ: e.g. papers in 2024, citations/documents/collaboration/TÜBİTAK projects during 2020–2024, and student/doctoral measures in academic years 2023–2025.

The report explicitly states that this edition contains 198 universities. A verified sample from its research-university table is Koç University, rank 1, Istanbul, article score 189.43, citation score 195.73, total score 1152.95. The PDF tables show university name, rank, city, total score and indicator **scores** (e.g. the research university table includes Article Score, Citation Score, Document Score, Doctoral Score, etc.). The report explains that several of the 15 measures are combined to reduce table columns. Therefore, a displayed score must not be stored or described as the underlying raw count.

The official portal is [newtr.urapcenter.org](https://newtr.urapcenter.org/). No documented public API, machine-readable download endpoint, underlying workbook, or pagination was verified. URAP `robots.txt` returned 404; this does not establish permission to crawl or republish, so automated-use/reuse terms still need review. Treat the PDF and official tables as the verified formats. A PDF parser/importer is feasible for a versioned static edition but needs row count and totals reconciled to the visible official table before acceptance.

## Grain, keys, and temporal meaning

- Candidate record grain: `(edition, ranking_group, source_university_name, indicator_code)`; rank/overall score can be edition/group-level attributes, while indicator scores need their own metric rows.
- No stable URAP institution ID was confirmed in the inspected PDF. Preserve exact source name and city as source-local values; do not invent an identifier.
- Edition and ranking group (including medical-faculty grouping) are part of identity. Preserve page/table/row locator.
- Store the methodological reference period per indicator, separate from edition/publication date and retrieval date.

## Rights, risks, value

The PDF is publicly reachable. A clear open-data license or permission for bulk redistribution/republication was not verified; source attribution and reuse terms need review. Main risks: PDF extraction layout changes, names without IDs, ranking table group changes, and score/count confusion. Value: a yearly national research profile and comparison of university-level research indicators.

## RAW design candidate (not implemented)

Preserve the PDF bytes as an immutable artifact; model edition, ranking group, source institution label, indicator definition/reference window, and numeric rank/score observations separately. Use a source row locator and raw text alongside parsed numeric value. Crosswalk to YÖK universities only in a reviewed mapping layer.

**API status:** `API_NOT_VERIFIED`; **alternative:** official PDF (verified 198 universities; byte hash and example row captured); **rights:** `REVIEW`; **schema readiness:** conditional on real table extraction and owner decision.  
**Recommendation:** `CONDITIONAL` — useful if the project accepts ranking scores and annual PDF import/review.  
**Owner decision:** `PENDING`.

Sources: [URAP report](https://newtr.urapcenter.org/cdn/storage/PDFs/tQbaMj9JihCHaaNuE/original/tQbaMj9JihCHaaNuE.pdf), [URAP official ranking portal](https://newtr.urapcenter.org/).
