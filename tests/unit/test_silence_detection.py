"""
Unit Tests for Energy and Hybrid Silence Detection.
"""

import unittest
from pathlib import Path
from engine.audio.energy import EnergyDetector
from engine.vad.detector import SilenceDetector


class TestSilenceDetection(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fixture_wav = str(Path(__file__).resolve().parent.parent / "fixtures" / "test_speech_and_silence.wav")

    def test_energy_detector_analyzes_fixture(self):
        detector = EnergyDetector(
            threshold_db=-35.0,
            min_silence_ms=500,
            padding_before_ms=100,
            padding_after_ms=100,
        )
        res = detector.analyze(self.fixture_wav)

        self.assertIn("total_duration", res)
        self.assertAlmostEqual(res["total_duration"], 8.0, delta=0.2)
        self.assertGreater(len(res["silence_intervals"]), 0)
        self.assertGreater(len(res["speech_intervals"]), 0)

        # Check detected silence intervals (expecting 2 silence regions corresponding to 2.0s and 1.5s pauses)
        silences = res["silence_intervals"]
        self.assertGreaterEqual(len(silences), 2)

        # Ensure no silence interval is shorter than min_silence (500ms - tolerance)
        for s in silences:
            self.assertGreaterEqual(s["duration"], 0.45)
            self.assertGreater(s["end"], s["start"])

    def test_silence_detector_hybrid_mode(self):
        detector = SilenceDetector()
        res = detector.detect(
            self.fixture_wav,
            mode="hybrid",
            preset="balanced",
            preserve_breathing=True,
        )

        self.assertEqual(res["mode"], "hybrid")
        self.assertEqual(res["preset"], "balanced")
        self.assertIn("silence_intervals", res)
        self.assertGreater(res["approved_cut_count"], 0)
        self.assertGreater(res["total_silence_duration"], 0.0)
        self.assertLess(res["estimated_edited_duration"], res["total_duration"])
        self.assertGreater(res["time_saved_percent"], 0.0)

    def test_silence_classification_rules(self):
        detector = SilenceDetector()
        res = detector.detect(self.fixture_wav, mode="hybrid", preset="balanced")

        for sil in res["silence_intervals"]:
            self.assertIn(sil["classification"], [
                "confirmed_silence",
                "likely_silence",
                "low_confidence_silence",
                "possible_quiet_speech",
                "protected_pause"
            ])
            self.assertIn("confidence", sil)
            self.assertIn("enabled", sil)
            self.assertIn("protected", sil)


if __name__ == "__main__":
    unittest.main()
