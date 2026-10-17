import requests
import json
import time

BASE_URL = "http://localhost:5000/api"

def run_simulation():
    # 1. Start Interview
    print("Starting Interview...")
    try:
        resp = requests.post(f"{BASE_URL}/start_interview")
        if resp.status_code != 200:
             print("Failed to start:", resp.text)
             return
        data = resp.json()
        interview_id = data["interview_id"]
        print(f"Interview ID: {interview_id}")
        
        current_q = data["question"]
    except Exception as e:
        print("Error connecting to server. Is app.py running?", e)
        return

    # 2. Answer Questions
    answers = {
        "name": "Kumar",
        "age": "65",
        "gender": "male",
        "marital_status": "single" 
    }
    
    while current_q:
        q_text = current_q["text"]
        q_key = current_q.get("normalized_key")
        
        answer = answers.get(q_key, "data")
        print(f"Q: {q_text} -> Ans: {answer}")
        
        resp = requests.post(f"{BASE_URL}/answer", json={
            "interview_id": interview_id,
            "question_id": current_q["id"],
            "answer": answer
        })
        
        data = resp.json()
        if data["status"] == "continue":
            current_q = data["question"]
        elif data["status"] == "completed":
            print("Interview Completed.")
            break
        else:
            print("Error:", data)
            break

    # 3. Get Results
    print("Fetching Results...")
    resp = requests.get(f"{BASE_URL}/results/{interview_id}")
    results = resp.json()
    
    print("\n--- Profile ---")
    print(json.dumps(results["profile"], indent=2))
    
    print("\n--- Eligibility ---")
    for r in results["results"]:
        status = "ELIGIBLE" if r["eligible"] else "NOT ELIGIBLE"
        print(f"{r['scheme_id']}: {status}")
        if not r["eligible"]:
            print(f"  Reasons: {r['reasons']}")
            
            
if __name__ == "__main__":
    # Ensure Test DB is ready (optional if running against same DB)
    run_simulation()
