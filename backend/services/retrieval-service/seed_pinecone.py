"""
Seed Pinecone Index for ZELIA
Generates embeddings from PostgreSQL data and uploads to Pinecone
"""
import psycopg2
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import json
import os
import time
from tqdm import tqdm

# Configuration
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/postgres')
MODEL_NAME = 'sentence-transformers/all-MiniLM-L6-v2'
BATCH_SIZE = 100

# Pinecone Config
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "zelia-documents")

def seed_pinecone():
    """Generate embeddings and upload to Pinecone"""
    
    if not PINECONE_API_KEY:
        print("ERROR: PINECONE_API_KEY environment variable not set")
        return

    print("Connecting to database...")
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        return
    
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
        print("WARNING: No schemes found in database!")
        print("Please ensure database is populated with sample data first.")
        return
    
    # Initialize Pinecone
    print(f"Initializing Pinecone (Index: {INDEX_NAME})...")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    
    # Check if index exists
    existing_indexes = [i.name for i in pc.list_indexes()]
    if INDEX_NAME not in existing_indexes:
        print(f"Index '{INDEX_NAME}' does not exist. Creating it...")
        # Create index if not exists (assuming serverless mostly)
        try:
            pc.create_index(
                name=INDEX_NAME,
                dimension=384, # all-MiniLM-L6-v2 dimension
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region='us-east-1'
                )
            )
            print("Waiting for index to be ready...")
            time.sleep(10)
        except Exception as e:
            print(f"Error creating index: {e}")
            return
            
    index = pc.Index(INDEX_NAME)
    
    # Load embedding model
    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    
    # Prepare batches
    vectors_to_upsert = []
    
    print("Generating embeddings and preparing vectors...")
    for row in tqdm(schemes):
        scheme_id, title, desc, category, state, eligibility, docs, weight = row
        
        # Create searchable text
        text = f"{title}. {desc or ''}. Category: {category or 'General'}"
        
        # Generate embedding
        embedding = model.encode(text).tolist()
        
        # Prepare metadata
        # Pinecone metadata values must be strings, numbers, booleans, or lists of strings
        # Complex objects like dicts need to be stringified
        metadata = {
            'scheme_id': str(scheme_id),
            'title': title,
            'description': desc or '',
            'category': category or 'General',
            'state_code': state or 'ALL',
            'eligibility_criteria': json.dumps(eligibility) if eligibility else '{}',
            'required_documents': json.dumps(docs) if docs else '[]',
            'relevance_score': float(weight) if weight else 0.5
        }
        
        vectors_to_upsert.append({
            "id": str(scheme_id),
            "values": embedding,
            "metadata": metadata
        })
        
        # Upsert in batches
        if len(vectors_to_upsert) >= BATCH_SIZE:
            index.upsert(vectors=vectors_to_upsert)
            vectors_to_upsert = []
            
    # Upsert remaining
    if vectors_to_upsert:
        index.upsert(vectors=vectors_to_upsert)
        
    print("✓ Pinecone seeding complete!")
    print(f"  - Indexed {len(schemes)} schemes")
    
    # Verify count
    stats = index.describe_index_stats()
    print(f"  - Total vectors in index: {stats.total_vector_count}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    seed_pinecone()
