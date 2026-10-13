# TÜİK higher-education employment indicators

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** official 2024/2025 releases, a table dataset code, and current SDMX/bulk-download documentation identified; no authenticated response captured.

## Access and actual data

The provided [2024 release](https://veriportali.tuik.gov.tr/Bulten/Index?dil=1&p=Yuksekogretim-Istihdam-Gostergeleri-2024-54096) says it uses the integrated Education-Labour Force database and covers people who graduated from Turkish higher-education programs in 2014–2023 and were in ADNKS in 2024. Measures include registered employment, time to first job, average monthly earnings, and work in a field compatible with the graduate's education. Official portal search also surfaces a newer **2025** release; selection should be based on the current release and whether historical comparisons are needed.

The 2024 bulletin exposes tables by level/field/program (search results list tables such as graduate-level employment rates by field and by department). This is not university-level output. The release does not establish an institution identifier or a one-program-to-YÖK-program key. No university-level value may be inferred from the field result.

TÜİK's [SDMX documentation](https://veriportali.tuik.gov.tr/en/sdmx-web-service-documentation) specifies `POST https://giris.tuik.gov.tr/realms/web/protocol/openid-connect/token` with `grant_type=password`, `client_id=nsi-ws-consumer`, and an API key; subsequent SDMX requests use `Authorization: Bearer …`. Its example structure endpoint is `GET https://nsiws.tuik.gov.tr/rest/dataflow/TR/all/latest?detail=full`. TÜİK also documents bulk downloads in CSV/XML/JSON. The exact 2025 dataflow version, current table query, response, suppression codes and pagination were not captured. The 2024 table code is confirmed as above; no response workbook bytes or hash were captured.

## Grain, keys, and temporal meaning

Candidate grain: `(release, education_level, field_or_department_code, indicator, graduate_cohort, reference_year)`. The source's **2025** release is currently newest. Keep release year, graduate cohort and population/outcome reference year distinct; the latter detailed dimensions remain to be confirmed from the 2025 metadata. Separate release/publication year, graduation cohort, and outcome reference year. Exact education-field codes and confidentiality/suppression markers must be obtained from dataset metadata, not guessed. Treat suppressed/unavailable cells distinctly from numeric zero and ordinary missing values.

## Rights, risks, value

The public release is readable, but a clear dataset-specific redistribution license was not verified. Request/auth and possible data-access terms need review. Risks: confusing 2024 outcome results with a 2024 graduate cohort; assuming university detail; level/field classification revisions; salary/registration definitions; and hidden suppression values. Value: informs broad career outcomes by discipline and graduate cohort. It supports field-level context, not university ranking or institution-specific placement advice.

## RAW design candidate (not implemented)

Capture release tables as original artifacts. Model release, published field/department codes and definitions, level, metric, cohort/reference year and source cell values independently. Keep source label/code and suppression state. Only later propose a reviewed classification crosswalk; no direct university or YÖK program FK is evidenced.

**API status:** `API_REQUIRES_AUTH` (general SDMX service; 2024 table code found; 2025 flow/query not verified); **alternative:** official bulletin and tables; **rights:** `REVIEW`.  
**Recommendation:** `CONDITIONAL` — useful only if field-level context fits the agreed product question.  
**Owner decision:** `PENDING`.

Sources: [TÜİK 2024 release](https://veriportali.tuik.gov.tr/Bulten/Index?dil=1&p=Yuksekogretim-Istihdam-Gostergeleri-2024-54096), [TÜİK SDMX documentation](https://veriportali.tuik.gov.tr/en/sdmx-web-service-documentation), [TÜİK portal search result identifying 2025 release](https://veriportali.tuik.gov.tr/tr/search?q=istihdam+oranlar%C4%B1).
