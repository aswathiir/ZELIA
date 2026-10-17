#!/usr/bin/env python3
"""Seed Pinecone with top-state scheme metadata from DB."""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor


def load_clients():
    from sentence_transformers import SentenceTransformer
    from pinecone import Pinecone

    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2"), Pinecone


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-url", default=os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL"))
    parser.add_argument("--pinecone-api-key", default=os.getenv("PINECONE_API_KEY"))
    parser.add_argument("--index", default=os.getenv("PINECONE_INDEX_NAME", "zelia-schemes"))
    parser.add_argument("--manifest", default="data/ingestion/top5_manifest.json")
    parser.add_argument("--namespace", default="schemes")
    parser.add_argument("--top-k", type=int, default=5000)
    args = parser.parse_args()

    if not args.db_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL required")
    if not args.pinecone_api_key:
        raise SystemExit("PINECONE_API_KEY required")

    model, Pinecone = load_clients()

    conn = psycopg2.connect(args.db_url, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT scheme_id, scheme_name, state_code, description, benefits,
               required_documents, eligibility_summary, pdf_template_key
        FROM schemes
        WHERE state_code IN ('KA','TN','UP','MH','RJ','ALL')
        LIMIT %s
        """,
        (args.top_k,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    pc = Pinecone(api_key=args.pinecone_api_key)
    index = pc.Index(args.index)

    vectors = []
    counts = defaultdict(int)
    missing_meta = 0

    for row in rows:
        text = " ".join(
            [
                row.get("scheme_name") or "",
                row.get("description") or "",
                row.get("benefits") or "",
                row.get("eligibility_summary") or "",
            ]
        ).strip()
        emb = model.encode(text).tolist()
        meta = {
            "scheme_id": row.get("scheme_id"),
            "title": row.get("scheme_name") or "",
            "description": row.get("description") or "",
            "state_code": row.get("state_code") or "",
            "benefits": row.get("benefits") or "",
            "required_documents": row.get("required_documents") or "",
            "eligibility_summary": row.get("eligibility_summary") or "",
            "pdf_template_key": row.get("pdf_template_key") or "",
        }
        if not meta["scheme_id"] or not meta["title"]:
            missing_meta += 1
            continue
        counts[meta["state_code"]] += 1
        vectors.append({"id": str(meta["scheme_id"]), "values": emb, "metadata": meta})

    # Upsert in chunks
    chunk = 100
    for i in range(0, len(vectors), chunk):
        index.upsert(vectors=vectors[i : i + chunk], namespace=args.namespace)

    summary = {
        "seeded_at": datetime.utcnow().isoformat() + "Z",
        "index": args.index,
        "namespace": args.namespace,
        "rows_read": len(rows),
        "vectors_upserted": len(vectors),
        "missing_metadata": missing_meta,
        "by_state": dict(counts),
    }

    manifest_path = args.manifest
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        manifest = {}
    manifest["pinecone_seed_summary"] = summary
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
