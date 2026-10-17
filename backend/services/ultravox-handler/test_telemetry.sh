#!/bin/bash

# Configuration
API_URL="http://localhost:8013"
C_ID="cit_test_$(date +%s)"
NAME="Aswathi Test"
REASON="PM-KISAN Verification"

echo "Step 1: Initiating mock call..."
INIT_RESP=$(curl -s -X POST "$API_URL/calls/initiate" \
  -H "Content-Type: application/json" \
  -d "{
    \"phone_number\": \"+919876543210\",
    \"name\": \"$NAME\",
    \"citizen_id\": \"$C_ID\",
    \"reason\": \"$REASON\"
  }")

CALL_ID=$(echo $INIT_RESP | grep -o '"callId":"[^"]*' | cut -d'"' -f4)

if [ -z "$CALL_ID" ]; then
  echo "Failed to initiate call. Response: $INIT_RESP"
  exit 1
fi

echo "Created Call ID: $CALL_ID"

echo "Step 2: Activating session..."
curl -s -X POST "$API_URL/session/create" \
  -H "Content-Type: application/json" \
  -d "{
    \"call_id\": \"$CALL_ID\",
    \"phone_number\": \"+919876543210\"
  }"

echo "Step 3: Sending real-time telemetry updates (Simulating conversation)..."
for i in {1..5}
do
  echo "Update $i..."
  curl -s -X POST "$API_URL/session/update/$CALL_ID" \
    -H "Content-Type: application/json" \
    -d "{
      \"structured_data\": {
        \"current_topic\": \"Eligibility Check\",
        \"confidence\": $((70 + $i)),
        \"duration\": $((i * 10))
      }
    }"
  sleep 2
done

echo "Step 4: Ending session..."
curl -s -X POST "$API_URL/session/end/$CALL_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"duration\": 60,
    \"status\": \"completed\"
  }"

echo "Telemetry test sequence complete."
