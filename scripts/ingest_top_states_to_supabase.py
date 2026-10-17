#!/usr/bin/env python3
"""Ingest top-5-state + central scheme text files into Supabase/Postgres schemes table."""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

TOP_STATES = ["karnataka", "tamilnadu", "uttar-pradesh", "maharashtra", "rajasthan", "central"]
STATE_CODE = {
    "karnataka": "KA",
    "tamilnadu": "TN",
    "uttar-pradesh": "UP",
    "maharashtra": "MH",
    "rajasthan": "RJ",
    "central": "ALL",
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def parse_doc(file_path: Path) -> Dict[str, str]:
    raw = file_path.read_text(encoding="utf-8", errors="ignore")
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    title = lines[0][:180] if lines else file_path.stem
    if title.lower().startswith("table of contents") and len(lines) > 1:
        title = lines[1][:180]

    cleaned = re.sub(r"\s+", " ", raw).strip()
    description = cleaned[:1200] if cleaned else title

    benefits = ""
    for marker in ["Benefits", "Assistance Amount", "coverage", "pension", "loan"]:
        if marker.lower() in cleaned.lower():
            benefits = f"Contains {marker}-related details in source text"
            break

    return {
        "title": title,
        "description": description,
        "benefits": benefits,
        "eligibility_summary": "Refer source description",
        "required_documents": "[]",
    }


def upsert_scheme(cur, payload: Dict[str, str]):
    cur.execute(
        """
        INSERT INTO schemes (
            scheme_id, scheme_name, state_code, category, description,
            benefits, required_documents, eligibility_summary, pdf_template_key, updated_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        ON CONFLICT (scheme_id) DO UPDATE SET
            scheme_name = EXCLUDED.scheme_name,
            state_code = EXCLUDED.state_code,
            category = EXCLUDED.category,
            description = EXCLUDED.description,
            benefits = EXCLUDED.benefits,
            required_documents = EXCLUDED.required_documents,
            eligibility_summary = EXCLUDED.eligibility_summary,
            updated_at = NOW()
        """,
        (
            payload["scheme_id"],
            payload["scheme_name"],
            payload["state_code"],
            payload["category"],
            payload["description"],
            payload["benefits"],
            payload["required_documents"],
            payload["eligibility_summary"],
            payload.get("pdf_template_key"),
        ),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", default="dataset/govt/government_schemes/govt scheme")
    parser.add_argument("--db-url", default=os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL"))
    parser.add_argument("--manifest", default="data/ingestion/top5_manifest.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.db_url and not args.dry_run:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    root = Path(args.dataset_root)
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "dataset_root": str(root),
        "scope": TOP_STATES,
        "states": {},
        "totals": {"files": 0, "parsed": 0, "upserted": 0, "failed": 0},
    }

    conn = None
    cur = None
    if not args.dry_run:
        conn = psycopg2.connect(args.db_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()

    try:
        for state in TOP_STATES:
            folder = root / state
            files = sorted(folder.glob("*.txt")) if folder.exists() else []
            state_stats = {"files": len(files), "parsed": 0, "upserted": 0, "failed": 0}

            for f in files:
                manifest["totals"]["files"] += 1
                try:
                    parsed = parse_doc(f)
                    state_code = STATE_CODE[state]
                    scheme_id = f"{state_code.lower()}-{slugify(f.stem)}"
                    payload = {
                        "scheme_id": scheme_id,
                        "scheme_name": parsed["title"],
                        "state_code": state_code,
                        "category": "general",
                        "description": parsed["description"],
                        "benefits": parsed["benefits"],
                        "required_documents": parsed["required_documents"],
                        "eligibility_summary": parsed["eligibility_summary"],
                        "pdf_template_key": None,
                    }
                    state_stats["parsed"] += 1
                    manifest["totals"]["parsed"] += 1
                    if cur:
                        upsert_scheme(cur, payload)
                        state_stats["upserted"] += 1
                        manifest["totals"]["upserted"] += 1
                except Exception:
                    state_stats["failed"] += 1
                    manifest["totals"]["failed"] += 1
            manifest["states"][state] = state_stats

        if conn:
            conn.commit()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    out = Path(args.manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["totals"], indent=2))
    print(f"Manifest written: {out}")


if __name__ == "__main__":
    main()
