"""SignalHistory.get_scorer_params 테스트 — Iteration 33."""

import unittest
from lib.predictor.btc_signal_history import SignalHistory, SignalHistoryEntry


def _entry(signal, phase="BEAR", cy=5, prog=0.7):
    return SignalHistoryEntry(
        signal=signal, phase=phase, confidence=0.8,
        stage=3, cycle_number=cy, box_progress_ratio=prog,
    )


class TestGetScorerParams(unittest.TestCase):

    def test_empty_history_returns_defaults(self):
        h = SignalHistory()
        p = h.get_scorer_params()
        self.assertEqual(p["consecutive_count"], 1)
        self.assertFalse(p["is_signal_changed"])

    def test_single_entry_count_one(self):
        h = SignalHistory()
        h.append(_entry("WATCH"))
        p = h.get_scorer_params()
        self.assertEqual(p["consecutive_count"], 1)
        self.assertFalse(p["is_signal_changed"])

    def test_consecutive_signals_counted(self):
        h = SignalHistory()
        for _ in range(4):
            h.append(_entry("ACCUMULATE"))
        p = h.get_scorer_params()
        self.assertEqual(p["consecutive_count"], 4)
        self.assertFalse(p["is_signal_changed"])

    def test_signal_change_detected(self):
        h = SignalHistory()
        h.append(_entry("WATCH"))
        h.append(_entry("ACCUMULATE"))
        p = h.get_scorer_params()
        self.assertTrue(p["is_signal_changed"])
        self.assertEqual(p["consecutive_count"], 1)

    def test_consecutive_count_minimum_one(self):
        """빈 히스토리에서도 consecutive_count >= 1 보장."""
        h = SignalHistory()
        p = h.get_scorer_params()
        self.assertGreaterEqual(p["consecutive_count"], 1)

    def test_mixed_then_stable(self):
        h = SignalHistory()
        h.append(_entry("WATCH"))
        h.append(_entry("ACCUMULATE"))
        h.append(_entry("ACCUMULATE"))
        h.append(_entry("ACCUMULATE"))
        p = h.get_scorer_params()
        self.assertEqual(p["consecutive_count"], 3)
        self.assertFalse(p["is_signal_changed"])

    def test_returns_dict_keys(self):
        h = SignalHistory()
        h.append(_entry("EXIT"))
        p = h.get_scorer_params()
        self.assertIn("consecutive_count", p)
        self.assertIn("is_signal_changed", p)

    def test_is_signal_changed_is_bool(self):
        h = SignalHistory()
        h.append(_entry("CAUTION"))
        p = h.get_scorer_params()
        self.assertIsInstance(p["is_signal_changed"], bool)

    def test_count_is_int(self):
        h = SignalHistory()
        h.append(_entry("WATCH"))
        p = h.get_scorer_params()
        self.assertIsInstance(p["consecutive_count"], int)


if __name__ == "__main__":
    unittest.main()
