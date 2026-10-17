"""
Intent Detector Service for ZELIA
Uses Google Gemini or OpenAI GPT to detect user intent from voice transcripts
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os
import httpx
import json

app = FastAPI(title="ZELIA Intent Detector", version="1.1.0")

# API Keys - Groq preferred, then Gemini, then OpenAI
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-0125")

from groq import Groq

# Initialize Groq client if key exists
groq_client = None
if GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Failed to initialize Groq client: {e}")

class IntentRequest(BaseModel):
    query: str | None = None
    transcript: str | None = None
    language: str = "en"
    context: str = "government_scheme"
    call_id: str | None = None

class EntitySchema(BaseModel):
    scheme_name: str | None = Field(None, description="Name of the government scheme")
    applicant_name: str | None = Field(None, description="Full name of the applicant")
    age: int | None = Field(None, description="Age of the applicant")
    gender: str | None = Field(None, description="Gender (male/female/other)")
    phone_number: str | None = Field(None, description="Phone number if mentioned")
    district: str | None = Field(None, description="District name")
    state_code: str | None = Field(None, description="Two letter state code e.g. KA, TN")
    annual_income: int | None = Field(None, description="Annual income in numbers")
    occupation: str | None = Field(None, description="Occupation/Profession")
    caste_category: str | None = Field(None, description="Category (SC/ST/OBC/General)")
    marital_status: str | None = Field(None, description="Single/Married/Widowed/Divorced")
    document_type: str | None = Field(None, description="Type of document mentioned")
    
class IntentResponse(BaseModel):
    detected_intent: str = Field(..., description="Classified intent")
    confidence: float = Field(..., description="Confidence score between 0 and 1")
    entities: EntitySchema = Field(default_factory=EntitySchema, description="Extracted entities")
    raw_query: str
    call_id: str | None = None
    status: str = "processed"

INTENT_PROMPT = """You are an expert intent detection system for ZELIA (Government Scheme Assistant).
Analyze the user's message and classify it into one of these intents:
- document_upload: User wants to upload/submit documents
- scheme_info: User asks about scheme details/benefits
- eligibility_check: User checks eligibility (mentions personal details)
- document_fill_request: User wants to fill an application form (e.g. "Apply for pension", "Fill form")
- application_status: User asks status of application
- greeting: Hello/Hi
- help: Needs help
- unknown: Cannot determine intent

EXTRACT ENTITIES strictly. If a value is not found, use null.
Focus heavily on: applicant_name, age, scheme_name, district.

User message: {query}
"""

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Intent Detector",
        "groq_configured": bool(GROQ_API_KEY),
        "gemini_configured": bool(GEMINI_API_KEY),
        "openai_configured": bool(OPENAI_API_KEY),
        "llm_provider": "groq" if GROQ_API_KEY else ("gemini" if GEMINI_API_KEY else ("openai" if OPENAI_API_KEY else "fallback"))
    }

@app.post("/detect-intent", response_model=IntentResponse)
async def detect_intent(request: IntentRequest):
    """Detect intent with strict JSON structure"""
    
    query_text = request.query or request.transcript
    if not query_text:
        raise HTTPException(status_code=400, detail="Either 'query' or 'transcript' is required")
    
    # Try Groq first (Parallel Tool Call or JSON Mode)
    if groq_client:
        try:
            completion = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": INTENT_PROMPT.format(query=query_text)},
                    {"role": "user", "content": query_text}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            content = completion.choices[0].message.content
            data = json.loads(content)
            
            # Map loose JSON to Strict Schema
            return IntentResponse(
                detected_intent=data.get("intent", "unknown"),
                confidence=data.get("confidence", 0.8),
                entities=data.get("entities", {}), # Pydantic will validate this
                raw_query=query_text,
                call_id=request.call_id
            )
        except Exception as e:
            print(f"Groq error: {e}")
            # Fallthrough to next provider
            
    # Try Gemini second
    if GEMINI_API_KEY:
        result = await call_gemini(query_text)
        if result:
            result.call_id = request.call_id
            return result
    
    # Fallback to OpenAI
    if OPENAI_API_KEY:
        result = await call_openai(query_text)
        if result:
            result.call_id = request.call_id
            return result
    
    # Final fallback to rule-based
    result = fallback_intent_detection(query_text)
    result.call_id = request.call_id
    return result

async def call_groq(query: str) -> IntentResponse | None:
    """Call Groq API"""
    try:
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": INTENT_PROMPT},
                {"role": "user", "content": query}
            ],
            model=GROQ_MODEL,
            temperature=0.3,
            max_tokens=200,
            response_format={"type": "json_object"}
        )
        
        content = completion.choices[0].message.content
        try:
            parsed = json.loads(content)
            return IntentResponse(
                detected_intent=parsed.get("intent", "unknown"),
                confidence=parsed.get("confidence", 0.5),
                entities=parsed.get("entities", {}),
                raw_query=query
            )
        except json.JSONDecodeError:
            print(f"Failed to parse Groq response: {content}")
            return None
            
    except Exception as e:
        print(f"Error calling Groq: {e}")
        return None
            
async def call_gemini(query: str) -> IntentResponse | None:
    """Call Google Gemini API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [{"text": INTENT_PROMPT + query}]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 200
                    }
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"Gemini API error: {response.text}")
                return None
            
            result = response.json()
            try:
                content = result["candidates"][0]["content"]["parts"][0]["text"]
            except KeyError:
                print(f"Unexpected Gemini response structure: {result}")
                return None
            
            # Extract JSON from response
            try:
                # Handle markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                parsed = json.loads(content.strip())
                return IntentResponse(
                    detected_intent=parsed.get("intent", "unknown"),
                    confidence=parsed.get("confidence", 0.5),
                    entities=parsed.get("entities", {}),
                    raw_query=query
                )
            except json.JSONDecodeError:
                print(f"Failed to parse Gemini response: {content}")
                return None
                
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return None

