import requests
import json
import time

# Configuration
N8N_HOST = "http://localhost:5678"
# PROBE MULTIPLE PATHS TO FIND THE ACTIVE WORKFLOW
PATHS_TO_TRY = ["voice/ultravox-v2", "voice/ultravox"]
ENDPOINTS = []
for path in PATHS_TO_TRY:
    ENDPOINTS.append(f"{N8N_HOST}/webhook-test/{path}")
    ENDPOINTS.append(f"{N8N_HOST}/webhook/{path}")

def send_webhook(event_type, payload):
    print(f"\n--- Sending {event_type} event ---")
    
    # Add common fields if missing
    if "event_type" not in payload:
        payload["event_type"] = event_type
    
    headers = {"Content-Type": "application/json"}
    
    for url in ENDPOINTS:
        print(f"Trying URL: {url}")
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ Success! Webhook received at {url}")
                print(f"Response: {response.text}")
                return True
            elif response.status_code == 404:
                print("❌ Endpoint not found (Workflow might not be active or waiting in test mode)")
            else:
                print(f"❌ Error: {response.text}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")
    
    return False

def main():
    call_id = "test_call_" + str(int(time.time()))
    phone_number = "+919876543210"
    
    # 1. Simulate Transcript Update (User speaking)
    transcript_payload = {
        "event_type": "transcript_update",
        "call_id": call_id,
        "phone_number": phone_number,
        "transcript": "Hello, I want to know about recent government schemes for farmers.",
        "language": "en",
        "confidence": 0.95
    }
    send_webhook("transcript_update", transcript_payload)
    
    time.sleep(1) # Wait a bit
    
    # 2. Simulate Call Ended
    end_payload = {
        "event_type": "call_ended",
        "call_id": call_id,
        "phone_number": phone_number,
        "duration": 45,
        "status": "completed",
        "audio_url": f"https://api.ultravox.ai/recordings/{call_id}.mp3"
    }
    send_webhook("call_ended", end_payload)

if __name__ == "__main__":
    main()
