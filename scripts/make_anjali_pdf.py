import json
import io
import fitz  # PyMuPDF
import psycopg2
from minio import Minio

# Form-filler logic for Anjali
conn = psycopg2.connect(host="localhost", port=5432, dbname="zelia", user="zelia", password="zelia_secure_2024")
cur = conn.cursor()
cur.execute("SELECT applicant_data FROM submissions WHERE submission_id = 313")
data = cur.fetchone()[0]
if isinstance(data, str): data = json.loads(data)

# Load template config
with open("data/ingestion/field_map_top5_calibrated.json", "r") as f:
    fmap = json.load(f)["templates"]["ka-widow-pension"]["fields"]

doc = fitz.open("dataset/govt/templates/pension1.pdf")
page = doc[0]

# Add text to exact coordinates matching the field map we built previously
def add_text(field, val):
    if field in fmap and val:
        x = fmap[field]['x']
        # PyMuPDF y coordinates are from the top of the page.
        # The field_map Y values we extracted earlier (e.g. 706.5) were measured from the BOTTOM in the extraction script.
        # However, the n8n/original system expected PyMuPDF standard coordinates (0 is top left).
        # In our extraction we used: y_bottom = page.rect.height - l["bbox"][3]
        # So to get PyMuPDF y back: y = page.rect.height - y_bottom
        y = page.rect.height - fmap[field]['y']
        
        point = fitz.Point(x, y)
        page.insert_text(point, str(val), fontsize=fmap[field]['fontSize'], color=(0, 0, 1))

add_text("name", data.get("name"))
add_text("date_of_birth", data.get("dob"))
add_text("gender", data.get("gender"))
add_text("address", data.get("address"))
add_text("aadhaar_number", data.get("aadhaar_number"))

pdf_bytes = doc.write()

# Push to MinIO
client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
client.put_object(
    "filled-forms", 
    "b4305d1da290289cb34a5b54892619e34382cc95ca0ab74f3856809e055d454f/kawidowpension_complete.pdf",
    io.BytesIO(pdf_bytes),
    len(pdf_bytes),
    content_type="application/pdf"
)

# Update the submission URI to point exactly where we dropped it
uri = "minio://filled-forms/b4305d1da290289cb34a5b54892619e34382cc95ca0ab74f3856809e055d454f/kawidowpension_complete.pdf"
cur.execute("UPDATE submissions SET filled_pdf_uri = %s WHERE submission_id = 313", (uri,))
conn.commit()

print("Anjali PDF Built and Uploaded to MinIO successfully!")
