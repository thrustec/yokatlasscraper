-- TÜİK ADNKS population observations, linked to the YÖK Atlas province lookup.
CREATE TABLE IF NOT EXISTS staging.tuik_population_by_province (
    staging_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_record_id BIGINT NOT NULL UNIQUE REFERENCES raw.source_records(source_record_id),
    il_kodu BIGINT NOT NULL REFERENCES core.cities(il_kodu),
    yil INTEGER NOT NULL CHECK (yil BETWEEN 1900 AND 2200),
    yas_grubu_kodu TEXT NOT NULL,
    yas_grubu TEXT NOT NULL,
    cinsiyet_kodu TEXT NOT NULL,
    cinsiyet TEXT NOT NULL,
    nufus BIGINT NOT NULL CHECK (nufus >= 0),
    tuik_ikamet_kodu TEXT NOT NULL,
    source_dataflow TEXT NOT NULL,
    source_version TEXT NOT NULL,
    source_payload JSONB NOT NULL,
    staged_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tuik_population_year_province
    ON staging.tuik_population_by_province (yil, il_kodu);
CREATE INDEX IF NOT EXISTS idx_tuik_population_year_age_sex
    ON staging.tuik_population_by_province (yil, yas_grubu_kodu, cinsiyet_kodu);

-- Surface the latest observation per province/period/age/sex to API consumers.
CREATE OR REPLACE VIEW api.tuik_population_by_province AS
SELECT DISTINCT ON (p.il_kodu, p.yil, p.yas_grubu_kodu, p.cinsiyet_kodu)
    p.il_kodu,
    c.il_adi,
    p.yil,
    p.yas_grubu_kodu,
    p.yas_grubu,
    p.cinsiyet_kodu,
    p.cinsiyet,
    p.nufus,
    p.tuik_ikamet_kodu,
    p.source_dataflow,
    p.source_version,
    r.endpoint AS source_endpoint,
    r.captured_at AS source_captured_at
FROM staging.tuik_population_by_province AS p
JOIN core.cities AS c ON c.il_kodu = p.il_kodu
JOIN raw.source_records AS sr ON sr.source_record_id = p.source_record_id
JOIN raw.api_responses AS r ON r.api_response_id = sr.api_response_id
ORDER BY p.il_kodu, p.yil, p.yas_grubu_kodu, p.cinsiyet_kodu,
         r.captured_at DESC, p.staged_at DESC;

GRANT SELECT ON staging.tuik_population_by_province TO atlas_analytics;
GRANT SELECT ON api.tuik_population_by_province TO atlas_api, atlas_analytics;
