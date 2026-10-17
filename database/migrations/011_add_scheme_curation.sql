-- Curated active schemes per state for cleaner matching across all states

CREATE TABLE IF NOT EXISTS scheme_curation (
    scheme_id VARCHAR(255) PRIMARY KEY REFERENCES schemes(scheme_id) ON DELETE CASCADE,
    state_code VARCHAR(16) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    curation_score NUMERIC NOT NULL DEFAULT 0,
    curation_reason TEXT,
    curated_by TEXT NOT NULL DEFAULT 'auto',
    curated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheme_curation_state_active
    ON scheme_curation (state_code, is_active);

CREATE INDEX IF NOT EXISTS idx_scheme_curation_active_score
    ON scheme_curation (is_active, curation_score DESC);
