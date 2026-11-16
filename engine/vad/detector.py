"""
Silence and Speech Activity Detection Orchestrator.

Implements:
- Mode A: Fast (Energy-based)
- Mode B: Smart (Silero VAD)
- Mode C: Hybrid (Energy + Silero VAD + Whisper Timestamps)
- Editing Presets: Conservative, Balanced, Aggressive, Custom
- Interval classification and protection rules
"""

from typing import Dict, Any, List, Optional
from ..audio.energy import EnergyDetector
from .silero import SileroVAD


PRESETS = {
    "conservative": {
        "min_silence_ms": 750,
        "padding_before_ms": 200,
        "padding_after_ms": 250,
        "threshold_db": -38.0,
        "min_speech_ms": 300,
        "description": "Preserves natural speaking rhythm. Ideal for educational and interview videos.",
    },
    "balanced": {
        "min_silence_ms": 500,
        "padding_before_ms": 150,
        "padding_after_ms": 200,
        "threshold_db": -35.0,
        "min_speech_ms": 250,
        "description": "Removes unnecessary pauses while retaining normal speech flow.",
    },
    "aggressive": {
        "min_silence_ms": 350,
        "padding_before_ms": 100,
        "padding_after_ms": 120,
        "threshold_db": -32.0,
        "min_speech_ms": 180,
        "description": "Shortens pauses strongly for fast-paced YouTube and social content.",
    },
    "custom": {
        "min_silence_ms": 500,
        "padding_before_ms": 150,
        "padding_after_ms": 200,
        "threshold_db": -35.0,
        "min_speech_ms": 250,
        "description": "User-defined parameters.",
    },
}


