from fastapi import APIRouter
from db import DB_MODE, get_sqlite, get_supabase

router = APIRouter()


@router.get("/coins")
def list_coins():
    if DB_MODE == "supabase":
        sb = get_supabase()
        res = sb.table("coins").select("id, symbol, name, rank").order("rank").execute()
        return res.data
    else:
        conn = get_sqlite()
        rows = conn.execute("SELECT id, symbol, name, rank FROM coins ORDER BY rank").fetchall()
        conn.close()
        return [dict(r) for r in rows]
