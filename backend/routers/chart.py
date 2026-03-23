from fastapi import APIRouter, HTTPException
from db import DB_MODE, get_sqlite, get_supabase

router = APIRouter()


@router.get("/chart-data/{coin_id}")
def chart_data(coin_id: str):
    if DB_MODE == "supabase":
        sb = get_supabase()
        ohlcv = sb.table("ohlcv").select(
            "date, open, high, low, close, volume_quote"
        ).eq("coin_id", coin_id).order("date").execute().data

        boxes = sb.table("coin_analysis_results").select("*").eq(
            "coin_id", coin_id
        ).order("box_index").execute().data
    else:
        conn = get_sqlite()
        ohlcv = [dict(r) for r in conn.execute(
            "SELECT date, open, high, low, close, volume_quote FROM ohlcv "
            "WHERE coin_id=? ORDER BY date", (coin_id,)
        ).fetchall()]
        boxes = [dict(r) for r in conn.execute(
            "SELECT * FROM coin_analysis_results WHERE coin_id=? ORDER BY box_index",
            (coin_id,)
        ).fetchall()]
        conn.close()

    if not ohlcv:
        raise HTTPException(status_code=404, detail=f"coin_id={coin_id} not found")

    return {"coin_id": coin_id, "ohlcv": ohlcv, "boxes": boxes}
