"""Bear 사이클 단계(Stage) 판별 및 투자 메시지 생성.

BTC Bear 사이클을 4단계로 구분하여 각 단계에 맞는
투자 가이드 메시지를 생성한다.

Stage 정의 (box_progress_ratio 기준):
    Stage 1 (0~30%):  Bear 초입 — 추가 하락 가능, 대기
    Stage 2 (30~60%): Bear 중반 — 분할 매수 소규모 시작 가능
    Stage 3 (60~85%): Bear 후반 — 적극 매수 구간
    Stage 4 (85%+):   Bear 말기 — 저점 임박, 최대 비중 진입

주요 함수:
    classify_bear_stage  — box_progress → Stage 번호 (1~4)
    get_bear_stage_info  — Stage 메타데이터 반환
    describe_bear_signal — SignalResult + Stage → 풍부한 투자 메시지
"""

from __future__ import annotations

from dataclasses import dataclass

STAGE_BOUNDARIES = [0.0, 0.30, 0.60, 0.85, float("inf")]

STAGE_INFO = {
    1: {
        "name": "Bear 초입",
        "action": "대기",
        "message_ko": "Bear 사이클 초입입니다. 추가 하락 가능성이 높아 현금 비중을 유지하세요.",
        "message_en": "Early Bear phase. High risk of further decline. Stay in cash.",
        "color": "#e17055",
        "emoji": "⏳",
    },
    2: {
        "name": "Bear 중반",
        "action": "소규모 분할 매수",
        "message_ko": "Bear 중반입니다. 전체 예산의 20~30% 수준으로 분할 매수를 시작할 수 있습니다.",
        "message_en": "Mid Bear phase. Consider 20-30% position sizing with DCA.",
        "color": "#fdcb6e",
        "emoji": "🔎",
    },
    3: {
        "name": "Bear 후반",
        "action": "적극 분할 매수",
        "message_ko": "Bear 후반입니다. 저점권 진입 가능성이 높습니다. 40~60% 비중으로 분할 매수를 진행하세요.",
        "message_en": "Late Bear phase. Likely approaching bottom. Increase DCA to 40-60%.",
        "color": "#00b894",
        "emoji": "📈",
    },
    4: {
        "name": "Bear 말기",
        "action": "최대 비중 진입",
        "message_ko": "Bear 말기입니다. 역사적 저점 패턴에 근접했습니다. 최대 비중(70~80%)으로 진입을 검토하세요.",
        "message_en": "End of Bear cycle. Near historical bottom pattern. Consider 70-80% allocation.",
        "color": "#00cec9",
        "emoji": "🎯",
    },
}


@dataclass
class BearStageInfo:
    """Bear 사이클 단계 정보."""
    stage: int                   # 1~4
    name: str
    action: str
    message_ko: str
    message_en: str
    color: str
    emoji: str
    box_progress_ratio: float    # 입력값 전달


def classify_bear_stage(box_progress_ratio: float) -> int:
    """box_progress_ratio → Stage 번호 (1~4).

    Args:
        box_progress_ratio: 0.0~1.5+ 범위 (1.0 초과 = 평균 초과)

    Returns:
        1, 2, 3, 4 중 하나
    """
    progress = max(0.0, box_progress_ratio)
    for stage, (lo, hi) in enumerate(
        zip(STAGE_BOUNDARIES[:-1], STAGE_BOUNDARIES[1:]), start=1
    ):
        if progress < hi:
            return stage
    return 4  # fallback: 평균 초과 시 Stage 4


def get_bear_stage_info(box_progress_ratio: float) -> BearStageInfo:
    """Stage 메타데이터 반환.

    Args:
        box_progress_ratio: CyclePosition.box_progress_ratio

    Returns:
        BearStageInfo
    """
    stage = classify_bear_stage(box_progress_ratio)
    info = STAGE_INFO[stage]
    return BearStageInfo(
        stage=stage,
        box_progress_ratio=box_progress_ratio,
        **{k: v for k, v in info.items()},
    )


def describe_bear_signal(signal_result, box_progress_ratio: float) -> dict:
    """SignalResult + Stage → 풍부한 투자 설명 반환.

    Args:
        signal_result: btc_investment_signal.SignalResult
        box_progress_ratio: CyclePosition.box_progress_ratio

    Returns:
        {
            "stage": 3,
            "stage_name": "Bear 후반",
            "signal": "ACCUMULATE",
            "action": "적극 분할 매수",
            "message_ko": "...",
            "message_en": "...",
            "confidence": 0.85,
            "color": "#00b894",
            "emoji": "📈",
            "reason": [...],
        }
    """
    stage_info = get_bear_stage_info(box_progress_ratio)
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
    """Bear 단계를 단일 짧은 레이블로 반환 (UI용).

    Returns:
        예: "[Bear Stage 3] Bear 후반 — 적극 분할 매수 (62%)"
    """
    info = get_bear_stage_info(box_progress_ratio)
    pct = int(round(box_progress_ratio * 100))
    return f"[Bear Stage {info.stage}] {info.name} — {info.action} ({pct}%)"
