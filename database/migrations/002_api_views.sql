-- VIEWS FOR BACKEND / DASHBOARD; expose curated, safe-to-join contracts.
CREATE SCHEMA IF NOT EXISTS api;

CREATE OR REPLACE VIEW api.universities AS
SELECT universite_id, universite_adi FROM core.universities;

CREATE OR REPLACE VIEW api.cities AS
SELECT il_kodu, il_adi FROM core.cities;

CREATE OR REPLACE VIEW api.program_groups AS
SELECT birim_grup_id, puan_turu, birim_grup_adi FROM core.program_groups;

-- Program data is actually available for 2026 in the current archive.
CREATE OR REPLACE VIEW api.program_catalog AS
SELECT
  p.program_version_id,
  p.kilavuz_kodu, p.yil, p.puan_turu,
  p.birim_id, p.birim_adi, p.fymk_id,
  p.universite_id, u.universite_adi,
  p.birim_grup_id, g.birim_grup_adi,
  p.il_kodu, c.il_adi,
  p.min_puan, p.basari_sirasi, p.kontenjan,
  p.ingested_at
FROM core.program_versions AS p
JOIN core.universities AS u ON u.universite_id = p.universite_id
LEFT JOIN core.program_groups AS g ON g.birim_grup_id = p.birim_grup_id AND g.puan_turu = p.puan_turu
LEFT JOIN core.cities AS c ON c.il_kodu = p.il_kodu;

-- Historical 2023..2025 net rows are NOT joined to 2026 program records.
CREATE OR REPLACE VIEW api.net_results AS
SELECT
  n.net_result_id, n.kilavuz_kodu, n.yil, n.puan_turu,
  n.program_version_id, n.universite_id, n.birim_grup_id,
  n.taban_puan, n.katsayi, n.obp,
  n.tyt_trk_net, n.tyt_sos_net, n.tyt_mat_net, n.tyt_fen_net,
  n.ayt_mat_net, n.ayt_fiz_net, n.ayt_kim_net, n.ayt_bio_net,
  n.ayt_tde_net, n.ayt_trh1_net, n.ayt_cog1_net, n.ayt_trh2_net,
  n.ayt_cog2_net, n.ayt_fel_net, n.ayt_din_net, n.ydt_ydil_net,
  n.ingested_at
FROM core.net_results AS n;

CREATE OR REPLACE VIEW api.program_year_summary AS
SELECT yil, puan_turu, count(*)::bigint AS programs,
       count(*) FILTER (WHERE min_puan IS NOT NULL)::bigint AS with_min_puan,
       avg(min_puan) AS avg_min_puan,
       sum(kontenjan)::bigint AS total_kontenjan
FROM core.program_versions
GROUP BY yil, puan_turu;

CREATE OR REPLACE VIEW api.net_year_summary AS
SELECT yil, puan_turu, count(*)::bigint AS net_records,
       avg(tyt_mat_net) AS avg_tyt_mat_net,
       avg(tyt_trk_net) AS avg_tyt_trk_net,
       avg(obp) AS avg_obp
FROM core.net_results
GROUP BY yil, puan_turu;

CREATE OR REPLACE VIEW api.data_coverage AS
SELECT 'universities'::text AS entity, count(*)::bigint AS row_count FROM core.universities
UNION ALL SELECT 'cities', count(*) FROM core.cities
UNION ALL SELECT 'program_groups', count(*) FROM core.program_groups
UNION ALL SELECT 'program_versions', count(*) FROM core.program_versions
UNION ALL SELECT 'net_results', count(*) FROM core.net_results;
