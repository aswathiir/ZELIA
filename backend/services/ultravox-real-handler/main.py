"""
main.py — FastAPI app entry point for the Ultravox Real Handler service.
All business logic lives in the sibling modules:
  config.py, db.py, models.py, utils.py, storage.py, ws.py, ai.py, n8n.py
"""
import json
import logging
import uuid

import httpx
from fastapi import BackgroundTasks, Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import db
import n8n
import ws
from ai import extract_from_transcript
from config import (
    CORS_ALLOWED_ORIGINS,
    SCHEME_DISPLAY_NAMES,
    SCHEME_REQUIRED_FIELDS,
    SUBMISSION_SERVICE_URL,
    ULTRAVOX_AGENT_ID,
    ULTRAVOX_API_KEY,
    ULTRAVOX_API_URL,
    ULTRAVOX_STRICT,
    UNIVERSAL_REQUIRED_FIELDS,
)
from models import (
    CreateSessionRequest,
    EndSessionRequest,
    GetOrCreateHashRequest,
    InitiateCallRequest,
    SubmitMissingFieldsRequest,
    TriggerVerificationRequest,
    UpdateSessionRequest,
    WebhookPayload,
    WorkflowCompletePayload,
)
from storage import ensure_household_folders
from utils import (
    household_hash,
    normalize_required_documents,
    normalize_workflow_result,
    now_iso,
    safe_json_obj,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ultravox Real Handler", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await db.init_pool()


@app.on_event("shutdown")
async def shutdown():
    await db.close_pool()


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "ultravox-handler",
        "ultravox_strict": ULTRAVOX_STRICT,
        "websocket_clients": ws.connected_count(),
        "n8n_webhook_url": n8n.N8N_WEBHOOK_URL,
    }


# ─── Call Lifecycle ───────────────────────────────────────────────────────────

@app.post("/calls/initiate")
async def initiate_call(req: InitiateCallRequest, background_tasks: BackgroundTasks):
    """Initiate a live Ultravox call via the Ultravox REST API."""
    if not ULTRAVOX_API_KEY:
        raise HTTPException(500, "ULTRAVOX_API_KEY not configured")

    hh = household_hash(req.citizen_id, req.phone_number)
    ensure_household_folders(hh)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = (
                f"{ULTRAVOX_API_URL}/agents/{ULTRAVOX_AGENT_ID}/calls"
                if ULTRAVOX_AGENT_ID
                else f"{ULTRAVOX_API_URL}/calls"
            )
            payload = {
                "firstSpeakerSettings": {
                    "agent": {
                        "text": f"Hi {req.name}, I'm calling from Zelia government schemes assistant. How can I help you today?"
                    }
                },
                "metadata": {
                    "citizen_id": req.citizen_id,
                    "household_hash": hh,
                    "scheme_id": req.scheme_id or "general",
                    "customer_name": req.name,
                    "phone_number": req.phone_number,
                    "language_hint": "hi",
                },
            }
            if not ULTRAVOX_AGENT_ID:
                payload["systemPrompt"] = (
                    f"You are ZELIA, a helpful government assistant speaking with {req.name} "
                    f"about {req.reason}. Support Hindi and English. Respond in the user's language. "
                    "All extracted data and summaries MUST be in English."
                )

            resp = await client.post(
                url,
                headers={"X-API-Key": ULTRAVOX_API_KEY, "Content-Type": "application/json"},
                json=payload,
            )
            if resp.status_code not in {200, 201}:
                raise HTTPException(resp.status_code, f"Ultravox API error: {resp.text}")

            call_data = resp.json()
            call_id = call_data.get("callId") or call_data.get("id")
            join_url = call_data.get("joinUrl")
            if not call_id or not join_url:
                raise HTTPException(502, f"Ultravox response missing callId/joinUrl: {call_data}")

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error initiating call: {exc}")
        if ULTRAVOX_STRICT:
            raise HTTPException(502, f"Live call initiation failed: {exc}")
        call_id = f"fallback_{uuid.uuid4().hex[:8]}"
        join_url = f"wss://api.ultravox.ai/calls/{call_id}/join"

    pool = db.get_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO active_calls
                    (call_id, citizen_id, phone_number, status, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (call_id) DO UPDATE SET status = $4, updated_at = NOW()
                """,
                call_id, req.citizen_id, req.phone_number, "initiated",
                json.dumps({"name": req.name, "reason": req.reason,
                            "joinUrl": join_url, "household_hash": hh}),
            )

    await ws.broadcast("call_initiated", {
        "call_id": call_id, "citizen_id": req.citizen_id,
        "phone_number": req.phone_number, "household_hash": hh,
    })

    return {"success": True, "callId": call_id, "joinUrl": join_url,
            "status": "initiated", "household_hash": hh}


@app.get("/calls")
async def get_all_calls():
    pool = db.get_pool()
    if not pool:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM active_calls ORDER BY created_at DESC LIMIT 100")
        return [dict(r) for r in rows]


@app.get("/calls/{call_id}")
async def get_call(call_id: str):
    pool = db.get_pool()
    if not pool:
        raise HTTPException(500, "Database unavailable")
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM active_calls WHERE call_id = $1", call_id)
        if not row:
            raise HTTPException(404, "Call not found")
        return dict(row)


# ─── Session Management ───────────────────────────────────────────────────────

@app.post("/session/create")
async def create_session(req: CreateSessionRequest):
    hh = req.household_hash or household_hash(req.citizen_id or "unknown", req.phone_number)
    ensure_household_folders(hh)
    pool = db.get_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO active_calls (call_id, citizen_id, phone_number, status, metadata, created_at)
                VALUES ($1, $2, $3, 'active', $4::jsonb, NOW())
                ON CONFLICT (call_id) DO UPDATE
                SET phone_number = EXCLUDED.phone_number,
                    citizen_id   = EXCLUDED.citizen_id,
                    status       = 'active',
                    metadata     = COALESCE(active_calls.metadata, '{}'::jsonb) || EXCLUDED.metadata
                """,
                req.call_id, req.citizen_id, req.phone_number,
                json.dumps({"household_hash": hh}),
            )
    await ws.broadcast("call_active", {"call_id": req.call_id, "household_hash": hh})
    return {"status": "created", "call_id": req.call_id, "household_hash": hh}


