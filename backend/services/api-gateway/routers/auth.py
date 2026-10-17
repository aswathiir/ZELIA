import os
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt
from typing import Optional

router = APIRouter()

SECRET_KEY = os.getenv("JWT_SECRET", "dev_secret_change_in_production")
ALGORITHM = "HS256"

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login", response_model=Token)
async def login(creds: LoginRequest):
    # STUB: Accept any login for 'admin' or 'chw'
    if creds.username in ["admin", "chw", "official"] and len(creds.password) > 0:
        # Create generic token
        expires = datetime.utcnow() + timedelta(days=1)
        access_token = jwt.encode(
            {"sub": creds.username, "role": "chw", "exp": expires},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@router.get("/me")
async def read_users_me(token: str):
    # Validate token manually for stub
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
