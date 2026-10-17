from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from annoy import AnnoyIndex
import json
import uvicorn
import sys

app = FastAPI(
    title='ZELIA Embedding Service',
    version='1.0.0',
    description='Semantic field mapping for government forms'
)

# Global variables
model = None
annoy_index = None
label_metadata = None
embedding_dim = None

@app.on_event('startup')
async def startup_event():
    global model, annoy_index, label_metadata, embedding_dim
    
    print('Starting ZELIA Embedding Service...')
    print('=' * 60)
    
    try:
        print('Loading model...')
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        embedding_dim = model.get_sentence_embedding_dimension()
        print(f'Model loaded (dim={embedding_dim})')
        
        print('Loading label metadata...')
        with open('label_index.json', 'r', encoding='utf-8') as f:
            label_metadata = json.load(f)
        print(f'Loaded {len(label_metadata)} labels')
        
        print('Loading Annoy index...')
        annoy_index = AnnoyIndex(embedding_dim, 'angular')
        annoy_index.load('annoy_index.ann')
        print(f'Index loaded')
        
        print('=' * 60)
        print('Service ready!')
        print(f'   Listening on http://0.0.0.0:8001')
        print(f'   API docs: http://0.0.0.0:8001/docs')
        print('=' * 60)
        
    except FileNotFoundError as e:
        print(f'ERROR: Index files not found. Run build_label_index.py first!', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'ERROR: {str(e)}', file=sys.stderr)
        sys.exit(1)

class TextBlock(BaseModel):
    block_id: str
    text: str
    lang: Optional[str] = 'en'
    bbox: Optional[List[float]] = None

class MappingRequest(BaseModel):
    file_id: str
    blocks: List[TextBlock]
    top_k: int = 5
    confidence_threshold: float = 0.75

class MappingCandidate(BaseModel):
    field_id: str
    canonical: str
    score: float
    matched_text: str
    field_type: str
    required: bool

class BlockMapping(BaseModel):
    block_id: str
    original_text: str
    candidates: List[MappingCandidate]
    top_match: Optional[MappingCandidate]
    auto_accepted: bool

class MappingResponse(BaseModel):
    file_id: str
    mappings: List[BlockMapping]
    stats: dict

@app.get('/health')
async def health():
    return {
        'status': 'healthy',
        'model': 'paraphrase-multilingual-MiniLM-L12-v2',
        'indexed_labels': len(label_metadata) if label_metadata else 0,
        'embedding_dim': embedding_dim
    }

class EmbedRequest(BaseModel):
    text: str

class EmbedResponse(BaseModel):
    embedding: List[float]
    dimension: int

@app.post('/embed', response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """Generate embedding for text - used by retrieval service"""
    if not model:
        raise HTTPException(503, 'Model not loaded')
    
    embedding = model.encode([request.text])[0].tolist()
    return EmbedResponse(
        embedding=embedding,
        dimension=len(embedding)
    )

@app.post('/map_blocks', response_model=MappingResponse)
async def map_blocks(request: MappingRequest):
    if not request.blocks:
        raise HTTPException(400, 'No blocks provided')
    
    mappings = []
    auto_accept_count = 0
    
    for block in request.blocks:
        # Encode block text
        query_embedding = model.encode([block.text])[0]
        
        # Search Annoy index
        indices, distances = annoy_index.get_nns_by_vector(
            query_embedding,
            request.top_k,
            include_distances=True
        )
        
        # Convert angular distance to similarity score
        candidates = []
        for idx, dist in zip(indices, distances):
            # Angular to cosine similarity: sim = 1 - (dist^2 / 2)
            similarity = max(0, min(1, 1 - (dist ** 2) / 2))
            meta = label_metadata[idx]
            
            candidates.append(MappingCandidate(
                field_id=meta['field_id'],
                canonical=meta['canonical'],
                score=round(similarity, 4),
                matched_text=meta['text'],
                field_type=meta['field_type'],
                required=meta['required']
            ))
        
        # Sort by score
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        # Determine top match and auto-accept
        top = candidates[0] if candidates else None
        auto_accepted = (top.score >= request.confidence_threshold) if top else False
        
        if auto_accepted:
            auto_accept_count += 1
        
        mappings.append(BlockMapping(
            block_id=block.block_id,
            original_text=block.text,
            candidates=candidates,
            top_match=top,
            auto_accepted=auto_accepted
        ))
    
    return MappingResponse(
        file_id=request.file_id,
        mappings=mappings,
        stats={
            'total': len(mappings),
            'auto_accepted': auto_accept_count,
            'needs_review': len(mappings) - auto_accept_count,
            'auto_accept_rate': round(auto_accept_count / len(mappings) * 100, 2) if mappings else 0
        }
    )

@app.get('/')
async def root():
    return {
        'service': 'ZELIA Embedding Service',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/health',
            'map_blocks': '/map_blocks',
            'docs': '/docs'
        }
    }

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8001)