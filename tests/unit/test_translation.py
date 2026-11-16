"""
Unit Tests for Persian <-> English Offline Translation.
"""

import unittest
from engine.translation.translator import OfflineTranslator


class TestTranslation(unittest.TestCase):

    def setUp(self):
        self.translator = OfflineTranslator()

    def test_english_to_persian_translation(self):
        text = "Hello and welcome to this video tutorial"
        res = self.translator.translate_text(text, source_lang="en", target_lang="fa")

        self.assertIn("translated", res)
        self.assertEqual(res["source_lang"], "en")
        self.assertEqual(res["target_lang"], "fa")
        self.assertTrue(res["is_machine_translated"])
        self.assertGreater(len(res["translated"]), 0)

    def test_persian_to_english_translation(self):
        text = "سلام و خوش آمدید"
        res = self.translator.translate_text(text, source_lang="fa", target_lang="en")

        self.assertIn("translated", res)
        self.assertEqual(res["source_lang"], "fa")
        self.assertEqual(res["target_lang"], "en")
        self.assertIn("hello", res["translated"].lower())

    def test_technical_glossary_preservation(self):
        text = "timeline and sequence and clip"
        res = self.translator.translate_text(text, source_lang="en", target_lang="fa")
        # Ensure terms are translated into Persian video editing terms
        self.assertIn("تایم‌لاین", res["translated"])
        self.assertIn("سکانس", res["translated"])
        self.assertIn("کلیپ", res["translated"])


if __name__ == "__main__":
    unittest.main()
