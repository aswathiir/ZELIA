#!/usr/bin/env python3
"""
Sync field-map JSON into generate_pdf_code.js fieldMap block.
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
    end_token = "const schemeTemplateMap = {"
    start = js_code.find(start_token)
    end = js_code.find(end_token)
    if start == -1 or end == -1 or end < start:
        raise ValueError("Could not find fieldMap block markers in generate code")
    return js_code[:start] + new_js_map + "\n\n" + js_code[end:]


def main() -> None:
    p = argparse.ArgumentParser(description="Sync field-map into generate_pdf_code.js")
    p.add_argument("--field-map", required=True)
    p.add_argument("--js-file", default="generate_pdf_code.js")
    args = p.parse_args()

    fm = json.loads(Path(args.field_map).read_text(encoding="utf-8"))
    js_path = Path(args.js_file)
    js = js_path.read_text(encoding="utf-8")
    updated = replace_field_map(js, to_js_map(fm))
    js_path.write_text(updated, encoding="utf-8")
    print(f"Wrote generate code with synced field map: {js_path}")


if __name__ == "__main__":
    main()

