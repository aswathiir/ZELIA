#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, List


def synthesize_tts(voice_endpoint: str, text: str, language: str) -> bytes:
    payload = json.dumps({"text": text, "language": language}).encode("utf-8")
    req = urllib.request.Request(
        voice_endpoint.rstrip("/") + "/tts/synthesize",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    b64 = data.get("audio_base64")
    if not b64:
        raise RuntimeError("TTS response missing audio_base64")
    return base64.b64decode(b64)


def synthesize_with_say(out_path: Path, text: str, language: str) -> bool:
    if shutil.which("say") is None:
        return False

    lang = (language or "en-IN").lower()
    voice = "Samantha"
    if lang.startswith("hi"):
        voice = "Lekha"
    elif lang.startswith("ta"):
        voice = "Vani"

    cmd = [
        "say",
        "-v",
        voice,
        "-o",
        str(out_path),
        "--data-format=LEI16@22050",
        text,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0


def load_manifest(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        rows.append(json.loads(raw))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate missing ASR QA audio samples via local TTS endpoint.")
    parser.add_argument("--manifest", default="data/audio_qa/manifest.jsonl")
    parser.add_argument("--voice-endpoint", default="http://localhost:8018")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--prefer-local-say", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")

    rows = load_manifest(manifest_path)
    created = 0
    skipped = 0
    failed: List[Dict[str, str]] = []

    for row in rows:
        rel = Path(row["audio_path"])
        out_path = rel if rel.is_absolute() else (manifest_path.parent / rel).resolve()
        if out_path.exists() and not args.overwrite:
            skipped += 1
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = row.get("reference", "")
            language = row.get("language", "en-IN")
            generated = False
            if args.prefer_local_say:
                generated = synthesize_with_say(out_path=out_path, text=text, language=language)
            if not generated:
                audio = synthesize_tts(
                    voice_endpoint=args.voice_endpoint,
                    text=text,
                    language=language,
                )
                out_path.write_bytes(audio)
            created += 1
        except Exception as exc:
            failed.append({"audio_path": str(out_path), "error": str(exc)})

    report = {
        "manifest": str(manifest_path),
        "voice_endpoint": args.voice_endpoint,
        "created": created,
        "skipped": skipped,
        "failed": failed,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
