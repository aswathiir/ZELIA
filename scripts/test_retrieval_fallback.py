#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.request
import urllib.error
import time
import uuid


def post_json(url: str, payload: dict):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(url: str):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_health(url: str, max_wait_sec: int = 300):
    start = time.time()
    last_err = None
    while time.time() - start < max_wait_sec:
        try:
            return get_json(url)
        except Exception as exc:
            last_err = exc
            time.sleep(2)
    raise RuntimeError(f"Retrieval service did not become ready in {max_wait_sec}s: {last_err}")


def main():
    health = wait_for_health("http://localhost:8007/health")
    annoy_ready = bool(health.get("annoy", {}).get("ready"))
    pinecone_ok = health.get("pinecone", {}).get("status") == "connected"

    payload = {"query": "widow pension Karnataka low income", "top_k": 5}
    # If Annoy is ready, explicitly test fallback path. Otherwise allow Pinecone primary.
    if annoy_ready:
        payload["use_pinecone_first"] = False
    else:
        payload["use_pinecone_first"] = True

    try:
        data = post_json("http://localhost:8007/search/hybrid", payload)
    except urllib.error.HTTPError as e:
        if e.code != 503:
            raise
        # Bootstrap one local embedding so Annoy fallback can be tested deterministically.
        bootstrap_id = f"fallback_bootstrap_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        post_json(
            "http://localhost:8007/embed",
            {
                "text": "Karnataka widow pension eligibility for low income households.",
                "document_id": bootstrap_id,
                "metadata": {"scheme_id": "ka-widow-pension", "document_type": "scheme_rule"},
            },
        )
        try:
            post_json("http://localhost:8007/rebuild-index", {})
        except Exception:
            pass
        data = post_json(
            "http://localhost:8007/search/hybrid",
            {"query": payload["query"], "top_k": payload["top_k"], "use_pinecone_first": False},
        )

    source = data.get("source_used")
    results = data.get("results", [])
    if source not in {"annoy", "hybrid", "pinecone"}:
        raise SystemExit(f"Unexpected source_used: {source}")
    if not results:
        raise SystemExit("No retrieval results returned")
    print(
        json.dumps(
            {
                "status": "ok",
                "source_used": source,
                "result_count": len(results),
                "annoy_ready": annoy_ready,
                "pinecone_connected": pinecone_ok,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