@app.post("/session/update/{call_id}")
async def update_session(call_id: str, req: UpdateSessionRequest = Body(...)):
    pool = db.get_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE active_calls
                SET metadata = metadata::jsonb || $2::jsonb,
                    raw_transcript = CASE WHEN $3::text IS NOT NULL
                        THEN COALESCE(raw_transcript, '') || E'\\n' || $3::text
                        ELSE raw_transcript END,
                    updated_at = NOW()
                WHERE call_id = $1
                """,
                call_id, json.dumps(req.structured_data or {}), req.transcript,
            )
    await ws.broadcast("call_updated", {"call_id": call_id})
    return {"status": "updated"}


@app.post("/session/end/{call_id}")
async def end_session(call_id: str, req: EndSessionRequest = Body(...)):
    pool = db.get_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE active_calls
                SET status = 'completed', end_time = NOW(),
                    duration_secs = $2,
                    metadata = metadata::jsonb || jsonb_build_object('final_status', $3::text)
                WHERE call_id = $1
                """,
                call_id, req.duration or 0, req.status or "completed",
            )
    await ws.broadcast("call_ended", {"call_id": call_id, "status": req.status or "completed"})
    return {"status": "ended", "call_id": call_id}


@app.post("/session/get-or-create-hash")
async def get_or_create_hash(req: GetOrCreateHashRequest):
    hh = household_hash(req.citizen_id, req.phone_number)
    ensure_household_folders(hh)
    pool = db.get_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO households (household_id_hash, profile_json, last_updated_ts) "
                "VALUES ($1, $2::jsonb, NOW()) ON CONFLICT (household_id_hash) DO NOTHING",
                hh, json.dumps({"citizen_id": req.citizen_id, "phone_number": req.phone_number}),
            )
    return {"household_hash": hh, "citizen_id": req.citizen_id}


# ─── Webhooks ─────────────────────────────────────────────────────────────────

