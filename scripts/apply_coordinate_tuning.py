#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="Apply edited calibration CSV into field_map JSON.")
    p.add_argument("--field-map", required=True)
    p.add_argument("--csv", required=True, help="Edited calibration CSV")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    fm = json.loads(Path(args.field_map).read_text(encoding="utf-8"))
    templates = fm.setdefault("templates", {})

    with Path(args.csv).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row.get("template_key") or "").strip()
            field = (row.get("field") or "").strip()
            if not key or not field:
                continue
            if key not in templates:
                templates[key] = {"strategy": {"overlay_priority_fields_only": True}, "fields": {}, "status": "stub"}
            fields = templates[key].setdefault("fields", {})
            fields[field] = {
                "page": int(float(row.get("page", 0) or 0)),
                "x": float(row.get("x", 0) or 0),
                "y": float(row.get("y", 0) or 0),
                "fontSize": float(row.get("fontSize", 11) or 11),
                "required": True,
            }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(fm, indent=2), encoding="utf-8")
    print(f"Wrote tuned field map: {out}")


if __name__ == "__main__":
    main()

