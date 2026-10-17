import requests
import json
import time

# Configuration
WEBHOOK_URL = "http://localhost:5678/webhook-test/ultravox/call-ended"

# Test payloads for different event types
call_ended_payload = {
    "event_type": "call_ended",
    "call_id": "test_call_12345",
    "phone_number": "+919876543210",
    "duration": 120,
    "status": "completed",
    "audio_url": "https://example.com/audio/test_call_12345.wav",
    "timestamp": "2026-01-30T10:30:00Z"
}

transcript_update_payload = {
    "event_type": "transcript_update",
    "call_id": "test_call_12345",
    "phone_number": "+919876543210",
    "transcript": "Hello, I need information about government schemes for farmers",
    "language": "en",
    "confidence": 0.95,
    "timestamp": "2026-01-30T10:28:00Z"
}

def send_webhook(payload, event_name):
    print(f"\n{'='*60}")
    print(f"Sending {event_name} event")
    print(f"{'='*60}")
    print(f"URL: {WEBHOOK_URL}")
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"\n--- Response ---")
        print(f"Status Code: {response.status_code}")
        
        try:
            response_json = response.json()
            print(f"Response Body:")
            print(json.dumps(response_json, indent=2))
        except:
            print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            print(f"\n✅ {event_name} webhook sent successfully!")
            return True
        else:
            print(f"\n⚠️ Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error sending webhook: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting N8N Webhook Test")
    print(f"Target: {WEBHOOK_URL}\n")
    
    # Test 1: Send call_ended event
    success1 = send_webhook(call_ended_payload, "call_ended")
    
    time.sleep(2)
    
    # Test 2: Send transcript_update event
    success2 = send_webhook(transcript_update_payload, "transcript_update")
    
    print(f"\n{'='*60}")
    print("Test Summary")
    print(f"{'='*60}")
    print(f"call_ended event: {'✅ SUCCESS' if success1 else '❌ FAILED'}")
    print(f"transcript_update event: {'✅ SUCCESS' if success2 else '❌ FAILED'}")
    print(f"\n{'='*60}")
