-- Enable pgvector extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Create submissions table
CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id TEXT,
    scheme_id TEXT,
    applicant_data JSONB,
    eligibility JSONB,
    status TEXT DEFAULT 'pending',
    document_reference TEXT,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create embeddings table (Real Vector Store)
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID, -- Soft reference to submission or document ID
    embedding vector(384) NOT NULL, -- Dimension match embeddings model
    chunk_text TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Search index
CREATE INDEX IF NOT EXISTS idx_embeddings_cosine ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
