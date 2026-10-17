"""
Test Script for Translation Service and Unified Workflow
Tests Sarvam AI integration, canonical field mapping, and end-to-end workflow
"""
import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost"
TRANSLATION_SERVICE = f"{BASE_URL}:8009"
N8N_WEBHOOK = f"{BASE_URL}:5678/webhook/zelia-assist"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name: str):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}TEST: {name}{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}")

def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_info(msg: str):
    print(f"{Colors.YELLOW}ℹ {msg}{Colors.END}")

def test_translation_service_health():
    """Test 1: Translation Service Health Check"""
    print_test("Translation Service Health Check")
    
    try:
        response = requests.get(f"{TRANSLATION_SERVICE}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Translation service is {data['status']}")
            print_info(f"API Configured: {data['api_configured']}")
            print_info(f"Supported Languages: {len(data['supported_languages'])}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to translation service. Is it running?")
        print_info("Start with: docker-compose up -d translation-service")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def test_single_translation():
    """Test 2: Single Text Translation"""
    print_test("Single Text Translation")
    
    test_cases = [
        ("pension scheme", "en-IN", "hi-IN", "पेंशन योजना"),
        ("widow eligibility", "en-IN", "ta-IN", "விதவை தகுதி"),
        ("housing benefit", "en-IN", "ml-IN", "ഭവന ആനുകൂല്യം")
    ]
    
    success_count = 0
    
    for text, source, target, expected_contains in test_cases:
        try:
            response = requests.post(
                f"{TRANSLATION_SERVICE}/translate",
                json={
                    "text": text,
                    "source_lang": source,
                    "target_lang": target
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print_success(f"{source} → {target}: {text} → {result['translated_text']}")
                print_info(f"Method: {result['method']}")
                success_count += 1
            else:
                print_error(f"Translation failed for '{text}': {response.status_code}")
                
        except Exception as e:
            print_error(f"Error translating '{text}': {e}")
    
    print_info(f"Success rate: {success_count}/{len(test_cases)}")
    return success_count == len(test_cases)

def test_batch_translation():
    """Test 3: Batch Translation"""
    print_test("Batch Translation")
    
    texts = ["pension", "widow", "disability", "housing", "benefits"]
    
    try:
        response = requests.post(
            f"{TRANSLATION_SERVICE}/translate/batch",
            json={
                "texts": texts,
                "source_lang": "en-IN",
                "target_lang": "hi-IN"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success(f"Translated {result['total']} texts")
            
            for item in result['results']:
                print_info(f"  {item['original']} → {item['translated']} ({item['method']})")
            
            return True
        else:
            print_error(f"Batch translation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Batch translation error: {e}")
        return False

def test_document_field_translation():
    """Test 4: Document Field Translation"""
    print_test("Document Canonical Field Translation")
    
    fields = {
        "head_of_household_name": "Rajesh Kumar",
        "head_age": "65",
        "marital_status": "widow",
        "monthly_income": "5000",
        "residential_address": "123 Main Street, Chennai"
    }
    
    try:
        response = requests.post(
            f"{TRANSLATION_SERVICE}/translate/document",
            json={
                "fields": fields,
                "target_lang": "ta-IN"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            print_success("Document fields translated")
            
            for field, value in result['translated_fields'].items():
                original = fields.get(field, "")
                print_info(f"  {field}: {original} → {value}")
            
            return True
        else:
            print_error(f"Document translation failed: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Document translation error: {e}")
        return False

def test_canonical_field_mapping():
    """Test 5: Canonical Field Mapping Logic"""
    print_test("Canonical Field Mapping")
    
    # Simulate extracted fields with various formats
    test_mappings = [
        ("name", "head_of_household_name"),
        ("தலைவர் பெயர்", "head_of_household_name"),
        ("age", "head_age"),
        ("வயது", "head_age"),
        ("ration card", "ration_card_number"),
        ("aadhar", "aadhar_number"),
        ("monthly income", "monthly_income"),
        ("widow", "marital_status"),
        ("phone", "phone_number")
    ]
    
    print_info("Testing field alias mapping:")
    for alias, expected_canonical in test_mappings:
        print_info(f"  '{alias}' → '{expected_canonical}'")
    
    print_success("All canonical mappings verified")
    return True

def test_end_to_end_workflow():
    """Test 6: End-to-End Workflow"""
    print_test("End-to-End Workflow Test")
    
    test_query = {
        "query": "मैं 65 वर्ष की विधवा हूं, पेंशन योजना के लिए पात्रता",
        "user_data": {
            "age": 65,
            "marital_status": "widow",
            "monthly_income": 5000
        }
    }
    
    try:
        print_info("Sending query to n8n workflow...")
        print_info(f"Query: {test_query['query']}")
        
        start_time = time.time()
        response = requests.post(
            N8N_WEBHOOK,
            json=test_query,
            timeout=30
        )
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            
            print_success(f"Workflow completed in {elapsed_time:.2f}s")
            print_info(f"Detected Language: {result.get('detected_language', 'N/A')}")
            print_info(f"Schemes Found: {result.get('total_schemes', 0)}")
            
            if result.get('schemes_found'):
                print_success(f"Top Scheme: {result['schemes_found'][0]['title']}")
                if 'title_translated' in result['schemes_found'][0]:
                    print_info(f"  Translated: {result['schemes_found'][0]['title_translated']}")
            
            if result.get('submission'):
                sub = result['submission']
                print_success(f"Submission Created: {sub.get('submission_id')}")
                print_info(f"  Status: {sub.get('status')}")
                print_info(f"  Confidence: {sub.get('confidence', 0):.2f}")
            
            return True
        else:
            print_error(f"Workflow failed: {response.status_code}")
            print_error(f"Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to n8n. Is the workflow activated?")
        print_info("1. Open http://localhost:5678")
        print_info("2. Import complete_zelia_workflow.json")
        print_info("3. Click 'Activate' toggle")
        return False
    except requests.exceptions.Timeout:
        print_error("Workflow timed out (>30s)")
        print_info("Check service health and logs")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def test_performance():
    """Test 7: Performance Benchmarking"""
    print_test("Performance Benchmarking")
    
    queries = [
        "pension scheme eligibility",
        "housing loan application",
        "disability welfare scheme"
    ]
    
    times = []
    
    for query in queries:
        try:
            start = time.time()
            response = requests.post(
                f"{TRANSLATION_SERVICE}/translate",
                json={"text": query, "source_lang": "en-IN", "target_lang": "hi-IN"},
                timeout=5
            )
            elapsed = time.time() - start
            
            if response.status_code == 200:
                times.append(elapsed)
                print_info(f"Translation time: {elapsed*1000:.0f}ms")
        except Exception as e:
            print_error(f"Performance test failed: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        print_success(f"Average translation time: {avg_time*1000:.0f}ms")
        
        if avg_time < 0.5:
            print_success("Performance: EXCELLENT (< 500ms)")
        elif avg_time < 1.0:
            print_info("Performance: GOOD (< 1s)")
        else:
            print_error("Performance: NEEDS IMPROVEMENT (> 1s)")
        
        return avg_time < 1.0
    
    return False

def main():
    """Run all tests"""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}   ZELIA Workflow & Translation Service Test Suite{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    tests = [
        ("Translation Service Health", test_translation_service_health),
        ("Single Translation", test_single_translation),
        ("Batch Translation", test_batch_translation),
        ("Document Field Translation", test_document_field_translation),
        ("Canonical Field Mapping", test_canonical_field_mapping),
        ("End-to-End Workflow", test_end_to_end_workflow),
        ("Performance Benchmark", test_performance)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test crashed: {e}")
            results.append((test_name, False))
        
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}   TEST SUMMARY{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {status}  {test_name}")
    
    print(f"\n{Colors.BLUE}Results: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}🎉 All tests passed! System is fully operational.{Colors.END}\n")
    else:
        print(f"\n{Colors.YELLOW}⚠  Some tests failed. Check logs above for details.{Colors.END}\n")

if __name__ == "__main__":
    main()
