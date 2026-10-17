from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncpg
from typing import Optional, Dict, Any, List
from decouple import config
import json
import base64
import io
import os
import tempfile
import wave

# Configuration
DATABASE_URL = config("DATABASE_URL", default="postgresql://zelia:zelia_secure_2024@postgres:5432/zelia")
FASTER_WHISPER_MODEL = config("FASTER_WHISPER_MODEL", default="base")
WHISPER_DEVICE = config("WHISPER_DEVICE", default="cpu")
WHISPER_COMPUTE_TYPE = config("WHISPER_COMPUTE_TYPE", default="int8")
WHISPER_BEAM_SIZE = int(config("WHISPER_BEAM_SIZE", default=5))
WHISPER_VAD_FILTER = config("WHISPER_VAD_FILTER", default="true").lower() == "true"
ASR_TEMPERATURE = float(config("ASR_TEMPERATURE", default="0.0"))
ASR_CONDITION_ON_PREVIOUS_TEXT = config("ASR_CONDITION_ON_PREVIOUS_TEXT", default="false").lower() == "true"
ASR_USE_LANGUAGE_PROMPTS = config("ASR_USE_LANGUAGE_PROMPTS", default="true").lower() == "true"
ASR_STRICT = config("ASR_STRICT", default="false").lower() == "true"

