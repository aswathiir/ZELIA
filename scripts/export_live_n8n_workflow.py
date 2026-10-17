#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

import psycopg2
from psycopg2.extras import RealDictCursor


def _as_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default
    return default


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export live n8n workflow JSON from workflow_entity."
    )
    parser.add_argument("--workflow-id", default="IJPL6b4yqlOayL0N")
    parser.add_argument("--host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PGPORT", "5432")))
    parser.add_argument("--db", default=os.getenv("PGDATABASE", "zelia"))
    parser.add_argument("--user", default=os.getenv("PGUSER", "zelia"))
    parser.add_argument(
        "--password",
        default=os.getenv("PGPASSWORD", "zelia_secure_2024"),
    )
    parser.add_argument(
        "--out",
        default="zeliaintegration_v28b_fresh.json",
        help="Output JSON file path.",
    )
    args = parser.parse_args()

    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.db,
        user=args.user,
        password=args.password,
        cursor_factory=RealDictCursor,
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, name, active, nodes, connections, settings, "pinData", "versionId", "activeVersionId"
        FROM workflow_entity
        WHERE id = %s
        """,
        (args.workflow_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise SystemExit(f"Workflow not found: {args.workflow_id}")

    payload: Dict[str, Any] = {
        "id": row["id"],
        "name": row["name"],
        "active": bool(row["active"]),
        "versionId": row.get("versionId"),
        "activeVersionId": row.get("activeVersionId"),
        "nodes": _as_json(row.get("nodes"), []),
        "connections": _as_json(row.get("connections"), {}),
        "settings": _as_json(row.get("settings"), {}),
        "pinData": _as_json(row.get("pinData"), {}),
    }

    out_path = Path(args.out)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "workflow_id": args.workflow_id,
                "nodes": len(payload["nodes"]),
                "out": str(out_path.resolve()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
