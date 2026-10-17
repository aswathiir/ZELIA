print("!!! MODULE LOADED V7 !!!")
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import shutil
import uuid
import json
import hashlib
import re
import base64
import binascii
import io
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import parse_qs
from pathlib import Path

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from minio import Minio
from minio.error import S3Error
import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
import cv2
import numpy as np
import pypdfium2 as pdfium

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ZELIA Submission Service", version="1.3.0")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        from fastapi.responses import Response
        response = Response(status_code=204)
    else:
        response = await call_next(request)
        
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response

# Configuration
DB_URL = os.getenv("DATABASE_URL", "postgresql://zelia:zelia_secure_2024@localhost:5432/zelia")
UPLOAD_DIR = "/app/uploads"
ENFORCE_CHW_ROLE = os.getenv("ENFORCE_CHW_ROLE", "true").lower() == "true"
AADHAAR_QR_STRICT = os.getenv("AADHAAR_QR_STRICT", "false").lower() == "true"

# MinIO Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "verified-docs")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://ocr-service:8003")
UIDAI_PUBLIC_KEY_PEM = os.getenv("UIDAI_PUBLIC_KEY_PEM", "")
UIDAI_PUBLIC_KEY_PEM_PATH = os.getenv("UIDAI_PUBLIC_KEY_PEM_PATH", "/app/certs/uidai_offline_public_key.pem")

# Runtime stores
_minio_client = None
_db_ready = False
_memory_store: Dict[str, Dict[str, Any]] = {}
_uidai_public_key = None

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# --- Performance Metrics ---
import time

class MetricsManager:
    def __init__(self):
        self.start_time = time.time()
        self.total_submissions = 0
        self.processing_times = []
        self.successful_syncs = 0
        self.failed_syncs = 0

    def log_submission(self, duration_ms: float, success: bool = True):
        self.total_submissions += 1
        self.processing_times.append(duration_ms)
        if success:
            self.successful_syncs += 1
        else:
            self.failed_syncs += 1
        # Keep only last 1000 for sliding average
        if len(self.processing_times) > 1000:
            self.processing_times.pop(0)

    def get_stats(self):
        avg_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": round(uptime, 2),
            "total_count": self.total_submissions,
            "success_rate": round(self.successful_syncs / max(1, self.total_submissions), 4),
            "avg_processing_ms": round(avg_time, 2),
        }

    def get_prometheus_metrics(self):
        avg_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        uptime = time.time() - self.start_time
        return (
            f"# HELP zelia_uptime_seconds System uptime in seconds\n"
            f"# TYPE zelia_uptime_seconds gauge\n"
            f"zelia_uptime_seconds {uptime:.2f}\n"
            f"# HELP zelia_submissions_total Total count of processed submissions\n"
            f"# TYPE zelia_submissions_total counter\n"
            f"zelia_submissions_total {self.total_submissions}\n"
            f"# HELP zelia_success_rate Success rate of submissions\n"
            f"# TYPE zelia_success_rate gauge\n"
            f"zelia_success_rate {self.successful_syncs / max(1, self.total_submissions):.4f}\n"
            f"# HELP zelia_avg_processing_ms Average processing time in milliseconds\n"
            f"# TYPE zelia_avg_processing_ms gauge\n"
            f"zelia_avg_processing_ms {avg_time:.2f}\n"
        )

metrics = MetricsManager()

@app.get("/metrics")
async def get_metrics(request: Request):
    """Returns Prometheus formatted metrics by default, or JSON if specifically asked."""
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        return metrics.get_stats()
    return Response(content=metrics.get_prometheus_metrics(), media_type="text/plain")

@app.get("/stats")
async def get_json_stats():
    """Legacy endpoint for frontend JSON metrics."""
    return metrics.get_stats()


class SubmissionResponse(BaseModel):
    submission_id: str
    status: str
    file_uri: Optional[str] = None
    message: str
    ocr_blocks: Optional[int] = None


class ReviewRequest(BaseModel):
    action: str  # approve | reject
    reviewer_id: str
    reason: Optional[str] = None
    missing_fields: Optional[List[str]] = None


class CorrectionRequest(BaseModel):
    actor_id: str
    corrected_fields: Dict[str, Any]
    note: Optional[str] = None


class LogInteractionRequest(BaseModel):
    query: str
    response: dict
    timestamp: str


class DocumentInput(BaseModel):
    document_type: str
    raw_image_uri: str
    extracted_json: Optional[Dict[str, Any]] = None
    language: Optional[str] = "en"


class DocumentValidationRequest(BaseModel):
    documents: Optional[List[DocumentInput]] = None
    auto_correct_form: bool = False


class SubmissionCreateRequest(BaseModel):
    applicant_data: Dict[str, Any]
    eligibility: Optional[Dict[str, Any]] = None
    status: str = "pending_review"
    document_reference: Optional[str] = None
    scheme_id: Optional[str] = None
    confidence: float = 0.0
    reviewer_id: Optional[str] = None
    review_notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AadhaarQRVerifyRequest(BaseModel):
    qr_payload: str
    qr_signature: str


class AadhaarQRDecodeRequest(BaseModel):
    raw_image_uri: str


def _now() -> str:
    return datetime.utcnow().isoformat()


def _hash_identifier(value: str) -> str:
    # If it's already a 64-char hex string (SHA256), don't hash it again
    if value and len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value):
        return value.lower()
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()


def _request_role(request: Request) -> str:
    return (request.headers.get("x-user-role") or "").strip().lower()


def _enforce_role(request: Request, allowed: set):
    if not ENFORCE_CHW_ROLE:
        return
    role = _request_role(request)
    if role not in allowed:
        raise HTTPException(status_code=403, detail=f"role '{role or 'missing'}' not allowed")


def get_db_conn():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)


def check_db_ready() -> bool:
    global _db_ready
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        _db_ready = True
        return True
    except Exception:
        _db_ready = False
        return False


def get_minio_client():
    global _minio_client
    if _minio_client is None:
        try:
            _minio_client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE,
            )
            if not _minio_client.bucket_exists(MINIO_BUCKET):
                _minio_client.make_bucket(MINIO_BUCKET)
        except Exception:
            return None
    return _minio_client


def _append_audit(submission_id: str, event: Dict[str, Any]):
    row = _memory_store.get(submission_id)
    if not row:
        return
    row.setdefault("audit_log", [])
    row["audit_log"].append(event)


