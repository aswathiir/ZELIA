from typing import Dict, Any, List
from schema import Profile, Scheme, RuleResult
import json

class RuleEngine:
    def evaluate(self, profile: Profile, schemes: List[Scheme]) -> List[RuleResult]:
        results = []
        for scheme in schemes:
            is_eligible, reasons = self._check_eligibility(profile.profile_data, scheme.conditions)
            results.append(RuleResult(
                scheme_id=scheme.id,
                eligible=is_eligible,
                reasons=reasons
            ))
        return results

    def _check_eligibility(self, data: Dict[str, Any], conditions: Dict[str, Any]) -> (bool, List[str]):
        """
        Recursively checks conditions.
        Supported operators: eq, gt, lt, gte, lte, and, or
        """
        matches = True
        reasons = []

        # If conditions is a list, assume implicit AND (or handle as 'all')
        # Structure: {"operator": "and", "rules": [...]} or simple key-value for equality
        
        operator = conditions.get("operator", "and")
        rules = conditions.get("rules", [])

        if operator == "and":
            for rule in rules:
                passed, sub_reasons = self._evaluate_single_rule(data, rule)
                if not passed:
                    matches = False
                    reasons.extend(sub_reasons)
                    # For AND, one failure is enough to stop (optimization), but we might want all reasons
        elif operator == "or":
            any_passed = False
            temp_reasons = []
            for rule in rules:
                passed, sub_reasons = self._evaluate_single_rule(data, rule)
                if passed:
                    any_passed = True
                else:
                    temp_reasons.extend(sub_reasons)
            if not any_passed:
                matches = False
                reasons.extend(temp_reasons)
        
        return matches, reasons

    def _evaluate_single_rule(self, data: Dict[str, Any], rule: Dict[str, Any]) -> (bool, List[str]):
        # Base case: leaf rule
        # { "field": "age", "op": "gt", "value": 60 }
        
        if "operator" in rule:
            # Nested rule
            return self._check_eligibility(data, rule)

        field = rule.get("field")
        op = rule.get("op")
        target = rule.get("value")
        
        actual = data.get(field)
        
        if actual is None:
            return False, [f"Missing field: {field}"]

        if op == "eq":
            if actual == target: return True, []
        elif op == "gt":
            if actual > target: return True, []
        elif op == "gte":
            if actual >= target: return True, []
        elif op == "lt":
            if actual < target: return True, []
        elif op == "lte":
            if actual <= target: return True, []
        
        return False, [f"{field} ({actual}) is not {op} {target}"]
