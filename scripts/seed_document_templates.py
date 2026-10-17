import os
import json
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

# Config
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "zelia")
NAMESPACE = "document_templates"

def seed():
    if not PINECONE_API_KEY:
        print("Error: PINECONE_API_KEY not set")
        return

    print(f"Connecting to Pinecone index: {INDEX_NAME}")
    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(INDEX_NAME)
    
    print("Loading embedding model...")
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

    documents = [
        {
            "id": "widow_pension_ka_form",
            "text": "Application form for Widow Pension Scheme in Karnataka. Social security pension for widows.",
            "metadata": {
                "document_name": "Widow Pension Application",
                "document_type": "application_form",
                "storage_path": "forms/widow_pension_karnataka.pdf",
                "scheme_id": "widow_pension",
                "state_code": "KA"
            }
        },
        {
            "id": "old_age_pension_ka_form",
            "text": "Application form for Old Age Pension Scheme in Karnataka. Sandhya Suraksha Yojana.",
            "metadata": {
                "document_name": "Old Age Pension Application",
                "document_type": "application_form",
                "storage_path": "forms/old_age_pension_karnataka.pdf",
                "scheme_id": "old_age_pension",
                "state_code": "KA"
            }
        }
    ]

    vectors = []
    for doc in documents:
        print(f"Embedding: {doc['id']}")
        embedding = model.encode(doc['text']).tolist()
        vectors.append({
            "id": doc['id'],
            "values": embedding,
            "metadata": doc['metadata']
        })

    print(f"Upserting {len(vectors)} vectors to namespace '{NAMESPACE}'...")
    index.upsert(vectors=vectors, namespace=NAMESPACE)
    print("Success!")

if __name__ == "__main__":
    seed()
