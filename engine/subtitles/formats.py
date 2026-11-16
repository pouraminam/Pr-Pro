"""
Subtitle Formats Serializer (SRT, WebVTT, Plain Text, JSON).

Converts structured subtitle items into industry-standard subtitle files.
Supports UTF-8 encoding, exact millisecond formatting, and bidirectional text markers.
"""

import json
from typing import List, Dict, Any


def seconds_to_srt_time(seconds: float) -> str:
    """Formats seconds as HH:MM:SS,mmm for SRT."""
    sec = max(0.0, float(seconds))
    hrs = int(sec // 3600)
    rem = sec % 3600
    mins = int(rem // 60)
    secs = rem % 60
    s = int(secs)
    ms = int(round((secs - s) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{hrs:02d}:{mins:02d}:{s:02d},{ms:03d}"


def seconds_to_vtt_time(seconds: float) -> str:
    """Formats seconds as HH:MM:SS.mmm for WebVTT."""
    sec = max(0.0, float(seconds))
    hrs = int(sec // 3600)
    rem = sec % 3600
    mins = int(rem // 60)
    secs = rem % 60
    s = int(secs)
    ms = int(round((secs - s) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{hrs:02d}:{mins:02d}:{s:02d}.{ms:03d}"


def export_to_srt(subtitles: List[Dict[str, Any]], add_rtl_markers: bool = False) -> str:
    """
    Exports a list of subtitle dictionaries to standard SRT format.
    """
    lines = []
    for idx, sub in enumerate(subtitles, start=1):
        start_str = seconds_to_srt_time(sub["start"])
        end_str = seconds_to_srt_time(sub["end"])
        text = sub.get("text", "").strip()

        if add_rtl_markers and sub.get("language", "").startswith("fa"):
            # Wrap Persian in Unicode RTL Embedding (U+202B) and Pop Directional Formatting (U+202C)
            text = f"\u202B{text}\u202C"

        lines.append(str(idx))
        lines.append(f"{start_str} --> {end_str}")
        lines.append(text)
        lines.append("")  # Blank line separator

    return "\r\n".join(lines)


def export_to_vtt(subtitles: List[Dict[str, Any]], add_rtl_markers: bool = False) -> str:
    """
    Exports a list of subtitle dictionaries to WebVTT format.
    """
    lines = ["WEBVTT", ""]
    for idx, sub in enumerate(subtitles, start=1):
        start_str = seconds_to_vtt_time(sub["start"])
        end_str = seconds_to_vtt_time(sub["end"])
        text = sub.get("text", "").strip()

        if add_rtl_markers and sub.get("language", "").startswith("fa"):
            text = f"\u202B{text}\u202C"

        lines.append(f"{idx}")
        lines.append(f"{start_str} --> {end_str}")
        lines.append(text)
        lines.append("")

    return "\n".join(lines)


def export_to_text(subtitles: List[Dict[str, Any]]) -> str:
    """Exports raw transcript lines without timestamps."""
    return "\n".join(sub.get("text", "").strip() for sub in subtitles if sub.get("text", "").strip())


def export_to_json(subtitles: List[Dict[str, Any]], metadata: Dict[str, Any] = None) -> str:
    """Exports structured subtitle JSON with full metadata and versioning."""
    data = {
        "version": "1.0",
        "metadata": metadata or {},
        "subtitles": subtitles,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)
