import json
import io
import fitz
import psycopg2
from minio import Minio

def draw_pdf(template_path, fields, fmap):
    doc = fitz.open(template_path)
    page = doc[0]
    out_pages = 1
    
    for fname, val in fields.items():
        if not val or fname not in fmap: continue
        pos = fmap[fname]
        p_num = int(pos.get("page", 0))
        if p_num >= len(doc): continue
        
        while p_num >= out_pages:
            out_pages += 1
        
        tgt = doc[p_num]
        
        x = float(pos.get("x", 100))
        y = float(pos.get("y", 100))
        fsz = float(pos.get("fontSize", 11.0))
        
        tgt.insert_text((x, y), str(val), fontsize=fsz, fontname="helv", color=(0,0,0))
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def upload(client, bucket, key, data):
    client.put_object(bucket, key, io.BytesIO(data), len(data), content_type="application/pdf")
    print(f"Uploaded {key}")

def main():
    client = Minio("localhost:9000", access_key="minioadmin", secret_key="minioadmin", secure=False)
    
    with open("data/ingestion/field_map_top5_calibrated.json") as f:
        maps = json.load(f)["templates"]
        
    # Anjali
    anjali_hash = "b727b0f447dd8b7ac2fe87561764d5637cbc65c88e76abfb418e30e6bdcfce98"
    anjali_fields = {
        "name": "Anjali",
        "age": "54",
        "gender": "female",
        "address": "Bangalore, Karnataka",
        "marital_status": "widowed"
    }
    anjali_pdf = draw_pdf("dataset/govt/templates/pension1.pdf", anjali_fields, maps["ka-widow-pension"]["fields"])
    anjali_key = f"{anjali_hash}/filled_forms/kawidowpension_complete.pdf"
    upload(client, "filled-forms", anjali_key, anjali_pdf)
    
    # Karthick
    karthik_hash = "6730b74fd2da9fa2974498fe04c906275c8369a9ecf9942a768dd5abfe90d813"
    karthik_fields = {
        "name": "Karthick H",
        "age": "68",
        "gender": "male",
        "address": "Mysuru, Karnataka"
    }
    karthik_pdf = draw_pdf("dataset/govt/templates/pension1.pdf", karthik_fields, maps["pension1.pdf"]["fields"])
    karthik_key = f"{karthik_hash}/filled_forms/kaoldagepension_complete.pdf"
    upload(client, "filled-forms", karthik_key, karthik_pdf)
    
    # Update DB
    conn = psycopg2.connect(host="localhost", port=5432, dbname="zelia", user="zelia", password="zelia_secure_2024")
    cur = conn.cursor()
    cur.execute("UPDATE submissions SET filled_pdf_uri = %s WHERE household_hash = %s", (f"filled-forms/{anjali_key}", anjali_hash))
    cur.execute("UPDATE submissions SET filled_pdf_uri = %s WHERE household_hash = %s", (f"filled-forms/{karthik_key}", karthik_hash))
    conn.commit()
    print("Database updated.")

if __name__ == "__main__":
    main()
