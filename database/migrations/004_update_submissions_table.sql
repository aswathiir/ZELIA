-- Add missing columns to submissions table to support n8n workflow
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS call_id TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS document_id TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS document_type TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS applicant_data JSONB DEFAULT '{}'::jsonb;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS storage_path TEXT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS confidence FLOAT;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now();

-- Add constraints or indexes if necessary
CREATE INDEX IF NOT EXISTS idx_submissions_call_id ON submissions(call_id);
CREATE INDEX IF NOT EXISTS idx_submissions_citizen_id ON submissions(citizen_id);
