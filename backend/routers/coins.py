from fastapi import APIRouter
from db import get_supabase

router = APIRouter()


@router.get("/coins")
def list_coins():
    sb = get_supabase()
    res = sb.table("coins").select("id, symbol, name, rank").order("rank").execute()
    return res.data
