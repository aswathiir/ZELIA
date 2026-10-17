import requests
import json
import time

# Configuration
NGROK_WEBHOOK_URL = "https://multiovulate-heathered-amia.ngrok-free.dev/workflow/z9F-9jwFsfqKxpzDqS01n"

# Test payloads
transcript_update_payload = {
    "event_type": "transcript_update",
    "call_id": "test_call_12345",
    "phone_number": "+919876543210",
    "transcript": "Hello, I need information about government schemes",
    "language": "en",
    "confidence": 0.95,
    "timestamp": "2026-01-30T10:26:00Z"
}

call_ended_payload = {
    "event_type": "call_ended",
    "call_id": "test_call_12345",
    "phone_number": "+919876543210",
    "duration": 120,
    "status": "completed",
    "audio_url": "https://example.com/audio/test_call_12345.wav",
    "timestamp": "2026-01-30T10:28:00Z"
}

def send_webhook(payload, event_name):
    print(f"\n--- Sending {event_name} event ---")
    print(f"URL: {NGROK_WEBHOOK_URL}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            NGROK_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            print(f"Response Body: {response.json()}")
        except:
            print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            print(f"✅ {event_name} webhook sent successfully!")
        else:
            print(f"⚠️ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error sending webhook: {e}")

if __name__ == "__main__":
    # Send transcript_update event
    send_webhook(transcript_update_payload, "transcript_update")
    
    time.sleep(2)
    
    # Send call_ended event
    send_webhook(call_ended_payload, "call_ended")
    
    print("\n✅ Test completed!")
