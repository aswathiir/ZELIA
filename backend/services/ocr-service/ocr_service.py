"""
ZELIA OCR Service — v2
CNN-based text extraction from uploaded documents using EasyOCR.
Structured field extraction for Indian government ID documents.
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import io
import os
import uuid
import time
import hashlib
import logging
import uvicorn

import easyocr
from PIL import Image
import numpy as np
import boto3
from botocore.client import Config

from document_parsers import parse_document, ExtractionResult, PARSER_REGISTRY
from document_classifier import classify_document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ocr-service")

app = FastAPI(
    title="ZELIA OCR Service",
    description="CNN-based document OCR with structured field extraction",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin_secure_2024")
DOCUMENTS_BUCKET = os.getenv("DOCUMENTS_BUCKET", "user-documents")
DB_URL = os.getenv("DATABASE_URL", "")

s3_client = boto3.client(
    "s3",
    endpoint_url=f"http://{MINIO_ENDPOINT}",
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4"),
)

# ---------------------------------------------------------------------------
# EasyOCR readers (per-language group – Tamil/Kannada need separate instances)
# ---------------------------------------------------------------------------
_readers: Dict[str, easyocr.Reader] = {}

# EasyOCR groups: languages that share compatible script models
_LANG_GROUPS = {
    "en": ["en"],
    "hi": ["en", "hi"],
    "ta": ["en", "ta"],
    "kn": ["en", "kn"],
}


def get_reader(lang: str = "en") -> easyocr.Reader:
    group_key = lang if lang in _LANG_GROUPS else "en"
    if group_key not in _readers:
        langs = _LANG_GROUPS[group_key]
        logger.info("Initialising EasyOCR reader for %s …", langs)
        _readers[group_key] = easyocr.Reader(
            langs,
            gpu=False,
            model_storage_directory="/tmp/easyocr_models",
        )
        logger.info("EasyOCR reader ready for %s.", langs)
    return _readers[group_key]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class OCRBlock(BaseModel):
    block_id: str
    text: str
    confidence: float
    bbox: List[float]
    page: int
    language: str


class OCRRequest(BaseModel):
    file_url: str
    language: str = "en"
    enhance: bool = True


class OCRResponse(BaseModel):
    file_id: str
    total_blocks: int
    total_pages: int
    blocks: List[OCRBlock]
    processing_time: float


class DocumentExtractionRequest(BaseModel):
    household_hash: str
    document_type: str = "auto"  # or aadhaar, pan, voter_id, etc.
    image_uri: Optional[str] = None
    image_base64: Optional[str] = None
    language: str = "en"


class DocumentExtractionResponse(BaseModel):
    document_id: str
    document_type: str
    classification_confidence: float
    extracted_fields: Dict[str, Optional[str]]
    extraction_confidence: float
    parser_warnings: List[str]
    stored: bool
    storage_path: Optional[str]
    processing_time: float


# ---------------------------------------------------------------------------
# Helper: ensure bucket exists
# ---------------------------------------------------------------------------
def ensure_bucket(bucket: str):
    try:
        s3_client.head_bucket(Bucket=bucket)
    except Exception:
        try:
            s3_client.create_bucket(Bucket=bucket)
            logger.info("Created bucket %s", bucket)
        except Exception as exc:
            logger.warning("Bucket %s may already exist: %s", bucket, exc)


# ---------------------------------------------------------------------------
# Helper: image → EasyOCR text
# ---------------------------------------------------------------------------
def ocr_image(image: Image.Image, lang: str = "en") -> List[dict]:
    """Run EasyOCR on a PIL image and return blocks."""
    reader = get_reader(lang)
    arr = np.array(image)
    results = reader.readtext(arr, detail=1)  # [(bbox, text, conf), …]

    blocks = []
    for bbox_pts, text, conf in results:
        # bbox_pts is [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        xs = [p[0] for p in bbox_pts]
        ys = [p[1] for p in bbox_pts]
        blocks.append({
            "text": text,
            "confidence": float(conf),
            "bbox": [min(xs), min(ys), max(xs), max(ys)],
        })
    return blocks


def blocks_to_text(blocks: List[dict]) -> str:
    """Merge blocks into a single string preserving approximate line order."""
    # Sort by y then x
    sorted_blocks = sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
    lines: List[str] = []
    prev_y = -999
    for b in sorted_blocks:
        y = b["bbox"][1]
        if abs(y - prev_y) > 15:
            lines.append(b["text"])
        else:
            lines[-1] += " " + b["text"]
        prev_y = y
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helper: load image from various sources
# ---------------------------------------------------------------------------
def load_image_from_uri(uri: str) -> Image.Image:
    """Load image from MinIO s3:// or http:// URI."""
    if uri.startswith("s3://"):
        parts = uri.replace("s3://", "").split("/", 1)
        bucket, key = parts[0], parts[1]
    elif "://" in uri:
        path = uri.split("://", 1)[1].split("/", 1)[1]
        parts = path.split("/", 1)
        bucket, key = parts[0], parts[1]
    else:
        bucket, key = DOCUMENTS_BUCKET, uri

    resp = s3_client.get_object(Bucket=bucket, Key=key)
    return Image.open(io.BytesIO(resp["Body"].read()))


