"""Iters 51-55: SignalHistory 고급 기능 테스트."""

import unittest
from lib.predictor.btc_signal_history import SignalHistory, SignalHistoryEntry


def _e(signal, phase="BEAR", cy=5, prog=0.7, conf=0.8):
    return SignalHistoryEntry(
        signal=signal, phase=phase, confidence=conf,
        stage=3, cycle_number=cy, box_progress_ratio=prog,
    )


class TestSignalHistoryAdvanced(unittest.TestCase):

    def test_max_size_enforced(self):
        """max_size=3이면 4번째 추가 시 첫 번째 제거."""
        h = SignalHistory(max_size=3)
        for s in ["WATCH", "ACCUMULATE", "WATCH", "EXIT"]:
            h.append(_e(s))
        self.assertEqual(len(h), 3)
        self.assertEqual(h.latest().signal, "EXIT")

    def test_signal_distribution_counts(self):
        h = SignalHistory()
        for s in ["WATCH", "WATCH", "ACCUMULATE", "EXIT", "WATCH"]:
            h.append(_e(s))
        dist = h.signal_distribution()
        self.assertEqual(dist["WATCH"], 3)
        self.assertEqual(dist["ACCUMULATE"], 1)
        self.assertEqual(dist["EXIT"], 1)

    def test_recent_n_order(self):
        """recent(3)는 최신순(역순)으로 반환."""
        h = SignalHistory()
        for s in ["WATCH", "ACCUMULATE", "EXIT"]:
            h.append(_e(s))
        recent = h.recent(3)
        self.assertEqual(recent[0].signal, "EXIT")
        self.assertEqual(recent[-1].signal, "WATCH")

    def test_clear_resets_all(self):
        h = SignalHistory()
        for _ in range(5):
            h.append(_e("WATCH"))
        h.clear()
        self.assertEqual(len(h), 0)
        self.assertIsNone(h.latest())

    def test_consecutive_count_after_clear(self):
        h = SignalHistory()
        for _ in range(3):
            h.append(_e("ACCUMULATE"))
        h.clear()
        self.assertEqual(h.consecutive_count(), 0)

    def test_get_scorer_params_after_mixed(self):
        h = SignalHistory()
        h.append(_e("WATCH"))
        h.append(_e("ACCUMULATE"))
        h.append(_e("ACCUMULATE"))
        p = h.get_scorer_params()
        self.assertEqual(p["consecutive_count"], 2)
        self.assertFalse(p["is_signal_changed"])

    def test_is_signal_changed_false_same(self):
        h = SignalHistory()
        h.append(_e("WATCH"))
        h.append(_e("WATCH"))
        self.assertFalse(h.is_signal_changed())

    def test_is_signal_changed_true_different(self):
        h = SignalHistory()
        h.append(_e("WATCH"))
        h.append(_e("EXIT"))
        self.assertTrue(h.is_signal_changed())

    def test_latest_confidence_retrieved(self):
        h = SignalHistory()
        h.append(_e("ACCUMULATE", conf=0.91))
        self.assertAlmostEqual(h.latest().confidence, 0.91)

    def test_distribution_empty(self):
        h = SignalHistory()
        self.assertEqual(h.signal_distribution(), {})


if __name__ == "__main__":
    unittest.main()
