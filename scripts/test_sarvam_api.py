"""
Sarvam AI Translation Service - Troubleshooting & Testing
"""
import os
import requests
import json

# API Configuration
API_KEY = os.getenv("SARVAM_API_KEY", "")
BASE_URL = "https://api.sarvam.ai"

def test_api_connection():
    """Test basic API connectivity"""
    print("=" * 70)
    print("SARVAM AI API TESTING")
    print("=" * 70)
    print()
    
    # Test 1: Simple translation
    print("[1] Testing Translation API...")
    print(f"    API Key: {API_KEY[:15]}...")
    print(f"    Base URL: {BASE_URL}")
    print()
    
    test_text = "Hello, how are you?"
    
    try:
        response = requests.post(
            f"{BASE_URL}/translate",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "input": test_text,
                "source_language_code": "en-IN",
                "target_language_code": "hi-IN",
                "speaker_gender": "Male",
                "mode": "formal",
                "model": "mayura:v1",
                "enable_preprocessing": True
            },
            timeout=30
        )
        
        print(f"    Status Code: {response.status_code}")
        print(f"    Response: {response.text[:200]}")
        print()
        
        if response.status_code == 200:
            result = response.json()
            print("    ✓ SUCCESS!")
            print(f"    Original: {test_text}")
            print(f"    Translated: {result.get('translated_text', 'N/A')}")
            return True
        elif response.status_code == 403:
            print("    ✗ 403 FORBIDDEN")
            print("    Possible reasons:")
            print("      - API key is invalid or expired")
            print("      - API key doesn't have translation permissions")
            print("      - Account needs verification")
            print()
            print("    Solutions:")
            print("      1. Verify API key at https://www.sarvam.ai/")
            print("      2. Check if account is activated")
            print("      3. Ensure you have credits/quota")
            return False
        elif response.status_code == 401:
            print("    ✗ 401 UNAUTHORIZED")
            print("    The API key format is incorrect")
            return False
        else:
            print(f"    ✗ ERROR: {response.status_code}")
            print(f"    Message: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("    ✗ TIMEOUT: Request took too long")
        return False
    except requests.exceptions.ConnectionError:
        print("    ✗ CONNECTION ERROR: Cannot reach Sarvam AI servers")
        return False
    except Exception as e:
        print(f"    ✗ EXCEPTION: {str(e)}")
        return False

def test_alternative_endpoint():
    """Test with different language codes"""
    print("\n[2] Testing Alternative Language Codes...")
    
    # Try different format
    test_cases = [
        ("en-IN", "hi-IN"),  # With region
        ("en", "hi"),         # Without region
    ]
    
    for source, target in test_cases:
        print(f"\n    Testing: {source} → {target}")
        try:
            response = requests.post(
                f"{BASE_URL}/translate",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": "pension scheme",
                    "source_language_code": source,
                    "target_language_code": target
                },
                timeout=10
            )
            
            print(f"      Status: {response.status_code}")
            if response.status_code == 200:
                print(f"      ✓ Works with {source} → {target}")
                return True
        except Exception as e:
            print(f"      ✗ Error: {str(e)}")
    
    return False

def show_fallback_solution():
    """Show how to use fallback"""
    print("\n" + "=" * 70)
    print("FALLBACK SOLUTION")
    print("=" * 70)
    print()
    print("Since the API key is not working, here are your options:")
    print()
    print("Option 1: Fix API Key")
    print("  - Visit: https://www.sarvam.ai/")
    print("  - Login to your account")
    print("  - Generate a new API key")
    print("  - Verify account is activated")
    print()
    print("Option 2: Use Mock Translation (Already Implemented)")
    print("  - Comment out line 41 in multilingual_sarvam.py")
    print("  - This will use the dictionary-based fallback")
    print("  - Good for testing, covers common scheme terms")
    print()
    print("Option 3: Use Alternative Translation Service")
    print("  - Google Cloud Translation API")
    print("  - Azure Translator")
    print("  - AWS Translate")
    print()

if __name__ == "__main__":
    success = test_api_connection()
    
    if not success:
        test_alternative_endpoint()
        show_fallback_solution()
    
    print("\n" + "=" * 70)
    print("Testing Complete!")
    print("=" * 70)
