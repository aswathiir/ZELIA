import sqlite3
from pathlib import Path
from datetime import datetime
import json

DB_PATH = Path("zelia_core.db")

def insert_fake_interview():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) create a fake household profile (empty for now)
    profile = {
        "head_of_household_name": "Kumarsami",
        "head_age": 52,
        "monthly_income": 8000
    }
    now = datetime.utcnow().isoformat()

    cur.execute(
        """
        INSERT INTO household_profile (created_at, updated_at, profile_json)
        VALUES (?, ?, ?)
        """,
        (now, now, json.dumps(profile))
    )
    household_id = cur.lastrowid

    # 2) create an interview row
    cur.execute(
        """
        INSERT INTO interview (household_id, started_at, completed_at, channel)
        VALUES (?, ?, ?, ?)
        """,
        (household_id, now, now, "text_desktop")
    )
    interview_id = cur.lastrowid

    # 3) insert a couple of answers
    answers = [
        {
            "question_id": "q_head_name",
            "answer_raw": "Kumarsami",
            "normalized_key": "head_of_household_name",
            "normalized_value": "Kumarsami",
        },
        {
            "question_id": "q_head_age",
            "answer_raw": "52",
            "normalized_key": "head_age",
            "normalized_value": "52",
        },
    ]

    for ans in answers:
        cur.execute(
            """
            INSERT INTO interview_answer
            (interview_id, question_id, answer_raw,
             normalized_key, normalized_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                interview_id,
                ans["question_id"],
                ans["answer_raw"],
                ans["normalized_key"],
                ans["normalized_value"],
                now,
            )
        )

    conn.commit()
    cur.close()
    conn.close()
    print("Inserted fake household_id =", household_id, "interview_id =", interview_id)

if __name__ == "__main__":
    insert_fake_interview()
