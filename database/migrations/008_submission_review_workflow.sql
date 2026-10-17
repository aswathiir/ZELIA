-- Add CHW review workflow columns to submissions
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS reviewer_id TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS review_notes TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS verification_checklist JSONB DEFAULT '{}'::jsonb;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS filled_pdf_uri TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS verified_documents_uri JSONB DEFAULT '[]'::jsonb;

-- Ensure submission status values can support CHW review states
-- (No enum type in current schema; this is a semantic guard via check that tolerates existing values.)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'submissions_status_check_zelia_v1'
  ) THEN
    ALTER TABLE submissions
      ADD CONSTRAINT submissions_status_check_zelia_v1
      CHECK (status IN ('draft', 'submitted', 'pending', 'pending_review', 'approved', 'rejected', 'processing_error', 'auto_processed'));
  END IF;
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_submissions_review_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_reviewer_id ON submissions(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_submissions_reviewed_at ON submissions(reviewed_at DESC);
