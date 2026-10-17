from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class Profile(BaseModel):
    id: Optional[int] = None
    profile_data: Dict[str, Any] = Field(default_factory=dict)
    # Expected keys in profile_data:
    # - name: str
    # - age: int
    # - gender: str (male/female/other)
    # - marital_status: str (single/married/widowed/divorced)
    # - spouse_name: str (optional)
    # - children_count: int
    # - children_schooling: bool
    # - income: int
    # - occupation: str
    # - housing_type: str (kutcha/pucca/homeless)
    # - disability: bool
    # - documents_held: List[str] (e.g., ["ration_card", "aadhar"])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class InterviewAnswer(BaseModel):
    question_id: str
    answer_raw: str
    normalized_key: Optional[str] = None
    normalized_value: Any = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Interview(BaseModel):
    id: Optional[int] = None
    household_id: int
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    channel: str = "web_ui"
    answers: List[InterviewAnswer] = Field(default_factory=list)

class Scheme(BaseModel):
    id: str
    name: str
    description: str
    benefits: str
    conditions: Dict[str, Any]  # JSON representation of eligibility rules

class RuleResult(BaseModel):
    scheme_id: str
    eligible: bool
    reasons: List[str] = Field(default_factory=list)
