from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import uuid
from datetime import datetime
from decouple import config
from typing import Optional, List, Any
import asyncpg
import json

# Configuration
DATABASE_URL = config("DATABASE_URL", default="postgresql://postgres:password@localhost/zelia")
REDIS_HOST = config("REDIS_HOST", default="redis")
REDIS_PORT = int(config("REDIS_PORT", default="6379"))

app = FastAPI(title="Scheme Service", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis client
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=1, decode_responses=True)

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=10)

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()

# Models
class EligibilityRule(BaseModel):
    field: str
    operator: str  # >=, <=, ==, >, <
    value: Any
    description: str = ""

class SchemeCreate(BaseModel):
    name: str
    description: str
    ministry: str
    eligibility_rules: List[EligibilityRule]
    pseudocode: str
    form_fields: List[str]

class SchemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    eligibility_rules: Optional[List[EligibilityRule]] = None
    pseudocode: Optional[str] = None

class SchemeResponse(BaseModel):
    scheme_id: str
    name: str
    description: str
    ministry: str
    status: str
    version: str
    eligibility_rules: List[dict]
    pseudocode: str
    form_fields: List[str]
    created_at: str
    updated_at: str

# Helper functions
def serialize_rules(rules: List[EligibilityRule]) -> list:
    """Convert Pydantic models to dicts"""
    return [
        {
            "field": r.field,
            "operator": r.operator,
            "value": r.value,
            "description": r.description
        }
        for r in rules
    ]

def increment_version(version_str: str) -> str:
    """v1.0 -> v1.1, v1.9 -> v2.0"""
    parts = version_str.split(".")
    minor = int(parts)
    major = int(parts)
    
    if minor < 9:
        return f"{major}.{minor + 1}"
    else:
        return f"{major + 1}.0"

def invalidate_scheme_cache(scheme_id: str = None):
    """Invalidate scheme cache"""
    if scheme_id:
        r.delete(f"scheme:{scheme_id}")
    r.delete("all_schemes")

# Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "scheme-service"}

@app.get("/schemes")
async def list_schemes():
    """
    List all active schemes (cached)
    Cache: 1 hour
    """
    cache_key = "all_schemes"
    
    # Check Redis cache
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query database
    async with db_pool.acquire() as conn:
        schemes = await conn.fetch(
            "SELECT scheme_id, scheme_name as name, description, category as ministry, 'active' as status, 'V-1.0' as version, created_at FROM schemes ORDER BY scheme_name"
        )
    
    # Convert to list of dicts
    result = [dict(s) for s in schemes]
    
    # Cache for 1 hour
    r.setex(cache_key, 3600, json.dumps(result, default=str))
    
    return result

@app.get("/schemes/{scheme_id}")
async def get_scheme(scheme_id: str):
    """
    Get full scheme with rules and templates
    Cache: 24 hours
    """
    cache_key = f"scheme:{scheme_id}"
    
    # Check Redis cache
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query database
    async with db_pool.acquire() as conn:
        scheme = await conn.fetchrow(
            "SELECT * FROM schemes WHERE scheme_id = $1",
            scheme_id
        )
        
        if not scheme:
            raise HTTPException(status_code=404, detail="Scheme not found")
        
        if not scheme:
            raise HTTPException(status_code=404, detail="Scheme not found")
    
    # Build response
    response = {
        "scheme_id": scheme["scheme_id"],
        "name": scheme["scheme_name"],
        "description": scheme["description"],
        "ministry": scheme["category"],
        "status": "active",
        "version": "1.0",
        "eligibility_rules": scheme["eligibility_summary"],
        "pseudocode": "",
        "form_fields": scheme["required_documents"],
        "created_at": str(scheme["created_at"]),
        "updated_at": str(scheme["updated_at"]),
        "version_history": []
    }
    
    # Cache for 24 hours
    r.setex(cache_key, 86400, json.dumps(response, default=str))
    
    return response

@app.post("/schemes")
async def create_scheme(req: SchemeCreate):
    """
    Create new scheme (draft status)
    """
    scheme_id = str(uuid.uuid4())
    rules = serialize_rules(req.eligibility_rules)
    
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO schemes 
            (scheme_id, name, description, ministry, eligibility_rules, pseudocode, form_fields, status, version)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'draft', 'v1.0')
            """,
            scheme_id,
            req.name,
            req.description,
            req.ministry,
            json.dumps(rules),
            req.pseudocode,
            json.dumps(req.form_fields)
        )
    
    # Invalidate cache
    invalidate_scheme_cache()
    
    return {
        "scheme_id": scheme_id,
        "status": "draft",
        "version": "v1.0"
    }

@app.patch("/schemes/{scheme_id}")
async def update_scheme(scheme_id: str, req: SchemeUpdate):
    """
    Update scheme and create new version
    """
    async with db_pool.acquire() as conn:
        # Get current scheme
        current = await conn.fetchrow(
            "SELECT version, name, description, ministry, eligibility_rules, pseudocode, form_fields FROM schemes WHERE scheme_id = $1",
            scheme_id
        )
        
        if not current:
            raise HTTPException(status_code=404, detail="Scheme not found")
        
        # Calculate new version
        new_version = increment_version(current["version"])
        
        # Create version record (for audit trail)
        await conn.execute(
            """
            INSERT INTO scheme_versions (scheme_id, version, data, created_at)
            VALUES ($1, $2, $3, NOW())
            """,
            scheme_id,
            new_version,
            json.dumps({
                "name": req.name or current["name"],
                "description": req.description or current["description"],
                "eligibility_rules": serialize_rules(req.eligibility_rules) if req.eligibility_rules else current["eligibility_rules"],
                "pseudocode": req.pseudocode or current["pseudocode"]
            })
        )
        
        # Update main scheme
        new_rules = serialize_rules(req.eligibility_rules) if req.eligibility_rules else current["eligibility_rules"]
        
        await conn.execute(
            """
            UPDATE schemes 
            SET 
                name = $2,
                description = $3,
                eligibility_rules = $4,
                pseudocode = $5,
                version = $6,
                updated_at = NOW()
            WHERE scheme_id = $1
            """,
            scheme_id,
            req.name or current["name"],
            req.description or current["description"],
            json.dumps(new_rules),
            req.pseudocode or current["pseudocode"],
            new_version
        )
    
    # Invalidate cache
    invalidate_scheme_cache(scheme_id)
    
    return {
        "scheme_id": scheme_id,
        "new_version": new_version,
        "status": "updated"
    }

@app.post("/schemes/{scheme_id}/publish")
async def publish_scheme(scheme_id: str):
    """
    Publish scheme (draft -> active)
    """
    async with db_pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE schemes SET status = 'active', published_at = NOW() WHERE scheme_id = $1 AND status = 'draft'",
            scheme_id
        )
    
    if result == "UPDATE 0":
        raise HTTPException(status_code=400, detail="Can only publish draft schemes")
    
    # Invalidate cache
    invalidate_scheme_cache(scheme_id)
    
    return {"message": "Scheme published", "scheme_id": scheme_id}

@app.get("/schemes/{scheme_id}/versions")
async def get_scheme_versions(scheme_id: str):
    """
    Get version history of scheme
    """
    async with db_pool.acquire() as conn:
        versions = await conn.fetch(
            "SELECT version, data, created_at FROM scheme_versions WHERE scheme_id = $1 ORDER BY created_at DESC",
            scheme_id
        )
    
    return [dict(v) for v in versions]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
