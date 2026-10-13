# TCMB EVDS Yeni Kiracı Kira Endeksi (YKKE)

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** official EVDS series group, method, access guide, and use terms verified; authenticated data request and exact series codes/observations not captured.

## Access and actual data

The [EVDS YKKE group](https://evds3.tcmb.gov.tr/tumSeriler/2003/bie_ykke) lists monthly Yeni Kiracı Kira Endeksi series. The TCMB methodology explains it uses rental valuations in bank property-appraisal reports and estimates across 13 NUTS-2 and 6 NUTS-1 strata; Türkiye and three large-city reporting appear in the publication. This is not a complete set of 81 provincial series.

TCMB's EVDS web-service guide documents service requests and CSV/XML/JSON responses. The documented legacy endpoint pattern uses `GET https://evds2.tcmb.gov.tr/service/evds/series={series-codes}&startDate={dd-mm-yyyy}&endDate={dd-mm-yyyy}&type={csv|xml|json}&key={API_KEY}`; the current EVDS3 endpoint contract still needs confirmation before implementation. API key requires an EVDS account. Exact YKKE series codes, date bounds, JSON structure, rate limits and revision behavior remain unverified.

EVDS use terms explicitly allow third-party use and publication when the source is cited, and reserve TCMB's right to change or remove data without notice.

## Grain, keys, and temporal meaning

Candidate grain: `(series_code, period_month, geography_code/label, measure, base)`. Store series metadata and geographic stratum independently. Exact codes and whether the series are indices or rent-value series should be copied from EVDS metadata. Monthly observation period differs from retrieval date.

## Rights, risks, value

Use/publication with source attribution is allowed by the inspected EVDS terms; obey the TCMB site terms. Risks: EVDS3 beta/current API transition, key secrecy, series group revisions, incomplete province coverage and methodology changes. Value: monthly local housing-cost/rent context for students and university locations, with geographic resolution limitations.

## RAW design candidate (not implemented)

Archive the exact response bytes, request parameters and series metadata. Store source series IDs, frequency, geographic stratum and observation values in separate source-oriented records. No mapping to all province rows is valid without official coverage metadata.

**API status:** `API_REQUIRES_AUTH`; exact YKKE API response not verified. **Rights:** source citation required; usage terms permit third-party use/publication.  
**Recommendation:** `CONDITIONAL` — approve only if 13 NUTS-2/6 NUTS-1 and selected-city coverage meets scope.  
**Owner decision:** `PENDING`.

Sources: [EVDS YKKE series group](https://evds3.tcmb.gov.tr/tumSeriler/2003/bie_ykke), [TCMB YKKE methodology](https://tcmb.gov.tr/wps/wcm/connect/blog/tr/main%20menu/analizler/kiralar%20icin%20yeni%20bir%20gosterge%20yeni%20kiraci%20kira%20endeksi), [EVDS API guide](https://evds2.tcmb.gov.tr/help/videos/EVDS_Web_Servis_Kullanim_Kilavuzu.pdf), [EVDS use terms](https://evds3.tcmb.gov.tr/igmevdsms-dis/documents/showDocument?docId=18).
