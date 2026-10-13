# Sanayi ve Teknoloji Bakanlığı SEGE

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** official program page and İlçe SEGE 2022 PDF inspected; 2025 province report/download columns and full raw inputs not extracted.

## Access and actual data

The Ministry's [SEGE page](https://www.sanayi.gov.tr/merkez-birimi/b94224510b7b/sege/il-sege-) identifies current studies as İl SEGE-2025 and İlçe SEGE-2022. İl SEGE-2025 covers 81 provinces and uses 52 indicators; İlçe SEGE-2022 covers 973 districts and uses 56 indicators. Both publish an index score, rank and one of six development tiers; provincial NUTS-2 regions have four tiers. The [2022 district report PDF](https://www.sanayi.gov.tr/assets/pdf/birimler/2022-ilce-sege.pdf) confirms the district findings and indicator count.

The public ministry page links reports, but a machine-readable API or raw indicator spreadsheet was not verified. Treat score/rank/tier as the confirmed extract scope; do not assume all 52/56 source variables are published as a machine-readable dataset. PDF or official report-table extraction is feasible with manual reconciliation. The page's specific robot/automated-use policy and redistribution license were not conclusively verified.

## Grain, keys, and temporal meaning

- Score row candidate: `(edition, geography_level, source_geography_label/code)`.
- If component variables are individually available, use a separate grain with variable code/definition, unit and reference year.
- Province 2025 and district 2022 are different editions and levels, not one continuous series. Preserve source labels and report page/table locator; no confirmed stable source geo ID in the inspected PDF summary.

## Rights, risks, value

Ministry reports are public to read; an open-data/republication license was not verified. Risks: version mismatch between levels, PDF extraction errors, differences in source years across 52/56 indicators, and interpreting rank/tier as raw socioeconomic measurements. Value: location-level socioeconomic context for province/district comparisons; no direct university or program measure.

## RAW design candidate (not implemented)

Archive each official report/artifact, edition and its metadata. Store score, rank, tier as separate observed values. If full components are published, preserve their source definitions and observation years in separate source-variable tables. Do not derive a YÖK/city key until official geography codes or a reviewed crosswalk are available.

**API status:** `API_NOT_VERIFIED`; **alternative:** ministry report/HTML page; **rights:** `REVIEW`.  
**Recommendation:** `CONDITIONAL` — useful for location context; confirm 2025/2022 editions and actual desired variables with owner.  
**Owner decision:** `PENDING`.

Sources: [Ministry SEGE page](https://www.sanayi.gov.tr/merkez-birimi/b94224510b7b/sege/il-sege-), [İlçe SEGE 2022 PDF](https://www.sanayi.gov.tr/assets/pdf/birimler/2022-ilce-sege.pdf).
