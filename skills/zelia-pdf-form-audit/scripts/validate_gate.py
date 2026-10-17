#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

DEFAULT_FAIL = [
    "PLACEHOLDER_FALLBACK",
    "HARDCODED_TEMPLATE_KEY",
    "MISSING_PDF_TEMPLATE_KEY_SCHEMA",
    "MISSING_EXTRACTED_FIELDS",
    "FIELD_MAP_MISSING_PRIORITY",
    "UPLOAD_PATH_VERIFICATION_MISSING",
]

REQUIRED_FIELDS = ["name", "age", "address", "gender"]


def main():
    parser = argparse.ArgumentParser(description="Validate strict gates for ZELIA PDF pipeline")
    parser.add_argument("--audit", required=True)
    parser.add_argument("--field-map", required=True)
    parser.add_argument("--fail-on", default=",".join(DEFAULT_FAIL))
    args = parser.parse_args()

    fail_rules = {r.strip() for r in args.fail_on.split(",") if r.strip()}
    audit = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    field_map = json.loads(Path(args.field_map).read_text(encoding="utf-8"))

    failures = []

    for finding in audit.get("findings", []):
        if finding.get("rule_id") in fail_rules and finding.get("severity") in {"critical", "high", "medium", "low"}:
            failures.append(
                {
                    "rule_id": finding.get("rule_id"),
                    "reason": finding.get("message"),
                    "severity": finding.get("severity"),
                }
            )

    templates = field_map.get("templates", {})
    for key, cfg in templates.items():
        fields = cfg.get("fields", {})
        missing = [f for f in REQUIRED_FIELDS if f not in fields]
        bad = []
        for f in REQUIRED_FIELDS:
            if f in fields:
                obj = fields[f]
                for k in ["page", "x", "y", "fontSize"]:
                    if obj.get(k) is None:
                        bad.append(f"{f}.{k}")
        if missing or bad:
            if "FIELD_MAP_MISSING_PRIORITY" in fail_rules:
                failures.append(
                    {
                        "rule_id": "FIELD_MAP_MISSING_PRIORITY",
                        "reason": f"Template {key} missing required mapping fields: {missing}; invalid attrs: {bad}",
                        "severity": "high",
                    }
                )

    status = "pass" if not failures else "fail"
    output = {
        "status": status,
        "fail_rule_count": len(fail_rules),
        "failure_count": len(failures),
        "failures": failures,
    }

    print(json.dumps(output, indent=2))
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
