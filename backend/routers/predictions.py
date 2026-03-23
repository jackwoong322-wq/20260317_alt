from fastapi import APIRouter, HTTPException
from db import DB_MODE, get_sqlite, get_supabase

router = APIRouter()


@router.get("/predictions/{coin_id}")
def predictions(coin_id: str):
    if DB_MODE == "supabase":
        sb = get_supabase()
        paths = sb.table("coin_prediction_paths").select("*").eq(
            "coin_id", coin_id
        ).order("day_x").execute().data
        peaks = sb.table("coin_prediction_peaks").select("*").eq(
            "coin_id", coin_id
        ).execute().data
    else:
        conn = get_sqlite()
        paths = [dict(r) for r in conn.execute(
            "SELECT * FROM coin_prediction_paths WHERE coin_id=? ORDER BY day_x",
            (coin_id,)
        ).fetchall()]
        peaks = [dict(r) for r in conn.execute(
            "SELECT * FROM coin_prediction_peaks WHERE coin_id=?",
            (coin_id,)
        ).fetchall()]
        conn.close()

    if not paths and not peaks:
        raise HTTPException(status_code=404, detail=f"No predictions for coin_id={coin_id}")

    return {"coin_id": coin_id, "paths": paths, "peaks": peaks}
