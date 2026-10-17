-- Document-grounded CHW revalidation support
-- Authoritative documents + deterministic consistency audit

ALTER TABLE submissions ADD COLUMN IF NOT EXISTS all_required_documents_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS all_form_fields_matched BOOLEAN DEFAULT FALSE;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS document_validation_status TEXT DEFAULT 'pending';
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS document_validation_summary JSONB DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS document_store (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id_hash VARCHAR(64) NOT NULL,
    document_type TEXT NOT NULL,
    raw_image_uri TEXT NOT NULL,
    extracted_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    verification_status TEXT NOT NULL DEFAULT 'pending',
    hash_signature VARCHAR(128) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_validation_audits (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id TEXT NOT NULL,
    household_id_hash VARCHAR(64) NOT NULL,
    scheme_id TEXT,
    verified_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    mismatched_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    chw_id TEXT,
    correction_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_store_household ON document_store(household_id_hash);
CREATE INDEX IF NOT EXISTS idx_document_store_type ON document_store(document_type);
CREATE INDEX IF NOT EXISTS idx_document_validation_audits_submission ON document_validation_audits(submission_id);
CREATE INDEX IF NOT EXISTS idx_document_validation_audits_household ON document_validation_audits(household_id_hash);
CREATE INDEX IF NOT EXISTS idx_submissions_validation_status ON submissions(document_validation_status);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'submissions_document_validation_status_check_zelia_v1'
  ) THEN
    ALTER TABLE submissions
      ADD CONSTRAINT submissions_document_validation_status_check_zelia_v1
      CHECK (document_validation_status IN ('pending', 'matched', 'mismatch', 'blocked'));
  END IF;
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;
