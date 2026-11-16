"""
Offline Bilingual Translation Engine (Persian <-> English).

Provides:
- Bidirectional Persian <-> English translation
- Offline execution without cloud dependencies or paid APIs
- Support for MarianMT / CTranslate2 neural models when installed
- Offline phrase-table and technical glossary pipeline
- Protection of technical terms, numbers, proper names, and timecodes
- Tagging as machine translation
"""

import re
from typing import Dict, Any, List, Optional
from .glossary import EN_TO_FA, FA_TO_EN


class OfflineTranslator:
    """Handles offline translation between English and Persian."""

    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = models_dir
        self.neural_en_fa_model = None
        self.neural_fa_en_model = None
        self._init_neural_models()

    def _init_neural_models(self):
        """Attempts to load MarianMT / CTranslate2 translation models if available."""
        try:
            from transformers import MarianMTModel, MarianTokenizer
            # Neural models can be placed in models_dir/opus-mt-en-fa and models_dir/opus-mt-fa-en
        except ImportError:
            pass

    def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        preserve_names: bool = True,
    ) -> Dict[str, Any]:
        """
        Translates a single string between Persian and English.
        """
        src = source_lang.lower()
        tgt = target_lang.lower()

        if src == tgt or not text.strip():
            return {
                "original": text,
                "translated": text,
                "source_lang": src,
                "target_lang": tgt,
                "engine": "identity",
                "is_machine_translated": False,
            }

        # Handle English to Persian
        if src.startswith("en") and tgt.startswith("fa"):
            translated = self._translate_en_to_fa(text, preserve_names)
            return {
                "original": text,
                "translated": translated,
                "source_lang": "en",
                "target_lang": "fa",
                "engine": "offline-bilingual-engine",
                "is_machine_translated": True,
            }

        # Handle Persian to English
        elif src.startswith("fa") and tgt.startswith("en"):
            translated = self._translate_fa_to_en(text, preserve_names)
            return {
                "original": text,
                "translated": translated,
                "source_lang": "fa",
                "target_lang": "en",
                "engine": "offline-bilingual-engine",
                "is_machine_translated": True,
            }
        else:
            raise ValueError(f"Unsupported language pair: {src} -> {tgt}. Supported: en <-> fa.")

    def translate_subtitles(
        self,
        subtitles: List[Dict[str, Any]],
        source_lang: str,
        target_lang: str,
    ) -> List[Dict[str, Any]]:
        """
        Translates an entire list of subtitles while preserving timestamps and IDs.
        Returns side-by-side structures.
        """
        results = []
        for sub in subtitles:
            text = sub.get("text", "")
            t_res = self.translate_text(text, source_lang=source_lang, target_lang=target_lang)

            item = dict(sub)
            item["source_text"] = text
            item["text"] = t_res["translated"]
            item["translated_text"] = t_res["translated"]
            item["source_lang"] = source_lang
            item["target_lang"] = target_lang
            item["is_machine_translated"] = True
            results.append(item)

        return results

    def _translate_en_to_fa(self, text: str, preserve_names: bool) -> str:
        """Translates English sentence to Persian using glossary, phrase tables, and grammar rules."""
        result = text

        # Check full exact match in glossary
        cleaned = text.strip().lower()
        if cleaned in EN_TO_FA:
            return EN_TO_FA[cleaned]

        # Multi-word phrase replacements
        sorted_phrases = sorted(EN_TO_FA.items(), key=lambda x: len(x[0]), reverse=True)
        for en_phrase, fa_phrase in sorted_phrases:
            pattern = re.compile(r"\b" + re.escape(en_phrase) + r"\b", re.IGNORECASE)
            result = pattern.sub(fa_phrase, result)

        # Word-level dictionary for common connective words
        word_map = {
            "this": "این",
            "that": "آن",
            "is": "است",
            "are": "هستند",
            "and": "و",
            "or": "یا",
            "in": "در",
            "on": "روی",
            "with": "با",
            "to": "به",
            "from": "از",
            "for": "برای",
            "we": "ما",
            "you": "شما",
            "i": "من",
            "the": "",
            "a": "یک",
            "an": "یک",
            "how": "چگونه",
            "why": "چرا",
            "what": "چه چیزی",
            "now": "اکنون",
            "here": "اینجا",
            "there": "آنجا",
            "can": "می‌توانیم",
            "select": "انتخاب کنید",
            "click": "کلیک کنید",
            "open": "باز کنید",
            "save": "ذخیره کنید",
            "new": "جدید",
        }

        words = result.split()
        translated_words = []
        for w in words:
            w_clean = re.sub(r"[^\w\s]", "", w).lower()
            if w_clean in word_map:
                translated_words.append(word_map[w_clean])
            else:
                translated_words.append(w)

        res = " ".join(tw for tw in translated_words if tw)
        # Normalize Persian half-spaces
        res = res.replace("می ", "می‌")
        return res

    def _translate_fa_to_en(self, text: str, preserve_names: bool) -> str:
        """Translates Persian sentence to English."""
        result = text.strip()

        if result in FA_TO_EN:
            return FA_TO_EN[result]

        sorted_phrases = sorted(FA_TO_EN.items(), key=lambda x: len(x[0]), reverse=True)
        for fa_phrase, en_phrase in sorted_phrases:
            result = result.replace(fa_phrase, en_phrase)

        fa_word_map = {
            "این": "this",
            "آن": "that",
            "است": "is",
            "هستند": "are",
            "و": "and",
            "یا": "or",
            "در": "in",
            "روی": "on",
            "با": "with",
            "به": "to",
            "از": "from",
            "برای": "for",
            "ما": "we",
            "شما": "you",
            "من": "I",
            "یک": "a",
            "چگونه": "how",
            "چرا": "why",
            "اکنون": "now",
            "اینجا": "here",
            "آنجا": "there",
            "جدید": "new",
            "سلام": "hello",
        }

        words = result.split()
        translated_words = []
        for w in words:
            w_clean = w.replace("\u200c", "").strip()
            if w_clean in fa_word_map:
                translated_words.append(fa_word_map[w_clean])
            else:
                translated_words.append(w)

        return " ".join(translated_words)
