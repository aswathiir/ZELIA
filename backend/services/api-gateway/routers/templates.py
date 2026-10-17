from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class TemplateResponse(BaseModel):
    template_id: str
    scheme_id: str
    name: str
    description: Optional[str] = None
    pdf_url: Optional[str] = None

# In-memory template store (will be replaced with DB)
TEMPLATES = [
    {
        "template_id": "tmpl_001",
        "scheme_id": "sch_kisan",
        "name": "PM-KISAN Application Form",
        "description": "Application form for PM-KISAN scheme",
        "pdf_url": None
    },
    {
        "template_id": "tmpl_002",
        "scheme_id": "sch_ration",
        "name": "Ration Card Application",
        "description": "Application form for new ration card",
        "pdf_url": None
    }
]

@router.get("/", response_model=List[TemplateResponse])
async def list_templates(scheme_id: Optional[str] = None):
    """
    List all available form templates.
    Optionally filter by scheme_id.
    """
    if scheme_id:
        return [t for t in TEMPLATES if t["scheme_id"] == scheme_id]
    return TEMPLATES

@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str):
    """
    Get a specific template by ID.
    """
    for t in TEMPLATES:
        if t["template_id"] == template_id:
            return t
    raise HTTPException(status_code=404, detail="Template not found")

@router.post("/generate/{template_id}")
async def generate_pdf(template_id: str, data: dict):
    """
    Generate a filled PDF from template (stub).
    Will be implemented with actual PDF generation.
    """
    # TODO: Integrate with pdf-service for actual generation
    return {
        "status": "pending",
        "template_id": template_id,
        "message": "PDF generation will be implemented with pdf-service integration"
    }
