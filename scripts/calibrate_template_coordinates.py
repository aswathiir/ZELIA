#!/usr/bin/env python3
"""
Generate a calibration workbook for template coordinate tuning.

This does not guess pixel-perfect field locations. It creates a deterministic
per-template baseline using page dimensions and writes:
1) a calibration CSV for manual tuning
2) an updated field-map JSON with normalized defaults by page size
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Dict, Tuple

PRIORITY_FIELDS = ("name", "age", "address", "gender")
LABEL_ALIASES = {
    "name": ("name", "applicant", "beneficiary"),
    "age": ("age", "dob", "years"),
    "address": ("address", "residence", "residential", "village", "street"),
    "gender": ("gender", "sex", "male", "female"),
}


def read_page_size(pdf_path: Path) -> Tuple[float, float]:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            return (595.0, 842.0)  # A4 fallback
        box = reader.pages[0].mediabox
        return (float(box.width), float(box.height))
    except Exception:
        return (595.0, 842.0)


def baseline_positions(width: float, height: float) -> Dict[str, Dict[str, float]]:
    # Percentage anchors keep overlays roughly proportional across page sizes.
    x = round(width * 0.23, 2)
    return {
        "name": {"page": 0, "x": x, "y": round(height * 0.83, 2), "fontSize": 11, "required": True},
        "age": {"page": 0, "x": x, "y": round(height * 0.80, 2), "fontSize": 11, "required": True},
        "address": {"page": 0, "x": x, "y": round(height * 0.77, 2), "fontSize": 11, "required": True},
        "gender": {"page": 0, "x": x, "y": round(height * 0.74, 2), "fontSize": 11, "required": True},
    }


def _norm_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def detect_label_anchors(pdf_path: Path, width: float, height: float) -> Dict[str, Dict[str, float]]:
    """
    Heuristic anchor detection:
    find known label words and place value X slightly to the right of the label.
    Returns only detected fields; caller can fallback to baseline for missing fields.
    """
    out: Dict[str, Dict[str, float]] = {}
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(str(pdf_path)) as pdf:
            if not pdf.pages:
                return out
            p = pdf.pages[0]
            words = p.extract_words() or []
            for field, aliases in LABEL_ALIASES.items():
                match = None
                for w in words:
                    token = _norm_token(w.get("text", ""))
                    if any(a in token for a in aliases):
                        match = w
                        break
                if not match:
                    continue
                x = float(match.get("x1", 0.0)) + 12.0
                top = float(match.get("top", 0.0))
                bottom = float(match.get("bottom", top))
                y = height - ((top + bottom) / 2.0)
                out[field] = {
                    "page": 0,
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "fontSize": 11,
                    "required": True,
                }
    except Exception:
        return out
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Build calibration workbook and tuned field map.")
    p.add_argument("--templates-dir", required=True)
    p.add_argument("--in-field-map", required=True, help="Input field map JSON")
    p.add_argument("--out-field-map", required=True, help="Output field map JSON")
    p.add_argument("--out-csv", required=True, help="Calibration CSV output path")
    args = p.parse_args()

    templates_dir = Path(args.templates_dir)
    in_map_path = Path(args.in_field_map)
    out_map_path = Path(args.out_field_map)
    out_csv_path = Path(args.out_csv)

    data = json.loads(in_map_path.read_text(encoding="utf-8"))
    templates = data.get("templates", {})

    rows = []
    for template_key, cfg in templates.items():
        pdf_path = templates_dir / template_key
        width, height = read_page_size(pdf_path)
        base = baseline_positions(width, height)
        auto = detect_label_anchors(pdf_path, width, height)
        cfg.setdefault("strategy", {})
        cfg["strategy"]["overlay_priority_fields_only"] = True
        cfg["strategy"]["coordinate_source"] = "auto_detect+baseline"
        cfg.setdefault("fields", {})

        for field in PRIORITY_FIELDS:
            current = cfg["fields"].get(field, {})
            fallback = auto.get(field) or base[field]
            merged = {
                "page": int(current.get("page", fallback["page"])),
                "x": float(current.get("x", fallback["x"])),
                "y": float(current.get("y", fallback["y"])),
                "fontSize": float(current.get("fontSize", fallback["fontSize"])),
                "required": bool(current.get("required", True)),
            }
            cfg["fields"][field] = merged
            rows.append(
                {
                    "template_key": template_key,
                    "field": field,
                    "page": merged["page"],
                    "x": merged["x"],
                    "y": merged["y"],
                    "fontSize": merged["fontSize"],
                    "page_width": width,
                    "page_height": height,
                    "status": cfg.get("status", "stub"),
                    "notes": (
                        "auto-detected from label anchors"
                        if field in auto
                        else "baseline fallback; adjust x/y and re-run sync_field_map_to_workflow.py"
                    ),
                }
            )

    out_map_path.parent.mkdir(parents=True, exist_ok=True)
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)
    out_map_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    with out_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "template_key",
                "field",
                "page",
                "x",
                "y",
                "fontSize",
                "page_width",
                "page_height",
                "status",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote tuned field map: {out_map_path}")
    print(f"Wrote calibration sheet: {out_csv_path}")


if __name__ == "__main__":
    main()
