"""
utils.py — Pure helper functions shared across modules.

Rules:
  - No imports from other service modules (no circular deps).
  - No I/O, no network, no database calls.
  - Every function is deterministic and unit-testable.
"""
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List


# ─────────────────────────────────────────────
# Timestamps
# ─────────────────────────────────────────────

def now_iso() -> str:
    """Return current UTC time as an ISO-8601 string."""
    return datetime.utcnow().isoformat()


# ─────────────────────────────────────────────
# Identity
# ─────────────────────────────────────────────

def household_hash(citizen_id: str, phone_number: str) -> str:
    """
    Derive a stable, opaque identifier for a household from citizen_id and phone.
    Used as the primary key across MinIO folders, DB rows, and N8N payloads.
    """
    token = f"{citizen_id}|{phone_number}".strip()
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────
# JSON safety
# ─────────────────────────────────────────────

def safe_json_obj(value: Any) -> Dict[str, Any]:
    """
    Coerce a value to a dict, parsing it if it's a JSON string.
    Returns an empty dict on any failure — never raises.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


# ─────────────────────────────────────────────
# Document normalization
# ─────────────────────────────────────────────

def normalize_required_documents(value: Any) -> List[str]:
    """
    Coerce a list or comma-delimited string of document names into a clean list.
    Strips whitespace and filters empty strings.
    """
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


# ─────────────────────────────────────────────
# Workflow result normalization
# ─────────────────────────────────────────────

def normalize_workflow_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten and standardize the raw JSON blob returned by N8N into the
    canonical response shape expected by the frontend and the DB persistence layer.

    The N8N workflow can return results in several slightly different shapes
    depending on which path through the workflow was taken. This function
    normalises all variants into a single consistent dict.
    """
    if not isinstance(result, dict):
        return {}

    schemes = result.get("eligible_schemes")
    if not isinstance(schemes, list):
        schemes = []

    # Prefer explicit best_match_scheme; fall back to first eligible scheme.
    best_scheme = result.get("best_match_scheme")
    if not best_scheme and schemes:
        first = schemes[0] if isinstance(schemes[0], dict) else {}
        best_scheme = {
            "scheme_id":       first.get("scheme_id"),
            "scheme_name":     first.get("scheme_name") or first.get("name"),
            "benefits":        first.get("benefits"),
            "required_documents": normalize_required_documents(first.get("required_documents")),
            "pdf_template_key": first.get("pdf_template_key"),
        }
    if not isinstance(best_scheme, dict):
        best_scheme = {}

    required_docs = normalize_required_documents(
        best_scheme.get("required_documents") or result.get("required_documents")
    )
    missing_docs   = normalize_required_documents(result.get("missing_required_documents"))
    storage_path   = (
        result.get("storage_path")
        or result.get("filled_pdf_uri")
        or result.get("file_uri")
        or result.get("pdf_uri")
    )
    response_text  = (
        result.get("response_text")
        or result.get("response")
        or result.get("message")
    )

    return {
        "status":        result.get("status") or "processed",
        "response_text": response_text,
        "best_match_scheme": {
            "scheme_id":        best_scheme.get("scheme_id")        or result.get("scheme_id"),
            "scheme_name":      best_scheme.get("scheme_name")      or result.get("scheme_name"),
            "benefits":         best_scheme.get("benefits"),
            "pdf_template_key": best_scheme.get("pdf_template_key") or result.get("pdf_template_key"),
            "required_documents": required_docs,
        },
        "required_documents":         required_docs,
        "missing_required_documents": missing_docs,
        "document_filled":            bool(result.get("document_filled") or storage_path),
        "storage_path":               storage_path,
        "household_hash":             result.get("household_hash"),
        "eligible_count":             len(schemes) if schemes else (1 if best_scheme else 0),
        "next_action": (
            "upload_missing_documents"
            if missing_docs
            else ("review_filled_form" if storage_path else "await_processing")
        ),
    }
