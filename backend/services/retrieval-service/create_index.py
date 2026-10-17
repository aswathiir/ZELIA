"""
Create vector index for scheme data
Generates embeddings and builds Annoy index for fast similarity search
"""
import psycopg2
from sentence_transformers import SentenceTransformer
from annoy import AnnoyIndex
import json
import os
from tqdm import tqdm

# Configuration
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/postgres')
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
DIM = 384  # all-MiniLM-L6-v2 embedding dimension
OUTPUT_DIR = '/app/data'
INDEX_PATH = os.path.join(OUTPUT_DIR, 'scheme_vectors.ann')
METADATA_PATH = os.path.join(OUTPUT_DIR, 'scheme_metadata.json')
N_TREES = 10  # Annoy trees (more = better accuracy, slower build)

def create_index():
    """Generate embeddings and create Annoy index"""
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("Connecting to database...")
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    
    # Fetch all schemes
    print("Fetching schemes from database...")
    cursor.execute("""
        SELECT scheme_id, title, description, category, state_code,
               eligibility_rules, required_documents, impact_weight
        FROM schemes
        ORDER BY scheme_id
    """)
    
    schemes = cursor.fetchall()
    print(f"Found {len(schemes)} schemes")
    
    if len(schemes) == 0:
        print("ERROR: No schemes found in database!")
        print("Please ensure database is populated with sample data")
        return
    
    # Load embedding model
    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    
    # Create Annoy index
    print(f"Creating Annoy index (dim={DIM}, trees={N_TREES})")
    index = AnnoyIndex(DIM, 'angular')
    metadata = []
    
    # Generate embeddings
    print("Generating embeddings...")
    for i, row in enumerate(tqdm(schemes)):
        scheme_id, title, desc, category, state, eligibility, docs, weight = row
        
        # Create searchable text
        text = f"{title}. {desc or ''}. Category: {category or 'General'}"
        
        # Generate embedding
        embedding = model.encode(text, convert_to_numpy=True)
        
        # Add to index
        index.add_item(i, embedding)
        
        # Store metadata
        metadata.append({
            'scheme_id': str(scheme_id),
            'title': title,
            'description': desc or '',
            'category': category or 'General',
            'state_code': state or 'ALL',
            'eligibility_criteria': eligibility or {},
            'required_documents': docs or [],
            'relevance_score': float(weight) if weight else 0.5
        })
    
    # Build index
    print(f"Building Annoy index with {N_TREES} trees...")
    index.build(N_TREES)
    
    # Save index
    print(f"Saving index to {INDEX_PATH}")
    index.save(INDEX_PATH)
    
    # Save metadata
    print(f"Saving metadata to {METADATA_PATH}")
    with open(METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print("✓ Index creation complete!")
    print(f"  - Indexed {len(schemes)} schemes")
    print(f"  - Index file: {INDEX_PATH}")
    print(f"  - Metadata file: {METADATA_PATH}")
    
    # Test search
    print("\nTesting index...")
    test_query = "widow pension scheme"
    test_vec = model.encode(test_query, convert_to_numpy=True)
    indices, distances = index.get_nns_by_vector(test_vec, 3, include_distances=True)
    
    print(f"\nTop 3 results for '{test_query}':")
    for idx, dist in zip(indices, distances):
        print(f"  {metadata[idx]['title']} (distance: {dist:.3f})")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    create_index()
