"""
KisanSetu (किसान सेतु) — FastAPI Backend
Sovereign Vernacular AI Voice Desk for Bharat's Farmers
Powered by Gnani Artha (Prisma v2.5 STT & Timbre v2.5 TTS)
"""

import os
import base64
import time
import logging
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env file
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

import sys
sys.path.append(os.path.dirname(__file__))

from gnani_client import GnaniClient, LANGUAGE_MAP
from indic_reasoner import IndicReasoner
from audio_processor import AudioProcessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(
    title="KisanSetu Voice Desk",
    description="Sovereign Vernacular Voice AI Desk for Bharat Farmers powered by Gnani AI",
    version="1.0.0"
)

# Enable CORS for frontend flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services
gnani = GnaniClient()
reasoner = IndicReasoner()
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


class TextQueryRequest(BaseModel):
    query: str
    language_code: Optional[str] = "hi-IN"
    voice: Optional[str] = "Nalini"


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "KisanSetu Sovereign Voice AI",
        "gnani_models": {
            "stt": "gnani-prisma-v2.5",
            "tts": "timbre-v2.5"
        }
    }


@app.post("/api/voice-query")
async def handle_voice_query(
    audio_file: UploadFile = File(...),
    language_code: str = Form("hi-IN"),
    noise_mode: str = Form("clean"),
    voice: str = Form("Nalini")
):
    """
    Main Voice Pipeline:
    1. Receive voice stream from farmer
    2. Optional Telephony 8kHz filter if noise_mode == 'telephony'
    3. Transcribe via Gnani Prisma v2.5
    4. Reason via Indic Agri Engine (Mandi / Disease / Schemes)
    5. Synthesize speech via Gnani Timbre v2.5
    6. Return real-time audio + cards + latency metrics
    """
    overall_start = time.perf_counter()

    try:
        audio_bytes = await audio_file.read()
        if not audio_bytes or len(audio_bytes) < 100:
            raise HTTPException(status_code=400, detail="Empty or invalid audio recorded.")

        # If telephony mode requested, apply 8kHz narrowband filter
        if noise_mode == "telephony":
            audio_bytes = AudioProcessor.apply_telephony_filter(audio_bytes)

        # Step 1: Transcribe via Gnani Prisma v2.5
        stt_result = gnani.transcribe_audio(
            audio_bytes=audio_bytes,
            language_code=language_code,
            filename=audio_file.filename or "voice.wav"
        )

        if not stt_result.get("success"):
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": stt_result.get("error", "Prisma STT failed"),
                    "stt_latency_ms": stt_result.get("stt_latency_ms", 0)
                }
            )

        transcript = stt_result.get("transcript", "").strip()

        # Step 2: Reason through Indic Agri Engine
        reasoning = reasoner.process_query(transcript, language_code)
        voice_response_text = reasoning.get("voice_response", "")

        # Step 3: Synthesize Speech via Gnani Timbre v2.5
        tts_audio_bytes, tts_latency_ms = gnani.synthesize_speech(
            text=voice_response_text,
            language=language_code,
            voice=voice,
            speed=1.0
        )

        total_latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)

        # Convert audio to base64 data URI if synthesized successfully
        audio_data_uri = None
        if tts_audio_bytes:
            audio_b64 = base64.b64encode(tts_audio_bytes).decode("utf-8")
            audio_data_uri = f"data:audio/wav;base64,{audio_b64}"

        return {
            "success": True,
            "transcript": transcript,
            "intent": reasoning.get("intent"),
            "title": reasoning.get("title"),
            "voice_response": voice_response_text,
            "card_data": reasoning.get("data"),
            "audio_url": audio_data_uri,
            "fallback_tts": (tts_audio_bytes is None),
            "metrics": {
                "stt_model": stt_result.get("model", "gnani-prisma-v2.5"),
                "tts_model": "timbre-v2.5" if tts_audio_bytes else "browser-speech-fallback",
                "stt_latency_ms": stt_result.get("stt_latency_ms"),
                "tts_latency_ms": tts_latency_ms,
                "total_roundtrip_ms": total_latency_ms,
                "noise_mode": noise_mode
            }
        }

    except Exception as e:
        logging.exception(f"Error handling voice query: {e}")
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


@app.post("/api/text-query")
def handle_text_query(req: TextQueryRequest):
    """Text-based query for rapid testing and fallback."""
    overall_start = time.perf_counter()
    reasoning = reasoner.process_query(req.query, req.language_code)
    voice_response_text = reasoning.get("voice_response", "")

    tts_audio_bytes, tts_latency_ms = gnani.synthesize_speech(
        text=voice_response_text,
        language=req.language_code,
        voice=req.voice or "Nalini"
    )

    audio_data_uri = None
    if tts_audio_bytes:
        audio_b64 = base64.b64encode(tts_audio_bytes).decode("utf-8")
        audio_data_uri = f"data:audio/wav;base64,{audio_b64}"

    total_latency_ms = round((time.perf_counter() - overall_start) * 1000, 2)

    return {
        "success": True,
        "query": req.query,
        "intent": reasoning.get("intent"),
        "title": reasoning.get("title"),
        "voice_response": voice_response_text,
        "card_data": reasoning.get("data"),
        "audio_url": audio_data_uri,
        "fallback_tts": (tts_audio_bytes is None),
        "metrics": {
            "tts_latency_ms": tts_latency_ms,
            "total_roundtrip_ms": total_latency_ms
        }
    }


@app.get("/api/mandi-rates")
def get_mandi_rates():
    return reasoner.mandi_data


@app.get("/api/crop-advisory")
def get_crop_advisory():
    return reasoner.crop_data


@app.get("/api/schemes")
def get_schemes():
    return reasoner.scheme_data


# Mount frontend static directory
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
