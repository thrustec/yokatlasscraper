# TCMB EVDS Yeni Kiracı Kira Endeksi (YKKE)

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** official EVDS3 YKKE series group, current platform documentation, method, and use terms verified; authenticated data request and exact YKKE series codes/observations not captured.

## Access and actual data

The [EVDS YKKE group](https://evds3.tcmb.gov.tr/tumSeriler/2003/bie_ykke) lists monthly Yeni Kiracı Kira Endeksi series. The TCMB methodology explains it uses rental valuations in bank property-appraisal reports and estimates across 13 NUTS-2 and 6 NUTS-1 strata; Türkiye and selected large-city reporting appear in the publication. This is not a complete set of 81 provincial series.

TCMB opened EVDS3 as a beta on 26 January 2026 and kept EVDS2 available during the transition. The current [EVDS3 platform page](https://evds3.tcmb.gov.tr/hakkinda) documents REST web services and export in JSON, CSV, and XML; the current [user-documentation page](https://evds3.tcmb.gov.tr/dokumanlar) lists an EVDS Web Service Guide. The current EVDS3 endpoint syntax, authentication/header details, exact YKKE series IDs, date bounds, response structure, rate limits and revision behavior have not yet been confirmed from that guide or a live request. The old EVDS2 endpoint pattern must not be copied into an EVDS3 implementation without verification.

EVDS terms permit third-party use and publication when the source is cited, including commercial use without passing on an extra fee. TCMB reserves the right to change or remove data without notice and does not guarantee completeness or accuracy.

## Grain, keys, and temporal meaning

Candidate grain: `(series_code, period_month, geography_code/label, measure, base)`. Store series metadata and geographic stratum independently. Exact codes and whether the series are indices or rent-value series should be copied from EVDS metadata. Monthly observation period differs from retrieval date.

## Rights, risks, value

Use/publication is allowed with TCMB attribution under the inspected EVDS terms. Risks: EVDS3 beta/current API transition, key handling, series group revisions, incomplete province coverage and methodology changes. Value: monthly regional housing-cost/rent context for students and university locations, with geographic resolution limitations.

## RAW design candidate (not implemented)

Archive the exact response bytes, request parameters and series metadata. Store source series IDs, frequency, geographic stratum and observation values in separate source-oriented records. No mapping to all province rows is valid without official coverage metadata.

**API status:** `API_REQUIRES_AUTH`; exact YKKE API response not verified. **Rights:** source citation required; terms permit third-party use/publication.  
**Recommendation:** `CONDITIONAL` — approve only if 13 NUTS-2/6 NUTS-1 and selected-city coverage meets scope.  
**Owner decision:** `PENDING`.

Sources: [EVDS YKKE series group](https://evds3.tcmb.gov.tr/tumSeriler/2003/bie_ykke), [TCMB YKKE methodology](https://tcmb.gov.tr/wps/wcm/connect/blog/tr/main%20menu/analizler/kiralar%20icin%20yeni%20bir%20gosterge%20yeni%20kiraci%20kira%20endeksi), [EVDS3 about and API format information](https://evds3.tcmb.gov.tr/hakkinda), [EVDS3 user documentation](https://evds3.tcmb.gov.tr/dokumanlar), [EVDS3 beta announcement](https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB%2BTR/Main%2BMenu/Duyurular/Basin/2026/DUY2026-03), [EVDS use terms](https://evds3.tcmb.gov.tr/igmevdsms-dis/documents/showDocument?docId=18).
