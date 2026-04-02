-- ============================================================
-- Supabase / PostgreSQL Schema
-- Source of truth for Supabase database
-- ============================================================

-- coins
CREATE TABLE IF NOT EXISTS coins (
    id         TEXT        PRIMARY KEY,
    symbol     TEXT        NOT NULL,
    name       TEXT        NOT NULL,
    rank       INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ohlcv
CREATE TABLE IF NOT EXISTS ohlcv (
    id           BIGSERIAL   PRIMARY KEY,
    coin_id      TEXT        NOT NULL REFERENCES coins(id),
    date         DATE        NOT NULL,
    open         REAL        NOT NULL,
    high         REAL        NOT NULL,
    low          REAL        NOT NULL,
    close        REAL        NOT NULL,
    volume_base  REAL        NOT NULL DEFAULT 0,
    volume_quote REAL        NOT NULL DEFAULT 0,
    trade_count  INTEGER     NOT NULL DEFAULT 0,
    source       TEXT,
    UNIQUE(coin_id, date)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_coin_date ON ohlcv(coin_id, date);

-- alt_cycle_data
CREATE TABLE IF NOT EXISTS alt_cycle_data (
    id              BIGSERIAL   PRIMARY KEY,
    coin_id         TEXT        NOT NULL,
    cycle_number    INTEGER     NOT NULL,
    cycle_name      TEXT,
    days_since_peak INTEGER     NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    close_price     REAL,
    low_price       REAL,
    high_price      REAL,
    close_rate      REAL,
    low_rate        REAL,
    high_rate       REAL,
    peak_date       DATE,
    peak_price      REAL,
    UNIQUE(coin_id, cycle_number, days_since_peak)
);
CREATE INDEX IF NOT EXISTS idx_alt_cycle_coin       ON alt_cycle_data(coin_id);
CREATE INDEX IF NOT EXISTS idx_alt_cycle_coin_cycle ON alt_cycle_data(coin_id, cycle_number);

-- alt_cycle_summary
CREATE TABLE IF NOT EXISTS alt_cycle_summary (
    id                  BIGSERIAL PRIMARY KEY,
    coin_id             TEXT      NOT NULL,
    cycle_number        INTEGER   NOT NULL,
    cycle_name          TEXT,
    peak_date           DATE,
    peak_price          REAL,
    peak_pct_from_low   REAL,
    low_date            DATE,
    low_price           REAL,
    low_pct_from_peak   REAL,
    prev_peak_date      DATE,
    prev_peak_price     REAL,
    prev_low_date       DATE,
    prev_low_price      REAL,
    UNIQUE(coin_id, cycle_number)
);
CREATE INDEX IF NOT EXISTS idx_alt_summary_coin ON alt_cycle_summary(coin_id);

-- coin_analysis_results
CREATE TABLE IF NOT EXISTS coin_analysis_results (
    id                  BIGSERIAL   PRIMARY KEY,
    coin_id             TEXT        NOT NULL,
    symbol              TEXT        NOT NULL,
    coin_rank           INTEGER,
    cycle_number        INTEGER     NOT NULL,
    cycle_name          TEXT        NOT NULL,
    box_index           INTEGER     NOT NULL,
    phase               TEXT        NOT NULL,
    result              TEXT        NOT NULL,
    start_x             INTEGER     NOT NULL,
    end_x               INTEGER     NOT NULL,
    hi                  REAL        NOT NULL,
    lo                  REAL        NOT NULL,
    hi_day              INTEGER,
    lo_day              INTEGER,
    duration            INTEGER     NOT NULL,
    range_pct           REAL        NOT NULL,
    hi_change_pct       REAL,
    lo_change_pct       REAL,
    gain_pct            REAL,
    norm_hi             REAL,
    norm_lo             REAL,
    norm_range_pct      REAL,
    norm_duration       REAL,
    norm_hi_change_pct  REAL,
    norm_lo_change_pct  REAL,
    norm_gain_pct       REAL,
    is_completed        INTEGER     DEFAULT 0,
    is_prediction       INTEGER     DEFAULT 0,
    rise_days           INTEGER,
    decline_days        INTEGER,
    rise_rate           REAL,
    decline_intensity   REAL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- coin_prediction_paths
CREATE TABLE IF NOT EXISTS coin_prediction_paths (
    id           BIGSERIAL   PRIMARY KEY,
    coin_id      TEXT,
    symbol       TEXT,
    cycle_number INTEGER,
    scenario     TEXT,
    start_x      INTEGER,
    end_x        INTEGER,
    day_x        INTEGER,
    value        REAL,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- coin_prediction_peaks
CREATE TABLE IF NOT EXISTS coin_prediction_peaks (
    id              BIGSERIAL   PRIMARY KEY,
    coin_id         TEXT        NOT NULL,
    symbol          TEXT        NOT NULL,
    coin_rank       INTEGER,
    cycle_number    INTEGER     NOT NULL,
    cycle_name      TEXT,
    peak_type       TEXT        NOT NULL,
    predicted_value REAL        NOT NULL,
    predicted_day   INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
