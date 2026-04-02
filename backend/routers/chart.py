from fastapi import APIRouter, HTTPException
from db import fetch_all_rows, get_supabase

router = APIRouter()


@router.get("/chart-data/{coin_id}")
def chart_data(coin_id: str):
    sb = get_supabase()
    ohlcv = fetch_all_rows(
        sb.table("ohlcv")
        .select("date, open, high, low, close, volume_quote")
        .eq("coin_id", coin_id)
        .order("date")
    )

    boxes = fetch_all_rows(
        sb.table("coin_analysis_results")
        .select("*")
        .eq("coin_id", coin_id)
        .order("cycle_number")
        .order("box_index")
    )

    if not ohlcv:
        raise HTTPException(status_code=404, detail=f"coin_id={coin_id} not found")

    return {"coin_id": coin_id, "ohlcv": ohlcv, "boxes": boxes}
