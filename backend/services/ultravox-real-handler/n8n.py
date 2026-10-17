"""
n8n.py — N8N workflow trigger logic.

Encapsulates all communication with the N8N automation platform.
Handles dynamic webhook path resolution (from DB), fallback URL strategies,
and error propagation.
"""
import logging
from typing import Any, Dict
from urllib.parse import quote

import httpx

from config import N8N_WEBHOOK_URL
from db import get_pool
from utils import now_iso

logger = logging.getLogger(__name__)


async def trigger_workflow(workflow_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a workflow trigger payload to N8N via its webhook endpoint.

    Strategy (in priority order):
      1. Dynamic path resolved from the N8N webhook_entity DB table.
      2. Production webhook path:      /webhook/ultravox/call-ended
      3. Test/staging webhook path:    /webhook-test/ultravox/call-ended

    The first target that returns 200/201 wins. All failures are collected
    and returned so the caller can surface them in the response.

    Args:
        workflow_type: A descriptive event type string (e.g., "document_processing").
        data: A dict containing call_id, phone_number, household_hash, messages, etc.

    Returns:
        {
            "success": bool,
            "target":  "<url that succeeded>" | None,
            "status_code": int | None,
            "response_json": dict | None,
            "errors": [str, ...],
        }
    """
    if not N8N_WEBHOOK_URL:
        logger.error("N8N_WEBHOOK_URL is not configured.")
        return {"success": False, "error": "N8N_WEBHOOK_URL not configured"}

    webhook_base = N8N_WEBHOOK_URL.rstrip("/")

    # ── Step 1: Try to resolve the active webhook path from N8N's own DB ──
    targets: list[str] = []
    pool = get_pool()
    if pool:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT "webhookPath"
                    FROM webhook_entity
                    WHERE method = 'POST'
                      AND "webhookPath" LIKE $1
                    ORDER BY LENGTH("webhookPath") DESC
                    LIMIT 1
                    """,
                    "%/ultravox/call-ended",
                )
                if row and row.get("webhookPath"):
                    dynamic_path = row["webhookPath"]
                    safe_path = quote(dynamic_path.lstrip("/"), safe="/")
                    targets.append(f"{webhook_base}/{safe_path}")
                    logger.debug(f"Resolved dynamic N8N webhook path: {dynamic_path}")
        except Exception as exc:
            logger.warning(f"Could not resolve dynamic N8N webhook path: {exc}")

    # ── Step 2: Add static fallback paths ──
    targets.extend([
        f"{webhook_base}/ultravox/call-ended",
        f"{webhook_base}-test/ultravox/call-ended",
    ])

    # Deduplicate while preserving order
    seen: set[str] = set()
    targets = [t for t in targets if not (t in seen or seen.add(t))]

    # ── Step 3: Build payload ──
    payload = {
        "event_type":      workflow_type,
        "call_id":         data.get("call_id"),
        "customer_number": data.get("phone_number"),
        "household_hash":  data.get("household_hash"),
        "duration_secs":   data.get("duration") or 0,
        "language":        data.get("language") or "auto",
        "messages":        data.get("messages") or [],
        "metadata": {
            "source":    "ultravox-real-handler",
            "timestamp": now_iso(),
            **(data.get("metadata") or {}),
        },
    }

    # ── Step 4: Try each target in order ──
    errors: list[str] = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for target in targets:
            try:
                logger.info(f"Attempting N8N webhook: POST {target}")
                resp = await client.post(target, json=payload)

                if resp.status_code in {200, 201}:
                    try:
                        parsed = resp.json()
                    except Exception:
                        parsed = {"text": resp.text}

                    logger.info(f"N8N webhook succeeded: {target} ({resp.status_code})")
                    return {
                        "success":       True,
                        "target":        target,
                        "status_code":   resp.status_code,
                        "response_json": parsed,
                        "errors":        [],
                    }

                msg = f"{target} → {resp.status_code}: {resp.text}"
                errors.append(msg)
                logger.warning(f"N8N webhook rejected: {msg}")

            except Exception as exc:
                msg = f"{target} → exception: {exc}"
                errors.append(msg)
                logger.error(f"N8N webhook attempt failed: {msg}")

    logger.error(f"All N8N webhook targets failed. Errors: {errors}")
    return {"success": False, "errors": errors}
