"""Tests for btc_signal_history.py — Iteration 23."""

import unittest

from lib.predictor.btc_signal_history import SignalHistory, SignalHistoryEntry


def _make_entry(signal="ACCUMULATE", phase="BEAR", confidence=0.8,
                stage=3, cycle=5, progress=0.7):
    return SignalHistoryEntry(
        signal=signal, phase=phase, confidence=confidence,
        stage=stage, cycle_number=cycle, box_progress_ratio=progress,
    )


class TestSignalHistory(unittest.TestCase):

    def setUp(self):
        self.hist = SignalHistory(max_size=5)

    def test_initially_empty(self):
        self.assertEqual(len(self.hist), 0)

    def test_append_increases_length(self):
        self.hist.append(_make_entry())
        self.assertEqual(len(self.hist), 1)

    def test_max_size_eviction(self):
        """max_size 초과 시 오래된 항목 제거."""
        for i in range(7):
            self.hist.append(_make_entry(signal=["ACCUMULATE", "WATCH"][i % 2]))
        self.assertEqual(len(self.hist), 5)

    def test_latest_returns_most_recent(self):
        self.hist.append(_make_entry(signal="WATCH"))
        self.hist.append(_make_entry(signal="ACCUMULATE"))
        self.assertEqual(self.hist.latest().signal, "ACCUMULATE")

    def test_latest_none_when_empty(self):
        self.assertIsNone(self.hist.latest())

    def test_recent_returns_n_items(self):
        for s in ["WATCH", "ACCUMULATE", "CAUTION"]:
            self.hist.append(_make_entry(signal=s))
        recent = self.hist.recent(2)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0].signal, "CAUTION")  # 최신순

    def test_is_signal_changed_true(self):
        self.hist.append(_make_entry(signal="WATCH"))
        self.hist.append(_make_entry(signal="ACCUMULATE"))
        self.assertTrue(self.hist.is_signal_changed())

    def test_is_signal_changed_false(self):
        self.hist.append(_make_entry(signal="ACCUMULATE"))
        self.hist.append(_make_entry(signal="ACCUMULATE"))
        self.assertFalse(self.hist.is_signal_changed())

    def test_is_signal_changed_false_when_too_few(self):
        self.hist.append(_make_entry())
        self.assertFalse(self.hist.is_signal_changed())

    def test_consecutive_count_single(self):
        self.hist.append(_make_entry(signal="ACCUMULATE"))
        self.assertEqual(self.hist.consecutive_count(), 1)

    def test_consecutive_count_multiple(self):
        for _ in range(3):
            self.hist.append(_make_entry(signal="ACCUMULATE"))
        self.assertEqual(self.hist.consecutive_count(), 3)

    def test_consecutive_count_resets_on_change(self):
        self.hist.append(_make_entry(signal="WATCH"))
        self.hist.append(_make_entry(signal="ACCUMULATE"))
        self.hist.append(_make_entry(signal="ACCUMULATE"))
        self.assertEqual(self.hist.consecutive_count(), 2)

    def test_consecutive_count_zero_when_empty(self):
        self.assertEqual(self.hist.consecutive_count(), 0)

    def test_signal_distribution(self):
        for s in ["ACCUMULATE", "WATCH", "ACCUMULATE", "EXIT"]:
            self.hist.append(_make_entry(signal=s))
        dist = self.hist.signal_distribution()
        self.assertEqual(dist["ACCUMULATE"], 2)
        self.assertEqual(dist["WATCH"], 1)
        self.assertEqual(dist["EXIT"], 1)

    def test_clear_empties_history(self):
        self.hist.append(_make_entry())
        self.hist.clear()
        self.assertEqual(len(self.hist), 0)

    def test_invalid_max_size_raises(self):
        with self.assertRaises(ValueError):
            SignalHistory(max_size=0)

    def test_entry_has_timestamp(self):
        entry = _make_entry()
        self.assertIsNotNone(entry.timestamp)
        self.assertIn("T", entry.timestamp)  # ISO 형식 확인


if __name__ == "__main__":
    unittest.main()
