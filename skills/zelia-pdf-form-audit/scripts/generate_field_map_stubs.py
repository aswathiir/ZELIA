#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

PRIORITY_FIELDS = ["name", "age", "address", "gender"]


def default_overlay(field: str):
    y_map = {"name": 700, "age": 675, "address": 650, "gender": 625}
    return {
        "page": 0,
        "x": 140,
        "y": y_map[field],
        "fontSize": 11,
        "required": True,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate field map stubs from template manifest")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    templates = {}

    for t in manifest.get("templates", []):
        key = t["template_key"]
        templates[key] = {
            "strategy": {
                "keep_original_page_1": True,
                "append_filled_data_page": True,
                "overlay_priority_fields_only": True,
            },
            "fields": {f: default_overlay(f) for f in PRIORITY_FIELDS},
            "status": "stub",
            "notes": "Adjust coordinates per template after visual verification",
        }

    output = {
        "version": "1.0",
        "priority_fields": PRIORITY_FIELDS,
        "templates": templates,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote field map stubs: {out}")
    print(f"Templates covered: {len(templates)}")


if __name__ == "__main__":
    main()
