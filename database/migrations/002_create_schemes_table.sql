-- Create schemes table
CREATE TABLE IF NOT EXISTS schemes (
    scheme_id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    ministry VARCHAR(100),
    status VARCHAR(50) DEFAULT 'draft',  -- draft, active, archived
    version VARCHAR(10) DEFAULT 'v1.0',
    eligibility_rules JSONB,  -- [{field, operator, value, description}]
    pseudocode TEXT,  -- Plain English rules
    form_fields JSONB,  -- List of form field names
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    published_at TIMESTAMP,
    
    CONSTRAINT scheme_status CHECK (status IN ('draft', 'active', 'archived'))
);

-- Create scheme versions table (for audit trail)
CREATE TABLE IF NOT EXISTS scheme_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_id UUID REFERENCES schemes(scheme_id) ON DELETE CASCADE,
    version VARCHAR(10),
    data JSONB,  -- Snapshot of scheme at this version
    created_at TIMESTAMP DEFAULT NOW(),
    approved BOOLEAN DEFAULT false,
    change_summary TEXT
);

-- Create form templates table
CREATE TABLE IF NOT EXISTS form_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheme_id UUID REFERENCES schemes(scheme_id) ON DELETE CASCADE,
    file_path VARCHAR(255),  -- e.g. /templates/farmer-subsidy-v1.pdf
    file_hash VARCHAR(64),  -- SHA256
    file_size INT,
    fields JSONB,  -- List of fillable fields
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Indexes
CREATE INDEX idx_scheme_status ON schemes(status);
CREATE INDEX idx_scheme_ministry ON schemes(ministry);
CREATE INDEX idx_scheme_published ON schemes(published_at);
CREATE INDEX idx_version_scheme ON scheme_versions(scheme_id);
CREATE INDEX idx_template_scheme ON form_templates(scheme_id);