@app.post("/webhook/call-ended")
async def handle_call_ended(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """
    Primary webhook called by Ultravox when a call ends.
    Normalises the transcript, updates the DB, and triggers the N8N workflow.
    """
    try:
        call_id = payload.call_id

        # Normalise messages: strip blanks, unify field names
        messages = []
        for msg in (payload.messages or []):
            text = str(msg.get("text") or msg.get("content") or "").strip()
            if text:
                messages.append({"role": (msg.get("role") or "user").lower(), "text": text})

        hh = payload.household_hash
        meta_in = payload.metadata or {}
        if not hh:
            hh = meta_in.get("household_hash")

        pool = db.get_pool()
        if pool:
            async with pool.acquire() as conn:
                if not hh:
                    row = await conn.fetchrow(
                        "SELECT metadata FROM active_calls WHERE call_id = $1", call_id
                    )
                    if row:
                        hh = safe_json_obj(row["metadata"]).get("household_hash")

                await conn.execute(
                    """
                    UPDATE active_calls
                    SET status = 'ended', end_time = NOW(), duration_secs = $3,
                        metadata = COALESCE(metadata, '{}'::jsonb) || $2::jsonb
                    WHERE call_id = $1
                    """,
                    call_id,
                    json.dumps({"messages": messages, "duration_secs": payload.duration_secs,
                                "language": payload.language, "household_hash": hh}),
                    payload.duration_secs or 0,
                )

        await ws.broadcast("call_ended", {"call_id": call_id, "status": "ended"})

        # Trigger N8N — skip if process_now is explicitly False
        n8n_result = {"success": False, "reason": "processing_disabled"}
        if payload.process_now is not False:
            n8n_result = await n8n.trigger_workflow(
                "document_processing",
                {
                    "call_id": call_id,
                    "phone_number": payload.customer_number,
                    "household_hash": hh,
                    "duration": payload.duration_secs or 0,
                    "language": payload.language or "auto",
                    "metadata": meta_in,
                    "messages": messages,
                },
            )

        workflow_json = n8n_result.get("response_json") or {}
        result = normalize_workflow_result(workflow_json)
        if hh and not result.get("household_hash"):
            result["household_hash"] = hh
        if workflow_json:
            result["raw_workflow"] = workflow_json
        if not n8n_result.get("success"):
            result["status"] = "processing_error"
            errs = n8n_result.get("errors") or []
            result["response_text"] = (
                errs[0] if errs
                else "Workflow unavailable. Activate the N8N webhook and retry."
            )
            result["next_action"] = "activate_workflow_and_retry"

        # Persist latest outcome
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        UPDATE active_calls
                        SET metadata = COALESCE(metadata, '{}'::jsonb) || $2::jsonb,
                            updated_at = NOW()
                        WHERE call_id = $1
                        """,
                        call_id,
                        json.dumps({
                            "last_result_status": result.get("status"),
                            "best_match_scheme":  result.get("best_match_scheme"),
                            "response_text":      result.get("response_text"),
                            "next_action":        result.get("next_action"),
                        }),
                    )
            except Exception as exc:
                logger.warning(f"Could not persist call result metadata: {exc}")

        return {"success": True, "call_id": call_id, "household_hash": hh,
                "n8n": n8n_result, "result": result}

    except Exception as exc:
        logger.error(f"Error handling call-ended webhook: {exc}")
        return {"success": False, "error": str(exc)}


@app.post("/webhook/workflow-complete")
async def workflow_complete(payload: WorkflowCompletePayload):
    """Receives completion notification from N8N; broadcasts to WebSocket clients."""
    event_data = {
        "household_hash": payload.household_hash,
        "status":         payload.status,
        "filled_pdf_uri": payload.filled_pdf_uri,
        "fields_empty":   payload.fields_empty or [],
        "best_scheme":    payload.best_scheme or {},
    }
    await ws.broadcast("workflow_complete", event_data)

    pool = db.get_pool()
    if pool:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE active_calls
                    SET metadata = COALESCE(metadata, '{}'::jsonb) ||
                        jsonb_build_object(
                            'workflow_status', $2,
                            'filled_pdf_uri',  $3,
                            'fields_empty',    $4::jsonb,
                            'best_match_scheme', $5::jsonb
                        ),
                        updated_at = NOW()
                    WHERE metadata->>'household_hash' = $1 OR citizen_id = $1
                    """,
                    payload.household_hash, payload.status, payload.filled_pdf_uri,
                    json.dumps(payload.fields_empty or []),
                    json.dumps(payload.best_scheme or {}),
                )
        except Exception as exc:
            logger.warning(f"workflow_complete DB update failed (non-fatal): {exc}")

    return {"received": True, "household_hash": payload.household_hash}


# ─── Household & Document Endpoints ──────────────────────────────────────────

@app.get("/households/{hh}")
async def get_household_profile(hh: str):
    pool = db.get_pool()
    if not pool:
        return {"success": False, "error": "Database unavailable"}
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT profile_json FROM households WHERE household_id_hash = $1", hh
            )
            if not row:
                return {"success": False, "error": "Household not found"}
            profile = safe_json_obj(row["profile_json"])
            return {"success": True, "profile": profile,
                    "suggestions": profile.get("suggested_schemes", [])}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@app.get("/households/{hh}/workflow-status")
