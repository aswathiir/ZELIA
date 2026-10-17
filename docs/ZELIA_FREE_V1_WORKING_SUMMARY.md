# ZELIA Free v1 - Working Summary

This document summarizes what is implemented in the project and how the end-to-end pipeline works today.

## 1) Core Goal

ZELIA takes voice input, identifies eligible welfare schemes using retrieval + rules, generates filled government-form PDFs, stores artifacts in object storage, and routes submissions for CHW review.

## 2) Canonical Workflow and Data Path

Canonical n8n flow:

- `zeliaintegration_v28b_fresh.json`

Pipeline stages in this workflow:

1. `Ultravox Webhook`
- Ingests call-ended payload with transcript messages.

2. `Extract Profile (Groq)`
- Extracts structured profile, including `name`, `age`, `gender`, `address`, `district`, `monthly_income`, `marital_status`, `state_code`, etc.

3. `Parse Profile + Hash`
- Normalizes profile and prepares contracts for downstream nodes.

4. `RAG Hybrid Search` + `Prepare RAG Filter`
- Queries retrieval service and builds `rag_scheme_ids`.
- If retrieval is unavailable and mandatory, workflow follows controlled failure path.

5. `Check Eligibility (SQL)`
- Filters schemes by state (`ALL` + profile state), optional RAG scheme IDs, and deterministic eligibility conditions.
- Includes `pdf_template_key` in selected results.

6. Response building
- Generates user-facing response from eligible scheme metadata.

7. `Fetch Template`
- Dynamically fetches template using `pdf_template_key` (production mapping, not hardcoded placeholder).

8. `Generate PDF (pdf-lib)`
- Page 1 overlay of priority fields (`name`, `age`, `address`, `gender`) using template-aware coordinates.
- Appends a structured “Filled Application Data” page with complete extracted profile and scheme summary.

9. Upload and return
- Uploads generated file and returns execution output.

## 3) Services and Responsibilities

### 3.1 Retrieval Service (RAG)
- File: `backend/services/retrieval-service/retrieval_service.py`
- Runs hybrid retrieval with Pinecone-first + Annoy fallback path.
- `RETRIEVAL_MODE=pinecone_primary_annoy_fallback` and `PINECONE_REQUIRED=false` defaults support partial offline operation.
- `/search/hybrid` returns deterministic metadata: `retrieval_mode`, `source_used`, `result_count`, `results`.

### 3.2 Rules Engine
- File: `backend/services/rules-engine/rules_service.py`
- Primary endpoint: `POST /evaluate`
- Compatibility endpoint: `POST /check-eligibility` (maps legacy payloads to evaluate logic).

### 3.3 Submission Service (CHW lifecycle)
- File: `backend/services/submission-service/main.py`
- Supports:
  - `POST /sync` -> creates `pending_review` record and uploads evidence to MinIO
  - `GET /submissions`
  - `GET /submissions/{submission_id}`
  - `POST /submissions/{submission_id}/review` (`approve`/`reject`)
  - `POST /submissions/{submission_id}/correction` -> resubmits corrected fields and re-queues `pending_review`
- Security baseline:
  - Role-based header enforcement (`X-User-Role`) for CHW endpoints
  - Hashed identifiers for user pathing/storage references

### 3.4 Voice Processor (offline contracts)
- File: `backend/services/voice-processor/main.py`
- Endpoints:
  - `POST /asr/transcribe`
  - `POST /tts/synthesize`
  - `POST /voice/process`
- Behavior:
  - Supports transcript-based local processing.
  - Optional audio-base64 ASR via faster-whisper if available.
  - TTS uses local engine with deterministic fallback payload for contract stability.

## 4) CHW Console Integration

Frontend files:

- `frontend/chw-console/api.js`
- `frontend/chw-console/app.js`
- `frontend/chw-console/voice-input-integrated.js`

Implemented behavior:

- Calls rules-engine compatibility endpoint.
- Loads real submissions from API and performs review actions.
- Uses local voice processor before webhook submission.
- Speaks summary via local TTS endpoint (fallback to browser speech synthesis).

## 5) Data and Mapping Assets

### 5.1 Templates
- Real templates source:
  - `dataset/govt/templates`

### 5.2 Template manifest and field map artifacts
- `data/ingestion/template_manifest_top5.json`
- `data/ingestion/field_map_top5.json`

### 5.3 Ingestion and seeding scripts
- `scripts/ingest_top_states_to_supabase.py`
- `scripts/seed_pinecone_top_states.py`

## 6) Schema and Migration State

Primary schema/migration files:

- `supabase_Schema.sql`
- `schema_v28_upgrade.sql`
- `database/migrations/008_submission_review_workflow.sql`
- `skills/zelia-pdf-form-audit/references/sql/001_add_pdf_template_key.sql`

Implemented schema expectations:

- `schemes.pdf_template_key` available and used.
- Submission review metadata columns available for CHW decision path.

## 7) Audit and Release Gates

Audit skill:

- `skills/zelia-pdf-form-audit`

Recent audit artifact:

- `data/ingestion/zelia_audit_after_rest_integration.json`

Gate script:

- `validate_gate.py` verifies placeholder removal, template mapping contract, required extraction fields, and field-map priority coverage.

## 8) E2E Walkthrough Command

Runnable walkthrough script:

- `scripts/e2e_voice_to_chw_walkthrough.sh`

It executes:

1. Voice preprocess (`/voice/process`)
2. Canonical webhook execution (`/webhook/ultravox/call-ended`)
3. Submission create (`/sync`, status `pending_review`)
4. CHW action (`/submissions/{id}/review`)
5. Optional correction requeue (`/submissions/{id}/correction`)
6. Post-action fetch (`approved`/`rejected`/requeued)

Output folder:

- `data/ingestion/e2e_walkthrough`

## 9) What remains manual/operational

1. Pixel-perfect coordinate tuning per template still needs visual calibration.
2. Production deployment requires all services up, keys configured, and migrations applied.
3. Real speech-audio ASR quality depends on optional faster-whisper runtime availability.

## 10) Implemented to reduce manual overhead

The following automations were added to operationalize the above:

1. Coordinate calibration workflow
- `scripts/calibrate_template_coordinates.py`
- `scripts/sync_field_map_to_workflow.py`
- Artifacts:
  - `data/ingestion/field_map_top5_calibrated.json`
  - `data/ingestion/field_map_calibration_sheet.csv`

2. Production readiness automation
- `scripts/validate_production_readiness.py`
- `scripts/deploy_free_v1.sh`

3. ASR operational hardening
- `backend/services/voice-processor/main.py`
- Added:
  - `GET /asr/health`
  - `POST /asr/transcribe-file`
  - strict mode with `ASR_STRICT`
  - configurable decode/transcribe params (`WHISPER_*`)
  - data-url audio handling and mime-aware temporary extension handling.

4. Data and migration readiness automation
- `scripts/run_migrations.py`
- `scripts/prepare_data_readiness.py`
- `scripts/asr_multilingual_qa.py`
- `scripts/strict_e2e_gate.sh`
