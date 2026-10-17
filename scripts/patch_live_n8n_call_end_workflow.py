#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict, List, Tuple

import psycopg2


PROCESS_MATCHES_JS = r"""
// Process Pinecone search results and resolve real government template path
const pineconeResults = $input.first().json || {};
const originalData = $('Merge Intent Data').first().json || {};
const matches = pineconeResults.matches || [];

const templateByScheme = {
  'ka-widow-pension': 'pension1.pdf',
  'ka-old-age-pension': 'pension1.pdf',
  'ka-disability-pension': 'disabledgovt.pdf',
  'ka-destitute-pension': 'pension1.pdf',
  'nsap-ignoaps': 'pension1.pdf',
  'pmjay': 'Application_for_assiatance.pdf',
  'pm-kisan': 'intimationform.pdf'
};

const templateByLegacyKey = {
  'widow_pension_karnataka.pdf': 'pension1.pdf',
  'old_age_pension_karnataka.pdf': 'pension1.pdf',
  'pmjay_enrollment.pdf': 'Application_for_assiatance.pdf'
};

const normalizeDocs = (v) => {
  if (Array.isArray(v)) return v.map(x => String(x).trim()).filter(Boolean);
  if (typeof v === 'string') return v.split(',').map(x => x.trim()).filter(Boolean);
  return [];
};

if (matches.length === 0) {
  return {
    json: {
      ...originalData,
      error: 'no_matching_documents',
      message: 'No matching document templates found',
      matched_document: null,
      documents_found: []
    }
  };
}

const topMatch = matches[0] || {};
const md = topMatch.metadata || {};
const schemeId = (md.scheme_id || originalData.scheme_id || originalData.entities?.scheme_id || '').toLowerCase();
const legacyKey = (md.storage_path || '').split('/').pop();
const pdfTemplateKey =
  md.pdf_template_key ||
  templateByScheme[schemeId] ||
  templateByLegacyKey[legacyKey] ||
  legacyKey ||
  'pension1.pdf';

return {
  json: {
    ...originalData,
    matched_document: {
      document_id: topMatch.id || null,
      similarity_score: topMatch.score || 0,
      document_name: md.document_name || md.title || md.scheme_name || 'Government Application Form',
      document_type: md.document_type || 'application_form',
      scheme_id: md.scheme_id || null,
      pdf_template_key: pdfTemplateKey,
      required_documents: normalizeDocs(md.required_documents),
      storage_path: `templates/${pdfTemplateKey}`,
      form_fields: md.form_fields || []
    },
    all_matches: matches.map(m => ({
      document_id: m.id,
      score: m.score,
      name: m.metadata?.document_name || m.metadata?.title || null
    }))
  }
};
""".strip()


SEND_RESPONSE_JS = r"""
={{ JSON.stringify({
  status: 'success',
  call_id: $json.call_id || $('Extract Transcript').first().json.call_id || null,
  intent: $json.detected_intent || $('Merge Intent Data').first().json.detected_intent || null,
  response: $json.response_text || 'Processing complete',
  best_match_scheme: {
    scheme_id: $json.matched_document?.scheme_id || null,
    scheme_name: $json.matched_document?.document_name || null,
    pdf_template_key: $json.matched_document?.pdf_template_key || null,
    required_documents: $json.matched_document?.required_documents || []
  },
  required_documents: $json.matched_document?.required_documents || [],
  missing_required_documents: [],
  document_filled: Boolean($json.storage_path),
  storage_path: $json.storage_path || null,
  household_hash: $json.household_hash || $('Extract Transcript').first().json.household_hash || null
}) }}
""".strip()


FETCH_URL_EXPR = (
    "={{ 'http://minio:9000/' + encodeURI($json.matched_document?.storage_path || "
    "('templates/' + ($json.matched_document?.pdf_template_key || 'pension1.pdf'))) }}"
)


def patch_nodes(nodes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    changed = False
    for node in nodes:
        name = node.get("name")
        params = node.setdefault("parameters", {})
        if name == "Ultravox Call Ended Webhook":
            if params.get("responseMode") != "responseNode":
                params["responseMode"] = "responseNode"
                changed = True
        elif name == "Process Document Matches":
            if params.get("jsCode") != PROCESS_MATCHES_JS:
                params["jsCode"] = PROCESS_MATCHES_JS
                changed = True
        elif name == "Fetch Document from MinIO":
            if params.get("url") != FETCH_URL_EXPR:
                params["url"] = FETCH_URL_EXPR
                changed = True
        elif name == "Send Webhook Response":
            if params.get("responseBody") != SEND_RESPONSE_JS:
                params["responseBody"] = SEND_RESPONSE_JS
                changed = True
    return nodes, changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch active n8n call-ended workflow for UI E2E.")
    parser.add_argument("--workflow-id", default="IJPL6b4yqlOayL0N")
    parser.add_argument("--host", default=os.getenv("PGHOST", "localhost"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PGPORT", "5432")))
    parser.add_argument("--db", default=os.getenv("PGDATABASE", "zelia"))
    parser.add_argument("--user", default=os.getenv("PGUSER", "zelia"))
    parser.add_argument("--password", default=os.getenv("PGPASSWORD", "zelia_secure_2024"))
    args = parser.parse_args()

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
    entity_nodes, entity_changed = patch_nodes(entity_nodes)

    if entity_changed:
        cur.execute(
            'UPDATE workflow_entity SET nodes = %s::json, "updatedAt" = NOW() WHERE id = %s',
            (json.dumps(entity_nodes, ensure_ascii=False), args.workflow_id),
        )

    history_changed = False
    if active_version_id:
        cur.execute(
            'SELECT nodes::text FROM workflow_history WHERE "versionId" = %s',
            (active_version_id,),
        )
        hrow = cur.fetchone()
        if hrow:
            hist_nodes = json.loads(hrow[0])
            hist_nodes, history_changed = patch_nodes(hist_nodes)
            if history_changed:
                cur.execute(
                    'UPDATE workflow_history SET nodes = %s::json, "updatedAt" = NOW() WHERE "versionId" = %s',
                    (json.dumps(hist_nodes, ensure_ascii=False), active_version_id),
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
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

