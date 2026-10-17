import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

def run_full_verification():
    print("--- Starting Phase 2 Verification ---")
    
    # 1. Start Interview
    resp = requests.post(f"{BASE_URL}/start_interview")
    data = resp.json()
    interview_id = data["interview_id"]
    current_q = data["question"]
    print(f"Session Started. ID: {interview_id}")

    # 2. Simulate User Answers (Widow, 62, Kutcha House)
    # Expected: Widow Pension, Old Age Pension, PM Awas Yojana
    answers = {
        "q_name": "Lakshmi",
        "q_age": "62",
        "q_gender": "Female",
        "q_marital": "Widowed",
        "q_children_count": "0",
        "q_occupation": "Unemployed",
        "q_income": "3000",
        "q_housing": "Kutcha",
        "q_disability": "No",
        "q_docs": "Ration Card, Aadhar" # Multi-select
    }

    while current_q:
        q_id = current_q["id"]
        q_text = current_q["text"]
        ans = answers.get(q_id, "Unknown")
        
        print(f"[{q_id}] {q_text} -> {ans}")
        
        # Simulate Doc Upload for q_docs
        if q_id == "q_docs":
            print("   [Simulating Document Upload...]")
            files = {'file': ('doc.jpg', b'fake_image_content')}
            up_resp = requests.post(f"{BASE_URL}/upload_document", files=files)
            print("   Upload Result:", up_resp.json()["message"])

        resp = requests.post(f"{BASE_URL}/answer", json={
            "interview_id": interview_id,
            "question_id": q_id,
            "answer": ans
        })
        
        data = resp.json()
        if data["status"] == "continue":
            current_q = data["question"]
        else:
            current_q = None

    # 3. Check Eligibility
    print("\n--- Checking Eligibility ---")
    resp = requests.get(f"{BASE_URL}/results/{interview_id}")
    results = resp.json()
    
    eligible_schemes = [r["scheme_id"] for r in results["results"] if r["eligible"]]
    print(f"Eligible Schemes: {eligible_schemes}")
    
    # Assertions
    expected = [
        "scheme_old_age_pension", 
        "scheme_widow_pension", 
        "scheme_pm_awas_yojana"
    ]
    missing = [s for s in expected if s not in eligible_schemes]
    
    if not missing:
        print("✅ SUCCESS: All expected schemes matched!")
    else:
        print(f"❌ FAILURE: Missing schemes: {missing}")

if __name__ == "__main__":
    try:
        run_full_verification()
    except Exception as e:
        print(f"Test Failed: {e}")
