#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def _headers(api_key: Optional[str], basic_user: Optional[str], basic_pass: Optional[str]) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if api_key:
        h["X-N8N-API-KEY"] = api_key
    elif basic_user and basic_pass:
        token = base64.b64encode(f"{basic_user}:{basic_pass}".encode("utf-8")).decode("ascii")
        h["Authorization"] = f"Basic {token}"
    return h


def _request_json(
    method: str,
    url: str,
    headers: Dict[str, str],
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, method=method, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read().decode("utf-8") or "{}"
        return json.loads(body)


def _list_workflows(api_base: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    url = f"{api_base}/workflows?limit=250"
    data = _request_json("GET", url, headers)
    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            return data["data"]
        if isinstance(data.get("workflows"), list):
            return data["workflows"]
    if isinstance(data, list):
        return data
    return []


def _resolve_workflow_id(
    api_base: str,
    headers: Dict[str, str],
    workflow_id: Optional[str],
    workflow_name: Optional[str],
) -> str:
    if workflow_id:
        return workflow_id
    workflows = _list_workflows(api_base, headers)
    if not workflows:
        raise RuntimeError("No workflows returned by n8n API.")
    if workflow_name:
        for wf in workflows:
            if str(wf.get("name")) == workflow_name:
                return str(wf.get("id"))
        # contains fallback
        for wf in workflows:
            if workflow_name.lower() in str(wf.get("name", "")).lower():
                return str(wf.get("id"))
    names = [str(w.get("name", "")) for w in workflows]
    raise RuntimeError(
        f"Could not resolve workflow id for name '{workflow_name}'. "
        f"Available workflows: {names[:20]}"
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Push local workflow JSON into live n8n workflow.")
    p.add_argument("--workflow-file", default="zeliaintegration_v28b_fresh.json")
    p.add_argument("--workflow-id", default=os.getenv("N8N_WORKFLOW_ID"))
    p.add_argument("--workflow-name", default=os.getenv("N8N_WORKFLOW_NAME"))
    p.add_argument("--n8n-base", default=os.getenv("N8N_BASE_URL", "http://localhost:5678/api/v1"))
    p.add_argument("--activate", action="store_true")
    args = p.parse_args()

    wf_path = Path(args.workflow_file)
    if not wf_path.exists():
        raise SystemExit(f"Workflow file not found: {wf_path}")
    local = json.loads(wf_path.read_text(encoding="utf-8"))

    api_key = os.getenv("N8N_API_KEY")
    basic_user = os.getenv("N8N_BASIC_AUTH_USER")
    basic_pass = os.getenv("N8N_BASIC_AUTH_PASSWORD")
    headers = _headers(api_key, basic_user, basic_pass)

    workflow_name = args.workflow_name or local.get("name")
    workflow_id = _resolve_workflow_id(args.n8n_base, headers, args.workflow_id, workflow_name)
    if not workflow_id:
        raise SystemExit("Could not resolve target workflow id.")

    current = _request_json("GET", f"{args.n8n_base}/workflows/{workflow_id}", headers)
    payload = {
        "name": local.get("name") or current.get("name") or "ZELIA Workflow",
        "nodes": local.get("nodes", []),
        "connections": local.get("connections", {}),
        "settings": local.get("settings", current.get("settings", {})),
        "active": bool(current.get("active", False)),
    }

    updated = _request_json("PUT", f"{args.n8n_base}/workflows/{workflow_id}", headers, payload)
    print(json.dumps({"status": "updated", "workflow_id": workflow_id, "name": payload["name"]}, indent=2))

    if args.activate and not bool(updated.get("active", False)):
        try:
            _request_json("POST", f"{args.n8n_base}/workflows/{workflow_id}/activate", headers, {})
            print(json.dumps({"status": "activated", "workflow_id": workflow_id}, indent=2))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            print(json.dumps({"status": "activation_failed", "workflow_id": workflow_id, "error": body}, indent=2))


if __name__ == "__main__":
    main()
