import sqlite3
from pathlib import Path
from datetime import datetime
import json

from question_graph import load_graph  # uses your previous file

DB_PATH = Path("zelia_core.db")

def start_interview():
    # 1) open DB connection
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 2) create a household placeholder (empty profile_json for now)
    now = datetime.utcnow().isoformat()
    empty_profile = {}
    cur.execute(
        """
        INSERT INTO household_profile (created_at, updated_at, profile_json)
        VALUES (?, ?, ?)
        """,
        (now, now, json.dumps(empty_profile))
    )
    household_id = cur.lastrowid

    # 3) create interview row
    cur.execute(
        """
        INSERT INTO interview (household_id, started_at, completed_at, channel)
        VALUES (?, ?, ?, ?)
        """,
        (household_id, now, None, "cli_desktop")
    )
    interview_id = cur.lastrowid

    print(f"Started interview_id={interview_id} for household_id={household_id}")

    # 4) load question graph
    graph = load_graph()  # tamil_nadu_v1 by default
    q = graph.get_first_question()

    # 5) loop through questions, ask via input(), store answers
    while q is not None:
        print()
        print("Q:", q["text"])
        raw_answer = input("Your answer: ").strip()

        normalized_key = q.get("normalized_key")
        normalized_value = raw_answer  # later you will add proper normalization

        cur.execute(
            """
            INSERT INTO interview_answer
            (interview_id, question_id, answer_raw,
             normalized_key, normalized_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                interview_id,
                q["id"],
                raw_answer,
                normalized_key,
                normalized_value,
                datetime.utcnow().isoformat(),
            )
        )

        # go to next question
        q = graph.get_next_question(q)

    # 6) mark interview completed
    cur.execute(
        "UPDATE interview SET completed_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), interview_id)
    )

    conn.commit()
    cur.close()
    conn.close()
    print("\nInterview completed and saved to DB.")

if __name__ == "__main__":
    start_interview()
