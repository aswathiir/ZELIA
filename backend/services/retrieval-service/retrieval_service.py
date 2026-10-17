"""
ZELIA Retrieval Service with Hybrid Vector Search
Supports both Pinecone (cloud) and Annoy (local) for vector embeddings
Port: 8007
"""

from flask import Flask, request, jsonify
from annoy import AnnoyIndex
from sentence_transformers import SentenceTransformer
import psycopg2
import psycopg2.extras
import numpy as np
import os
import logging
from datetime import datetime
import json
from typing import Optional

# Optional Pinecone import
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("Pinecone not available, using Annoy only")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
EMBEDDING_DIM = 384
ANNOY_TREES = 50  # Trade-off: more trees = better accuracy but slower
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/zelia')

# Pinecone configuration (optional)
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', 'zelia-schemes')
PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT', 'us-east-1')
PINECONE_NAMESPACE = os.getenv('PINECONE_NAMESPACE', 'schemes')
PINECONE_REQUIRED = os.getenv('PINECONE_REQUIRED', 'false').lower() == 'true'
RETRIEVAL_MODE = os.getenv('RETRIEVAL_MODE', 'pinecone_primary_annoy_fallback').strip()
USE_PINECONE = PINECONE_AVAILABLE and PINECONE_API_KEY

# Global state
model = None
annoy_index = None
pinecone_index = None
pc_client = None
doc_id_map = {}
index_built = False


def ensure_annoy_index():
    """Ensure Annoy index is available for fallback lookups."""
    global index_built
    if index_built and annoy_index and len(doc_id_map) > 0:
        return True
    try:
        rebuild_annoy_index()
        return index_built and annoy_index is not None
    except Exception as e:
        logger.warning(f"Annoy index unavailable: {e}")
        return False


def parse_embedding(raw) -> Optional[np.ndarray]:
    """Best-effort conversion of stored embedding to fixed-size float vector."""
    if raw is None:
        return None
    arr = None
    try:
        if isinstance(raw, np.ndarray):
            arr = raw.astype(np.float32)
        elif isinstance(raw, (list, tuple)):
            arr = np.asarray(raw, dtype=np.float32)
        elif isinstance(raw, str):
            loaded = json.loads(raw)
            arr = np.asarray(loaded, dtype=np.float32)
        else:
            # Try generic iteration (e.g. memoryview)
            arr = np.asarray(list(raw), dtype=np.float32)
    except Exception:
        return None

    if arr is None:
        return None
    arr = np.ravel(arr)
    if arr.size != EMBEDDING_DIM:
        return None
    return arr

def get_db_connection():
    """Create PostgreSQL connection"""
    return psycopg2.connect(DB_URL)

def load_model():
    """Load sentence transformer model"""
    global model
    if model is None:
        logger.info(f"Loading model: {MODEL_NAME}")
        model = SentenceTransformer(MODEL_NAME)
        logger.info("Model loaded successfully")
    return model

def init_pinecone():
    """Initialize Pinecone client and index (if configured)"""
    global pc_client, pinecone_index
    
    if not USE_PINECONE:
        logger.info("Pinecone not configured, using Annoy only")
        return False
    
    try:
        logger.info("Initializing Pinecone...")
        pc_client = Pinecone(api_key=PINECONE_API_KEY)
        
        # Check if index exists
        existing_indexes = [idx.name for idx in pc_client.list_indexes()]
        
        if PINECONE_INDEX_NAME not in existing_indexes:
            logger.info(f"Creating Pinecone index: {PINECONE_INDEX_NAME}")
            pc_client.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=EMBEDDING_DIM,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=PINECONE_ENVIRONMENT
                )
            )
        
        pinecone_index = pc_client.Index(PINECONE_INDEX_NAME)
        logger.info(f"Pinecone index '{PINECONE_INDEX_NAME}' ready")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Pinecone: {e}")
        logger.warning("Falling back to Annoy only")
        return False

