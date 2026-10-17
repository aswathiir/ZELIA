-- Create citizens table
CREATE TABLE IF NOT EXISTS citizens (
    citizen_id UUID PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    aadhaar_hash VARCHAR(256) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    dob DATE,
    gender VARCHAR(10),
    address TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    
    -- Indexes for fast lookups
    CONSTRAINT phone_format CHECK (phone_number ~ '^\d{10}$'),
    CONSTRAINT aadhaar_hash_length CHECK (length(aadhaar_hash) = 64)
);

-- Create auth tokens table
CREATE TABLE IF NOT EXISTS auth_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID REFERENCES citizens(citizen_id) ON DELETE CASCADE,
    jwt_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    revoked BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    created_from_ip VARCHAR(45)
);

-- Create OTP log table (for audit)
CREATE TABLE IF NOT EXISTS otp_logs (
    otp_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(20),
    requested_at TIMESTAMP DEFAULT NOW(),
    verified BOOLEAN DEFAULT false,
    verified_at TIMESTAMP,
    attempts INT DEFAULT 0
);

-- Create login audit table
CREATE TABLE IF NOT EXISTS login_audits (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID REFERENCES citizens(citizen_id),
    login_at TIMESTAMP DEFAULT NOW(),
    logout_at TIMESTAMP,
    ip_address VARCHAR(45),
    device_info TEXT,
    status VARCHAR(50) -- 'success', 'failed', 'expired'
);

-- Indexes for performance
CREATE INDEX idx_citizen_phone ON citizens(phone_number);
CREATE INDEX idx_citizen_active ON citizens(is_active);
CREATE INDEX idx_token_citizen ON auth_tokens(citizen_id);
CREATE INDEX idx_token_expires ON auth_tokens(expires_at);
CREATE INDEX idx_otp_phone ON otp_logs(phone_number);
CREATE INDEX idx_login_citizen ON login_audits(citizen_id);
CREATE INDEX idx_login_time ON login_audits(login_at);

-- Grant permissions
ALTER TABLE citizens ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_tokens ENABLE ROW LEVEL SECURITY;