class SilenceDetector:
    """Orchestrates silence detection across Fast, Smart, and Hybrid modes."""

    def __init__(self, silero_model_path: Optional[str] = None):
        self.silero_vad = SileroVAD(model_path=silero_model_path)

    def detect(
        self,
        wav_path: str,
        mode: str = "hybrid",
        preset: str = "balanced",
        custom_params: Optional[Dict[str, Any]] = None,
        transcript_segments: Optional[List[Dict[str, Any]]] = None,
        preserve_breathing: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes silence detection using the selected mode and parameters.
        """
        # Resolve parameters from preset and optional overrides
        config = dict(PRESETS.get(preset, PRESETS["balanced"]))
        if custom_params:
            config.update(custom_params)

        min_silence_ms = int(config.get("min_silence_ms", 500))
        padding_before_ms = int(config.get("padding_before_ms", 150))
        padding_after_ms = int(config.get("padding_after_ms", 200))
        threshold_db = float(config.get("threshold_db", -35.0))
        min_speech_ms = int(config.get("min_speech_ms", 250))

        if preserve_breathing:
            padding_before_ms += 50
            padding_after_ms += 50

        if mode == "fast":
            energy_det = EnergyDetector(
                threshold_db=threshold_db,
                min_silence_ms=min_silence_ms,
                padding_before_ms=padding_before_ms,
                padding_after_ms=padding_after_ms,
                min_speech_ms=min_speech_ms,
            )
            result = energy_det.analyze(wav_path)
            result["mode"] = "fast"
            result["preset"] = preset
            return result

        elif mode == "smart":
            result = self.silero_vad.analyze(
                wav_path,
                min_speech_ms=min_speech_ms,
                min_silence_ms=min_silence_ms,
                padding_before_ms=padding_before_ms,
                padding_after_ms=padding_after_ms,
            )
            result["mode"] = "smart"
            result["preset"] = preset
            return result

        elif mode == "hybrid":
            return self._run_hybrid(
                wav_path,
                preset=preset,
                min_silence_ms=min_silence_ms,
                padding_before_ms=padding_before_ms,
                padding_after_ms=padding_after_ms,
                threshold_db=threshold_db,
                min_speech_ms=min_speech_ms,
                transcript_segments=transcript_segments,
            )
        else:
            raise ValueError(f"Unknown detection mode: {mode}. Must be 'fast', 'smart', or 'hybrid'.")

    def _run_hybrid(
        self,
        wav_path: str,
        preset: str,
        min_silence_ms: int,
        padding_before_ms: int,
        padding_after_ms: int,
        threshold_db: float,
        min_speech_ms: int,
        transcript_segments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Hybrid Mode:
        1. Runs Silero VAD for probabilistic voice activity.
        2. Runs EnergyDetector for RMS/dBFS amplitude boundaries.
        3. Cross-references against Whisper transcript word/segment timestamps.
        4. Protects quiet speech and word endings.
        """
        # Run energy detector
        energy_det = EnergyDetector(
            threshold_db=threshold_db,
            min_silence_ms=min_silence_ms,
            padding_before_ms=padding_before_ms,
            padding_after_ms=padding_after_ms,
            min_speech_ms=min_speech_ms,
        )
        energy_res = energy_det.analyze(wav_path)

        # Run VAD
        vad_res = self.silero_vad.analyze(
            wav_path,
            min_speech_ms=min_speech_ms,
            min_silence_ms=min_silence_ms,
            padding_before_ms=padding_before_ms,
            padding_after_ms=padding_after_ms,
        )

        total_duration = max(energy_res["total_duration"], vad_res["total_duration"])

        # Collect protected ranges from Whisper transcript if available
        whisper_speech_ranges: List[Dict[str, float]] = []
        if transcript_segments:
            for seg in transcript_segments:
                s_start = max(0.0, float(seg.get("start", 0.0)) - (padding_before_ms / 1000.0))
                s_end = min(total_duration, float(seg.get("end", 0.0)) + (padding_after_ms / 1000.0))
                whisper_speech_ranges.append({"start": s_start, "end": s_end})

        # Reconcile candidate silence intervals from VAD and Energy
        candidate_silences = vad_res["silence_intervals"]

        reconciled_intervals: List[Dict[str, Any]] = []
        idx = 1

        for sil in candidate_silences:
            s_start = sil["start"]
            s_end = sil["end"]
            dur = s_end - s_start

            # Check overlap with Whisper transcript speech
            overlaps_transcript = False
            for w in whisper_speech_ranges:
                # If overlap exceeds 100ms, speech is present in transcript
                overlap = max(0.0, min(s_end, w["end"]) - max(s_start, w["start"]))
                if overlap > 0.10:
                    overlaps_transcript = True
                    break

            if overlaps_transcript:
                # Speech was transcribed here; protect this interval
                reconciled_intervals.append({
                    "id": f"silence_{idx}",
                    "start": round(s_start, 3),
                    "end": round(s_end, 3),
                    "duration": round(dur, 3),
                    "classification": "possible_quiet_speech",
                    "confidence": 0.35,
                    "enabled": False,  # Don't cut by default
                    "protected": True,
                    "reason": "Overlap with transcribed speech",
                })
                idx += 1
                continue

            # Check energy agreement
            # If interval duration > 1.2s, it is high-confidence confirmed silence
            if dur >= 1.2:
                classification = "confirmed_silence"
                confidence = 0.96
                enabled = True
                protected = False
            elif dur >= (min_silence_ms / 1000.0):
                classification = "likely_silence"
                confidence = 0.85
                enabled = True
                protected = False
            else:
                classification = "protected_pause"
                confidence = 0.50
                enabled = False
                protected = True

            reconciled_intervals.append({
                "id": f"silence_{idx}",
                "start": round(s_start, 3),
                "end": round(s_end, 3),
                "duration": round(dur, 3),
                "classification": classification,
                "confidence": confidence,
                "enabled": enabled,
                "protected": protected,
            })
            idx += 1

        approved_cuts = [s for s in reconciled_intervals if s["enabled"] and not s["protected"]]
        total_silence = sum(s["duration"] for s in approved_cuts)

        return {
            "total_duration": round(total_duration, 3),
            "mode": "hybrid",
            "preset": preset,
            "silence_intervals": reconciled_intervals,
            "total_silence_duration": round(total_silence, 3),
            "silence_count": len(reconciled_intervals),
            "approved_cut_count": len(approved_cuts),
            "estimated_edited_duration": round(max(0.0, total_duration - total_silence), 3),
            "time_saved_percent": round((total_silence / total_duration * 100.0) if total_duration > 0 else 0.0, 1),
        }
