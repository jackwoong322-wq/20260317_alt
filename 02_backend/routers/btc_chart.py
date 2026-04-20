"""FastAPI router — BTC 차트 전용 엔드포인트 (04_frontend_0222fb 대응)"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import fetch_all_rows, get_supabase

router = APIRouter()

BTC_COIN_ID = "bitcoin"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CyclePoint(BaseModel):
    x: int
    y: float


class CycleSeries(BaseModel):
    name: str
    startDate: str
    minRate: float
    dayCount: int
    data: list[CyclePoint]


class CycleComparisonResponse(BaseModel):
    series: list[CycleSeries]


class LineDataPoint(BaseModel):
    timestamp: str
    day: int
    value: float


class BearBox(BaseModel):
    Start_Timestamp: Optional[str]
    Peak_Timestamp: Optional[str]
    End_Timestamp: Optional[str]
    Start_Rate: float
    Peak_Rate: float


class BearPrediction(BaseModel):
    Start_Timestamp: Optional[str]
    Peak_Timestamp: Optional[str]
    End_Timestamp: Optional[str]
    Start_Rate: float
    Peak_Rate: float
    Peak_Rate_Hi: Optional[float] = None
    Peak_Rate_Lo: Optional[float] = None
    Start_Rate_Hi: Optional[float] = None
    Start_Rate_Lo: Optional[float] = None


class BearCycleInfo(BaseModel):
    startDate: str
    endDate: str


class BearBoxesResponse(BaseModel):
    lineData: list[LineDataPoint]
    boxes: list[BearBox]
    predictions: list[BearPrediction]
    cycleInfo: BearCycleInfo
    config: dict


class BullBox(BaseModel):
    Start_Timestamp: Optional[str]
    End_Timestamp: Optional[str]
    Low_Timestamp: Optional[str]
    Start_Rate: float
    Low_Rate: float


class BullCycleInfo(BaseModel):
    startDate: str
    endDate: str
    maxDays: int


class BullBoxesResponse(BaseModel):
    lineData: list[LineDataPoint]
    boxes: list[BullBox]
    cycleInfo: BullCycleInfo
    config: dict


class OhlcvPoint(BaseModel):
    readable_time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class OhlcvResponse(BaseModel):
    data: list[OhlcvPoint]


class CycleMenuItem(BaseModel):
    number: int
    label: str
    current: Optional[bool] = None


class CycleMenuResponse(BaseModel):
    bearCycles: list[CycleMenuItem]
    bullCycles: list[CycleMenuItem]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _offset_to_ts(peak_dt: date, day_offset: Optional[int]) -> Optional[str]:
    """day 오프셋 → 'YYYY-MM-DDTHH:MM:SS'. None이면 None 반환."""
    if day_offset is None:
        return None
    return (peak_dt + timedelta(days=int(day_offset))).strftime("%Y-%m-%dT00:00:00")


def _get_peak_date(cycle_number: int, sb) -> Optional[date]:
    """alt_cycle_data에서 해당 사이클의 peak_date 조회."""
    r = (
        sb.table("alt_cycle_data")
        .select("peak_date")
        .eq("coin_id", BTC_COIN_ID)
        .eq("cycle_number", cycle_number)
        .limit(1)
        .execute()
    )
    if not r.data:
        return None
    raw = r.data[0].get("peak_date")
    if not raw:
        return None
    return date.fromisoformat(str(raw)[:10])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/ohlcv", response_model=OhlcvResponse)
def btc_ohlcv() -> OhlcvResponse:
    """BTC 일봉 OHLCV 전체 — TradingChart용."""
    sb = get_supabase()
    rows = fetch_all_rows(
        sb.table("ohlcv")
        .select("date, open, high, low, close, volume_quote")
        .eq("coin_id", BTC_COIN_ID)
        .order("date")
    )
    data = [
        OhlcvPoint(
            readable_time=str(row["date"]) + "T00:00:00",
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume_quote"] or 0.0),
        )
        for row in rows
    ]
    return OhlcvResponse(data=data)


@router.get("/cycle-menu", response_model=CycleMenuResponse)
def cycle_menu() -> CycleMenuResponse:
    """Bear/Bull 사이드바 사이클 목록 — SidebarNavigation용."""
    sb = get_supabase()

    box_rows = fetch_all_rows(
        sb.table("coin_analysis_results")
        .select("cycle_number, phase, is_completed, is_prediction")
        .eq("coin_id", BTC_COIN_ID)
        .order("cycle_number")
    )

    # peak_date 조회 (label 생성용) — 사이클별 첫 번째 행만 사용
    peak_rows = fetch_all_rows(
        sb.table("alt_cycle_data")
        .select("cycle_number, peak_date")
        .eq("coin_id", BTC_COIN_ID)
        .order("cycle_number")
        .order("days_since_peak")
    )
    peak_by_cycle: dict[int, str] = {}
    for row in peak_rows:
        cn = int(row["cycle_number"])
        if cn not in peak_by_cycle and row.get("peak_date"):
            peak_by_cycle[cn] = str(row["peak_date"])[:10]

    # 실제(is_prediction=0) 박스만으로 bear/bull 사이클 집계
    bear_cycles: dict[int, dict] = {}
    bull_cycles: dict[int, dict] = {}

    for row in box_rows:
        cn = int(row["cycle_number"])
        phase = (row.get("phase") or "").upper()
        is_completed = int(row.get("is_completed") or 0)
        is_prediction = int(row.get("is_prediction") or 0)

        if is_prediction != 0:
            continue

        if phase == "BEAR":
            if cn not in bear_cycles:
                bear_cycles[cn] = {"current": False}
            # 미완료 실제 박스가 있으면 현재 진행 중 사이클
            if is_completed == 0:
                bear_cycles[cn]["current"] = True

        elif phase == "BULL":
            if cn not in bull_cycles:
                bull_cycles[cn] = {"current": False}
            if is_completed == 0:
                bull_cycles[cn]["current"] = True

    def _make_label(cn: int) -> str:
        pd = peak_by_cycle.get(cn, "")
        if pd:
            ym = pd[:7].replace("-", ".")  # "2021-11" → "2021.11"
            return f"Cycle {cn} ({ym})"
        return f"Cycle {cn}"

    bear_list = [
        CycleMenuItem(
            number=cn,
            label=_make_label(cn),
            current=True if info["current"] else None,
        )
        for cn, info in sorted(bear_cycles.items())
    ]
    bull_list = [
        CycleMenuItem(
            number=cn,
            label=_make_label(cn),
            current=True if info["current"] else None,
        )
        for cn, info in sorted(bull_cycles.items())
    ]

    return CycleMenuResponse(bearCycles=bear_list, bullCycles=bull_list)


@router.get("/cycle-comparison", response_model=CycleComparisonResponse)
def cycle_comparison() -> CycleComparisonResponse:
    """사이클 비교 선 차트 — CycleComparisonChart용."""
    sb = get_supabase()
    rows = fetch_all_rows(
        sb.table("alt_cycle_data")
        .select("cycle_number, cycle_name, days_since_peak, close_rate, peak_date")
        .eq("coin_id", BTC_COIN_ID)
        .order("cycle_number")
        .order("days_since_peak")
    )

    groups: dict[int, dict] = {}
    for row in rows:
        cn = int(row["cycle_number"])
        close_rate = float(row.get("close_rate") or 0.0)
        dsp = int(row.get("days_since_peak") or 0)

        if cn not in groups:
            groups[cn] = {
                "name": row.get("cycle_name") or f"Cycle {cn}",
                "startDate": str(row.get("peak_date") or "")[:10],
                "min_rate": close_rate,
                "max_day": dsp,
                "data": [],
            }

        g = groups[cn]
        if close_rate < g["min_rate"]:
            g["min_rate"] = close_rate
        if dsp > g["max_day"]:
            g["max_day"] = dsp
        g["data"].append(CyclePoint(x=dsp, y=round(close_rate, 4)))

    series = [
        CycleSeries(
            name=g["name"],
            startDate=g["startDate"],
            minRate=round(g["min_rate"], 4),
            dayCount=g["max_day"],
            data=g["data"],
        )
        for g in groups.values()
    ]

    return CycleComparisonResponse(series=series)


@router.get("/bear-boxes", response_model=BearBoxesResponse)
def bear_boxes(cycle: int = Query(default=5, ge=1)) -> BearBoxesResponse:
    """Bear 사이클 박스 차트 — BearBoxChart용."""
    sb = get_supabase()

    peak_dt = _get_peak_date(cycle, sb)
    if peak_dt is None:
        raise HTTPException(status_code=404, detail=f"cycle={cycle} 데이터 없음")

    # BULL 실제 박스의 최소 start_x → bear lineData 상한 결정
    bull_starts = fetch_all_rows(
        sb.table("coin_analysis_results")
        .select("start_x")
        .eq("coin_id", BTC_COIN_ID)
        .eq("cycle_number", cycle)
        .eq("phase", "BULL")
        .eq("is_prediction", 0)
        .order("start_x")
    )
    bull_start_x: Optional[int] = int(bull_starts[0]["start_x"]) if bull_starts else None

    # lineData: BEAR 구간(BULL 시작 전)
    cycle_rows = fetch_all_rows(
        sb.table("alt_cycle_data")
        .select("timestamp, days_since_peak, close_rate")
        .eq("coin_id", BTC_COIN_ID)
        .eq("cycle_number", cycle)
        .order("days_since_peak")
    )
    line_rows = (
        [r for r in cycle_rows if int(r["days_since_peak"]) < bull_start_x]
        if bull_start_x is not None
        else cycle_rows
    )
    line_data = [
        LineDataPoint(
            timestamp=str(row["timestamp"])[:19],
            day=int(row["days_since_peak"]),
            value=round(float(row.get("close_rate") or 0.0), 4),
        )
        for row in line_rows
    ]

    # boxes: 실제 BEAR 박스 (is_prediction=0)
    bear_box_rows = fetch_all_rows(
        sb.table("coin_analysis_results")
        .select("start_x, end_x, hi, lo, hi_day, lo_day")
        .eq("coin_id", BTC_COIN_ID)
        .eq("cycle_number", cycle)
        .eq("phase", "BEAR")
        .eq("is_prediction", 0)
        .order("box_index")
    )
    boxes = [
        BearBox(
            Start_Timestamp=_offset_to_ts(peak_dt, row.get("lo_day")),
            Peak_Timestamp=_offset_to_ts(peak_dt, row.get("hi_day")),
            End_Timestamp=_offset_to_ts(peak_dt, row.get("end_x")),
            Start_Rate=round(float(row.get("lo") or 0.0), 4),
            Peak_Rate=round(float(row.get("hi") or 0.0), 4),
        )
        for row in bear_box_rows
    ]

    # predictions: 예측 BEAR 박스 (is_prediction=1)
    pred_rows = fetch_all_rows(
        sb.table("coin_analysis_results")
        .select("start_x, end_x, hi, lo, hi_day, lo_day")
        .eq("coin_id", BTC_COIN_ID)
        .eq("cycle_number", cycle)
        .eq("phase", "BEAR")
        .eq("is_prediction", 1)
        .order("box_index")
    )
    predictions = [
        BearPrediction(
            Start_Timestamp=_offset_to_ts(peak_dt, row.get("lo_day")),
            Peak_Timestamp=_offset_to_ts(peak_dt, row.get("hi_day")),
            End_Timestamp=_offset_to_ts(peak_dt, row.get("end_x")),
            Start_Rate=round(float(row.get("lo") or 0.0), 4),
            Peak_Rate=round(float(row.get("hi") or 0.0), 4),
        )
        for row in pred_rows
    ]

    start_date = line_data[0].timestamp[:10] if line_data else str(peak_dt)
    end_date = line_data[-1].timestamp[:10] if line_data else str(peak_dt)

    return BearBoxesResponse(
        lineData=line_data,
        boxes=boxes,
        predictions=predictions,
        cycleInfo=BearCycleInfo(startDate=start_date, endDate=end_date),
        config={},
    )


@router.get("/bull-boxes", response_model=BullBoxesResponse)
def bull_boxes(cycle: int = Query(default=4, ge=1)) -> BullBoxesResponse:
    """Bull 사이클 박스 차트 — BullBoxChart용."""
    sb = get_supabase()

    peak_dt = _get_peak_date(cycle, sb)
    if peak_dt is None:
        raise HTTPException(status_code=404, detail=f"cycle={cycle} 데이터 없음")

    # BULL 실제 박스
    bull_box_rows = fetch_all_rows(
        sb.table("coin_analysis_results")
        .select("start_x, end_x, hi, lo, hi_day, lo_day")
        .eq("coin_id", BTC_COIN_ID)
        .eq("cycle_number", cycle)
        .eq("phase", "BULL")
        .eq("is_prediction", 0)
        .order("box_index")
    )
    if not bull_box_rows:
        raise HTTPException(status_code=404, detail=f"cycle={cycle} BULL 박스 없음")

    bull_min_start_x = int(bull_box_rows[0]["start_x"])

    # lineData: BULL 시작점(첫 BULL start_x)부터
    cycle_rows = fetch_all_rows(
        sb.table("alt_cycle_data")
        .select("timestamp, days_since_peak, close_rate")
        .eq("coin_id", BTC_COIN_ID)
        .eq("cycle_number", cycle)
        .gte("days_since_peak", bull_min_start_x)
        .order("days_since_peak")
    )
    line_data = [
        LineDataPoint(
            timestamp=str(row["timestamp"])[:19],
            day=int(row["days_since_peak"]),
            value=round(float(row.get("close_rate") or 0.0), 4),
        )
        for row in cycle_rows
    ]

    boxes = [
        BullBox(
            Start_Timestamp=_offset_to_ts(peak_dt, row.get("start_x")),
            End_Timestamp=_offset_to_ts(peak_dt, row.get("end_x")),
            Low_Timestamp=_offset_to_ts(peak_dt, row.get("lo_day")),
            Start_Rate=round(float(row.get("hi") or 0.0), 4),
            Low_Rate=round(float(row.get("lo") or 0.0), 4),
        )
        for row in bull_box_rows
    ]

    max_days = line_data[-1].day if line_data else 0
    start_date = line_data[0].timestamp[:10] if line_data else str(peak_dt)
    end_date = line_data[-1].timestamp[:10] if line_data else str(peak_dt)

    return BullBoxesResponse(
        lineData=line_data,
        boxes=boxes,
        cycleInfo=BullCycleInfo(startDate=start_date, endDate=end_date, maxDays=max_days),
        config={},
    )
