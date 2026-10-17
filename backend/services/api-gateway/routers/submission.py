from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import os

router = APIRouter()

# Submission service URL
SUBMISSION_SERVICE_URL = os.getenv("SUBMISSION_SERVICE_URL", "http://submission-service:8004")

class SubmissionStatus(BaseModel):
    submission_id: str
    status: str
    file_path: Optional[str] = None
    message: Optional[str] = None

@router.post("/")
async def submit_form(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    metadata: str = Form("{}")
):
    """
    Submit a form image for processing.
    Proxies the request to the submission-service.
    """
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {"file": (file.filename, await file.read(), file.content_type)}
            data = {"user_id": user_id, "metadata": metadata}
            
            response = await client.post(
                f"{SUBMISSION_SERVICE_URL}/sync",
                files=files,
                data=data
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Submission service unavailable: {str(e)}")

@router.get("/status/{submission_id}")
async def get_submission_status(submission_id: str):
    """
    Get the status of a submission.
    """
    # TODO: Implement actual status tracking from database
    return SubmissionStatus(
        submission_id=submission_id,
        status="pending",
        message="Submission status tracking will be implemented with database integration"
    )

@router.get("/health")
async def check_submission_service_health():
    """
    Check if the submission service is healthy.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SUBMISSION_SERVICE_URL}/health")
            response.raise_for_status()
            return {"status": "healthy", "submission_service": response.json()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
