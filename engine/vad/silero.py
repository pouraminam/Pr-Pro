"""
Silero Voice Activity Detection (VAD) Wrapper.

Supports:
- ONNX Runtime execution of Silero VAD v4/v5 model
- Frame-by-frame speech probability calculation (512 samples / 32ms at 16kHz)
- Minimum speech duration, minimum silence duration, pre/post padding
- Graceful adaptive spectral-energy VAD fallback when ONNX Runtime or model file is unavailable
"""

import os
import math
import struct
import wave
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional


class SileroVAD:
    """Wrapper for Silero VAD with fallback support."""

    def __init__(self, model_path: Optional[str] = None, threshold: float = 0.5):
        self.threshold = threshold
        self.model_path = model_path or self._find_model()
        self.session = None
        self._init_session()

    def _find_model(self) -> Optional[str]:
        """Looks for silero_vad.onnx in bundled or models directory."""
        candidates = [
            Path(__file__).resolve().parent.parent / "models" / "silero_vad.onnx",
            Path(__file__).resolve().parent / "silero_vad.onnx",
            Path.home() / ".cache" / "premiere_ai_editor" / "models" / "silero_vad.onnx",
        ]
        for c in candidates:
            if c.is_file():
                return str(c)
        return None

    def _init_session(self):
        """Initializes ONNX Runtime session if library and model are available."""
        if not self.model_path or not os.path.exists(self.model_path):
            return

        try:
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 2
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self.session = ort.InferenceSession(self.model_path, sess_options=opts, providers=["CPUExecutionProvider"])
        except Exception:
            self.session = None

    def is_onnx_available(self) -> bool:
        return self.session is not None

    def analyze(
        self,
        wav_path: str,
        threshold: Optional[float] = None,
        min_speech_ms: int = 250,
        min_silence_ms: int = 500,
        padding_before_ms: int = 150,
        padding_after_ms: int = 200,
    ) -> Dict[str, Any]:
        """
        Runs VAD analysis on 16kHz mono audio.
        Returns speech and silence intervals with probabilities.
        """
        th = threshold if threshold is not None else self.threshold

        with wave.open(wav_path, "rb") as wf:
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            rate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)

        if rate != 16000:
            raise ValueError(f"Silero VAD requires 16000 Hz audio, got {rate} Hz")

        total_samples = n_frames * channels
        all_samples = struct.unpack(f"<{total_samples}h", raw)

        # Mono conversion
        if channels > 1:
            samples = [sum(all_samples[i:i + channels]) // channels for i in range(0, total_samples, channels)]
        else:
            samples = list(all_samples)

        total_duration = len(samples) / 16000.0

        if self.is_onnx_available():
            speech_probs = self._run_onnx(samples)
        else:
            speech_probs = self._run_adaptive_fallback(samples)

        return self._process_probabilities(
            speech_probs,
            total_duration,
            threshold=th,
            min_speech_ms=min_speech_ms,
            min_silence_ms=min_silence_ms,
            padding_before_ms=padding_before_ms,
            padding_after_ms=padding_after_ms,
        )

    def _run_onnx(self, samples: List[int]) -> List[Tuple[float, float, float]]:
        """Runs Silero ONNX model over 512-sample (32ms) windows."""
        import numpy as np

        # Normalize 16-bit PCM to float32 [-1.0, 1.0]
        audio_float = np.array(samples, dtype=np.float32) / 32768.0
        window_size = 512
        num_windows = len(audio_float) // window_size

        # Reset states
        h = np.zeros((2, 1, 64), dtype=np.float32)
        c = np.zeros((2, 1, 64), dtype=np.float32)
        sr_tensor = np.array(16000, dtype=np.int64)

        results = []

        for i in range(num_windows):
            chunk = audio_float[i * window_size:(i + 1) * window_size]
            chunk_input = chunk.reshape(1, -1)

            ort_inputs = {
                "input": chunk_input,
                "sr": sr_tensor,
                "h": h,
                "c": c,
            }
            out, h, c = self.session.run(None, ort_inputs)
            prob = float(out[0][0])
            start_t = (i * window_size) / 16000.0
            end_t = ((i + 1) * window_size) / 16000.0
            results.append((start_t, end_t, prob))

        return results

    def _run_adaptive_fallback(self, samples: List[int]) -> List[Tuple[float, float, float]]:
        """
        High-precision spectral/zero-crossing and energy adaptive VAD fallback.
        Ensures dependable operation even before ONNX runtime / model download.
        """
        window_size = 512  # 32ms at 16kHz
        num_windows = len(samples) // window_size
        results = []

        # First pass: compute energy profile to determine dynamic noise threshold
        energies = []
        for i in range(num_windows):
            chunk = samples[i * window_size:(i + 1) * window_size]
            rms = math.sqrt(sum(s * s for s in chunk) / len(chunk)) if chunk else 0.0
            energies.append(rms)

        sorted_e = sorted(energies)
        noise_floor = sorted_e[int(len(sorted_e) * 0.15)] if sorted_e else 50.0
        speech_ref = sorted_e[int(len(sorted_e) * 0.85)] if sorted_e else 1500.0
        speech_ref = max(speech_ref, noise_floor * 3.0, 300.0)

        for i in range(num_windows):
            chunk = samples[i * window_size:(i + 1) * window_size]
            rms = energies[i]

            # Zero crossing rate (detects unvoiced consonants vs silence)
            zcr = 0
            for j in range(1, len(chunk)):
                if (chunk[j] >= 0 and chunk[j - 1] < 0) or (chunk[j] < 0 and chunk[j - 1] >= 0):
                    zcr += 1
            zcr_rate = zcr / float(len(chunk))

            # Speech probability heuristic
            if rms <= noise_floor * 1.2:
                prob = 0.05
            else:
                energy_factor = min(1.0, (rms - noise_floor) / max(1.0, speech_ref - noise_floor))
                # Boost if consonant-like zero-crossing
                if 0.08 <= zcr_rate <= 0.40 and rms > noise_floor * 1.5:
                    energy_factor = min(1.0, energy_factor + 0.15)
                prob = max(0.0, min(1.0, energy_factor))

            start_t = (i * window_size) / 16000.0
            end_t = ((i + 1) * window_size) / 16000.0
            results.append((start_t, end_t, prob))

        return results

    def _process_probabilities(
        self,
        frames: List[Tuple[float, float, float]],
        total_duration: float,
        threshold: float,
        min_speech_ms: int,
        min_silence_ms: int,
        padding_before_ms: int,
        padding_after_ms: int,
    ) -> Dict[str, Any]:
        """Translates frame probabilities into discrete padded speech & silence intervals."""
        speech_flags = [prob >= threshold for _, _, prob in frames]

        raw_speech_blocks = []
        is_speech = speech_flags[0] if speech_flags else False
        b_start = frames[0][0] if frames else 0.0

        for i in range(1, len(frames)):
            if speech_flags[i] != is_speech:
                b_end = frames[i][0]
                if is_speech:
                    raw_speech_blocks.append({"start": b_start, "end": b_end, "duration": b_end - b_start})
                is_speech = speech_flags[i]
                b_start = b_end

        if frames and is_speech:
            b_end = frames[-1][1]
            raw_speech_blocks.append({"start": b_start, "end": b_end, "duration": b_end - b_start})

        min_speech_sec = min_speech_ms / 1000.0
        filtered_speech = [b for b in raw_speech_blocks if b["duration"] >= min_speech_sec]

        # Apply padding
        pad_before = padding_before_ms / 1000.0
        pad_after = padding_after_ms / 1000.0
        padded = []
        for b in filtered_speech:
            padded.append({
                "start": max(0.0, b["start"] - pad_before),
                "end": min(total_duration, b["end"] + pad_after),
            })

        # Merge overlapping
        merged_speech: List[Dict[str, float]] = []
        for b in padded:
            if not merged_speech:
                merged_speech.append(dict(b))
            else:
                prev = merged_speech[-1]
                if b["start"] <= prev["end"]:
                    prev["end"] = max(prev["end"], b["end"])
                else:
                    merged_speech.append(dict(b))

        # Invert to silence
        min_silence_sec = min_silence_ms / 1000.0
        silence_intervals = []
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
                        "classification": "confirmed_silence" if silence_dur > 0.9 else "likely_silence",
                        "confidence": round(0.85 if silence_dur < 1.0 else 0.95, 2),
                        "enabled": True,
                        "protected": False,
                    })
                    interval_id += 1
            cur_t = max(cur_t, s["end"])

        if cur_t < total_duration:
            tail_dur = total_duration - cur_t
            if tail_dur >= min_silence_sec:
                silence_intervals.append({
                    "id": f"silence_{interval_id}",
                    "start": round(cur_t, 3),
                    "end": round(total_duration, 3),
                    "duration": round(tail_dur, 3),
                    "classification": "confirmed_silence",
                    "confidence": 0.96,
                    "enabled": True,
                    "protected": False,
                })

        total_silence = sum(interval["duration"] for interval in silence_intervals)

        return {
            "total_duration": round(total_duration, 3),
            "backend": "silero_onnx" if self.is_onnx_available() else "adaptive_spectral_vad",
            "silence_intervals": silence_intervals,
            "speech_intervals": [
                {"start": round(s["start"], 3), "end": round(s["end"], 3), "duration": round(s["end"] - s["start"], 3)}
                for s in merged_speech
            ],
            "total_silence_duration": round(total_silence, 3),
            "silence_count": len(silence_intervals),
        }
