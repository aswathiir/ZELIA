"""
ZELIA Rules Engine
Evaluates household eligibility for government schemes using rule-based logic
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
import uvicorn

app = FastAPI(
    title="ZELIA Rules Engine",
    description="Eligibility evaluation for government schemes",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DB_URL = os.getenv('DATABASE_URL', 'postgresql://zelia:zelia_secure_2024@localhost:5432/zelia')


def get_db_connection():
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)


def _safe_load_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default
    return default


def _parse_required_documents(value: Any) -> List[str]:
    parsed = _safe_load_json(value, None)
    if isinstance(parsed, list):
        return [str(v).strip() for v in parsed if str(v).strip()]
    if isinstance(parsed, str):
        return [v.strip() for v in parsed.split(",") if v.strip()]
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    return []


def fetch_schemes_for_profile(
    cursor,
    state_code: str,
    scheme_ids: Optional[List[str]],
) -> List[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'schemes'
        """
    )
    cols = {r["column_name"] for r in cursor.fetchall()}

    title_col = "scheme_name" if "scheme_name" in cols else ("title" if "title" in cols else "scheme_id")
    rules_expr = "eligibility_rules" if "eligibility_rules" in cols else "NULL::text AS eligibility_rules"
    docs_expr = "required_documents" if "required_documents" in cols else "NULL::text AS required_documents"
    weight_expr = "impact_weight" if "impact_weight" in cols else "1.0 AS impact_weight"

    select_sql = f"""
        SELECT
            scheme_id,
            {title_col} AS title,
            {rules_expr},
            {docs_expr},
            {weight_expr}
        FROM schemes
    """

    where = []
    params: List[Any] = []
    if scheme_ids:
        placeholders = ",".join(["%s"] * len(scheme_ids))
        where.append(f"scheme_id IN ({placeholders})")
        params.extend(scheme_ids)
    if "state_code" in cols:
        where.append("(COALESCE(state_code, 'ALL') = %s OR COALESCE(state_code, 'ALL') = 'ALL')")
        params.append(state_code)

    if where:
        select_sql += "\n WHERE " + " AND ".join(where)

    cursor.execute(select_sql, params)
    return cursor.fetchall()


class HouseholdProfile(BaseModel):
    age: Optional[int]
    marital_status: Optional[str]
    monthly_income: Optional[int]
    children_count: Optional[int]
    disability_status: Optional[bool]
    disability_percentage: Optional[int]
    caste_category: Optional[str]
    state_code: str
    occupation: Optional[str]
    housing_type: Optional[str]
    documents_available: List[str] = []


class SchemeEvaluation(BaseModel):
    scheme_id: str
    eligible: bool
    rule_matches: List[str]
    missing_requirements: List[str]
    missing_documents: List[str]
    confidence_score: float


class EligibilityRequest(BaseModel):
    profile: HouseholdProfile
    scheme_ids: Optional[List[str]] = None


class EligibilityResponse(BaseModel):
    household_profile: HouseholdProfile
    total_schemes_evaluated: int
    eligible_schemes: List[SchemeEvaluation]
    ineligible_schemes: List[SchemeEvaluation]


class LegacyEligibilityRequest(BaseModel):
    scheme_id: Optional[str] = None
    applicant_data: Dict[str, Any] = {}
    extracted_data: Dict[str, Any] = {}
    document_type: Optional[str] = None


def _to_int(v):
    try:
        return int(v) if v is not None and v != "" else None
    except Exception:
        return None


def build_household_profile(payload: Dict[str, Any]) -> HouseholdProfile:
    merged = payload.get("applicant_data") or payload.get("extracted_data") or {}
    state_code = (merged.get("state_code") or merged.get("state") or "KA")
    return HouseholdProfile(
        age=_to_int(merged.get("age")),
        marital_status=merged.get("marital_status"),
        monthly_income=_to_int(merged.get("monthly_income")),
        children_count=_to_int(merged.get("children_count")),
        disability_status=bool(merged.get("disability_status")) if merged.get("disability_status") is not None else None,
        disability_percentage=_to_int(merged.get("disability_percentage")),
        caste_category=merged.get("caste_category"),
        state_code=str(state_code).upper(),
        occupation=merged.get("occupation"),
        housing_type=merged.get("housing_type"),
        documents_available=merged.get("documents_available") or [],
    )


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "Rules Engine"
    }


def evaluate_rule(rule: Dict[str, Any], profile: HouseholdProfile) -> bool:
    """Evaluate a single rule against household profile"""
    
    field = rule.get('field')
    operator = rule.get('op')
    value = rule.get('value')
    
    profile_value = getattr(profile, field, None)
    
    if profile_value is None:
        return False
    
    if operator == 'equals':
        return profile_value == value
    elif operator == '>=':
        return profile_value >= value
    elif operator == '<=':
        return profile_value <= value
    elif operator == '>':
        return profile_value > value
    elif operator == '<':
        return profile_value < value
    elif operator == 'in':
        return profile_value in value
    elif operator == 'not_equals':
        return profile_value != value
    else:
        return False


