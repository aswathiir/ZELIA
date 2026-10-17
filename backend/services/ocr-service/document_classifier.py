"""
ZELIA Document Classifier
Auto-detects Indian ID document type from OCR text using keyword heuristics.
"""

import re
from typing import Tuple


# (pattern, document_type, weight)
_CLASSIFICATION_RULES = [
    # Aadhaar ---------------------------------------------------------------
    (re.compile(r"unique\s*identification|uidai|aadhaar|आधार", re.I), "aadhaar", 3),
    (re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), "aadhaar", 2),
    (re.compile(r"Government\s*of\s*India.*Enrolment", re.I), "aadhaar", 2),

    # PAN -------------------------------------------------------------------
    (re.compile(r"income\s*tax\s*department|permanent\s*account|PAN\s*Card", re.I), "pan", 3),
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "pan", 2),

    # Voter ID / EPIC -------------------------------------------------------
    (re.compile(r"election\s*commission|voter|EPIC|elector|निर्वाचन", re.I), "voter_id", 3),
    (re.compile(r"\b[A-Z]{3}\d{7}\b"), "voter_id", 2),

    # Ration Card -----------------------------------------------------------
    (re.compile(r"ration\s*card|food\s*(?:and\s*)?(?:civil\s*)?supply|राशन", re.I), "ration_card", 3),
    (re.compile(r"\b(?:APL|BPL|AAY|PHH|NPHH|Antyodaya)\b", re.I), "ration_card", 2),

    # Bank Passbook ---------------------------------------------------------
    (re.compile(r"bank\s*(?:pass\s*book|account)|savings\s*(?:bank|account)|IFSC", re.I), "bank_passbook", 3),
    (re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"), "bank_passbook", 2),  # IFSC pattern

    # Disability Certificate ------------------------------------------------
    (re.compile(r"disability\s*certificate|UDID|person\s*with\s*disability|विकलांग", re.I), "disability_certificate", 3),
    (re.compile(r"\d{1,3}\s*%\s*(?:disability|disab)", re.I), "disability_certificate", 2),
]


def classify_document(text: str) -> Tuple[str, float]:
    """
    Return (document_type, confidence) based on keyword matching.

    Confidence is 0.0-1.0 indicating how certain we are about the type.
    Returns ("unknown", 0.0) if no patterns match.
    """
    scores: dict = {}

    for pattern, doc_type, weight in _CLASSIFICATION_RULES:
        if pattern.search(text):
            scores[doc_type] = scores.get(doc_type, 0) + weight

    if not scores:
        return ("unknown", 0.0)

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Normalise: max possible per type is ~7 (3+2+2), map to 0-1
    confidence = min(best_score / 5.0, 1.0)

    return (best_type, round(confidence, 2))
