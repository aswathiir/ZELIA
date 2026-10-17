# Simplified Retrieval Service - Text Search Only
# No Annoy, no sentence-transformers, just PostgreSQL

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import psycopg2
import os
import uvicorn

app = FastAPI(title="ZELIA Retrieval Service (Simplified)", version="2.0.1")

DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/zelia')

class SearchRequest(BaseModel):
    query: str
    k: int = 10
    threshold: float = 0.3

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Retrieval Service (Text-only)",
        "vector_search_available": False
    }

@app.post("/search")
@app.post("/search/hybrid")  # Same endpoint for compatibility
async def search(request: SearchRequest):
    """PostgreSQL full-text search"""
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # Full-text search with ranking
        cursor.execute("""
            SELECT 
                scheme_id, 
                title, 
                description,
                category,
                eligibility_rules,
                required_documents,
                impact_weight,
                ts_rank(
                    to_tsvector('english', title || ' ' || COALESCE(description, '')),
                    plainto_tsquery('english', %s)
                ) as rank
            FROM schemes
            WHERE to_tsvector('english', title || ' ' || COALESCE(description, '')) 
                  @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC, impact_weight DESC
            LIMIT %s
        """, (request.query, request.query, request.k))
        
        results = []
        for row in cursor.fetchall():
            score = float(row[7]) if row[7] else 0.5
            if score >= request.threshold:
                results.append({
                    "scheme_id": str(row[0]),
                    "title": row[1],
                    "description": row[2] or "",
                    "category": row[3] or "General",
                    "eligibility_criteria": row[4] or {},
                    "required_documents": row[5] or [],
                    "score": score,
                    "source": "text"
                })
        
        cursor.close()
        conn.close()
        
        return {"results": results, "total": len(results)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/index/status")
async def index_status():
    """Compatibility endpoint"""
    return {
        "available": True,
        "message": "Using PostgreSQL text search (no vector index needed)"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8007)