def evaluate_expression(expression: Dict[str, Any], profile: HouseholdProfile) -> tuple:
    """Recursively evaluate rule expression (supports and/or/not)"""
    
    if 'and' in expression:
        results = [evaluate_expression(sub_expr, profile) for sub_expr in expression['and']]
        matches = [m for r, m in results for m in m]
        return all(r[0] for r in results), matches
    
    elif 'or' in expression:
        results = [evaluate_expression(sub_expr, profile) for sub_expr in expression['or']]
        matches = [m for r, m in results for m in m]
        return any(r[0] for r in results), matches
    
    elif 'not' in expression:
        result, matches = evaluate_expression(expression['not'], profile)
        return not result, matches
    
    else:
        # Single rule
        result = evaluate_rule(expression, profile)
        match_desc = f"{expression.get('field')} {expression.get('op')} {expression.get('value')}"
        return result, [match_desc] if result else []


def evaluate_scheme(scheme: Dict[str, Any], profile: HouseholdProfile) -> SchemeEvaluation:
    """Evaluate a single scheme against household profile"""
    
    eligibility_rules = _safe_load_json(scheme.get('eligibility_rules', {}), {})
    required_documents = _parse_required_documents(scheme.get('required_documents', []))
    
    # Evaluate rules
    if not isinstance(eligibility_rules, dict):
        eligibility_rules = {}
    
    rules = eligibility_rules.get('rules', [])
    if not isinstance(rules, list):
        rules = []
    
    if not rules:
        # No rules means universally eligible
        eligible = True
        rule_matches = ["universal_eligibility"]
        missing_requirements = []
    else:
        results = []
        all_matches = []
        
        for rule in rules:
            result, matches = evaluate_expression(rule, profile)
            results.append(result)
            all_matches.extend(matches)
        
        eligible = all(results)
        rule_matches = all_matches if eligible else []
        missing_requirements = [f"Failed rule check"] if not eligible else []
    
    missing_documents = [
        doc for doc in required_documents 
        if doc not in profile.documents_available
    ]
    
    # Calculate confidence score
    confidence = 1.0
    if missing_documents:
        confidence *= 0.8  # Reduce confidence if documents missing
    if not eligible:
        confidence = 0.0
    
    return SchemeEvaluation(
        scheme_id=scheme['scheme_id'],
        eligible=eligible,
        rule_matches=rule_matches,
        missing_requirements=missing_requirements,
        missing_documents=missing_documents,
        confidence_score=round(confidence, 2)
    )


@app.post("/evaluate", response_model=EligibilityResponse)
async def evaluate_eligibility(request: EligibilityRequest):
    """Evaluate household eligibility for schemes"""
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        schemes = fetch_schemes_for_profile(
            cursor=cursor,
            state_code=request.profile.state_code,
            scheme_ids=request.scheme_ids,
        )
        
        eligible_schemes = []
        ineligible_schemes = []
        
        for scheme in schemes:
            evaluation = evaluate_scheme(scheme, request.profile)
            
            if evaluation.eligible:
                eligible_schemes.append(evaluation)
            else:
                ineligible_schemes.append(evaluation)
        
        cursor.close()
        conn.close()
        
        return EligibilityResponse(
            household_profile=request.profile,
            total_schemes_evaluated=len(schemes),
            eligible_schemes=eligible_schemes,
            ineligible_schemes=ineligible_schemes
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.post("/batch-evaluate")
async def batch_evaluate(profiles: List[HouseholdProfile]):
    """Evaluate multiple households at once"""
    
    results = []
    
    for profile in profiles:
        request = EligibilityRequest(profile=profile)
        response = await evaluate_eligibility(request)
        results.append({
            "profile_id": f"{profile.state_code}_{hash(str(profile.dict()))}",
            "eligible_count": len(response.eligible_schemes),
            "top_schemes": [s.scheme_id for s in response.eligible_schemes[:3]]
        })
    
    return {"batch_results": results}


@app.post("/check-eligibility")
async def check_eligibility_compat(request: LegacyEligibilityRequest):
    """
    Backward-compatible endpoint for existing n8n and document-processor payloads.
    Maps to /evaluate and returns a compact response.
    """
    try:
        profile = build_household_profile(request.dict())
        scheme_ids = [request.scheme_id] if request.scheme_id else None
        eval_req = EligibilityRequest(profile=profile, scheme_ids=scheme_ids)
        response = await evaluate_eligibility(eval_req)

        top = response.eligible_schemes[0] if response.eligible_schemes else None
        return {
            "eligible": bool(response.eligible_schemes),
            "confidence": (top.confidence_score if top else 0.0),
            "eligible_count": len(response.eligible_schemes),
            "ineligible_count": len(response.ineligible_schemes),
            "matched_schemes": [s.scheme_id for s in response.eligible_schemes],
            "missing_fields": [],
            "result": "eligible" if response.eligible_schemes else "not_eligible",
            "message": "Compatibility response from /check-eligibility",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compatibility eligibility check failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
