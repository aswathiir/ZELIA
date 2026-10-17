from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import json
import asyncpg
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging
from datetime import datetime
import uuid
import base64

try:
    from minio import Minio
except Exception:  # pragma: no cover
    Minio = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Document Processor", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
DB_URL = os.getenv("DATABASE_URL")
OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://ocr-service:8003")
LAYOUT_WORKER_URL = os.getenv("LAYOUT_WORKER_URL", "http://layout-worker:8006")
RETRIEVAL_SERVICE_URL = os.getenv("RETRIEVAL_SERVICE_URL", "http://retrieval-service:8007")
RULES_ENGINE_URL = os.getenv("RULES_ENGINE_URL", "http://rules-engine:8005")

# MinIO for verified docs
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "verified-docs")

_db_pool: Optional[asyncpg.pool.Pool] = None
_minio = None


class DocumentProcessRequest(BaseModel):
    call_id: Optional[str] = None
    phone_number: Optional[str] = None
    document_type: str
    document_url: str
    citizen_id: Optional[str] = None
    scheme_id: Optional[str] = None
    image_base64: Optional[str] = None


async def get_submission_columns(conn) -> List[str]:
    rows = await conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'submissions'
        """
    )
    return [r["column_name"] for r in rows]


def _status_from_eligibility(result: Dict[str, Any]) -> str:
    if result.get("eligible") is True:
        return "pending_review"
    if result.get("eligible") is False:
        return "pending_review"
    return "pending_review"


async def persist_submission(conn, payload: Dict[str, Any]) -> str:
    cols = await get_submission_columns(conn)
    if not cols:
        raise RuntimeError("submissions table not found")

    insertable: Dict[str, Any] = {}
    for key, val in payload.items():
        if key in cols:
            insertable[key] = val

    if not insertable:
        raise RuntimeError("no compatible submissions columns found")

    keys = list(insertable.keys())
    placeholders = [f"${i}" for i in range(1, len(keys) + 1)]
    values = [insertable[k] for k in keys]

    returning_col = "submission_id" if "submission_id" in cols else ("id" if "id" in cols else None)

    sql = f"INSERT INTO submissions ({', '.join(keys)}) VALUES ({', '.join(placeholders)})"
    if returning_col:
        sql += f" RETURNING {returning_col}"
        rec = await conn.fetchrow(sql, *values)
        return str(rec[returning_col])

    await conn.execute(sql, *values)
    return str(payload.get("call_id") or payload.get("document_id") or uuid.uuid4())


def get_minio_client():
    global _minio
    if _minio is not None:
        return _minio
    if Minio is None:
        return None
    try:
        _minio = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE,
        )
        if not _minio.bucket_exists(MINIO_BUCKET):
            _minio.make_bucket(MINIO_BUCKET)
        return _minio
    except Exception as e:
        logger.warning(f"MinIO unavailable: {e}")
        return None


@app.on_event("startup")
async def startup():
    global _db_pool
    if DB_URL:
        _db_pool = await asyncpg.create_pool(DB_URL, min_size=2, max_size=10)
        logger.info("Database pool created")


@app.on_event("shutdown")
async def shutdown():
    global _db_pool
    if _db_pool:
        await _db_pool.close()


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "document-processor",
        "db_ready": _db_pool is not None,
        "minio_ready": get_minio_client() is not None,
    }


async def call_ocr(document_url: str) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{OCR_SERVICE_URL}/extract", json={"document_url": document_url})
        if resp.status_code != 200:
            logger.warning(f"OCR failed: {resp.text}")
            return ""
        data = resp.json()
        return data.get("text", "")


async def call_layout(document_id: str, document_type: str, text: str, document_url: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{LAYOUT_WORKER_URL}/extract-document",
            json={
                "document_id": document_id,
                "document_type": document_type,
                "text": text,
                "document_url": document_url,
            },
        )
        if resp.status_code != 200:
            logger.warning(f"Layout worker failed: {resp.text}")
            return {}
        return resp.json().get("extracted_data", {})


async def call_embed(text: str, document_id: str, metadata: Dict[str, Any]):
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{RETRIEVAL_SERVICE_URL}/embed",
            json={"text": text, "document_id": document_id, "metadata": metadata},
        )
        if resp.status_code != 200:
            logger.warning(f"Embedding failed: {resp.text}")


async def call_rules(scheme_id: Optional[str], extracted_data: Dict[str, Any], document_type: str) -> Dict[str, Any]:
    if not scheme_id:
        return {"eligible": None, "message": "Scheme id missing", "confidence": 0.0}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{RULES_ENGINE_URL}/check-eligibility",
            json={"scheme_id": scheme_id, "extracted_data": extracted_data, "document_type": document_type},
        )
        if resp.status_code != 200:
            logger.warning(f"Rules check failed: {resp.text}")
            return {"eligible": None, "message": "Manual review needed", "confidence": 0.0}
        return resp.json()


@app.post("/documents/process")
async def process_document(request: DocumentProcessRequest, background_tasks: BackgroundTasks):
    try:
        structured_data = {}
        extracted_text = ""
        document_id = str(uuid.uuid4())
        
        if request.image_base64:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{OCR_SERVICE_URL}/extract-document",
                    json={
                        "household_hash": request.citizen_id or "unknown",
                        "document_type": "auto",
                        "image_base64": request.image_base64,
                        "language": "en"
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    structured_data = data.get("extracted_fields", {})
                    extracted_text = " ".join([str(v) for v in structured_data.values() if v])
                else:
                    logger.warning(f"Structured OCR failed: {resp.text}")

        await call_embed(
            extracted_text,
            document_id,
            {
                "document_type": request.document_type,
                "call_id": request.call_id,
                "citizen_id": request.citizen_id,
                "scheme_id": request.scheme_id,
            },
        )

        eligibility_result = await call_rules(request.scheme_id, structured_data, request.document_type)

        submission_status = _status_from_eligibility(eligibility_result)
        submission_id = "simulated_id"

        if _db_pool:
            async with _db_pool.acquire() as conn:
                payload = {
                    "call_id": request.call_id or f"doc_{document_id}",
                    "household_hash": request.citizen_id,
                    "household_id_hash": request.citizen_id,
                    "citizen_id": None,
                    "scheme_id": request.scheme_id,
                    "schemes_applied": [request.scheme_id] if request.scheme_id else [],
                    "status": submission_status,
                    "applicant_data": json.dumps(structured_data),
                    "form_data": json.dumps({
                        "document_type": request.document_type,
                        "eligibility": eligibility_result,
                        "document_reference": document_id,
                    }),
                    "eligibility": json.dumps(eligibility_result),
                    "document_reference": document_id,
                    "document_id": document_id,
                    "document_type": request.document_type,
                    "storage_path": request.document_url,
                    "pdf_url": request.document_url,
                    "filled_pdf_uri": request.document_url,
                    "verified_documents_uri": json.dumps([request.document_url]),
                    "confidence": float(eligibility_result.get("confidence", 0.0) or 0.0),
                    "review_notes": None,
                    "reviewer_id": None,
                    "reviewed_at": None,
                    "verification_checklist": json.dumps({}),
                    "audit_log": json.dumps([{"event": "document_processed", "at": datetime.utcnow().isoformat()}]),
                    "timestamps": json.dumps({"created_at": datetime.utcnow().isoformat()}),
                    "created_at": datetime.utcnow(),
                }

                submission_id = await persist_submission(conn, payload)

                try:
                    await conn.execute(
                        """
                        INSERT INTO audit_ledger (event_type, entity_type, entity_id, payload)
                        VALUES ($1, $2, $3, $4::jsonb)
                        """,
                        "document_processed",
                        "submission",
                        submission_id,
                        json.dumps(
                            {
                                "call_id": request.call_id,
                                "document_type": request.document_type,
                                "eligibility": eligibility_result,
                            }
                        ),
                    )
                except Exception:
                    # audit table may not exist in some environments
                    pass

        return {
            "success": True,
            "submission_id": submission_id,
            "document_id": document_id,
            "extracted_data": structured_data,
            "eligibility": eligibility_result,
            "status": submission_status,
        }

    except Exception as e:
        logger.error(f"Document processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    citizen_id: str = Form(None),
    scheme_id: str = Form(None),
    call_id: str = Form(None),
):
    try:
        document_id = str(uuid.uuid4())
        content = await file.read()

        doc_url = f"local://{document_id}/{file.filename}"
        minio = get_minio_client()
        if minio:
            obj = f"{citizen_id or 'anon'}/{document_id}/{file.filename}"
            import io

            minio.put_object(
                MINIO_BUCKET,
                obj,
                io.BytesIO(content),
                length=len(content),
                content_type=file.content_type or "application/octet-stream",
            )
            doc_url = f"minio://{MINIO_BUCKET}/{obj}"

        result = await process_document(
            DocumentProcessRequest(
                call_id=call_id,
                phone_number="",
                document_type="auto",
                document_url=doc_url,
                citizen_id=citizen_id,
                scheme_id=scheme_id,
                image_base64=base64.b64encode(content).decode()
            ),
            BackgroundTasks(),
        )

        return {
            "success": True,
            "document_id": document_id,
            "document_url": doc_url,
            "processing": result,
        }

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
