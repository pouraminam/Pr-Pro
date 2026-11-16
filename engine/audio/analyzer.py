"""
Audio Waveform Downsampler and Envelope Generator.

Generates normalized visual waveform peaks and RMS envelopes
for rendering interactive SVG / HTML5 Canvas waveforms in the Premiere panel.
"""

import math
import struct
import wave
from typing import Dict, Any, List


class WaveformAnalyzer:
    """Extracts downsampled waveform peaks and RMS values for UI visualization."""

    def __init__(self, target_points: int = 1200):
        self.target_points = target_points

    def generate_envelope(self, wav_path: str, max_points: int = 1200) -> Dict[str, Any]:
        """
        Reads a WAV file and computes min/max/RMS values for consecutive bins.
        Returns normalized arrays (-1.0 to 1.0) and time values.
        """
        with wave.open(wav_path, "rb") as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        if width != 2:
            raise ValueError(f"Expected 16-bit PCM WAV, got width={width}")

        total_samples = n_frames * channels
        all_samples = struct.unpack(f"<{total_samples}h", raw)

        # Downmix to mono
        if channels > 1:
            samples = [
                sum(all_samples[i:i + channels]) // channels
                for i in range(0, total_samples, channels)
            ]
        else:
            samples = list(all_samples)

        total_len = len(samples)
        duration = total_len / float(rate) if rate > 0 else 0.0

        if total_len == 0:
            return {
                "duration": 0.0,
                "sample_rate": rate,
                "peaks_max": [],
                "peaks_min": [],
                "rms": [],
                "points_count": 0,
            }

        num_points = min(max_points, total_len)
        bin_size = total_len / float(num_points)

        peaks_max: List[float] = []
        peaks_min: List[float] = []
        rms_vals: List[float] = []

        max_val = 32768.0

        for i in range(num_points):
            start_idx = int(i * bin_size)
            end_idx = int((i + 1) * bin_size)
            end_idx = max(start_idx + 1, min(total_len, end_idx))

            chunk = samples[start_idx:end_idx]
            c_max = max(chunk) / max_val
            c_min = min(chunk) / max_val

            sum_sq = sum((s / max_val) ** 2 for s in chunk)
            c_rms = math.sqrt(sum_sq / len(chunk))

            peaks_max.append(round(c_max, 4))
            peaks_min.append(round(c_min, 4))
            rms_vals.append(round(c_rms, 4))

        return {
            "duration": round(duration, 3),
            "sample_rate": rate,
            "peaks_max": peaks_max,
            "peaks_min": peaks_min,
            "rms": rms_vals,
            "points_count": num_points,
        }
