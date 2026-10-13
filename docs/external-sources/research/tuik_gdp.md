# TÜİK GDP by province

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** 2024 official bulletin and its table list verified; authenticated SDMX dataflow/query and table download bytes not captured.

## Access and actual data

The [2024 bulletin](https://veriportali.tuik.gov.tr/en/press/53930) lists official tables for 2020–2024: GDP by province and NACE A10 activity at current prices; province GDP in chained volume index and percent change by NACE A10; GDP per capita by province; corresponding NUTS-2 regional GDP; NUTS-2 GDP per capita; and provinces' contribution to national GDP growth. This is a publication surface with tables, not evidence of one API endpoint.

General TÜİK SDMX 2.1 web service documentation exists and describes API-key/token authentication and CSV/XML/JSON output. The specific GDP flow, code lists, source unit labels, revision history, and live query were not verified. Use the current official table download or resolve the dataflow through the authenticated catalog before implementation.

## Grain, keys, temporal meaning

Candidate grain: `(release, geographic_scheme, geo_code, year, activity_code, measure, price_or_volume_basis, unit)`. Province and NUTS-2 are separate geography levels. Current-price TRY, chained-volume index, growth rate, per-capita value and contribution-to-growth are distinct measures and cannot be combined. Capture release/revision date separately from observation year.

## Rights, risks, value

Public bulletin available; data-specific reuse license was not verified. Risk: revised historical values, mixed geography level, mixing nominal and chained volume measures, and NACE classifications. Value: regional economic context at province/NUTS-2 level; it does not measure a university or program.

## RAW design candidate (not implemented)

Store the original table artifact and its release metadata. Preserve source geography/activity codes, measure name, exact raw value and published unit; parsed numeric values should not discard source text. Geography mapping is a candidate only after codes/classification vintages are confirmed.

**API status:** `API_REQUIRES_AUTH` (general SDMX service, GDP flow not verified); **alternative:** official 2024 table set; **rights:** `REVIEW`.  
**Recommendation:** `CONDITIONAL` — approve if province-level socioeconomic context is in scope; not for university-specific claims.  
**Owner decision:** `PENDING`.

Sources: [TÜİK GDP 2024](https://veriportali.tuik.gov.tr/en/press/53930), [TÜİK SDMX Web Service](https://veriportali.tuik.gov.tr/en/sdmx-web-service-documentation).