app = FastAPI(title="Voice Processor", version="1.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None
_whisper_model = None
_whisper_import_error: Optional[str] = None
_whisper_dependency_ready: Optional[bool] = None


def _normalize_text(text: str) -> str:
    return " ".join((text or "").strip().split())


def _wav_silence_base64(duration_ms: int = 800, sample_rate: int = 22050) -> str:
    frame_count = max(int(sample_rate * (duration_ms / 1000.0)), 1)
    pcm = b"\x00\x00" * frame_count
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _is_data_url(b64: str) -> bool:
    return b64.startswith("data:") and ";base64," in b64


def _decode_audio_base64(raw: str) -> bytes:
    payload = raw
    if _is_data_url(raw):
        payload = raw.split(";base64,", 1)[1]
    return base64.b64decode(payload)


def _ensure_whisper_model():
    global _whisper_model, _whisper_import_error
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:
        _whisper_import_error = str(exc)
        return None

    if _whisper_model is None:
        _whisper_model = WhisperModel(
            FASTER_WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    return _whisper_model


def _check_whisper_dependency() -> bool:
    global _whisper_dependency_ready, _whisper_import_error
    if _whisper_dependency_ready is not None:
        return _whisper_dependency_ready
    try:
        from faster_whisper import WhisperModel  # type: ignore # noqa: F401
        _whisper_dependency_ready = True
        _whisper_import_error = None
    except Exception as exc:
        _whisper_dependency_ready = False
        _whisper_import_error = str(exc)
    return _whisper_dependency_ready


def _normalize_language_code(language_code: str) -> str:
    raw = (language_code or "en").strip().lower()
    if raw.startswith("hi"):
        return "hi"
    if raw.startswith("ta"):
        return "ta"
    if raw.startswith("en"):
        return "en"
    if "-" in raw:
        return raw.split("-", 1)[0]
    return raw or "en"


def _asr_initial_prompt(lang: str) -> str:
    if lang == "hi":
        return "यह हिंदी वाक्य है। केवल देवनागरी लिपि में लिखें।"
    if lang == "ta":
        return "இது தமிழ் பேச்சு. தமிழ் எழுத்தில் மட்டும் எழுதவும்."
    return "This is English speech. Transcribe faithfully."


def _transcribe_with_faster_whisper(audio_bytes: bytes, language_code: str, mime_type: Optional[str] = None) -> str:
    model = _ensure_whisper_model()
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=f"ASR backend unavailable: faster-whisper import failed ({_whisper_import_error})",
        )

    suffix = ".wav"
    mt = (mime_type or "").lower()
    if "webm" in mt:
        suffix = ".webm"
    elif "mpeg" in mt or "mp3" in mt:
        suffix = ".mp3"
    elif "mp4" in mt or "m4a" in mt:
        suffix = ".m4a"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        lang = _normalize_language_code(language_code)
        prompt = _asr_initial_prompt(lang) if ASR_USE_LANGUAGE_PROMPTS else None
        segments, _ = model.transcribe(
            tmp_path,
            language=lang,
            task="transcribe",
            beam_size=WHISPER_BEAM_SIZE,
            temperature=ASR_TEMPERATURE,
            condition_on_previous_text=ASR_CONDITION_ON_PREVIOUS_TEXT,
            initial_prompt=prompt,
            vad_filter=WHISPER_VAD_FILTER,
        )
        text = " ".join(seg.text.strip() for seg in segments if seg.text).strip()
        return _normalize_text(text)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _synthesize_with_pyttsx3(text: str) -> str:
    try:
        import pyttsx3  # type: ignore
        engine = pyttsx3.init()
    except Exception:
        # Deterministic silent fallback to keep offline API contract available.
        return _wav_silence_base64(duration_ms=max(800, min(4000, len(text) * 25)))

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp_path = tmp.name

    try:
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return _wav_silence_base64(duration_ms=max(800, min(4000, len(text) * 25)))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.on_event("startup")
async def startup():
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    except Exception as e:
        print(f"Error connecting to database: {e}")


@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()


# Models
class TranscriptRequest(BaseModel):
    call_id: str
    transcript: List[Dict[str, str]]
    summary: Optional[str] = None
    duration: Optional[int] = 0
    end_reason: Optional[str] = "completed"


class ProcessResponse(BaseModel):
    status: str
    intent: str
    entities: Dict[str, Any]


class ASRRequest(BaseModel):
    call_id: Optional[str] = None
    language: Optional[str] = "en-IN"
    transcript_text: Optional[str] = None
    audio_base64: Optional[str] = None
    mime_type: Optional[str] = None


class TTSRequest(BaseModel):
    text: str
    language: Optional[str] = "en-IN"


class VoiceProcessRequest(BaseModel):
    call_id: Optional[str] = None
    language: Optional[str] = "en-IN"
    transcript_text: Optional[str] = None
    audio_base64: Optional[str] = None
    mime_type: Optional[str] = None


@app.get("/health")
async def health_check():
    dep_ready = _check_whisper_dependency()
    model_ready = _whisper_model is not None
    status = "ok"
    if ASR_STRICT and not dep_ready:
        status = "degraded"
    return {
        "status": status,
        "service": "voice-processor",
        "asr_backend": "faster-whisper",
        "asr_dependency_ready": dep_ready,
        "asr_ready": model_ready,
        "asr_strict": ASR_STRICT,
        "asr_error": _whisper_import_error,
        "asr_config": {
            "model": FASTER_WHISPER_MODEL,
            "device": WHISPER_DEVICE,
            "compute_type": WHISPER_COMPUTE_TYPE,
            "beam_size": WHISPER_BEAM_SIZE,
            "temperature": ASR_TEMPERATURE,
            "condition_on_previous_text": ASR_CONDITION_ON_PREVIOUS_TEXT,
            "language_prompts": ASR_USE_LANGUAGE_PROMPTS,
            "vad_filter": WHISPER_VAD_FILTER,
        },
        "tts_backend": "pyttsx3 (optional)",
    }


@app.get("/asr/health")
async def asr_health():
    dep_ready = _check_whisper_dependency()
    model_ready = _whisper_model is not None
    if ASR_STRICT and not dep_ready:
        raise HTTPException(status_code=503, detail={"asr_ready": False, "error": _whisper_import_error})
    return {
        "asr_dependency_ready": dep_ready,
        "asr_ready": model_ready,
        "error": _whisper_import_error,
        "strict": ASR_STRICT,
        "model": FASTER_WHISPER_MODEL,
    }


@app.post("/asr/transcribe")
async def asr_transcribe(req: ASRRequest):
    if req.transcript_text:
        text = _normalize_text(req.transcript_text)
        return {
            "status": "ok",
            "transcript": text,
            "language": req.language,
            "source": "provided_text",
        }

    if not req.audio_base64:
        raise HTTPException(status_code=400, detail="Provide transcript_text or audio_base64")

    try:
        audio_bytes = _decode_audio_base64(req.audio_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid audio_base64 payload: {exc}")

    transcript = _transcribe_with_faster_whisper(audio_bytes, req.language or "en-IN", req.mime_type)
    return {
        "status": "ok",
        "transcript": transcript,
        "language": req.language,
        "source": "faster_whisper",
    }


@app.post("/asr/transcribe-file")
async def asr_transcribe_file(
    file: UploadFile = File(...),
    language: str = Form("en-IN"),
):
    audio_bytes = await file.read()
    transcript = _transcribe_with_faster_whisper(audio_bytes, language, file.content_type)
    return {
        "status": "ok",
        "transcript": transcript,
        "language": language,
        "source": "faster_whisper_file",
        "mime_type": file.content_type or "application/octet-stream",
    }


@app.post("/tts/synthesize")
async def tts_synthesize(req: TTSRequest):
    text = _normalize_text(req.text)
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    wav_b64 = _synthesize_with_pyttsx3(text)
    return {
        "status": "ok",
        "language": req.language,
        "mime_type": "audio/wav",
        "audio_base64": wav_b64,
    }


@app.post("/voice/process")
async def voice_process(req: VoiceProcessRequest):
    asr = await asr_transcribe(
        ASRRequest(
            call_id=req.call_id,
            language=req.language,
            transcript_text=req.transcript_text,
            audio_base64=req.audio_base64,
            mime_type=req.mime_type,
        )
    )
    text = (asr.get("transcript") or "").lower()

    intent = "general_inquiry"
    if "scheme" in text or "benefit" in text:
        intent = "scheme_inquiry"
    elif "upload" in text or "document" in text:
        intent = "document_upload"
    elif "status" in text or "check" in text:
        intent = "status_check"

    return {
        "status": "processed",
        "intent": intent,
        "transcript": asr.get("transcript"),
        "entities": {},
    }


@app.post("/process", response_model=ProcessResponse)
async def process_transcript(req: TranscriptRequest):
    """
    Process transcript to detect intent and extract entities.
    Called by N8N workflow.
    """
    full_text = " ".join([m.get("text", "") for m in req.transcript])
    full_text_lower = full_text.lower()

    intent = "general_inquiry"
    if "scheme" in full_text_lower or "benefit" in full_text_lower:
        intent = "scheme_inquiry"
    elif "upload" in full_text_lower or "document" in full_text_lower:
        intent = "document_upload"
    elif "status" in full_text_lower or "check" in full_text_lower:
        intent = "status_check"

    # Save transcript to DB
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO call_transcripts (call_id, full_transcript, summary, detected_intent, duration, end_reason, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (call_id) DO UPDATE
                SET full_transcript = EXCLUDED.full_transcript,
                    detected_intent = EXCLUDED.detected_intent,
                    updated_at = NOW()
                """,
                req.call_id,
                full_text,
                req.summary or "No summary",
                intent,
                req.duration,
                req.end_reason,
                json.dumps({"message_count": len(req.transcript)}),
            )

            await conn.execute(
                "UPDATE active_calls SET status = 'completed', updated_at = NOW() WHERE call_id = $1",
                req.call_id,
            )

    return {
        "status": "processed",
        "intent": intent,
        "entities": {},
    }


@app.get("/transcript/{call_id}")
async def get_transcript(call_id: str):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not initialized")

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM call_transcripts WHERE call_id = $1",
            call_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Transcript not found")

        data = dict(row)
        return {
            "callId": data["call_id"],
            "transcript": data["full_transcript"],
            "intent": data["detected_intent"],
            "formPrefill": {},
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
