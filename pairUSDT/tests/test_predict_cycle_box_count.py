"""BTC 사이클 Bear/Bull 박스 수 예측 로직 테스트."""

import pytest

from lib.predictor.predict_cycle_box_count import (
    get_btc_completed_cycle_box_counts,
    get_completed_cycle_box_counts,
    predict_cycle_box_counts,
    _linear_regression_predict,
    _apply_guards,
    METHOD_LINEAR_REGRESSION,
)
from lib.common.config import MIN_BOX_COUNT, BEAR_GUARD_DELTA


SPEC_COUNTS = [(1, 4, 3), (2, 3, 5), (3, 4, 6), (4, 7, 7)]


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_args, **_kwargs):
        return _FakeCursor(self._rows)


class TestGetCounts:
    def test_btc_counts_aggregation(self):
        conn = _FakeConn(SPEC_COUNTS)
        counts = get_btc_completed_cycle_box_counts(conn)
        assert [c[1] for c in counts] == [4, 3, 4, 7]
        assert [c[2] for c in counts] == [3, 5, 6, 7]

    def test_coin_counts_aggregation(self):
        conn = _FakeConn(SPEC_COUNTS)
        counts = get_completed_cycle_box_counts(conn, coin_id=1)
        assert counts == SPEC_COUNTS


class TestLinearRegression:
    def test_bear_prediction_positive(self):
        pred = _linear_regression_predict([(1, 4), (2, 3), (3, 4), (4, 7)], 5)
        assert pred > 0

    def test_bull_prediction_ge_7(self):
        pred = _linear_regression_predict([(1, 3), (2, 5), (3, 6), (4, 7)], 5)
        assert pred >= 7 or round(pred) >= 7

    def test_two_points(self):
        pred = _linear_regression_predict([(1, 2), (2, 4)], 3)
        assert pred == pytest.approx(6.0)

    def test_one_point_returns_zero(self):
        assert _linear_regression_predict([(1, 5)], 2) == 0.0


class TestGuards:
    def test_bear_guard(self):
        bear_count, bull_count, _, _ = _apply_guards(5.0, 8.0, 7, 6)
        assert bear_count >= 7 - BEAR_GUARD_DELTA
        assert bull_count >= MIN_BOX_COUNT

    def test_bull_guard(self):
        _, bull_count, _, _ = _apply_guards(7.5, 4.0, 7, 6)
        assert bull_count >= 6


class TestPredictCycleBoxCounts:
    def test_empty_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            "lib.predictor.predict_cycle_box_count.get_btc_completed_cycle_box_counts",
            lambda _conn: [],
        )
        assert predict_cycle_box_counts(None, 5) is None

    def test_single_cycle_returns_none(self, monkeypatch):
        monkeypatch.setattr(
            "lib.predictor.predict_cycle_box_count.get_btc_completed_cycle_box_counts",
            lambda _conn: [(1, 4, 3)],
        )
        assert predict_cycle_box_counts(None, 2) is None

    def test_prediction_structure_cycle5(self, monkeypatch):
        monkeypatch.setattr(
            "lib.predictor.predict_cycle_box_count.get_btc_completed_cycle_box_counts",
            lambda _conn: SPEC_COUNTS,
        )
        result = predict_cycle_box_counts(None, 5)
        assert result is not None
        assert result.cycle_number == 5
        assert result.method == METHOD_LINEAR_REGRESSION
        assert isinstance(result.bear_count, int)
        assert isinstance(result.bull_count, int)
        assert result.bear_count >= MIN_BOX_COUNT
        assert result.bull_count >= MIN_BOX_COUNT
        assert "bear" in result.guard_applied
        assert "bull" in result.guard_applied

    def test_prediction_cycle6_uses_prev_cycle(self, monkeypatch):
        monkeypatch.setattr(
            "lib.predictor.predict_cycle_box_count.get_btc_completed_cycle_box_counts",
            lambda _conn: SPEC_COUNTS,
        )
        result5 = predict_cycle_box_counts(None, 5)
        result6 = predict_cycle_box_counts(None, 6)
        assert result5 is not None and result6 is not None
        assert result6.bear_count >= result5.bear_count - BEAR_GUARD_DELTA
        assert result6.bull_count >= result5.bull_count
