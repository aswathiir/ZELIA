#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

from minio import Minio
from pypdf import PdfReader

PRIORITY_FIELDS = ("name", "age", "address", "gender")
ALIASES = {
    "name": ("name", "applicant", "pensioner", "beneficiary"),
    "age": ("age", "dob", "retirement"),
    "address": ("address", "residence", "registered", "office", "village", "street"),
    "gender": ("gender", "sex", "male", "female"),
}


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def has_alias(text: str, alias: str) -> bool:
    t = (text or "").lower()
    if alias in {"name", "age", "sex"}:
        return re.search(rf"\b{re.escape(alias)}\b", t) is not None
    return alias in t


def page_size(pdf_path: Path) -> Tuple[float, float]:
    r = PdfReader(str(pdf_path))
    if not r.pages:
        return (595.0, 842.0)
    b = r.pages[0].mediabox
    return (float(b.width), float(b.height))


def baseline(width: float, height: float) -> Dict[str, Dict[str, float]]:
    x = round(width * 0.68, 2)
    return {
        "name": {"page": 0, "x": x, "y": round(height * 0.84, 2), "fontSize": 11.0, "required": True},
        "age": {"page": 0, "x": x, "y": round(height * 0.80, 2), "fontSize": 11.0, "required": True},
        "address": {"page": 0, "x": x, "y": round(height * 0.76, 2), "fontSize": 11.0, "required": True},
        "gender": {"page": 0, "x": x, "y": round(height * 0.72, 2), "fontSize": 11.0, "required": True},
    }


def detect_words(pdf_path: Path, width: float, height: float) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    # Try pdfplumber first for proper bounding boxes.
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(str(pdf_path)) as pdf:
            if not pdf.pages:
                return out
            words = pdf.pages[0].extract_words() or []
            for field, aliases in ALIASES.items():
                hit = None
                for w in words:
                    token = w.get("text", "")
                    if any(has_alias(token, a) for a in aliases):
                        hit = w
                        break
                if not hit:
                    continue
                # Place value in blank space to right side of label row.
                x = max(float(hit.get("x1", 0.0)) + 16.0, width * 0.68)
                x = min(x, width - 110.0)
                y = height - ((float(hit.get("top", 0.0)) + float(hit.get("bottom", 0.0))) / 2.0)
                out[field] = {
                    "page": 0,
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "fontSize": 11.0,
                    "required": True,
                }
    except Exception:
        pass

    if out:
        return out

    # Fallback: use pypdf text visitor coordinates.
    try:
        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            return out
        page = reader.pages[0]
        lines: List[Tuple[float, float, str]] = []

        def visitor(text, cm, tm, font_dict, font_size):  # noqa: ANN001
            t = (text or "").strip()
            if not t:
                return
            x = float(tm[4])
            y = float(tm[5])
            clean = " ".join(t.split())
            lines.append((y, x, clean))

        page.extract_text(visitor_text=visitor)
        # Higher y appears earlier on page.
        lines.sort(key=lambda v: (-v[0], v[1]))

        # Prefer top "name" anchor first, then restrict other matches to nearby band.
        name_hit = None
        for y, x, t in lines:
            if any(has_alias(t, a) for a in ALIASES["name"]):
                name_hit = (y, x, t)
                break

        for field, aliases in ALIASES.items():
            hit = None
            candidates = lines
            if name_hit and field != "name":
                name_y = float(name_hit[0])
                # Keep search in same form section near name row.
                candidates = [row for row in lines if (name_y - 260.0) <= row[0] <= (name_y + 20.0)]
            for y, x, t in candidates:
                if any(has_alias(t, a) for a in aliases):
                    hit = (y, x, t)
                    break
            if not hit:
                continue
            y, x, text_line = hit
            est_right = x + min(280.0, max(40.0, len(text_line) * 4.5))
            val_x = max(width * 0.68, est_right + 12.0)
            val_x = min(val_x, width - 110.0)
            out[field] = {
                "page": 0,
                "x": round(val_x, 2),
                "y": round(y, 2),
                "fontSize": 11.0,
                "required": True,
            }
    except Exception:
        return out
    return out


def infer_fields(pdf_path: Path) -> Tuple[Dict[str, Dict[str, float]], str]:
    w, h = page_size(pdf_path)
    base = baseline(w, h)
    det = detect_words(pdf_path, w, h)
    fields: Dict[str, Dict[str, float]] = {}
    for f in PRIORITY_FIELDS:
        fields[f] = det.get(f, base[f])
    det_count = len(det)
    status = "auto_detected" if det_count == 4 else ("partial_auto_detected" if det_count > 0 else "baseline")
    return fields, status


def main() -> None:
    p = argparse.ArgumentParser(description="Build field map for all PDFs in MinIO templates bucket.")
    p.add_argument("--endpoint", default="localhost:9000")
    p.add_argument("--access-key", default="minioadmin")
    p.add_argument("--secret-key", default="minioadmin")
    p.add_argument("--bucket", default="templates")
    p.add_argument("--secure", action="store_true")
    p.add_argument("--out", default="data/ingestion/field_map_all_minio.json")
    args = p.parse_args()

    client = Minio(
        args.endpoint,
        access_key=args.access_key,
        secret_key=args.secret_key,
        secure=args.secure,
    )

    keys = [
        o.object_name
        for o in client.list_objects(args.bucket, recursive=True)
        if o.object_name.lower().endswith(".pdf")
    ]
    keys = sorted(keys)

    out = {
        "version": "1.1",
        "priority_fields": list(PRIORITY_FIELDS),
        "templates": {},
    }

    with tempfile.TemporaryDirectory(prefix="zelia_templates_") as td:
        td_path = Path(td)
        for key in keys:
            local = td_path / Path(key).name
            client.fget_object(args.bucket, key, str(local))
            fields, status = infer_fields(local)
            out["templates"][Path(key).name] = {
                "strategy": {
                    "overlay_priority_fields_only": True,
                    "coordinate_source": "label_anchor+baseline",
                },
                "fields": fields,
                "status": status,
                "notes": "Auto-generated from current MinIO template object; visually calibrate if needed.",
            }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"templates": len(keys), "out": str(out_path)}, indent=2))


if __name__ == "__main__":
    main()
