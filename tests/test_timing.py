from __future__ import annotations

import unittest

from arcaea_rhythm.timing import measure_aligned, valid_bpm, valid_beats_per_measure


class TimingSanityTest(unittest.TestCase):
    def test_bpm(self) -> None:
        self.assertTrue(valid_bpm(200))
        self.assertTrue(valid_bpm(0.5))
        self.assertFalse(valid_bpm(0))
        self.assertFalse(valid_bpm(-200))
        self.assertTrue(valid_bpm(9999999))
        self.assertFalse(valid_bpm(9999999, 10000))
        self.assertFalse(valid_bpm(9999999, 1000))
        self.assertTrue(valid_bpm(200, 1000))

    def test_beats_per_measure(self) -> None:
        self.assertTrue(valid_beats_per_measure(3))
        self.assertTrue(valid_beats_per_measure(4))
        self.assertFalse(valid_beats_per_measure(0))
        self.assertFalse(valid_beats_per_measure(0.25))
        self.assertFalse(valid_beats_per_measure(999))
        self.assertFalse(valid_beats_per_measure(1024))

    def test_measure_alignment(self) -> None:
        self.assertTrue(measure_aligned(24.0, 2))
        self.assertTrue(measure_aligned(24.000000000000004, 2))
        self.assertTrue(measure_aligned(6.0, 3))
        self.assertFalse(measure_aligned(326.00333333333333, 4))
        self.assertTrue(measure_aligned(0, 4))


if __name__ == "__main__":
    unittest.main()