def rebuild_annoy_index():
    """Rebuild Annoy index from PostgreSQL embeddings"""
    global annoy_index, doc_id_map, index_built
    
    logger.info("Rebuilding Annoy index from database...")
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Fetch all embeddings
    cur.execute("""
        SELECT id, document_id, embedding, metadata, text_chunk, created_at
        FROM document_embeddings
        ORDER BY id
    """)
    
    rows = cur.fetchall()
    
    # Initialize new Annoy index
    annoy_index = AnnoyIndex(EMBEDDING_DIM, 'angular')
    doc_id_map = {}
    
    valid_idx = 0
    skipped = 0
    for row in rows:
        embedding = parse_embedding(row.get('embedding'))
        if embedding is None:
            skipped += 1
            continue

        # Add to Annoy index
        annoy_index.add_item(valid_idx, embedding.tolist())

        # Store mapping
        doc_id_map[valid_idx] = {
            'db_id': row['id'],
            'document_id': row['document_id'],
            'metadata': row['metadata'],
            'text_chunk': row['text_chunk'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None
        }
        valid_idx += 1
    
    # Build index
    if len(doc_id_map) > 0:
        logger.info(f"Building Annoy index with {len(doc_id_map)} vectors and {ANNOY_TREES} trees (skipped={skipped})...")
        annoy_index.build(ANNOY_TREES)
        index_built = True
    else:
        logger.warning(f"No valid embeddings found for Annoy index (skipped={skipped}).")
        index_built = False
    
    cur.close()
    conn.close()
    
    logger.info(f"Annoy index built status={index_built}, total_vectors={len(doc_id_map)}")
    return len(doc_id_map)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    if pinecone_index:
        pinecone_status = 'connected'
    elif PINECONE_REQUIRED:
        pinecone_status = 'required_but_unavailable'
    else:
        pinecone_status = 'not_configured'
    annoy_ready = bool(index_built and annoy_index and len(doc_id_map) > 0)
    overall_status = 'healthy'
    if PINECONE_REQUIRED and not pinecone_index and not annoy_ready:
        overall_status = 'degraded'
    elif not pinecone_index and not annoy_ready:
        overall_status = 'degraded'
    
    return jsonify({
        'status': overall_status,
        'service': 'retrieval-service',
        'retrieval_mode': RETRIEVAL_MODE,
        'model': MODEL_NAME,
        'embedding_dim': EMBEDDING_DIM,
        'annoy': {
            'index_built': index_built,
            'ready': annoy_ready,
            'total_vectors': len(doc_id_map)
        },
        'pinecone': {
            'status': pinecone_status,
            'index_name': PINECONE_INDEX_NAME if USE_PINECONE else None,
            'required': PINECONE_REQUIRED
        },
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/embed', methods=['POST'])
def embed_text():
    """
    Generate embedding and store in database
    
    Request:
    {
        "text": "Income certificate for widow pension",
        "document_id": "doc_12345",
        "metadata": {
            "call_id": "call_001",
            "citizen_id": "CIT001",
            "scheme_id": "widow-pension",
            "document_type": "income_certificate"
        }
    }
    
    Response:
    {
        "vector_id": 42,
        "document_id": "doc_12345",
        "embedding_dim": 384,
        "stored": true,
        "index_rebuilt": true
    }
    """
    try:
        data = request.json
        text = data.get('text', '')
        document_id = data.get('document_id')
        metadata = data.get('metadata', {})
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        if not document_id:
            return jsonify({'error': 'document_id is required'}), 400
        
        # Generate embedding
        model_instance = load_model()
        embedding = model_instance.encode(text).tolist()
        
        # Store in PostgreSQL
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO document_embeddings 
            (document_id, text_chunk, embedding, metadata, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            RETURNING id
        """, (
            document_id,
            text[:5000],  # Truncate very long text
            embedding,
            json.dumps(metadata)
        ))
        
        vector_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        # Rebuild Annoy index (in production, do this async or periodically)
        rebuild_annoy_index()
        
        # Also store in Pinecone if available
        if pinecone_index is not None:
            try:
                pinecone_index.upsert(vectors=[(
                    document_id,  # ID
                    embedding,    # Vector
                    metadata      # Metadata
                )], namespace=PINECONE_NAMESPACE)
                logger.info(f"Stored in Pinecone: {document_id}")
            except Exception as e:
                logger.warning(f"Pinecone upsert failed: {e}")
        
        logger.info(f"Embedded text for document {document_id}, vector_id: {vector_id}")
        
        return jsonify({
            'vector_id': vector_id,
            'document_id': document_id,
            'embedding_dim': len(embedding),
            'stored': True,
            'index_rebuilt': True,
            'pinecone_stored': pinecone_index is not None
        })
        
    except Exception as e:
        logger.error(f"Error in embed_text: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/embed-query', methods=['POST'])
def embed_query():
    """
    Generate embedding for a query string
    
    Request:
    {
        "text": "widow pension application form",
        "return_vector": true
    }
    
    Response:
    {
        "embedding": [0.123, 0.456, ...],  # 384-dim vector
        "dimension": 384,
        "model": "sentence-transformers/all-MiniLM-L6-v2"
    }
    """
    try:
        data = request.json
        text = data.get('text', '')
        
        # Generate embedding
        model_instance = load_model()
        embedding = model_instance.encode(text).tolist()
        
        return jsonify({
            'embedding': embedding,
            'dimension': len(embedding),
            'model': MODEL_NAME
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['POST'])
def search_similar():
    """
    Search for similar documents using Annoy index
    
    Request:
    {
        "query": "widow pension eligibility",
        "top_k": 5,
        "filters": {
            "scheme_id": "widow-pension",
            "document_type": "income_certificate"
        }
    }
    
    Response:
    [
        {
            "document_id": "doc_12345",
            "text": "Income certificate text...",
            "similarity": 0.92,
            "metadata": {...},
            "db_id": 42
        },
        ...
    ]
    """
    global index_built
    
    try:
        # Rebuild index if not built
        if not index_built or annoy_index is None:
            logger.info("Index not built, rebuilding...")
            rebuild_annoy_index()
        
        data = request.json
        query = data.get('query', '')
        top_k = data.get('top_k', 5)
        filters = data.get('filters', {})
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Generate query embedding
        model_instance = load_model()
        query_vector = model_instance.encode(query)
        
        # Search Annoy index
        # Fetch more than top_k to allow for filtering
        search_count = min(top_k * 3, len(doc_id_map))
        
        if search_count == 0:
            return jsonify([])
        
        indices, distances = annoy_index.get_nns_by_vector(
            query_vector,
            search_count,
            include_distances=True
        )
        
        # Apply filters and format results
        results = []
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        for idx, distance in zip(indices, distances):
            doc_info = doc_id_map.get(idx)
            if not doc_info:
                continue
            
            # Fetch additional data if needed
            cur.execute("""
                SELECT de.*, s.scheme_id, s.applicant_data, s.status
                FROM document_embeddings de
                LEFT JOIN submissions s ON de.document_id = s.submission_id::text
                WHERE de.id = %s
            """, (doc_info['db_id'],))
            
            row = cur.fetchone()
            if not row:
                continue
            
            # Parse metadata
            doc_metadata = row['metadata'] if isinstance(row['metadata'], dict) else json.loads(row['metadata'] or '{}')
            
            # Apply filters
            filter_match = True
            for filter_key, filter_value in filters.items():
                if doc_metadata.get(filter_key) != filter_value:
                    filter_match = False
                    break
            
            if not filter_match:
                continue
            
            # Calculate cosine similarity from angular distance
            # Annoy angular distance: d = 2 * (1 - cos_sim)
            # Therefore: cos_sim = 1 - (d / 2)
            similarity = 1 - (distance / 2)
            
            results.append({
                'document_id': doc_info['document_id'],
                'text': row['text_chunk'],
                'similarity': float(similarity),
                'metadata': doc_metadata,
                'db_id': doc_info['db_id'],
                'created_at': doc_info['created_at']
            })
            
            if len(results) >= top_k:
                break
        
        cur.close()
        conn.close()
        
        logger.info(f"Search for '{query}' returned {len(results)} results")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error in search_similar: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/search/hybrid', methods=['POST'])
def search_hybrid():
    """
    Hybrid search: Pinecone (if available) + Annoy fallback
    
    Request:
    {
        "query": "widow pension eligibility",
        "top_k": 5,
        "use_pinecone_first": true
    }
   """
    try:
        data = request.json
        query = data.get('query', '')
        top_k = data.get('top_k', 5)
        use_pinecone_first = data.get('use_pinecone_first', True)
        legacy_array = bool(data.get('legacy_array', False))
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Generate embedding
        model_instance = load_model()
        query_vector = model_instance.encode(query).tolist()
        
        results = []
        sources_used = []
        
        annoy_ready = ensure_annoy_index()

        if PINECONE_REQUIRED and not pinecone_index and not annoy_ready:
            return jsonify({
                'error': 'Pinecone is required but unavailable',
                'status': 'retrieval_unavailable',
                'details': 'Set PINECONE_API_KEY and ensure index connectivity, or enable Annoy fallback index'
            }), 503

        pinecone_allowed = RETRIEVAL_MODE in {'pinecone_primary_annoy_fallback', 'pinecone_only'}
        annoy_allowed = RETRIEVAL_MODE in {'pinecone_primary_annoy_fallback', 'annoy_only'}

        if RETRIEVAL_MODE == 'pinecone_only':
            annoy_ready = False

        # Try Pinecone first (if available and preferred)
        if pinecone_allowed and pinecone_index and use_pinecone_first:
            try:
                pc_results = pinecone_index.query(
                    vector=query_vector,
                    top_k=top_k,
                    include_metadata=True,
                    namespace=PINECONE_NAMESPACE
                )
                
                for match in pc_results['matches']:
                    results.append({
                        'document_id': match['id'],
                        'similarity': float(match['score']),
                        'metadata': match.get('metadata', {}),
                        'source': 'pinecone'
                    })
                if pc_results.get('matches'):
                    sources_used.append('pinecone')
                
                logger.info(f"Pinecone returned {len(results)} results")
                
                if len(results) >= top_k and RETRIEVAL_MODE != 'annoy_only':
                    if legacy_array:
                        return jsonify(results[:top_k])
                    return jsonify({
                        'status': 'ok',
                        'retrieval_mode': RETRIEVAL_MODE,
                        'source_used': 'pinecone',
                        'result_count': len(results[:top_k]),
                        'results': results[:top_k]
                    })
                    
            except Exception as e:
                logger.error(f"Pinecone search failed: {e}")
        
        # Fallback to Annoy or supplement results
        if annoy_allowed and len(results) < top_k:
            annoy_needed = top_k - len(results)

            if annoy_ready and annoy_index and len(doc_id_map) > 0:
                indices, distances = annoy_index.get_nns_by_vector(
                    query_vector,
                    annoy_needed,
                    include_distances=True
                )
                
                for idx, distance in zip(indices, distances):
                    doc_info = doc_id_map.get(idx)
                    if doc_info:
                        results.append({
                            'document_id': doc_info['document_id'],
                            'similarity': float(1 - (distance / 2)),
                            'metadata': doc_info.get('metadata', {}),
                            'text': doc_info.get('text_chunk', ''),
                            'source': 'annoy'
                        })
                if indices:
                    sources_used.append('annoy')
        
        final_results = results[:top_k]
        if not final_results:
            return jsonify({
                'status': 'retrieval_unavailable',
                'retrieval_mode': RETRIEVAL_MODE,
                'source_used': 'none',
                'result_count': 0,
                'results': [],
                'error': 'No retrieval sources available'
            }), 503

        if len(set(sources_used)) > 1:
            source_used = 'hybrid'
        elif sources_used:
            source_used = sources_used[0]
        else:
            source_used = 'unknown'

        if legacy_array:
            return jsonify(final_results)
        return jsonify({
            'status': 'ok',
            'retrieval_mode': RETRIEVAL_MODE,
            'source_used': source_used,
            'result_count': len(final_results),
            'results': final_results
        })
        
    except Exception as e:
        logger.error(f"Hybrid search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/rebuild-index', methods=['POST'])
def rebuild_index():
    """Manually trigger index rebuild"""
    try:
        count = rebuild_annoy_index()
        return jsonify({
            'status': 'success',
            'message': 'Index rebuilt successfully',
            'total_vectors': count
        })
    except Exception as e:
        logger.error(f"Error rebuilding index: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get index statistics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) FROM document_embeddings")
        total_embeddings = cur.fetchone()[0]
        
        cur.execute("""
            SELECT 
                metadata->>'document_type' as doc_type,
                COUNT(*) as count
            FROM document_embeddings
            GROUP BY metadata->>'document_type'
        """)
        
        type_stats = {row[0]: row[1] for row in cur.fetchall()}
        
        cur.close()
        conn.close()
        
        return jsonify({
            'total_embeddings': total_embeddings,
            'index_vectors': len(doc_id_map),
            'index_built': index_built,
            'embedding_dim': EMBEDDING_DIM,
            'annoy_trees': ANNOY_TREES,
            'document_types': type_stats
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Initialize services (Runs on Gunicorn start)
logger.info("Starting ZELIA Retrieval Service...")
logger.info(f"Pinecone enabled: {USE_PINECONE}")
logger.info(f"Retrieval mode: {RETRIEVAL_MODE}")
load_model()
if USE_PINECONE:
    init_pinecone()
if not os.getenv('SKIP_ANNOY_INDEX'):
    try:
        rebuild_annoy_index()
    except Exception:
        pass

if __name__ == '__main__':
    # Load model and build initial index
    logger.info("Starting Retrieval Service...")
    load_model()
    
    try:
        rebuild_annoy_index()
    except Exception as e:
        logger.warning(f"Could not build initial index: {e}")
        logger.info("Index will be built on first request")
    
    app.run(host='0.0.0.0', port=8007, debug=False)
