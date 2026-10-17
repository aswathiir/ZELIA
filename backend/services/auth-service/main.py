from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
import redis
import uuid
from datetime import datetime, timedelta
from decouple import config
from typing import Optional
import asyncpg
import hashlib

# Configuration
JWT_SECRET = config("JWT_SECRET", default="your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
DATABASE_URL = config("DATABASE_URL", default="postgresql://postgres:password@localhost/zelia")
REDIS_HOST = config("REDIS_HOST", default="redis")
REDIS_PORT = int(config("REDIS_PORT", default="6379"))

app = FastAPI(title="Auth Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=10, max_size=20)

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()

# Models
class SendOTPRequest(BaseModel):
    phone_number: str

class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp_code: str
    aadhaar_hash: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    phone_number: str
    otp_code: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    token: str

# Helper functions
def generate_otp() -> str:
    """Generate 6-digit OTP"""
    import random
    return str(random.randint(100000, 999999))

def hash_aadhaar(aadhaar: str) -> str:
    """Hash Aadhaar for storage (never store plaintext)"""
    return hashlib.sha256(aadhaar.encode()).hexdigest()

def create_jwt_token(citizen_id: str, expires_in_hours: int = 24) -> str:
    """Create JWT token"""
    payload = {
        'citizen_id': citizen_id,
        'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(citizen_id: str) -> str:
    """Create refresh token (valid for 30 days)"""
    payload = {
        'citizen_id': citizen_id,
        'exp': datetime.utcnow() + timedelta(days=30),
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def verify_jwt_token(token: str) -> dict:
    """Verify JWT token"""
    try:
        # Check if token is blacklisted
        if r.exists(f"blacklisted_token:{token}"):
            raise HTTPException(status_code=401, detail="Token has been revoked")
        
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_citizen(token: str = Depends(lambda: None)) -> dict:
    """Dependency to get current citizen from JWT"""
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await verify_jwt_token(token)

async def send_sms(phone_number: str, message: str) -> bool:
    """Send SMS using Twilio"""
    import os
    from twilio.rest import Client
    
    try:
        # Get Twilio credentials from environment
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        from_number = os.getenv('TWILIO_FROM_NUMBER')
        
        # If credentials are not set or are placeholders, just log
        if not account_sid or not auth_token or account_sid.startswith('your'):
            print(f"SMS to {phone_number}: {message}")
            return True
        
        # Send real SMS via Twilio
        client = Client(account_sid, auth_token)
        
        # Format phone number for international (add +91 for India if not present)
        if not phone_number.startswith('+'):
            phone_number = f"+91{phone_number}"
        
        message_obj = client.messages.create(
            body=message,
            from_=from_number,
            to=phone_number
        )
        
        print(f"✅ SMS sent to {phone_number} - SID: {message_obj.sid}")
        return True
        
    except Exception as e:
        print(f"❌ SMS Error: {e}")
        # Log the OTP as fallback
        print(f"SMS to {phone_number}: {message}")
        return False

async def verify_aadhaar(aadhaar_hash: str) -> bool:
    """Verify Aadhaar with India Stack API"""
    # TODO: Call India Stack API
    # For testing, just return True if hash looks valid
    return len(aadhaar_hash) == 64  # SHA256 produces 64 char hash

# Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "auth-service"}

@app.post("/auth/send-otp")
async def send_otp(req: SendOTPRequest):
    """
    Step 1: Send OTP to phone number via SMS
    """
    phone = req.phone_number
    
    # Validate phone format
    if not phone or len(phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    
    # Rate limit: max 5 OTP attempts per phone per hour
    attempt_key = f"otp_attempts:{phone}"
    attempts = r.get(attempt_key)
    if attempts and int(attempts) >= 5:
        raise HTTPException(status_code=429, detail="Too many OTP attempts. Try again later.")
    
    # Generate OTP
    otp = generate_otp()
    
    # Store in Redis (valid for 5 minutes)
    r.setex(f"otp:{phone}", 300, otp)
    
    # Increment attempt counter
    r.incr(attempt_key)
    r.expire(attempt_key, 3600)  # Reset after 1 hour
    
    # Send SMS
    await send_sms(phone, f"Your ZELIA OTP: {otp}. Valid for 5 minutes. Do not share.")
    
    return {
        "message": "OTP sent successfully",
        "phone_number": phone,
        "expires_in": 300
    }

@app.post("/auth/verify-otp")
async def verify_otp(req: VerifyOTPRequest):
    """
    Step 2: Verify OTP and Aadhaar, create citizen
    """
    phone = req.phone_number
    otp = req.otp_code
    aadhaar_hash = req.aadhaar_hash
    name = req.name or f"Citizen_{phone[-4:]}"
    
    # Verify OTP
    stored_otp = r.get(f"otp:{phone}")
    if not stored_otp:
        raise HTTPException(status_code=401, detail="OTP expired. Request a new one.")
    
    if stored_otp != otp:
        raise HTTPException(status_code=401, detail="Invalid OTP")
    
    # Verify Aadhaar
    if not await verify_aadhaar(aadhaar_hash):
        raise HTTPException(status_code=401, detail="Invalid Aadhaar")
    
    # Check if citizen already exists
    async with db_pool.acquire() as conn:
        existing = await conn.fetchval(
            "SELECT citizen_id FROM citizens WHERE phone_number = $1",
            phone
        )
        
        if existing:
            # Citizen exists, update last_login and return tokens
            await conn.execute(
                "UPDATE citizens SET last_login = NOW() WHERE phone_number = $1",
                phone
            )
            citizen_id = existing
        else:
            # Create new citizen
            citizen_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO citizens (citizen_id, phone_number, aadhaar_hash, name, created_at, last_login)
                VALUES ($1, $2, $3, $4, NOW(), NOW())
                """,
                citizen_id, phone, aadhaar_hash, name
            )
    
    # Generate tokens
    jwt_token = create_jwt_token(citizen_id)
    refresh_token = create_refresh_token(citizen_id)
    
    # Store refresh token in Redis
    r.setex(f"refresh_token:{citizen_id}", 30*24*3600, refresh_token)
    
    # Clean up OTP
    r.delete(f"otp:{phone}")
    
    return {
        "citizen_id": citizen_id,
        "jwt_token": jwt_token,
        "refresh_token": refresh_token,
        "name": name,
        "token_type": "bearer",
        "expires_in": 86400
    }

@app.post("/auth/refresh")
async def refresh_token(req: RefreshTokenRequest):
    """
    Refresh JWT token using refresh token
    """
    refresh_token_str = req.refresh_token
    
    try:
        payload = jwt.decode(refresh_token_str, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        citizen_id = payload.get('citizen_id')
        
        if not citizen_id or payload.get('type') != 'refresh':
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Check if refresh token exists in Redis
        stored_token = r.get(f"refresh_token:{citizen_id}")
        if not stored_token or stored_token != refresh_token_str:
            raise HTTPException(status_code=401, detail="Refresh token invalid or revoked")
        
        # Generate new JWT
        new_jwt = create_jwt_token(citizen_id)
        
        return {
            "jwt_token": new_jwt,
            "token_type": "bearer",
            "expires_in": 86400
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.post("/auth/logout")
async def logout(req: LogoutRequest):
    """
    Logout by blacklisting JWT token
    """
    token = req.token
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        exp = payload.get('exp')
        
        # Calculate TTL (time until token expires)
        ttl = int(exp - datetime.utcnow().timestamp())
        
        if ttl > 0:
            # Blacklist token
            r.setex(f"blacklisted_token:{token}", ttl, "true")
        
        return {"message": "Logged out successfully"}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/auth/me")
async def get_current_user(token: str = Depends(lambda r: r.headers.get("authorization", "").replace("Bearer ", ""))):
    """
    Get current citizen info
    """
    if not token:
        raise HTTPException(status_code=401, detail="No authorization token")
    
    payload = await verify_jwt_token(token)
    citizen_id = payload.get('citizen_id')
    
    async with db_pool.acquire() as conn:
        citizen = await conn.fetchrow(
            "SELECT citizen_id, phone_number, name, created_at, last_login FROM citizens WHERE citizen_id = $1",
            citizen_id
        )
    
    if not citizen:
        raise HTTPException(status_code=404, detail="Citizen not found")
    
    return dict(citizen)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
