-- ZELIA v28 upgrade (idempotent)
-- Canonical upgrade script used by run_migrations.py --include-upgrade

ALTER TABLE IF EXISTS schemes
ADD COLUMN IF NOT EXISTS pdf_template_key VARCHAR(255);

ALTER TABLE IF EXISTS submissions
ADD COLUMN IF NOT EXISTS reviewer_id TEXT,
ADD COLUMN IF NOT EXISTS review_notes TEXT,
ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS verification_checklist JSONB,
ADD COLUMN IF NOT EXISTS filled_pdf_uri TEXT,
ADD COLUMN IF NOT EXISTS verified_documents_uri JSONB,
ADD COLUMN IF NOT EXISTS correction_required_fields JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS correction_prompt JSONB,
ADD COLUMN IF NOT EXISTS document_validation_status TEXT,
ADD COLUMN IF NOT EXISTS document_validation_summary JSONB,
ADD COLUMN IF NOT EXISTS all_required_documents_verified BOOLEAN,
ADD COLUMN IF NOT EXISTS all_form_fields_matched BOOLEAN;

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

CREATE INDEX IF NOT EXISTS idx_submissions_household_hash
  ON submissions (household_hash);

CREATE INDEX IF NOT EXISTS idx_submissions_status
  ON submissions (status);

CREATE INDEX IF NOT EXISTS idx_document_store_household
  ON document_store (household_id_hash);

