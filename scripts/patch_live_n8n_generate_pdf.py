#!/usr/bin/env python3
import argparse
import json
import os
import sys

import psycopg2


def patch_nodes(nodes, js_code, build_response_js=None):
    changed = False
    for node in nodes:
        if node.get("name") == "Generate PDF (pdf-lib)":
            node.setdefault("parameters", {})["jsCode"] = js_code
            changed = True
        if build_response_js and node.get("name") == "Build Response Data":
            node.setdefault("parameters", {})["jsCode"] = build_response_js
            changed = True
        if node.get("name") == "Upload to MinIO":
            node.setdefault("parameters", {})["fileName"] = "={{ $json.object_key || $json.filename }}"
            changed = True
        if node.get("name") == "Fetch Template":
            node.setdefault("parameters", {})["fileKey"] = (
                "={{ $json.pdf_template_key || ($json.eligible_schemes && $json.eligible_schemes[0] && $json.eligible_schemes[0].pdf_template_key) || $('Build Response Data').first().json.pdf_template_key }}"
            )
            changed = True
    return nodes, changed


def main():
    parser = argparse.ArgumentParser(
        description="Patch active n8n workflow Generate PDF and Upload nodes from local JS code."
    )
    parser.add_argument("--workflow-id", default="IJPL6b4yqlOayL0N")
    parser.add_argument("--js-file", default="generate_pdf_code.js")
    parser.add_argument("--build-response-js-file", default="build_response_code.js")
    parser.add_argument("--host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PGPORT", "5432")))
    parser.add_argument("--db", default=os.getenv("PGDATABASE", "zelia"))
    parser.add_argument("--user", default=os.getenv("PGUSER", "zelia"))
    parser.add_argument("--password", default=os.getenv("PGPASSWORD", "zelia_secure_2024"))
    args = parser.parse_args()

    if not os.path.exists(args.js_file):
        print(f"JS file not found: {args.js_file}", file=sys.stderr)
        sys.exit(1)

    js_code = open(args.js_file, "r", encoding="utf-8").read()
    build_response_js = None
    if os.path.exists(args.build_response_js_file):
        build_response_js = open(args.build_response_js_file, "r", encoding="utf-8").read()
    conn = psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.db,
        user=args.user,
        password=args.password,
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute(
        'SELECT "activeVersionId", nodes::text FROM workflow_entity WHERE id = %s',
        (args.workflow_id,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Workflow not found: {args.workflow_id}")
    active_version_id, entity_nodes_text = row

    entity_nodes = json.loads(entity_nodes_text)
    entity_nodes, entity_changed = patch_nodes(entity_nodes, js_code, build_response_js=build_response_js)
    if entity_changed:
        cur.execute(
            'UPDATE workflow_entity SET nodes = %s::json, "updatedAt" = NOW() WHERE id = %s',
            (json.dumps(entity_nodes, ensure_ascii=False), args.workflow_id),
        )

    cur.execute(
        'SELECT nodes::text FROM workflow_history WHERE "versionId" = %s',
        (active_version_id,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Active workflow history not found: {active_version_id}")
    history_nodes = json.loads(row[0])
    history_nodes, history_changed = patch_nodes(history_nodes, js_code, build_response_js=build_response_js)
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
                "upload_fileName": "={{ $json.object_key || $json.filename }}",
                "fetch_template_fileKey": "={{ $json.pdf_template_key || ($json.eligible_schemes && $json.eligible_schemes[0] && $json.eligible_schemes[0].pdf_template_key) || $('Build Response Data').first().json.pdf_template_key }}",
                "build_response_updated": bool(build_response_js),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
