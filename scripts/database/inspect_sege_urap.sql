-- DBeaver: "SEGE URAP - Sunucu" bağlantısıyla çalıştırın. Yalnızca okuma yapar.

-- Yayımlanmış raporların kapsamı
SELECT 'SEGE ' || yerlesim_duzeyi AS kaynak,
       yil::text AS donem,
       count(*) AS kayit_sayisi
FROM api.sege_results
GROUP BY yerlesim_duzeyi, yil
UNION ALL
SELECT 'URAP universite', donem, count(*)
FROM api.urap_rankings
GROUP BY donem
ORDER BY kaynak, donem;

-- Kaynak PDF'ler ve yayın bilgileri
SELECT *
FROM api.report_publications
ORDER BY report_id;

-- SEGE: il, ilçe ve bölge sonuçları
SELECT *
FROM api.sege_results
ORDER BY yerlesim_duzeyi, sira;

-- URAP: üniversiteler ve ölçüt puanları
SELECT *
FROM api.urap_rankings
ORDER BY sira;
