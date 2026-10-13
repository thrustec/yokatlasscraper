# TÜİK ADNKS population by age/sex/geography

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** 2025 release metadata and official series description verified; dataset-specific API response not captured.

## Access and actual data

The [ADNKS 2025 release metadata](https://veriportali.tuik.gov.tr/tr/press/53899/metadata) states the population reference date is 31 December 2025 and describes annual results. TÜİK's series metadata/search descriptions say the publication levels include NUTS 1/2/3 and the administrative units defined in the address database (province, district, municipality, village, neighborhood), with age and sex dimensions. Age categories include five-year groups (0–4 through 90+), alongside other published age groupings.

TÜİK SDMX is the candidate API, but the specific ADNKS dataflow, exact geographic/age/sex codes and response were not verified. Official downloadable tables are the fallback. Exact table completeness and whether every age-by-sex breakdown is available at district level should be confirmed in a real extract.

## Grain, keys, temporal meaning

Candidate grain: `(release, reference_date, geography_scheme, geo_code, sex_code, age_group_code, measure)`. Use official geography codes and classification vintage; labels alone are not keys. The measurement date is year end, distinct from publication/retrieval date. Do not merge changing districts on name alone.

## Rights, risks, value

The official release is public; explicit reuse license was not verified. Risks: administrative boundary changes, code vintage changes, multiple age group definitions, and sparse/suppressed combinations. Value: local population context for university-city/district service planning, not enrollment or demand itself.

## RAW design candidate (not implemented)

Keep release and source geography/age/sex code lists as versioned metadata, and annual population observations separately. Preserve source strings for unavailable/suppressed values rather than coercing to zero. Crosswalk to project geographies only with code-system evidence.

**API status:** `API_REQUIRES_AUTH` (general SDMX API; ADNKS flow not verified); **alternative:** official release and tables; **rights:** `REVIEW`.  
**Recommendation:** `RECOMMEND_APPROVE` if district/province population context is needed; require geography-code vintage handling.  
**Owner decision:** `PENDING`.

Sources: [ADNKS 2025 release metadata](https://veriportali.tuik.gov.tr/tr/press/53899/metadata), [ADNKS series metadata example](https://veriportali.tuik.gov.tr/tr/databrowser/tuik/TR%2CDF_ADNKS_T23%2C1.1), [TÜİK SDMX docs](https://veriportali.tuik.gov.tr/en/sdmx-web-service-documentation).
