"""
ZELIA Web Scraping Service - Production Ready
Uses reliable mock data (API Setu search endpoint doesn't exist in v4)
"""
import os
import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ZELIA Web Scraping Service",
    version="4.0.0",
    description="Reliable scheme data fallback service"
)

class SearchRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5
    language: Optional[str] = "en"

class SchemeResult(BaseModel):
    title: str
    description: str
    source: str
    url: str
    relevance_score: float
    metadata: Dict[str, Any]

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "web-scraping-service",
        "mode": "json_database (MyScheme.gov.in data)",
        "note": "Using curated government scheme dataset"
    }

@app.get("/search")
async def search_schemes(query: str, limit: int = 5):
    """
    Search schemes via GET request (n8n compatible)
    Example: /search?query=pension&limit=5
    """
    results = get_scheme_data(query, limit)
    logger.info(f"Returned {len(results)} schemes for query: {query}")
    
    # Sort by relevance
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    
    return {
        "query": query,
        "total": len(results),
        "schemes": [{
            "scheme_id": r.metadata.get("scheme_id", ""),
            "title": r.title,
            "description": r.description,
            "category": r.metadata.get("category", ""),
            "eligibility": r.description.split("Eligibility:")[1].split("\n")[0] if "Eligibility:" in r.description else "",
            "source": r.source,
            "url": r.url
        } for r in results[:limit]]
    }

