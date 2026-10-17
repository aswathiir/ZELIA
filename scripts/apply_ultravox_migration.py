import asyncio
import asyncpg
import os

DATABASE_URL = "postgresql://postgres:password@localhost:5432/zelia"
# Note: Using localhost because running from host machine, but port 5432 is mapped.
# Password might be different. Let's check .env or docker-compose.
# docker-compose says POSTGRES_PASSWORD=${POSTGRES_PASSWORD}.
# I'll try 'password' as it's common default or read from .env if possible.
# Actually, I'll read from .env file path manually since python-decouple might not be installed in this script context unless I use the virtualenv.
# But I can just parse it.

def get_db_url():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env')
    user = "postgres"
    password = "password" # fallback
    db = "zelia"
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith("POSTGRES_USER="):
                    user = line.strip().split("=")[1]
                if line.startswith("POSTGRES_PASSWORD="):
                    password = line.strip().split("=")[1]
                if line.startswith("POSTGRES_DB="):
                    db = line.strip().split("=")[1]
    
    return f"postgresql://{user}:{password}@localhost:5432/{db}"

async def apply_migration():
    url = get_db_url()
    print(f"Connecting to {url}...")
    try:
        conn = await asyncpg.connect(url)
        
        migration_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../database/migrations/003_create_ultravox_tables.sql')
        with open(migration_path, 'r') as f:
            sql = f.read()
            
        print(f"Applying migration from {migration_path}...")
        await conn.execute(sql)
        print("✅ Migration applied successfully.")
        
        await conn.close()
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(apply_migration())
