from fastapi import APIRouter, HTTPException
from db import fetch_all_rows, get_supabase

router = APIRouter()


@router.get("/predictions/{coin_id}")
def predictions(coin_id: str):
    sb = get_supabase()
    paths = fetch_all_rows(
        sb.table("coin_prediction_paths")
        .select("*")
        .eq("coin_id", coin_id)
        .order("cycle_number")
        .order("day_x")
    )
    peaks = fetch_all_rows(
        sb.table("coin_prediction_peaks")
        .select("*")
        .eq("coin_id", coin_id)
        .order("cycle_number")
        .order("peak_type")
    )

    if not paths and not peaks:
        raise HTTPException(
            status_code=404, detail=f"No predictions for coin_id={coin_id}"
        )

    return {"coin_id": coin_id, "paths": paths, "peaks": peaks}
