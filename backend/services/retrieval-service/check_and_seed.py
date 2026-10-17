"""
Check Database and Seed Pinecone
1. Checks if 'schemes' table has data
2. if empty, populates from data/schemes.json
3. Runs seed_pinecone logic to upload to Pinecone
"""
import psycopg2
import json
import os
import sys
from seed_pinecone import seed_pinecone

# Configuration
DB_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/postgres')
DATA_PATH = '/app/data/schemes.json'
LOCAL_DATA_PATH = '../../../../data/schemes.json' # Relative path if running locally

def get_data_path():
    if os.path.exists(DATA_PATH):
        return DATA_PATH
    if os.path.exists(LOCAL_DATA_PATH):
        return LOCAL_DATA_PATH
    return 'schemes.json'

def populate_db(conn):
    print("Populating database with sample schemes...")
    data_file = get_data_path()
    
    if not os.path.exists(data_file):
        print(f"ERROR: Data file not found at {data_file}")
        return False
        
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            schemes = json.load(f)
            
        cursor = conn.cursor()
        count = 0
        for scheme in schemes:
            try:
                cursor.execute("""
                    INSERT INTO schemes 
                    (scheme_id, title, description, category, state_code, eligibility_rules, required_documents, impact_weight)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (scheme_id) DO NOTHING
                """, (
                    scheme.get('id') or scheme.get('scheme_id'),
                    scheme.get('title'),
                    scheme.get('description'),
                    scheme.get('category'),
                    scheme.get('state', 'ALL'),
                    json.dumps(scheme.get('eligibility', {})),
                    json.dumps(scheme.get('documents', [])),
                    scheme.get('score', 0.5)
                ))
                count += 1
            except Exception as e:
                print(f"Skipping scheme {scheme.get('title')}: {e}")
                conn.rollback()
                continue
                
        conn.commit()
        cursor.close()
        print(f"Successfully inserted {count} schemes into database.")
        return True
        
    except Exception as e:
        print(f"Error reading data file: {e}")
        return False

def main():
    print("--- ZELIA Data Seeding Tool ---")
    
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        
        # Check table
        cursor.execute("SELECT COUNT(*) FROM schemes")
        count = cursor.fetchone()[0]
        print(f"Current db scheme count: {count}")
        
        if count == 0:
            print("Database is empty. Attempting to populate...")
            if not populate_db(conn):
                print("Failed to populate database. Aborting.")
                return
        else:
            print("Database already has data. Skipping population.")
            
        cursor.close()
        conn.close()
        
        # Run Pinecone Seeding
        print("\n--- Starting Pinecone Seeding ---")
        seed_pinecone()
        
    except Exception as e:
        print(f"Database error: {e}")
        print("Ensure you are running this with access to the database (e.g., via docker exec or port forwarding)")

if __name__ == "__main__":
    main()
