import sqlite3
from pathlib import Path
import json

DB_PATH = Path("zelia_core.db")

def print_latest_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("== Household profiles ==")
    for row in cur.execute("SELECT id, created_at, profile_json FROM household_profile"):
        print("id:", row[0], "| created_at:", row[1])
        print("  profile_json:", row[2])
        try:
            print("  parsed:", json.loads(row[2]))
        except Exception:
            pass

    print("\n== Interviews ==")
    for row in cur.execute("SELECT id, household_id, started_at, channel FROM interview"):
        print(row)

    print("\n== Interview answers ==")
    for row in cur.execute(
        "SELECT interview_id, question_id, answer_raw, normalized_key, normalized_value "
        "FROM interview_answer"
    ):
        print(row)

    cur.close()
    conn.close()

if __name__ == "__main__":
    print_latest_data()
