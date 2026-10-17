from typing import Any, Optional
import re

def normalize_answer(question_type: str, raw_input: str) -> Any:
    """
    Normalizes raw user input based on the expected question type.
    """
    raw_input = raw_input.strip().lower()
    
    if question_type == "int":
        # extract first number found
        match = re.search(r'\d+', raw_input)
        if match:
            return int(match.group())
        # TODO: Handle text-to-number (e.g., "fifty")
        return None
    
    elif question_type == "bool":
        if raw_input in ["yes", "y", "true", "1", "amaam", "aama"]: # Tamil supports
            return True
        if raw_input in ["no", "n", "false", "0", "illai"]:
            return False
        return None

    elif question_type == "select":
        return raw_input

    elif question_type == "multi_select":
        # Split by comma or 'and'
        parts = re.split(r',|\sand\s', raw_input)
        return [p.strip() for p in parts if p.strip()]

    return raw_input
