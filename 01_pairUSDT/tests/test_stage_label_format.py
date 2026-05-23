"""Iter 39+40: bear/bull format_stage_label 테스트."""

import unittest
from lib.predictor.bear_stage_descriptor import (
    format_stage_label as bear_label, classify_bear_stage,
)
from lib.predictor.bull_stage_descriptor import (
    format_stage_label as bull_label, classify_bull_stage,
)


class TestBearFormatStageLabel(unittest.TestCase):

    def test_returns_string(self):
        self.assertIsInstance(bear_label(0.7), str)

    def test_stage_1_in_label(self):
        lbl = bear_label(0.1)
        self.assertIn("Stage 1", lbl)
        self.assertIn("Bear", lbl)

    def test_stage_4_in_label(self):
        lbl = bear_label(0.9)
        self.assertIn("Stage 4", lbl)

    def test_pct_in_label(self):
        lbl = bear_label(0.62)
        self.assertIn("62%", lbl)

    def test_boundary_zero(self):
        lbl = bear_label(0.0)
        self.assertIn("Stage 1", lbl)

    def test_over_one_is_stage_4(self):
        lbl = bear_label(1.2)
        self.assertIn("Stage 4", lbl)

    def test_format_matches_classify(self):
        for prog in [0.1, 0.4, 0.7, 0.9]:
            stage = classify_bear_stage(prog)
            lbl = bear_label(prog)
            self.assertIn(f"Stage {stage}", lbl)


class TestBullFormatStageLabel(unittest.TestCase):

    def test_returns_string(self):
        self.assertIsInstance(bull_label(0.5), str)

    def test_stage_1_in_label(self):
        lbl = bull_label(0.1)
        self.assertIn("Stage 1", lbl)
        self.assertIn("Bull", lbl)

    def test_stage_4_in_label(self):
        lbl = bull_label(0.85)
        self.assertIn("Stage 4", lbl)

    def test_pct_in_label(self):
        lbl = bull_label(0.68)
        self.assertIn("68%", lbl)

    def test_boundary_zero_bull(self):
        lbl = bull_label(0.0)
        self.assertIn("Stage 1", lbl)

    def test_over_one_is_stage_4_bull(self):
        lbl = bull_label(1.1)
        self.assertIn("Stage 4", lbl)

    def test_format_matches_classify_bull(self):
        for prog in [0.1, 0.3, 0.6, 0.85]:
            stage = classify_bull_stage(prog)
            lbl = bull_label(prog)
            self.assertIn(f"Stage {stage}", lbl)


if __name__ == "__main__":
    unittest.main()