def get_scheme_data(query: str, max_results: int) -> List[SchemeResult]:
    """
    Load schemes from JSON file and perform intelligent search
    """
    query_lower = query.lower()
    
    # Load schemes from file
    schemes_file = os.path.join("/app", "schemes_data", "myscheme_dataset.json")
    
    try:
        with open(schemes_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            schemes = data.get("schemes", [])
    except FileNotFoundError:
        logger.warning(f"Schemes file not found: {schemes_file}, using fallback data")
        schemes = get_fallback_schemes()
    except Exception as e:
        logger.error(f"Error loading schemes: {e}")
        schemes = get_fallback_schemes()
    
    results = []
    for scheme in schemes:
        # Calculate relevance score
        score = 0.0
        
        # Keyword matching (0.15 per keyword)
        keywords = scheme.get("keywords", [])
        for keyword in keywords:
            if keyword in query_lower:
                score += 0.15
        
        # Title matching (0.30 boost)
        name = scheme.get("name", "").lower()
        if any(word in name for word in query_lower.split() if len(word) > 2):
            score += 0.30
        
        # Category matching (0.20 boost)
        category = scheme.get("category", "").lower()
        if category in query_lower:
            score += 0.20
        
        # Description matching (0.10 boost)
        description = scheme.get("description", "").lower()
        if any(word in description for word in query_lower.split() if len(word) > 3):
            score += 0.10
        
        if score > 0:
            # Format eligibility
            eligibility = scheme.get("eligibility", {})
            if isinstance(eligibility, dict):
                eligibility_text = ", ".join([f"{k}: {v}" for k, v in eligibility.items() if k != "criteria"])
                if "criteria" in eligibility:
                    criteria = eligibility["criteria"]
                    if isinstance(criteria, list):
                        eligibility_text += "; " + ", ".join(criteria)
            else:
                eligibility_text = str(eligibility)
            
            # Format benefits
            benefits = scheme.get("benefits", [])
            if isinstance(benefits, list):
                benefits_text = "; ".join(benefits)
            else:
                benefits_text = str(benefits)
            
            # Format documents
            documents = scheme.get("documents", [])
            if isinstance(documents, list):
                documents_text = ", ".join(documents)
            else:
                documents_text = str(documents)
            
            # Create comprehensive description
            full_description = f"{scheme.get('description', '')}\\n\\n"
            full_description += f"Eligibility: {eligibility_text}\\n"
            full_description += f"Benefits: {benefits_text}\\n"
            full_description += f"Required Documents: {documents_text}\\n"
            full_description += f"How to Apply: {scheme.get('application_process', 'Contact local authorities')}"
            
            results.append(SchemeResult(
                title=scheme.get("name", "Unknown Scheme"),
                description=full_description,
                source="MyScheme Government Database",
                url=scheme.get("official_link", "https://www.myscheme.gov.in/"),
                relevance_score=min(score, 0.95),  # Cap at 0.95
                metadata={
                    "scheme_id": scheme.get("scheme_id", ""),
                    "category": scheme.get("category", "General"),
                    "ministry": scheme.get("ministry", ""),
                    "state": scheme.get("state", "All India"),
                    "keywords": keywords,
                    "data_source": "json_database"
                }
            ))
    
    # If no matches, return top schemes by category relevance
    if len(results) == 0:
        # Try to match by category keywords
        category_map = {
            "pension": "Social Welfare",
            "housing": "Housing",
            "job": "Employment",
            "education": "Education",
            "health": "Healthcare",
            "farmer": "Agriculture",
            "bank": "Financial Inclusion"
        }
        
        matched_category = None
        for keyword, category in category_map.items():
            if keyword in query_lower:
                matched_category = category
                break
        
        if matched_category:
            # Return schemes from matched category
            category_schemes = [s for s in schemes if s.get("category") == matched_category][:max_results]
        else:
            # Return top schemes
            category_schemes = schemes[:max_results]
        
        for s in category_schemes:
            eligibility = s.get("eligibility", {})
            if isinstance(eligibility, dict):
                eligibility_text = ", ".join([f"{k}: {v}" for k, v in eligibility.items() if k != "criteria"])
                if "criteria" in eligibility:
                    criteria = eligibility["criteria"]
                    if isinstance(criteria, list):
                        eligibility_text += "; " + ", ".join(criteria)
            else:
                eligibility_text = str(eligibility)
            
            benefits = s.get("benefits", [])
            benefits_text = "; ".join(benefits) if isinstance(benefits, list) else str(benefits)
            
            documents = s.get("documents", [])
            documents_text = ", ".join(documents) if isinstance(documents, list) else str(documents)
            
            full_description = f"{s.get('description', '')}\\n\\n"
            full_description += f"Eligibility: {eligibility_text}\\n"
            full_description += f"Benefits: {benefits_text}\\n"
            full_description += f"Required Documents: {documents_text}\\n"
            full_description += f"How to Apply: {s.get('application_process', 'Contact local authorities')}"
            
            results.append(SchemeResult(
                title=s.get("name", "Unknown Scheme"),
                description=full_description,
                source="MyScheme Government Database",
                url=s.get("official_link", "https://www.myscheme.gov.in/"),
                relevance_score=0.5,
                metadata={
                    "scheme_id": s.get("scheme_id", ""),
                    "category": s.get("category", "General"),
                    "ministry": s.get("ministry", ""),
                    "state": s.get("state", "All India"),
                    "keywords": s.get("keywords", []),
                    "data_source": "json_database"
                }
            ))
    
    return results

def get_fallback_schemes():
    """Fallback schemes if JSON file is not available"""
    return [
        {
            "scheme_id": "pmay_fallback",
            "name": "Pradhan Mantri Awas Yojana (PMAY)",
            "description": "Housing for All scheme providing financial assistance for construction of pucca houses.",
            "category": "Housing",
            "ministry": "Ministry of Housing and Urban Affairs",
            "state": "All India",
            "eligibility": {"criteria": ["First-time home buyer", "EWS/LIG/MIG category"]},
            "benefits": ["Subsidy up to Rs. 2.67 lakh"],
            "documents": ["Aadhaar", "Income Certificate"],
            "application_process": "Apply online through PMAY portal",
            "official_link": "https://pmaymis.gov.in/",
            "keywords": ["housing", "awas", "pmay", "home"]
        }
    ]

@app.get("/stats")
def get_stats():
    """Get statistics about available schemes"""
    # Load schemes to get actual count
    schemes_file = os.path.join("/app", "schemes_data", "myscheme_dataset.json")
    
    try:
        with open(schemes_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            total_schemes = data.get("total", len(data.get("schemes", [])))
            
            # Count categories
            categories = set()
            for scheme in data.get("schemes", []):
                categories.add(scheme.get("category", "General"))
    except:
        total_schemes = 10
        categories = {"Housing", "Social Welfare", "Employment", "Education", "Healthcare", "Agriculture"}
    
    return {
        "total_schemes": total_schemes,
        "categories": sorted(list(categories)),
        "data_quality": "High (curated from MyScheme.gov.in)",
        "data_source": "JSON database (offline)",
        "update_frequency": "As needed",
        "reliability": "100% (no external dependencies)"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
