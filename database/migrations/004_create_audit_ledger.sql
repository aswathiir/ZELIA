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

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_ledger(entity_type, entity_id);
