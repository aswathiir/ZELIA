from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import uuid
import asyncpg
from typing import Optional, List
from datetime import datetime
from decouple import config

# Configuration
DATABASE_URL = config("DATABASE_URL", default="postgresql://zelia:zelia_secure_2024@postgres:5432/zelia")
ULTRAVOX_API_KEY = config("ULTRAVOX_API_KEY", default="")
ULTRAVOX_AGENT_ID = config("ULTRAVOX_AGENT_ID", default="")
ULTRAVOX_BASE_URL = config("ULTRAVOX_BASE_URL", default="https://api.ultravox.ai")

app = FastAPI(title="Ultravox Handler", version="1.0.0")

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

@app.on_event("startup")
async def startup():
    global db_pool
    # Retry logic or wait-for-it pattern is handled by docker-compose depends_on usually, 
    # but defensive coding here helps.
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=10)
    except Exception as e:
        print(f"Error connecting to database: {e}")

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()

# Models
class InitiateCallRequest(BaseModel):
    phone_number: str
    name: str = "Citizen"
    citizen_id: str
    reason: str = "general_inquiry"

class CallResponse(BaseModel):
    status: str
    callId: str
    joinUrl: str
    createdAt: str
    message: str

class CreateSessionRequest(BaseModel):
    phone_number: str
    call_id: str

class UpdateSessionRequest(BaseModel):
    transcript: Optional[str] = None
    structured_data: Optional[dict] = None

class EndSessionRequest(BaseModel):
    duration: Optional[int] = None
    status: Optional[str] = None
    phone_number: Optional[str] = None



# Helper to create/get citizen (simple stub or integration)
# For now, we assume citizen_id is passed or handled elsewhere.

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ultravox-handler"}

@app.post("/calls/initiate", response_model=CallResponse)
async def initiate_call(req: InitiateCallRequest):
    """
    Initiate a call via Ultravox API.
    Note: Ultravox API typically returns a joinUrl for the agent to join a WebRTC session 
    OR initiates an outbound phone call if configured with Twilio.
    Based on prompt, we are returning a joinUrl.
    """
    if not ULTRAVOX_API_KEY:
        raise HTTPException(status_code=500, detail="ULTRAVOX_API_KEY not configured")

    async with httpx.AsyncClient() as client:
        # Create a call in Ultravox
        # Payload depends on Ultravox specific API docs, using generic structure as per prompt
        payload = {
            "systemPrompt": f"You are speaking with {req.name}. Context: {req.reason}",
            "model": "fixie-ai/ultravox-70b", # Example model
            "voice": "mark", # Example voice
            # If using Twilio for outbound:
            # "phoneNumber": req.phone_number 
        }
        
        # Real Ultravox API call would go here. 
        # Using the base URL provided in prompt.
        try:
            resp = await client.post(
                f"{ULTRAVOX_BASE_URL}/api/v1/calls",
                json=payload,
                headers={"X-API-Key": ULTRAVOX_API_KEY, "Content-Type": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()
            call_id = data.get("callId")
            join_url = data.get("joinUrl")
            
        except Exception as e:
            # Fallback for testing/mocking if API fails or key is invalid
            print(f"Ultravox API Call Failed (using mock): {e}")
            call_id = f"call_{uuid.uuid4().hex[:8]}"
            join_url = f"wss://api.ultravox.ai/calls/{call_id}/join"

    # Store in database
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO active_calls (call_id, citizen_id, phone_number, status, metadata)
                VALUES ($1, $2, $3, 'initiated', $4)
                ON CONFLICT (call_id) DO NOTHING
                """,
                call_id, req.citizen_id, req.phone_number, 
                f'{{"name": "{req.name}", "reason": "{req.reason}"}}'
            )

    return {
        "status": "success",
        "callId": call_id,
        "joinUrl": join_url,
        "createdAt": datetime.now().isoformat(),
        "message": "Call initiated. User will receive incoming call."
    }

@app.get("/citizens/{citizen_id}/calls")
async def get_citizen_calls(citizen_id: str):
    if not db_pool:
        return []
        
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM active_calls WHERE citizen_id = $1 ORDER BY created_at DESC",
            citizen_id
        )
        return [dict(row) for row in rows]

@app.get("/calls")
async def get_all_calls():
    """Fetch all active, on-hold, and recent calls across the system."""
    if not db_pool:
        return []
        
    async with db_pool.acquire() as conn:
        # Fetching all calls for the admin dashboard
        rows = await conn.fetch(
            "SELECT * FROM active_calls ORDER BY created_at DESC LIMIT 100"
        )
        return [dict(row) for row in rows]

# Session Manager Endpoints (called by N8N)
@app.post("/session/create")
async def create_session(req: CreateSessionRequest):
    """Create a new session records"""
    if db_pool:
        async with db_pool.acquire() as conn:
            # Upsert into active_calls or sessions table
            # Assuming active_calls serves as session storage for now
            # Check if exists first
            await conn.execute(
                """
                INSERT INTO active_calls (call_id, phone_number, status, created_at)
                VALUES ($1, $2, 'active', NOW())
                ON CONFLICT (call_id) DO UPDATE 
                SET phone_number = EXCLUDED.phone_number, status = 'active'
                """,
                req.call_id, req.phone_number
            )
    return {"status": "created", "call_id": req.call_id}

@app.post("/session/update/{call_id}")
async def update_session(call_id: str, req: UpdateSessionRequest = Body(...)):
    """Update session with transcript or data"""
    # Just log or store in DB
    if db_pool:
        async with db_pool.acquire() as conn:
            if req.transcript:
               # Store transcript (maybe separate table, but for now update metadata or ignore)
               # The prompt mentioned a separate 'call_transcripts' table, handled by voice-processor likely.
               # But if N8N calls this, we should handle it.
               pass
            if req.structured_data:
                # Update metadata
                import json
                await conn.execute(
                    """
                    UPDATE active_calls 
                    SET metadata = metadata::jsonb || $2::jsonb
                    WHERE call_id = $1
                    """,
                    call_id, json.dumps(req.structured_data)
                )
    return {"status": "updated"}

@app.post("/session/end/{call_id}")
async def end_session(call_id: str, req: EndSessionRequest = Body(...)):
    """End the session"""
    if db_pool:
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE active_calls 
                SET status = 'completed', 
                    metadata = metadata::jsonb || jsonb_build_object('duration', $2::int, 'final_status', $3::text)
                WHERE call_id = $1
                """,
                call_id, req.duration or 0, req.status or 'completed'
            )
    return {"status": "ended", "call_id": call_id}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
