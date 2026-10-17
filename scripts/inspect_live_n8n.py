import psycopg2
import json

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="zelia", user="zelia", password="zelia_secure_2024"
)
cur = conn.cursor()
cur.execute('SELECT "activeVersionId", nodes::text FROM workflow_entity WHERE id = %s', ("IJPL6b4yqlOayL0N",))
row = cur.fetchone()
nodes = json.loads(row[1])
for node in nodes:
    if node.get("name") == "Generate PDF (pdf-lib)":
        print(node["parameters"]["jsCode"])
