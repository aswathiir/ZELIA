#!/usr/bin/env python3
"""
ZELIA Scheme Embeddings Population Script
Generates vector embeddings for all schemes in database and rebuilds Annoy index
"""

import psycopg2
import psycopg2.extras
from sentence_transformers import SentenceTransformer
import json
import requests
import sys
from datetime import datetime

import os

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://zelia:zelia_secure_2024@postgres:5432/zelia")
RETRIEVAL_SERVICE_URL = "http://localhost:8007"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

def main():
    print("="*60)
    print("ZELIA Scheme Embeddings Population Script")
    print("="*60)
    print()
    
    # Step 1: Load model
    print("Step 1: Loading sentence transformer model...")
    try:
        model = SentenceTransformer(MODEL_NAME)
        print(f"✓ Model loaded: {MODEL_NAME}")
    except Exception as e:
        print(f"✗ Error loading model: {e}")
        sys.exit(1)
    
    # Step 2: Connect to database
    print("\nStep 2: Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        print("✓ Connected to database")
    except Exception as e:
        print(f"✗ Error connecting to database: {e}")
        sys.exit(1)
    
    # Step 3: Fetch schemes
    print("\nStep 3: Fetching schemes from database...")
    try:
        cur.execute("""
            SELECT scheme_id, scheme_name, description, state_code, eligibility_summary
            FROM schemes
            ORDER BY scheme_id
        """)
        schemes = cur.fetchall()
        print(f"✓ Found {len(schemes)} schemes")
        
        if len(schemes) == 0:
            print("\n⚠ WARNING: No schemes found in database!")
            print("Run the sample data insertion script first:")
            print("  psql -U zelia -d zelia -f database/sample_schemes.sql")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Error fetching schemes: {e}")
        sys.exit(1)
    
    # Step 4: Generate embeddings
    print("\nStep 4: Generating embeddings...")
    embeddings_created = 0
    embeddings_skipped = 0
    
    for scheme in schemes:
        scheme_id = scheme['scheme_id']
        scheme_name = scheme['scheme_name']
        description = scheme['description'] or ''
        state_code = scheme['state_code']
        
        # Combine title + description for richer semantic search
        text = f"{scheme_name}. {description}"
        
        print(f"\n  Processing: {scheme_id}")
        print(f"    Scheme: {scheme_name[:50]}...")
        
        # Generate embedding
        try:
            embedding = model.encode(text).tolist()
            print(f"    ✓ Embedding generated (dim={len(embedding)})")
        except Exception as e:
            print(f"    ✗ Error generating embedding: {e}")
            continue
        
        # Check if embedding already exists
        cur.execute("""
            SELECT id FROM document_embeddings 
            WHERE document_id = %s
        """, (scheme_id,))
        
        existing = cur.fetchone()
        
        if existing:
            print(f"    ⚠ Embedding already exists (id={existing['id']}), skipping")
            embeddings_skipped += 1
            continue
        
        # Insert embedding
        try:
            cur.execute("""
                INSERT INTO document_embeddings 
                (document_id, text_chunk, embedding, metadata, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                scheme_id,
                text[:5000],  # Truncate very long text
                embedding,
                json.dumps({
                    "scheme_id": scheme_id,
                    "scheme_name": scheme_name,
                    "state_code": state_code,
                    "type": "scheme_information",
                    "generated_at": datetime.utcnow().isoformat()
                })
            ))
            
            embedding_id = cur.fetchone()['id']
            conn.commit()
            print(f"    ✓ Embedding stored (id={embedding_id})")
            embeddings_created += 1
            
        except Exception as e:
            print(f"    ✗ Error storing embedding: {e}")
            conn.rollback()
            continue
    
    # Step 5: Verify embeddings
    print("\n" + "="*60)
    print("Step 5: Verifying embeddings in database...")
    cur.execute("SELECT COUNT(*) as count FROM document_embeddings")
    total_embeddings = cur.fetchone()['count']
    print(f"✓ Total embeddings in database: {total_embeddings}")
    
    # Step 6: Rebuild Annoy index
    print("\nStep 6: Rebuilding Annoy index...")
    try:
        response = requests.post(f"{RETRIEVAL_SERVICE_URL}/rebuild-index", timeout=60)
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Annoy index rebuilt successfully")
            print(f"  Total vectors: {result.get('total_vectors', 'N/A')}")
        else:
            print(f"⚠ Warning: Index rebuild returned status {response.status_code}")
            print(f"  Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("⚠ Warning: Could not connect to retrieval service")
        print("  Make sure the service is running on port 8007")
        print("  You can rebuild the index manually by restarting the service")
    except Exception as e:
        print(f"⚠ Warning: Error rebuilding index: {e}")
    
    # Close database connection
    cur.close()
    conn.close()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Schemes processed: {len(schemes)}")
    print(f"Embeddings created: {embeddings_created}")
    print(f"Embeddings skipped: {embeddings_skipped}")
    print(f"Total embeddings: {total_embeddings}")
    print()
    
    if embeddings_created > 0:
        print("✓ SUCCESS: Embeddings populated successfully!")
        print()
        print("Next steps:")
        print("  1. Verify vector search works:")
        print("     curl -X POST http://localhost:8007/search \\")
        print("       -H 'Content-Type: application/json' \\")
        print("       -d '{\"query\": \"widow pension\", \"top_k\": 3}'")
        print()
        print("  2. Test n8n workflow with scheme_search intent")
        print("  3. Check Annoy index stats:")
        print("     curl http://localhost:8007/stats")
    else:
        print("⚠ No new embeddings created (all already exist)")
        print()
        print("To regenerate embeddings:")
        print("  1. DELETE FROM document_embeddings;")
        print("  2. Run this script again")

if __name__ == "__main__":
    main()
