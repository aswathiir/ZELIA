-- ZELIA Database Initialization Script (FIXED)
-- Fixed JSON escaping for PostgreSQL compatibility

-- Create extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Schemes table
CREATE TABLE IF NOT EXISTS schemes (
  scheme_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  state_code TEXT,
  category TEXT,
  description TEXT,
  eligibility_rules JSONB,
  required_documents JSONB,
  template_uri TEXT,
  impact_weight FLOAT DEFAULT 0.5,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

-- Manifest table
CREATE TABLE IF NOT EXISTS manifest (
  manifest_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_url TEXT,
  local_path TEXT NOT NULL,
  scheme_id UUID REFERENCES schemes(scheme_id),
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
  submission_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  household_hash TEXT REFERENCES households(household_id_hash),
  scheme_id UUID REFERENCES schemes(scheme_id),
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
INSERT INTO schemes (title, state_code, category, description, eligibility_rules, required_documents, impact_weight) VALUES
('Widow Pension Scheme', 'TN', 'pension', 'Monthly pension for widows aged 60+', 
 $${
   "rules": [
     {"field": "marital_status", "op": "equals", "value": "widowed"},
     {"field": "age", "op": ">=", "value": 60}
   ]
 }$$::jsonb,
 $$["death_certificate", "age_proof", "income_certificate", "aadhar"]$$::jsonb, 
 0.8),

('Ration Card - APL', 'TN', 'food_security', 'Above Poverty Line ration card',
 $${
   "rules": [
     {"field": "monthly_income", "op": "<=", "value": 12000}
   ]
 }$$::jsonb,
 $$["address_proof", "income_certificate", "family_photo", "aadhar"]$$::jsonb, 
 0.6),

('Disability Pension', 'TN', 'pension', 'Monthly support for persons with disabilities',
 $${
   "rules": [
     {"field": "disability_status", "op": "equals", "value": true},
     {"field": "disability_percentage", "op": ">=", "value": 40}
   ]
 }$$::jsonb,
 $$["disability_certificate", "medical_report", "aadhar", "bank_passbook"]$$::jsonb, 
 0.9),

('Old Age Pension', 'TN', 'pension', 'Pension for senior citizens above 60',
 $${
   "rules": [
     {"field": "age", "op": ">=", "value": 60},
     {"field": "monthly_income", "op": "<=", "value": 5000}
   ]
 }$$::jsonb,
 $$["age_proof", "income_certificate", "aadhar", "bank_passbook"]$$::jsonb, 
 0.7),

('Girl Child Education Scholarship', 'TN', 'education', 'Scholarship for girl students',
 $${
   "rules": [
     {"field": "gender", "op": "equals", "value": "female"},
     {"field": "student_status", "op": "equals", "value": true}
   ]
 }$$::jsonb,
 $$["school_certificate", "marks_card", "income_certificate", "aadhar"]$$::jsonb, 
 0.85);

-- Success message
DO $$
BEGIN
  RAISE NOTICE 'ZELIA database initialized successfully with % sample schemes', 
    (SELECT COUNT(*) FROM schemes);
END $$;