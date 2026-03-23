"""SQL schema constants for prediction tables."""

INSERT_SQL = """
INSERT INTO coin_analysis_results (
    coin_id, symbol, coin_rank,
    cycle_number, cycle_name,
    box_index, phase, result,
    start_x, end_x, hi, lo, hi_day, lo_day,
    duration, range_pct,
    hi_change_pct, lo_change_pct, gain_pct,
    norm_hi, norm_lo, norm_range_pct, norm_duration,
    norm_hi_change_pct, norm_lo_change_pct, norm_gain_pct,
    is_completed, is_prediction,
    rise_days, decline_days
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""

CREATE_PATHS_SQL = """
CREATE TABLE IF NOT EXISTS coin_prediction_paths (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    coin_id      TEXT,
    symbol       TEXT,
    cycle_number INTEGER,
    scenario     TEXT,
    start_x      INTEGER,
    end_x        INTEGER,
    day_x        INTEGER,
    value        REAL,
    created_at   TEXT DEFAULT (datetime('now'))
)
"""

CREATE_PEAKS_SQL = """
CREATE TABLE IF NOT EXISTS coin_prediction_peaks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    coin_id         TEXT    NOT NULL,
    symbol          TEXT    NOT NULL,
    coin_rank       INTEGER,
    cycle_number    INTEGER NOT NULL,
    cycle_name      TEXT,
    peak_type       TEXT    NOT NULL,
    predicted_value REAL    NOT NULL,
    predicted_day   INTEGER,
    created_at      TEXT DEFAULT (datetime('now'))
)
"""
