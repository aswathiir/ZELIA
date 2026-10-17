-- ZELIA Database Initialization Script (FIXED)
-- Fixed JSON escaping for PostgreSQL compatibility

-- Create extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Schemes table
CREATE TABLE IF NOT EXISTS schemes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme_id TEXT UNIQUE,
  scheme_name TEXT NOT NULL,
  state_code TEXT,
  category TEXT,
  description TEXT,
  benefits TEXT,
  eligibility_summary TEXT,
  required_documents JSONB,
  pdf_template_key TEXT,
  impact_weight FLOAT DEFAULT 0.5,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- Manifest table
CREATE TABLE IF NOT EXISTS manifest (
  manifest_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_url TEXT,
  local_path TEXT NOT NULL,
  scheme_id TEXT,
  state_code TEXT,
  language_code TEXT,
  doc_type TEXT,
  file_type TEXT,
  download_date TIMESTAMP DEFAULT now(),
  version TEXT,
  checksum TEXT,
  notes TEXT,
  created_at TIMESTAMP DEFAULT now()
);

-- Mappings table
CREATE TABLE IF NOT EXISTS mappings (
  mapping_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manifest_id UUID REFERENCES manifest(manifest_id),
  block_id TEXT NOT NULL,
  field_id TEXT NOT NULL,
  score FLOAT NOT NULL,
  method TEXT DEFAULT 'embedding',
  evidence JSONB,
  auto_accepted BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT now()
);

-- Households table
CREATE TABLE IF NOT EXISTS households (
  household_id_hash TEXT PRIMARY KEY,
  salted_hash_meta JSONB,
  head_of_household_name_hash TEXT,
  location_district TEXT,
  location_block TEXT,
  profile_json JSONB,
  documents_meta JSONB,
  consent_ledger_json JSONB,
  last_updated_ts TIMESTAMP DEFAULT now(),
  sync_status TEXT DEFAULT 'local'
);

-- Submissions table
CREATE TABLE IF NOT EXISTS submissions (
  submission_id SERIAL PRIMARY KEY,
  household_hash TEXT,
  scheme_id TEXT,
  chw_id UUID,
  filled_pdf_uri TEXT,
  status TEXT DEFAULT 'draft',
  audit_log JSONB DEFAULT '[]'::jsonb,
  timestamps JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT now()
);

-- Audit ledger
CREATE TABLE IF NOT EXISTS audit_ledger (
  audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  actor_id TEXT,
  payload JSONB,
  signature TEXT,
  created_at TIMESTAMP DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_schemes_state ON schemes(state_code);
CREATE INDEX IF NOT EXISTS idx_manifest_scheme ON manifest(scheme_id);
CREATE INDEX IF NOT EXISTS idx_mappings_manifest ON mappings(manifest_id);
CREATE INDEX IF NOT EXISTS idx_households_district ON households(location_district);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_ledger(entity_type, entity_id);

-- Sample schemes with PROPER JSON using dollar-quoted strings
INSERT INTO schemes (scheme_id, scheme_name, state_code, category, description, eligibility_summary, required_documents, impact_weight) VALUES
('widow_pension_001', 'Widow Pension Scheme', 'TN', 'pension', 'Monthly pension for widows', 
 'Widowed status, Age 18+',
 $$["death_certificate", "age_proof", "income_certificate", "aadhar"]$$::jsonb, 
 0.8),

('ration_apl_001', 'Ration Card - APL', 'TN', 'food_security', 'Above Poverty Line ration card',
 'Monthly income <= 12000',
 $$["address_proof", "income_certificate", "family_photo", "aadhar"]$$::jsonb, 
 0.6),

('disability_pension_001', 'Disability Pension', 'TN', 'pension', 'Monthly support for persons with disabilities',
 'Disability status = true, Percentage >= 40%',
 $$["disability_certificate", "medical_report", "aadhar", "bank_passbook"]$$::jsonb, 
 0.9),

('old_age_pension_001', 'Old Age Pension', 'TN', 'pension', 'Pension for senior citizens above 60',
 'Age >= 60, Monthly income <= 5000',
 $$["age_proof", "income_certificate", "aadhar", "bank_passbook"]$$::jsonb, 
 0.7),

('girl_scholarship_001', 'Girl Child Education Scholarship', 'TN', 'education', 'Scholarship for girl students',
 'Gender = female, Student status = true',
 $$["school_certificate", "marks_card", "income_certificate", "aadhar"]$$::jsonb, 
 0.85);

-- Success message
DO $$
BEGIN
  RAISE NOTICE 'ZELIA database initialized successfully with % sample schemes', 
    (SELECT COUNT(*) FROM schemes);
END $$;

-- ==========================================
-- ADDED FOR RETRIEVAL SERVICE & EMBEDDINGS
-- ==========================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create embeddings table (Real Vector Store)
CREATE TABLE IF NOT EXISTS document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id TEXT, -- Changed to TEXT to match other IDs loosely
    text_chunk TEXT NOT NULL,
    embedding vector(384) NOT NULL, -- Dimension matches all-MiniLM-L6-v2
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Search index
CREATE INDEX IF NOT EXISTS idx_embeddings_cosine ON document_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ==========================================
-- PRODUCTION FIXES (migration 012)
-- ==========================================

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