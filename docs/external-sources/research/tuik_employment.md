# TÜİK higher-education employment indicators

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** official 2024 bulletin and SDMX documentation discovered; dataset-specific authenticated response/dataflow not verified.

## Access and actual data

The provided [2024 release](https://veriportali.tuik.gov.tr/Bulten/Index?dil=1&p=Yuksekogretim-Istihdam-Gostergeleri-2024-54096) says it uses the integrated Education-Labour Force database and covers people who graduated from Turkish higher-education programs in 2014–2023 and were in ADNKS in 2024. Measures include registered employment, time to first job, average monthly earnings, and work in a field compatible with the graduate's education. Official portal search also surfaces a newer **2025** release; selection should be based on the current release and whether historical comparisons are needed.

The 2024 bulletin exposes tables by level/field/program (search results list tables such as graduate-level employment rates by field and by department). This is not university-level output. The release does not establish an institution identifier or a one-program-to-YÖK-program key. No university-level value may be inferred from the field result.

TÜİK's official [SDMX Web Service documentation](https://veriportali.tuik.gov.tr/en/sdmx-web-service-documentation) describes SDMX 2.1 structural objects and REST API use, with API key plus access token for Turkish mobile-verified users and output formats including SDMX-ML/XML, CSV, and JSON. The actual employment dataflow ID, dataset-specific query, response schema, suppression markers, pagination/time coverage and rates were not verified. The bulletin/table surface is a viable official fallback; no workbook bytes or SHA-256 were captured.

## Grain, keys, and temporal meaning

Candidate grain: `(release, education_level, field_or_department_code, indicator, graduate_cohort, reference_year)`. Separate release/publication year, graduation cohort, and outcome reference year. Exact education-field codes and confidentiality/suppression markers must be obtained from dataset metadata, not guessed. Treat suppressed/unavailable cells distinctly from numeric zero and ordinary missing values.

## Rights, risks, value

The public release is readable, but a clear dataset-specific redistribution license was not verified. Request/auth and possible data-access terms need review. Risks: confusing 2024 outcome results with a 2024 graduate cohort; assuming university detail; level/field classification revisions; salary/registration definitions; and hidden suppression values. Value: informs broad career outcomes by discipline and graduate cohort. It supports field-level context, not university ranking or institution-specific placement advice.

## RAW design candidate (not implemented)

Capture release tables as original artifacts. Model release, published field/department codes and definitions, level, metric, cohort/reference year and source cell values independently. Keep source label/code and suppression state. Only later propose a reviewed classification crosswalk; no direct university or YÖK program FK is evidenced.

**API status:** `API_REQUIRES_AUTH` (general SDMX service; source dataflow not verified); **alternative:** official bulletin tables; **rights:** `REVIEW`.  
**Recommendation:** `CONDITIONAL` — useful only if field-level context fits the agreed product question.  
**Owner decision:** `PENDING`.

Sources: [TÜİK 2024 release](https://veriportali.tuik.gov.tr/Bulten/Index?dil=1&p=Yuksekogretim-Istihdam-Gostergeleri-2024-54096), [TÜİK SDMX documentation](https://veriportali.tuik.gov.tr/en/sdmx-web-service-documentation), [TÜİK portal search result identifying 2025 release](https://veriportali.tuik.gov.tr/tr/search?q=istihdam+oranlar%C4%B1).
