from flask import Flask, render_template, jsonify, request
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path

from schema import Profile, Scheme
from rule_engine import RuleEngine
from normalization import normalize_answer
from question_graph import load_graph

app = Flask(__name__)
DB_PATH = Path("zelia_core.db")
GRAPH_PATH = Path("question_graphs")

# Initialize Logic Components
rule_engine = RuleEngine()
# For Demo: hard code a scheme associated with the graph or load from DB
# ideally we load schemes from DB.
# For this sprint, we can stub a scheme list or add an endpoint to load them.

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("interview.html")

@app.route("/api/start_interview", methods=["POST"])
def start_interview():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Create household
    now = datetime.utcnow().isoformat()
    cur.execute("INSERT INTO household_profile (created_at, updated_at, profile_json) VALUES (?, ?, ?)",
                (now, now, "{}"))
    household_id = cur.lastrowid
    
    # Create interview
    cur.execute("INSERT INTO interview (household_id, started_at, channel) VALUES (?, ?, ?)",
                (household_id, now, "web_ui"))
    interview_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    
    # Load graph and get first question
    # Assuming standard graph for now
    graph = load_graph("tamil_nadu_v2") 
    first_q = graph.get_first_question()
    
    return jsonify({
        "status": "success",
        "interview_id": interview_id,
        "household_id": household_id,
        "question": first_q
    })

@app.route("/api/answer", methods=["POST"])
def submit_answer():
    data = request.json
    interview_id = data.get("interview_id")
    # household_id = data.get("household_id")
    question_id = data.get("question_id")
    raw_answer = data.get("answer")
    
    # Load Graph to find current question details and next question
    graph = load_graph("tamil_nadu_v2")
    current_q = graph.get_question(question_id)
    
    if not current_q:
        return jsonify({"error": "Invalid question ID"}), 400

    # Normalize
    norm_val = normalize_answer(current_q.get("type", "text"), raw_answer)
    norm_key = current_q.get("normalized_key")
    
    # Save answer to DB
    conn = get_db_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    
    cur.execute("""
        INSERT INTO interview_answer 
        (interview_id, question_id, answer_raw, normalized_key, normalized_value, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (interview_id, question_id, raw_answer, norm_key, json.dumps(norm_val), now))
    
    # Update Household Profile if it's a profile attribute
    if norm_key:
        # Fetch current profile
        cur.execute("SELECT household_id FROM interview WHERE id = ?", (interview_id,))
        row = cur.fetchone()
        if row:
            hh_id = row["household_id"]
            cur.execute("SELECT profile_json FROM household_profile WHERE id = ?", (hh_id,))
            prof_row = cur.fetchone()
            if prof_row:
                current_profile = json.loads(prof_row["profile_json"] or "{}")
                current_profile[norm_key] = norm_val
                
                cur.execute("UPDATE household_profile SET profile_json = ? WHERE id = ?", 
                            (json.dumps(current_profile), hh_id))

    conn.commit()
    conn.close()
    
    # Get Next Question
    next_q = graph.get_next_question(current_q)
    
    if next_q:
        return jsonify({
            "status": "continue",
            "question": next_q
        })
    else:
        # End of interview
        # Trigger Eligibility Check (in background or immediately)
        return jsonify({
            "status": "completed",
            "message": "Interview finished. Calculating eligibility..."
        })

@app.route("/api/upload_document", methods=["POST"])
def upload_document():
    # Stub for document upload
    # In a real app, this would save the file to object storage and run OCR
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Simulate OCR delay
    import time
    time.sleep(1)
    
    return jsonify({
        "status": "success",
        "message": "Document uploaded and verified.",
        "extracted_data": {"doc_type": "ration_card", "number": "TN123456"}
    })

@app.route("/api/results/<int:interview_id>", methods=["GET"])
def get_results(interview_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get household ID
    cur.execute("SELECT household_id FROM interview WHERE id = ?", (interview_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error": "Interview not found"}), 404
    
    hh_id = row["household_id"]
    
    # Get Profile
    cur.execute("SELECT profile_json FROM household_profile WHERE id = ?", (hh_id,))
    prof_row = cur.fetchone()
    profile_data = json.loads(prof_row["profile_json"] or "{}")
    
    # Comprehensive Scheme Registry
    schemes = [
        Scheme(
            id="scheme_old_age_pension",
            name="Indira Gandhi National Old Age Pension",
            description="Pension for senior citizens above 60 years in BPL households.",
            benefits="Rs. 1000/month",
            conditions={
                 "operator": "and",
                 "rules": [
                     {"field": "age", "op": "gte", "value": 60},
                     {"field": "income", "op": "lt", "value": 5000} # Implicit BPL proxy
                 ]
            }
        ),
        Scheme(
             id="scheme_widow_pension",
             name="Widow Pension Scheme",
             description="Financial assistance for widowed women.",
             benefits="Rs. 1000/month",
             conditions={
                 "operator": "and",
                 "rules": [
                     {"field": "marital_status", "op": "eq", "value": "widowed"},
                     {"field": "gender", "op": "eq", "value": "female"},
                     {"field": "age", "op": "gte", "value": 18}
                 ]
             }
        ),
        Scheme(
            id="scheme_pm_awas_yojana",
            name="PM Awas Yojana (Rural)",
            description="Housing subsidy for families living in kutcha houses or homeless.",
            benefits="Rs. 1.2 Lakhs for house construction",
            conditions={
                 "operator": "or",
                 "rules": [
                     {"field": "housing_type", "op": "eq", "value": "kutcha"},
                     {"field": "housing_type", "op": "eq", "value": "homeless"}
                 ]
            }
        ),
        Scheme(
            id="scheme_disability_pension",
            name="Disability Pension",
            description="Support for persons with disability certification.",
            benefits="Rs. 1500/month + Assistive Devices",
            conditions={
                "operator": "and",
                "rules": [
                    {"field": "disability", "op": "eq", "value": True}
                ]
            }
        )
    ]
    
    # Evaluate
    profile_obj = Profile(profile_data=profile_data)
    results = rule_engine.evaluate(profile_obj, schemes)
    
    return jsonify({
        "profile": profile_data,
        "results": [r.dict() for r in results]
    })

if __name__ == "__main__":
    # Ensure DB tables exist
    from db_init import init_db
    init_db()
    
    app.run(debug=True, port=5000)
