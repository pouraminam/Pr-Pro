"""
Unit Tests for Premiere Pro Exact Timebase and Tick Conversions.
"""

import unittest

# Internal constants matching plugin/src/timeline/timebase.js
TICKS_PER_SECOND = 254016000000


class PyTimebase:
    def __init__(self, fps=25.0):
        self.fps = fps
        if abs(fps - 23.976) < 0.01:
            num, den = 24000, 1001
        elif abs(fps - 29.97) < 0.01:
            num, den = 30000, 1001
        elif abs(fps - 59.94) < 0.01:
            num, den = 60000, 1001
        else:
            num, den = int(round(fps * 1000)), 1000

        self.ticks_per_frame = (TICKS_PER_SECOND * den) // num

    def seconds_to_ticks(self, sec):
        raw_ticks = int(round(sec * TICKS_PER_SECOND))
        # Round to nearest frame boundary
        half = self.ticks_per_frame // 2
        f = (raw_ticks + half) // self.ticks_per_frame
        return f * self.ticks_per_frame

    def ticks_to_seconds(self, ticks):
        return ticks / float(TICKS_PER_SECOND)

    def round_seconds_to_frame(self, sec):
        t = self.seconds_to_ticks(sec)
        return self.ticks_to_seconds(t)


class TestTimebase(unittest.TestCase):

    def test_25fps_pal_timebase(self):
        tb = PyTimebase(25.0)
        # Exactly 254016000000 / 25 = 10160640000 ticks per frame
        self.assertEqual(tb.ticks_per_frame, 10160640000)

        # 1.0 second should be exactly 254016000000 ticks
        self.assertEqual(tb.seconds_to_ticks(1.0), TICKS_PER_SECOND)
        self.assertEqual(tb.ticks_to_seconds(TICKS_PER_SECOND), 1.0)

    def test_24fps_film_timebase(self):
        tb = PyTimebase(24.0)
        # Exactly 254016000000 / 24 = 10584000000 ticks per frame
        self.assertEqual(tb.ticks_per_frame, 10584000000)
        self.assertEqual(tb.seconds_to_ticks(1.0), TICKS_PER_SECOND)

    def test_29_97fps_ntsc_timebase(self):
        tb = PyTimebase(29.97)
        self.assertAlmostEqual(tb.ticks_to_seconds(tb.ticks_per_frame * 30000 // 1001), 1.0, delta=0.001)

    def test_frame_rounding_precision(self):
        tb = PyTimebase(25.0)
        # 0.04s is 1 frame (1/25 = 0.04)
        self.assertAlmostEqual(tb.round_seconds_to_frame(0.041), 0.04, places=4)
        self.assertAlmostEqual(tb.round_seconds_to_frame(0.079), 0.08, places=4)


if __name__ == "__main__":
    unittest.main()
