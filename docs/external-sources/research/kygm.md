# GSB/KYGM dormitory-present localities

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** official HTML table read; no bulk response bytes/hash or formal automated-use terms verified.

## Access and actual data

The official [Yurt Bulunan İl ve İlçeler page](https://kygm.gsb.gov.tr/Sayfalar/2635/2389/yurt-bulunan-il-ve-ilceler.aspx) renders a directly readable HTML table with columns `İL`, `İLÇE`, `CİNSİYET`. Example rows include Adana/Merkez/Kız ve Erkek and Afyonkarahisar/Çay/Kız. The returned page is semantically table-like and appears server-rendered in the inspected content; no API or downloadable CSV was found. The page includes Cyprus localities as well as Türkiye. No pagination was observed in the visible table, but completeness and stable row count were not measured.

This dataset expresses that dormitory service is present in a locality for a gender category. It does not itself enumerate dorm facilities, addresses, beds/capacity, or distances. Separate facility popup links elsewhere on the site do not change the scope of this table and are not part of this source contract without a separate approval.

## Grain, keys, and temporal meaning

Candidate grain: `(snapshot_date, source_province_name, source_district_name, source_gender_label)`. No stable source IDs are shown in the table. Exact source text and page row locator are needed. Treat an entry as a dated presence observation, not a permanent truth. No listed row means “not listed in this snapshot,” not necessarily “no dormitory exists.”

## Rights, risks, value

Page is publicly viewable. Specific reuse license/ToS for automated extraction was not verified; inspect site terms/robots and request guidance if needed before scheduled crawling. Risks: structure and naming changes, ambiguous “Merkez,” county renames, gender labels and missing rows. Value: coarse student housing availability by district and gender, not campus proximity or capacity.

## RAW design candidate (not implemented)

Archive original HTML bytes and retrieval metadata. Keep source province/district labels, gender label, snapshot date and row locator. Resolve official administrative codes only through a documented crosswalk, retaining unmatched entries. Do not turn the page into a dormitory facility table.

**API status:** `API_NOT_VERIFIED`; **alternative:** official HTML table; **rights/bot:** `REVIEW`; **schema readiness:** low until snapshot and locality mapping validation.  
**Recommendation:** `CONDITIONAL` — useful only if locality-level presence is sufficient and scheduled access is permitted.  
**Owner decision:** `PENDING`.

Source: [KYGM official table](https://kygm.gsb.gov.tr/Sayfalar/2635/2389/yurt-bulunan-il-ve-ilceler.aspx).
