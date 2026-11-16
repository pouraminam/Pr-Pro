"""
Subtitle Segmentation and Generator.

Splits speech segments into professional, readable subtitles adhering to:
- Maximum characters per line (e.g. 42 chars)
- Maximum lines per caption (e.g. 2 lines)
- Minimum and maximum duration limits (1.0s - 6.0s)
- Reading speed validation (characters per second)
- Sentence and punctuation awareness (supporting English and Persian punctuation)
- Word-level timing alignment
"""

import re
from typing import List, Dict, Any, Optional


class SubtitleGenerator:
    """Generates structured subtitles from speech transcript segments."""

    def __init__(
        self,
        max_chars_per_line: int = 42,
        max_lines_per_caption: int = 2,
        min_duration: float = 1.0,
        max_duration: float = 6.0,
        min_gap: float = 0.05,
        max_reading_speed_cps: float = 21.0,
    ):
        self.max_chars_per_line = max_chars_per_line
        self.max_lines_per_caption = max_lines_per_caption
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.min_gap = min_gap
        self.max_reading_speed_cps = max_reading_speed_cps

    def generate(
        self,
        segments: List[Dict[str, Any]],
        language: str = "en",
    ) -> List[Dict[str, Any]]:
        """
        Converts Whisper segments into formatted, segmented subtitles.
        """
        raw_items: List[Dict[str, Any]] = []

        for seg in segments:
            words = seg.get("words", [])
            text = seg.get("text", "").strip()
            if not text:
                continue

            if words and len(words) > 1:
                # Use word-level timing to build captions within constraints
                seg_subs = self._split_words_into_captions(words, language)
                raw_items.extend(seg_subs)
            else:
                # Fall back to sentence/length splitting on segment text
                seg_subs = self._split_text_into_captions(
                    text,
                    seg["start"],
                    seg["end"],
                    language,
                )
                raw_items.extend(seg_subs)

        # Merge tiny trailing captions (< min_duration) with previous if they fit
        merged_raw: List[Dict[str, Any]] = []
        max_total_chars = self.max_chars_per_line * self.max_lines_per_caption

        for item in raw_items:
            if not merged_raw:
                merged_raw.append(dict(item))
            else:
                prev = merged_raw[-1]
                item_dur = item["end"] - item["start"]
                combined_text = (prev["text"].replace("\n", " ") + " " + item["text"].replace("\n", " ")).strip()
                if item_dur < self.min_duration and len(combined_text) <= max_total_chars:
                    prev["end"] = item["end"]
                    prev["text"] = self._format_lines(combined_text)
                    prev["duration"] = round(prev["end"] - prev["start"], 3)
                else:
                    merged_raw.append(dict(item))

        # Enforce minimum gap and duration limits
        final_subs: List[Dict[str, Any]] = []
        for i, item in enumerate(merged_raw):
            cur = dict(item)
            cur["id"] = i + 1

            # Check min duration
            dur = cur["end"] - cur["start"]
            if dur < self.min_duration:
                cur["end"] = round(cur["start"] + self.min_duration, 3)

            # Prevent overlap with next
            if i + 1 < len(merged_raw):
                next_start = merged_raw[i + 1]["start"]
                if cur["end"] + self.min_gap > next_start:
                    cur["end"] = max(cur["start"] + self.min_duration, round(next_start - self.min_gap, 3))

            cur["duration"] = round(cur["end"] - cur["start"], 3)

            # Run validation checks
            validation = self._validate_caption(cur)
            cur["is_valid"] = validation["is_valid"]
            cur["warnings"] = validation["warnings"]
            cur["reading_speed_cps"] = validation["cps"]

            final_subs.append(cur)

        return final_subs

    def _split_words_into_captions(
        self, words: List[Dict[str, Any]], language: str
    ) -> List[Dict[str, Any]]:
        """Groups words into chunks fitting character and duration limits."""
        captions = []
        cur_words = []
        cur_chars = 0
        cap_start = words[0]["start"]

        for w in words:
            word_str = w.get("word", "").strip()
            if not word_str:
                continue

            w_len = len(word_str)
            projected_chars = cur_chars + (1 if cur_chars > 0 else 0) + w_len
            projected_dur = w["end"] - cap_start

            # Check punctuation boundaries (period, question mark, Persian punctuation)
            has_sentence_end = bool(re.search(r"[.?!؟؛]", word_str))

            if cur_words and (
                projected_chars > (self.max_chars_per_line * self.max_lines_per_caption)
                or projected_dur > self.max_duration
                or (has_sentence_end and cur_chars >= self.max_chars_per_line)
            ):
                # Flush current caption
                cap_text = " ".join(cw.get("word", "").strip() for cw in cur_words)
                formatted = self._format_lines(cap_text)
                captions.append({
                    "start": round(cap_start, 3),
                    "end": round(cur_words[-1]["end"], 3),
                    "duration": round(cur_words[-1]["end"] - cap_start, 3),
                    "text": formatted,
                    "language": language,
                })
                cur_words = [w]
                cur_chars = w_len
                cap_start = w["start"]
            else:
                cur_words.append(w)
                cur_chars = projected_chars

        if cur_words:
            cap_text = " ".join(cw.get("word", "").strip() for cw in cur_words)
            formatted = self._format_lines(cap_text)
            captions.append({
                "start": round(cap_start, 3),
                "end": round(cur_words[-1]["end"], 3),
                "duration": round(cur_words[-1]["end"] - cap_start, 3),
                "text": formatted,
                "language": language,
            })

        return captions

    def _split_text_into_captions(
        self, text: str, start: float, end: float, language: str
    ) -> List[Dict[str, Any]]:
        """Splits text when word timestamps are unavailable, estimating time based on length."""
        words = text.split()
        if not words:
            return []

        total_dur = max(0.1, end - start)
        total_chars = sum(len(w) for w in words)

        max_cap_chars = self.max_chars_per_line * self.max_lines_per_caption
        if len(text) <= max_cap_chars:
            return [{
                "start": round(start, 3),
                "end": round(end, 3),
                "duration": round(total_dur, 3),
                "text": self._format_lines(text),
                "language": language,
            }]

        # Split into multiple chunks
        chunks = []
        cur_chunk = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + 1 > max_cap_chars and cur_chunk:
                chunks.append(" ".join(cur_chunk))
                cur_chunk = [w]
                cur_len = len(w)
            else:
                cur_chunk.append(w)
                cur_len += len(w) + 1

        if cur_chunk:
            chunks.append(" ".join(cur_chunk))

        captions = []
        c_start = start
        for c in chunks:
            c_ratio = len(c) / float(total_chars) if total_chars > 0 else (1.0 / len(chunks))
            c_dur = total_dur * c_ratio
            c_end = min(end, c_start + c_dur)
            captions.append({
                "start": round(c_start, 3),
                "end": round(c_end, 3),
                "duration": round(c_end - c_start, 3),
                "text": self._format_lines(c),
                "language": language,
            })
            c_start = c_end

        return captions

    def _format_lines(self, text: str) -> str:
        """Splits long text across lines respecting max_chars_per_line."""
        if len(text) <= self.max_chars_per_line:
            return text

        words = text.split()
        lines = []
        cur_line = []
        cur_len = 0

        for w in words:
            if cur_len + len(w) + 1 > self.max_chars_per_line and cur_line:
                lines.append(" ".join(cur_line))
                cur_line = [w]
                cur_len = len(w)
            else:
                cur_line.append(w)
                cur_len += len(w) + 1

        if cur_line:
            lines.append(" ".join(cur_line))

        return "\n".join(lines[:self.max_lines_per_caption])

    def _validate_caption(self, caption: Dict[str, Any]) -> Dict[str, Any]:
        """Validates caption against readability and formatting criteria."""
        warnings = []
        text = caption.get("text", "")
        dur = max(0.1, caption.get("end", 0.0) - caption.get("start", 0.0))
        char_count = len(text.replace("\n", ""))
        cps = round(char_count / dur, 1)

        if not text.strip():
            warnings.append("Empty caption text.")

        if dur < self.min_duration:
            warnings.append(f"Caption duration ({dur:.1f}s) is shorter than minimum ({self.min_duration:.1f}s).")

        if dur > self.max_duration:
            warnings.append(f"Caption duration ({dur:.1f}s) exceeds maximum ({self.max_duration:.1f}s).")

        if cps > self.max_reading_speed_cps:
            warnings.append(f"Reading speed ({cps} cps) exceeds recommended {self.max_reading_speed_cps} cps.")

        lines = text.split("\n")
        if len(lines) > self.max_lines_per_caption:
            warnings.append(f"Caption has {len(lines)} lines (max is {self.max_lines_per_caption}).")

        for l in lines:
            if len(l) > self.max_chars_per_line + 5:
                warnings.append(f"Line length ({len(l)} chars) exceeds {self.max_chars_per_line}.")

        return {
            "is_valid": len(warnings) == 0,
            "warnings": warnings,
            "cps": cps,
        }
