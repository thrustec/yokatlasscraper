-- ÜniRota admin paneli: bot yönetimi için "ops" şeması.
-- Mevcut raw / staging / core / quality / api şemalarına dokunmaz; sadece ekler.
-- Tekrar çalıştırılabilir (IF NOT EXISTS).

CREATE SCHEMA IF NOT EXISTS ops;

-- Panel kullanıcıları (ekip). Parolalar scrypt ile özetlenmiş tutulur.
CREATE TABLE IF NOT EXISTS ops.users (
    user_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username       text NOT NULL UNIQUE CHECK (username ~ '^[a-z0-9._-]{2,40}$'),
    full_name      text NOT NULL,
    email          text,
    password_hash  text NOT NULL,
    receive_alerts boolean NOT NULL DEFAULT true,
    is_active      boolean NOT NULL DEFAULT true,
    created_at     timestamptz NOT NULL DEFAULT now(),
    last_login_at  timestamptz
);

CREATE TABLE IF NOT EXISTS ops.sessions (
    token_hash   text PRIMARY KEY,
    user_id      bigint NOT NULL REFERENCES ops.users(user_id) ON DELETE CASCADE,
    created_at   timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON ops.sessions(user_id);

-- Bot tanımları. Yeni bot eklemek = buraya bir satır (panelden "Yeni bot").
CREATE TABLE IF NOT EXISTS ops.bots (
    bot_id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    slug            text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9][a-z0-9-]{1,40}$'),
    name            text NOT NULL,
    description     text NOT NULL DEFAULT '',
    source_url      text,
    owner_user_id   bigint REFERENCES ops.users(user_id) ON DELETE SET NULL,
    command         text NOT NULL,               -- ör. python -m scraper.yokatlas
    working_dir     text NOT NULL DEFAULT '.',   -- repo köküne göre
    enabled         boolean NOT NULL DEFAULT true,
    schedule_cron   text,                        -- NULL = sadece elle
    timeout_minutes integer NOT NULL DEFAULT 180 CHECK (timeout_minutes BETWEEN 1 AND 2880),
    settings        jsonb NOT NULL DEFAULT '{}'::jsonb,
    expected_min_records integer,                -- bundan az kayıt gelirse uyarı
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Her çalışma bir satır. Panel "başlat" deyince status='queued' satırı açılır,
-- çalıştırıcı (runner) onu alıp botu başlatır.
CREATE TABLE IF NOT EXISTS ops.runs (
    run_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bot_id            bigint NOT NULL REFERENCES ops.bots(bot_id) ON DELETE CASCADE,
    status            text NOT NULL DEFAULT 'queued'
                      CHECK (status IN ('queued','running','succeeded','failed','stopped','timed_out')),
    trigger           text NOT NULL DEFAULT 'manual' CHECK (trigger IN ('manual','schedule','retry')),
    triggered_by      bigint REFERENCES ops.users(user_id) ON DELETE SET NULL,
    queued_at         timestamptz NOT NULL DEFAULT now(),
    started_at        timestamptz,
    finished_at       timestamptz,
    heartbeat_at      timestamptz,
    pid               integer,
    stop_requested    boolean NOT NULL DEFAULT false,
    progress_current  bigint,
    progress_total    bigint,
    progress_label    text,
    pages_requested   bigint NOT NULL DEFAULT 0,
    pages_ok          bigint NOT NULL DEFAULT 0,
    pages_failed      bigint NOT NULL DEFAULT 0,
    records_written   bigint NOT NULL DEFAULT 0,
    warnings          integer NOT NULL DEFAULT 0,
    errors            integer NOT NULL DEFAULT 0,
    exit_code         integer,
    error_message     text,
    retry_of_run_id   bigint REFERENCES ops.runs(run_id) ON DELETE SET NULL,
    ingestion_run_id  bigint REFERENCES raw.ingestion_runs(ingestion_run_id) ON DELETE SET NULL,
    summary           jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_runs_bot ON ops.runs(bot_id, queued_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_status ON ops.runs(status);
-- Aynı bot için aynı anda tek bekleyen/çalışan çalışma.
CREATE UNIQUE INDEX IF NOT EXISTS ux_runs_one_active_per_bot
    ON ops.runs(bot_id) WHERE status IN ('queued','running');

CREATE TABLE IF NOT EXISTS ops.run_logs (
    log_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id   bigint NOT NULL REFERENCES ops.runs(run_id) ON DELETE CASCADE,
    ts       timestamptz NOT NULL DEFAULT clock_timestamp(),
    level    text NOT NULL DEFAULT 'info' CHECK (level IN ('debug','info','warning','error')),
    message  text NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_run_logs_run ON ops.run_logs(run_id, log_id);

-- Başarısız istekler: panelden "hatalıları yeniden dene" ile tekrar denenir.
CREATE TABLE IF NOT EXISTS ops.failed_requests (
    failed_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id       bigint NOT NULL REFERENCES ops.runs(run_id) ON DELETE CASCADE,
    bot_id       bigint NOT NULL REFERENCES ops.bots(bot_id) ON DELETE CASCADE,
    request_key  text NOT NULL,                 -- botun yeniden denemek için anladığı anahtar
    url          text,
    params       jsonb NOT NULL DEFAULT '{}'::jsonb,
    http_status  integer,
    error        text,
    attempts     integer NOT NULL DEFAULT 1,
    created_at   timestamptz NOT NULL DEFAULT now(),
    resolved_at  timestamptz,
    resolved_by_run_id bigint REFERENCES ops.runs(run_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_failed_open ON ops.failed_requests(bot_id) WHERE resolved_at IS NULL;

-- Kim ne yaptı.
CREATE TABLE IF NOT EXISTS ops.audit_log (
    audit_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts        timestamptz NOT NULL DEFAULT now(),
    user_id   bigint REFERENCES ops.users(user_id) ON DELETE SET NULL,
    action    text NOT NULL,
    bot_id    bigint REFERENCES ops.bots(bot_id) ON DELETE SET NULL,
    details   jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON ops.audit_log(ts DESC);

-- E-posta bildirim kuralları.
CREATE TABLE IF NOT EXISTS ops.alert_rules (
    rule_key    text PRIMARY KEY,
    enabled     boolean NOT NULL DEFAULT true,
    threshold   numeric
);
INSERT INTO ops.alert_rules(rule_key, enabled, threshold) VALUES
    ('run_failed',      true,  NULL),   -- çalışma hata ile bitti / zaman aşımı
    ('schedule_missed', true,  24),     -- planlı bot X saattir başarıyla çalışmadı
    ('disk_usage',      true,  80),     -- disk doluluğu % X'i geçti
    ('low_records',     true,  NULL),   -- kayıt sayısı botun beklenen alt sınırının altında
    ('stalled',         true,  15)      -- çalışan bot X dakikadır ses vermiyor
ON CONFLICT (rule_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS ops.alerts_sent (
    alert_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts          timestamptz NOT NULL DEFAULT now(),
    rule_key    text NOT NULL,
    dedupe_key  text NOT NULL,
    bot_id      bigint REFERENCES ops.bots(bot_id) ON DELETE SET NULL,
    run_id      bigint REFERENCES ops.runs(run_id) ON DELETE SET NULL,
    subject     text NOT NULL,
    body        text NOT NULL,
    recipients  text[] NOT NULL DEFAULT '{}',
    delivered   boolean NOT NULL DEFAULT false,
    error       text
);
CREATE INDEX IF NOT EXISTS idx_alerts_dedupe ON ops.alerts_sent(dedupe_key, ts DESC);

-- Çalıştırıcının "yaşıyorum" kaydı (panel üstünde gösterilir).
CREATE TABLE IF NOT EXISTS ops.runner_status (
    runner_name   text PRIMARY KEY,
    heartbeat_at  timestamptz NOT NULL DEFAULT now(),
    started_at    timestamptz NOT NULL DEFAULT now(),
    hostname      text,
    version       text
);
