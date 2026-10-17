"""
models.py — All Pydantic request/response models for the Ultravox Handler service.
Keeping models in one place makes the API contract visible and easy to evolve.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


# ─────────────────────────────────────────────
# Call lifecycle models
# ─────────────────────────────────────────────

class InitiateCallRequest(BaseModel):
    """Incoming request to start a new Ultravox call."""
    phone_number: str
    name: str = "Citizen"
    citizen_id: str
    reason: str = "general_inquiry"
    scheme_id: Optional[str] = None


class CreateSessionRequest(BaseModel):
    """Called by N8N or the frontend to register a new in-progress call session."""
    phone_number: str
    call_id: str
    citizen_id: Optional[str] = None
    household_hash: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    """Incrementally update an active call session with transcript or extracted data."""
    transcript: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None


class EndSessionRequest(BaseModel):
    """Mark a call session as complete."""
    duration: Optional[int] = None
    status: Optional[str] = None
    phone_number: Optional[str] = None


# ─────────────────────────────────────────────
# Webhook payloads
# ─────────────────────────────────────────────

class WebhookPayload(BaseModel):
    """
    Payload sent by Ultravox (or N8N) when a call concludes.
    This is the primary trigger for downstream AI processing.
    """
    event_type: Optional[str] = "call_ended"
    call_id: str
    customer_number: Optional[str] = None
    duration_secs: Optional[int] = 0
    messages: Optional[List[Dict[str, Any]]] = []
    status: Optional[str] = "completed"
    language: Optional[str] = "auto"
    household_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}
    process_now: Optional[bool] = True


class WorkflowCompletePayload(BaseModel):
    """
    Sent by N8N when PDF filling or downstream workflow finishes.
    Triggers a real-time WebSocket broadcast to the frontend.
    """
    household_hash: str
    status: str = "pdf_ready"
    filled_pdf_uri: Optional[str] = None
    fields_empty: Optional[List[str]] = []
    best_scheme: Optional[Dict[str, Any]] = {}


# ─────────────────────────────────────────────
# Other endpoint request models
# ─────────────────────────────────────────────

class TriggerVerificationRequest(BaseModel):
    """Manually kick off document verification for a household."""
    household_hash: str


class SubmitMissingFieldsRequest(BaseModel):
    """Submit corrected or missing fields for a pending application."""
    household_hash: str
    corrected_fields: Dict[str, Any]


class GetOrCreateHashRequest(BaseModel):
    """Derive a household hash from citizen login credentials."""
    citizen_id: str
    phone_number: str
