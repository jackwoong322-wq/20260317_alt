"""Bear cycle pattern matching.

마지막 완료 Bear 박스와 전 사이클 Bear 박스 간 유사도 비교 → 매핑 오프셋 반환.

유사도 가중치:
  decline_intensity 50% / rise_rate 30% / duration 20%
"""

import logging
import math

log = logging.getLogger(__name__)

# 유사도 가중치
_W_DECLINE = 0.5
_W_RISE    = 0.3
_W_DUR     = 0.2


def _similarity(cur: dict, ref: dict) -> float:
    """두 박스 간 유사도 점수 (0~1, 높을수록 유사)."""
    scores = []

    # decline_intensity
    c_di = cur.get("decline_intensity")
    r_di = ref.get("decline_intensity")
    if c_di is not None and r_di is not None and (c_di > 0 or r_di > 0):
        denom = max(abs(c_di), abs(r_di), 1e-6)
        scores.append((_W_DECLINE, 1.0 - min(abs(c_di - r_di) / denom, 1.0)))
    else:
        scores.append((_W_DECLINE, 0.5))  # 데이터 없으면 중립

    # rise_rate
    c_rr = cur.get("rise_rate")
    r_rr = ref.get("rise_rate")
    if c_rr is not None and r_rr is not None:
        denom = max(abs(c_rr), abs(r_rr), 1e-6)
        scores.append((_W_RISE, 1.0 - min(abs(c_rr - r_rr) / denom, 1.0)))
    else:
        scores.append((_W_RISE, 0.5))

    # duration (log 스케일 차이)
    c_d = cur.get("duration")
    r_d = ref.get("duration")
    if c_d and r_d:
        diff = abs(math.log1p(c_d) - math.log1p(r_d))
        scores.append((_W_DUR, 1.0 - min(diff / math.log1p(max(c_d, r_d)), 1.0)))
    else:
        scores.append((_W_DUR, 0.5))

    total_w = sum(w for w, _ in scores)
    return sum(w * s for w, s in scores) / total_w if total_w > 0 else 0.0


def match_bear_pattern(
    current_boxes: list[dict],
    ref_boxes: list[dict],
) -> tuple[int, float]:
    """마지막 완료 Bear 박스와 가장 유사한 ref 박스를 찾아 오프셋 반환.

    Args:
        current_boxes: 현재 사이클 완료된 Bear 박스 목록 (box_index 순)
        ref_boxes:     전 사이클 Bear 박스 목록 (box_index 순)

    Returns:
        (offset, score)
        offset: ref_boxes에서 매핑된 박스 다음 인덱스 (ref[offset:]부터 사용)
        score:  매핑 유사도 (0~1)

    Fallback:
        완료 박스가 없거나 ref가 비어있으면 단순 카운트 오프셋 반환.
    """
    if not current_boxes or not ref_boxes:
        fallback = len(current_boxes)
        log.info("[BearMatcher] 데이터 없음 → 단순 오프셋 %d", fallback)
        return fallback, 0.0

    last_cur = current_boxes[-1]

    best_idx = 0
    best_score = -1.0
    for i, ref_box in enumerate(ref_boxes):
        score = _similarity(last_cur, ref_box)
        if score > best_score:
            best_score = score
            best_idx = i

    offset = best_idx + 1  # 매핑된 박스 다음부터 남은 구간
    simple_offset = len(current_boxes)

    log.info(
        "[BearMatcher] 마지막완료 box_idx=%s  → ref[%d] 매핑 (유사도=%.3f)  "
        "단순오프셋=%d vs 패턴오프셋=%d",
        last_cur.get("box_index"),
        best_idx,
        best_score,
        simple_offset,
        offset,
    )

    return offset, best_score
