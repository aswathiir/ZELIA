-- Migration 010: OCR extracted data enhancements
-- Adds confidence and category columns to document_store for richer querying

ALTER TABLE document_store
  ADD COLUMN IF NOT EXISTS ocr_confidence FLOAT DEFAULT 0.0;

ALTER TABLE document_store
  ADD COLUMN IF NOT EXISTS document_category TEXT DEFAULT 'identity';

-- Category lookup for documents
COMMENT ON COLUMN document_store.document_category IS
  'One of: identity, address, income, disability, banking, family';

-- Index for faster lookups by category
CREATE INDEX IF NOT EXISTS idx_document_store_category
  ON document_store(document_category);

-- Map document types to categories
-- (used by application code, documented here for clarity)
-- aadhaar         -> identity
-- pan             -> identity
-- voter_id        -> identity
-- ration_card     -> family
-- bank_passbook   -> banking
-- disability_cert -> disability

DO $$
BEGIN
  RAISE NOTICE 'Migration 010: OCR extracted data columns added to document_store';
END $$;
