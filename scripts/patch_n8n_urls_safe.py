#!/usr/bin/env python3
"""
Lightweight N8N workflow URL patcher.
Fetches the current workflow from N8N API, patches localhost URLs to Docker
service names, and pushes the update back — all with proper timeouts.

Usage:
    python3 scripts/patch_n8n_urls_safe.py
"""
import json
import sys
import os
import urllib.request
import urllib.error

N8N_BASE = os.getenv("N8N_BASE_URL", "http://localhost:5678")
API_KEY  = os.getenv("N8N_API_KEY", "n8n_api_key_debug_123")
WFID     = os.getenv("N8N_WORKFLOW_ID", "IJPL6b4yqlOayL0N")
TIMEOUT  = 30  # seconds — prevents hanging

# URL mappings: host -> docker internal
URL_MAPPINGS = {
    "127.0.0.1:8007": "retrieval-service:8007",
    "localhost:8007":  "retrieval-service:8007",
    "127.0.0.1:8011": "rules-engine:8000",
    "localhost:8011":  "rules-engine:8000",
    "127.0.0.1:8009": "submission-service:8009",
    "localhost:8009":  "submission-service:8009",
    "127.0.0.1:8010": "document-processor:8010",
    "localhost:8010":  "document-processor:8010",
    "127.0.0.1:9000": "minio:9000",
    "localhost:9000":  "minio:9000",
    "127.0.0.1:8019": "form-filler-service:8013",
    "localhost:8019":  "form-filler-service:8013",
    "127.0.0.1:8013": "ultravox-handler:8000",
    "localhost:8013":  "ultravox-handler:8000",
    "127.0.0.1:5432": "postgres:5432",
    "localhost:5432":  "postgres:5432",
}

# N8N API allowed top-level fields for PUT — strict minimum
ALLOWED_KEYS = {"name", "nodes", "connections", "settings"}


def api_get(path):
    """GET from N8N API with timeout."""
    url = f"{N8N_BASE}/api/v1{path}"
    req = urllib.request.Request(url, headers={"X-N8N-API-KEY": API_KEY})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"❌ GET {url} failed: {e}")
        sys.exit(1)


def api_put(path, data):
    """PUT to N8N API with timeout."""
    url = f"{N8N_BASE}/api/v1{path}"
    payload = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=payload, method="PUT",
        headers={
            "X-N8N-API-KEY": API_KEY,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"❌ PUT {url} failed: {e}")
        if hasattr(e, 'read'):
            print(f"   Response: {e.read().decode()[:500]}")
        return None


def patch_urls(workflow_json):
    """Replace localhost URLs with Docker service names."""
    raw = json.dumps(workflow_json)
    count = 0
    for old, new in URL_MAPPINGS.items():
        if old in raw:
            raw = raw.replace(old, new)
            count += 1
            print(f"  ✅ {old} → {new}")
    if count == 0:
        print("  ℹ️  No localhost URLs found to patch")
    return json.loads(raw)


def main():
    print("=" * 60)
    print("ZELIA N8N Workflow URL Patcher (Safe)")
    print("=" * 60)

    # Step 1: Fetch current workflow
    print(f"\n[1/3] Fetching workflow {WFID}...")
    wf = api_get(f"/workflows/{WFID}")
    print(f"  Got workflow: {wf.get('name', '?')} ({len(wf.get('nodes', []))} nodes)")

    # Step 2: Patch URLs
    print("\n[2/3] Patching localhost URLs...")
    patched = patch_urls(wf)

    # Step 3: Upload — strip read-only fields
    print("\n[3/3] Uploading patched workflow...")
    upload_payload = {k: v for k, v in patched.items() if k in ALLOWED_KEYS}
    result = api_put(f"/workflows/{WFID}", upload_payload)

    if result and result.get("id") == WFID:
        print(f"\n✅ Workflow {WFID} updated successfully!")
    elif result:
        print(f"\n⚠️  Response received but unexpected: {json.dumps(result)[:300]}")
    else:
        print("\n❌ Upload failed. You may need to run this manually or restart n8n.")
        print("   Try: docker compose restart n8n")

    print("=" * 60)


if __name__ == "__main__":
    main()
