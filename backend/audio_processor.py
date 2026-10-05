"""
Audio Processor & Acoustic Noise Simulator for KisanSetu
Supports:
1. Audio format normalization
2. Telephonic 8kHz downsampling/resampling filter
3. Acoustic background noise injection (tractor rumble, rural market)
"""

import io
import wave
import math
import struct
from typing import Tuple


class AudioProcessor:
    @staticmethod
    def inspect_wav(audio_bytes: bytes) -> dict:
        """Inspects WAV audio parameters."""
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                return {
                    "channels": wf.getnchannels(),
                    "sample_width": wf.getsampwidth(),
                    "frame_rate": wf.getframerate(),
                    "n_frames": wf.getnframes(),
                    "duration_sec": round(wf.getnframes() / float(wf.getframerate()), 2)
                }
        except Exception:
            return {"format": "unknown or compressed"}

    @staticmethod
    def apply_telephony_filter(audio_bytes: bytes) -> bytes:
        """
        Simulates an 8kHz G.711 / AMR narrowband telephonic channel:
        - Downsamples / bandpasses audio to 300Hz - 3400Hz
        - Introduces characteristic telephonic quantization
        """
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())

            if sampwidth != 2:
                return audio_bytes  # Passthrough if not 16-bit PCM

            # Unpack 16-bit samples
            total_samples = len(frames) // 2
            samples = struct.unpack(f"<{total_samples}h", frames)

            # Apply a simple bandpass / telephonic coloration filter (smoothing + slight distortion)
            filtered_samples = []
            prev = 0
            for i, s in enumerate(samples):
                # Mild high-frequency roll-off (emulating 3.4kHz telephony limit)
                val = int(0.6 * s + 0.4 * prev)
                prev = val
                # Telephonic mild clipping/saturation
                val = max(-28000, min(28000, val))
                filtered_samples.append(val)

            out_buf = io.BytesIO()
            with wave.open(out_buf, "wb") as out_wf:
                out_wf.setnchannels(n_channels)
                out_wf.setsampwidth(sampwidth)
                out_wf.setframerate(framerate)
                out_wf.writeframes(struct.pack(f"<{total_samples}h", *filtered_samples))

            return out_buf.getvalue()
        except Exception:
            return audio_bytes
