# External source owner decisions

**Status:** All decisions are `PENDING` as of 13 October 2026. The research work does not approve a source. Per the project contract, do not implement physical RAW tables or durable ingestion for a source until its owner decision is explicitly recorded as `APPROVED`.

The project owner should select one value per source:

- `APPROVED`
- `APPROVED_CONDITIONALLY` (write explicit conditions)
- `REJECTED`
- `HOLD`

| Source | Research recommendation | Owner decision | Conditions / reason | Owner / date |
|---|---|---|---|---|
| URAP | CONDITIONAL | PENDING | Decide whether annual ranking scores and PDF extraction meet project scope. | |
| OpenAlex institution aggregates | RECOMMEND_APPROVE | PENDING | Limit first phase to institution metadata/yearly aggregates; decide separately on works-level import and usage budget. | |
| TÜİK employment | CONDITIONAL | PENDING | Confirm field-level context is useful despite no university-level measure being evidenced. | |
| TÜİK provincial GDP | CONDITIONAL | PENDING | Confirm province/NUTS-2 socioeconomic context is in scope. | |
| TÜİK ADNKS | RECOMMEND_APPROVE | PENDING | Confirm need for annual age/sex population context and geography-code maintenance. | |
| SEGE | CONDITIONAL | PENDING | Choose province 2025 and/or district 2022, and specify desired published values. | |
| TCMB YKKE | CONDITIONAL | PENDING | Confirm regional/city coverage is sufficient and EVDS API access is available. | |
| KYGM | CONDITIONAL | PENDING | Confirm locality-level dorm presence is useful; does not include capacity or proximity. | |

Approval may be recorded by editing this file after the project owner makes the decision. Do not infer approval from a general instruction to research or from a conditional recommendation.