async def call_openai(query: str) -> IntentResponse | None:
    """Call OpenAI API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": INTENT_PROMPT},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"OpenAI API error: {response.text}")
                return None
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            try:
                parsed = json.loads(content)
                return IntentResponse(
                    detected_intent=parsed.get("intent", "unknown"),
                    confidence=parsed.get("confidence", 0.5),
                    entities=parsed.get("entities", {}),
                    raw_query=query
                )
            except json.JSONDecodeError:
                return None
                
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return None

def fallback_intent_detection(query: str) -> IntentResponse:
    """Rule-based fallback when APIs are unavailable"""
    query_lower = query.lower()
    import re
    
    intent = "unknown"
    confidence = 0.3
    entities = {}

    # 1. Detect Intent
    if any(word in query_lower for word in ["apply", "fill form", "fill application", "process"]):
        intent, confidence = "document_fill_request", 0.8
    elif any(word in query_lower for word in ["upload", "submit", "document", "attach", "send"]):
        intent, confidence = "document_upload", 0.7
    elif any(word in query_lower for word in ["eligible", "qualify", "can i apply", "am i eligible", "year old", "earning", "income", "rupees"]):
        # Expanded keywords to catch "I am a 65 year old..." statements
        intent, confidence = "eligibility_check", 0.8
    elif any(word in query_lower for word in ["what is", "tell me about", "explain", "benefits", "how to"]):
        intent, confidence = "scheme_info", 0.6
    elif any(word in query_lower for word in ["status", "application", "track", "where is"]):
        intent, confidence = "application_status", 0.7
    elif any(word in query_lower for word in ["hello", "hi", "namaste", "good morning"]):
        intent, confidence = "greeting", 0.9
    elif any(word in query_lower for word in ["help", "don't know", "confused"]):
        intent, confidence = "help", 0.6
        
    # 2. Extract Entities (Regex Fallback)
    if intent == "eligibility_check":
        # Extract Age
        age_match = re.search(r'(\d+)\s*(?:years?|yrs?)\s*old', query_lower)
        if age_match:
            entities['age'] = int(age_match.group(1))
            
        # Extract Income (monthly)
        # Matches: "earning 5000", "5000 rupees", "income is 5000"
        income_match = re.search(r'(?:earning|income|salary|rupees|rs\.?)\s*:?\s*(\d+)', query_lower) or \
                       re.search(r'(\d+)\s*(?:rupees|rs)', query_lower)
        if income_match:
            entities['monthly_income'] = int(income_match.group(1))
            
        # Extract Occupation
        occupations = ["farmer", "student", "teacher", "driver", "laborer", "worker", "widow", "unemployed", "retired"]
        for job in occupations:
            if job in query_lower:
                entities['occupation'] = job
                break
                
        # Extract State (simple lookup)
        states = {"tamil nadu": "TN", "kerala": "KL", "karnataka": "KA", "maharashtra": "MH", "delhi": "DL"}
        for state_name, code in states.items():
            if state_name in query_lower:
                entities['state_code'] = code
                break

    return IntentResponse(
        detected_intent=intent,
        confidence=confidence,
        entities=entities,
        raw_query=query
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
