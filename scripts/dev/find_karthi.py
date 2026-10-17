import psycopg2
import json

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="zelia", user="zelia", password="zelia_secure_2024"
)
cur = conn.cursor()
cur.execute("SELECT * FROM households LIMIT 10")
for row in cur.fetchall():
    print("Household:", row)

cur.execute("SELECT * FROM active_calls ORDER BY created_at DESC LIMIT 10")
for row in cur.fetchall():
    meta = row[4] if row[4] else {}
    if isinstance(meta, str):
        try:
            meta = json.loads(meta)
        except:
            pass
    if "karthi" in str(meta).lower():
        print("Call for Karthi:", row[0], meta)

cur.execute("SELECT * FROM submissions ORDER BY created_at DESC LIMIT 10")
for row in cur.fetchall():
    print("Submission:", row[0], row[1], row[3], row[4], row[6])

