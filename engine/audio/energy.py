"""
Energy-Based Silence Analysis Module.

Calculates:
- Short-time RMS energy and dBFS per frame
- Dynamic noise floor estimation
- Dual-threshold hysteresis (onset/offset)
- Silence intervals with pre/post-speech padding
- Minimum silence and minimum retained speech constraints
"""

import math
import struct
import wave
from typing import List, Dict, Any, Tuple, Optional


class EnergyDetector:
    """Detects speech and silence intervals based on RMS energy and dBFS thresholds."""

    def __init__(
        self,
        threshold_db: float = -35.0,
        min_silence_ms: int = 500,
        padding_before_ms: int = 150,
        padding_after_ms: int = 200,
        min_speech_ms: int = 250,
        frame_duration_ms: int = 20,
    ):
        self.threshold_db = threshold_db
        self.min_silence_ms = min_silence_ms
        self.padding_before_ms = padding_before_ms
        self.padding_after_ms = padding_after_ms
        self.min_speech_ms = min_speech_ms
        self.frame_duration_ms = frame_duration_ms

    def read_wav_samples(self, wav_path: str) -> Tuple[List[int], int]:
        """Reads 16-bit PCM WAV samples and returns (samples, sample_rate)."""
        with wave.open(wav_path, "rb") as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        if width != 2:
            raise ValueError(f"Expected 16-bit PCM WAV (width=2), got {width}")

        total_samples = n_frames * channels
        all_samples = struct.unpack(f"<{total_samples}h", raw)

        if channels == 1:
            return list(all_samples), rate
        else:
            # Downmix to mono
            mono = [
                sum(all_samples[i:i + channels]) // channels
                for i in range(0, total_samples, channels)
            ]
            return mono, rate

    def compute_frame_energies(
        self, samples: List[int], sample_rate: int
    ) -> List[Dict[str, float]]:
        """
        Computes RMS and dBFS for consecutive frames.
        Returns list of frames with start_time, end_time, rms, and dbfs.
        """
        frame_size = int(sample_rate * (self.frame_duration_ms / 1000.0))
        if frame_size < 1:
            frame_size = 1

        frames = []
        n_samples = len(samples)
        max_possible_amp = 32768.0

        for i in range(0, n_samples, frame_size):
            chunk = samples[i:i + frame_size]
            if not chunk:
                break

            # Calculate RMS
            sum_sq = sum(s * s for s in chunk)
            rms = math.sqrt(sum_sq / len(chunk))

            # Calculate dBFS relative to full scale (32768)
            if rms > 0:
                dbfs = 20.0 * math.log10(rms / max_possible_amp)
            else:
                dbfs = -100.0

            start_t = i / float(sample_rate)
            end_t = min(n_samples, i + frame_size) / float(sample_rate)

            frames.append({
                "start": start_t,
                "end": end_t,
                "rms": rms,
                "dbfs": max(-100.0, dbfs),
            })

        return frames

    def estimate_noise_floor(self, frames: List[Dict[str, float]]) -> float:
        """
        Estimates ambient noise floor using the 10th percentile of dBFS values.
        """
        if not frames:
            return -60.0
        db_values = sorted(f["dbfs"] for f in frames)
        idx = int(len(db_values) * 0.10)
        return db_values[max(0, min(idx, len(db_values) - 1))]

    def detect_speech_frames(
        self,
        frames: List[Dict[str, float]],
        effective_threshold_db: Optional[float] = None
    ) -> List[bool]:
        """
        Applies dual-threshold hysteresis:
        - Speech onset triggered when dBFS >= threshold
        - Speech offset triggered when dBFS falls below (threshold - 4 dB)
        """
        threshold = effective_threshold_db if effective_threshold_db is not None else self.threshold_db
        drop_threshold = threshold - 4.0

        is_speech = []
        currently_speech = False

        for f in frames:
            db = f["dbfs"]
            if not currently_speech:
                if db >= threshold:
                    currently_speech = True
            else:
                if db < drop_threshold:
                    currently_speech = False
            is_speech.append(currently_speech)

        return is_speech

    def analyze(self, wav_path: str) -> Dict[str, Any]:
        """
        Performs full energy analysis on a WAV file.
        Returns silence intervals, speech intervals, noise floor, and summary metrics.
        """
        samples, rate = self.read_wav_samples(wav_path)
        total_duration = len(samples) / float(rate) if rate > 0 else 0.0

        if not samples:
            return {
                "total_duration": 0.0,
                "silence_intervals": [],
                "speech_intervals": [],
                "noise_floor_db": -60.0,
                "silence_duration": 0.0,
            }

        frames = self.compute_frame_energies(samples, rate)
        noise_floor = self.estimate_noise_floor(frames)

        # Dynamic adjustment: if user threshold is lower than noise floor, adapt
        effective_threshold = max(self.threshold_db, noise_floor + 6.0)

        speech_flags = self.detect_speech_frames(frames, effective_threshold)

        # Group consecutive frames into initial speech and silence blocks
        raw_speech_blocks: List[Dict[str, float]] = []
        raw_silence_blocks: List[Dict[str, float]] = []

        current_is_speech = speech_flags[0] if speech_flags else False
        block_start = frames[0]["start"] if frames else 0.0

        for i in range(1, len(frames)):
            if speech_flags[i] != current_is_speech:
                block_end = frames[i]["start"]
                block = {"start": block_start, "end": block_end, "duration": block_end - block_start}
                if current_is_speech:
                    raw_speech_blocks.append(block)
                else:
                    raw_silence_blocks.append(block)
                current_is_speech = speech_flags[i]
                block_start = block_end

        if frames:
            block_end = frames[-1]["end"]
            block = {"start": block_start, "end": block_end, "duration": block_end - block_start}
            if current_is_speech:
                raw_speech_blocks.append(block)
            else:
                raw_silence_blocks.append(block)

        # Filter speech blocks shorter than minimum speech duration (treat as spurious clicks/breaths)
        min_speech_sec = self.min_speech_ms / 1000.0
        filtered_speech = [b for b in raw_speech_blocks if b["duration"] >= min_speech_sec]

        # Reconstruct speech intervals with padding
        padding_before = self.padding_before_ms / 1000.0
        padding_after = self.padding_after_ms / 1000.0
        padded_speech: List[Dict[str, float]] = []

        for b in filtered_speech:
            p_start = max(0.0, b["start"] - padding_before)
            p_end = min(total_duration, b["end"] + padding_after)
            padded_speech.append({"start": p_start, "end": p_end})

        # Merge overlapping padded speech regions
        merged_speech: List[Dict[str, float]] = []
        for b in padded_speech:
            if not merged_speech:
                merged_speech.append(dict(b))
            else:
                prev = merged_speech[-1]
                if b["start"] <= prev["end"]:
                    prev["end"] = max(prev["end"], b["end"])
                else:
                    merged_speech.append(dict(b))

        # Invert merged speech to derive candidate silence intervals
        min_silence_sec = self.min_silence_ms / 1000.0
        silence_intervals: List[Dict[str, Any]] = []

        cur_t = 0.0
        interval_id = 1
        for s in merged_speech:
            if s["start"] > cur_t:
                silence_dur = s["start"] - cur_t
                if silence_dur >= min_silence_sec:
                    silence_intervals.append({
                        "id": f"silence_{interval_id}",
                        "start": round(cur_t, 3),
                        "end": round(s["start"], 3),
                        "duration": round(silence_dur, 3),
                        "classification": "confirmed_silence" if silence_dur > 1.0 else "likely_silence",
                        "confidence": 0.90 if silence_dur > 1.0 else 0.75,
                        "enabled": True,
                        "protected": False,
                    })
                    interval_id += 1
            cur_t = max(cur_t, s["end"])

        # Check silence at the end of the media
        if cur_t < total_duration:
            tail_dur = total_duration - cur_t
            if tail_dur >= min_silence_sec:
                silence_intervals.append({
                    "id": f"silence_{interval_id}",
                    "start": round(cur_t, 3),
                    "end": round(total_duration, 3),
                    "duration": round(tail_dur, 3),
                    "classification": "confirmed_silence" if tail_dur > 1.0 else "likely_silence",
                    "confidence": 0.92,
                    "enabled": True,
                    "protected": False,
                })

        total_silence = sum(interval["duration"] for interval in silence_intervals)

        return {
            "total_duration": round(total_duration, 3),
            "noise_floor_db": round(noise_floor, 1),
            "effective_threshold_db": round(effective_threshold, 1),
            "silence_intervals": silence_intervals,
            "speech_intervals": [
                {
                    "start": round(s["start"], 3),
                    "end": round(s["end"], 3),
                    "duration": round(s["end"] - s["start"], 3),
                }
                for s in merged_speech
            ],
            "total_silence_duration": round(total_silence, 3),
            "silence_count": len(silence_intervals),
        }
