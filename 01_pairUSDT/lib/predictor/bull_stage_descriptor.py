"""Bull 사이클 단계(Stage) 판별 및 투자 메시지 생성.

BTC Bull 사이클을 4단계로 구분하여 각 단계에 맞는
투자 가이드 메시지를 생성한다.

Stage 정의 (box_progress_ratio 기준):
    Stage 1 (0~25%):  Bull 초입 — 포지션 유지, 상승 시작
    Stage 2 (25~55%): Bull 중반 — 수익 실현 일부 시작
    Stage 3 (55~80%): Bull 후반 — 비중 축소, CAUTION
    Stage 4 (80%+):   Bull 말기 — 정점 임박, EXIT 준비

주요 함수:
    classify_bull_stage  — box_progress → Stage 번호 (1~4)
    get_bull_stage_info  — Stage 메타데이터 반환
    describe_bull_signal — SignalResult + Stage → 풍부한 투자 메시지
"""

from __future__ import annotations

from dataclasses import dataclass

STAGE_BOUNDARIES = [0.0, 0.25, 0.55, 0.80, float("inf")]

STAGE_INFO = {
    1: {
        "name": "Bull 초입",
        "action": "포지션 유지",
        "message_ko": "Bull 사이클 초입입니다. Bear에서 축적한 포지션을 유지하고 추가 상승을 기다리세요.",
        "message_en": "Early Bull phase. Hold positions accumulated in Bear. Wait for further rally.",
        "color": "#74b9ff",
        "emoji": "🚀",
    },
    2: {
        "name": "Bull 중반",
        "action": "일부 수익 실현",
        "message_ko": "Bull 중반입니다. 전체 포지션의 20~30%를 수익 실현하여 현금 비중을 높이세요.",
        "message_en": "Mid Bull phase. Take partial profits (20-30%) and increase cash.",
        "color": "#a29bfe",
        "emoji": "💰",
    },
    3: {
        "name": "Bull 후반",
        "action": "비중 축소",
        "message_ko": "Bull 후반입니다. 고점 임박 가능성이 있습니다. 50~70%까지 비중을 축소하세요.",
        "message_en": "Late Bull phase. Peak approaching. Reduce to 30-50% exposure.",
        "color": "#e17055",
        "emoji": "⚠️",
    },
    4: {
        "name": "Bull 말기",
        "action": "매도 준비",
        "message_ko": "Bull 말기입니다. 역사적 정점 패턴에 근접했습니다. 80~100% 매도를 준비하세요.",
        "message_en": "End of Bull cycle. Near historical peak. Prepare to exit 80-100%.",
        "color": "#d63031",
        "emoji": "📉",
    },
}


@dataclass
class BullStageInfo:
    """Bull 사이클 단계 정보."""
    stage: int
    name: str
    action: str
    message_ko: str
    message_en: str
    color: str
    emoji: str
    box_progress_ratio: float


def classify_bull_stage(box_progress_ratio: float) -> int:
    """box_progress_ratio → Stage 번호 (1~4).

    Returns:
        1, 2, 3, 4 중 하나
    """
    progress = max(0.0, box_progress_ratio)
    for stage, (lo, hi) in enumerate(
        zip(STAGE_BOUNDARIES[:-1], STAGE_BOUNDARIES[1:]), start=1
    ):
        if progress < hi:
            return stage
    return 4


def get_bull_stage_info(box_progress_ratio: float) -> BullStageInfo:
    """Stage 메타데이터 반환."""
    stage = classify_bull_stage(box_progress_ratio)
    info = STAGE_INFO[stage]
    return BullStageInfo(
        stage=stage,
        box_progress_ratio=box_progress_ratio,
        **{k: v for k, v in info.items()},
    )


def describe_bull_signal(signal_result, box_progress_ratio: float) -> dict:
    """SignalResult + Stage → 풍부한 투자 설명 반환."""
    stage_info = get_bull_stage_info(box_progress_ratio)
    return {
        "stage": stage_info.stage,
        "stage_name": stage_info.name,
        "signal": signal_result.signal if signal_result else "WATCH",
        "action": stage_info.action,
        "message_ko": stage_info.message_ko,
        "message_en": stage_info.message_en,
        "confidence": round(float(signal_result.confidence), 4) if signal_result else 0.0,
        "color": stage_info.color,
        "emoji": stage_info.emoji,
        "reason": list(signal_result.reason) if signal_result else [],
        "box_progress_ratio": round(box_progress_ratio, 4),
    }


def format_stage_label(box_progress_ratio: float) -> str:
    """Bull 단계를 단일 짧은 레이블로 반환 (UI용).

    Returns:
        예: "[Bull Stage 3] Bull 후반 — 비중 축소 (68%)"
    """
    info = get_bull_stage_info(box_progress_ratio)
    pct = int(round(box_progress_ratio * 100))
    return f"[Bull Stage {info.stage}] {info.name} — {info.action} ({pct}%)"

