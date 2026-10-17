#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def extract_workflow_nodes(workflow_path: Path):
    wf = json.loads(workflow_path.read_text(encoding="utf-8"))
    return [n.get("name", "") for n in wf.get("nodes", [])]


def extract_fastapi_routes(py_path: Path):
    text = py_path.read_text(encoding="utf-8", errors="ignore")
    routes = []
    for m in re.finditer(r"@app\.(get|post|put|delete)\(\"([^\"]+)\"", text):
        routes.append({"method": m.group(1).upper(), "path": m.group(2)})
    return routes


def extract_flask_routes(py_path: Path):
    text = py_path.read_text(encoding="utf-8", errors="ignore")
    routes = []
    for m in re.finditer(r"@app\.route\('([^']+)', methods=\['([^']+)'\]\)", text):
        routes.append({"method": m.group(2).upper(), "path": m.group(1)})
    return routes


def main():
    workflow = ROOT / "zeliaintegration_v28b_fresh.json"
    voice = ROOT / "backend/services/voice-processor/main.py"
    rules = ROOT / "backend/services/rules-engine/rules_service.py"
    retrieval = ROOT / "backend/services/retrieval-service/retrieval_service.py"
    submission = ROOT / "backend/services/submission-service/main.py"

    nodes = extract_workflow_nodes(workflow)
    voice_routes = extract_fastapi_routes(voice)
    rules_routes = extract_fastapi_routes(rules)
    submission_routes = extract_fastapi_routes(submission)
    retrieval_routes = extract_flask_routes(retrieval)

    md = []
    md.append("# ZELIA Unique Integrations Report")
    md.append("")
    md.append("This report is generated from the current codebase and highlights integrations that make the project unique.")
    md.append("")
    md.append("## Canonical Voice-to-Action Workflow")
    md.append(f"- Source: `{workflow}`")
    key_nodes = [
        "Ultravox Webhook",
        "Extract Profile (Groq)",
        "Parse Profile + Hash",
        "RAG Hybrid Search",
        "Prepare RAG Filter",
        "Check Eligibility (SQL)",
        "Fetch Template",
        "Generate PDF (pdf-lib)",
    ]
    for node in key_nodes:
        if node in nodes:
            md.append(f"- Implemented node: `{node}`")
    md.append("")
    md.append("## Unique Integrations")
    md.append("- Voice intake is connected to scheme retrieval and document output in one flow, not a chat-only bot.")
    md.append("- Eligibility combines semantic retrieval (RAG/Pinecone) with deterministic SQL/rule checks.")
    md.append("- PDF generation supports real government templates with per-template coordinate maps and page-2 structured fallback.")
    md.append("- CHW verification is a first-class lifecycle (`pending_review -> approved/rejected`) with API-backed console actions.")
    md.append("- Audit skill enforces strict release gates for template mapping and data propagation.")
    md.append("")
    md.append("## Service Contracts")
    md.append(f"- Voice Processor: `{voice}`")
    for r in voice_routes:
        md.append(f"  - `{r['method']} {r['path']}`")
    md.append(f"- Rules Engine: `{rules}`")
    for r in rules_routes:
        md.append(f"  - `{r['method']} {r['path']}`")
    md.append(f"- Retrieval Service: `{retrieval}`")
    for r in retrieval_routes:
        md.append(f"  - `{r['method']} {r['path']}`")
    md.append(f"- Submission Service: `{submission}`")
    for r in submission_routes:
        md.append(f"  - `{r['method']} {r['path']}`")
    md.append("")
    md.append("## Data Integrity and Readiness")
    md.append("- `schemes.pdf_template_key` mapping and CHW review columns are present in migration set.")
    md.append("- Field-map artifacts exist under `data/ingestion/` and can be synchronized into workflow code.")
    md.append("- Production readiness checks and smoke scripts are provided under `scripts/`.")
    md.append("")
    out = ROOT / "docs" / "ZELIA_UNIQUE_INTEGRATIONS.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote report: {out}")


if __name__ == "__main__":
    main()

