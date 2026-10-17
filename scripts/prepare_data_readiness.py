#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

import psycopg2
from minio import Minio


TOP_STATE_CODES = {"KA", "TN", "UP", "MH", "RJ", "ALL"}
DEFAULT_EXCLUDE = {"formsandregister.pdf"}
LOCAL_DB_FALLBACK = "postgresql://zelia:zelia_secure_2024@localhost:5432/zelia"
PHASE1_ACTIVE_SCHEMES = [
    "ka-widow-pension",
    "ka-old-age-pension",
    "ka-disability-pension",
    "pmjay",
    "pm-kisan",
    "ka-destitute-pension",
    "pm-ujjwala",
    "nsap-ignoaps",
]


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, val = s.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def normalize_db_url(db_url: str) -> str:
    if not db_url:
        return db_url
    normalized = db_url
    normalized = normalized.replace("@postgres:", "@localhost:")
    normalized = normalized.replace("@db:", "@localhost:")
    return normalized


def ensure_bucket(client: Minio, bucket: str) -> None:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_templates(
    client: Minio, bucket: str, templates_dir: Path, include_bundle: bool, prefix: str = ""
) -> Dict[str, int]:
    uploaded = 0
    existing = 0
    considered = 0
    keys = []
    for pdf in sorted(templates_dir.glob("*.pdf")):
        if not include_bundle and pdf.name in DEFAULT_EXCLUDE:
            continue
        considered += 1
        obj = f"{prefix}{pdf.name}" if prefix else pdf.name
        stat_ok = True
        try:
            client.stat_object(bucket, obj)
        except Exception:
            stat_ok = False
        if stat_ok:
            existing += 1
        else:
            content_type = mimetypes.guess_type(pdf.name)[0] or "application/pdf"
            client.fput_object(bucket, obj, str(pdf), content_type=content_type)
            uploaded += 1
        keys.append(obj)
    return {"considered": considered, "uploaded": uploaded, "existing": existing, "keys": keys}


def db_mapping_status(db_url: str, scope: str = "active") -> Dict[str, object]:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    if scope == "all":
        cur.execute(
            """
            SELECT scheme_id, state_code, COALESCE(pdf_template_key,'') AS pdf_template_key
            FROM schemes
            WHERE COALESCE(state_code,'ALL') = ANY(%s)
            """,
            (list(TOP_STATE_CODES),),
        )
    else:
        cur.execute(
            """
            SELECT scheme_id, state_code, COALESCE(pdf_template_key,'') AS pdf_template_key
            FROM schemes
            WHERE scheme_id = ANY(%s)
            """,
            (PHASE1_ACTIVE_SCHEMES,),
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    total = len(rows)
    unmapped = [r for r in rows if not str(r[2]).strip()]
    mapped_keys = sorted({str(r[2]).strip() for r in rows if str(r[2]).strip()})
    return {
        "scope": scope,
        "total_schemes_in_scope": total,
        "unmapped_count": len(unmapped),
        "unmapped_scheme_ids": [r[0] for r in unmapped][:100],
        "mapped_template_keys": mapped_keys,
    }


def main() -> None:
    load_dotenv()
    p = argparse.ArgumentParser(description="Prepare data readiness for ZELIA Free v1.")
    p.add_argument(
        "--db-url",
        default=(os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL") or LOCAL_DB_FALLBACK),
    )
    p.add_argument("--templates-dir", default="dataset/govt/templates")
    p.add_argument("--minio-endpoint", default=os.getenv("MINIO_ENDPOINT", "localhost:9000"))
    p.add_argument("--minio-access-key", default=os.getenv("MINIO_ROOT_USER", "minioadmin"))
    p.add_argument("--minio-secret-key", default=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin"))
    p.add_argument("--minio-secure", action="store_true")
    p.add_argument("--include-bundle", action="store_true")
    p.add_argument("--template-prefix", default="")
    p.add_argument("--run-ingest", action="store_true")
    p.add_argument("--run-pinecone-seed", action="store_true")
    p.add_argument("--pinecone-api-key", default=os.getenv("PINECONE_API_KEY"))
    p.add_argument("--pinecone-index", default=os.getenv("PINECONE_INDEX_NAME", "zelia-schemes"))
    p.add_argument("--mapping-scope", choices=["active", "all"], default="active")
    p.add_argument("--out", default="data/ingestion/data_readiness_report.json")
    args = p.parse_args()
    args.db_url = normalize_db_url(args.db_url)

    report: Dict[str, object] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "status": "pending",
        "steps": {},
    }

    if args.run_ingest:
        cmd = [
            "python3",
            "scripts/ingest_top_states_to_supabase.py",
            "--dataset-root",
            "dataset/govt/government_schemes/govt scheme",
            "--manifest",
            "data/ingestion/top5_manifest.json",
        ]
        if args.db_url:
            cmd.extend(["--db-url", args.db_url])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        report["steps"]["ingest"] = {"returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}

    if args.run_pinecone_seed:
        cmd = [
            "python3",
            "scripts/seed_pinecone_top_states.py",
            "--index",
            args.pinecone_index,
            "--manifest",
            "data/ingestion/top5_manifest.json",
        ]
        if args.db_url:
            cmd.extend(["--db-url", args.db_url])
        if args.pinecone_api_key:
            cmd.extend(["--pinecone-api-key", args.pinecone_api_key])
        proc = subprocess.run(cmd, capture_output=True, text=True)
        report["steps"]["pinecone_seed"] = {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
        }

    client = Minio(
        args.minio_endpoint,
        access_key=args.minio_access_key,
        secret_key=args.minio_secret_key,
        secure=args.minio_secure,
    )
    for b in ("templates", "filled-forms", "verified-docs"):
        ensure_bucket(client, b)
    upload_stats = upload_templates(
        client=client,
        bucket="templates",
        templates_dir=Path(args.templates_dir),
        include_bundle=args.include_bundle,
        prefix=args.template_prefix,
    )
    report["steps"]["minio_templates"] = upload_stats

    mapping = {}
    if args.db_url:
        mapping = db_mapping_status(args.db_url, scope=args.mapping_scope)
        uploaded_keys = set(upload_stats["keys"])
        missing_in_bucket = [k for k in mapping.get("mapped_template_keys", []) if (args.template_prefix + k) not in uploaded_keys]
        mapping["mapped_keys_missing_in_templates_bucket"] = missing_in_bucket
    report["steps"]["db_mapping"] = mapping

    ok = True
    if mapping:
        ok = ok and (mapping.get("unmapped_count", 0) == 0)
        ok = ok and (len(mapping.get("mapped_keys_missing_in_templates_bucket", [])) == 0)
    for step in ("ingest", "pinecone_seed"):
        if step in report["steps"] and report["steps"][step].get("returncode", 0) != 0:
            ok = False

    report["status"] = "ready" if ok else "not_ready"

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
