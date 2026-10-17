# -*- coding: utf-8 -*-
"""
ZELIA Retrieval Service Test Script
"""
import requests
import time
import sys
import json

RETRIEVAL_URL = "http://localhost:8007"

def test_retrieval_service():
    print("=" * 60)
    print(" RETRIEVAL SERVICE TESTS")
    print("=" * 60)
    
    # 1. Wait for health check (service needs to load model)
    print("\n[1] Waiting for service to become healthy (loading model)...")
    for i in range(30):
        try:
            resp = requests.get(f"{RETRIEVAL_URL}/health")
            if resp.status_code == 200:
                print(f"    Service is UP: {resp.json()}")
                break
        except requests.exceptions.ConnectionError:
            pass
        print(f"    Waiting... ({i+1}/30)")
        time.sleep(2)
    else:
        print("    ERROR: Service timed out")
        return False

    # 2. Index a document
    print("\n[2] Indexing test document...")
    doc_text = """
    The Pradhan Mantri Awas Yojana (PMAY) is a housing scheme by the Government of India.
    Beneficiaries receive financial assistance to build pucca houses.
    Eligibility includes EWS (Economically Weaker Section) and LIG (Low Income Group) families.
    """
    
    try:
        resp = requests.post(f"{RETRIEVAL_URL}/index/text", json={
            "text": doc_text,
            "metadata": {
                "source": "manual_test",
                "scheme": "PMAY"
            }
        })
        print(f"    Index Status: {resp.status_code}")
        print(f"    Response: {resp.json()}")
    except Exception as e:
        print(f"    ERROR: Indexing failed - {e}")
        return False
        
    # 3. Search
    print("\n[3] Searching for 'housing scheme'...")
    try:
        resp = requests.post(f"{RETRIEVAL_URL}/search", json={
            "query": "Who is eligible for housing assistance?",
            "k": 2
        })
        results = resp.json()
        print(f"    Found {len(results)} results")
        for res in results:
            print(f"    - Score: {res['score']:.4f}")
            print(f"      Content: {res['content'][:100]}...")
            print(f"      Metadata: {res['metadata']}")
            
        if len(results) > 0:
            print("    ✅ Search verification SUCCESS")
            return True
        else:
            print("    ❌ Search verification FAILED (No results)")
            return False
            
    except Exception as e:
        print(f"    ERROR: Search failed - {e}")
        return False

if __name__ == "__main__":
    success = test_retrieval_service()
    sys.exit(0 if success else 1)
