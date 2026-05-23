"""FastAPI router — BTC 투자 신호 엔드포인트 (04_frontend_0222fb SignalPanel 대응)

GET /api/btc-signal
  → Supabase coin_analysis_results에서 BTC 현재 사이클 박스 조회
  → btc_investment_pipeline() 호출하여 ACCUMULATE/WATCH/CAUTION/EXIT 신호 반환
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import fetch_all_rows, get_supabase

# ---------------------------------------------------------------------------
# 01_pairUSDT 경로를 sys.path에 추가 (btc_signal_api import용)
# ---------------------------------------------------------------------------
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # e:\source\20260317_alt
_PAIR_DIR = _ROOT_DIR / "01_pairUSDT"
if str(_PAIR_DIR) not in sys.path:
    sys.path.insert(0, str(_PAIR_DIR))

router = APIRouter()

BTC_COIN_ID: str = os.getenv("CYCLE_COIN_ID", "bitcoin")


# ---------------------------------------------------------------------------
# Pydantic 응답 모델
# ---------------------------------------------------------------------------

class SignalDisplay(BaseModel):
    label: str
    color: str
    icon: str


class SignalInfo(BaseModel):
    signal: str
    phase: str
    confidence: float
    reason: Optional[str] = None


class SignalDescription(BaseModel):
    stage: int
    stage_name: Optional[str] = None
    signal: str
    action: Optional[str] = None
    message_ko: str
    message_en: Optional[str] = None


class CyclePositionInfo(BaseModel):
    completed_boxes: int
    total_boxes: int
    box_progress: float
    price_position: float
    is_near_target: bool
    phase: str
    cycle_number: int


class ValidationInfo(BaseModel):
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class BtcSignalResponse(BaseModel):
    symbol: str
    cycle_number: int
    phase: str
    signal: SignalInfo
    display: SignalDisplay
    description: SignalDescription
    cycle_position: Optional[CyclePositionInfo] = None
    validation: ValidationInfo


class DashboardSummaryResponse(BaseModel):
    cycleNumber: int
    currentPrice: float
    highPrice: float
    lowPrice: float
    positionPercent: float
    signal: str
    nextPredictedPrice: float
    updatedAt: str


# ---------------------------------------------------------------------------
# Helper: Supabase에서 현재 BTC 사이클 정보 조회
# ---------------------------------------------------------------------------

def _get_current_cycle_info(sb: Any) -> dict:
    """현재 활성 BTC 사이클 번호, 페이즈, 박스 정보 조회.

    is_completed=0 인 박스를 현재 활성 박스로 간주한다.
    """
    rows = fetch_all_rows(
        sb.table("coin_analysis_results")
        .select(
            "cycle_number, phase, is_completed, is_prediction, "
            "start_x, end_x, hi, lo, hi_day, lo_day, box_index"
        )
        .eq("coin_id", BTC_COIN_ID)
        .eq("is_prediction", 0)
        .order("cycle_number", desc=True)
        .order("box_index", desc=True)
    )

    if not rows:
        return {}

    # 최신 사이클에서 미완료(is_completed=0) 박스 찾기
    active_row = None
    for row in rows:
        if int(row.get("is_completed", 1)) == 0:
            active_row = row
            break

    # 미완료 박스가 없으면 가장 최신 row 사용
    if active_row is None:
        active_row = rows[0]

    cycle_number = int(active_row.get("cycle_number", 5))
    phase = str(active_row.get("phase", "BEAR")).upper()

    # 해당 사이클의 전체 박스 목록
    cycle_boxes = [
        r for r in rows
        if int(r.get("cycle_number", 0)) == cycle_number
        and str(r.get("phase", "")).upper() == phase
    ]
    completed_boxes = sum(
        1 for r in cycle_boxes if int(r.get("is_completed", 0)) == 1
    )
    total_boxes = len(cycle_boxes)

    # 현재 박스 hi/lo (정규화 비율값)
    box_hi = float(active_row.get("hi") or 0.0)
    box_lo = float(active_row.get("lo") or 0.0)

    return {
        "cycle_number": cycle_number,
        "phase": phase,
        "box_hi": box_hi,
        "box_lo": box_lo,
        "completed_boxes": completed_boxes,
        "total_boxes": total_boxes,
        "active_row": active_row,
        "cycle_boxes": cycle_boxes,
    }


def _get_latest_close_rate(sb: Any, cycle_number: int) -> float:
    """alt_cycle_data에서 해당 사이클의 가장 최근 close_rate 조회."""
    rows = fetch_all_rows(
        sb.table("alt_cycle_data")
        .select("close_rate, days_since_peak")
        .eq("coin_id", BTC_COIN_ID)
        .eq("cycle_number", cycle_number)
        .order("days_since_peak", desc=True)
        .limit(1)
    )
    if not rows:
        return 50.0
    return float(rows[0].get("close_rate") or 50.0)


def _get_prediction_target(sb: Any, cycle_number: int, phase: str) -> float:
    """coin_analysis_results에서 예측 박스의 hi(Bear)/lo(Bull) 값 조회."""
    pred_rows = fetch_all_rows(
        sb.table("coin_analysis_results")
        .select("hi, lo")
        .eq("coin_id", BTC_COIN_ID)
        .eq("cycle_number", cycle_number)
        .eq("phase", phase)
        .eq("is_prediction", 1)
        .order("box_index")
        .limit(1)
    )
    if not pred_rows:
        return 0.0

    row = pred_rows[0]
    if phase == "BEAR":
        return float(row.get("lo") or 0.0)
    else:
        return float(row.get("hi") or 0.0)


def _build_df_from_rows(cycle_boxes: list[dict]):
    """coin_analysis_results rows → btc_signal_adapter가 요구하는 형태의 DataFrame 생성."""
    try:
        import pandas as pd

        records = []
        for r in cycle_boxes:
            records.append({
                "cycle_number": r.get("cycle_number"),
                "phase": r.get("phase"),
                "is_completed": r.get("is_completed", 0),
                "is_prediction": r.get("is_prediction", 0),
                "hi": r.get("hi"),
                "lo": r.get("lo"),
                "box_index": r.get("box_index", 0),
            })
        return pd.DataFrame(records)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/btc-signal", response_model=BtcSignalResponse)
def btc_signal() -> BtcSignalResponse:
    """BTC 투자 신호 — ACCUMULATE/WATCH/CAUTION/EXIT 4단계 신호 반환.

    Supabase에서 현재 사이클 박스 데이터를 조회하고
    btc_investment_pipeline()을 실행하여 신호를 생성한다.
    """
    try:
        from lib.predictor.btc_signal_api import btc_investment_pipeline

        sb = get_supabase()
        info = _get_current_cycle_info(sb)

        if not info:
            raise HTTPException(status_code=404, detail="BTC 사이클 데이터가 없습니다")

        cycle_number = info["cycle_number"]
        phase = info["phase"]
        box_hi = info["box_hi"]
        box_lo = info["box_lo"]
        completed_boxes = info["completed_boxes"]
        total_boxes = info["total_boxes"]
        cycle_boxes = info["cycle_boxes"]

        # 현재 가격 위치 (close_rate)
        current_price_pct = _get_latest_close_rate(sb, cycle_number)

        # 예측 목표가
        target_price_pct = _get_prediction_target(sb, cycle_number, phase)
        if target_price_pct == 0.0:
            # 예측 없으면 박스 중간값 사용
            target_price_pct = (box_hi + box_lo) / 2.0

        # DataFrame 구성
        df = _build_df_from_rows(cycle_boxes)
        if df is None:
            raise HTTPException(status_code=500, detail="DataFrame 구성 실패")

        # 파이프라인 실행
        result = btc_investment_pipeline(
            df=df,
            cycle_number=cycle_number,
            phase=phase,
            current_price_pct=float(current_price_pct),
            box_lo=float(box_lo),
            box_hi=float(box_hi),
            target_price_pct=float(target_price_pct),
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        # 응답 조립
        sig = result.get("signal", {})
        disp = result.get("display", {})
        desc = result.get("description", {})
        val = result.get("validation", {})
        cp = result.get("cycle_position", {})

        cycle_pos = None
        if cp:
            cycle_pos = CyclePositionInfo(
                completed_boxes=cp.get("completed_boxes", completed_boxes),
                total_boxes=cp.get("total_boxes", total_boxes),
                box_progress=float(cp.get("box_progress", 0.0)),
                price_position=float(cp.get("price_position", 0.0)),
                is_near_target=bool(cp.get("is_near_target", False)),
                phase=phase,
                cycle_number=cycle_number,
            )

        # reason 필드 타입 안전 처리 (list일 수도 있음)
        raw_reason = sig.get("reason")
        if isinstance(raw_reason, list):
            raw_reason = "; ".join(str(r) for r in raw_reason)
        elif raw_reason is not None:
            raw_reason = str(raw_reason)

        return BtcSignalResponse(
            symbol="BTC",
            cycle_number=cycle_number,
            phase=phase,
            signal=SignalInfo(
                signal=sig.get("signal", "WATCH"),
                phase=sig.get("phase", phase),
                confidence=float(sig.get("confidence", 0.5)),
                reason=raw_reason,
            ),
            display=SignalDisplay(
                label=disp.get("label", "WATCH"),
                color=disp.get("color", "#636e72"),
                icon=disp.get("icon", "👁"),
            ),
            description=SignalDescription(
                stage=int(desc.get("stage", 0)),
                stage_name=desc.get("stage_name"),
                signal=desc.get("signal", "WATCH"),
                action=desc.get("action"),
                message_ko=desc.get("message_ko", ""),
                message_en=desc.get("message_en"),
            ),
            cycle_position=cycle_pos,
            validation=ValidationInfo(
                is_valid=bool(val.get("is_valid", True)),
                errors=val.get("errors", []),
                warnings=val.get("warnings", []),
            ),
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/dashboard-summary", response_model=DashboardSummaryResponse)
def dashboard_summary() -> DashboardSummaryResponse:
    """대시보드 상단 요약 카드 데이터 반환.

    BTC 현재 사이클의 가격 범위(고점, 저점) 및 현재가,
    다음 예측가, 투자 신호 등을 계산하여 반환한다.
    """
    try:
        sb = get_supabase()

        # 1. 현재 사이클 정보 가져오기
        info = _get_current_cycle_info(sb)
        if not info:
            raise HTTPException(status_code=404, detail="BTC 사이클 데이터가 없습니다")

        cycle_number = info["cycle_number"]
        phase = info["phase"]

        # 2. alt_cycle_summary에서 peak_price 및 peak_date 조회
        summary_rows = fetch_all_rows(
            sb.table("alt_cycle_summary")
            .select("peak_price, peak_date")
            .eq("coin_id", BTC_COIN_ID)
            .eq("cycle_number", cycle_number)
        )
        if not summary_rows:
            raise HTTPException(status_code=404, detail=f"BTC Cycle {cycle_number} 요약 정보가 없습니다")

        summary_data = summary_rows[0]
        high_price = float(summary_data.get("peak_price") or 0.0)
        peak_date_str = summary_data.get("peak_date")

        # 3. ohlcv 테이블에서 현재 가격(가장 최근 종가) 조회
        ohlcv_rows = fetch_all_rows(
            sb.table("ohlcv")
            .select("close, date")
            .eq("coin_id", BTC_COIN_ID)
            .order("date", desc=True)
            .limit(1)
        )
        if not ohlcv_rows:
            raise HTTPException(status_code=404, detail="BTC 현재 가격 정보가 없습니다")

        current_price = float(ohlcv_rows[0].get("close") or 0.0)
        updated_at_date = ohlcv_rows[0].get("date")

        # 4. 해당 사이클 내 최저 가격(lowPrice) 조회
        # peak_date_str 이후의 최저 low 가격을 ohlcv에서 찾는다.
        # 만약 peak_date_str가 없으면 전체 기간 중 최저가를 사용한다.
        if peak_date_str:
            low_rows = fetch_all_rows(
                sb.table("ohlcv")
                .select("low")
                .eq("coin_id", BTC_COIN_ID)
                .gte("date", peak_date_str)
                .order("low")
                .limit(1)
            )
        else:
            low_rows = fetch_all_rows(
                sb.table("ohlcv")
                .select("low")
                .eq("coin_id", BTC_COIN_ID)
                .order("low")
                .limit(1)
            )

        if low_rows:
            low_price = float(low_rows[0].get("low") or 0.0)
        else:
            low_price = 0.0

        # 5. positionPercent 계산: (currentPrice - lowPrice) / (highPrice - lowPrice) * 100
        denom = (high_price - low_price)
        if denom > 0:
            position_percent = ((current_price - low_price) / denom) * 100.0
        else:
            position_percent = 0.0

        # 6. 신호 구하기
        # btc_signal()과 동일한 로직으로 파이프라인 실행
        box_hi = info["box_hi"]
        box_lo = info["box_lo"]
        cycle_boxes = info["cycle_boxes"]

        current_price_pct = _get_latest_close_rate(sb, cycle_number)
        target_price_pct = _get_prediction_target(sb, cycle_number, phase)
        if target_price_pct == 0.0:
            target_price_pct = (box_hi + box_lo) / 2.0

        df = _build_df_from_rows(cycle_boxes)
        if df is None:
            raise HTTPException(status_code=500, detail="DataFrame 구성 실패")

        from lib.predictor.btc_signal_api import btc_investment_pipeline
        result = btc_investment_pipeline(
            df=df,
            cycle_number=cycle_number,
            phase=phase,
            current_price_pct=float(current_price_pct),
            box_lo=float(box_lo),
            box_hi=float(box_hi),
            target_price_pct=float(target_price_pct),
        )

        sig_data = result.get("signal", {})
        signal_str = sig_data.get("signal", "WATCH")

        # 7. nextPredictedPrice 계산: peak_price * (target_price_pct / 100.0)
        next_predicted_price = high_price * (target_price_pct / 100.0)

        # 8. updatedAt 생성 (ISO 8601 형식)
        if updated_at_date:
            updated_at_str = f"{updated_at_date}T00:00:00Z"
        else:
            from datetime import datetime, timezone
            updated_at_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        return DashboardSummaryResponse(
            cycleNumber=cycle_number,
            currentPrice=round(current_price, 2),
            highPrice=round(high_price, 2),
            lowPrice=round(low_price, 2),
            positionPercent=round(position_percent, 1),
            signal=signal_str,
            nextPredictedPrice=round(next_predicted_price, 2),
            updatedAt=updated_at_str,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
