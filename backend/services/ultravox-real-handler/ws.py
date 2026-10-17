"""
ws.py — WebSocket connection registry and broadcast helper.

Manages the list of live WebSocket clients and provides a single
`broadcast()` coroutine that all endpoints use to push real-time events
to the frontend.
"""
import logging
from typing import Any, Dict, List

from fastapi import WebSocket

from utils import now_iso

logger = logging.getLogger(__name__)

# In-memory list of currently connected WebSocket clients.
_clients: List[WebSocket] = []


def connected_count() -> int:
    """Return the number of currently connected WebSocket clients."""
    return len(_clients)


async def broadcast(event: str, payload: Dict[str, Any]) -> None:
    """
    Push a JSON frame to every connected WebSocket client.
    Dead connections are pruned automatically.

    Frame shape:
        {
            "event":   "<event_name>",
            "payload": { ... },
            "ts":      "<utc_iso_timestamp>"
        }
    """
    if not _clients:
        return

    frame = {"event": event, "payload": payload, "ts": now_iso()}
    dead: List[WebSocket] = []

    for ws in _clients:
        try:
            await ws.send_json(frame)
        except Exception:
            dead.append(ws)

    for ws in dead:
        if ws in _clients:
            _clients.remove(ws)
            logger.debug(f"Pruned dead WebSocket client. Remaining: {len(_clients)}")


async def register(websocket: WebSocket) -> None:
    """Accept and register a new WebSocket connection."""
    await websocket.accept()
    _clients.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(_clients)}")


def deregister(websocket: WebSocket) -> None:
    """Remove a WebSocket from the active client list."""
    if websocket in _clients:
        _clients.remove(websocket)
        logger.info(f"WebSocket client disconnected. Remaining: {len(_clients)}")
