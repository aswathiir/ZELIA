#!/usr/bin/env bash
set -euo pipefail

echo "[1/9] retrieval-service health"
curl -fsS http://localhost:8007/health | tee /tmp/zelia_retrieval_health.json

echo "[2/9] rules-engine evaluate endpoint"
curl -fsS -X POST http://localhost:8005/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"profile":{"age":65,"marital_status":"widowed","monthly_income":3000,"children_count":0,"disability_status":false,"disability_percentage":0,"caste_category":"OBC","state_code":"KA","occupation":"none","housing_type":"own","documents_available":[]},"scheme_ids":[]}' > /tmp/zelia_rules_evaluate.json || true

echo "[3/9] rules-engine compatibility endpoint"
curl -fsS -X POST http://localhost:8005/check-eligibility \
  -H 'Content-Type: application/json' \
  -d '{"scheme_id":"ka-widow-pension","applicant_data":{"age":65,"state_code":"KA","marital_status":"widowed","monthly_income":3000}}' > /tmp/zelia_rules_compat.json || true

echo "[4/9] voice-processor health + offline contracts"
curl -fsS http://localhost:8018/health > /tmp/zelia_voice_health.json || true
curl -fsS -X POST http://localhost:8018/asr/transcribe \
  -H 'Content-Type: application/json' \
  -d '{"call_id":"smoke_voice_001","language":"en-IN","transcript_text":"My name is Lakshmi from Mysuru"}' > /tmp/zelia_voice_asr.json || true
curl -fsS -X POST http://localhost:8018/tts/synthesize \
  -H 'Content-Type: application/json' \
  -d '{"text":"Zelia voice smoke test successful","language":"en-IN"}' > /tmp/zelia_voice_tts.json || true

echo "[5/9] n8n webhook basic check"
curl -fsS -X POST http://localhost:5678/webhook/ultravox/call-ended \
  -H 'Content-Type: application/json' \
  -d '{"call_id":"smoke_call_001","customer_number":"+919999999999","language":"en","messages":[{"role":"user","text":"My name is Lakshmi, age 65, widowed from Mysuru Karnataka"}],"metadata":{"confidence":0.9,"tone":"neutral","urgency":"normal"}}' > /tmp/zelia_n8n_response.json || true

echo "[6/9] submission service review lifecycle"
SYNC_TMP="$(mktemp)"
printf "test" > "${SYNC_TMP}"
curl -fsS -X POST http://localhost:8009/sync \
  -H 'X-User-Role: system' \
  -F "file=@${SYNC_TMP};type=text/plain" \
  -F "user_id=chw_001" \
  -F 'metadata={"household_hash":"hh_smoke","scheme_id":"ka-old-age-pension","required_documents":["aadhaar","income_certificate"],"applicant_name":"Lakshmi","user_profile":{"name":"Lakshmi","age":64,"date_of_birth":"12-04-1961","aadhaar_number":"123412341234","annual_income":36000,"gender":"female","address":"Mysuru Karnataka"}}' \
  > /tmp/zelia_submission_sync.json || true
rm -f "${SYNC_TMP}"
SUB_ID=$(python3 - <<'PY'
import json
try:
    data = json.load(open("/tmp/zelia_submission_sync.json"))
    print(data.get("submission_id",""))
except Exception:
    print("")
PY
)
if [[ -n "$SUB_ID" ]]; then
  curl -fsS -X POST "http://localhost:8009/submissions/${SUB_ID}/validate-documents" \
    -H 'Content-Type: application/json' \
    -H 'X-User-Role: chw' \
    -d '{
      "auto_correct_form": false,
      "documents": [
        {"document_type":"aadhaar","raw_image_uri":"minio://verified-docs/hh_smoke/aadhaar.txt","extracted_json":{"name":"Lakshmi","date_of_birth":"12-04-1961","gender":"female","address":"Mysuru Karnataka","aadhaar_number":"123412341234"}},
        {"document_type":"income_certificate","raw_image_uri":"minio://verified-docs/hh_smoke/income.txt","extracted_json":{"annual_income":36000,"issuing_authority":"Tahsildar Mysuru","issue_date":"01-01-2026"}}
      ]
    }' > /tmp/zelia_submission_validate.json || true
  curl -fsS -X POST "http://localhost:8009/submissions/${SUB_ID}/review" \
    -H 'Content-Type: application/json' \
    -H 'X-User-Role: chw' \
    -d '{"action":"approve","reviewer_id":"chw_001","reason":"documents verified"}' > /tmp/zelia_submission_review.json || true
fi

echo "[7/9] MinIO object list"
python3 - <<'PY'
from minio import Minio
c=Minio('localhost:9000',access_key='minioadmin',secret_key='minioadmin',secure=False)
for b in ['templates','filled-forms','verified-docs']:
  try:
    objs=list(c.list_objects(b,recursive=True))
    print(b,len(objs))
  except Exception as e:
    print(b,'unavailable',e)
PY

echo "[8/9] PDF strict gate check"
python3 skills/zelia-pdf-form-audit/scripts/audit_pdf_pipeline.py \
  --workflow zeliaintegration_v28b_fresh.json \
  --schema schema_v28_upgrade.sql \
  --templates-dir dataset/govt/templates \
  --placeholders-dir data/forms \
  --out /tmp/zelia_smoke_audit.json || true
python3 skills/zelia-pdf-form-audit/scripts/validate_gate.py \
  --audit /tmp/zelia_smoke_audit.json \
  --field-map data/ingestion/field_map_all_minio.json > /tmp/zelia_gate_result.json || true

echo "[9/9] Data readiness status"
python3 scripts/prepare_data_readiness.py > /tmp/zelia_data_readiness.json || true

echo "Smoke test complete. Artifacts in /tmp/zelia_*.json"
