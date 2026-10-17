from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
import os
import uvicorn

app = FastAPI(title="ZELIA Submission Service", version="1.0.0")

DB_URL = os.getenv('DATABASE_URL', 'postgresql://zelia:zelia_secure_2024@localhost:5432/zelia')

class SubmissionRequest(BaseModel):
    household_hash: str
    scheme_id: str
    filled_pdf_uri: str
    chw_id: str

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Submission Service"}

@app.post("/submit")
async def submit_application(request: SubmissionRequest):
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO submissions (household_hash, scheme_id, filled_pdf_uri, chw_id, status)
            VALUES (%s, %s, %s, %s, 'pending_chw_review')
            RETURNING submission_id
        """, (request.household_hash, request.scheme_id, request.filled_pdf_uri, request.chw_id))
        
        submission_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"submission_id": str(submission_id), "status": "pending_chw_review"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)