async def get_household_workflow_status(hh: str):
    pool = db.get_pool()
    if not pool:
        return {"success": False, "error": "Database unavailable"}

    try:
        output = {
            "success": True, "household_hash": hh, "status": "unknown",
            "response_text": None, "best_match_scheme": {},
            "required_documents": [], "missing_required_documents": [],
            "next_action": "await_processing", "latest_call": None,
            "latest_submission": None, "filled_forms": [],
        }

        async with pool.acquire() as conn:
            call_row = await conn.fetchrow(
                """
                SELECT call_id, status, metadata, created_at, updated_at
                FROM active_calls
                WHERE metadata->>'household_hash' = $1
                ORDER BY COALESCE(updated_at, created_at) DESC LIMIT 1
                """,
                hh,
            )
            if call_row:
                meta = safe_json_obj(call_row["metadata"])
                best = safe_json_obj(meta.get("best_match_scheme"))
                output["latest_call"] = {
                    "call_id": call_row["call_id"], "status": call_row["status"],
                    "created_at": str(call_row["created_at"]) if call_row["created_at"] else None,
                }
                output["status"]                       = meta.get("last_result_status") or output["status"]
                output["response_text"]                = meta.get("response_text")
                output["best_match_scheme"]            = best
                output["required_documents"]           = normalize_required_documents(meta.get("required_documents"))
                output["missing_required_documents"]   = normalize_required_documents(meta.get("missing_required_documents"))
                output["next_action"]                  = meta.get("next_action") or output["next_action"]

            sub_rows = await conn.fetch(
                """
                SELECT submission_id, scheme_id, status, filled_pdf_uri, created_at
                FROM submissions WHERE household_hash = $1
                ORDER BY created_at DESC LIMIT 10
                """,
                hh,
            )
            if sub_rows:
                latest = dict(sub_rows[0])
                output["latest_submission"] = {
                    "submission_id": latest["submission_id"],
                    "scheme_id":     latest["scheme_id"],
                    "status":        latest["status"],
                    "filled_pdf_uri": latest["filled_pdf_uri"],
                }
                filled = [
                    {"submission_id": r["submission_id"], "scheme_id": r["scheme_id"],
                     "status": r["status"], "filled_pdf_uri": str(r["filled_pdf_uri"])}
                    for r in sub_rows
                    if r["filled_pdf_uri"] and ".pdf" in str(r["filled_pdf_uri"]).lower()
                ]
                output["filled_forms"] = filled
                if output["status"] in {"unknown", "processed"}:
                    output["status"]      = "form_ready"       if filled else "documents_pending"
                    output["next_action"] = "review_filled_form" if filled else "upload_missing_documents"

        return output
    except Exception as exc:
        logger.error(f"Error fetching workflow status for {hh}: {exc}")
        return {"success": False, "error": str(exc)}