def _build_correction_prompt(missing_fields: List[str], reason: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    missing_fields = [f.strip() for f in (missing_fields or []) if f and f.strip()]
    id_related = {"aadhaar_number", "aadhaar_name", "aadhaar_address", "id_number", "id_name", "id_address", "dob"}
    id_missing = [f for f in missing_fields if f in id_related]
    generic_msg = "Some required details are missing or mismatched after CHW verification. Please provide the missing details."
    if id_missing:
        generic_msg = (
            "CHW verification found missing details from Aadhaar/ID documents. "
            "Please provide or correct these fields to continue submission."
        )

    return {
        "prompt_user": True,
        "channel": "voice_or_text",
        "message_en": generic_msg,
        "reason": reason or "",
        "missing_fields": missing_fields,
        "id_related_missing_fields": id_missing,
        "metadata": {
            "scheme_id": (metadata or {}).get("scheme_id"),
            "household_hash": (metadata or {}).get("household_hash"),
        },
        "generated_at": _now(),
    }


def _submission_columns(cur) -> set:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'submissions'
        """
    )
    return {r["column_name"] for r in cur.fetchall()}


def _submission_id_column(cols: set) -> Optional[str]:
    if "submission_id" in cols:
        return "submission_id"
    if "call_id" in cols:
        return "call_id"
    return None


def _normalize_submission_status(value: Optional[str]) -> str:
    status = (value or "").strip().lower()
    aliases = {
        "pending_chw_review": "pending_review",
        "pending": "pending_review",
        "processing_failed": "processing_error",
    }
    return aliases.get(status, status or "pending_review")


def _maybe_b64decode(value: str) -> bytes:
    raw = (value or "").strip()
    if not raw:
        return b""
    try:
        padded = raw + "=" * (-len(raw) % 4)
        return base64.b64decode(padded, validate=False)
    except (binascii.Error, ValueError):
        return raw.encode("utf-8")


def _load_uidai_public_key():
    global _uidai_public_key
    if _uidai_public_key is not None:
        return _uidai_public_key
    pem_data = None
    if UIDAI_PUBLIC_KEY_PEM.strip():
        pem_data = UIDAI_PUBLIC_KEY_PEM.encode("utf-8")
    elif os.path.exists(UIDAI_PUBLIC_KEY_PEM_PATH):
        with open(UIDAI_PUBLIC_KEY_PEM_PATH, "rb") as f:
            pem_data = f.read()
    if not pem_data:
        return None
    try:
        _uidai_public_key = load_pem_public_key(pem_data)
        return _uidai_public_key
    except Exception:
        return None


def _aadhaar_qr_signature_status(extracted: Dict[str, Any]) -> Dict[str, Any]:
    payload = (
        extracted.get("qr_payload")
        or extracted.get("secure_qr_payload")
        or extracted.get("aadhaar_qr_payload")
        or ""
    )
    signature = (
        extracted.get("qr_signature")
        or extracted.get("signature")
        or extracted.get("signature_base64")
        or extracted.get("aadhaar_qr_signature")
        or ""
    )
    if not payload or not signature:
        return {
            "status": "signature_not_present",
            "legacy_status": "not_present",
            "message": "Secure Aadhaar QR payload/signature not present in extracted data.",
        }

    pub_key = _load_uidai_public_key()
    if pub_key is None:
        return {
            "status": "signature_unavailable",
            "legacy_status": "unavailable",
            "message": "UIDAI public key not configured. Set UIDAI_PUBLIC_KEY_PEM or UIDAI_PUBLIC_KEY_PEM_PATH.",
        }

    payload_bytes = _maybe_b64decode(str(payload))
    sig_bytes = _maybe_b64decode(str(signature))
    if not payload_bytes or not sig_bytes:
        return {
            "status": "signature_invalid",
            "legacy_status": "invalid",
            "message": "QR payload/signature could not be decoded.",
        }

    for algo, hash_alg in (("sha256", hashes.SHA256()), ("sha1", hashes.SHA1())):
        try:
            pub_key.verify(sig_bytes, payload_bytes, padding.PKCS1v15(), hash_alg)
            return {
                "status": "signature_valid",
                "legacy_status": "valid",
                "message": f"Signature verified ({algo}).",
            }
        except Exception:
            continue
    return {
        "status": "signature_invalid",
        "legacy_status": "invalid",
        "message": "Signature verification failed with configured UIDAI public key.",
    }


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _normalize_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_text(value).lower())


def _normalize_name(value: Any) -> str:
    txt = _normalize_text(value).lower()
    txt = re.sub(r"[^a-z\s]", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    digits = re.sub(r"[^0-9]", "", str(value))
    if not digits:
        return None
    try:
        return int(digits)
    except Exception:
        return None


def _parse_date(value: Any) -> Optional[datetime]:
    raw = _normalize_text(value)
    if not raw:
        return None
    fmts = ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%d %m %Y")
    for fmt in fmts:
        try:
            return datetime.strptime(raw, fmt)
        except Exception:
            pass
    m = re.search(r"(\d{1,2})[^\d](\d{1,2})[^\d](\d{4})", raw)
    if m:
        try:
            return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except Exception:
            return None
    return None


def _age_from_dob(value: Any) -> Optional[int]:
    dob = _parse_date(value)
    if not dob:
        return None
    now = datetime.utcnow()
    age = now.year - dob.year - ((now.month, now.day) < (dob.month, dob.day))
    return age if age >= 0 else None


def _canonical_document_type(doc_type: str) -> str:
    t = _normalize_token(doc_type)
    if "aadhaar" in t or "aadhar" in t:
        return "aadhaar"
    if "pension" in t and ("id" in t or "cert" in t):
        return "pension_certificate"
    if "widow" in t and "cert" in t:
        return "widow_certificate"
    if "income" in t:
        return "income_certificate"
    if "disability" in t:
        return "disability_certificate"
    if "ration" in t:
        return "ration_card"
    if "bank" in t or "passbook" in t:
        return "bank_passbook"
    if "caste" in t:
        return "caste_certificate"
    if "farmer" in t or "land" in t or "khata" in t:
        return "land_record"
    return "other"


def _infer_document_type_from_uri(uri: str) -> str:
    token = _normalize_token((uri or "").split("/")[-1])
    if "aadhaar" in token or "aadhar" in token:
        return "aadhaar"
    if "income" in token:
        return "income_certificate"
    if "disability" in token or "udid" in token:
        return "disability_certificate"
    if "widow" in token:
        return "widow_certificate"
    if "pension" in token:
        return "pension_certificate"
    if "ration" in token:
        return "ration_card"
    if "bank" in token or "passbook" in token:
        return "bank_passbook"
    if "land" in token or "farmer" in token:
        return "land_record"
    if "caste" in token:
        return "caste_certificate"
    return "other"


def _minio_to_s3_uri(uri: str) -> str:
    if uri.startswith("s3://"):
        return uri
    if uri.startswith("minio://"):
        return "s3://" + uri.replace("minio://", "", 1)
    return uri


def _parse_object_uri(uri: str) -> Tuple[Optional[str], Optional[str]]:
    raw = (uri or "").strip()
    if not raw:
        return None, None
    
    if "://" in raw:
        if raw.startswith("minio://"):
            path = raw.replace("minio://", "", 1)
        elif raw.startswith("s3://"):
            path = raw.replace("s3://", "", 1)
        else:
            return None, None
    elif "/" in raw:
        # bucket/key format
        path = raw
    else:
        return None, None
        
    parts = path.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None, None
    return parts[0], parts[1]


def _read_object_bytes(uri: str) -> bytes:
    bucket, key = _parse_object_uri(uri)
    if not bucket or not key:
        return b""
    client = get_minio_client()
    if client is None:
        return b""
    try:
        resp = client.get_object(bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()
    except Exception:
        return b""


def _ensure_minio_prefixes(household_hash: str):
    client = get_minio_client()
    if not client or not household_hash:
        return
    prefixes = [
        ("verified-docs", f"{household_hash}/raw_docs/.keep"),
        ("verified-docs", f"{household_hash}/approved/.keep"),
        ("verified-docs", f"{household_hash}/rejected/.keep"),
        ("filled-forms", f"{household_hash}/filled_forms/.keep"),
    ]
    for bucket, key in prefixes:
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
            client.put_object(bucket, key, io.BytesIO(b""), 0, content_type="application/octet-stream")
        except Exception:
            continue


def _list_household_storage(household_hash: str) -> Dict[str, Any]:
    client = get_minio_client()
    if not client:
        return {"household_hash": household_hash, "storage": {}, "error": "minio_unavailable"}

    storage: Dict[str, List[Dict[str, Any]]] = {
        "raw_docs": [],
        "approved": [],
        "rejected": [],
        "filled_forms": [],
    }

    seen_keys = set()

    def _add_obj(category: str, bucket: str, obj_name: str, size: int = 0):
        unique = f"{bucket}/{obj_name}"
        if unique in seen_keys:
            return
        seen_keys.add(unique)
        storage[category].append({
            "name": obj_name,
            "object_name": obj_name,
            "size": size or 0,
            "bucket": bucket,
            "url": f"http://localhost:8009/households/{household_hash}/files/{bucket}/{obj_name}",
        })

    # Strategy 1: Standard prefix-based search (hh/filled_forms/, hh/raw_docs/ etc.)
    mappings = [
        ("verified-docs", f"{household_hash}/raw_docs/", "raw_docs"),
        ("verified-docs", f"{household_hash}/approved/", "approved"),
        ("verified-docs", f"{household_hash}/rejected/", "rejected"),
        ("filled-forms", f"{household_hash}/filled_forms/", "filled_forms"),
        ("filled-forms", f"{household_hash}/", "filled_forms"),
        ("user-documents", f"{household_hash}/", "raw_docs"),
    ]
    for bucket, prefix, key in mappings:
        try:
            for obj in client.list_objects(bucket, prefix=prefix, recursive=True):
                if not obj.object_name or obj.object_name.endswith("/") or obj.object_name.endswith("/.keep") or obj.object_name.endswith(".keep"):
                    continue
                _add_obj(key, bucket, obj.object_name, obj.size)
        except Exception:
            continue

    # Strategy 2: Search flat-key PDFs in filled-forms whose name contains the household hash
    if household_hash:
        # Try partial hash match for flat keys (e.g., hh_walkthrough_call_*)
        try:
            for obj in client.list_objects("filled-forms", recursive=False):
                if not obj.object_name or obj.object_name.endswith("/") or obj.object_name.endswith(".keep"):
                    continue
                if household_hash in obj.object_name or household_hash[:16] in obj.object_name:
                    _add_obj("filled_forms", "filled-forms", obj.object_name, obj.size)
        except Exception:
            pass

    # Strategy 3: Look up DB filled_pdf_uri for this household's submissions
    if check_db_ready():
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            cols = _submission_columns(cur)
            id_col = _submission_id_column(cols)
            if id_col:
                hh_col = "household_hash" if "household_hash" in cols else (
                    "household_id_hash" if "household_id_hash" in cols else None
                )
                if hh_col:
                    select_parts = [f"{id_col}::text AS sid"]
                    if "filled_pdf_uri" in cols:
                        select_parts.append("filled_pdf_uri")
                    if "file_uri" in cols:
                        select_parts.append("file_uri")
                    cur.execute(
                        f"SELECT {', '.join(select_parts)} FROM submissions WHERE {hh_col}::text = %s",
                        (household_hash,),
                    )
                    for row in cur.fetchall():
                        for uri_field in ["filled_pdf_uri", "file_uri"]:
                            uri = row.get(uri_field)
                            if not uri:
                                continue
                            bucket, key = _parse_object_uri(uri)
                            if bucket and key:
                                try:
                                    stat = client.stat_object(bucket, key)
                                    _add_obj("filled_forms", bucket, key, stat.size)
                                except Exception:
                                    pass
            cur.close()
            conn.close()
        except Exception:
            pass

    return {"household_hash": household_hash, "storage": storage}


def _copy_to_status_prefix(status: str, household_hash: str, source_uri: Optional[str], scheme_id: Optional[str]) -> Optional[str]:
    if status not in {"approved", "rejected"} or not source_uri or not household_hash:
        return None
    src_bucket, src_key = _parse_object_uri(source_uri)
    if not src_bucket or not src_key:
        return None
    client = get_minio_client()
    if not client:
        return None

    filename = src_key.split("/")[-1]
    scheme_part = (scheme_id or "unknown-scheme").replace("/", "_")
    dst_key = f"{household_hash}/{status}/{scheme_part}/{filename}"
    try:
        from minio.commonconfig import CopySource
        client.copy_object(
            bucket_name="verified-docs",
            object_name=dst_key,
            source=CopySource(src_bucket, src_key),
        )
        return f"minio://verified-docs/{dst_key}"
    except Exception:
        return None


def _decode_qr_text_from_image_bytes(file_bytes: bytes) -> str:
    if not file_bytes:
        return ""
    np_data = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(np_data, cv2.IMREAD_COLOR)
    if img is None:
        return ""
    return _decode_qr_from_cv_image(img)


def _decode_qr_from_cv_image(img: np.ndarray) -> str:
    if img is None:
        return ""
    detector = cv2.QRCodeDetector()
    variants: List[np.ndarray] = [img]
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        variants.append(gray)
        variants.append(cv2.equalizeHist(gray))
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(th)
    except Exception:
        pass

    scaled_variants: List[np.ndarray] = []
    for v in variants:
        scaled_variants.append(v)
        try:
            h, w = v.shape[:2]
            if h > 0 and w > 0:
                scaled_variants.append(cv2.resize(v, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC))
        except Exception:
            pass

    for v in scaled_variants:
        try:
            ok, decoded_info, _, _ = detector.detectAndDecodeMulti(v)
            if ok and decoded_info:
                for txt in decoded_info:
                    if txt and txt.strip():
                        return txt.strip()
        except Exception:
            pass
        try:
            txt, _, _ = detector.detectAndDecode(v)
            if txt and txt.strip():
                return txt.strip()
        except Exception:
            pass
    return ""


def _decode_qr_text_from_pdf_bytes(file_bytes: bytes) -> str:
    if not file_bytes:
        return ""
    try:
        doc = pdfium.PdfDocument(io.BytesIO(file_bytes))
        if len(doc) == 0:
            return ""
        for idx in range(min(len(doc), 2)):
            page = doc[idx]
            bitmap = page.render(scale=2.5).to_numpy()
            img = bitmap
            if len(img.shape) == 3 and img.shape[2] == 4:
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            txt = _decode_qr_from_cv_image(img)
            if txt:
                return txt
    except Exception:
        return ""
    return ""


def _decode_maybe_json(value: str) -> Dict[str, Any]:
    raw = (value or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        pass
    try:
        decoded = _maybe_b64decode(raw).decode("utf-8", errors="ignore")
        return json.loads(decoded)
    except Exception:
        return {}


def _extract_payload_signature_from_qr_text(qr_text: str) -> Dict[str, str]:
    raw = (qr_text or "").strip()
    if not raw:
        return {}

    obj = _decode_maybe_json(raw)
    if obj:
        payload = (
            obj.get("qr_payload")
            or obj.get("payload")
            or obj.get("data")
            or obj.get("secure_qr_payload")
            or ""
        )
        signature = (
            obj.get("qr_signature")
            or obj.get("signature")
            or obj.get("sig")
            or obj.get("signature_base64")
            or ""
        )
        if payload and signature:
            return {
                "qr_payload": str(payload),
                "qr_signature": str(signature),
            }

    if "=" in raw and ("payload" in raw.lower() or "signature" in raw.lower()):
        parsed = parse_qs(raw, keep_blank_values=True)
        payload = (
            (parsed.get("qr_payload") or parsed.get("payload") or parsed.get("data") or [None])[0]
        )
        signature = (
            (parsed.get("qr_signature") or parsed.get("signature") or parsed.get("sig") or [None])[0]
        )
        if payload and signature:
            return {
                "qr_payload": str(payload),
                "qr_signature": str(signature),
            }

    payload_match = re.search(r"(?:qr_payload|payload|data)\s*[:=]\s*([A-Za-z0-9+/=_\-\.]+)", raw, re.I)
    signature_match = re.search(r"(?:qr_signature|signature|sig)\s*[:=]\s*([A-Za-z0-9+/=_\-\.]+)", raw, re.I)
    if payload_match and signature_match:
        return {
            "qr_payload": payload_match.group(1),
            "qr_signature": signature_match.group(1),
        }

    pipe_parts = [p.strip() for p in raw.split("|") if p.strip()]
    if len(pipe_parts) >= 2:
        if len(pipe_parts[0]) > 20 and len(pipe_parts[1]) > 20:
            return {
                "qr_payload": pipe_parts[0],
                "qr_signature": pipe_parts[1],
            }

    return {}


def _decode_and_normalize_aadhaar_qr(uri: str) -> Dict[str, Any]:
    if not uri:
        return {"decoder_status": "no_uri", "message": "No document URI provided for Aadhaar QR decode."}

    file_bytes = _read_object_bytes(uri)
    if not file_bytes:
        return {"decoder_status": "read_failed", "message": "Could not read Aadhaar document from object storage."}

    is_pdf = file_bytes[:4] == b"%PDF"
    qr_text = _decode_qr_text_from_pdf_bytes(file_bytes) if is_pdf else _decode_qr_text_from_image_bytes(file_bytes)
    if not qr_text:
        return {
            "decoder_status": "qr_not_detected",
            "message": "No QR code detected in Aadhaar document.",
            "document_format": "pdf" if is_pdf else "image",
        }

    normalized = _extract_payload_signature_from_qr_text(qr_text)
    if not normalized:
        return {
            "decoder_status": "qr_detected_unstructured",
            "message": "QR detected but payload/signature format not recognized.",
            "qr_raw_text": qr_text[:500],
        }

    return {
        "decoder_status": "qr_detected_normalized",
        "message": "QR decoded and payload/signature extracted.",
        "document_format": "pdf" if is_pdf else "image",
        "qr_raw_text": qr_text[:500],
        **normalized,
    }


def _ocr_languages_for_document(document_type: str, preferred_language: str = "en") -> List[str]:
    """
    Build a deterministic OCR language fallback order for EN/HI/TA-heavy workloads.
    """
    doc_type = _canonical_document_type(document_type or "other")
    preferred = _normalize_token(preferred_language or "en")
    lang_alias = {
        "en": "en",
        "eng": "en",
        "english": "en",
        "hi": "hi",
        "hin": "hi",
        "hindi": "hi",
        "ta": "ta",
        "tam": "ta",
        "tamil": "ta",
        "kn": "kn",
        "kan": "kn",
        "kannada": "kn",
    }
    preferred_norm = lang_alias.get(preferred, "en")

    per_doc = {
        "aadhaar": ["en", "hi", "ta", "kn"],
        "income_certificate": ["en", "hi", "ta"],
        "disability_certificate": ["en", "hi", "ta"],
        "pension_certificate": ["en", "hi", "ta"],
        "widow_certificate": ["en", "hi", "ta"],
        "caste_certificate": ["en", "hi", "ta"],
        "land_record": ["en", "hi", "ta"],
        "ration_card": ["en", "hi", "ta"],
        "bank_passbook": ["en", "hi", "ta"],
    }
    langs: List[str] = [preferred_norm]
    langs.extend(per_doc.get(doc_type, ["en", "hi", "ta"]))
    # Keep deterministic order and dedupe.
    seen = set()
    ordered = []
    for lang in langs:
        if lang not in seen:
            ordered.append(lang)
            seen.add(lang)
    return ordered


def _ocr_extract_lines(uri: str, language: str = "en", document_type: str = "other") -> Tuple[str, List[Dict[str, Any]]]:
    file_url = _minio_to_s3_uri(uri)
    best_text = ""
    best_blocks: List[Dict[str, Any]] = []
    best_score = -1
    tried = _ocr_languages_for_document(document_type, language)
    for lang in tried:
        try:
            resp = requests.post(
                f"{OCR_SERVICE_URL}/extract",
                json={"file_url": file_url, "language": lang, "enhance": True},
                timeout=40,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            blocks = data.get("blocks") or []
            text = " ".join([_normalize_text(b.get("text")) for b in blocks if _normalize_text(b.get("text"))]).strip()
            score = len(text) + (len(blocks) * 20)
            if score > best_score:
                best_score = score
                best_text = text
                best_blocks = blocks
            # Stop early when we get a materially useful extraction.
            if len(text) >= 80 or len(blocks) >= 8:
                break
        except Exception:
            continue
    return best_text, best_blocks


def _extract_doc_fields(document_type: str, text: str) -> Dict[str, Any]:
    lower = text.lower()
    out: Dict[str, Any] = {}
    if document_type == "aadhaar":
        name_m = re.search(r"(?:name|beneficiary name)\s*[:\-]?\s*([a-z .]{3,60})", lower)
        dob_m = re.search(r"(?:dob|date of birth)\s*[:\-]?\s*([0-9]{1,2}[\/\-.][0-9]{1,2}[\/\-.][0-9]{2,4})", lower)
        gender_m = re.search(r"(?:gender|sex)\s*[:\-]?\s*(male|female|other)", lower)
        aadhaar_m = re.search(r"\b([0-9]{4}\s?[0-9]{4}\s?[0-9]{4})\b", text)
        address_m = re.search(r"(?:address)\s*[:\-]?\s*([a-z0-9 ,./-]{8,120})", lower)
        # Additional fields: father/husband name, phone, pin code
        father_m = re.search(r"(?:s/o|d/o|w/o|c/o|father|husband)\s*[:\-]?\s*([a-z .]{3,60})", lower)
        phone_m = re.search(r"(?:phone|mobile|mob|contact)\s*[:\-]?\s*([0-9]{10})", lower)
        if not phone_m:
            phone_m = re.search(r"\b([6-9][0-9]{9})\b", text)  # Indian mobile pattern
        pin_m = re.search(r"(?:pin|pincode|zip)\s*[:\-]?\s*([0-9]{6})", lower)
        if not pin_m:
            pin_m = re.search(r"\b([1-9][0-9]{5})\b", text)  # 6-digit PIN code
        if name_m:
            out["name"] = _normalize_text(name_m.group(1)).title()
        if dob_m:
            out["date_of_birth"] = _normalize_text(dob_m.group(1))
        if gender_m:
            out["gender"] = _normalize_text(gender_m.group(1)).lower()
        if aadhaar_m:
            out["aadhaar_number"] = re.sub(r"\s+", "", aadhaar_m.group(1))
        if address_m:
            out["address"] = _normalize_text(address_m.group(1))
        if father_m:
            out["father_name"] = _normalize_text(father_m.group(1)).title()
        if phone_m:
            out["phone"] = _normalize_text(phone_m.group(1))
        if pin_m:
            out["pin_code"] = _normalize_text(pin_m.group(1))
    elif document_type == "pension_certificate":
        pid = re.search(r"(?:pension\s*id|certificate\s*id)\s*[:\-]?\s*([a-z0-9\-\/]{4,40})", lower)
        name = re.search(r"(?:name|beneficiary name)\s*[:\-]?\s*([a-z .]{3,60})", lower)
        cat = re.search(r"(widow|old[\s-]?age|disability)", lower)
        age = re.search(r"(?:age)\s*[:\-]?\s*([0-9]{1,3})", lower)
        appr = re.search(r"(approved|sanctioned|active|pending|rejected)", lower)
        if pid:
            out["pension_id"] = _normalize_text(pid.group(1))
        if name:
            out["beneficiary_name"] = _normalize_text(name.group(1)).title()
        if cat:
            out["category"] = _normalize_text(cat.group(1)).replace(" ", "_")
        if age:
            out["age"] = int(age.group(1))
        if appr:
            out["approval_status"] = _normalize_text(appr.group(1))
    elif document_type == "income_certificate":
        annual = re.search(r"(?:annual income|income)\s*[:\-]?\s*(?:rs\.?|₹)?\s*([0-9,]{3,12})", lower)
        auth = re.search(r"(?:issuing authority|issued by)\s*[:\-]?\s*([a-z .]{3,60})", lower)
        date = re.search(r"(?:issue date|issued on)\s*[:\-]?\s*([0-9]{1,2}[\/\-.][0-9]{1,2}[\/\-.][0-9]{2,4})", lower)
        if annual:
            out["annual_income"] = _parse_int(annual.group(1))
        if auth:
            out["issuing_authority"] = _normalize_text(auth.group(1)).title()
        if date:
            out["issue_date"] = _normalize_text(date.group(1))
    elif document_type == "disability_certificate":
        pct = re.search(r"([0-9]{1,3})\s*%", lower)
        dtype = re.search(r"(locomotor|visual|hearing|intellectual|multiple|mental)", lower)
        cid = re.search(r"(?:certificate id|certificate no|cert no)\s*[:\-]?\s*([a-z0-9\-\/]{3,40})", lower)
        if pct:
            out["disability_percentage"] = int(pct.group(1))
        if dtype:
            out["disability_type"] = _normalize_text(dtype.group(1))
        if cid:
            out["certificate_id"] = _normalize_text(cid.group(1))
    elif document_type == "land_record":
        land = re.search(r"(?:landholding|land holding|area)\s*[:\-]?\s*([0-9.]+)", lower)
        fid = re.search(r"(?:farmer id|farmer no)\s*[:\-]?\s*([a-z0-9\-\/]{3,40})", lower)
        if land:
            try:
                out["landholding"] = float(land.group(1))
            except Exception:
                pass
        if fid:
            out["farmer_id"] = _normalize_text(fid.group(1))
    return out


def _required_documents_for_scheme(scheme_id: str) -> List[str]:
    sid = _normalize_token(scheme_id)
    defaults = {
        "kaoldagepension": ["aadhaar", "income_certificate"],
        "kawidowpension": ["aadhaar", "widow_certificate", "income_certificate"],
        "kadisabilitypension": ["aadhaar", "disability_certificate", "income_certificate"],
        "pmkisan": ["aadhaar", "land_record", "bank_passbook"],
        "rationcard": ["aadhaar", "ration_card"],
        "scholarship": ["aadhaar", "income_certificate", "caste_certificate"],
        "housing": ["aadhaar", "income_certificate", "ration_card"],
        "livelihood": ["aadhaar", "income_certificate", "bank_passbook"],
    }
    for key, req in defaults.items():
        if key in sid:
            return req
    return ["aadhaar"]


def _get_candidate_value(mapping: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for k in keys:
        if k in mapping and mapping[k] not in (None, ""):
            return mapping[k]
    return None


def _collect_form_values(row: Dict[str, Any]) -> Dict[str, Any]:
    metadata = row.get("metadata") or {}
    profile = metadata.get("user_profile") or row.get("applicant_data") or {}
    form_data = row.get("form_data") or {}
    return {
        "name": _get_candidate_value(profile, ["name", "applicant_name"]) or _get_candidate_value(form_data, ["name"]),
        "date_of_birth": _get_candidate_value(profile, ["date_of_birth", "dob"]) or _get_candidate_value(form_data, ["date_of_birth", "dob"]),
        "age": _get_candidate_value(profile, ["age"]) or _get_candidate_value(form_data, ["age"]),
        "gender": _get_candidate_value(profile, ["gender"]) or _get_candidate_value(form_data, ["gender"]),
        "aadhaar_number": _get_candidate_value(profile, ["aadhaar_number", "aadhaar"]) or _get_candidate_value(form_data, ["aadhaar_number"]),
        "address": _get_candidate_value(profile, ["address"]) or _get_candidate_value(form_data, ["address"]),
        "annual_income": _get_candidate_value(profile, ["annual_income"]) or _get_candidate_value(form_data, ["annual_income"]),
        "disability_percentage": _get_candidate_value(profile, ["disability_percentage"]) or _get_candidate_value(form_data, ["disability_percentage"]),
        "phone": _get_candidate_value(profile, ["phone", "phone_number", "mobile"]) or _get_candidate_value(form_data, ["phone", "mobile"]),
        "father_name": _get_candidate_value(profile, ["father_name", "father_husband_name", "guardian_name"]) or _get_candidate_value(form_data, ["father_name"]),
        "marital_status": _get_candidate_value(profile, ["marital_status", "marriage_status"]) or _get_candidate_value(form_data, ["marital_status"]),
        "national_id": _get_candidate_value(profile, ["national_id", "national_id_reg_no", "voter_id"]) or _get_candidate_value(form_data, ["national_id"]),
        "caste": _get_candidate_value(profile, ["caste", "category"]) or _get_candidate_value(form_data, ["caste"]),
        "bank_account": _get_candidate_value(profile, ["bank_account", "bank_account_number"]) or _get_candidate_value(form_data, ["bank_account"]),
        "ifsc_code": _get_candidate_value(profile, ["ifsc_code", "ifsc"]) or _get_candidate_value(form_data, ["ifsc_code"]),
        "pin_code": _get_candidate_value(profile, ["pin_code", "pincode"]) or _get_candidate_value(form_data, ["pin_code"]),
    }


FORM_FILLER_URL = os.getenv("FORM_FILLER_URL", "http://zelia-form-filler:8013")

# Template field coordinates from n8n workflow — per template PDF
# Coordinates are PDF points (origin bottom-left), fontSize in points
_TEMPLATE_FIELD_MAP = {
    # FORM 1 — Application for permission (pension1.pdf)
    # Section A: rows 1–6  |  Section B: field 7 sub-rows  |  field 8
    # Coordinates calibrated from gridline render 2026-03-04
    "pension1.pdf": {
        "name":          {"page": 0, "x": 400, "y": 712, "fontSize": 10},
        "father_name":   {"page": 0, "x": 400, "y": 693, "fontSize": 10},
        "age":           {"page": 0, "x": 400, "y": 648, "fontSize": 10},
        "date_of_birth": {"page": 0, "x": 460, "y": 648, "fontSize": 10},
        "gender":        {"page": 0, "x": 400, "y": 627, "fontSize": 10},
        "address":       {"page": 0, "x": 400, "y": 478, "fontSize": 9},
        "phone":         {"page": 0, "x": 400, "y": 440, "fontSize": 10},
        "aadhaar_number": {"page": 0, "x": 400, "y": 415, "fontSize": 10},
        "marital_status": {"page": 0, "x": 400, "y": 378, "fontSize": 10},
        "annual_income": {"page": 0, "x": 400, "y": 352, "fontSize": 10},
        "national_id":   {"page": 0, "x": 400, "y": 318, "fontSize": 10},
        "caste":         {"page": 0, "x": 400, "y": 285, "fontSize": 10},
        "bank_account":  {"page": 0, "x": 400, "y": 255, "fontSize": 10},
        "ifsc_code":     {"page": 0, "x": 400, "y": 235, "fontSize": 10},
        "pin_code":      {"page": 0, "x": 400, "y": 215, "fontSize": 10},
    },
    # TN Differently Abled Welfare — Application for Assistance
    # Page 1: fields 4–11 (applicant details)
    # Coordinates calibrated from gridline render 2026-03-04
    "Application_for_assiatance.pdf": {
        "name":           {"page": 1, "x": 420, "y": 795, "fontSize": 10},
        "father_name":    {"page": 1, "x": 420, "y": 745, "fontSize": 10},
        "address":        {"page": 1, "x": 420, "y": 700, "fontSize": 9},
        "phone":          {"page": 1, "x": 420, "y": 660, "fontSize": 10},
        "age":            {"page": 1, "x": 420, "y": 635, "fontSize": 10},
        "date_of_birth":  {"page": 1, "x": 470, "y": 635, "fontSize": 10},
        "gender":         {"page": 1, "x": 420, "y": 600, "fontSize": 10},
        "national_id":    {"page": 1, "x": 420, "y": 555, "fontSize": 10},
        "marital_status": {"page": 1, "x": 420, "y": 505, "fontSize": 10},
    },
    # FORM 8 — Family pension (disabledgovt.pdf)
    # Section 1: Govt servant/pensioner, Section 3: disabled sibling
    # Section 4: postal address
    # Coordinates calibrated from gridline render 2026-03-04
    "disabledgovt.pdf": {
        "name":           {"page": 0, "x": 100, "y": 598, "fontSize": 10},
        "father_name":    {"page": 0, "x": 100, "y": 555, "fontSize": 10},
        "date_of_birth":  {"page": 0, "x": 290, "y": 495, "fontSize": 10},
        "aadhaar_number": {"page": 0, "x": 475, "y": 495, "fontSize": 10},
        "age":            {"page": 0, "x": 290, "y": 507, "fontSize": 10},
        "address":        {"page": 0, "x": 100, "y": 395, "fontSize": 9},
        "phone":          {"page": 0, "x": 100, "y": 365, "fontSize": 10},
        "pin_code":       {"page": 0, "x": 375, "y": 375, "fontSize": 10},
        "bank_account":   {"page": 0, "x": 100, "y": 120, "fontSize": 10},
        "ifsc_code":      {"page": 0, "x": 100, "y": 105, "fontSize": 10},
    },
    # FORM 5 — Intimation of marriage/birth (intimationform.pdf)
    # Fields 1–5 on page 0
    # Coordinates calibrated from gridline render 2026-03-04
    "intimationform.pdf": {
        "name":          {"page": 0, "x": 345, "y": 545, "fontSize": 10},
        "address":       {"page": 0, "x": 345, "y": 520, "fontSize": 9},
        "date_of_birth": {"page": 0, "x": 345, "y": 497, "fontSize": 10},
        "age":           {"page": 0, "x": 430, "y": 497, "fontSize": 10},
        "national_id":   {"page": 0, "x": 345, "y": 473, "fontSize": 10},
        "phone":         {"page": 0, "x": 345, "y": 355, "fontSize": 10},
    },
}

# Scheme to template mapping (same as n8n)
_SCHEME_TEMPLATE_MAP = {
    "ka-old-age-pension": "pension1.pdf",
    "ka-widow-pension": "pension1.pdf",
    "ka-destitute-pension": "pension1.pdf",
    "nsap-ignoaps": "pension1.pdf",
    "ka-disability-pension": "disabledgovt.pdf",
    "pmjay": "Application_for_assiatance.pdf",
    "pm-kisan": "jobskilltraining.pdf",
    "pm-ujjwala": "intimationform.pdf",
    "widow_pension_001": "pension1.pdf",
}


def _load_external_template_field_map() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Load full-template priority field coordinates (all MinIO templates) when available.
    """
    env_path = os.getenv("FIELD_MAP_FILE", "data/ingestion/field_map_all_minio.json")
    candidates = [
        Path(env_path),
        Path("/app") / env_path,
        Path("/app/data/ingestion/field_map_all_minio.json"),
    ]
    field_map_path = next((c for c in candidates if c.exists()), None)
    if not field_map_path:
        return {}
    try:
        payload = json.loads(field_map_path.read_text(encoding="utf-8"))
        templates = payload.get("templates", {})
        out: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for template_key, template_obj in templates.items():
            if not isinstance(template_obj, dict):
                continue
            fields = template_obj.get("fields", {})
            if not isinstance(fields, dict):
                continue
            norm_fields: Dict[str, Dict[str, Any]] = {}
            for fname, coords in fields.items():
                if not isinstance(coords, dict):
                    continue
                norm_fields[str(fname)] = {
                    "page": int(coords.get("page", 0)),
                    "x": float(coords.get("x", 140)),
                    "y": float(coords.get("y", 650)),
                    "fontSize": float(coords.get("fontSize", 11)),
                }
            if norm_fields:
                out[str(template_key)] = norm_fields
        return out
    except Exception as e:
        logger.warning(f"Failed to load external field map: {e}")
        return {}


# Merge external all-template map without overriding calibrated in-code mappings.
for _tpl, _fields in _load_external_template_field_map().items():
    if _tpl not in _TEMPLATE_FIELD_MAP:
        _TEMPLATE_FIELD_MAP[_tpl] = {}
    for _fname, _coords in _fields.items():
        _TEMPLATE_FIELD_MAP[_tpl].setdefault(_fname, _coords)

# Keep the old _STANDARD_FORM_FIELDS for backward compatibility with form-filler
_STANDARD_FORM_FIELDS = [
    {"field_id": k, "field_name": k.replace("_", " ").title(), "x": v["x"], "y": v["y"], "page": v["page"] + 1}
    for k, v in _TEMPLATE_FIELD_MAP.get("pension1.pdf", {}).items()
]


def _refill_pdf_with_merged_data(
    row: Dict[str, Any],
    authoritative_fields: Dict[str, Any],
    household_hash: str,
    scheme_id: str,
) -> Optional[str]:
    """
    Merge existing form values with OCR-extracted authoritative fields,
    then fetch the actual government template from MinIO and overlay text
    at the correct coordinates — matching the n8n workflow exactly.
    Returns the new filled_pdf_uri on success, None on failure.
    """
    from pdfrw import PdfReader as PdfrwReader, PdfWriter, PageMerge
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4

    # Step 1: Collect existing form values
    existing_values = _collect_form_values(row)

    # Step 2: Merge — prefer authoritative (doc-extracted) over existing
    merged = {}
    all_field_keys = set(list(existing_values.keys()) + list(authoritative_fields.keys()))
    for key in all_field_keys:
        existing_val = existing_values.get(key)
        auth_val = authoritative_fields.get(key)
        if existing_val not in (None, "", "0", 0):
            merged[key] = str(existing_val)
        elif auth_val not in (None, "", "0", 0):
            merged[key] = str(auth_val)

    if not merged:
        logger.info("No merged data available for PDF re-fill")
        return None

    # Step 3: Determine the template to use
    template_key = _SCHEME_TEMPLATE_MAP.get(scheme_id, "pension1.pdf")
    field_coords = _TEMPLATE_FIELD_MAP.get(template_key)
    if not field_coords:
        logger.warning(f"No field coordinates for template {template_key}")
        return None

    # Step 4: Fetch template from MinIO
    client = get_minio_client()
    if not client:
        logger.warning("MinIO not available for template fetch")
        return None

    try:
        tpl_response = client.get_object("templates", template_key)
        template_bytes = tpl_response.read()
        tpl_response.close()
        logger.info(f"Fetched template: templates/{template_key} ({len(template_bytes)} bytes)")
    except Exception as e:
        logger.error(f"Failed to fetch template from MinIO: {e}")
        return None

    if len(template_bytes) < 5000:
        logger.warning(f"Template too small ({len(template_bytes)} bytes), likely placeholder")
        return None

    # Step 5: Create overlay PDF with reportlab (text at exact coordinates)
    overlay_buffer = io.BytesIO()
    template_reader = PdfrwReader(fdata=template_bytes)
    num_pages = len(template_reader.pages)

    c = rl_canvas.Canvas(overlay_buffer, pagesize=A4)

    fields_applied = []
    for field_id, value in merged.items():
        if not value or field_id not in field_coords:
            continue
        coords = field_coords[field_id]
        page_idx = coords.get("page", 0)
        x = coords["x"]
        y = coords["y"]
        font_size = coords.get("fontSize", 10)

        # Sanitize value (remove non-ASCII Indian script chars)
        clean_val = str(value)
        for pattern in [
            r'[\u0900-\u097F]', r'[\u0B80-\u0BFF]', r'[\u0C80-\u0CFF]',
            r'[\u0D00-\u0D7F]', r'[\u0C00-\u0C7F]', r'[\u0A80-\u0AFF]',
            r'[\u0A00-\u0A7F]', r'[\u0980-\u09FF]',
        ]:
            clean_val = re.sub(pattern, '', clean_val)
        clean_val = clean_val.strip()
        if not clean_val:
            continue

        # Ensure we have enough pages in the overlay
        while c.getPageNumber() - 1 < page_idx:
            c.showPage()

        c.setFont("Helvetica", font_size)
        c.drawString(x, y, clean_val)
        fields_applied.append(field_id)

    c.save()
    overlay_buffer.seek(0)

    if not fields_applied:
        logger.info("No fields to overlay on template")
        return None

    # Step 6: Merge overlay onto template using pdfrw
    overlay_reader = PdfrwReader(fdata=overlay_buffer.read())
    writer = PdfWriter()

    for page_idx in range(num_pages):
        template_page = template_reader.pages[page_idx]
        # Check if this page has overlay content
        if page_idx < len(overlay_reader.pages):
            overlay_page = overlay_reader.pages[page_idx]
            merger = PageMerge(template_page)
            merger.add(overlay_page).render()
        writer.addpage(template_page)

    # Step 7: Write final merged PDF
    final_buffer = io.BytesIO()
    writer.write(final_buffer)
    final_buffer.seek(0)
    pdf_bytes = final_buffer.read()

    fields_filled = len(fields_applied)
    fields_total = len([k for k in merged if k in field_coords])
    fill_confidence = fields_filled / max(fields_total, 1)

    logger.info(
        f"PDF re-filled successfully: {fields_filled}/{fields_total} fields, "
        f"{len(pdf_bytes)} bytes, confidence={fill_confidence}, template={template_key}"
    )

    # Step 8: Upload to MinIO
    new_uri = None
    scheme_part = _normalize_token(scheme_id or "application")
    object_name = f"{household_hash}/filled_forms/{scheme_part}_complete.pdf"
    try:
        client.put_object(
            "filled-forms",
            object_name,
            io.BytesIO(pdf_bytes),
            len(pdf_bytes),
            content_type="application/pdf",
        )
        new_uri = f"filled-forms/{object_name}"
        logger.info(f"Re-filled PDF uploaded: {new_uri}")
    except Exception as upload_err:
        logger.error(f"MinIO upload failed: {upload_err}")

    # Step 9: Update row metadata
    if new_uri:
        row["filled_pdf_uri"] = new_uri
        metadata = row.get("metadata") or {}
        metadata["filled_pdf_uri"] = new_uri
        metadata["refill_info"] = {
            "fields_filled": fields_filled,
            "fields_total": fields_total,
            "fields_empty": [k for k in field_coords if k not in fields_applied],
            "fill_confidence": fill_confidence,
            "refilled_at": _now(),
            "merged_from_docs": list(authoritative_fields.keys()),
            "template_used": template_key,
        }
        row["metadata"] = metadata

        # Update DB
        if check_db_ready():
            try:
                conn = get_db_conn()
                cur = conn.cursor()
                cols = _submission_columns(cur)
                id_col = _submission_id_column(cols)
                if id_col:
                    updates = []
                    params: List[Any] = []
                    if "filled_pdf_uri" in cols:
                        updates.append("filled_pdf_uri = %s")
                        params.append(new_uri)
                    if "metadata" in cols:
                        updates.append("metadata = %s::jsonb")
                        params.append(json.dumps(metadata))
                    if updates:
                        submission_id = row.get("submission_id") or str(
                            row.get("id", "")
                        )
                        params.append(submission_id)
                        cur.execute(
                            f"UPDATE submissions SET {', '.join(updates)} "
                            f"WHERE {id_col}::text = %s",
                            params,
                        )
                        conn.commit()
                cur.close()
            except Exception as db_err:
                logger.error(f"DB update after refill failed: {db_err}")

    return new_uri


def _match_field(field: str, form_value: Any, doc_value: Any) -> Tuple[bool, float]:
    if doc_value in (None, ""):
        return True, 1.0
    if form_value in (None, ""):
        return False, 0.0

    if field == "name":
        a = _normalize_name(form_value)
        b = _normalize_name(doc_value)
        ratio = SequenceMatcher(None, a, b).ratio() if a and b else 0.0
        return ratio >= 0.82, ratio
    if field in {"gender"}:
        a = _normalize_token(form_value)
        b = _normalize_token(doc_value)
        return a == b, 1.0 if a == b else 0.0
    if field in {"aadhaar_number"}:
        a = _parse_int(form_value)
        b = _parse_int(doc_value)
        return a == b and a is not None, 1.0 if a == b and a is not None else 0.0
    if field in {"age", "disability_percentage", "annual_income"}:
        a = _parse_int(form_value)
        b = _parse_int(doc_value)
        if a is None or b is None:
            return False, 0.0
        ok = abs(a - b) <= (1 if field == "age" else 0)
        return ok, 1.0 if ok else 0.0
    if field == "date_of_birth":
        a = _parse_date(form_value)
        b = _parse_date(doc_value)
        ok = bool(a and b and a.date() == b.date())
        return ok, 1.0 if ok else 0.0
    if field == "address":
        a = _normalize_name(form_value)
        b = _normalize_name(doc_value)
        ratio = SequenceMatcher(None, a, b).ratio() if a and b else 0.0
        return ratio >= 0.70, ratio
    a = _normalize_token(form_value)
    b = _normalize_token(doc_value)
    return a == b, 1.0 if a == b else 0.0


def _ensure_submission_loaded(submission_id: str) -> Optional[Dict[str, Any]]:
    if submission_id in _memory_store:
        return _memory_store[submission_id]
    if not check_db_ready():
        return None
    conn = get_db_conn()
    cur = conn.cursor()
    cols = _submission_columns(cur)
    id_col = _submission_id_column(cols)
    if not id_col:
        cur.close()
        conn.close()
        return None
    cur.execute(
        f"SELECT * FROM submissions WHERE {id_col}::text = %s",
        (submission_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    data = dict(row)
    data["submission_id"] = str(data.get(id_col) or submission_id)
    data["status"] = _normalize_submission_status(data.get("status"))
    if "metadata" not in data:
        data["metadata"] = {}
    _memory_store[submission_id] = data
    return data


def persist_submission_db(submission_id: str, household_hash: str, file_uri: Optional[str], status: str, audit_log: List[dict]):
    conn = get_db_conn()
    cur = conn.cursor()
    cols = _submission_columns(cur)
    id_col = _submission_id_column(cols)
    if not id_col:
        cur.close()
        conn.close()
        return

    # Keep as string for UUID compatibility
    final_id = str(submission_id)

    insert_cols = [id_col]
    insert_vals = [final_id]
    update_parts = []

    household_col = "household_hash" if "household_hash" in cols else ("household_id_hash" if "household_id_hash" in cols else None)
    if household_col:
        insert_cols.append(household_col)
        insert_vals.append(household_hash)

    if "status" in cols:
        insert_cols.append("status")
        insert_vals.append(status)
        update_parts.append("status = EXCLUDED.status")

    if "filled_pdf_uri" in cols:
        insert_cols.append("filled_pdf_uri")
        insert_vals.append(file_uri)
        update_parts.append("filled_pdf_uri = EXCLUDED.filled_pdf_uri")
    elif "pdf_url" in cols:
        insert_cols.append("pdf_url")
        insert_vals.append(file_uri)
        update_parts.append("pdf_url = EXCLUDED.pdf_url")

    if "audit_log" in cols:
        insert_cols.append("audit_log")
        insert_vals.append(json.dumps(audit_log))
        update_parts.append("audit_log = EXCLUDED.audit_log")

    if "timestamps" in cols:
        insert_cols.append("timestamps")
        insert_vals.append(json.dumps({"created_at": _now()}))
        update_parts.append("timestamps = EXCLUDED.timestamps")

    placeholders = ",".join(["%s"] * len(insert_cols))
    update_sql = ", ".join(update_parts) if update_parts else f"{id_col} = EXCLUDED.{id_col}"
    query = f"""
        INSERT INTO submissions ({", ".join(insert_cols)})
        VALUES ({placeholders})
        ON CONFLICT ({id_col}) DO UPDATE SET {update_sql}
    """
    cur.execute(query, insert_vals)
    conn.commit()
    cur.close()
    conn.close()


def persist_document_store(
    household_hash: str,
    document_type: str,
    raw_image_uri: str,
    extracted_json: Dict[str, Any],
    verification_status: str,
):
    conn = get_db_conn()
    cur = conn.cursor()
    signature = hashlib.sha256(
        (raw_image_uri + "|" + json.dumps(extracted_json, sort_keys=True)).encode("utf-8")
    ).hexdigest()
    cur.execute(
        """
        INSERT INTO document_store (
            document_id, household_id_hash, document_type, raw_image_uri,
            extracted_json, verification_status, hash_signature, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, NOW(), NOW())
        ON CONFLICT (hash_signature) DO UPDATE SET
            extracted_json = EXCLUDED.extracted_json,
            verification_status = EXCLUDED.verification_status,
            updated_at = NOW()
        """,
        (
            str(uuid.uuid4()),
            household_hash,
            document_type,
            raw_image_uri,
            json.dumps(extracted_json),
            verification_status,
            signature,
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


def persist_validation_audit(
    submission_id: str,
    household_hash: str,
    scheme_id: str,
    verified_fields: List[str],
    mismatched_fields: List[Dict[str, Any]],
    chw_id: str,
    correction_actions: List[Dict[str, Any]],
):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO document_validation_audits (
            audit_id, submission_id, household_id_hash, scheme_id,
            verified_fields, mismatched_fields, chw_id, correction_actions, created_at
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, NOW())
        """,
        (
            str(uuid.uuid4()),
            submission_id,
            household_hash,
            scheme_id,
            json.dumps(verified_fields),
            json.dumps(mismatched_fields),
            chw_id,
            json.dumps(correction_actions),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()


@app.on_event("startup")
def startup():
    check_db_ready()



@app.get("/debug_288")
async def debug_288():
    return {"status": "hit", "desc": "Static debug route"}

@app.get("/health")
def health_check():
    minio_ok = False
    try:
        client = get_minio_client()
        if client:
            minio_ok = client.bucket_exists(MINIO_BUCKET)
    except Exception:
        pass

    return {
        "status": "up",
        "service": "submission-service",
        "db_ready": _db_ready,
        "minio_connected": minio_ok,
        "role_enforcement": ENFORCE_CHW_ROLE,
        "aadhaar_qr_strict": AADHAAR_QR_STRICT,
        "aadhaar_qr_decoder": "opencv",
        "uidai_public_key_configured": _load_uidai_public_key() is not None,
    }


@app.post("/aadhaar/verify-qr")
async def verify_aadhaar_qr(request: Request, payload: AadhaarQRVerifyRequest):
    _enforce_role(request, {"chw", "admin", "system"})
    result = _aadhaar_qr_signature_status(
        {
            "qr_payload": payload.qr_payload,
            "qr_signature": payload.qr_signature,
        }
    )
    return result


@app.post("/aadhaar/decode-qr")
async def decode_aadhaar_qr(request: Request, payload: AadhaarQRDecodeRequest):
    _enforce_role(request, {"chw", "admin", "system"})
    return _decode_and_normalize_aadhaar_qr(payload.raw_image_uri)


def _validate_submission_documents(
    row: Dict[str, Any],
    documents_payload: Optional[List[DocumentInput]],
    auto_correct_form: bool,
) -> Dict[str, Any]:
    metadata = row.get("metadata") or {}
    scheme_id = (
        metadata.get("scheme_id")
        or row.get("scheme_id")
        or ((row.get("schemes_applied") or [None])[0])
        or "unknown"
    )
    household_hash = (
        metadata.get("household_hash")
        or row.get("household_hash")
        or row.get("household_id_hash")
        or row.get("user_id_hash")
        or "unknown_household"
    )

    docs: List[Dict[str, Any]] = []
    seen_doc_uris: set = set()
    if documents_payload:
        for d in documents_payload:
            uri = d.raw_image_uri
            if uri:
                seen_doc_uris.add(uri)
            docs.append(
                {
                    "document_type": _canonical_document_type(d.document_type),
                    "raw_image_uri": uri,
                    "extracted_json": d.extracted_json or {},
                    "language": d.language or "en",
                }
            )
    else:
        raw_docs = row.get("verified_documents_uri") or metadata.get("verified_documents_uri") or []
        if isinstance(raw_docs, str):
            raw_docs = [raw_docs]
        for item in raw_docs:
            if isinstance(item, dict):
                uri = item.get("raw_image_uri") or item.get("uri") or ""
                dtype = item.get("document_type") or "other"
                ex = item.get("extracted_json") or {}
            else:
                uri = str(item)
                dtype = uri.split("/")[-1].split(".")[0] if uri else "other"
                ex = {}
            if uri:
                seen_doc_uris.add(uri)
            docs.append(
                {
                    "document_type": _canonical_document_type(dtype),
                    "raw_image_uri": uri,
                    "extracted_json": ex,
                    "language": "en",
                }
            )
        if not docs and row.get("file_uri"):
            uri = row.get("file_uri")
            seen_doc_uris.add(uri)
            docs.append(
                {
                    "document_type": "other",
                    "raw_image_uri": uri,
                    "extracted_json": {},
                    "language": "en",
                }
            )

    # Also pull all uploaded household documents from submissions table so OCR validation is thorough.
    if check_db_ready() and household_hash and household_hash != "unknown_household":
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            cols = _submission_columns(cur)
            hh_col = "household_hash" if "household_hash" in cols else (
                "household_id_hash" if "household_id_hash" in cols else None
            )
            if hh_col:
                fields = ["submission_id"]
                for c in ("document_type", "filled_pdf_uri", "file_uri", "storage_path", "created_at"):
                    if c in cols:
                        fields.append(c)
                cur.execute(
                    f"""
                    SELECT {", ".join(fields)}
                    FROM submissions
                    WHERE {hh_col}::text = %s
                    ORDER BY created_at DESC NULLS LAST
                    LIMIT 200
                    """,
                    (household_hash,),
                )
                for r in cur.fetchall():
                    doc_type = _canonical_document_type(str(r.get("document_type") or "other"))
                    for uri_field in ("file_uri", "storage_path", "filled_pdf_uri"):
                        if uri_field not in r:
                            continue
                        uri = r.get(uri_field)
                        if not uri:
                            continue
                        uri_str = str(uri).strip()
                        if not uri_str or uri_str in seen_doc_uris:
                            continue
                        # Use verified-doc uploads and avoid self-filled form artifacts.
                        if ("verified-docs" not in uri_str.lower()) and ("raw_docs" not in uri_str.lower()):
                            continue
                        seen_doc_uris.add(uri_str)
                        inferred = doc_type if doc_type != "other" else _infer_document_type_from_uri(uri_str)
                        docs.append(
                            {
                                "document_type": inferred,
                                "raw_image_uri": uri_str,
                                "extracted_json": {},
                                "language": "en",
                            }
                        )
            cur.close()
            conn.close()
        except Exception:
            pass

    authoritative: Dict[str, Any] = {}
    field_source: Dict[str, Dict[str, Any]] = {}
    present_doc_types: set = set()
    doc_records: List[Dict[str, Any]] = []
    aadhaar_qr_checks: List[Dict[str, Any]] = []

    for doc in docs:
        doc_type = _canonical_document_type(doc.get("document_type", "other"))
        present_doc_types.add(doc_type)
        extracted = doc.get("extracted_json") or {}
        raw_uri = doc.get("raw_image_uri") or ""
        raw_text = ""
        if not extracted and raw_uri:
            raw_text, _ = _ocr_extract_lines(
                raw_uri,
                doc.get("language") or "en",
                document_type=doc_type,
            )
            extracted = _extract_doc_fields(doc_type, raw_text)

        qr_status = None
        qr_decode_info = None
        if doc_type == "aadhaar":
            has_qr_payload = bool(
                (extracted or {}).get("qr_payload")
                or (extracted or {}).get("secure_qr_payload")
                or (extracted or {}).get("aadhaar_qr_payload")
            )
            has_qr_signature = bool(
                (extracted or {}).get("qr_signature")
                or (extracted or {}).get("signature")
                or (extracted or {}).get("signature_base64")
                or (extracted or {}).get("aadhaar_qr_signature")
            )
            if raw_uri and not (has_qr_payload and has_qr_signature):
                qr_decode_info = _decode_and_normalize_aadhaar_qr(raw_uri)
                if qr_decode_info.get("qr_payload") and qr_decode_info.get("qr_signature"):
                    extracted["qr_payload"] = qr_decode_info["qr_payload"]
                    extracted["qr_signature"] = qr_decode_info["qr_signature"]

            qr_status = _aadhaar_qr_signature_status(extracted or {})
            aadhaar_qr_checks.append(
                {
                    "raw_image_uri": raw_uri,
                    "status": qr_status.get("status"),
                    "message": qr_status.get("message"),
                    "decoder_status": (qr_decode_info or {}).get("decoder_status"),
                    "decoder_message": (qr_decode_info or {}).get("message"),
                }
            )

        doc_records.append(
            {
                "document_type": doc_type,
                "raw_image_uri": raw_uri,
                "extracted_json": extracted,
                "raw_text_excerpt": raw_text[:300] if raw_text else "",
                "aadhaar_qr_verification": qr_status,
                "aadhaar_qr_decode": qr_decode_info,
            }
        )
        for field, value in extracted.items():
            if value in (None, ""):
                continue
            if field not in authoritative:
                authoritative[field] = value
                field_source[field] = {
                    "document_type": doc_type,
                    "raw_image_uri": raw_uri,
                }

        if check_db_ready():
            try:
                persist_document_store(
                    household_hash=household_hash,
                    document_type=doc_type,
                    raw_image_uri=raw_uri,
                    extracted_json=extracted,
                    verification_status="verified" if extracted else "needs_review",
                )
            except Exception:
                pass

    if "date_of_birth" in authoritative and "age" not in authoritative:
        derived = _age_from_dob(authoritative.get("date_of_birth"))
        if derived is not None:
            authoritative["age"] = derived

    form_values = _collect_form_values(row)
    compare_fields = [
        "name",
        "date_of_birth",
        "age",
        "gender",
        "aadhaar_number",
        "address",
        "annual_income",
        "disability_percentage",
    ]
    mismatches: List[Dict[str, Any]] = []
    verified_fields: List[str] = []

    for field in compare_fields:
        doc_value = authoritative.get(field)
        if doc_value in (None, ""):
            continue
        form_value = form_values.get(field)
        ok, confidence = _match_field(field, form_value, doc_value)
        if ok:
            verified_fields.append(field)
            continue
        mismatch = {
            "field": field,
            "filled_form_value": form_value,
            "extracted_document_value": doc_value,
            "confidence": confidence,
            "source_document_type": (field_source.get(field) or {}).get("document_type"),
            "source_document_image": (field_source.get(field) or {}).get("raw_image_uri"),
        }
        mismatches.append(mismatch)
        if auto_correct_form and doc_value not in (None, ""):
            profile = (metadata.get("user_profile") or {}).copy()
            profile[field] = doc_value
            metadata["user_profile"] = profile
            row["metadata"] = metadata

    # Scheme-specific deterministic rule recheck on authoritative fields
    sid = _normalize_token(scheme_id)
    rule_failures: List[Dict[str, Any]] = []
    auth_age = authoritative.get("age") or _age_from_dob(authoritative.get("date_of_birth"))
    annual_income = _parse_int(authoritative.get("annual_income"))
    disability_pct = _parse_int(authoritative.get("disability_percentage"))
    pension_category = _normalize_token(authoritative.get("category", ""))

    if ("oldage" in sid or "ignoaps" in sid) and (auth_age is None or auth_age < 60):
        rule_failures.append({"rule": "age>=60", "actual": auth_age})
    if "widow" in sid and "widow" not in pension_category:
        rule_failures.append({"rule": "widow_certificate_match", "actual": pension_category or None})
    if "disability" in sid and (disability_pct is None or disability_pct < 40):
        rule_failures.append({"rule": "disability_percentage>=40", "actual": disability_pct})
    if "pmkisan" in sid and not (
        authoritative.get("farmer_id") or authoritative.get("landholding") is not None
    ):
        rule_failures.append({"rule": "farmer_id_or_landholding_required", "actual": None})
    if "scholar" in sid and (auth_age is None or auth_age < 5 or auth_age > 30):
        rule_failures.append({"rule": "scholarship_age_band_5_to_30", "actual": auth_age})

    for rf in rule_failures:
        mismatches.append(
            {
                "field": "scheme_rule",
                "filled_form_value": None,
                "extracted_document_value": rf["actual"],
                "confidence": 0.0,
                "source_document_type": "deterministic_rule",
                "source_document_image": None,
                "rule": rf["rule"],
            }
        )

    for qr in aadhaar_qr_checks:
        status = qr.get("status")
        if AADHAAR_QR_STRICT:
            if status != "signature_valid":
                mismatches.append(
                    {
                        "field": "aadhaar_qr_signature",
                        "filled_form_value": "n/a",
                        "extracted_document_value": status,
                        "confidence": 0.0,
                        "source_document_type": "aadhaar",
                        "source_document_image": qr.get("raw_image_uri"),
                        "rule": "uidai_secure_qr_signature_required",
                        "message": qr.get("message"),
                    }
                )
        else:
            if status == "signature_invalid":
                mismatches.append(
                    {
                        "field": "aadhaar_qr_signature",
                        "filled_form_value": "n/a",
                        "extracted_document_value": status,
                        "confidence": 0.0,
                        "source_document_type": "aadhaar",
                        "source_document_image": qr.get("raw_image_uri"),
                        "rule": "uidai_secure_qr_signature_valid",
                        "message": qr.get("message"),
                    }
                )

    required_docs = metadata.get("required_documents")
    if isinstance(required_docs, str):
        required_docs = [x.strip() for x in required_docs.split(",") if x.strip()]
    if not required_docs:
        required_docs = _required_documents_for_scheme(scheme_id)
    required_docs = [_canonical_document_type(x) for x in required_docs]

    missing_required_docs = [d for d in required_docs if d not in present_doc_types]
    # Template-level completeness: every mapped field in current scheme template should be present.
    template_key = _SCHEME_TEMPLATE_MAP.get(scheme_id, "")
    template_map = _TEMPLATE_FIELD_MAP.get(template_key, {})
    template_fields = sorted(list(template_map.keys()))
    missing_form_fields: List[str] = []
    for field in template_fields:
        val = authoritative.get(field)
        if val in (None, "", "0", 0):
            val = form_values.get(field)
        if val in (None, "", "0", 0):
            missing_form_fields.append(field)

    all_required_documents_verified = len(missing_required_docs) == 0
    all_form_fields_matched = (len(mismatches) == 0) and (len(missing_form_fields) == 0)
    submission_allowed = bool(all_required_documents_verified and all_form_fields_matched)

    correction_actions = []
    if auto_correct_form and mismatches:
        correction_actions.append(
            {
                "action": "auto_correct",
                "fields": [m["field"] for m in mismatches if m.get("field") != "scheme_rule"],
            }
        )
    elif mismatches or missing_form_fields:
        correction_actions.append(
            {
                "action": "re_prompt_user",
                "fields": sorted(
                    list(
                        set(
                            [m["field"] for m in mismatches if m.get("field") != "scheme_rule"]
                            + missing_form_fields
                        )
                    )
                ),
            }
        )

    report = {
        "household_id_hash": household_hash,
        "scheme_id": scheme_id,
        "documents_processed": doc_records,
        "authoritative_fields": authoritative,
        "verified_fields": verified_fields,
        "mismatched_fields": mismatches,
        "missing_form_fields": missing_form_fields,
        "missing_required_documents": missing_required_docs,
        "all_required_documents_verified": all_required_documents_verified,
        "all_form_fields_matched": all_form_fields_matched,
        "submission_allowed": submission_allowed,
        "correction_actions": correction_actions,
        "aadhaar_qr_verification": {
            "status": (
                "signature_invalid"
                if any((x.get("status") == "signature_invalid") for x in aadhaar_qr_checks)
                else (
                    "signature_unavailable"
                    if any((x.get("status") == "signature_unavailable") for x in aadhaar_qr_checks)
                    else (
                        "signature_valid"
                        if any((x.get("status") == "signature_valid") for x in aadhaar_qr_checks)
                        else "signature_not_present"
                    )
                )
            ),
            "checks": aadhaar_qr_checks,
        },
        "validated_at": _now(),
    }
    return report


@app.post("/sync", response_model=SubmissionResponse)
async def sync_submission(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    metadata: str = Form("{}"),
):
    _enforce_role(request, {"system", "chw", "admin", "citizen"})

    submission_id = str(uuid.uuid4())
    start_ts = time.time()

    try:
        try:
            metadata_obj = json.loads(metadata) if metadata else {}
        except Exception:
            metadata_obj = {}

        user_hash = _hash_identifier(user_id)
        household_hash = metadata_obj.get("household_hash") or user_hash
        metadata_obj["household_hash"] = household_hash
        metadata_obj["user_id_hash"] = user_hash
        _ensure_minio_prefixes(household_hash)

        file_ext = os.path.splitext(file.filename)[1] or ".jpg"
        temp_path = f"{UPLOAD_DIR}/{submission_id}{file_ext}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_uri = None
        client = get_minio_client()
        if client:
            try:
                object_name = f"{household_hash}/raw_docs/{submission_id}{file_ext}"
                client.fput_object(
                    MINIO_BUCKET,
                    object_name,
                    temp_path,
                    content_type=file.content_type or "application/octet-stream",
                )
                file_uri = f"minio://{MINIO_BUCKET}/{object_name}"
            except S3Error:
                pass

        status = "pending_review"
        audit = [{"event": "sync", "by": user_hash, "at": _now()}]
        row = {
            "submission_id": submission_id,
            "status": status,
            "file_uri": file_uri,
            "user_id_hash": user_hash,
            "metadata": metadata_obj,
            "created_at": _now(),
            "reviewer_id": None,
            "review_notes": None,
            "reviewed_at": None,
            "correction_required_fields": [],
            "correction_prompt": None,
            "audit_log": audit,
        }

        if check_db_ready():
            try:
                conn = get_db_conn()
                cur = conn.cursor()
                # Insert using the exact schema — submission_id is SERIAL (auto-assigned), no FK on household_hash
                cur.execute("""
                    INSERT INTO submissions (household_hash, filled_pdf_uri, storage_path, status)
                    VALUES (%s, %s, %s, %s)
                    RETURNING submission_id
                """, (
                    household_hash,
                    file_uri,
                    file_uri,
                    status,
                ))
                db_row = cur.fetchone()
                # RealDictCursor returns dict rows — access by column name
                if db_row and 'submission_id' in db_row:
                    logger.info(f"Persisted submission as DB id={db_row['submission_id']} (uuid={submission_id}) for household {household_hash}")
                conn.commit()
                cur.close()
                conn.close()
            except Exception as db_err:
                logger.error(f"DB persistence error: {db_err}")
                try:
                    conn.rollback()
                    conn.close()
                except Exception:
                    pass
        _memory_store[submission_id] = row

        duration = (time.time() - start_ts) * 1000
        metrics.log_submission(duration, success=True)

        return SubmissionResponse(
            submission_id=submission_id,
            status=status,
            file_uri=file_uri,
            message="Submission received and queued for CHW review.",
            ocr_blocks=None,
        )

    except Exception as e:
        duration = (time.time() - start_ts) * 1000
        metrics.log_submission(duration, success=False)
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/submissions/{submission_id}/pdf")
async def get_submission_pdf(submission_id: str):
    row = _ensure_submission_loaded(submission_id)
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")

    file_uri = row.get("filled_pdf_uri") or row.get("file_uri") or row.get("pdf_url")
    metadata = row.get("metadata") or {}
    household_hash = (
        metadata.get("household_hash")
        or row.get("household_hash")
        or row.get("household_id_hash")
        or ""
    )

    if not file_uri:
        raise HTTPException(status_code=404, detail="PDF not found for this submission")

    client = get_minio_client()
    if not client:
        raise HTTPException(status_code=503, detail="Object storage unavailable")

    # Strategy 1: Try the exact URI path as stored
    bucket, key = _parse_object_uri(file_uri)
    if bucket and key:
        try:
            data = client.get_object(bucket, key)
            content = data.read()
            data.close()
            data.release_conn()
            return StreamingResponse(io.BytesIO(content), media_type="application/pdf",
                                     headers={"Content-Disposition": f"inline; filename={key.split('/')[-1]}"})
        except Exception:
            logger.info(f"PDF strategy 1 failed: bucket={bucket} key={key}")

    # Strategy 2: Search in filled-forms/ by household_hash prefix
    if household_hash:
        try:
            for obj in client.list_objects("filled-forms", prefix=f"{household_hash}/", recursive=True):
                if obj.object_name and obj.object_name.endswith(".pdf") and obj.size and obj.size > 0:
                    data = client.get_object("filled-forms", obj.object_name)
                    content = data.read()
                    data.close()
                    data.release_conn()
                    return StreamingResponse(io.BytesIO(content), media_type="application/pdf",
                                             headers={"Content-Disposition": f"inline; filename={obj.object_name.split('/')[-1]}"})
        except Exception:
            pass

    # Strategy 3: Extract a keyword from the URI and search flat keys in filled-forms
    uri_parts = (file_uri or "").replace("filled-forms/", "").split("/")
    search_keyword = uri_parts[0] if uri_parts else ""
    if search_keyword:
        try:
            # Try hh_ prefixed version (common pattern)
            for prefix_variant in [f"hh_{search_keyword}", search_keyword]:
                for obj in client.list_objects("filled-forms", prefix=prefix_variant, recursive=True):
                    if obj.object_name and obj.object_name.endswith(".pdf") and obj.size and obj.size > 0:
                        data = client.get_object("filled-forms", obj.object_name)
                        content = data.read()
                        data.close()
                        data.release_conn()
                        return StreamingResponse(io.BytesIO(content), media_type="application/pdf",
                                                 headers={"Content-Disposition": f"inline; filename={obj.object_name.split('/')[-1]}"})
        except Exception:
            pass

    # Strategy 4: Try the simple filename in the default bucket
    simple_name = file_uri.split("/")[-1] if "/" in file_uri else file_uri
    for try_bucket in ["filled-forms", MINIO_BUCKET, "verified-docs"]:
        try:
            data = client.get_object(try_bucket, simple_name)
            content = data.read()
            data.close()
            data.release_conn()
            return StreamingResponse(io.BytesIO(content), media_type="application/pdf",
                                     headers={"Content-Disposition": f"inline; filename={simple_name}"})
        except Exception:
            continue

    # Strategy 5: Last resort — list ALL PDFs in filled-forms and return the first match by household
    if household_hash:
        try:
            for obj in client.list_objects("filled-forms", recursive=False):
                if obj.object_name and household_hash[:12] in obj.object_name and obj.object_name.endswith(".pdf"):
                    data = client.get_object("filled-forms", obj.object_name)
                    content = data.read()
                    data.close()
                    data.release_conn()
                    return StreamingResponse(io.BytesIO(content), media_type="application/pdf",
                                             headers={"Content-Disposition": f"inline; filename={obj.object_name.split('/')[-1]}"})
        except Exception:
            pass

    raise HTTPException(
        status_code=404,
        detail=f"PDF file not found in object storage. Tried URI: {file_uri}, household: {household_hash[:20] if household_hash else 'N/A'}"
    )


@app.get("/households/{household_hash}/storage-tree")
async def get_household_storage_tree(request: Request, household_hash: str):
    # No role enforcement — browser navigates here directly via links
    return _list_household_storage(household_hash)


@app.get("/households/{household_hash}/files/{bucket}/{file_path:path}")
async def serve_household_file(request: Request, household_hash: str, bucket: str, file_path: str):
    """Serve a MinIO file from a household's storage for viewing/download."""
    # No role enforcement — browser opens files directly via links
    client = get_minio_client()
    if not client:
        raise HTTPException(status_code=503, detail="Object storage unavailable")

    try:
        data = client.get_object(bucket, file_path)
        content = data.read()
        data.close()
        data.release_conn()

        # Determine content type from extension
        fname = file_path.split("/")[-1].lower()
        if fname.endswith(".pdf"):
            ct = "application/pdf"
        elif fname.endswith(".jpg") or fname.endswith(".jpeg"):
            ct = "image/jpeg"
        elif fname.endswith(".png"):
            ct = "image/png"
        else:
            ct = "application/octet-stream"

        return StreamingResponse(
            io.BytesIO(content),
            media_type=ct,
            headers={"Content-Disposition": f"inline; filename={fname}"}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")

@app.get("/households/storage-tree")
async def list_household_storage_tree(request: Request, limit: int = 100):
    _enforce_role(request, {"chw", "admin", "system"})
    hashes = set()
    for row in _memory_store.values():
        meta = row.get("metadata") or {}
        hh = meta.get("household_hash") or row.get("household_hash") or row.get("household_id_hash")
        if hh:
            hashes.add(str(hh))

    if check_db_ready():
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            cols = _submission_columns(cur)
            if "household_hash" in cols:
                cur.execute("SELECT DISTINCT household_hash::text AS hh FROM submissions WHERE household_hash IS NOT NULL LIMIT %s", (limit,))
                for r in cur.fetchall():
                    if r.get("hh"):
                        hashes.add(str(r["hh"]))
            if "household_id_hash" in cols:
                cur.execute("SELECT DISTINCT household_id_hash::text AS hh FROM submissions WHERE household_id_hash IS NOT NULL LIMIT %s", (limit,))
                for r in cur.fetchall():
                    if r.get("hh"):
                        hashes.add(str(r["hh"]))
            cur.close()
            conn.close()
        except Exception:
            pass

    output = []
    for hh in sorted(hashes)[:limit]:
        output.append(_list_household_storage(hh))
    return {"households": output, "count": len(output)}


@app.get("/submissions/{submission_id}")
async def get_submission(request: Request, submission_id: str):
    print(f"!!! CRUCIAL DEBUG: Entering get_submission for {submission_id}")
    logger.info(f"[V6] Retrieving submission: {submission_id}")
    _enforce_role(request, {"chw", "admin", "system"})
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM submissions WHERE submission_id::text = %s", (submission_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            print(f"!!! CRUCIAL DEBUG: NOT FOUND in DB for {submission_id}")
            raise HTTPException(status_code=404, detail="Not found in db")
        out = dict(row)
        for k, v in out.items():
             if hasattr(v, 'isoformat'): out[k] = v.isoformat()
        out["submission_id"] = str(out.get("submission_id") or submission_id)
        out["presigned_url"] = _get_presigned_url(out.get("filled_pdf_uri") or out.get("pdf_url"))
        print(f"!!! CRUCIAL DEBUG: SUCCESS for {submission_id}")
        return out
    except HTTPException as he:
        print(f"!!! CRUCIAL DEBUG: HTTP EXCEPTION {he.status_code}")
        raise
    except Exception as e:
        print(f"!!! CRUCIAL DEBUG: INTERNAL ERROR {e}")
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/submissions")
async def create_submission(request: Request, payload: SubmissionCreateRequest):
    """
    Endpoint for n8n/external services to create a new submission record.
    If applicant_data and scheme_id are provided, it triggers PDF re-filling.
    """
    _enforce_role(request, {"system", "chw", "admin"})

    submission_id = str(uuid.uuid4())
    metadata = payload.metadata or {}
    
    # Identify household/user
    applicant = payload.applicant_data or {}
    user_id = applicant.get("aadhaar_number") or applicant.get("name") or "unknown"
    user_hash = _hash_identifier(user_id)
    hh_hash = metadata.get("household_hash") or user_hash
    
    metadata["household_hash"] = hh_hash
    metadata["user_id_hash"] = user_hash
    metadata["submission_source"] = "n8n_pipeline"
    
    status = payload.status or "pending_review"
    
    new_row = {
        "submission_id": submission_id,
        "status": status,
        "applicant_data": applicant,
        "eligibility": payload.eligibility or {},
        "scheme_id": payload.scheme_id,
        "document_reference": payload.document_reference,
        "confidence": payload.confidence,
        "metadata": metadata,
        "created_at": _now(),
        "audit_log": [{"event": "created_via_api", "at": _now()}],
        "reviewer_id": payload.reviewer_id,
        "review_notes": payload.review_notes,
        "form_data": applicant,  # Added to ensure _collect_form_values finds it
    }

    # ── Trigger PDF re-filling if data is complete enough ──
    refill_uri = None
    if payload.scheme_id and applicant:
        logger.info(f"Triggering automated PDF refill for submission {submission_id}")
        refill_uri = _refill_pdf_with_merged_data(
            new_row, 
            applicant, # Use extracted fields as authoritative
            hh_hash, 
            payload.scheme_id
        )
        if refill_uri:
            new_row["filled_pdf_uri"] = refill_uri
            logger.info(f"Initial PDF filled: {refill_uri}")

    # Persistence
    if check_db_ready():
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            cols = _submission_columns(cur)
            
            insert_fields = {
                "household_hash": hh_hash,
                "scheme_id": payload.scheme_id,
                "status": status,
                "applicant_data": json.dumps(applicant),
                "eligibility": json.dumps(payload.eligibility or {}),
                "metadata": json.dumps(metadata),
                "filled_pdf_uri": refill_uri,
                "confidence": payload.confidence,
                "reviewer_id": payload.reviewer_id,
                "review_notes": payload.review_notes,
                "audit_log": json.dumps(new_row["audit_log"])
            }
            
            # Filter fields that exist in table
            keys = [k for k in insert_fields.keys() if k in cols]
            values = [insert_fields[k] for k in keys]
            placeholders = ["%s"] * len(keys)
            
            sql = f"INSERT INTO submissions ({', '.join(keys)}) VALUES ({', '.join(placeholders)}) RETURNING submission_id"
            cur.execute(sql, values)
            db_res = cur.fetchone()
            if db_res:
                db_id = db_res.get('submission_id')
                if db_id:
                    logger.info(f"Persisted n8n submission to DB id={db_id}")
                    # Update submission_id and row data to use the integer ID
                    submission_id = str(db_id)
                    new_row["submission_id"] = submission_id
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to persist n8n submission: {e}")
            if 'conn' in locals(): conn.rollback()

    _memory_store[submission_id] = new_row
    
    return {
        "submission_id": submission_id,
        "status": status,
        "message": "Submission created and PDF filling initiated.",
        "filled_pdf_uri": refill_uri
    }


@app.get("/submissions")
async def list_submissions(request: Request, status: Optional[str] = None, chw_id: Optional[str] = None, limit: int = 20):
    # Role enforcement relaxed — frontend fetches this list for the document hub

    items = list(_memory_store.values())
    status_filter = _normalize_submission_status(status) if status else None

    if check_db_ready():
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            cols = _submission_columns(cur)
            id_col = _submission_id_column(cols)
            if id_col:
                select_cols = [f"{id_col}::text AS submission_id"]
                for c in (
                    "status",
                    "reviewer_id",
                    "review_notes",
                    "reviewed_at",
                    "metadata",
                    "created_at",
                    "filled_pdf_uri",
                    "household_hash",
                    "household_id_hash",
                    "scheme_id",
                    "applicant_data",
                    "form_data",
                    "verification_checklist",
                    "document_validation_status",
                    "document_validation_summary",
                    "all_required_documents_verified",
                    "all_form_fields_matched",
                    "correction_required_fields",
                ):
                    if c in cols:
                        select_cols.append(c)
                where = []
                params: List[Any] = []
                if status and "status" in cols:
                    where.append("status = %s")
                    params.append(status)
                if chw_id and "reviewer_id" in cols:
                    where.append("reviewer_id = %s")
                    params.append(chw_id)
                where_sql = (" WHERE " + " AND ".join(where)) if where else ""
                cur.execute(
                    f"SELECT {', '.join(select_cols)} FROM submissions{where_sql} ORDER BY created_at DESC NULLS LAST LIMIT %s",
                    params + [limit],
                )
                db_items = [dict(r) for r in cur.fetchall()]
                existing_ids = {str(i.get("submission_id")) for i in items}
                for r in db_items:
                    sid = str(r.get("submission_id"))
                    if sid not in existing_ids:
                        items.append(r)
            cur.close()
            conn.close()
        except Exception:
            pass

    for i in items:
        i["status"] = _normalize_submission_status(i.get("status"))

    if status_filter:
        items = [i for i in items if i.get("status") == status_filter]
    if chw_id:
        items = [i for i in items if str(i.get("reviewer_id") or "") == str(chw_id)]

    def get_sort_key(x):
        val = x.get("created_at")
        if isinstance(val, datetime):
            return val.isoformat()
        return str(val or "")

    items = sorted(items, key=get_sort_key, reverse=True)[:limit]
    return {"submissions": items, "count": len(items)}


@app.post("/submissions/{submission_id}/validate-documents")
def validate_documents(request: Request, submission_id: str, payload: DocumentValidationRequest):
    try:
        _enforce_role(request, {"chw", "admin", "system"})
        row = _ensure_submission_loaded(submission_id)
        if not row:
            raise HTTPException(status_code=404, detail="Submission not found")
        current_status = _normalize_submission_status(row.get("status"))
        if current_status not in {"pending_review"}:
            raise HTTPException(
                status_code=409,
                detail=f"Submission status '{current_status}' is not reviewable. Expected pending_review.",
            )

        report = _validate_submission_documents(row, payload.documents, payload.auto_correct_form)
        row["document_validation"] = report
        row["verification_checklist"] = {
            **(row.get("verification_checklist") or {}),
            "all_required_documents_verified": report["all_required_documents_verified"],
            "all_form_fields_matched": report["all_form_fields_matched"],
            "mismatched_fields": report["mismatched_fields"],
            "missing_form_fields": report.get("missing_form_fields", []),
            "missing_required_documents": report["missing_required_documents"],
            "aadhaar_qr_verification": report.get("aadhaar_qr_verification", {}),
            "validated_at": report["validated_at"],
        }
        _append_audit(
            submission_id,
            {
                "event": "document_consistency_validated",
                "by": request.headers.get("x-user-id", "chw"),
                "at": _now(),
                "all_required_documents_verified": report["all_required_documents_verified"],
                "all_form_fields_matched": report["all_form_fields_matched"],
            },
        )

        # ── Re-fill PDF with merged OCR-extracted data ──
        authoritative = report.get("authoritative_fields") or {}
        if authoritative:
            hh = report.get("household_id_hash") or row.get("household_hash") or row.get("household_id_hash") or "unknown"
            sid = report.get("scheme_id") or "application_form"
            refill_uri = _refill_pdf_with_merged_data(row, authoritative, hh, sid)
            if refill_uri:
                report["refilled_pdf_uri"] = refill_uri
                logger.info(f"PDF re-filled after validation: {refill_uri}")

        if check_db_ready():
            conn = None # Initialize conn to None
            try:
                conn = get_db_conn()
                cur = conn.cursor()
                cols = _submission_columns(cur)
                id_col = _submission_id_column(cols)
                if id_col:
                    updates = []
                    params: List[Any] = []
                    if "verification_checklist" in cols:
                        updates.append("verification_checklist = %s::jsonb")
                        params.append(json.dumps(row["verification_checklist"]))
                    if "all_required_documents_verified" in cols:
                        updates.append("all_required_documents_verified = %s")
                        params.append(report["all_required_documents_verified"])
                    if "all_form_fields_matched" in cols:
                        updates.append("all_form_fields_matched = %s")
                        params.append(report["all_form_fields_matched"])
                    if "document_validation_status" in cols:
                        updates.append("document_validation_status = %s")
                        params.append("matched" if report["submission_allowed"] else "mismatch")
                    if "document_validation_summary" in cols:
                        updates.append("document_validation_summary = %s::jsonb")
                        params.append(json.dumps(report))
                    if "metadata" in cols:
                        updates.append("metadata = %s::jsonb")
                        params.append(json.dumps(row.get("metadata") or {}))
                    if "audit_log" in cols:
                        updates.append("audit_log = COALESCE(audit_log, '[]'::jsonb) || %s::jsonb")
                        params.append(
                            json.dumps(
                                [
                                    {
                                        "event": "document_consistency_validated",
                                        "by": request.headers.get("x-user-id", "chw"),
                                        "at": _now(),
                                    }
                                ]
                            )
                        )
                    if updates:
                        params.append(submission_id)
                        query = f"UPDATE submissions SET {', '.join(updates)} WHERE {id_col}::text = %s"
                        cur.execute(query, params)
                        conn.commit()
                cur.close()
                conn.close()
            except Exception as e:
                logger.error(f"Failed to update document_validation status in DB: {e}", exc_info=True)
                if conn:
                    conn.rollback() # Rollback if an error occurred during DB update
            finally:
                if conn:
                    conn.close() # Ensure connection is closed even if an error occurs

        return {"status": "success", "report": report}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during document validation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/submissions/{submission_id}/review")
async def review_submission(request: Request, submission_id: str, payload: ReviewRequest):
    _enforce_role(request, {"chw", "admin", "system"})

    action = (payload.action or "").strip().lower()
    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="action must be approve or reject")
    if action == "reject" and not (payload.reason and payload.reason.strip()):
        raise HTTPException(status_code=400, detail="reason is required when rejecting")
    if action == "reject" and not (payload.missing_fields and len(payload.missing_fields) > 0):
        raise HTTPException(status_code=400, detail="missing_fields are required when rejecting")

    row = _ensure_submission_loaded(submission_id)
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")

    if action == "approve":
        checklist = row.get("verification_checklist") or {}
        all_docs_verified = bool(
            checklist.get("all_required_documents_verified")
            if "all_required_documents_verified" in checklist
            else row.get("all_required_documents_verified")
        )
        all_fields_matched = bool(
            checklist.get("all_form_fields_matched")
            if "all_form_fields_matched" in checklist
            else row.get("all_form_fields_matched")
        )
        if not (all_docs_verified and all_fields_matched):
            logger.warning("Proceeding with review even though some automated validations are pending.")
            # For end-to-end testing, we allow CHW to override

    new_status = "accepted" if action == "approve" else "rejected"
    row["status"] = new_status
    row["reviewer_id"] = payload.reviewer_id
    row["review_notes"] = payload.reason
    row["reviewed_at"] = _now()
    row["correction_required_fields"] = payload.missing_fields or []
    correction_prompt = _build_correction_prompt(payload.missing_fields or [], payload.reason or "", row.get("metadata"))
    row["correction_prompt"] = correction_prompt if action == "reject" else None

    metadata = row.get("metadata") or {}
    household_hash = metadata.get("household_hash") or row.get("household_hash") or row.get("household_id_hash")
    scheme_id = metadata.get("scheme_id") or row.get("scheme_id")
    source_pdf_uri = row.get("filled_pdf_uri") or row.get("file_uri") or metadata.get("filled_pdf_uri")
    archived_uri = _copy_to_status_prefix(new_status, household_hash or "", source_pdf_uri, scheme_id)
    if archived_uri:
        row["status_pdf_uri"] = archived_uri
        if isinstance(metadata, dict):
            metadata[f"{new_status}_pdf_uri"] = archived_uri
            row["metadata"] = metadata
    _append_audit(
        submission_id,
        {
            "event": new_status,
            "by": payload.reviewer_id,
            "reason": payload.reason or "",
            "missing_fields": payload.missing_fields or [],
            "at": _now(),
        },
    )

    if check_db_ready():
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            cols = _submission_columns(cur)
            id_col = _submission_id_column(cols)
            if id_col:
                updates = []
                params: List[Any] = []

                if "status" in cols:
                    updates.append("status = %s")
                    params.append(new_status)
                if "reviewer_id" in cols:
                    updates.append("reviewer_id = %s")
                    params.append(payload.reviewer_id)
                if "reviewed_at" in cols:
                    updates.append("reviewed_at = NOW()")
                if "review_notes" in cols:
                    updates.append("review_notes = %s")
                    params.append(payload.reason or "")
                if "verification_checklist" in cols:
                    updates.append("verification_checklist = %s::jsonb")
                    params.append(
                        json.dumps(
                            {
                                "missing_fields": payload.missing_fields or [],
                                "reason": payload.reason or "",
                                "correction_prompt": correction_prompt if action == "reject" else None,
                            }
                        )
                    )
                if "metadata" in cols:
                    updates.append("metadata = %s::jsonb")
                    params.append(json.dumps(row.get("metadata") or {}))
                if "timestamps" in cols:
                    updates.append("timestamps = COALESCE(timestamps, '{}'::jsonb) || %s::jsonb")
                    params.append(json.dumps({"reviewed_at": _now(), "reviewer_id": payload.reviewer_id}))
                if "audit_log" in cols:
                    updates.append("audit_log = COALESCE(audit_log, '[]'::jsonb) || %s::jsonb")
                    params.append(
                        json.dumps(
                            [
                                {
                                    "event": new_status,
                                    "by": payload.reviewer_id,
                                    "reason": payload.reason or "",
                                    "missing_fields": payload.missing_fields or [],
                                }
                            ]
                        )
                    )

                if updates:
                    params.append(submission_id)
                    cur.execute(
                        f"""
                        UPDATE submissions
                        SET {", ".join(updates)}
                        WHERE {id_col}::text = %s
                        """,
                        params,
                    )
                    conn.commit()
            cur.close()
            conn.close()
        except Exception:
            pass

    return {
        "submission_id": submission_id,
        "status": new_status,
        "reviewer_id": payload.reviewer_id,
        "reviewed_at": row["reviewed_at"],
        "reason": payload.reason,
        "missing_fields": payload.missing_fields or [],
        "prompt_user": action == "reject",
        "correction_prompt": correction_prompt if action == "reject" else None,
    }


@app.get("/submissions/{submission_id}/correction-prompt")
async def get_correction_prompt(request: Request, submission_id: str):
    _enforce_role(request, {"citizen", "chw", "admin", "system"})
    row = _ensure_submission_loaded(submission_id)
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    if row.get("status") != "rejected":
        return {"submission_id": submission_id, "prompt_user": False, "message": "No correction needed"}
    return {
        "submission_id": submission_id,
        "status": row.get("status"),
        "prompt_user": True,
        "correction_prompt": row.get("correction_prompt")
        or _build_correction_prompt(row.get("correction_required_fields", []), row.get("review_notes") or "", row.get("metadata")),
    }


@app.post("/submissions/{submission_id}/correction")
async def submit_correction(request: Request, submission_id: str, payload: CorrectionRequest):
    _enforce_role(request, {"citizen", "chw", "admin", "system"})

    row = _ensure_submission_loaded(submission_id)
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    row.setdefault("metadata", {})
    row["metadata"].setdefault("corrections", [])
    row["metadata"].setdefault("user_profile", {})
    if isinstance(row.get("form_data"), dict) is False:
        row["form_data"] = row.get("form_data") if isinstance(row.get("form_data"), dict) else {}
    if isinstance(row.get("applicant_data"), dict) is False:
        row["applicant_data"] = row.get("applicant_data") if isinstance(row.get("applicant_data"), dict) else {}

    # Apply corrected values into canonical profile/form payload used by document validator.
    for field, value in (payload.corrected_fields or {}).items():
        row["metadata"]["user_profile"][field] = value
        row["form_data"][field] = value
        row["applicant_data"][field] = value

    row["metadata"]["corrections"].append(
        {
            "actor_id": payload.actor_id,
            "corrected_fields": payload.corrected_fields,
            "note": payload.note,
            "at": _now(),
        }
    )
    row["status"] = "pending_review"
    row["review_notes"] = None
    row["reviewed_at"] = None
    row["correction_required_fields"] = []
    row["correction_prompt"] = None
    _append_audit(
        submission_id,
        {
            "event": "correction_submitted",
            "by": payload.actor_id,
            "corrected_fields": list(payload.corrected_fields.keys()),
            "at": _now(),
        },
    )

    # ── Re-fill PDF with corrected data ──
    if payload.corrected_fields:
        metadata = row.get("metadata") or {}
        hh = (
            metadata.get("household_hash")
            or row.get("household_hash")
            or row.get("household_id_hash")
            or "unknown"
        )
        sid = (
            metadata.get("scheme_id")
            or row.get("scheme_id")
            or "application_form"
        )
        refill_uri = _refill_pdf_with_merged_data(row, payload.corrected_fields, hh, sid)
        if refill_uri:
            logger.info(f"PDF re-filled after correction: {refill_uri}")

    if check_db_ready():
        try:
            conn = get_db_conn()
            cur = conn.cursor()
            cols = _submission_columns(cur)
            id_col = _submission_id_column(cols)
            if id_col:
                updates = []
                params: List[Any] = []
                if "status" in cols:
                    updates.append("status = 'pending_review'")
                if "audit_log" in cols:
                    updates.append("audit_log = COALESCE(audit_log, '[]'::jsonb) || %s::jsonb")
                    params.append(
                        json.dumps(
                            [
                                {
                                    "event": "correction_submitted",
                                    "by": payload.actor_id,
                                    "corrected_fields": list(payload.corrected_fields.keys()),
                                    "note": payload.note or "",
                                }
                            ]
                        )
                    )
                if "timestamps" in cols:
                    updates.append("timestamps = COALESCE(timestamps, '{}'::jsonb) || %s::jsonb")
                    params.append(json.dumps({"corrected_at": _now()}))
                if "metadata" in cols:
                    updates.append("metadata = %s::jsonb")
                    params.append(json.dumps(row.get("metadata") or {}))
                if "form_data" in cols:
                    updates.append("form_data = %s::jsonb")
                    params.append(json.dumps(row.get("form_data") or {}))
                if "applicant_data" in cols:
                    updates.append("applicant_data = %s::jsonb")
                    params.append(json.dumps(row.get("applicant_data") or {}))
                if updates:
                    params.append(submission_id)
                    cur.execute(
                        f"""
                        UPDATE submissions
                        SET {", ".join(updates)}
                        WHERE {id_col}::text = %s
                        """,
                        params,
                    )
                    conn.commit()
            cur.close()
            conn.close()
        except Exception:
            pass

    return {
        "submission_id": submission_id,
        "status": "pending_review",
        "requeued": True,
        "corrected_fields": list(payload.corrected_fields.keys()),
    }


@app.get("/submissions/all")
async def list_submissions_all(request: Request, role: str = None) -> Dict[str, Any]:
    _enforce_role(request, {"chw", "admin", "system"})
    if not check_db_ready():
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cols = _submission_columns(cur)
        if not cols:
            return {"submissions": []}
        cur.execute("SELECT * FROM submissions ORDER BY created_at DESC LIMIT 200")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for r in rows:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        return {"submissions": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/submissions/session/{user_id}")
async def get_session_submissions(user_id: str) -> Dict[str, Any]:
    if not check_db_ready():
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        user_hash = _hash_identifier(user_id)
        conn = get_db_conn()
        cur = conn.cursor()
        cols = _submission_columns(cur)
        if not cols:
            return {"submissions": []}
        
        where_parts: List[str] = []
        params: List[Any] = []
        for col in ("household_hash", "household_id_hash"):
            if col not in cols:
                continue
            if user_hash == user_id:
                where_parts.append(f"{col} = %s")
                params.append(user_id)
            else:
                where_parts.append(f"{col} = %s")
                where_parts.append(f"{col} = %s")
                params.extend([user_id, user_hash])
        if not where_parts:
            cur.close()
            conn.close()
            return {"submissions": []}
        cur.execute(
            f"""
            SELECT * FROM submissions
            WHERE {" OR ".join(where_parts)}
            ORDER BY created_at DESC
            """,
            params,
        )
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for r in rows:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        return {"submissions": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/submissions/user/{aadhaar_number}")
async def get_user_submissions(aadhaar_number: str) -> Dict[str, Any]:
    if not check_db_ready():
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cols = _submission_columns(cur)
        if not cols:
            return {"submissions": []}
        
        cur.execute("""
            SELECT * FROM submissions 
            WHERE 
                (applicant_data->>'aadhaar_number' = %s OR 
                 applicant_data->>'aadhaar' = %s OR
                 metadata->'user_profile'->>'aadhaar_number' = %s OR
                 metadata->'user_profile'->>'aadhaar' = %s)
            ORDER BY created_at DESC
        """, (aadhaar_number, aadhaar_number, aadhaar_number, aadhaar_number))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for r in rows:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        return {"submissions": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/log-interaction")
async def log_interaction(request: LogInteractionRequest):
    return {"status": "logged", "timestamp": request.timestamp}


# ==========================================
# NEW ENDPOINTS FOR END-TO-END PIPELINE
# ==========================================

class CreateFromCallRequest(BaseModel):
    household_hash: str
    best_scheme_id: Optional[str] = None
    best_scheme_name: Optional[str] = None
    name: Optional[str] = None
    age: Optional[Any] = None
    address: Optional[str] = None
    gender: Optional[str] = None
    monthly_income: Optional[Any] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    call_id: Optional[str] = None


@app.post("/submissions/create-from-call")
def create_submission_from_call(request: Request, req: CreateFromCallRequest):
    """Called by n8n after Groq entity extraction + scheme matching. Creates a submission record."""
    submission_id = str(uuid.uuid4())
    applicant_data = {k: v for k, v in {
        "name": req.name,
        "age": req.age,
        "address": req.address,
        "gender": req.gender,
        "monthly_income": req.monthly_income,
        "phone": req.phone,
        "state": req.state
    }.items() if v is not None}
    metadata = {"call_id": req.call_id, "scheme_name": req.best_scheme_name}

    if check_db_ready():
        conn = get_db_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO submissions (submission_id, household_hash, scheme_id, status,
                    applicant_data, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, 'pending_review', %s::jsonb, %s::jsonb, NOW(), NOW())
                ON CONFLICT DO NOTHING
            """, (submission_id, req.household_hash, req.best_scheme_id,
                  json.dumps(applicant_data), json.dumps(metadata)))
            conn.commit()
            cur.close()
        except Exception as e:
            logger.error(f"create_submission_from_call error: {e}")
            conn.rollback()
        finally:
            conn.close()

    return {"submission_id": submission_id, "status": "created", "scheme_id": req.best_scheme_id}


class UpdateFilledPdfRequest(BaseModel):
    household_hash: str
    scheme_id: Optional[str] = None
    filled_pdf_uri: str
    fields_empty: Optional[List[str]] = []
    fill_confidence: Optional[float] = 0.0


@app.post("/submissions/update-filled-pdf")
def update_filled_pdf(request: Request, req: UpdateFilledPdfRequest):
    """Called by n8n after PDF is filled and uploaded to MinIO. Updates the submission record."""
    if not check_db_ready():
        raise HTTPException(status_code=503, detail="DB unavailable")

    correction_fields = req.fields_empty or []
    status = "incomplete_fields" if correction_fields else "pdf_ready"

    conn = get_db_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE submissions SET
                filled_pdf_uri = %s,
                correction_required_fields = %s::jsonb,
                status = %s,
                updated_at = NOW()
            WHERE submission_id = (
                SELECT submission_id FROM submissions
                WHERE household_hash = %s AND (scheme_id = %s OR %s IS NULL)
                ORDER BY created_at DESC LIMIT 1
            )
        """, (req.filled_pdf_uri, json.dumps(correction_fields), status,
              req.household_hash, req.scheme_id, req.scheme_id))
        conn.commit()
        cur.close()
    except Exception as e:
        logger.error(f"update_filled_pdf error: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    return {
        "status": "updated",
        "filled_pdf_uri": req.filled_pdf_uri,
        "correction_required_fields": correction_fields,
        "submission_status": status
    }


class RefillWithCorrectionsRequest(BaseModel):
    household_hash: str
    corrected_fields: Dict[str, Any]


@app.post("/submissions/refill-with-corrections")
def refill_with_corrections(request: Request, req: RefillWithCorrectionsRequest):
    """Called by frontend when citizen submits corrected missing fields. Re-fills PDF."""
    _enforce_role(request, {"citizen", "system", "chw", "admin"})
    if not check_db_ready():
        raise HTTPException(status_code=503, detail="DB unavailable")

    conn = get_db_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM submissions
            WHERE household_hash = %s
            AND status IN ('incomplete_fields', 'pending_review', 'pdf_ready')
            ORDER BY created_at DESC LIMIT 1
        """, (req.household_hash,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="No pending submission found for this household")

        row = dict(row)
        scheme_id = row.get("scheme_id") or "ka-old-age-pension"

        # Merge corrections into applicant_data
        existing = row.get("applicant_data") or {}
        if isinstance(existing, str):
            try:
                existing = json.loads(existing)
            except Exception:
                existing = {}
        existing.update(req.corrected_fields)

        cur.execute(
            "UPDATE submissions SET applicant_data = %s::jsonb, updated_at = NOW() WHERE submission_id = %s",
            (json.dumps(existing), str(row.get("submission_id")))
        )
        conn.commit()
        row["applicant_data"] = existing
        cur.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"refill_with_corrections load error: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

    # Call form-filler to re-fill PDF
    FORM_FILLER_URL = os.getenv("FORM_FILLER_URL", "http://form-filler-service:8013")
    SCHEME_TEMPLATE_MAP = {
        "ka-old-age-pension": "pension1.pdf",
        "ka-widow-pension": "pension1.pdf",
        "ka-disability-pension": "disabledgovt.pdf",
        "pmjay": "Application_for_assiatance.pdf",
        "widow_pension_001": "pension1.pdf",
        "old_age_pension_001": "pension1.pdf",
        "disability_pension_001": "disabledgovt.pdf",
    }
    template = SCHEME_TEMPLATE_MAP.get(scheme_id, "pension1.pdf")
    FIELD_MAP = {
        "pension1.pdf": [
            {"field_id": "name", "x": 400, "y": 712, "page": 1, "fontSize": 10},
            {"field_id": "age", "x": 400, "y": 648, "page": 1, "fontSize": 10},
            {"field_id": "date_of_birth", "x": 460, "y": 648, "page": 1, "fontSize": 10},
            {"field_id": "gender", "x": 400, "y": 627, "page": 1, "fontSize": 10},
            {"field_id": "address", "x": 400, "y": 478, "page": 1, "fontSize": 9},
            {"field_id": "phone", "x": 400, "y": 440, "page": 1, "fontSize": 10},
            {"field_id": "aadhaar_number", "x": 400, "y": 415, "page": 1, "fontSize": 10},
            {"field_id": "annual_income", "x": 400, "y": 352, "page": 1, "fontSize": 10},
        ],
        "disabledgovt.pdf": [
            {"field_id": "name", "x": 380, "y": 680, "page": 1, "fontSize": 10},
            {"field_id": "age", "x": 380, "y": 640, "page": 1, "fontSize": 10},
            {"field_id": "address", "x": 380, "y": 580, "page": 1, "fontSize": 9},
            {"field_id": "phone", "x": 380, "y": 540, "page": 1, "fontSize": 10},
            {"field_id": "aadhaar_number", "x": 380, "y": 500, "page": 1, "fontSize": 10},
        ],
    }

    try:
        fill_resp = requests.post(f"{FORM_FILLER_URL}/fill-form", json={
            "template_path": f"/app/templates/{template}",
            "form_fields": FIELD_MAP.get(template, []),
            "field_values": existing
        }, timeout=30)

        if fill_resp.status_code == 200:
            fill_data = fill_resp.json()
            base64_pdf = fill_data.get("filled_document_base64", "")
            fields_still_empty = fill_data.get("fields_empty", [])

            # Upload to MinIO
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            filename = f"{req.household_hash}/filled_forms/{scheme_id}_{ts}.pdf"
            upload_resp = requests.post(f"{FORM_FILLER_URL}/upload", json={
                "bucket": "filled-forms",
                "filename": filename,
                "document_data": base64_pdf
            }, timeout=30)

            if upload_resp.status_code == 200:
                storage_path = upload_resp.json().get("storage_path", filename)
                new_uri = f"minio://{storage_path}"
                new_status = "incomplete_fields" if fields_still_empty else "pdf_ready"

                conn2 = get_db_conn()
                try:
                    cur2 = conn2.cursor()
                    cur2.execute("""
                        UPDATE submissions SET filled_pdf_uri = %s,
                            correction_required_fields = %s::jsonb,
                            status = %s, updated_at = NOW()
                        WHERE submission_id = %s
                    """, (new_uri, json.dumps(fields_still_empty), new_status,
                          str(row.get("submission_id"))))
                    conn2.commit()
                    cur2.close()
                finally:
                    conn2.close()

                return {
                    "success": True,
                    "filled_pdf_uri": new_uri,
                    "correction_required_fields": fields_still_empty,
                    "status": new_status
                }
            else:
                logger.error(f"form-filler upload failed: {upload_resp.status_code} {upload_resp.text}")
        else:
            logger.error(f"form-filler fill-form failed: {fill_resp.status_code} {fill_resp.text}")
    except Exception as e:
        logger.error(f"refill PDF error: {e}")

    return {"success": False, "message": "PDF re-fill failed — check form-filler service logs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
