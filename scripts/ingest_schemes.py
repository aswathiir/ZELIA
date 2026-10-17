# -*- coding: utf-8 -*-
"""
ZELIA Scheme Ingestion Pipeline
Ingests scheme definitions from JSON files into the database via API.
"""
import requests
import json
import os
import glob
import sys

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
SCHEMES_DIR = "schemes_data"

def get_token():
    """Get authentication token."""
    print("Authenticating...")
    try:
        resp = requests.post(f"{API_URL}/auth/login", json={"username": "admin", "password": "admin123"})
        if resp.status_code == 200:
            return resp.json()["access_token"]
        else:
            print(f"Auth Failed: {resp.status_code}")
            return None
    except Exception as e:
        print(f"Connection Failed: {e}")
        return None

def ingest_scheme(file_path, token=None):
    """Ingest a single scheme from JSON file."""
    print(f"Processing {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Map old format to new API format
        scheme_data = {
            "title": data.get("name", data.get("title", "Unknown Scheme")),
            "description": data.get("description", ""),
            "state_code": data.get("state_code", "TN"),
            "category": data.get("category", "general"),
            "eligibility_rules": data.get("criteria", data.get("eligibility_rules")),
            "required_documents": data.get("required_documents"),
            "impact_weight": data.get("impact_weight", 0.5)
        }
        
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        resp = requests.post(f"{API_URL}/schemes/", json=scheme_data, headers=headers)
        
        if resp.status_code == 200:
            result = resp.json()
            print(f"  [OK] Ingested: {scheme_data['title']} (ID: {result.get('scheme_id', 'N/A')})")
            return True
        else:
            print(f"  [FAIL] {resp.status_code}: {resp.text[:100]}")
            return False
            
    except json.JSONDecodeError as e:
        print(f"  [ERROR] Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def list_current_schemes():
    """List schemes currently in database."""
    try:
        resp = requests.get(f"{API_URL}/schemes/")
        if resp.status_code == 200:
            schemes = resp.json()
            print(f"\nCurrent schemes in database: {len(schemes)}")
            for s in schemes[:5]:
                print(f"  - {s['title']} ({s['category']})")
            if len(schemes) > 5:
                print(f"  ... and {len(schemes) - 5} more")
            return schemes
    except Exception as e:
        print(f"Failed to list schemes: {e}")
    return []

def main():
    print("=" * 50)
    print("ZELIA Scheme Ingestion Pipeline")
    print("=" * 50)
    
    # Get auth token (optional for dev)
    token = get_token()
    
    # Show current state
    list_current_schemes()
    
    # Find JSON files
    if not os.path.exists(SCHEMES_DIR):
        print(f"\nNo {SCHEMES_DIR} directory found. Creating sample...")
        os.makedirs(SCHEMES_DIR, exist_ok=True)
        
        # Create sample schemes
        samples = [
            {
                "name": "MGNREGA",
                "description": "100 days guaranteed wage employment for rural households",
                "state_code": "TN",
                "category": "employment",
                "criteria": {"min_age": 18, "residence": "Rural"},
                "impact_weight": 0.9
            },
            {
                "name": "PM-KISAN",
                "description": "Direct income support to farmers",
                "state_code": "TN", 
                "category": "agriculture",
                "criteria": {"land_owner": True},
                "impact_weight": 0.85
            }
        ]
        
        for i, scheme in enumerate(samples):
            with open(f"{SCHEMES_DIR}/sample_{i+1}.json", "w") as f:
                json.dump(scheme, f, indent=2)
        print(f"Created {len(samples)} sample scheme files")
    
    # Process all JSON files
    files = glob.glob(f"{SCHEMES_DIR}/*.json")
    print(f"\nFound {len(files)} scheme files to process")
    
    success = 0
    failed = 0
    
    for f in files:
        if ingest_scheme(f, token):
            success += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"INGESTION COMPLETE: {success} success, {failed} failed")
    print("=" * 50)
    
    # Show updated state
    list_current_schemes()

if __name__ == "__main__":
    main()
