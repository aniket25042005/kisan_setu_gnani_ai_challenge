"""
Gnani AI Client Wrapper for KisanSetu
Supports:
- Prisma v2.5 (Speech to Text)
- Timbre v2.5 (Text to Speech)
"""

import os
import time
import uuid
import json
import logging
from typing import Optional, Dict, Any, Tuple
import urllib.request
import urllib.error

# Load environment variable if present
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "")

STT_ENDPOINT = "https://api.vachana.ai/stt/v3"
TTS_ENDPOINT = "https://api.vachana.ai/api/v1/tts/inference"

# Standard User-Agent to avoid Cloudflare 1010 blocking
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Supported Indic languages mapping
LANGUAGE_MAP = {
    "hi": {"code": "hi-IN", "name": "Hindi", "default_voice": "Nalini"},
    "mr": {"code": "mr-IN", "name": "Marathi", "default_voice": "Nalini"},
    "te": {"code": "te-IN", "name": "Telugu", "default_voice": "Nalini"},
    "kn": {"code": "kn-IN", "name": "Kannada", "default_voice": "Nalini"},
    "ta": {"code": "ta-IN", "name": "Tamil", "default_voice": "Nalini"},
    "bn": {"code": "bn-IN", "name": "Bengali", "default_voice": "Nalini"},
    "gu": {"code": "gu-IN", "name": "Gujarati", "default_voice": "Nalini"},
    "en": {"code": "en-IN", "name": "Indian English", "default_voice": "Nalini"}
}


class GnaniClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GNANI_API_KEY
        if not self.api_key:
            raise ValueError("Gnani API key is missing. Set GNANI_API_KEY in environment or pass to client.")
        self.cache_dir = os.path.join(os.path.dirname(__file__), "cache", "tts_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

    def transcribe_audio(
        self,
        audio_bytes: bytes,
        language_code: str = "hi-IN",
        filename: str = "audio.wav"
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Gnani Prisma v2.5.
        Auto-detects container format (WAV, WebM, OGG, MP3) from magic bytes
        to prevent FFmpeg decoding errors.
        """
        start_time = time.perf_counter()
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"

        # Detect container from magic bytes
        content_type = "audio/wav"
        actual_filename = filename

        if audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
            content_type = "audio/webm"
            actual_filename = "audio.webm"
        elif audio_bytes.startswith(b"OggS"):
            content_type = "audio/ogg"
            actual_filename = "audio.ogg"
        elif audio_bytes.startswith(b"ID3") or audio_bytes[:2] in [b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"]:
            content_type = "audio/mpeg"
            actual_filename = "audio.mp3"
        elif audio_bytes.startswith(b"RIFF"):
            content_type = "audio/wav"
            actual_filename = "audio.wav"

        headers = {
            "X-API-Key-ID": self.api_key,
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": USER_AGENT
        }

        # Build multipart/form-data payload
        body = bytearray()
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="audio_file"; filename="{actual_filename}"\r\n'.encode("utf-8"))
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(audio_bytes)
        body.extend(b"\r\n")

        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(b'Content-Disposition: form-data; name="language_code"\r\n\r\n')
        body.extend(f"{language_code}\r\n".encode("utf-8"))

        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        req = urllib.request.Request(STT_ENDPOINT, data=bytes(body), headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
                raw_json = json.loads(resp.read().decode("utf-8"))
                
                transcript = raw_json.get("transcript", "")
                if not transcript and "output" in raw_json:
                    transcript = raw_json["output"].get("literal", "")

                return {
                    "success": True,
                    "transcript": transcript,
                    "model": raw_json.get("model", "gnani-prisma-v2.5"),
                    "stt_latency_ms": elapsed_ms,
                    "gnani_processing_time": raw_json.get("processing_time", 0.0),
                    "request_id": raw_json.get("request_id", "")
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logging.error(f"Gnani STT HTTP {e.code}: {err_body}")
            return {
                "success": False,
                "error": f"HTTP {e.code}: {err_body}",
                "transcript": ""
            }
        except Exception as e:
            logging.error(f"Gnani STT Exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "transcript": ""
            }

    def _get_cache_path(self, text: str, language: str, voice: str) -> str:
        import hashlib
        key = f"{text}_{language}_{voice}".encode("utf-8")
        h = hashlib.md5(key).hexdigest()
        return os.path.join(self.cache_dir, f"{h}.wav")

    def synthesize_speech(
        self,
        text: str,
        language: str = "hi-IN",
        voice: str = "Nalini",
        speed: float = 1.0,
        sample_rate: int = 24000
    ) -> Tuple[Optional[bytes], float]:
        """
        Synthesize text to speech using Gnani Timbre v2.5.
        Includes:
        1. Fast disk caching (0ms latency & saves 5,000 credits)
        2. Automatic retry on HTTP 429 (Rate Limit)
        3. Graceful fallback without crashing
        """
        start_time = time.perf_counter()

        # Check local cache first
        cache_path = self._get_cache_path(text, language, voice)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "rb") as cf:
                    cached_bytes = cf.read()
                    if len(cached_bytes) > 100:
                        logging.info("Serving TTS audio from local cache (0ms Gnani cost)")
                        return cached_bytes, 1.0
            except Exception as e:
                logging.warning(f"Cache read error: {e}")

        headers = {
            "Content-Type": "application/json",
            "X-API-Key-ID": self.api_key,
            "User-Agent": USER_AGENT
        }

        payload = {
            "text": text,
            "voice": voice,
            "model": "timbre-v2.5",
            "language": language,
            "speed": speed,
            "audio_config": {
                "sample_rate": sample_rate,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav"
            }
        }

        max_retries = 2
        for attempt in range(max_retries + 1):
            req = urllib.request.Request(
                TTS_ENDPOINT,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )

            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    audio_bytes = resp.read()
                    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

                    # Save to local cache
                    try:
                        with open(cache_path, "wb") as cf:
                            cf.write(audio_bytes)
                    except Exception as ce:
                        logging.warning(f"Failed to write TTS cache: {ce}")

                    return audio_bytes, elapsed_ms

            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                if e.code == 429 and attempt < max_retries:
                    wait_time = 2.0 * (attempt + 1)
                    logging.warning(f"Gnani TTS rate limited (429). Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                
                logging.error(f"Gnani TTS HTTP {e.code}: {err_body}")
                if e.code == 429:
                    # Return None gracefully instead of crashing the server
                    return None, round((time.perf_counter() - start_time) * 1000, 2)
                raise RuntimeError(f"Gnani TTS Error {e.code}: {err_body}")

            except Exception as e:
                logging.error(f"Gnani TTS Exception: {e}")
                return None, round((time.perf_counter() - start_time) * 1000, 2)

        return None, round((time.perf_counter() - start_time) * 1000, 2)
