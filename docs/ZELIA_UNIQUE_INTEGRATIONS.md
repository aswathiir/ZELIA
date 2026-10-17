# ZELIA Unique Integrations Report

This report is generated from the current codebase and highlights integrations that make the project unique.

## Canonical Voice-to-Action Workflow
- Source: `zeliaintegration_v28b_fresh.json`
- Implemented node: `Ultravox Webhook`
- Implemented node: `Extract Profile (Groq)`
- Implemented node: `Parse Profile + Hash`
- Implemented node: `RAG Hybrid Search`
- Implemented node: `Prepare RAG Filter`
- Implemented node: `Check Eligibility (SQL)`
- Implemented node: `Fetch Template`
- Implemented node: `Generate PDF (pdf-lib)`

## Unique Integrations
- Voice intake is connected to scheme retrieval and document output in one flow, not a chat-only bot.
- Eligibility combines semantic retrieval (RAG/Pinecone) with deterministic SQL/rule checks.
- PDF generation supports real government templates with per-template coordinate maps and page-2 structured fallback.
- CHW verification is a first-class lifecycle (`pending_review -> approved/rejected`) with API-backed console actions.
- Audit skill enforces strict release gates for template mapping and data propagation.

## Service Contracts
- Voice Processor: `backend/services/voice-processor/main.py`
  - `GET /health`
  - `GET /asr/health`
  - `POST /asr/transcribe`
  - `POST /asr/transcribe-file`
  - `POST /tts/synthesize`
  - `POST /voice/process`
  - `POST /process`
  - `GET /transcript/{call_id}`
- Rules Engine: `backend/services/rules-engine/rules_service.py`
  - `GET /health`
  - `POST /evaluate`
  - `POST /batch-evaluate`
  - `POST /check-eligibility`
- Retrieval Service: `backend/services/retrieval-service/retrieval_service.py`
  - `GET /health`
  - `POST /embed`
  - `POST /embed-query`
  - `POST /search`
  - `POST /search/hybrid`
  - `POST /rebuild-index`
  - `GET /stats`
- Submission Service: `backend/services/submission-service/main.py`
  - `GET /health`
  - `POST /sync`
  - `GET /submissions/{submission_id}`
  - `GET /submissions`
  - `POST /submissions/{submission_id}/review`
  - `POST /submissions/{submission_id}/correction`
  - `POST /log-interaction`

## Data Integrity and Readiness
- `schemes.pdf_template_key` mapping and CHW review columns are present in migration set.
- Field-map artifacts exist under `data/ingestion/` and can be synchronized into workflow code.
- Production readiness checks and smoke scripts are provided under `scripts/`.

