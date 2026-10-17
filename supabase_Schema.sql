-- ZELIA canonical schema reference (Supabase/PostgreSQL)
-- This file documents core tables used by voice -> eligibility -> PDF -> CHW verification.

CREATE TABLE IF NOT EXISTS schemes (
  scheme_id TEXT PRIMARY KEY,
  scheme_name TEXT,
  state_code TEXT,
  description TEXT,
  benefits TEXT,
  required_documents JSONB DEFAULT '[]'::jsonb,
  pdf_template_key VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS submissions (
  submission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id TEXT UNIQUE,
  household_hash TEXT,
  scheme_id TEXT,
  status TEXT DEFAULT 'pending_review',
  applicant_data JSONB DEFAULT '{}'::jsonb,
  form_data JSONB DEFAULT '{}'::jsonb,
  metadata JSONB DEFAULT '{}'::jsonb,
  file_uri TEXT,
  storage_path TEXT,
  filled_pdf_uri TEXT,
  review_notes TEXT,
  reviewer_id TEXT,
  reviewed_at TIMESTAMP,
  correction_required_fields JSONB DEFAULT '[]'::jsonb,
  correction_prompt JSONB,
  document_validation_status TEXT,
  document_validation_summary JSONB,
  verification_checklist JSONB,
  all_required_documents_verified BOOLEAN,
  all_form_fields_matched BOOLEAN,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS active_calls (
  call_id TEXT PRIMARY KEY,
  citizen_id TEXT,
  phone_number TEXT,
  status TEXT,
  duration_secs INTEGER DEFAULT 0,
  raw_transcript TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP,
  end_time TIMESTAMP
);

CREATE TABLE IF NOT EXISTS households (
  household_id_hash TEXT PRIMARY KEY,
  profile_json JSONB DEFAULT '{}'::jsonb,
  paralinguistic_json JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profile_assessments (
  call_id TEXT PRIMARY KEY,
  phone_number TEXT,
  user_profile JSONB DEFAULT '{}'::jsonb,
  eligible_schemes JSONB DEFAULT '[]'::jsonb,
  response_text TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_store (
  document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  household_id_hash TEXT NOT NULL,
  document_type TEXT NOT NULL,
  raw_image_uri TEXT NOT NULL,
  extracted_json JSONB DEFAULT '{}'::jsonb,
  verification_status TEXT DEFAULT 'extracted',
  hash_signature TEXT UNIQUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