@app.post("/submit-missing-fields")
async def submit_missing_fields(req: SubmitMissingFieldsRequest):
    pool = db.get_pool()
    if not pool:
        raise HTTPException(500, "Database unavailable")
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT submission_id, applicant_data FROM submissions
                WHERE household_hash = $1 AND status = 'pending_review'
                ORDER BY created_at DESC LIMIT 1
                """,
                req.household_hash,
            )
            if not row:
                raise HTTPException(404, "No pending submission found to update")
            current = safe_json_obj(row["applicant_data"])
            current.update(req.corrected_fields)
            await conn.execute(
                "UPDATE submissions SET applicant_data = $1::jsonb WHERE submission_id = $2",
                json.dumps(current), row["submission_id"],
            )
            return {"success": True, "message": "Missing fields updated successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"submit_missing_fields error: {exc}")
        return {"success": False, "error": str(exc)}


@app.post("/trigger-verification")
async def trigger_verification(req: TriggerVerificationRequest, background_tasks: BackgroundTasks):
    """
    Manually trigger document verification + N8N workflow for a household.
    Used by the frontend after a citizen uploads their documents.
    """
    try:
        hh = req.household_hash
        pool = db.get_pool()

        # ── Step 1: Validate latest pending submission ──
        scheme_id = None
        if pool:
            async with pool.acquire() as conn:
                target = await conn.fetchrow(
                    """
                    SELECT submission_id, scheme_id FROM submissions
                    WHERE household_hash = $1 AND scheme_id IS NOT NULL
                      AND COALESCE(status,'pending') NOT IN ('approved','accepted','verified')
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    hh,
                )
            if target:
                scheme_id = target["scheme_id"]
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        vresp = await client.post(
                            f"{SUBMISSION_SERVICE_URL}/submissions/{target['submission_id']}/validate-documents",
                            headers={"x-user-role": "system", "x-user-id": "ultravox-handler"},
                            json={"auto_correct_form": True},
                        )
                    if vresp.status_code == 200:
                        report = vresp.json()
                        missing = set()
                        for f in report.get("missing_required_documents") or []:
                            missing.add(str(f))
                        for m in report.get("mismatched_fields") or []:
                            field = str((m or {}).get("field") or "").strip()
                            if field and field not in {"scheme_rule", "aadhaar_qr_signature"}:
                                missing.add(field)
                        if not report.get("submission_allowed", False):
                            return {
                                "success": False, "status": "incomplete",
                                "missing_fields": sorted(missing),
                                "missing_required_documents": report.get("missing_required_documents", []),
                                "message": "Document verification found missing or mismatched fields.",
                            }
                except Exception as exc:
                    logger.warning(f"Submission validation call failed: {exc}")

        # ── Step 2: Gather aggregated applicant data from transcript + OCR ──
        transcript_data = {}
        call_data = None
        if pool:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT call_id, metadata FROM active_calls "
                    "WHERE metadata->>'household_hash' = $1 ORDER BY created_at DESC LIMIT 1",
                    hh,
                )
                if row:
                    call_data = dict(row)
                    messages = safe_json_obj(call_data["metadata"]).get("messages", [])
                    if messages:
                        transcript_data = await extract_from_transcript(messages)

        aggregated = {**transcript_data}
        if pool:
            async with pool.acquire() as conn:
                docs = await conn.fetch(
                    "SELECT applicant_data, scheme_id FROM submissions "
                    "WHERE household_hash = $1 AND status = 'pending_review' ORDER BY created_at DESC",
                    hh,
                )
                for doc in docs:
                    if not scheme_id and doc.get("scheme_id"):
                        scheme_id = doc["scheme_id"]
                    if doc.get("applicant_data"):
                        data = safe_json_obj(doc["applicant_data"])
                        aggregated.update({k.lower(): v for k, v in data.items() if v})

        # ── Step 3: Check for missing fields ──
        missing = [f for f in UNIVERSAL_REQUIRED_FIELDS if f not in aggregated]
        if not any(k in aggregated for k in ["age", "dob", "date_of_birth"]):
            missing.append("age")
        for f in SCHEME_REQUIRED_FIELDS.get(scheme_id or "", []):
            if f not in aggregated:
                missing.append(f)

        if missing:
            return {"success": False, "status": "incomplete",
                    "missing_fields": missing,
                    "message": f"Missing fields for {scheme_id or 'application'}"}

        # ── Step 4: Build enriched transcript and trigger N8N ──
        if call_data:
            meta = safe_json_obj(call_data["metadata"])
            call_id    = call_data["call_id"]
            phone      = meta.get("phone_number", "unknown")
            duration   = meta.get("duration_secs", 0)
            raw_msgs   = meta.get("messages", [])
        else:
            call_id, phone, duration, raw_msgs = f"no-call-{hh[:8]}", "unknown", 0, []

        name = aggregated.get("name", "Applicant")
        human_scheme = SCHEME_DISPLAY_NAMES.get(scheme_id or "", scheme_id or "government")
        summary = (
            f"My name is {name}. "
            + (f"I am {aggregated.get('age') or aggregated.get('dob')} years old. " if aggregated.get("age") or aggregated.get("dob") else "")
            + (f"I live at {aggregated['address']}. " if aggregated.get("address") else "")
            + (f"My monthly income is {aggregated.get('monthly_income')} rupees. " if aggregated.get("monthly_income") else "")
            + f"I want to apply for the {human_scheme} scheme."
        )
        combined_messages = [{"role": "system_summary", "text": summary}] + raw_msgs

        background_tasks.add_task(
            n8n.trigger_workflow,
            "document_processing",
            {"call_id": call_id, "phone_number": phone, "household_hash": hh,
             "duration": duration, "messages": combined_messages},
        )
        return {"success": True, "status": "validated",
                "scheme_id": scheme_id,
                "message": "Verification triggered. You may now proceed to the Voice Interview."}

    except Exception as exc:
        logger.error(f"trigger_verification error: {exc}")
        return {"success": False, "error": str(exc)}


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/calls")
async def ws_calls(websocket: WebSocket):
    await ws.register(websocket)
    try:
        await websocket.send_json({
            "event": "connected",
            "payload": {"service": "ultravox-handler"},
            "ts": now_iso(),
        })
        while True:
            await websocket.receive_text()  # keep-alive; client may send pings
    except WebSocketDisconnect:
        pass
    finally:
        ws.deregister(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
