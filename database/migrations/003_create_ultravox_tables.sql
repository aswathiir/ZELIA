CREATE TABLE IF NOT EXISTS active_calls (
    call_id TEXT PRIMARY KEY,
    citizen_id TEXT,
    phone_number TEXT,
    status TEXT DEFAULT 'initiated',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);

-- Ensure columns exist if table already existed without them
ALTER TABLE active_calls ADD COLUMN IF NOT EXISTS citizen_id TEXT;
ALTER TABLE active_calls ADD COLUMN IF NOT EXISTS phone_number TEXT;
ALTER TABLE active_calls ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'initiated';
ALTER TABLE active_calls ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_active_calls_citizen ON active_calls(citizen_id);
CREATE INDEX IF NOT EXISTS idx_active_calls_status ON active_calls(status);

CREATE TABLE IF NOT EXISTS call_transcripts (
    transcript_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id TEXT REFERENCES active_calls(call_id),
    transcript TEXT,
    language TEXT,
    confidence FLOAT,
    analysis_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT now()
);

-- Ensure columns exist
ALTER TABLE call_transcripts ADD COLUMN IF NOT EXISTS call_id TEXT REFERENCES active_calls(call_id);
ALTER TABLE call_transcripts ADD COLUMN IF NOT EXISTS transcript TEXT;
ALTER TABLE call_transcripts ADD COLUMN IF NOT EXISTS language TEXT;
ALTER TABLE call_transcripts ADD COLUMN IF NOT EXISTS confidence FLOAT;
ALTER TABLE call_transcripts ADD COLUMN IF NOT EXISTS analysis_json JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_transcripts_call ON call_transcripts(call_id);
