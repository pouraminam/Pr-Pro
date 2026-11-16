"""
Audio Extractor and Resampler Module.

Prepares audio files for Faster-Whisper and Silero VAD.
Ensures uniform format: 16,000 Hz, 16-bit PCM mono WAV.
"""

import os
import shutil
import subprocess
import wave
import struct
from pathlib import Path
from typing import Optional, Tuple


class AudioExtractor:
    """Handles extracting, downmixing, and resampling media audio to 16kHz mono PCM WAV."""

    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_cmd = self._find_ffmpeg(ffmpeg_path)

    def _find_ffmpeg(self, custom_path: Optional[str] = None) -> Optional[str]:
        """Locates ffmpeg executable in custom path, bundled tools, or system PATH."""
        if custom_path and os.path.exists(custom_path):
            return custom_path

        # Check bundled directory relative to engine
        engine_root = Path(__file__).resolve().parent.parent
        bundled_candidates = [
            engine_root / "tools" / "ffmpeg.exe",
            engine_root / "tools" / "ffmpeg",
            engine_root.parent / "tools" / "ffmpeg.exe",
        ]
        for candidate in bundled_candidates:
            if candidate.is_file():
                return str(candidate)

        # Check system PATH
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg

        return None

    def has_ffmpeg(self) -> bool:
        return self.ffmpeg_cmd is not None

    def extract_to_16k_mono(self, input_file: str, output_wav: str) -> bool:
        """
        Extracts/converts audio from any supported media file to 16kHz mono WAV.
        Uses ffmpeg if available; falls back to pure-Python WAV resampling if input is WAV.
        """
        input_path = Path(input_file).resolve()
        output_path = Path(output_wav).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not input_path.exists():
            raise FileNotFoundError(f"Input media file not found: {input_path}")

        # Attempt ffmpeg conversion first
        if self.ffmpeg_cmd:
            cmd = [
                self.ffmpeg_cmd,
                "-y",  # Overwrite output
                "-i", str(input_path),
                "-vn",  # No video
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-f", "wav",
                str(output_path),
            ]
            try:
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True,
                    timeout=300
                )
                if output_path.exists() and output_path.stat().st_size > 44:
                    return True
            except (subprocess.SubprocessError, OSError) as e:
                # If ffmpeg failed or timed out, log and attempt WAV fallback
                pass

        # Native fallback: if input is a WAV file, resample via Python wave module
        if input_path.suffix.lower() == ".wav":
            return self._resample_wav_native(str(input_path), str(output_path))

        raise RuntimeError(
            f"Cannot extract audio from {input_path.suffix} without ffmpeg installed. "
            "Please provide a WAV file or ensure ffmpeg is available."
        )

    def _resample_wav_native(self, input_wav: str, output_wav: str, target_sr: int = 16000) -> bool:
        """
        Pure Python fallback to convert uncompressed PCM WAV to 16kHz mono.
        Does not require external dependencies or C libraries.
        """
        with wave.open(input_wav, "rb") as win:
            nchannels = win.getnchannels()
            sampwidth = win.getsampwidth()
            framerate = win.getframerate()
            nframes = win.getnframes()
            raw_data = win.readframes(nframes)

        if sampwidth != 2:
            raise ValueError(f"Only 16-bit PCM WAV supported in native fallback (got {sampwidth * 8}-bit)")

        total_samples = nframes * nchannels
        fmt = f"<{total_samples}h"
        samples = struct.unpack(fmt, raw_data)

        # Downmix to mono if multi-channel
        if nchannels > 1:
            mono_samples = []
            for i in range(0, total_samples, nchannels):
                avg = sum(samples[i:i + nchannels]) // nchannels
                mono_samples.append(avg)
        else:
            mono_samples = list(samples)

        # Resample to target_sr if sample rate differs
        if framerate != target_sr:
            ratio = target_sr / framerate
            out_len = int(len(mono_samples) * ratio)
            resampled = [0] * out_len
            for out_idx in range(out_len):
                src_pos = out_idx / ratio
                src_idx = int(src_pos)
                frac = src_pos - src_idx
                if src_idx + 1 < len(mono_samples):
                    val = int(mono_samples[src_idx] * (1.0 - frac) + mono_samples[src_idx + 1] * frac)
                else:
                    val = mono_samples[-1] if mono_samples else 0
                resampled[out_idx] = max(-32768, min(32767, val))
            final_samples = resampled
        else:
            final_samples = mono_samples

        out_raw = struct.pack(f"<{len(final_samples)}h", *final_samples)

        with wave.open(output_wav, "wb") as wout:
            wout.setnchannels(1)
            wout.setsampwidth(2)
            wout.setframerate(target_sr)
            wout.writeframes(out_raw)

        return True

    @staticmethod
    def get_wav_info(wav_path: str) -> Tuple[float, int, int]:
        """Returns (duration_seconds, sample_rate, channels) for a WAV file."""
        with wave.open(wav_path, "rb") as w:
            sr = w.getframerate()
            ch = w.getnchannels()
            frames = w.getnframes()
            duration = frames / float(sr) if sr > 0 else 0.0
            return duration, sr, ch
