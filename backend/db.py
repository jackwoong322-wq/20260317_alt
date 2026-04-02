"""Supabase client factory for backend API."""

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _BACKEND_DIR.parent
load_dotenv(_ROOT_DIR / ".env")
load_dotenv(_BACKEND_DIR / ".env", override=False)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_PAGE_SIZE = 1000


def get_supabase():
    from supabase import create_client

    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_all_rows(query: Any, page_size: int = SUPABASE_PAGE_SIZE) -> list[dict]:
    rows: list[dict] = []
    start = 0

    while True:
        batch = query.range(start, start + page_size - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size

    return rows
