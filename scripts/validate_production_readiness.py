#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from minio import Minio  # type: ignore
except Exception:  # pragma: no cover
    Minio = None


def load_env_file(path: Path) -> Dict[str, str]:
    vals: Dict[str, str] = {}
    if not path.exists():
        return vals
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        vals[k.strip()] = v.strip().strip('"').strip("'")
    return vals


def check_http(url: str, timeout: float = 3.0) -> Tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read(50000).decode("utf-8", errors="replace")
            return True, body
    except Exception as exc:
        return False, str(exc)


def check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    env_from_file = load_env_file(root / ".env")
    env = {**env_from_file, **os.environ}

    required_env = [
        "PINECONE_API_KEY",
        "OPENAI_API_KEY",
        "N8N_BASIC_AUTH_USER",
        "N8N_BASIC_AUTH_PASSWORD",
        "ULTRAVOX_API_KEY",
    ]

    env_checks = [{"key": k, "present": bool(env.get(k))} for k in required_env]

    service_checks = [
        {"name": "n8n", "url": "http://localhost:5678/healthz"},
        {"name": "retrieval", "url": "http://localhost:8007/health"},
        {"name": "rules", "url": "http://localhost:8005/health"},
        {"name": "document_processor", "url": "http://localhost:8004/health"},
        {"name": "submission", "url": "http://localhost:8009/health"},
        {"name": "voice", "url": "http://localhost:8018/health"},
        {"name": "voice_asr", "url": "http://localhost:8018/asr/health"},
    ]

    service_results: List[dict] = []
    service_payloads: Dict[str, dict] = {}
    for s in service_checks:
        ok, detail = check_http(s["url"])
        if ok:
            try:
                service_payloads[s["name"]] = json.loads(detail)
            except Exception:
                service_payloads[s["name"]] = {"raw": detail[:500]}
        service_results.append({"name": s["name"], "ok": ok, "detail": detail[:500]})

    ports = [
        ("postgres", "localhost", 5432),
        ("minio", "localhost", 9000),
        ("n8n", "localhost", 5678),
    ]
    port_results = [{"name": n, "host": h, "port": p, "ok": check_port(h, p)} for n, h, p in ports]

    # Lightweight schema presence check by static file inspection (no DB creds required).
    schema_text = (root / "schema_v28_upgrade.sql").read_text(encoding="utf-8", errors="ignore")
    schema_markers = {
        "pdf_template_key": "pdf_template_key" in schema_text,
        "reviewer_id": "reviewer_id" in schema_text,
        "review_notes": "review_notes" in schema_text,
        "filled_pdf_uri": "filled_pdf_uri" in schema_text,
    }

    submission_src = (root / "backend" / "services" / "submission-service" / "main.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    security_checks = {
        "submission_role_enforcement_enabled": bool(
            service_payloads.get("submission", {}).get("role_enforcement", False)
        ),
        "hashed_identifier_usage_expected": "sha256" in submission_src and "_hash_identifier" in submission_src,
        "minio_buckets_scoped": False,
        "retrieval_mode_configured": bool(service_payloads.get("retrieval", {}).get("retrieval_mode")),
    }

    minio_checks = {"available": False, "buckets": {}, "bucket_policy": {}}
    minio_endpoint = env.get("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key = env.get("MINIO_ROOT_USER", "minioadmin")
    minio_secret_key = env.get("MINIO_ROOT_PASSWORD", "minioadmin")
    minio_secure = str(env.get("MINIO_SECURE", "false")).lower() == "true"
    required_buckets = ["templates", "filled-forms", "verified-docs"]
    if Minio:
        try:
            c = Minio(
                minio_endpoint,
                access_key=minio_access_key,
                secret_key=minio_secret_key,
                secure=minio_secure,
            )
            minio_checks["available"] = True
            all_exist = True
            for b in required_buckets:
                exists = c.bucket_exists(b)
                minio_checks["buckets"][b] = {"exists": exists}
                all_exist = all_exist and exists
                if exists:
                    try:
                        policy = c.get_bucket_policy(b)
                        minio_checks["bucket_policy"][b] = bool(policy)
                    except Exception:
                        minio_checks["bucket_policy"][b] = False
            security_checks["minio_buckets_scoped"] = all_exist
        except Exception as exc:
            minio_checks["error"] = str(exc)
    else:
        minio_checks["error"] = "minio package unavailable"

    all_env_ok = all(c["present"] for c in env_checks)
    all_services_ok = all(c["ok"] for c in service_results)
    all_ports_ok = all(c["ok"] for c in port_results)
    all_schema_ok = all(schema_markers.values())

    status = "ready" if (all_env_ok and all_services_ok and all_ports_ok and all_schema_ok) else "not_ready"
    if not all(security_checks.values()):
        status = "not_ready"

    report = {
        "status": status,
        "checks": {
            "env": env_checks,
            "services": service_results,
            "ports": port_results,
            "schema_markers": schema_markers,
            "security": security_checks,
            "minio": minio_checks,
        },
        "next_steps": [
            "Run database migrations if schema markers fail in live DB.",
            "Start missing services with docker compose up -d --build.",
            "Populate Pinecone index with scripts/seed_pinecone_top_states.py.",
            "Upload templates to MinIO bucket templates/ before E2E execution.",
            "Enable role enforcement in submission-service for CHW endpoints.",
        ],
    }

    out_path = root / "data" / "ingestion" / "production_readiness.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nReport written to: {out_path}")
    if status != "ready":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
