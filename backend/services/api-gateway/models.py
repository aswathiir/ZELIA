from sqlalchemy import Column, String, Boolean, JSON, Text, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from database import Base
import uuid
from datetime import datetime

# Schemes table - matches init.sql
class Scheme(Base):
    __tablename__ = "schemes"
    
    scheme_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    state_code = Column(Text)
    category = Column(Text)
    description = Column(Text)
    eligibility_rules = Column(JSON)  # JSONB with rules for matching
    required_documents = Column(JSON)  # JSONB array of required doc types
    application_template_uri = Column(Text)
    impact_weight = Column(Float, default=0.5)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Submissions table - matches init.sql
class Submission(Base):
    __tablename__ = "submissions"
    
    submission_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    household_hash = Column(Text)  # References households(household_id_hash)
    scheme_id = Column(UUID(as_uuid=True))  # References schemes(scheme_id)
    chw_id = Column(UUID(as_uuid=True))
    filled_pdf_uri = Column(Text)
    status = Column(Text, default='draft')  # draft, submitted, approved, rejected
    audit_log = Column(JSON, default=[])
    timestamps = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

# Households table - matches init.sql
class Household(Base):
    __tablename__ = "households"
    
    household_id_hash = Column(Text, primary_key=True)
    salted_hash_meta = Column(JSON)
    head_of_household_name_hash = Column(Text)
    location_district = Column(Text)
    location_block = Column(Text)
    profile_json = Column(JSON)  # Encrypted profile data
    documents_meta = Column(JSON)
    consent_ledger_json = Column(JSON)
    last_updated_ts = Column(DateTime, default=datetime.utcnow)
    sync_status = Column(Text, default='local')

# CHW Users table - matches init.sql
class CHWUser(Base):
    __tablename__ = "chw_users"
    
    chw_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    full_name = Column(Text)
    phone = Column(Text)
    district = Column(Text)
    role = Column(Text, default='chw')  # chw, admin, official
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# Audit Ledger table - matches init.sql
class AuditLedger(Base):
    __tablename__ = "audit_ledger"
    
    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)
    entity_id = Column(Text, nullable=False)
    actor_id = Column(Text)
    payload = Column(JSON)
    signature = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
