#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "[1/9] Production readiness validation"
python3 scripts/validate_production_readiness.py

echo "[2/9] Data readiness validation (ingest + Pinecone seed)"
python3 scripts/prepare_data_readiness.py --run-ingest --run-pinecone-seed

echo "[3/9] Retrieval fallback check"
python3 scripts/test_retrieval_fallback.py

echo "[4/9] PDF audit"
python3 skills/zelia-pdf-form-audit/scripts/audit_pdf_pipeline.py \
  --workflow zeliaintegration_v28b_fresh.json \
  --schema schema_v28_upgrade.sql \
  --templates-dir dataset/govt/templates \
  --placeholders-dir data/forms \
  --out data/ingestion/final_audit.json

echo "[5/9] Strict gate validation"
python3 skills/zelia-pdf-form-audit/scripts/validate_gate.py \
  --audit data/ingestion/final_audit.json \
  --field-map data/ingestion/field_map_top5_calibrated.json

echo "[6/9] Smoke test"
bash scripts/smoke_test_free_v1.sh

echo "[7/9] E2E walkthrough (approve)"
REVIEW_ACTION=approve bash scripts/e2e_voice_to_chw_walkthrough.sh

echo "[8/9] E2E walkthrough (reject + correction)"
REVIEW_ACTION=reject RUN_CORRECTION_LOOP=true MISSING_FIELDS=address bash scripts/e2e_voice_to_chw_walkthrough.sh

echo "[9/9] ASR multilingual QA (EN/HI/TA)"
python3 scripts/generate_audio_qa_samples.py \
  --manifest data/audio_qa/manifest.jsonl \
  --voice-endpoint http://localhost:8018 \
  --prefer-local-say
python3 scripts/asr_multilingual_qa.py \
  --manifest data/audio_qa/manifest.jsonl \
  --voice-endpoint http://localhost:8018 \
  --target-wer 0.35 \
  --asr-timeout 300 \
  --asr-retries 2

echo "Strict E2E gate PASSED"
