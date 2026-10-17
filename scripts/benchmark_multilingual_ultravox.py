import urllib.request
import urllib.error
import json
import time
import uuid
import sys
import argparse
from typing import Dict, Any

WEBHOOK_URL = "http://localhost:8013/webhook/call-ended"

TEST_CASES = [
    {
        "language": "en",
        "name": "English",
        "expected_intent": "pension",
        "expected_age": 65,
        "expected_state": "Karnataka",
        "messages": [
            {"role": "agent", "text": "Hi, I'm calling from Zelia government schemes assistant. How can I help you today?"},
            {"role": "user", "text": "I am a 65 year old widow from Karnataka and I need a monthly pension. My income is 2000 rupees."}
        ]
    },
    {
        "language": "hi",
        "name": "Hindi",
        "expected_intent": "pension",
        "expected_age": 65,
        "expected_state": "Karnataka",
        "messages": [
            {"role": "agent", "text": "नमस्ते, मैं ज़ेलिया सरकारी योजना सहायक बोल रही हूँ। मैं आपकी कैसे मदद कर सकती हूँ?"},
            {"role": "user", "text": "मैं 65 साल की विधवा हूँ, कर्नाटक से। मुझे मासिक पेंशन चाहिए, मेरी मासिक आय 2000 रुपये है।"}
        ]
    },
    {
        "language": "ta",
        "name": "Tamil",
        "expected_intent": "pension",
        "expected_age": 65,
        "expected_state": "Karnataka",
        "messages": [
            {"role": "agent", "text": "வணக்கம், நான் செலியா அரசு திட்ட உதவியாளரில் இருந்து அழைக்கிறேன். நான் உங்களுக்கு எப்படி உதவ முடியும்?"},
            {"role": "user", "text": "நான் கர்நாடகாவைச் சேர்ந்த 65 வயது விதவை. எனக்கு மாத ஓய்வூதியம் வேண்டும். என் மாத வருமானம் 2000 ரூபாய்."}
        ]
    },
    {
        "language": "kn",
        "name": "Kannada",
        "expected_intent": "pension",
        "expected_age": 65,
        "expected_state": "Karnataka",
        "messages": [
            {"role": "agent", "text": "ನಮಸ್ಕಾರ, ನಾನು ಜೀಲಿಯಾ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳ ಸಹಾಯಕಿ. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?"},
            {"role": "user", "text": "ನಾನು ಕರ್ನಾಟಕದ 65 ವರ್ಷದ ವಿಧವೆ. ನನಗೆ ಮಾಸಿಕ ಪಿಂಚಣಿ ಬೇಕು. ನನ್ನ ಮಾಸಿಕ ಆದಾಯ 2000 ರೂಪಾಯಿ."}
        ]
    },
    {
        "language": "te",
        "name": "Telugu",
        "expected_intent": "pension",
        "expected_age": 65,
        "expected_state": "Karnataka",
        "messages": [
            {"role": "agent", "text": "నమస్కారం, నేను జెలియా ప్రభుత్వ పథకాల సహాయకారిని. నేను మీకు ఎలా సహాయపడగలను?"},
            {"role": "user", "text": "నేను కర్ణాటకకు చెందిన 65 ఏళ్ల వితంతువును. నాకు నెలవారీ పింఛను కావాలి. నా నెలవారీ ఆదాయం 2000 రూపాయలు."}
        ]
    }
]

def run_benchmark():
    print(f"{'='*70}")
    print(f"{'Multilingual Ultravox Endpoint Benchmark':^70}")
    print(f"{'='*70}\n")
    
    results = []
    
    for case in TEST_CASES:
        lang_name = case["name"]
        lang_code = case["language"]
        print(f"Testing Language: {lang_name} ({lang_code})")
        print("-" * 50)
        
        call_id = f"bench_{lang_code}_{uuid.uuid4().hex[:8]}"
        household_hash = f"bench_hh_{lang_code}_{uuid.uuid4().hex[:8]}"
        
        payload = {
            "event_type": "call_ended",
            "call_id": call_id,
            "customer_number": "+919999999999",
            "duration_secs": 45,
            "messages": case["messages"],
            "status": "completed",
            "language": lang_code,
            "household_hash": household_hash,
            "metadata": {
                "household_hash": household_hash,
                "benchmark": True
            },
            "process_now": True
        }
        
        data_json = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(WEBHOOK_URL, data=data_json, headers={'Content-Type': 'application/json'}, method='POST')
        
        start_time = time.time()
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                latency = time.time() - start_time
                resp_text = response.read().decode('utf-8')
                
                data = json.loads(resp_text)
                n8n_success = data.get("n8n", {}).get("success", False)
                result_data = data.get("result", {})
                
                best_scheme = result_data.get("best_match_scheme", {})
                scheme_name = best_scheme.get("scheme_name") or best_scheme.get("scheme_id") or "None"
                
                print(f"✓ Request Successful (Latency: {latency:.2f}s)")
                print(f"  N8N Processed: {n8n_success}")
                print(f"  Best Match Scheme: {scheme_name}")
                print(f"  Response Text: {result_data.get('response_text', 'N/A')}")
                
                results.append({
                    "Language": lang_name,
                    "Latency (s)": round(latency, 2),
                    "Scheme Found": scheme_name != "None",
                    "Scheme Name": scheme_name,
                    "Success": n8n_success
                })
        except urllib.error.HTTPError as e:
            latency = time.time() - start_time
            print(f"✗ Request Failed with status {e.code}")
            print(f"  Response: {e.read().decode('utf-8')}")
            results.append({
                "Language": lang_name,
                "Latency (s)": round(latency, 2),
                "Scheme Found": False,
                "Scheme Name": "Error",
                "Success": False
            })
        except Exception as e:
            latency = time.time() - start_time
            print(f"✗ Request Exception: {e}")
            results.append({
                "Language": lang_name,
                "Latency (s)": round(latency, 2),
                "Scheme Found": False,
                "Scheme Name": "Exception",
                "Success": False
            })
            
        print("\n")
        
    print(f"{'='*70}")
    print(f"{'Benchmark Summary':^70}")
    print(f"{'='*70}")
    
    # Print table header
    print(f"{'Language':<15} | {'Latency (s)':<12} | {'Success':<8} | {'Scheme Found':<12} | {'Scheme Name'}")
    print("-" * 70)
    for r in results:
        print(f"{r['Language']:<15} | {r['Latency (s)']:<12} | {str(r['Success']):<8} | {str(r['Scheme Found']):<12} | {r['Scheme Name']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Multilingual Ultravox Endpoint")
    parser.parse_args()
    run_benchmark()
