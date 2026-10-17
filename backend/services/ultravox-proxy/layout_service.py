from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(title="ZELIA Layout Worker", version="1.0.0")

class Block(BaseModel):
    block_id: str
    text: str
    bbox: List[float]

class LayoutRequest(BaseModel):
    file_id: str
    blocks: List[Block]

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Layout Worker"}

@app.post("/analyze")
async def analyze_layout(request: LayoutRequest):
    # Stub implementation - returns blocks as-is
    return {
        "file_id": request.file_id,
        "fields": {
            block.block_id: {
                "text": block.text,
                "type": "text",
                "confidence": 0.85
            }
            for block in request.blocks
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)