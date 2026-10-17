#!/usr/bin/env python3
import argparse
import json
import os
import sys

import psycopg2


def patch_nodes(nodes, parse_js):
    changed = False
    for node in nodes:
        if node.get("name") == "Parse Profile + Hash":
            node.setdefault("parameters", {})["jsCode"] = parse_js
            changed = True
        if node.get("name") == "Extract Profile (Groq)":
            # Keep workflow alive when Groq DNS/API is transiently unavailable.
            node["onError"] = "continueRegularOutput"
            changed = True
    return nodes, changed


def main():
    parser = argparse.ArgumentParser(description="Patch live workflow with resilient profile fallback parsing.")
    parser.add_argument("--workflow-id", default="IJPL6b4yqlOayL0N")
    parser.add_argument("--parse-js-file", default="parse_profile_code.js")
    parser.add_argument("--host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PGPORT", "5432")))
    parser.add_argument("--db", default=os.getenv("PGDATABASE", "zelia"))
    parser.add_argument("--user", default=os.getenv("PGUSER", "zelia"))
    parser.add_argument("--password", default=os.getenv("PGPASSWORD", "zelia_secure_2024"))
    args = parser.parse_args()

    if not os.path.exists(args.parse_js_file):
        print(f"parse js file not found: {args.parse_js_file}", file=sys.stderr)
        sys.exit(1)

    parse_js = open(args.parse_js_file, "r", encoding="utf-8").read()
    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.db,
        user=args.user,
        password=args.password,
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute('SELECT "activeVersionId", nodes::text FROM workflow_entity WHERE id = %s', (args.workflow_id,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Workflow not found: {args.workflow_id}")
    active_version_id, entity_nodes_text = row

    entity_nodes = json.loads(entity_nodes_text)
    entity_nodes, entity_changed = patch_nodes(entity_nodes, parse_js)
    if entity_changed:
        cur.execute(
            'UPDATE workflow_entity SET nodes = %s::json, "updatedAt" = NOW() WHERE id = %s',
            (json.dumps(entity_nodes, ensure_ascii=False), args.workflow_id),
        )

    cur.execute('SELECT nodes::text FROM workflow_history WHERE "versionId" = %s', (active_version_id,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Workflow history not found: {active_version_id}")
    history_nodes = json.loads(row[0])
    history_nodes, history_changed = patch_nodes(history_nodes, parse_js)
    if history_changed:
        cur.execute(
            'UPDATE workflow_history SET nodes = %s::json, "updatedAt" = NOW() WHERE "versionId" = %s',
            (json.dumps(history_nodes, ensure_ascii=False), active_version_id),
        )

    conn.commit()
    cur.close()
    conn.close()

    print(
        json.dumps(
            {
                "workflow_id": args.workflow_id,
                "active_version_id": active_version_id,
                "entity_patched": entity_changed,
                "history_patched": history_changed,
                "groq_onError": "continueRegularOutput",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

