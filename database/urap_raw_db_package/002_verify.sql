-- Execute after importer; should be 198 ranking rows and 1584 metric rows.
SELECT e.edition,g.code AS ranking_group, count(*) AS row_count,
 min(r.source_rank) AS min_rank,max(r.source_rank) AS max_rank,
 count(DISTINCT r.source_rank) AS unique_ranks
FROM raw.urap_ranking_rows r
JOIN raw.urap_editions e ON e.id=r.edition_id
JOIN raw.urap_ranking_groups g ON g.id=r.group_id
GROUP BY e.edition,g.code;
SELECT count(*) AS metric_count FROM raw.urap_metric_scores;
SELECT r.source_rank,r.university_name,r.city,r.total_score,
  sum(m.score) AS metric_sum,abs(sum(m.score)-r.total_score) AS absolute_delta
FROM raw.urap_ranking_rows r JOIN raw.urap_metric_scores m ON m.ranking_row_id=r.id
GROUP BY r.id
HAVING abs(sum(m.score)-r.total_score)>0.06;
