import sqlite3
from pathlib import Path

DB_PATH = Path("zelia_core.db")

def init_db():
    # 1. open a connection (creates file if not exists)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 2. create basic tables (temporary very small version)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS household_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT,
        updated_at TEXT,
        profile_json TEXT  -- Stores the accumulated normalized data
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS interview (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id INTEGER,
        started_at TEXT,
        completed_at TEXT,
        channel TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS interview_answer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        interview_id INTEGER,
        question_id TEXT,
        answer_raw TEXT,
        normalized_key TEXT,
        normalized_value TEXT, -- JSON string of value
        created_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS schemes (
        id TEXT PRIMARY KEY,
        name TEXT,
        description TEXT,
        benefits TEXT,
        rule_definition_json TEXT -- The logic for eligibility
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS eligibility_result (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        household_id INTEGER,
        scheme_id TEXT,
        is_eligible BOOLEAN,
        reasons_json TEXT,
        created_at TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ledger_event (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT,
        entity_id INTEGER,
        event_type TEXT,
        event_payload TEXT,
        timestamp TEXT
    );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("DB initialized at", DB_PATH)

if __name__ == "__main__":
    init_db()
