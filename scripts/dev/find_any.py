import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="zelia", user="zelia", password="zelia_secure_2024"
)
cur = conn.cursor()
cur.execute("SELECT count(*) FROM households")
print("households count:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM active_calls")
print("active_calls count:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM submissions")
print("submissions count:", cur.fetchone()[0])