def load_image_from_base64(b64: str) -> Image.Image:
    import base64
    data = base64.b64decode(b64)
    return Image.open(io.BytesIO(data))


# ---------------------------------------------------------------------------
# Database helpers (direct psycopg2 — lightweight, no ORM)
# ---------------------------------------------------------------------------
def get_db_conn():
    """Return a psycopg2 connection or None if DB_URL is not set."""
    if not DB_URL:
        return None
    try:
        import psycopg2
        return psycopg2.connect(DB_URL)
    except Exception as exc:
        logger.warning("DB connection failed: %s", exc)
        return None


def store_document_record(
    household_hash: str,
    document_type: str,
    raw_image_uri: str,
    extracted_json: dict,
    confidence: float,
) -> Optional[str]:
    """Insert into document_store; return document_id or None."""
    conn = get_db_conn()
    if conn is None:
        return None
    try:
        import json as _json
        hash_sig = hashlib.sha256(
            f"{household_hash}:{document_type}:{raw_image_uri}".encode()
        ).hexdigest()

        cur = conn.cursor()
        cur.execute(
            """INSERT INTO document_store
               (household_id_hash, document_type, raw_image_uri,
                extracted_json, verification_status, hash_signature)
               VALUES (%s, %s, %s, %s, 'extracted', %s)
               ON CONFLICT (hash_signature) DO UPDATE
                 SET extracted_json = EXCLUDED.extracted_json,
                     verification_status = 'extracted',
                     updated_at = NOW()
               RETURNING document_id::text""",
            (household_hash, document_type, raw_image_uri,
             _json.dumps(extracted_json), hash_sig),
        )
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None
    except Exception as exc:
        logger.error("DB store failed: %s", exc)
        conn.rollback()
        return None
    finally:
        conn.close()


