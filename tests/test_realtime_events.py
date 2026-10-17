#!/usr/bin/env python3
"""
Simulate realtime Ultravox webhook events as they would occur during an actual call.
This script sends a sequence of events with realistic timing to test the N8N workflow.
"""

import requests
import json
import time
from datetime import datetime, timedelta
import uuid

# Configuration
N8N_WEBHOOK_URL = "http://localhost:5678/webhook-test/ultravox/call-ended"
CALL_ID = f"realtime_test_{uuid.uuid4().hex[:8]}"
PHONE_NUMBER = "+919876543210"

# Color codes for terminal output
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_event(event_type, status="SENDING"):
    """Print formatted event information"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = BLUE if status == "SENDING" else GREEN if status == "SUCCESS" else RED
    print(f"{color}[{timestamp}] {status}: {event_type}{RESET}")

def send_webhook(payload, event_name, delay_before=0):
    """Send webhook with optional delay and formatted output"""
    if delay_before > 0:
        print(f"{YELLOW}⏱️  Waiting {delay_before}s...{RESET}")
        time.sleep(delay_before)
    
    print_event(event_name, "SENDING")
    print(f"   Payload: {json.dumps(payload, indent=6)}")
    
    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print_event(event_name, "SUCCESS")
            try:
                print(f"   Response: {json.dumps(response.json(), indent=6)}")
            except:
                print(f"   Response: {response.text}")
            return True
        else:
            print_event(event_name, f"FAILED ({response.status_code})")
            print(f"   {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print_event(event_name, "ERROR")
        print(f"   {RED}{e}{RESET}")
        return False

def simulate_realtime_call():
    """Simulate a complete phone call with realtime events"""
    
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}🎙️  ULTRAVOX REALTIME EVENT SIMULATION{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}Call ID:{RESET} {CALL_ID}")
    print(f"{BOLD}Phone:{RESET} {PHONE_NUMBER}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    start_time = datetime.now()
    
    # Event 1: Call Started
    call_started = {
        "event_type": "call_started",
        "call_id": CALL_ID,
        "phone_number": PHONE_NUMBER,
        "timestamp": start_time.isoformat()
    }
    send_webhook(call_started, "call_started", delay_before=0)
    
    # Event 2-5: Progressive transcript updates (simulating real conversation)
    transcripts = [
        ("Hello", 2),
        ("Hello, I need information", 3),
        ("Hello, I need information about government schemes", 2),
        ("Hello, I need information about government schemes for farmers in Kerala", 3),
    ]
    
    for i, (transcript, delay) in enumerate(transcripts, 1):
        transcript_update = {
            "event_type": "transcript_update",
            "call_id": CALL_ID,
            "phone_number": PHONE_NUMBER,
            "transcript": transcript,
            "language": "en",
            "confidence": 0.85 + (i * 0.03),  # Increasing confidence
            "timestamp": (start_time + timedelta(seconds=sum(d for _, d in transcripts[:i]))).isoformat()
        }
        send_webhook(transcript_update, f"transcript_update #{i}", delay_before=delay)
    
    # Event 6: Another transcript segment
    time.sleep(2)
    transcript_update_2 = {
        "event_type": "transcript_update",
        "call_id": CALL_ID,
        "phone_number": PHONE_NUMBER,
        "transcript": "I am interested in agricultural subsidies and crop insurance schemes",
        "language": "en",
        "confidence": 0.92,
        "timestamp": (start_time + timedelta(seconds=15)).isoformat()
    }
    send_webhook(transcript_update_2, "transcript_update #5", delay_before=3)
    
    # Event 7: Final transcript
    final_transcript = {
        "event_type": "transcript_update",
        "call_id": CALL_ID,
        "phone_number": PHONE_NUMBER,
        "transcript": "Thank you for the information. That was very helpful.",
        "language": "en",
        "confidence": 0.95,
        "timestamp": (start_time + timedelta(seconds=20)).isoformat()
    }
    send_webhook(final_transcript, "transcript_update #6 (final)", delay_before=4)
    
    # Event 8: Call Ended
    end_time = datetime.now()
    duration = int((end_time - start_time).total_seconds())
    
    call_ended = {
        "event_type": "call_ended",
        "call_id": CALL_ID,
        "phone_number": PHONE_NUMBER,
        "duration": duration,
        "status": "completed",
        "audio_url": f"https://storage.example.com/calls/{CALL_ID}.wav",
        "timestamp": end_time.isoformat()
    }
    send_webhook(call_ended, "call_ended", delay_before=2)
    
    # Summary
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}{GREEN}✅ SIMULATION COMPLETE{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    print(f"Total Duration: {duration} seconds")
    print(f"Events Sent: 8 (1 call_started + 6 transcript_updates + 1 call_ended)")
    print(f"\n{YELLOW}💡 Check N8N workflow execution to see how events were processed{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")

if __name__ == "__main__":
    print(f"\n{YELLOW}⚠️  IMPORTANT: Make sure to click 'Execute workflow' in N8N before running!{RESET}")
    print(f"{YELLOW}   The test webhook only works when the workflow is listening.{RESET}\n")
    
    input(f"{BOLD}Press ENTER to start the realtime simulation...{RESET}")
    
    simulate_realtime_call()
