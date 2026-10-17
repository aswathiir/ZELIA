"""
ai.py — AI/LLM helper functions used by the Ultravox handler.

Currently contains:
  - extract_from_transcript(): uses Groq (llama3) to extract structured
    citizen profile data from a raw voice conversation transcript.

Adding future AI helpers here keeps all LLM calls in one auditable place.
"""
import json
import logging
from typing import Any, Dict, List

import httpx

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)


async def extract_from_transcript(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract citizen profile entities from a voice call transcript using Groq.

    The model is prompted to return a JSON object with any of the following
    keys that it can identify from the conversation:
        name, age, address, monthly_income, dob, state, gender, phone

    This is a best-effort enrichment step — the caller should always
    handle an empty dict return gracefully.

    Args:
        messages: List of message dicts, each with 'role' and 'text' keys.

    Returns:
        A dict of extracted fields, all keys lowercased.
        Returns {} if Groq is unconfigured, the transcript is empty,
        or extraction fails for any reason.
    """
    if not GROQ_API_KEY:
        logger.debug("Groq API key not configured — skipping transcript extraction.")
        return {}

    if not messages:
        return {}

    transcript_text = "\n".join(
        f"{msg.get('role', 'user')}: {msg.get('text', '')}"
        for msg in messages
    ).strip()

    if not transcript_text:
        return {}

    system_prompt = (
        "You are a precise data extractor. Extract these entities from the transcript if mentioned: "
        "name, age, address, monthly_income, dob, state, gender, phone.\n"
        "Return ONLY valid JSON with those keys. If an entity is not mentioned, exclude the key or set it to null.\n"
        "For 'state', extract the full Indian state name (e.g., Karnataka, Tamil Nadu, Maharashtra, etc.).\n"
        "For 'gender', use 'male', 'female', or 'other'."
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": f"Transcript:\n{transcript_text}"},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )

            if resp.status_code != 200:
                logger.warning(
                    f"Groq API returned non-200 status {resp.status_code}: {resp.text}"
                )
                return {}

            content = resp.json()["choices"][0]["message"]["content"]
            extracted = json.loads(content)
            # Normalise keys to lowercase and strip null/empty values
            result = {k.lower(): v for k, v in extracted.items() if v is not None and v != ""}
            logger.info(f"Groq extraction successful. Fields found: {list(result.keys())}")
            return result

    except Exception as exc:
        logger.warning(f"Groq transcript extraction failed: {exc}")
        return {}
