#!/usr/bin/env bash
set -euo pipefail

# ZELIA E2E Walkthrough:
# voice transcript -> n8n eligibility/pdf -> submission -> CHW review -> optional correction loop

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/data/ingestion/e2e_walkthrough"
mkdir -p "${OUT_DIR}"

CALL_ID="${CALL_ID:-walkthrough_call_$(date +%s)}"
LANGUAGE="${LANGUAGE:-en-IN}"
TRANSCRIPT_TEXT="${TRANSCRIPT_TEXT:-My name is Lakshmi. I am 65 years old, widowed, from Mysuru district in Karnataka. My monthly income is 3000 rupees. My address is Kuvempunagar Mysuru.}"
CHW_ID="${CHW_ID:-CHW_12345}"
REVIEW_ACTION="${REVIEW_ACTION:-approve}" # approve | reject
REVIEW_REASON="${REVIEW_REASON:-Verified with supporting documents}"
MISSING_FIELDS="${MISSING_FIELDS:-address}"
RUN_CORRECTION_LOOP="${RUN_CORRECTION_LOOP:-false}"
WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:5678/webhook/ultravox/call-ended}"
VOICE_URL="${VOICE_URL:-http://localhost:8018}"
SUBMISSION_URL="${SUBMISSION_URL:-http://localhost:8009}"

if [[ "${REVIEW_ACTION}" != "approve" && "${REVIEW_ACTION}" != "reject" ]]; then
  echo "REVIEW_ACTION must be approve or reject"
  exit 1
fi

echo "[1/8] Voice pre-processing (offline contract)"
curl -fsS -X POST "${VOICE_URL}/voice/process" \
  -H "Content-Type: application/json" \
  -d "{
    \"call_id\": \"${CALL_ID}\",
    \"language\": \"${LANGUAGE}\",
    \"transcript_text\": \"${TRANSCRIPT_TEXT}\"
  }" > "${OUT_DIR}/01_voice_process.json"

echo "[2/8] Trigger canonical n8n flow"
curl -fsS -X POST "${WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d "{
    \"call_id\": \"${CALL_ID}\",
    \"customer_number\": \"+919999999999\",
    \"duration_secs\": 55,
    \"status\": \"completed\",
    \"language\": \"en\",
    \"messages\": [
      {\"role\": \"user\", \"text\": \"${TRANSCRIPT_TEXT}\"}
    ],
    \"metadata\": {
      \"confidence\": 0.92,
      \"tone\": \"positive\",
      \"urgency\": \"normal\",
      \"citizen_id\": \"citizen_demo\"
    }
  }" > "${OUT_DIR}/02_n8n_response.json"

echo "[3/8] Create demo verified document"
DOC_PATH="${OUT_DIR}/supporting_document.txt"
cat > "${DOC_PATH}" <<EOF
Applicant: Lakshmi
Call ID: ${CALL_ID}
Document: Income and identity proof
Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

echo "[4/8] Create submission (pending_review)"
SYNC_RESP_PATH="${OUT_DIR}/03_submission_sync.json"
curl -fsS -X POST "${SUBMISSION_URL}/sync" \
  -H "X-User-Role: system" \
  -F "file=@${DOC_PATH};type=text/plain" \
  -F "user_id=${CHW_ID}" \
  -F "metadata={\"household_hash\":\"hh_${CALL_ID}\",\"scheme_id\":\"ka-old-age-pension\",\"applicant_name\":\"Lakshmi\",\"required_documents\":[\"aadhaar\",\"income_certificate\"],\"user_profile\":{\"name\":\"Lakshmi\",\"age\":64,\"date_of_birth\":\"12-04-1961\",\"aadhaar_number\":\"123412341234\",\"annual_income\":36000,\"address\":\"Kuvempunagar Mysuru Karnataka\",\"gender\":\"female\"},\"filled_pdf_uri\":\"filled-forms/${CALL_ID}/ka-old-age-pension.pdf\"}" \
  > "${SYNC_RESP_PATH}"

SUBMISSION_ID="$(python3 - <<'PY' "${SYNC_RESP_PATH}"
import json,sys
data=json.load(open(sys.argv[1]))
print(data.get("submission_id",""))
PY
)"

