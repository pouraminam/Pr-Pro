"""
Unit Tests for Subtitle Generation and Serialization.
"""

import unittest
from engine.subtitles.generator import SubtitleGenerator
from engine.subtitles.formats import (
    seconds_to_srt_time,
    seconds_to_vtt_time,
    export_to_srt,
    export_to_vtt,
    export_to_text,
    export_to_json,
)


class TestSubtitles(unittest.TestCase):

    def test_time_formatting(self):
        self.assertEqual(seconds_to_srt_time(0.0), "00:00:00,000")
        self.assertEqual(seconds_to_srt_time(65.123), "00:01:05,123")
        self.assertEqual(seconds_to_srt_time(3661.050), "01:01:01,050")

        self.assertEqual(seconds_to_vtt_time(0.0), "00:00:00.000")
        self.assertEqual(seconds_to_vtt_time(65.123), "00:01:05.123")

    def test_subtitle_generator_constraints(self):
        generator = SubtitleGenerator(
            max_chars_per_line=30,
            max_lines_per_caption=2,
            min_duration=1.0,
            max_duration=5.0,
        )

        segments = [
            {
                "id": 1,
                "start": 0.5,
                "end": 4.0,
                "text": "This is a clean test sentence for automated subtitle segmentation.",
                "words": [
                    {"word": "This", "start": 0.5, "end": 0.8},
                    {"word": "is", "start": 0.8, "end": 1.0},
                    {"word": "a", "start": 1.0, "end": 1.1},
                    {"word": "clean", "start": 1.1, "end": 1.5},
                    {"word": "test", "start": 1.5, "end": 1.9},
                    {"word": "sentence", "start": 1.9, "end": 2.5},
                    {"word": "for", "start": 2.5, "end": 2.7},
                    {"word": "automated", "start": 2.7, "end": 3.4},
                    {"word": "subtitle", "start": 3.4, "end": 3.7},
                    {"word": "segmentation.", "start": 3.7, "end": 4.0},
                ],
            }
        ]

        subs = generator.generate(segments, language="en")
        self.assertGreater(len(subs), 0)

        for sub in subs:
            self.assertGreaterEqual(sub["duration"], 0.99)
            self.assertLessEqual(sub["duration"], 5.05)
            self.assertIn("is_valid", sub)
            self.assertTrue(sub["is_valid"])

    def test_srt_and_vtt_export(self):
        subs = [
            {"id": 1, "start": 1.0, "end": 2.5, "text": "First caption", "language": "en"},
            {"id": 2, "start": 3.0, "end": 4.5, "text": "Second caption", "language": "en"},
        ]

        srt_out = export_to_srt(subs)
        self.assertIn("1\r\n00:00:01,000 --> 00:00:02,500\r\nFirst caption", srt_out)
        self.assertIn("2\r\n00:00:03,000 --> 00:00:04,500\r\nSecond caption", srt_out)

        vtt_out = export_to_vtt(subs)
        self.assertTrue(vtt_out.startswith("WEBVTT"))
        self.assertIn("00:00:01.000 --> 00:00:02.500", vtt_out)

        txt_out = export_to_text(subs)
        self.assertEqual(txt_out, "First caption\nSecond caption")

    def test_persian_rtl_markers(self):
        subs = [
            {"id": 1, "start": 1.0, "end": 2.5, "text": "سلام و درود به همه", "language": "fa"},
        ]
        srt_rtl = export_to_srt(subs, add_rtl_markers=True)
        # Expecting Unicode RTL embedding markers U+202B and U+202C
        self.assertIn("\u202B", srt_rtl)
        self.assertIn("\u202C", srt_rtl)


if __name__ == "__main__":
    unittest.main()
