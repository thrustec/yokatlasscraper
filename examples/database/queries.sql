-- Run these as atlas_api; views exist even when the bot has not loaded records.
SELECT * FROM api.data_coverage ORDER BY entity;
SELECT * FROM api.universities ORDER BY universite_adi LIMIT 20;
SELECT * FROM api.program_catalog WHERE yil = 2026 AND puan_turu = 'SAY' ORDER BY basari_sirasi NULLS LAST LIMIT 20;
SELECT * FROM api.program_year_summary ORDER BY yil DESC, puan_turu;
SELECT * FROM api.net_year_summary ORDER BY yil DESC, puan_turu;
-- Never JOIN net records from 2023..2025 to 2026 program details on code alone.
