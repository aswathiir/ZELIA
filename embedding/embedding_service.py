from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from annoy import AnnoyIndex
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "annoy_index.ann"
LABELS_PATH = BASE_DIR / "label_index.json"
MODEL_NAME = os.getenv("EMBED_MODEL_NAME", "all-MiniLM-L6-v2")
NUM_RESULTS = int(os.getenv("EMBED_NUM_RESULTS", 5))

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("embedding_service")


class SearchRequest(BaseModel):
    text: str = Field(..., description="Query text")
    k: int = Field(NUM_RESULTS, ge=1, le=50, description="Number of nearest neighbors to return")


class SearchResult(BaseModel):
    score: float
    field_id: str
    alias: str


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]


def _load_label_index(path: Path) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Label index file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Ensure deterministic ordering by integer key
    return [data[str(i)] for i in range(len(data))]


class EmbeddingEngine:
    def __init__(self) -> None:
        if not INDEX_PATH.exists():
            raise FileNotFoundError(
                f"Annoy index not found at {INDEX_PATH}. Run build_label_index.py first."
            )
        self.labels = _load_label_index(LABELS_PATH)
        self.model = SentenceTransformer(MODEL_NAME)
        self.index = AnnoyIndex(self.model.get_sentence_embedding_dimension(), "angular")
        self.index.load(str(INDEX_PATH))
        logger.info("Loaded Annoy index (%d items)", len(self.labels))

    def search(self, text: str, k: int) -> List[SearchResult]:
        if not text.strip():
            raise ValueError("Query text cannot be empty")
        vector = self.model.encode([text], convert_to_numpy=True)[0]
        ids, distances = self.index.get_nns_by_vector(vector, k, include_distances=True)
        results: List[SearchResult] = []
        for idx, dist in zip(ids, distances):
            meta = self.labels[idx]
            results.append(
                SearchResult(score=1 - dist / 2, field_id=meta["field_id"], alias=meta["alias"])
            )
        return results



@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing embedding engine via lifespan handler")
    app.state.engine = EmbeddingEngine()
    try:
        yield
    finally:
        if hasattr(app.state, "engine"):
            del app.state.engine


app = FastAPI(title="Embedding Service", version="1.0.0", lifespan=lifespan)


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    engine: EmbeddingEngine | None = getattr(app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    try:
        results = engine.search(req.text, req.k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SearchResponse(query=req.text, results=results)

@app.get("/health")
def health():
    return {"status": "healthy", "service": "embedding", "port": 8001}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Embedding Service on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
