# -*- coding: utf-8 -*-
"""
Ingest real government schemes from dataset into Retrieval Service.
"""
import os
import requests
import glob
import time

DATASET_ROOT = r"dataset/govt/government_schemes/govt scheme"
RETRIEVAL_URL = "http://localhost:8007"
MAX_DOCS = 100

def ingest_data():
    print("=" * 60)
    print(f" INGESTING REAL DATA (Max {MAX_DOCS} docs)")
    print("=" * 60)
    
    # Verify service is up
    try:
        resp = requests.get(f"{RETRIEVAL_URL}/health")
        if resp.status_code != 200:
            print("ERROR: Retrieval Service not healthy")
            return
        print(f"Service status: {resp.json()}")
    except Exception as e:
        print(f"ERROR: Could not connect to service: {e}")
        return

    # Find text files
    pattern = os.path.join(DATASET_ROOT, "**", "*.txt")
    files = glob.glob(pattern, recursive=True)
    print(f"Found {len(files)} scheme files in dataset.")
    
    count = 0
    start_time = time.time()
    
    for file_path in files:
        if count >= MAX_DOCS:
            break
            
        try:
            # Extract metadata
            filename = os.path.basename(file_path)
            state = os.path.basename(os.path.dirname(file_path))
            
            # Read content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read().strip()
            
            if len(text) < 100:
                print(f"Skipping short file: {filename}")
                continue
                
            # Send to index
            resp = requests.post(f"{RETRIEVAL_URL}/index/text", json={
                "text": text,
                "metadata": {
                    "source": filename,
                    "state": state,
                    "type": "scheme_text"
                }
            })
            
            if resp.status_code == 200:
                print(f"[{count+1}/{MAX_DOCS}] Indexed: {state}/{filename}")
                count += 1
            else:
                print(f"Failed to index {filename}: {resp.text}")
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            
    duration = time.time() - start_time
    print("-" * 60)
    print(f"Ingestion complete. {count} documents indexed in {duration:.2f}s")

if __name__ == "__main__":
    ingest_data()
