"""generate_btc_signal에 신뢰도 보정기 통합 테스트.

Iteration 31 — btc_signal_confidence_scorer를 generate_btc_signal에 통합한 후
보정이 실제로 적용되는지 검증.
"""

import unittest

from lib.predictor.btc_cycle_position import CyclePosition
from lib.predictor.btc_investment_signal import generate_btc_signal


def _make_pos(
    phase="BEAR",
    box_progress_ratio=0.7,
    price_position=0.25,
    day_progress_ratio=0.7,
    is_near_target=True,
    distance_to_target_pct=5.0,
    cycle_number=5,
):
    # completed_boxes / avg_boxes_historical → box_progress_ratio 재현
    avg_boxes = 10.0
    completed = round(box_progress_ratio * avg_boxes)
    return CyclePosition(
        phase=phase,
        cycle_number=cycle_number,
        completed_boxes=completed,
        avg_boxes_historical=avg_boxes,
        box_progress_ratio=box_progress_ratio,
        price_position=price_position,
        day_progress_ratio=day_progress_ratio,
        is_near_target=is_near_target,
        distance_to_target_pct=distance_to_target_pct,
    )


class TestGenerateBtcSignalWithScorer(unittest.TestCase):
    """generate_btc_signal이 신뢰도 보정기를 통합했는지 검증."""

    def test_consecutive_bonus_increases_confidence(self):
        """연속 신호(consecutive_count=5)이면 기본 confidence보다 높아야 한다."""
        pos = _make_pos()
        result_base = generate_btc_signal(pos, consecutive_count=1)
        result_consec = generate_btc_signal(pos, consecutive_count=5)
        self.assertGreater(result_consec.confidence, result_base.confidence)

    def test_signal_changed_decreases_confidence(self):
        """신호 변화 직후(is_signal_changed=True)는 기본보다 confidence 낮아야 한다."""
        pos = _make_pos()
        result_base = generate_btc_signal(pos, consecutive_count=1, is_signal_changed=False)
        result_changed = generate_btc_signal(pos, consecutive_count=1, is_signal_changed=True)
        self.assertLess(result_changed.confidence, result_base.confidence)

    def test_near_target_bonus_applied_bear(self):
        """Bear: is_near_target=True는 is_near_target=False보다 confidence가 높아야 한다."""
        pos_near = _make_pos(is_near_target=True)
        pos_far = _make_pos(is_near_target=False)
        result_near = generate_btc_signal(pos_near)
        result_far = generate_btc_signal(pos_far)
        # near_target 보너스(+0.10) 기대
        self.assertGreaterEqual(result_near.confidence, result_far.confidence)

    def test_confidence_clipped_to_one(self):
        """최대 보정 후에도 confidence는 1.0을 초과하지 않아야 한다."""
        pos = _make_pos(box_progress_ratio=1.5, day_progress_ratio=0.95, is_near_target=True)
        result = generate_btc_signal(pos, consecutive_count=10)
        self.assertLessEqual(result.confidence, 1.0)

    def test_confidence_never_negative(self):
        """최소 보정 후에도 confidence는 0.0 이상이어야 한다."""
        pos = _make_pos(box_progress_ratio=0.1, price_position=0.5, is_near_target=False)
        result = generate_btc_signal(pos, consecutive_count=1, is_signal_changed=True)
        self.assertGreaterEqual(result.confidence, 0.0)

    def test_backward_compatible_default_call(self):
        """기존 호출 방식(파라미터 없이)이 여전히 작동해야 한다."""
        pos = _make_pos()
        result = generate_btc_signal(pos)
        self.assertIn(result.signal, ["ACCUMULATE", "WATCH", "CAUTION", "EXIT"])
        self.assertIsInstance(result.confidence, float)

    def test_bull_consecutive_bonus(self):
        """Bull 사이클에서도 연속 신호 보너스가 적용되어야 한다."""
        pos = _make_pos(
            phase="BULL",
            box_progress_ratio=0.85,
            price_position=0.8,
            day_progress_ratio=0.85,
            is_near_target=True,
        )
        result_base = generate_btc_signal(pos, consecutive_count=1)
        result_consec = generate_btc_signal(pos, consecutive_count=4)
        self.assertGreater(result_consec.confidence, result_base.confidence)

    def test_inconsistent_progress_reduces_confidence(self):
        """box_progress와 day_progress 차이가 크면 confidence에 페널티가 적용된다."""
        pos_consistent = _make_pos(box_progress_ratio=0.7, day_progress_ratio=0.7)
        pos_inconsistent = _make_pos(box_progress_ratio=0.7, day_progress_ratio=0.2)
        r_consistent = generate_btc_signal(pos_consistent)
        r_inconsistent = generate_btc_signal(pos_inconsistent)
        self.assertGreaterEqual(r_consistent.confidence, r_inconsistent.confidence)


if __name__ == "__main__":
    unittest.main()
