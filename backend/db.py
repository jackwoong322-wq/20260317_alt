"""DB 연결 — DB_MODE 환경변수에 따라 SQLite 또는 Supabase 사용"""

import os
import sqlite3

DB_MODE     = os.getenv("DB_MODE", "sqlite")
SQLITE_PATH = os.getenv("SQLITE_PATH", "../pairUSDT/crypto_usdt.db")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def get_supabase():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_sqlite():
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn
