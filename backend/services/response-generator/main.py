"""
Response Generator Service for ZELIA
Uses Google Gemini, OpenAI, or Groq to generate natural language responses
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import httpx
import json

app = FastAPI(title="ZELIA Response Generator", version="1.2.1")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
RETRIEVAL_SERVICE_URL = os.getenv("RETRIEVAL_SERVICE_URL", "http://retrieval-service:8007")

class ResponseRequest(BaseModel):
    call_id: str
    intent: str
    data: Optional[str] = "{}"
    phone_number: Optional[str] = None
    status: Optional[str] = None
    eligibility: Optional[str] = "{}"

class ResponseOutput(BaseModel):
    formatted_response: str
    language: str = "en"
    ssml: Optional[str] = None

class ChatRequest(BaseModel):
    chatInput: str

class ChatResponse(BaseModel):
    output: str

RESPONSE_PROMPT = """You are a helpful voice assistant for ZELIA, a government scheme assistance platform in India.
Generate a natural, conversational response based on the provided context.

Guidelines:
- Keep responses concise (2-3 sentences max) for voice output
- Use simple language that works well when spoken aloud
- Be warm and helpful
- If eligibility result is provided, clearly state whether user is eligible or not
- For scheme info, summarize key benefits briefly
- For document upload confirmation, reassure the user their documents are being processed

Intent: {intent}
Data: {data}
Status: {status}

Generate a natural spoken response:"""

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Response Generator",
        "gemini_configured": bool(GEMINI_API_KEY),
        "openai_configured": bool(OPENAI_API_KEY),
        "groq_configured": bool(GROQ_API_KEY),
        "llm_provider": "groq" if GROQ_API_KEY else ("gemini" if GEMINI_API_KEY else "fallback")
    }

@app.post("/chat", response_model=ChatResponse)
async def chatbot_interface(request: ChatRequest):
    """Production RAG Chatbot Endpoint"""
    query = request.chatInput
    
    # 1. Search for context
    context = ""
    try:
        async with httpx.AsyncClient() as client:
            search_response = await client.post(
                f"{RETRIEVAL_SERVICE_URL}/search/hybrid",
                json={"query": query, "top_k": 3},
                timeout=10.0
            )
            if search_response.status_code == 200:
                results = search_response.json().get("results", [])
                context = "\n\n---\n\n".join([r.get("text", "") or json.dumps(r.get("metadata", {})) for r in results])
            else:
                print(f"Retrieval service returned {search_response.status_code}")
    except Exception as e:
        print(f"Retrieval error: {e}")
        context = "No additional context found."

    # 2. Generate response with Groq (preferred) or Gemini
    system_prompt = f"You are ZELIA Chatbot, a helpful assistant for Indian government schemes. Use the provided context to answer the user query. Be concise and helpful. If the context doesn't contain the answer, say you don't know but offer to help find more information.\n\nCONTEXT:\n{context}"
    
    if GROQ_API_KEY:
        result = await call_groq(system_prompt, query)
        if result:
            return ChatResponse(output=result)
            
    if GEMINI_API_KEY:
        # Combine into one prompt for Gemini
        result = await call_gemini(f"{system_prompt}\n\nUSER QUESTION: {query}")
        if result:
            return ChatResponse(output=result)
            
    return ChatResponse(output="I'm sorry, I'm having trouble connecting to my brain right now. Please try again in 15 seconds.")

async def call_groq(system_prompt: str, user_prompt: str) -> str | None:
    """Call Groq API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"Groq API error: {response.text}")
                return None
            
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
                
    except Exception as e:
        print(f"Error calling Groq: {e}")
        return None

async def call_gemini(prompt: str) -> str | None:
    """Call Google Gemini API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 300
                    }
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"Gemini API error: {response.text}")
                return None
            
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"].strip()
                
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return None

async def call_openai(prompt: str) -> str | None:
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
                        {"role": "system", "content": "You are a helpful assistant. Keep responses brief and natural."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 300
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"OpenAI API error: {response.text}")
                return None
            
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
                
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return None

@app.post("/generate-voice-response", response_model=ResponseOutput)
async def generate_voice_response(request: ResponseRequest):
    """Voice response generation logic"""
    prompt = RESPONSE_PROMPT.format(
        intent=request.intent,
        data=request.data,
        status=request.status or "processing"
    )
    
    if GEMINI_API_KEY:
        result = await call_gemini(prompt)
        if result: return ResponseOutput(formatted_response=result)
    
    if OPENAI_API_KEY:
        result = await call_openai(prompt)
        if result: return ResponseOutput(formatted_response=result)
        
    return fallback_response(request)

def fallback_response(request: ResponseRequest) -> ResponseOutput:
    """Template-based fallback"""
    templates = {
        "greeting": "Hello! Welcome to ZELIA. How can I help you today?",
        "unknown": "I'm sorry, I didn't quite understand that. Could you please repeat?"
    }
    return ResponseOutput(formatted_response=templates.get(request.intent, templates["unknown"]))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8015)