if [[ -z "${SUBMISSION_ID}" ]]; then
  echo "Could not parse submission_id from ${SYNC_RESP_PATH}"
  exit 1
fi

echo "[5/8] Fetch submission details"
curl -fsS -H "X-User-Role: chw" "${SUBMISSION_URL}/submissions/${SUBMISSION_ID}" > "${OUT_DIR}/04_submission_before_review.json"

echo "[5.1/8] Document consistency validation"
curl -fsS -X POST "${SUBMISSION_URL}/submissions/${SUBMISSION_ID}/validate-documents" \
  -H "Content-Type: application/json" \
  -H "X-User-Role: chw" \
  -d "{
    \"auto_correct_form\": false,
    \"documents\": [
      {
        \"document_type\": \"aadhaar\",
        \"raw_image_uri\": \"minio://verified-docs/hh_${CALL_ID}/aadhaar.txt\",
        \"extracted_json\": {
          \"name\": \"Lakshmi\",
          \"date_of_birth\": \"12-04-1961\",
          \"gender\": \"female\",
          \"address\": \"Kuvempunagar Mysuru Karnataka\",
          \"aadhaar_number\": \"123412341234\"
        }
      },
      {
        \"document_type\": \"income_certificate\",
        \"raw_image_uri\": \"minio://verified-docs/hh_${CALL_ID}/income.txt\",
        \"extracted_json\": {
          \"annual_income\": 36000,
          \"issuing_authority\": \"Tahsildar Mysuru\",
          \"issue_date\": \"01-01-2026\"
        }
      }
    ]
  }" > "${OUT_DIR}/04b_document_validation.json"

echo "[6/8] CHW review action (${REVIEW_ACTION})"
if [[ "${REVIEW_ACTION}" == "reject" ]]; then
  curl -fsS -X POST "${SUBMISSION_URL}/submissions/${SUBMISSION_ID}/review" \
    -H "Content-Type: application/json" \
    -H "X-User-Role: chw" \
    -d "{
      \"action\": \"reject\",
      \"reviewer_id\": \"${CHW_ID}\",
      \"reason\": \"${REVIEW_REASON}\",
      \"missing_fields\": [$(printf '"%s"' "${MISSING_FIELDS}" | sed 's/,/","/g')]
    }" > "${OUT_DIR}/05_submission_review.json"
else
  curl -fsS -X POST "${SUBMISSION_URL}/submissions/${SUBMISSION_ID}/review" \
    -H "Content-Type: application/json" \
    -H "X-User-Role: chw" \
    -d "{
      \"action\": \"approve\",
      \"reviewer_id\": \"${CHW_ID}\",
      \"reason\": \"${REVIEW_REASON}\"
    }" > "${OUT_DIR}/05_submission_review.json"
fi

echo "[7/8] Optional correction loop"
if [[ "${RUN_CORRECTION_LOOP}" == "true" || "${REVIEW_ACTION}" == "reject" ]]; then
  curl -fsS -X POST "${SUBMISSION_URL}/submissions/${SUBMISSION_ID}/correction" \
    -H "Content-Type: application/json" \
    -H "X-User-Role: citizen" \
    -d "{
      \"actor_id\": \"citizen_demo\",
      \"corrected_fields\": {\"address\": \"Kuvempunagar Mysuru\"},
      \"note\": \"Updated after CHW feedback\"
    }" > "${OUT_DIR}/06_correction_submitted.json"
fi

echo "[8/8] Fetch submission details after final action"
curl -fsS -H "X-User-Role: chw" "${SUBMISSION_URL}/submissions/${SUBMISSION_ID}" > "${OUT_DIR}/07_submission_after_action.json"

cat > "${OUT_DIR}/README.txt" <<EOF
ZELIA E2E walkthrough completed.

Call ID: ${CALL_ID}
Submission ID: ${SUBMISSION_ID}
Review Action: ${REVIEW_ACTION}
Correction Loop: ${RUN_CORRECTION_LOOP}

Artifacts:
- 01_voice_process.json
- 02_n8n_response.json
- 03_submission_sync.json
- 04_submission_before_review.json
- 05_submission_review.json
- 06_correction_submitted.json (if executed)
- 07_submission_after_action.json
EOF

echo "Walkthrough finished. Output: ${OUT_DIR}"
