#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path

DEFAULT_DEFERRED = {"formsandregister.pdf"}
SCANNED_HINTS = {"niramaya.pdf", "disabledgovt.pdf"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pdf_meta(path: Path):
    pages = None
    scanned = path.name.lower() in SCANNED_HINTS
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        pages = len(reader.pages)
        if reader.pages:
            text = (reader.pages[0].extract_text() or "").strip()
            if len(text) < 20:
                scanned = True
    except Exception:
        pass
    return pages, scanned


def build_manifest(templates_dir: Path, include_bundle: bool):
    templates = []
    deferred = []

    for pdf in sorted(templates_dir.glob("*.pdf")):
        name = pdf.name
        if not include_bundle and name in DEFAULT_DEFERRED:
            deferred.append(
                {
                    "template_key": name,
                    "reason": "Deferred large bundle template; not used in strict default scope",
                }
            )
            continue

        page_count, scanned = pdf_meta(pdf)
        templates.append(
            {
                "template_key": name,
                "path": str(pdf),
                "size_bytes": pdf.stat().st_size,
                "sha256": sha256_file(pdf),
                "page_count": page_count,
                "is_scanned": scanned,
                "deferred": False,
            }
        )

    return {
        "version": "1.0",
        "templates_dir": str(templates_dir),
        "include_bundle": include_bundle,
        "template_count": len(templates),
        "templates": templates,
        "deferred": deferred,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate template manifest for ZELIA PDF templates")
    parser.add_argument("--templates-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--include-bundle", action="store_true")
    args = parser.parse_args()

    templates_dir = Path(args.templates_dir)
    if not templates_dir.is_dir():
        raise SystemExit(f"templates directory not found: {templates_dir}")

    manifest = build_manifest(templates_dir, args.include_bundle)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote manifest: {out}")
    print(f"Templates included: {manifest['template_count']}")
    if manifest["deferred"]:
        print(f"Deferred templates: {', '.join(d['template_key'] for d in manifest['deferred'])}")


if __name__ == "__main__":
    main()
