#!/bin/bash
# ======================================================
# ZELIA OCR Document Pipeline — E2E Test
# Tests: upload → extract → verify → auto-fill
# ======================================================
set -euo pipefail

API_BASE="${OCR_SERVICE_URL:-http://localhost:8003}"
HH_HASH="test_household_$(date +%s)"
PASS=0
FAIL=0

red()   { printf "\033[31m%s\033[0m\n" "$1"; }
green() { printf "\033[32m%s\033[0m\n" "$1"; }

check() {
  local label="$1" actual="$2" expected="$3"
  if echo "$actual" | grep -qi "$expected"; then
    green "  ✅ $label"
    PASS=$((PASS + 1))
  else
    red   "  ❌ $label  (expected: $expected, got: $actual)"
    FAIL=$((FAIL + 1))
  fi
}

echo "============================================"
echo " ZELIA OCR Pipeline — E2E Test"
echo " API: $API_BASE  Household: $HH_HASH"
echo "============================================"

# ----- 1. Health check -----
echo "[1/5] Health check"
HC=$(curl -sS -m 5 "$API_BASE/health" 2>&1 || echo '{"status":"fail"}')
check "service healthy" "$HC" "healthy"
check "EasyOCR version" "$HC" "EasyOCR"

# ----- 2. Extract Aadhaar (via JSON body with base64) -----
echo "[2/5] Extract Aadhaar document"
# Create a simple test image with text (using Python + PIL)
AADHAAR_B64=$(python3 -c "
from PIL import Image, ImageDraw, ImageFont
import base64, io
img = Image.new('RGB', (600, 400), 'white')
d = ImageDraw.Draw(img)
d.text((50, 20), 'GOVERNMENT OF INDIA', fill='black')
d.text((50, 50), 'UNIQUE IDENTIFICATION AUTHORITY', fill='black')
d.text((50, 100), 'Name: Lakshmi Devi', fill='black')
d.text((50, 130), 'DOB: 15/03/1961', fill='black')
d.text((50, 160), 'Female', fill='black')
d.text((50, 200), 'Address: Kuvempunagar Mysuru', fill='black')
d.text((50, 230), 'Karnataka 570023', fill='black')
d.text((50, 280), '1234 5678 9012', fill='black')
buf = io.BytesIO()
img.save(buf, format='JPEG')
print(base64.b64encode(buf.getvalue()).decode())
" 2>/dev/null)

if [ -z "$AADHAAR_B64" ]; then
  red "  ⚠ Could not create test image (PIL not installed). Skipping image tests."
  echo "[SKIP] Steps 2-4 require PIL"
else
  EXTRACT_RESP=$(curl -sS -m 30 "$API_BASE/extract-document" \
    -H "Content-Type: application/json" \
    -d "{
      \"household_hash\": \"$HH_HASH\",
      \"document_type\": \"aadhaar\",
      \"image_base64\": \"$AADHAAR_B64\"
    }" 2>&1)

  check "document_type is aadhaar" "$EXTRACT_RESP" "aadhaar"
  check "extraction returned fields" "$EXTRACT_RESP" "extracted_fields"

  # ----- 3. Get household documents -----
  echo "[3/5] Retrieve household documents"
  DOCS_RESP=$(curl -sS -m 10 "$API_BASE/household/$HH_HASH/documents" 2>&1)
  check "has documents" "$DOCS_RESP" "documents"

  # ----- 4. Verify submission -----
  echo "[4/5] Verify submission (mismatch test)"
  VERIFY_RESP=$(curl -sS -m 10 "$API_BASE/verify-submission" \
    -H "Content-Type: application/json" \
    -d "{
      \"household_hash\": \"$HH_HASH\",
      \"user_profile\": {
        \"name\": \"Wrong Name\",
        \"aadhaar_number\": \"1234 5678 9012\"
      }
    }" 2>&1)
  check "overall_status present" "$VERIFY_RESP" "overall_status"
fi

# ----- 5. Auto-fill test (with mock data) -----
echo "[5/5] Auto-fill test"
AUTOFILL_RESP=$(curl -sS -m 10 "$API_BASE/auto-fill" \
  -H "Content-Type: application/json" \
  -d "{
    \"household_hash\": \"$HH_HASH\",
    \"user_profile\": {
      \"name\": null,
      \"aadhaar_number\": null,
      \"address\": \"\"
    }
  }" 2>&1)
check "auto-fill response" "$AUTOFILL_RESP" "filled_profile"

echo ""
echo "============================================"
echo " Results: $PASS passed, $FAIL failed"
echo "============================================"

[ "$FAIL" -eq 0 ] && exit 0 || exit 1
