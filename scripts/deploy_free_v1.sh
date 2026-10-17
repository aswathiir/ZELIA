#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

echo "[1/8] Starting core services"
docker compose up -d --build \
  postgres minio n8n retrieval-service rules-engine document-processor submission-service voice-processor || true

echo "[2/8] Applying SQL migrations"
python3 scripts/run_migrations.py --include-upgrade || true

echo "[3/8] Generating template manifest + field map (all active templates)"
python3 skills/zelia-pdf-form-audit/scripts/generate_template_manifest.py \
  --templates-dir dataset/govt/templates \
  --out data/ingestion/template_manifest_all.json
python3 skills/zelia-pdf-form-audit/scripts/generate_field_map_stubs.py \
  --manifest data/ingestion/template_manifest_all.json \
  --out data/ingestion/field_map_all_minio.json

echo "[4/8] Calibrating coordinates and syncing workflow map"
python3 scripts/calibrate_template_coordinates.py \
  --templates-dir dataset/govt/templates \
  --in-field-map data/ingestion/field_map_all_minio.json \
  --out-field-map data/ingestion/field_map_all_minio.json \
  --out-csv data/ingestion/field_map_calibration_sheet.csv
python3 scripts/sync_field_map_to_workflow.py \
  --workflow zeliaintegration_v28b_fresh.json \
  --field-map data/ingestion/field_map_all_minio.json \
  --out zeliaintegration_v28b_fresh.json

echo "[5/8] Running data readiness + production readiness checks"
python3 scripts/prepare_data_readiness.py \
  --run-ingest \
  --run-pinecone-seed || true
python3 scripts/validate_production_readiness.py || true

echo "[6/8] Running smoke checks"
bash scripts/smoke_test_free_v1.sh || true

echo "[7/8] Running E2E walkthrough (approve + reject/correction)"
REVIEW_ACTION=approve bash scripts/e2e_voice_to_chw_walkthrough.sh || true
REVIEW_ACTION=reject RUN_CORRECTION_LOOP=true bash scripts/e2e_voice_to_chw_walkthrough.sh || true

echo "[8/8] Running ASR multilingual QA (EN/HI/TA)"
python3 scripts/generate_audio_qa_samples.py \
  --manifest data/audio_qa/manifest.jsonl \
  --voice-endpoint http://localhost:8018 \
  --prefer-local-say || true
python3 scripts/asr_multilingual_qa.py \
  --manifest data/audio_qa/manifest.jsonl \
  --voice-endpoint http://localhost:8018 \
  --target-wer 0.35 \
  --asr-timeout 300 \
  --asr-retries 2 || true

echo "Deployment routine completed. Review data/ingestion/production_readiness.json and data/ingestion/asr_qa_report.json"
