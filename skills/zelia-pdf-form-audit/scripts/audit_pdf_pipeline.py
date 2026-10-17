#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

SEVERITY = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}


def add_finding(findings, rule_id, severity, message, remediation, evidence=None, node_refs=None, file_refs=None):
    findings.append(
        {
            "id": f"F{len(findings)+1:03d}",
            "rule_id": rule_id,
            "severity": severity,
            "message": message,
            "remediation": remediation,
            "evidence": evidence or {},
            "node_refs": node_refs or [],
            "file_refs": file_refs or [],
        }
    )


def load_workflow(path: Path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    nodes = obj.get("nodes", [])
    by_name = {n.get("name", ""): n for n in nodes}
    return obj, nodes, by_name


def extract_assigned_profile_fields(js_code: str):
    fields = set()
    m = re.search(r"user_profile\s*:\s*\{([\s\S]*?)\}\s*,\s*paralinguistic", js_code)
    if m:
        block = m.group(1)
        for k in re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*:", block):
            fields.add(k)
    return fields


def extract_pdf_profile_fields(js_code: str):
    return set(re.findall(r"profile\.([a-zA-Z_][a-zA-Z0-9_]*)", js_code or ""))


def main():
    parser = argparse.ArgumentParser(description="Audit ZELIA PDF pipeline")
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--schema", required=True, help="Comma-separated SQL file paths")
    parser.add_argument("--templates-dir", required=True)
    parser.add_argument("--placeholders-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    workflow_path = Path(args.workflow)
    schema_paths = [Path(p.strip()) for p in args.schema.split(",") if p.strip()]
    templates_dir = Path(args.templates_dir)
    placeholders_dir = Path(args.placeholders_dir)

    findings = []

    _, _, by_name = load_workflow(workflow_path)

    fetch_node = by_name.get("Fetch Template")
    generate_node = by_name.get("Generate PDF (pdf-lib)")
    parse_node = by_name.get("Parse Profile + Hash")

    placeholder_keys = {p.name for p in placeholders_dir.glob("*.pdf")}
    real_keys = {p.name for p in templates_dir.glob("*.pdf")}

    fetch_params = ((fetch_node or {}).get("parameters") or {})
    file_key_expr = fetch_params.get("fileKey", "")
    if any(k in str(file_key_expr) for k in placeholder_keys):
        add_finding(
            findings,
            "PLACEHOLDER_FALLBACK",
            "critical",
            "Fetch Template contains placeholder fallback key(s).",
            "Replace placeholder fallback with mapped `pdf_template_key` from schemes table and validate key exists in real templates bucket.",
            evidence={"fileKey": file_key_expr},
            node_refs=["Fetch Template"],
            file_refs=[str(workflow_path)],
        )

    if "widow_pension_karnataka.pdf" in str(file_key_expr):
        add_finding(
            findings,
            "HARDCODED_TEMPLATE_KEY",
            "high",
            "Workflow still hardcodes widow placeholder key in template fetch expression.",
            "Remove hardcoded key and use dynamic mapping from eligibility result row.",
            evidence={"fileKey": file_key_expr},
            node_refs=["Fetch Template"],
            file_refs=[str(workflow_path)],
        )

    schema_text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in schema_paths if p.exists())
    if "pdf_template_key" not in schema_text:
        add_finding(
            findings,
            "MISSING_PDF_TEMPLATE_KEY_SCHEMA",
            "critical",
            "Schema/migrations do not define `schemes.pdf_template_key`.",
            "Add idempotent migration to introduce `pdf_template_key` and seed mappings for active schemes.",
            file_refs=[str(p) for p in schema_paths],
        )

    parse_js = ((parse_node or {}).get("parameters") or {}).get("jsCode", "")
    gen_js = ((generate_node or {}).get("parameters") or {}).get("jsCode", "")

    extracted = extract_assigned_profile_fields(parse_js)
    consumed = extract_pdf_profile_fields(gen_js)

    missing = sorted([f for f in consumed if f not in extracted])
    if missing:
        add_finding(
            findings,
            "MISSING_EXTRACTED_FIELDS",
            "high",
            "PDF renderer consumes profile fields not emitted by Parse Profile + Hash.",
            "Update extractor prompt and parser to emit missing fields, or stop consuming them in PDF generation.",
            evidence={"consumed": sorted(consumed), "extracted": sorted(extracted), "missing": missing},
            node_refs=["Parse Profile + Hash", "Generate PDF (pdf-lib)"],
            file_refs=[str(workflow_path)],
        )

    # Template key mapping in workflow SQL
    eligibility_node = by_name.get("Check Eligibility (SQL)")
    eligibility_query = ((eligibility_node or {}).get("parameters") or {}).get("query", "")
    if "pdf_template_key" not in str(eligibility_query):
        add_finding(
            findings,
            "MISSING_TEMPLATE_KEY_IN_ELIGIBILITY",
            "high",
            "Eligibility SQL does not project `pdf_template_key`.",
            "Select `s.pdf_template_key` in eligibility query and propagate it through response/build nodes.",
            evidence={"query_snippet": str(eligibility_query)[:500]},
            node_refs=["Check Eligibility (SQL)"],
            file_refs=[str(workflow_path)],
        )

    # Upload verification check
    upload_node = by_name.get("Upload to MinIO")
    upload_ok = False
    if upload_node:
        p = upload_node.get("parameters") or {}
        upload_ok = bool(p.get("bucketName") and p.get("fileName"))
    if not upload_ok:
        add_finding(
            findings,
            "UPLOAD_PATH_VERIFICATION_MISSING",
            "high",
            "Upload path verification evidence missing or incomplete in Upload to MinIO node.",
            "Ensure upload node has bucket/file path parameters and add explicit post-upload response check.",
            node_refs=["Upload to MinIO"],
            file_refs=[str(workflow_path)],
        )

    # Info: deferred bundle template
    if "formsandregister.pdf" in real_keys:
        add_finding(
            findings,
            "BUNDLE_TEMPLATE_DEFERRED",
            "info",
            "formsandregister.pdf detected and treated as deferred bundle by default strict scope.",
            "Keep deferred unless explicitly opting in with dedicated mapping and performance validation.",
            file_refs=[str(templates_dir / "formsandregister.pdf")],
        )

    findings.sort(key=lambda f: SEVERITY[f["severity"]], reverse=True)

    summary = {
        "critical": sum(1 for f in findings if f["severity"] == "critical"),
        "high": sum(1 for f in findings if f["severity"] == "high"),
        "medium": sum(1 for f in findings if f["severity"] == "medium"),
        "low": sum(1 for f in findings if f["severity"] == "low"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
        "total": len(findings),
    }

    report = {
        "version": "1.0",
        "workflow": str(workflow_path),
        "schema_files": [str(p) for p in schema_paths],
        "templates_dir": str(templates_dir),
        "placeholders_dir": str(placeholders_dir),
        "summary": summary,
        "strict_ready": summary["critical"] == 0 and summary["high"] == 0,
        "findings": findings,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote audit report: {out}")
    print(f"Findings: {summary['total']} (critical={summary['critical']}, high={summary['high']})")


if __name__ == "__main__":
    main()
