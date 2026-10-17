"""
ZELIA Translation Service - Sarvam AI Integration
Provides multilingual translation for scheme data and user interactions
"""
import os
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import json
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ZELIA Translation Service",
    version="1.0.0",
    description="Multilingual translation using Sarvam AI"
)

# Configuration
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_BASE_URL = "https://api.sarvam.ai"
TRANSLATION_TIMEOUT = 30

# Language Codes
SUPPORTED_LANGUAGES = {
    "en-IN": "English",
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "ml-IN": "Malayalam",
    "te-IN": "Telugu",
    "bn-IN": "Bengali",
    "mr-IN": "Marathi",
    "gu-IN": "Gujarati",
    "kn-IN": "Kannada",
    "pa-IN": "Punjabi",
    "or-IN": "Odia"
}

# Fallback Translations Dictionary
FALLBACK_TRANSLATIONS = {
    "hi-IN": {
        "pension": "पेंशन",
        "widow": "विधवा",
        "old age": "वृद्धावस्था",
        "disability": "विकलांगता",
        "housing": "आवास",
        "scheme": "योजना",
        "eligibility": "पात्रता",
        "benefits": "लाभ",
        "documents": "दस्तावेज़",
        "apply": "आवेदन करें",
        "income": "आय",
        "age": "उम्र",
        "name": "नाम",
        "address": "पता"
    },
    "ta-IN": {
        "pension": "ஓய்வூதியம்",
        "widow": "விதவை",
        "old age": "முதுமை",
        "disability": "ஊனம்",
        "housing": "வீட்டுவசதி",
        "scheme": "திட்டம்",
        "eligibility": "தகுதி",
        "benefits": "நன்மைகள்",
        "documents": "ஆவணங்கள்",
        "apply": "விண்ணப்பிக்கவும்",
        "income": "வருமானம்",
        "age": "வயது",
        "name": "பெயர்",
        "address": "முகவரி"
    },
    "ml-IN": {
        "pension": "പെൻഷൻ",
        "widow": "വിധവ",
        "old age": "വാർധക്യം",
        "disability": "വൈകല്യം",
        "housing": "ഭവനം",
        "scheme": "പദ്ധതി",
        "eligibility": "യോഗ്യത",
        "benefits": "ആനുകൂല്യങ്ങൾ",
        "documents": "രേഖകൾ",
        "apply": "അപേക്ഷിക്കുക",
        "income": "വരുമാനം",
        "age": "പ്രായം",
        "name": "പേര്",
        "address": "വിലാസം"
    }
}

# Request/Response Models
class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "en-IN"
    target_lang: str = "hi-IN"

class BatchTranslateRequest(BaseModel):
    texts: List[str]
    source_lang: str = "en-IN"
    target_lang: str = "hi-IN"

class DocumentTranslateRequest(BaseModel):
    fields: Dict[str, str]
    target_lang: str = "hi-IN"

class TranslateResponse(BaseModel):
    translated_text: str
    source_lang: str
    target_lang: str
    method: str  # "api" or "fallback"

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "translation-service",
        "api_configured": bool(SARVAM_API_KEY),
        "supported_languages": list(SUPPORTED_LANGUAGES.keys())
    }

@lru_cache(maxsize=1000)
def _cached_translate(text: str, source_lang: str, target_lang: str) -> tuple:
    """Cached translation to reduce API calls"""
    try:
        return _translate_with_sarvam(text, source_lang, target_lang), "api"
    except Exception as e:
        logger.warning(f"API translation failed: {e}, using fallback")
        return _fallback_translate(text, target_lang), "fallback"

def _translate_with_sarvam(text: str, source_lang: str, target_lang: str) -> str:
    """Translate using Sarvam AI API"""
    if not SARVAM_API_KEY:
        raise ValueError("SARVAM_API_KEY not configured")
    
    try:
        with httpx.Client(timeout=TRANSLATION_TIMEOUT) as client:
            response = client.post(
                f"{SARVAM_BASE_URL}/translate",
                headers={
                    "Authorization": f"Bearer {SARVAM_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": text,
                    "source_language_code": source_lang,
                    "target_language_code": target_lang,
                    "speaker_gender": "Male",
                    "mode": "formal",
                    "model": "mayura:v1",
                    "enable_preprocessing": True
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("translated_text", text)
            else:
                raise Exception(f"Sarvam AI API error: {response.status_code}")
                
    except httpx.TimeoutException:
        raise Exception("Translation timeout")
    except httpx.ConnectError:
        raise Exception("Cannot connect to Sarvam AI")

def _fallback_translate(text: str, target_lang: str) -> str:
    """Simple dictionary-based fallback translation"""
    if target_lang not in FALLBACK_TRANSLATIONS:
        return text
    
    translations = FALLBACK_TRANSLATIONS[target_lang]
    text_lower = text.lower()
    
    for eng, translated in translations.items():
        if eng in text_lower:
            text = text.replace(eng, translated)
            text = text.replace(eng.title(), translated)
    
    return text

@app.post("/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """
    Translate single text from source to target language
    """
    try:
        # Skip translation if already in target language or both are English
        if request.source_lang == request.target_lang or request.target_lang == "en-IN":
            return TranslateResponse(
                translated_text=request.text,
                source_lang=request.source_lang,
                target_lang=request.target_lang,
                method="skip"
            )
        
        translated, method = _cached_translate(
            request. text,
            request.source_lang,
            request.target_lang
        )
        
        logger.info(f"Translated '{request.text[:50]}...' via {method}")
        
        return TranslateResponse(
            translated_text=translated,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            method=method
        )
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/translate/batch")
async def translate_batch(request: BatchTranslateRequest):
    """
    Translate multiple texts at once
    """
    results = []
    
    for text in request.texts:
        try:
            translated, method = _cached_translate(
                text,
                request.source_lang,
                request.target_lang
            )
            results.append({
                "original": text,
                "translated": translated,
                "method": method
            })
        except Exception as e:
            logger.error(f"Failed to translate '{text}': {e}")
            results.append({
                "original": text,
                "translated": text,  # Return original on error
                "method": "error",
                "error": str(e)
            })
    
    return {
        "total": len(request.texts),
        "results": results,
        "source_lang": request.source_lang,
        "target_lang": request.target_lang
    }

@app.post("/translate/document")
async def translate_document(request: DocumentTranslateRequest):
    """
    Translate document fields (for canonical field values)
    """
    translated_fields = {}
    
    for field_name, field_value in request.fields.items():
        try:
            # Only translate text fields, preserve numbers and codes
            if field_value and isinstance(field_value, str) and not field_value.isdigit():
                translated, method = _cached_translate(
                    field_value,
                    "en-IN",
                    request.target_lang
                )
                translated_fields[field_name] = translated
            else:
                translated_fields[field_name] = field_value
        except Exception as e:
            logger.error(f"Failed to translate field '{field_name}': {e}")
            translated_fields[field_name] = field_value
    
    return {
        "translated_fields": translated_fields,
        "target_lang": request.target_lang
    }

@app.get("/languages")
def get_supported_languages():
    """Get list of supported languages"""
    return {
        "languages": SUPPORTED_LANGUAGES,
        "total": len(SUPPORTED_LANGUAGES)
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8009))
    uvicorn.run(app, host="0.0.0.0", port=port)