def get_household_documents(household_hash: str) -> List[dict]:
    """Retrieve all extracted documents for a household."""
    conn = get_db_conn()
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT document_id::text, document_type, extracted_json,
                      verification_status, created_at::text
               FROM document_store
               WHERE household_id_hash = %s
               ORDER BY created_at DESC""",
            (household_hash,),
        )
        rows = cur.fetchall()
        return [
            {
                "document_id": r[0],
                "document_type": r[1],
                "extracted_json": r[2],
                "verification_status": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error("DB read failed: %s", exc)
        return []
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "OCR Service v2 (EasyOCR)",
        "supported_document_types": list(PARSER_REGISTRY.keys()),
        "supported_languages": ["en", "hi", "ta", "kn"],
    }


# --- Legacy /extract endpoint (backward-compatible) -----------------------
@app.post("/extract", response_model=OCRResponse)
async def extract_text(request: OCRRequest):
    """Extract raw text blocks from a document (PDF or image)."""
    start = time.time()
    try:
        image = load_image_from_uri(request.file_url)
        blocks = ocr_image(image, request.language)

        ocr_blocks = [
            OCRBlock(
                block_id=f"b{i}",
                text=b["text"],
                confidence=b["confidence"],
                bbox=b["bbox"],
                page=1,
                language=request.language,
            )
            for i, b in enumerate(blocks)
        ]

        return OCRResponse(
            file_id=request.file_url,
            total_blocks=len(ocr_blocks),
            total_pages=1,
            blocks=ocr_blocks,
            processing_time=round(time.time() - start, 2),
        )
    except Exception as exc:
        raise HTTPException(500, f"OCR extraction failed: {exc}")


# --- New /extract-document endpoint (structured extraction) ----------------
@app.post("/extract-document", response_model=DocumentExtractionResponse)
async def extract_document(req: DocumentExtractionRequest):
    """
    Extract structured fields from an Indian ID document image.

    1. Load image (from URI or base64)
    2. Run EasyOCR → raw text
    3. Auto-detect document type (or use provided type)
    4. Run document-specific parser → structured fields
    5. Store in MinIO + PostgreSQL
    """
    start = time.time()

    # 1. Load image ----------------------------------------------------------
    if req.image_base64:
        image = load_image_from_base64(req.image_base64)
    elif req.image_uri:
        image = load_image_from_uri(req.image_uri)
    else:
        raise HTTPException(400, "Provide either image_uri or image_base64")

    # 2. OCR -----------------------------------------------------------------
    blocks = ocr_image(image, req.language)
    raw_text = blocks_to_text(blocks)
    logger.info("OCR extracted %d blocks, %d chars", len(blocks), len(raw_text))

    # 3. Classify ------------------------------------------------------------
    if req.document_type == "auto":
        doc_type, cls_conf = classify_document(raw_text)
        if doc_type == "unknown":
            raise HTTPException(
                422,
                "Could not auto-detect document type. "
                "Please specify document_type explicitly.",
            )
    else:
        doc_type = req.document_type
        cls_conf = 1.0

    if doc_type not in PARSER_REGISTRY:
        raise HTTPException(
            400,
            f"Unsupported document type '{doc_type}'. "
            f"Supported: {list(PARSER_REGISTRY.keys())}",
        )

    # 4. Parse ---------------------------------------------------------------
    result: ExtractionResult = parse_document(doc_type, raw_text)

    # 5. Store image in MinIO ------------------------------------------------
    storage_path = None
    stored = False
    try:
        ensure_bucket(DOCUMENTS_BUCKET)
        ts = int(time.time())
        ext = "jpg"
        object_key = f"{req.household_hash}/{doc_type}_{ts}.{ext}"

        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)

        s3_client.put_object(
            Bucket=DOCUMENTS_BUCKET,
            Key=object_key,
            Body=buf.read(),
            ContentType="image/jpeg",
        )
        storage_path = f"s3://{DOCUMENTS_BUCKET}/{object_key}"
        stored = True
    except Exception as exc:
        logger.warning("MinIO upload failed: %s", exc)

    # 6. Store extraction in DB ----------------------------------------------
    doc_id = store_document_record(
        household_hash=req.household_hash,
        document_type=doc_type,
        raw_image_uri=storage_path or "in-memory",
        extracted_json={
            "fields": result.fields,
            "confidence": result.confidence,
            "raw_text_length": len(raw_text),
        },
        confidence=result.confidence,
    )
    if doc_id is None:
        doc_id = str(uuid.uuid4())

    return DocumentExtractionResponse(
        document_id=doc_id,
        document_type=doc_type,
        classification_confidence=cls_conf,
        extracted_fields=result.fields,
        extraction_confidence=result.confidence,
        parser_warnings=result.parser_warnings,
        stored=stored,
        storage_path=storage_path,
        processing_time=round(time.time() - start, 2),
    )


# --- Upload + extract (multipart) -----------------------------------------
@app.post("/upload-and-extract")
async def upload_and_extract(
    file: UploadFile = File(...),
    household_hash: str = Form("unknown"),
    document_type: str = Form("auto"),
    language: str = Form("en"),
):
    """Upload a document image and extract structured fields in one step."""
    import base64

    file_bytes = await file.read()
    b64 = base64.b64encode(file_bytes).decode()

    req = DocumentExtractionRequest(
        household_hash=household_hash,
        document_type=document_type,
        image_base64=b64,
        language=language,
    )
    return await extract_document(req)


# --- Household document query ----------------------------------------------
@app.get("/household/{household_hash}/documents")
async def get_documents(household_hash: str):
    """Retrieve all OCR-extracted documents for a household."""
    docs = get_household_documents(household_hash)
    return {
        "household_hash": household_hash,
        "total_documents": len(docs),
        "documents": docs,
    }


# ---------------------------------------------------------------------------
# Mount verification router
# ---------------------------------------------------------------------------
from document_verification import router as verification_router, set_document_fetcher

set_document_fetcher(get_household_documents)
app.include_router(verification_router)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)