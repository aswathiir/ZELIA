import requests
import json
import sys

def test_submission_creation():
    url = "http://localhost:8009/submissions" # submission-service internal port 8004 is mapped to 8009
    
    # Karthik 5 data from database
    payload = {
        "scheme_id": "nsap-ignoaps",
        "applicant_data": {
            "dob": "02/10/2007",
            "name": "Karthik 5",
            "gender": "Male",
            "address": "Isio Srinivasan; 2/202 , chennathur; #Chenathur; PO: Chennathur;, DiST: ] Krishnagir; Tamil Nadu 63",
            "pincode": "635109", # Added a sample pincode if missing, though null in DB
            "aadhaar_number": "4630 9798 6614"
        },
        "eligibility": {
            "is_eligible": True,
            "reason": "Meets criteria based on document analysis"
        },
        "status": "pending_review",
        "confidence": 0.88,
        "document_reference": "ded52a07-8cd2-41d8-b22b-ad070743e771",
        "metadata": {
            "household_hash": "1d0d99f65d941c9dda7f5d80af5473e8c7440356de05a798548cc4fca94ed997"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-user-role": "system" # Required if ENFORCE_CHW_ROLE is true
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        print("\nSuccess! Submission created.")
        print(f"Submission ID: {result.get('submission_id')}")
        print(f"Status: {result.get('status')}")
        print(f"Filled PDF URI: {result.get('filled_pdf_uri')}")
        
        if result.get('filled_pdf_uri'):
            print("\nVerification Passed: PDF Filling logic was triggered and returned an URI.")
        else:
            print("\nWarning: No PDF URI returned. Check if 'templates/pension1.pdf' exists in MinIO.")
            
    except Exception as e:
        print(f"\nError: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)

if __name__ == "__main__":
    test_submission_creation()
