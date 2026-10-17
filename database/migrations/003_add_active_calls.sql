-- Migration: Add active_calls table for Ultravox Telemetry
CREATE TABLE IF NOT EXISTS active_calls (
    call_id TEXT PRIMARY KEY,
    citizen_id TEXT,
    phone_number TEXT,
    status TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    raw_transcript TEXT,
    duration_secs INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    end_time TIMESTAMP
);

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_active_calls_status ON active_calls(status);
CREATE INDEX IF NOT EXISTS idx_active_calls_citizen ON active_calls(citizen_id);
