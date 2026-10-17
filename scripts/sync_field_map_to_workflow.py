#!/usr/bin/env python3
"""
Inject field-map coordinates into the Generate PDF (pdf-lib) node in workflow JSON.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def to_js_map(field_map: dict) -> str:
    templates = field_map.get("templates", {})
    lines = ["const fieldMap = {"]
    for template_key in sorted(templates.keys()):
        fields = templates[template_key].get("fields", {})
        parts = []
        for field_name in ("name", "age", "address", "gender"):
            pos = fields.get(field_name, {})
            parts.append(
                f"{field_name}: {{ page: {int(pos.get('page', 0))}, x: {float(pos.get('x', 140))}, y: {float(pos.get('y', 650))}, fontSize: {float(pos.get('fontSize', 11))} }}"
            )
        lines.append(f"  '{template_key}': {{ {', '.join(parts)} }},")
    lines.append("};")
    return "\n".join(lines)


def replace_field_map(js_code: str, new_js_map: str) -> str:
    start_token = "const fieldMap = {"
    end_tokens = [
        "const schemeTemplateMap = {",
        "const defaultOverlay = fieldMap['pension1.pdf'];",
    ]
    start = js_code.find(start_token)
    end = -1
    for token in end_tokens:
        idx = js_code.find(token)
        if idx != -1 and idx > start:
            end = idx
            break
    if start == -1 or end == -1 or end < start:
        raise ValueError("Could not find fieldMap block markers in workflow jsCode")
    return js_code[:start] + new_js_map + "\n\n" + js_code[end:]


def main() -> None:
    p = argparse.ArgumentParser(description="Sync field-map JSON into n8n workflow jsCode.")
    p.add_argument("--workflow", required=True)
    p.add_argument("--field-map", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    wf_path = Path(args.workflow)
    out_path = Path(args.out)
    fm_path = Path(args.field_map)

    wf = json.loads(wf_path.read_text(encoding="utf-8"))
    field_map = json.loads(fm_path.read_text(encoding="utf-8"))
    new_js_map = to_js_map(field_map)

    updated = False
    for node in wf.get("nodes", []):
        if node.get("name") == "Generate PDF (pdf-lib)":
            params = node.setdefault("parameters", {})
            js_code = params.get("jsCode", "")
            params["jsCode"] = replace_field_map(js_code, new_js_map)
            updated = True
            break

    if not updated:
        raise SystemExit("Generate PDF (pdf-lib) node not found")

    out_path.write_text(json.dumps(wf, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote synced workflow: {out_path}")


if __name__ == "__main__":
    main()
