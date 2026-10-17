from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

router = APIRouter()

# Response models
class SchemeResponse(BaseModel):
    scheme_id: UUID
    title: str
    state_code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    eligibility_rules: Optional[dict] = None
    required_documents: Optional[list] = None
    impact_weight: Optional[float] = 0.5
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SchemeCreate(BaseModel):
    title: str
    state_code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    eligibility_rules: Optional[dict] = None
    required_documents: Optional[list] = None
    impact_weight: Optional[float] = 0.5

@router.get("/", response_model=List[SchemeResponse])
async def list_schemes(
    state_code: Optional[str] = Query(None, description="Filter by state code (e.g., TN)"),
    category: Optional[str] = Query(None, description="Filter by category (e.g., pension)"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all available welfare schemes.
    Can be filtered by state_code and/or category.
    """
    query = "SELECT * FROM schemes WHERE 1=1"
    params = {}
    
    if state_code:
        query += " AND state_code = :state_code"
        params["state_code"] = state_code
    if category:
        query += " AND category = :category"
        params["category"] = category
    
    query += " ORDER BY impact_weight DESC LIMIT :limit OFFSET :skip"
    params["limit"] = limit
    params["skip"] = skip
    
    result = db.execute(text(query), params)
    schemes = result.mappings().all()
    return [SchemeResponse(**dict(s)) for s in schemes]

@router.get("/{scheme_id}", response_model=SchemeResponse)
async def get_scheme(scheme_id: UUID, db: Session = Depends(get_db)):
    """Get a single scheme by ID."""
    result = db.execute(
        text("SELECT * FROM schemes WHERE scheme_id = :id"),
        {"id": scheme_id}
    )
    scheme = result.mappings().first()
    
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    
    return SchemeResponse(**dict(scheme))

@router.post("/", response_model=SchemeResponse)
async def create_scheme(scheme: SchemeCreate, db: Session = Depends(get_db)):
    """
    Create a new welfare scheme.
    Requires admin role in production.
    """
    query = text("""
        INSERT INTO schemes (title, state_code, category, description, 
                           eligibility_rules, required_documents, impact_weight)
        VALUES (:title, :state_code, :category, :description,
                :eligibility_rules, :required_documents, :impact_weight)
        RETURNING *
    """)
    
    import json
    result = db.execute(query, {
        "title": scheme.title,
        "state_code": scheme.state_code,
        "category": scheme.category,
        "description": scheme.description,
        "eligibility_rules": json.dumps(scheme.eligibility_rules) if scheme.eligibility_rules else None,
        "required_documents": json.dumps(scheme.required_documents) if scheme.required_documents else None,
        "impact_weight": scheme.impact_weight
    })
    db.commit()
    
    new_scheme = result.mappings().first()
    return SchemeResponse(**dict(new_scheme))

@router.get("/categories/list")
async def list_categories(db: Session = Depends(get_db)):
    """Get list of unique scheme categories."""
    result = db.execute(text("SELECT DISTINCT category FROM schemes WHERE category IS NOT NULL"))
    categories = [row[0] for row in result.fetchall()]
    return {"categories": categories}

@router.get("/states/list")
async def list_states(db: Session = Depends(get_db)):
    """Get list of unique state codes."""
    result = db.execute(text("SELECT DISTINCT state_code FROM schemes WHERE state_code IS NOT NULL"))
    states = [row[0] for row in result.fetchall()]
    return {"states": states}
