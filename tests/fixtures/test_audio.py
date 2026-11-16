"""
Synthetic Audio Fixture Generator for Unit & Integration Tests.

Creates deterministic 16kHz mono 16-bit PCM WAV audio files with
known speech bursts and silence intervals for automated testing.
"""

import math
import struct
import wave
from pathlib import Path


def generate_test_wav(
    output_path: str,
    pattern: list = None,
    sample_rate: int = 16000,
) -> str:
    """
    Generates a WAV file based on a pattern of ('speech'|'silence', duration_seconds).
    Default pattern:
    - 1.5s speech (440Hz tone modulated)
    - 2.0s silence (zero amplitude)
    - 2.0s speech (550Hz tone modulated)
    - 1.5s silence (zero amplitude)
    - 1.0s speech (660Hz tone modulated)
    Total duration: 8.0s
    """
    if pattern is None:
        pattern = [
            ("speech", 1.5, 440.0),
            ("silence", 2.0, 0.0),
            ("speech", 2.0, 550.0),
            ("silence", 1.5, 0.0),
            ("speech", 1.0, 660.0),
        ]

    p = Path(output_path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)

    samples = []
    for item in pattern:
        kind = item[0]
        dur = item[1]
        freq = item[2] if len(item) > 2 else 440.0
        n_samples = int(dur * sample_rate)

        if kind == "silence":
            # Silence: small ambient noise (-60 dBFS) or zeroes
            samples.extend([0] * n_samples)
        else:
            # Speech: modulated sine wave with harmonics
            for i in range(n_samples):
                t = i / float(sample_rate)
                # Primary fundamental + second harmonic + envelope modulation
                mod = 0.5 + 0.5 * math.sin(2 * math.pi * 3.0 * t)  # 3Hz speech rhythm
                val = (0.7 * math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * (freq * 2) * t)) * mod
                int_val = int(val * 24000)  # ~-2.7 dBFS peak
                samples.append(max(-32768, min(32767, int_val)))

    raw_data = struct.pack(f"<{len(samples)}h", *samples)

    with wave.open(str(p), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_data)

    return str(p)


if __name__ == "__main__":
    out = generate_test_wav("tests/fixtures/test_speech_and_silence.wav")
    print(f"Generated test audio at {out}")
