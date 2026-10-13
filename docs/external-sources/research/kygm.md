# GSB/KYGM dormitory-present localities

**Reviewed:** 13 October 2026  
**Decision status:** `PENDING`  
**Evidence status:** live official HTML response captured; formal automated-use terms and robots policy remain unverified.

## Access and actual data

The official [Yurt Bulunan İl ve İlçeler page](https://kygm.gsb.gov.tr/Sayfalar/2635/2389/yurt-bulunan-il-ve-ilceler.aspx) was fetched directly on 2026-10-13T16:03:38Z: HTTP 200, `text/html`, 134,968 bytes, SHA-256 `9479fb69e451596912e3e6042131eb7c5b5e2671495f6808812dcff8c07a08d9`. The HTML contains 354 `<tr>` elements: one header and 353 data rows in this captured response. Columns are `İL`, `İLÇE`, `CİNSİYET`; sample rows include Adana/Merkez/Kız ve Erkek and Afyonkarahisar/Çay/Kız. The table is present in server-delivered HTML; no API or CSV was found. Cyprus localities are included. A single fetch does not establish a stable row count or complete historical coverage. `robots.txt` could not be fetched within the timeout, so automated-access policy remains unresolved.

This dataset expresses that dormitory service is present in a locality for a gender category. It does not itself enumerate dorm facilities, addresses, beds/capacity, or distances. Separate facility popup links elsewhere on the site do not change the scope of this table and are not part of this source contract without a separate approval.

## Grain, keys, and temporal meaning

Candidate grain: `(snapshot_date, source_province_name, source_district_name, source_gender_label)`. No stable source IDs are shown in the table. Exact source text and page row locator are needed. Treat an entry as a dated presence observation, not a permanent truth. No listed row means “not listed in this snapshot,” not necessarily “no dormitory exists.”

## Rights, risks, value

Page is publicly viewable. Specific reuse license/ToS for automated extraction was not verified; inspect site terms/robots and request guidance if needed before scheduled crawling. Risks: structure and naming changes, ambiguous “Merkez,” county renames, gender labels and missing rows. Value: coarse student housing availability by district and gender, not campus proximity or capacity.

## RAW design candidate (not implemented)

Archive original HTML bytes and retrieval metadata. Keep source province/district labels, gender label, snapshot date and row locator. Resolve official administrative codes only through a documented crosswalk, retaining unmatched entries. Do not turn the page into a dormitory facility table.

**API status:** `API_NOT_VERIFIED`; **alternative:** official HTML table, one 353-row snapshot captured; **rights/bot:** `REVIEW`; **schema readiness:** low until snapshot and locality mapping validation.  
**Recommendation:** `CONDITIONAL` — useful only if locality-level presence is sufficient and scheduled access is permitted.  
**Owner decision:** `PENDING`.

Source: [KYGM official table](https://kygm.gsb.gov.tr/Sayfalar/2635/2389/yurt-bulunan-il-ve-ilceler.aspx).
