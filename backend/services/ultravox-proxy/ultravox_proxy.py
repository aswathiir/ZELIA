"""
ZELIA Ultravox Proxy - Enhanced with Agent-Specific Configuration
Manages voice AI sessions using Ultravox Agent ID: 6cead17c-30da-43b7-b5ec-f1d271d828d0
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import httpx
import os
import json
import uvicorn

app = FastAPI(
    title="ZELIA Ultravox Proxy",
    description="Voice session manager for Ultravox AI with ZELIA Query Processor",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration from ULTRAVOX_AGENT_REFERENCE.md
ULTRAVOX_API_KEY = os.getenv('ULTRAVOX_API_KEY', '')
ULTRAVOX_AGENT_ID = os.getenv('ULTRAVOX_AGENT_ID', "6cead17c-30da-43b7-b5ec-f1d271d828d0")
ULTRAVOX_BASE_URL = "https://api.ultravox.ai/api"
ULTRAVOX_STRICT = os.getenv("ULTRAVOX_STRICT", "true").lower() == "true"

# Language mapping
LANGUAGE_HINTS = {
    'ta-IN': 'ta',
    'hi-IN': 'hi',
    'te-IN': 'te',
    'kn-IN': 'kn',
    'ml-IN': 'ml',
    'en-IN': 'en'
}


class VoiceSessionRequest(BaseModel):
    language: str = "ta-IN"
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


class VoiceSessionResponse(BaseModel):
    call_id: str
    join_url: str
    status: str
    agent_id: str


class VoiceQueryRequest(BaseModel):
    transcript: str
    language: str
    call_id: Optional[str] = None
    extracted_entities: Optional[Dict[str, Any]] = None


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ZELIA Ultravox Proxy",
        "agent_id": ULTRAVOX_AGENT_ID,
        "configured": bool(ULTRAVOX_API_KEY),
        "strict_live": ULTRAVOX_STRICT,
        "supported_languages": list(LANGUAGE_HINTS.keys())
    }


@app.post("/create-session", response_model=VoiceSessionResponse)
async def create_voice_session(request: VoiceSessionRequest):
    """
    Create a new Ultravox voice session using the configured ZELIA agent.
    
    The agent is pre-configured with:
    - System prompt as ZELIA Query Processor
    - Interview questions for household data collection
    - Entity extraction for profile building
    """
    
    if not ULTRAVOX_API_KEY:
        raise HTTPException(
            status_code=500, 
            detail="Ultravox API key not configured. Set ULTRAVOX_API_KEY environment variable."
        )
    
    try:
        # Get language hint (e.g., 'ta' from 'ta-IN')
        language_hint = LANGUAGE_HINTS.get(request.language, 'en')
        
        # Prepare call request
        # Note: languageHint and temperature are not valid top-level fields in StartAgentCallRequest
        # They should be configured in the Agent itself or passed differently if supported.
        # for now, we remove them to fix the 400 error.
        call_payload = {
            "maxDuration": "1800s"
        }
        
        # Note: context should be passed via metadata or templateContext if needed
        # initialContext is not a valid field per API schema
        
        # Create call through Ultravox API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ULTRAVOX_BASE_URL}/agents/{ULTRAVOX_AGENT_ID}/calls",
                headers={
                    "X-API-Key": ULTRAVOX_API_KEY,
                    "Content-Type": "application/json"
                },
                json=call_payload
            )
            
            if response.status_code not in [200, 201]:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get('detail', error_detail)
                except:
                    pass
                
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ultravox API error: {error_detail}"
                )
            
            data = response.json()
            
            call_id = data.get("callId")
            join_url = data.get("joinUrl")
            if ULTRAVOX_STRICT and (not call_id or not join_url):
                raise HTTPException(status_code=502, detail=f"Live Ultravox response missing callId/joinUrl: {data}")

            return VoiceSessionResponse(
                call_id=call_id,
                join_url=join_url,
                status=data.get("status", "created"),
                agent_id=ULTRAVOX_AGENT_ID
            )
    
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, 
            detail="Ultravox API request timed out. Please try again."
        )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Network error connecting to Ultravox: {str(e)}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Session creation failed: {repr(e)}"
        )


@app.get("/session/{call_id}/status")
async def get_session_status(call_id: str):
    """
    Get the current status of a voice session.
    
    Returns:
    - callId: Unique identifier
    - status: created | connecting | active | idle | ended | error
    - duration: Call duration in seconds
    - transcript: Conversation transcript (if available)
    - metadata: Additional call information
    """
    
    if not ULTRAVOX_API_KEY:
        raise HTTPException(status_code=500, detail="Ultravox API key not configured")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{ULTRAVOX_BASE_URL}/agents/{ULTRAVOX_AGENT_ID}/calls/{call_id}",
                headers={"X-API-Key": ULTRAVOX_API_KEY}
            )
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {call_id} not found. It may have expired or never existed."
                )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to retrieve session status: {response.text}"
                )
            
            data = response.json()
            
            # Enrich response with ZELIA-specific metadata
            return {
                "call_id": data.get("callId"),
                "agent_id": ULTRAVOX_AGENT_ID,
                "status": data.get("status"),
                "duration": data.get("duration", 0),
                "transcript": data.get("transcript"),
                "metadata": data.get("metadata", {}),
                "created_at": data.get("createdAt"),
                "ended_at": data.get("endedAt")
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Status check failed: {str(e)}"
        )


@app.post("/session/{call_id}/end")
async def end_session(call_id: str):
    """
    End an active voice session and retrieve final transcript.
    
    Returns:
    - call_id: Session identifier
    - status: ended
    - duration: Total call duration
    - finalTranscript: Complete conversation
    - extractedData: Structured data extracted by the agent
    """
    
    if not ULTRAVOX_API_KEY:
        raise HTTPException(status_code=500, detail="Ultravox API key not configured")
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{ULTRAVOX_BASE_URL}/agents/{ULTRAVOX_AGENT_ID}/calls/{call_id}/end",
                headers={
                    "X-API-Key": ULTRAVOX_API_KEY,
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {call_id} not found or already ended."
                )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to end session: {response.text}"
                )
            
            data = response.json()
            
            return {
                "call_id": call_id,
                "status": "ended",
                "duration": data.get("duration", 0),
                "final_transcript": data.get("finalTranscript"),
                "extracted_data": data.get("extractedData", {}),
                "ended_at": data.get("endedAt")
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Session end failed: {str(e)}"
        )


@app.post("/process-voice-query")
async def process_voice_query(request: VoiceQueryRequest):
    """
    Process a voice query transcript and extract structured entities.
    This endpoint bridges Ultravox voice input with ZELIA's n8n workflow.
    
    The extracted entities are used for:
    - Household profile building
    - Scheme eligibility checking
    - Application auto-filling
    """
    
    # Extract entities from transcript
    entities = extract_entities_from_transcript(request.transcript, request.language)
    
    # Merge with any pre-extracted entities from Ultravox agent
    if request.extracted_entities:
        entities.update(request.extracted_entities)
    
    return {
        "call_id": request.call_id,
        "transcript": request.transcript,
        "language": request.language,
        "entities": entities,
        "confidence": calculate_confidence(entities),
        "query_type": determine_query_type(request.transcript, entities)
    }


def extract_entities_from_transcript(transcript: str, language: str) -> Dict[str, Any]:
    """
    Extract structured household data from voice transcript.
    Uses keyword matching and pattern recognition (enhanced version with NER in production).
    """
    
    entities = {
        "head_name": None,
        "age": None,
        "marital_status": None,
        "children_count": None,
        "monthly_income": None,
        "disability_status": False,
        "caste_category": None,
        "documents_available": []
    }
    
    text_lower = transcript.lower()
    
    # Extract age (numeric patterns)
    import re
    age_patterns = [
        r'age[\s:]+(\d{1,3})',
        r'வயது[\s:]+(\d{1,3})',
        r'(\d{1,3})[\s]*(?:years|வயது)',
    ]
    for pattern in age_patterns:
        match = re.search(pattern, text_lower)
        if match:
            entities['age'] = int(match.group(1))
            break
    
    # Extract income
    income_patterns = [
        r'income[\s:]+(?:₹|rs\.?)?[\s]*(\d{3,7})',
        r'வருமானம்[\s:]+[\s]*(\d{3,7})',
        r'(\d{3,7})[\s]*(?:rupees|ரூபாய்)',
    ]
    for pattern in income_patterns:
        match = re.search(pattern, text_lower)
        if match:
            entities['monthly_income'] = int(match.group(1))
            break
    
    # Extract children count
    children_patterns = [
        r'(\d+)[\s]*children',
        r'(\d+)[\s]*குழந்தைகள்',
    ]
    for pattern in children_patterns:
        match = re.search(pattern, text_lower)
        if match:
            entities['children_count'] = int(match.group(1))
            break
    
    # Extract marital status
    if any(word in text_lower for word in ['widow', 'widowed', 'விதவை']):
        entities['marital_status'] = 'widowed'
    elif any(word in text_lower for word in ['married', 'திருமணமானவர்']):
        entities['marital_status'] = 'married'
    elif any(word in text_lower for word in ['single', 'unmarried', 'தனிமை']):
        entities['marital_status'] = 'single'
    
    # Extract disability status
    disability_keywords = ['disability', 'disabled', 'மாற்றுத்திறனாளி', 'differently abled']
    if any(keyword in text_lower for keyword in disability_keywords):
        entities['disability_status'] = True
    
    # Extract caste category
    if any(word in text_lower for word in ['sc', 'scheduled caste']):
        entities['caste_category'] = 'SC'
    elif any(word in text_lower for word in ['st', 'scheduled tribe']):
        entities['caste_category'] = 'ST'
    elif any(word in text_lower for word in ['obc', 'backward']):
        entities['caste_category'] = 'OBC'
    elif any(word in text_lower for word in ['general', 'forward']):
        entities['caste_category'] = 'General'
    
    # Extract documents
    doc_keywords = {
        'aadhaar': ['aadhaar', 'ஆதார்', 'aadhar'],
        'ration_card': ['ration', 'அட்டை', 'food card'],
        'income_certificate': ['income certificate', 'வருமான சான்றிதழ்'],
        'disability_certificate': ['disability certificate', 'மாற்றுத்திறனாளி சான்றிதழ்'],
    }
    
    for doc_type, keywords in doc_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            entities['documents_available'].append(doc_type)
    
    return entities


def calculate_confidence(entities: Dict[str, Any]) -> float:
    """Calculate confidence score based on number of extracted entities"""
    
    total_fields = len(entities)
    filled_fields = sum(1 for v in entities.values() if v not in [None, False, []])
    
    return round(filled_fields / total_fields, 2)


def determine_query_type(transcript: str, entities: Dict[str, Any]) -> str:
    """Determine the type of query from transcript"""
    
    text_lower = transcript.lower()
    
    # Check for scheme search keywords
    scheme_keywords = ['scheme', 'योजना', 'திட்டம்', 'pension', 'ஓய்வூதியம்', 'benefit']
    if any(keyword in text_lower for keyword in scheme_keywords):
        return "scheme_search"
    
    # Check for profile creation (multiple entities present)
    if sum(1 for v in entities.values() if v not in [None, False, []]) >= 3:
        return "profile_creation"
    
    # Check for document query
    doc_keywords = ['document', 'certificate', 'சான்றிதழ்', 'proof']
    if any(keyword in text_lower for keyword in doc_keywords):
        return "document_query"
    
    # Check for eligibility query
    eligibility_keywords = ['eligible', 'qualify', 'தகுதி', 'apply']
    if any(keyword in text_lower for keyword in eligibility_keywords):
        return "eligibility_check"
    
    return "general_query"


@app.get("/agent/info")
async def get_agent_info():
    """Get information about the configured Ultravox agent"""
    
    return {
        "agent_id": ULTRAVOX_AGENT_ID,
        "agent_name": "ZELIA Query Processor",
        "description": "Silent, back-end data extraction agent for the ZELIA platform",
        "persona": "Functional and non-conversational",
        "supported_languages": list(LANGUAGE_HINTS.keys()),
        "interview_questions": [
            "What is the head of household's name?",
            "How old is the head of household?",
            "What is the marital status?",
            "How many children under 18 live in the household?",
            "What is the approximate monthly household income in rupees?",
            "Does anyone in the household have a disability?",
            "What is the caste category?",
            "Which documents do you currently have?"
        ],
        "extracted_entities": [
            "head_name",
            "age",
            "marital_status",
            "children_count",
            "monthly_income",
            "disability_status",
            "caste_category",
            "documents_available"
        ]
    }


if __name__ == "__main__":
    print(f"Starting ZELIA Ultravox Proxy")
    print(f"Agent ID: {ULTRAVOX_AGENT_ID}")
    print(f"API Configured: {bool(ULTRAVOX_API_KEY)}")
    uvicorn.run(app, host="0.0.0.0", port=8010)
