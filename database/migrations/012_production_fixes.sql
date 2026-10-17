-- Migration 012: Production fixes for end-to-end pipeline
-- Adds missing columns to submissions table and creates document_store table

-- Missing columns on submissions
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS correction_required_fields JSONB DEFAULT '[]'::jsonb;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT now();

-- document_store table (referenced in submission-service validation logic)
CREATE TABLE IF NOT EXISTS document_store (
  document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  household_id_hash TEXT,
  document_type TEXT,
  raw_image_uri TEXT,
  extracted_json JSONB,
  verification_status TEXT DEFAULT 'pending',
  hash_signature TEXT UNIQUE,
  ocr_confidence FLOAT DEFAULT 0.0,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_doc_store_household ON document_store(household_id_hash);
CREATE INDEX IF NOT EXISTS idx_doc_store_type ON document_store(document_type);

-- document_validation_audits table (referenced in submission-service)
CREATE TABLE IF NOT EXISTS document_validation_audits (
  audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id TEXT,
  household_id_hash TEXT,
  scheme_id TEXT,
  verified_fields JSONB DEFAULT '{}'::jsonb,
  mismatched_fields JSONB DEFAULT '[]'::jsonb,
  chw_id TEXT,
  correction_actions JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dva_submission ON document_validation_audits(submission_id);
CREATE INDEX IF NOT EXISTS idx_dva_household ON document_validation_audits(household_id_hash);
