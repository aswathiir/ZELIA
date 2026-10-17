"""
ZELIA Document Verification & Auto-Fill
Cross-checks user-provided profile data against OCR-extracted document data.
Provides auto-fill for missing fields using verified document data.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import logging
import json as _json

logger = logging.getLogger("ocr-service.verification")

router = APIRouter(tags=["verification"])


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
class VerifySubmissionRequest(BaseModel):
    """User-provided profile data to verify against OCR documents."""
    household_hash: str
    user_profile: Dict[str, Any]  # e.g. {"name": "Lakshmi", "age": 65, ...}
    scheme_id: Optional[str] = None


class FieldVerification(BaseModel):
    field: str
    user_value: Optional[str]
    document_value: Optional[str]
    source_document: str
    status: str  # "matched", "mismatch", "auto_filled", "not_in_documents"


class VerifySubmissionResponse(BaseModel):
    household_hash: str
    overall_status: str  # "verified", "needs_review", "no_documents"
    total_fields_checked: int
    matched: int
    mismatched: int
    auto_filled: int
    field_details: List[FieldVerification]
    suggested_corrections: Dict[str, str]


class AutoFillRequest(BaseModel):
    household_hash: str
    user_profile: Dict[str, Any]


class AutoFillResponse(BaseModel):
    household_hash: str
    original_profile: Dict[str, Any]
    filled_profile: Dict[str, Any]
    fields_filled: List[str]
    fill_sources: Dict[str, str]  # field -> document_type


# ---------------------------------------------------------------------------
# Field mapping: user profile field → document field equivalents
# ---------------------------------------------------------------------------
FIELD_MAPPING = {
    # user_profile_key: [(document_type, document_field_key), ...]
    "name": [
        ("aadhaar", "name"),
        ("pan", "name"),
        ("voter_id", "name"),
        ("bank_passbook", "name"),
        ("disability_certificate", "name"),
        ("ration_card", "head_of_family"),
    ],
    "age": [],  # Computed from DOB
    "dob": [
        ("aadhaar", "dob"),
        ("pan", "dob"),
        ("voter_id", "dob"),
        ("disability_certificate", "dob"),
    ],
    "gender": [
        ("aadhaar", "gender"),
        ("voter_id", "gender"),
    ],
    "address": [
        ("aadhaar", "address"),
        ("voter_id", "address"),
        ("ration_card", "address"),
    ],
    "aadhaar_number": [
        ("aadhaar", "aadhaar_number"),
    ],
    "pan_number": [
        ("pan", "pan_number"),
    ],
    "voter_id_number": [
        ("voter_id", "voter_id_number"),
    ],
    "bank_account": [
        ("bank_passbook", "account_number"),
    ],
    "bank_ifsc": [
        ("bank_passbook", "ifsc"),
    ],
    "phone_number": [],  # Usually not on ID docs
    "pincode": [
        ("aadhaar", "pincode"),
    ],
    "disability_percentage": [
        ("disability_certificate", "disability_percentage"),
    ],
    "disability_type": [
        ("disability_certificate", "disability_type"),
    ],
    "father_name": [
        ("pan", "father_name"),
        ("voter_id", "father_name"),
    ],
}


def _normalise(val: Any) -> str:
    """Lowercase, strip, collapse whitespace for comparison."""
    if val is None:
        return ""
    return " ".join(str(val).lower().strip().split())


def _values_match(user_val: Any, doc_val: Any) -> bool:
    """Fuzzy match: case-insensitive, ignoring extra whitespace."""
    u = _normalise(user_val)
    d = _normalise(doc_val)
    if not u or not d:
        return False
    # Exact match
    if u == d:
        return True
    # One contains the other (partial match for names/addresses)
    if u in d or d in u:
        return True
    return False


# ---------------------------------------------------------------------------
# Verification logic
# ---------------------------------------------------------------------------
def verify_against_documents(
    user_profile: Dict[str, Any],
    documents: List[dict],
) -> VerifySubmissionResponse:
    """
    Cross-check every user profile field against OCR-extracted document data.
    """
    # Build lookup: document_type -> extracted_fields
    doc_lookup: Dict[str, Dict] = {}
    for doc in documents:
        ej = doc.get("extracted_json", {})
        if isinstance(ej, str):
            ej = _json.loads(ej)
        fields = ej.get("fields", ej)
        doc_lookup[doc["document_type"]] = fields

    field_details: List[FieldVerification] = []
    matched = 0
    mismatched = 0
    auto_filled = 0
    corrections: Dict[str, str] = {}

    for user_field, doc_sources in FIELD_MAPPING.items():
        user_val = user_profile.get(user_field)

        if not doc_sources:
            continue  # No document source for this field

        best_doc_val = None
        best_doc_type = None

        for doc_type, doc_field in doc_sources:
            if doc_type in doc_lookup:
                dv = doc_lookup[doc_type].get(doc_field)
                if dv:
                    best_doc_val = dv
                    best_doc_type = doc_type
                    break

        if best_doc_val is None:
            # No document has this field
            field_details.append(FieldVerification(
                field=user_field,
                user_value=str(user_val) if user_val else None,
                document_value=None,
                source_document="none",
                status="not_in_documents",
            ))
            continue

        user_str = str(user_val) if user_val else ""
        is_empty = (
            not user_str
            or user_str.lower() in ("not_specified", "none", "null", "")
        )

        if is_empty:
            # User didn't provide → auto-fill from document
            auto_filled += 1
            corrections[user_field] = str(best_doc_val)
            field_details.append(FieldVerification(
                field=user_field,
                user_value=None,
                document_value=str(best_doc_val),
                source_document=best_doc_type,
                status="auto_filled",
            ))
        elif _values_match(user_val, best_doc_val):
            matched += 1
            field_details.append(FieldVerification(
                field=user_field,
                user_value=str(user_val),
                document_value=str(best_doc_val),
                source_document=best_doc_type,
                status="matched",
            ))
        else:
            mismatched += 1
            corrections[user_field] = str(best_doc_val)
            field_details.append(FieldVerification(
                field=user_field,
                user_value=str(user_val),
                document_value=str(best_doc_val),
                source_document=best_doc_type,
                status="mismatch",
            ))

    total = matched + mismatched + auto_filled
    if total == 0:
        overall = "no_documents"
    elif mismatched > 0:
        overall = "needs_review"
    else:
        overall = "verified"

    return VerifySubmissionResponse(
        household_hash=user_profile.get("household_hash", ""),
        overall_status=overall,
        total_fields_checked=total,
        matched=matched,
        mismatched=mismatched,
        auto_filled=auto_filled,
        field_details=field_details,
        suggested_corrections=corrections,
    )


def auto_fill_profile(
    user_profile: Dict[str, Any],
    documents: List[dict],
) -> AutoFillResponse:
    """
    Merge OCR-extracted data into user profile for missing fields.
    """
    doc_lookup: Dict[str, Dict] = {}
    for doc in documents:
        ej = doc.get("extracted_json", {})
        if isinstance(ej, str):
            ej = _json.loads(ej)
        fields = ej.get("fields", ej)
        doc_lookup[doc["document_type"]] = fields

    filled = dict(user_profile)
    fields_filled: List[str] = []
    fill_sources: Dict[str, str] = {}

    for user_field, doc_sources in FIELD_MAPPING.items():
        current = filled.get(user_field)
        is_empty = (
            current is None
            or str(current).lower() in ("not_specified", "none", "null", "")
        )

        if not is_empty:
            continue  # User already has this field

        for doc_type, doc_field in doc_sources:
            if doc_type in doc_lookup:
                val = doc_lookup[doc_type].get(doc_field)
                if val:
                    filled[user_field] = val
                    fields_filled.append(user_field)
                    fill_sources[user_field] = doc_type
                    break

    return AutoFillResponse(
        household_hash=user_profile.get("household_hash", ""),
        original_profile=user_profile,
        filled_profile=filled,
        fields_filled=fields_filled,
        fill_sources=fill_sources,
    )


# ---------------------------------------------------------------------------
# API Routes (mounted as router in main app)
# ---------------------------------------------------------------------------
# Note: these are attached to the main app via app.include_router(router)
# The actual DB calls use the helper from ocr_service.py

_get_household_docs = None  # Injected at mount time


def set_document_fetcher(fn):
    """Allow the main app to inject the DB fetch function."""
    global _get_household_docs
    _get_household_docs = fn


@router.post("/verify-submission", response_model=VerifySubmissionResponse)
async def verify_submission(req: VerifySubmissionRequest):
    """Cross-check a user's submitted profile against their OCR documents."""
    if _get_household_docs is None:
        raise HTTPException(500, "Document fetcher not configured")

    docs = _get_household_docs(req.household_hash)
    if not docs:
        return VerifySubmissionResponse(
            household_hash=req.household_hash,
            overall_status="no_documents",
            total_fields_checked=0,
            matched=0,
            mismatched=0,
            auto_filled=0,
            field_details=[],
            suggested_corrections={},
        )

    result = verify_against_documents(req.user_profile, docs)
    result.household_hash = req.household_hash
    return result


@router.post("/auto-fill", response_model=AutoFillResponse)
async def auto_fill(req: AutoFillRequest):
    """Fill missing profile fields using OCR-extracted document data."""
    if _get_household_docs is None:
        raise HTTPException(500, "Document fetcher not configured")

    docs = _get_household_docs(req.household_hash)
    if not docs:
        return AutoFillResponse(
            household_hash=req.household_hash,
            original_profile=req.user_profile,
            filled_profile=req.user_profile,
            fields_filled=[],
            fill_sources={},
        )

    return auto_fill_profile(req.user_profile, docs)
