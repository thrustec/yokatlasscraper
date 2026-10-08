# YÖK Atlas Schema Discovery

Observed endpoint entities: 5
Direct scalar/JSON columns: 121
Candidate relationships: 10
Available sample rows: 0

## Important distinction
The result reconstructs a **logical model of exposed API resources**, not the server's hidden physical DB schema.
All name-derived relations are candidates. Review overlap and cardinality before enforcing foreign keys.

## Tables
- universities: 2 columns, 0 sample records, PK candidate universiteId
- program_groups: 3 columns, 0 sample records, PK candidate birimGrupId
- cities: 2 columns, 0 sample records, PK candidate ilKodu
- programs: 83 columns, 0 sample records, PK candidate kilavuzKodu
- net_results: 31 columns, 0 sample records, PK candidate None

## Candidate relationships
- programs.universiteId -> universities.universiteId: unverified, overlap=None
- programs.birimGrupId -> program_groups.birimGrupId: unverified, overlap=None
- programs.ilKodu -> cities.ilKodu: unverified, overlap=None
- net_results.universiteId -> universities.universiteId: unverified, overlap=None
- net_results.birimGrupId -> program_groups.birimGrupId: unverified, overlap=None
- net_results.kilavuzKodu -> programs.kilavuzKodu: unverified, overlap=None
- net_results.birimId -> programs.birimId: unverified, overlap=None
- net_results.kilavuzKodu+yil -> programs.kilavuzKodu+yil: year_sensitive_unverified, overlap=None
- program_conditions.kilavuz_kodu -> programs.kilavuzKodu: derived_model, overlap=not applicable
- program_conditions.condition_code -> conditions.condition_code: derived_model, overlap=not applicable

## Next steps
1. Download complete pages in a separately rate-limited collector and retain original response JSON.
2. Compare candidate keys with full-set cardinalities and orphan rates.
3. Verify historical year offsets and net data year independently.
4. Review ERD and approve constraints before production migrations.
5. Implement incremental yearly ingestion, validation, versioning and insight jobs.
