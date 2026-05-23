"""Unit tests for predict_paths DB-dependent functions using mock DB.

DevLoop Iteration 3 — DB 의존 함수 mock 테스트
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from lib.predictor.predict_paths import _load_bottom_predictions


def _make_mock_conn(rows):
    """mock conn.execute(...).fetchall() 패턴 헬퍼."""
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows
    mock_conn = MagicMock()
    mock_conn.execute.return_value = mock_cursor
    return mock_conn


class TestLoadBottomPredictions(unittest.TestCase):

    def test_empty_db_returns_empty_dict(self):
        """DB에 결과가 없으면 빈 dict 반환."""
        conn = _make_mock_conn([])
        result = _load_bottom_predictions(conn)
        self.assertEqual(result, {})

    def test_single_row_int_coin_id(self):
        """정수 coin_id 단일 행 → (int_id, cycle) 키로 저장."""
        conn = _make_mock_conn([(1, 2, 300, 45000.0)])
        result = _load_bottom_predictions(conn)
        self.assertIn((1, 2), result)
        day, val = result[(1, 2)]
        self.assertEqual(day, 300)
        self.assertAlmostEqual(val, 45000.0)

    def test_string_coin_id_non_numeric(self):
        """문자열 coin_id (숫자 변환 불가) → str 키로 저장."""
        conn = _make_mock_conn([("abc", 1, 100, 30000.0)])
        result = _load_bottom_predictions(conn)
        self.assertIn(("abc", 1), result)

    def test_string_coin_id_numeric(self):
        """숫자형 문자열 coin_id → int 변환 후 키로 저장."""
        conn = _make_mock_conn([("42", 3, 200, 55000.0)])
        result = _load_bottom_predictions(conn)
        self.assertIn((42, 3), result)

    def test_none_coin_id_defaults_to_zero(self):
        """coin_id=None → 0으로 정규화."""
        conn = _make_mock_conn([(None, 1, 150, 20000.0)])
        result = _load_bottom_predictions(conn)
        self.assertIn((0, 1), result)

    def test_none_cycle_defaults_to_zero(self):
        """cycle_number=None → 0으로 정규화."""
        conn = _make_mock_conn([(5, None, 100, 10000.0)])
        result = _load_bottom_predictions(conn)
        self.assertIn((5, 0), result)

    def test_multiple_rows_all_stored(self):
        """복수 행이 모두 dict에 저장되어야 한다."""
        rows = [
            (1, 1, 100, 10000.0),
            (2, 1, 200, 20000.0),
            (3, 2, 300, 30000.0),
        ]
        conn = _make_mock_conn(rows)
        result = _load_bottom_predictions(conn)
        self.assertEqual(len(result), 3)
        self.assertIn((1, 1), result)
        self.assertIn((2, 1), result)
        self.assertIn((3, 2), result)

    def test_db_exception_returns_empty_dict(self):
        """DB 접근 예외 발생 시 빈 dict 반환 (방어 로직)."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("DB connection error")
        result = _load_bottom_predictions(mock_conn)
        self.assertEqual(result, {})

    def test_return_tuple_is_int_float(self):
        """반환 dict 값이 (int, float) 튜플이어야 한다."""
        conn = _make_mock_conn([(10, 2, 500, 99999.99)])
        result = _load_bottom_predictions(conn)
        day, val = result[(10, 2)]
        self.assertIsInstance(day, int)
        self.assertIsInstance(val, float)

    def test_later_row_overwrites_same_key(self):
        """동일 (coin_id, cycle) 중복 시 마지막 행으로 덮어쓰기."""
        rows = [
            (1, 1, 100, 10000.0),
            (1, 1, 200, 20000.0),  # 같은 키, 나중 값
        ]
        conn = _make_mock_conn(rows)
        result = _load_bottom_predictions(conn)
        day, _ = result[(1, 1)]
        self.assertEqual(day, 200)  # 마지막 행의 값


if __name__ == "__main__":
    unittest.main()
