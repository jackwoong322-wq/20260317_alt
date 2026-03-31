-- 011_create_coins_ohlcv.sql
-- 목적: 011, 012, 021, 031, 032 스크립트 실행에 필요한 전체 테이블 생성
-- 포함: coins, ohlcv, alt_cycle_data, alt_cycle_summary,
--       coin_analysis_results, coin_prediction_paths, coin_prediction_peaks
-- 주의: 아래 권한/RLS 설정은 로컬 개발 편의 기준(완화). 운영 환경에서는 최소 권한 정책 권장.

BEGIN;

-- ============================================================
-- 011 / 012: 수집 데이터
-- ============================================================

CREATE TABLE IF NOT EXISTS public.coins (
    id         TEXT PRIMARY KEY,
    symbol     TEXT NOT NULL,
    name       TEXT NOT NULL,
    rank       INTEGER,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.ohlcv (
    id           BIGSERIAL PRIMARY KEY,
    coin_id      TEXT NOT NULL REFERENCES public.coins(id),
    date         DATE NOT NULL,
    open         REAL NOT NULL,
    high         REAL NOT NULL,
    low          REAL NOT NULL,
    close        REAL NOT NULL,
    volume_base  REAL NOT NULL DEFAULT 0,
    volume_quote REAL NOT NULL DEFAULT 0,
    trade_count  INTEGER NOT NULL DEFAULT 0,
    source       TEXT,
    UNIQUE (coin_id, date)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_coin_date
    ON public.ohlcv (coin_id, date);

-- ============================================================
-- 021: 사이클 분석 테이블
-- ============================================================

CREATE TABLE IF NOT EXISTS public.alt_cycle_data (
    id              BIGSERIAL PRIMARY KEY,
    coin_id         TEXT NOT NULL,
    cycle_number    INTEGER NOT NULL,
    cycle_name      TEXT,
    days_since_peak INTEGER NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    close_price     REAL,
    low_price       REAL,
    high_price      REAL,
    close_rate      REAL,
    low_rate        REAL,
    high_rate       REAL,
    peak_date       DATE,
    peak_price      REAL,
    UNIQUE (coin_id, cycle_number, days_since_peak)
);

CREATE INDEX IF NOT EXISTS idx_alt_cycle_coin
    ON public.alt_cycle_data (coin_id);

CREATE INDEX IF NOT EXISTS idx_alt_cycle_coin_cycle
    ON public.alt_cycle_data (coin_id, cycle_number);

CREATE TABLE IF NOT EXISTS public.alt_cycle_summary (
    id                  BIGSERIAL PRIMARY KEY,
    coin_id             TEXT NOT NULL,
    cycle_number        INTEGER NOT NULL,
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
    UNIQUE (coin_id, cycle_number)
);

CREATE INDEX IF NOT EXISTS idx_alt_summary_coin
    ON public.alt_cycle_summary (coin_id);

-- ============================================================
-- 031 / 032: 박스 분석 및 예측 테이블
-- ============================================================

CREATE TABLE IF NOT EXISTS public.coin_analysis_results (
    id                  BIGSERIAL PRIMARY KEY,
    coin_id             TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    coin_rank           INTEGER,
    cycle_number        INTEGER NOT NULL,
    cycle_name          TEXT NOT NULL,
    box_index           INTEGER NOT NULL,
    phase               TEXT NOT NULL,
    result              TEXT NOT NULL,
    start_x             INTEGER NOT NULL,
    end_x               INTEGER NOT NULL,
    hi                  REAL NOT NULL,
    lo                  REAL NOT NULL,
    hi_day              INTEGER,
    lo_day              INTEGER,
    duration            INTEGER NOT NULL,
    range_pct           REAL NOT NULL,
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
    is_completed        INTEGER DEFAULT 0,
    is_prediction       INTEGER DEFAULT 0,
    rise_days           INTEGER,
    decline_days        INTEGER,
    rise_rate           REAL,
    decline_intensity   REAL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.coin_prediction_paths (
    id           BIGSERIAL PRIMARY KEY,
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

CREATE TABLE IF NOT EXISTS public.coin_prediction_peaks (
    id              BIGSERIAL PRIMARY KEY,
    coin_id         TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    coin_rank       INTEGER,
    cycle_number    INTEGER NOT NULL,
    cycle_name      TEXT,
    peak_type       TEXT NOT NULL,
    predicted_value REAL NOT NULL,
    predicted_day   INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 권한 (개발 편의)
-- ============================================================

GRANT USAGE ON SCHEMA public TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.coins TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.ohlcv TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.alt_cycle_data TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.alt_cycle_summary TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.coin_analysis_results TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.coin_prediction_paths TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.coin_prediction_peaks TO anon, authenticated;

GRANT USAGE, SELECT ON SEQUENCE public.ohlcv_id_seq TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.alt_cycle_data_id_seq TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.alt_cycle_summary_id_seq TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.coin_analysis_results_id_seq TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.coin_prediction_paths_id_seq TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.coin_prediction_peaks_id_seq TO anon, authenticated;

-- RLS 비활성화 (개발 편의)
ALTER TABLE public.coins DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.ohlcv DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.alt_cycle_data DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.alt_cycle_summary DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.coin_analysis_results DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.coin_prediction_paths DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.coin_prediction_peaks DISABLE ROW LEVEL SECURITY;

COMMIT;
