# TÜİK GDP by province

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** 2024 official bulletin, table list, revision details and general SDMX download/API interface verified; GDP-specific authenticated flow/query not captured.

## Access and actual data

The [2024 bulletin](https://veriportali.tuik.gov.tr/en/press/53930) lists official tables for 2020–2024: GDP by province and NACE A10 activity at current prices; province GDP in chained volume index and percent change by NACE A10; GDP per capita by province; corresponding NUTS-2 regional GDP; NUTS-2 GDP per capita; and provinces' contribution to national GDP growth. This is a publication surface with tables, not evidence of one API endpoint.

General TÜİK SDMX docs specify an API-key-to-token flow and bearer authorization; the portal also documents bulk SDMX downloads in CSV/XML/JSON. The 2024 GDP release documents its table outputs and current yearly revision information, but this review did not resolve the specific dataflow ID/API query or capture a table download. Before implementation, identify the exact flow and code lists via the authenticated catalog or use the official table download.

## Grain, keys, temporal meaning

Candidate grain: `(release, geographic_scheme, geo_code, year, activity_code, measure, price_or_volume_basis, unit)`. Province and NUTS-2 are separate geography levels. Current-price TRY, chained-volume index, growth rate, per-capita value and contribution-to-growth are distinct measures and cannot be combined. Capture release/revision date separately from observation year.

## Rights, risks, value

Public bulletin available; data-specific reuse license was not verified. Risk: revised historical values, mixed geography level, mixing nominal and chained volume measures, and NACE classifications. Value: regional economic context at province/NUTS-2 level; it does not measure a university or program.

## RAW design candidate (not implemented)

Store the original table artifact and its release metadata. Preserve source geography/activity codes, measure name, exact raw value and published unit; parsed numeric values should not discard source text. Geography mapping is a candidate only after codes/classification vintages are confirmed.

**API status:** `API_REQUIRES_AUTH` (general SDMX service, GDP flow not verified); **alternative:** official 2024 table set; **rights:** `REVIEW`.  
**Recommendation:** `CONDITIONAL` — approve if province-level socioeconomic context is in scope; not for university-specific claims.  
**Owner decision:** `PENDING`.

Sources: [TÜİK GDP 2024](https://veriportali.tuik.gov.tr/en/press/53930), [TÜİK SDMX Web Service](https://veriportali.tuik.gov.tr/en/sdmx-web-service-documentation), [TÜİK bulk dataset download](https://veriportali.tuik.gov.tr/tr/bulk-download).
