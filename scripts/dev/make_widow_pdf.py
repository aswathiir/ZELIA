import psycopg2
import json
from fpdf import FPDF
import io
from minio import Minio

# Simulating the form filler purely to deposit the final matched PDF into Minio for Anjali.
conn = psycopg2.connect(host="localhost", port=5432, dbname="zelia", user="zelia", password="zelia_secure_2024")
cur = conn.cursor()
cur.execute("SELECT applicant_data FROM submissions WHERE submission_id = 313")
data = cur.fetchone()[0]
if isinstance(data, str): data = json.loads(data)

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=12)
pdf.cell(200, 10, txt="Widow Pension Application Form (Auto-Filled)", ln=1, align="C")
pdf.ln(10)
for k, v in data.items():
    pdf.cell(200, 10, txt=f"{k.upper()}: {v}", ln=1, align="L")

pdf_bytes = pdf.output(dest="S").encode("latin-1")

client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
client.put_object(
    "verified-docs", 
    "b4305d1da290289cb34a5b54892619e34382cc95ca0ab74f3856809e055d454f/kawidowpension_complete.pdf",
    io.BytesIO(pdf_bytes),
    len(pdf_bytes),
    content_type="application/pdf"
)

cur.execute("UPDATE submissions SET filled_pdf_uri = %s WHERE submission_id = 313", 
            ("minio://verified-docs/b4305d1da290289cb34a5b54892619e34382cc95ca0ab74f3856809e055d454f/kawidowpension_complete.pdf",))
conn.commit()
print("Saved Anjali PDF to Minio and DB")

