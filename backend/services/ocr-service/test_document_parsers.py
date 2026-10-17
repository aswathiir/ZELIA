"""
Unit Tests for ZELIA Document Parsers and Classifier.
Run: python -m pytest test_document_parsers.py -v
"""

import pytest
from document_parsers import (
    AadhaarParser, PANParser, VoterIDParser,
    RationCardParser, BankPassbookParser, DisabilityCertParser,
    parse_document,
)
from document_classifier import classify_document
from document_verification import verify_against_documents, auto_fill_profile


# ===================================================================
# Test Data (synthetic — matches format of real Indian ID documents)
# ===================================================================

SAMPLE_AADHAAR_TEXT = """
GOVERNMENT OF INDIA
भारत सरकार

Lakshmi Devi

DOB: 15/03/1961
Female

S/O Ramesh Kumar
House No 42, Kuvempunagar
Mysuru, Karnataka 570023

1234 5678 9012
"""

SAMPLE_PAN_TEXT = """
INCOME TAX DEPARTMENT
GOVT OF INDIA

LAKSHMI DEVI
RAMESH KUMAR

15/03/1961

ABCDE1234F

Permanent Account Number Card
"""

SAMPLE_VOTER_ID_TEXT = """
ELECTION COMMISSION OF INDIA
ELECTOR PHOTO IDENTITY CARD

Elector's Name: Lakshmi Devi
Father's Name: Ramesh Kumar

DOB: 15/03/1961
Female

Address: House No 42, Kuvempunagar, Mysuru

ABC1234567
"""

SAMPLE_RATION_CARD_TEXT = """
FOOD AND CIVIL SUPPLY DEPARTMENT
GOVERNMENT OF KARNATAKA

RATION CARD

Card No: KA-RC-123456
Category: BPL

Head of Family: Lakshmi Devi
No. of Members: 3

Address: House No 42, Kuvempunagar, Mysuru
"""

SAMPLE_BANK_TEXT = """
STATE BANK OF INDIA
SAVINGS BANK PASSBOOK

Name: Lakshmi Devi
A/c No: 12345678901234
Branch: Kuvempunagar Branch

IFSC: SBIN0001234
"""

SAMPLE_DISABILITY_TEXT = """
DISABILITY CERTIFICATE

Certificate No: UDID-KA-2024-001

Name of the person: Lakshmi Devi
DOB: 15/03/1961

Nature of disability: Locomotor
Disability percentage: 65%

Issuing Authority: District Medical Board, Mysuru
"""


# ===================================================================
# Aadhaar Parser Tests
# ===================================================================
class TestAadhaarParser:
    parser = AadhaarParser()

    def test_extracts_aadhaar_number(self):
        result = self.parser.parse(SAMPLE_AADHAAR_TEXT)
        assert result.fields["aadhaar_number"] == "1234 5678 9012"

    def test_extracts_dob(self):
        result = self.parser.parse(SAMPLE_AADHAAR_TEXT)
        assert result.fields["dob"] == "15/03/1961"

    def test_extracts_gender(self):
        result = self.parser.parse(SAMPLE_AADHAAR_TEXT)
        assert result.fields["gender"] == "Female"

    def test_extracts_pincode(self):
        result = self.parser.parse(SAMPLE_AADHAAR_TEXT)
        assert result.fields["pincode"] == "570023"

    def test_confidence_is_high(self):
        result = self.parser.parse(SAMPLE_AADHAAR_TEXT)
        assert result.confidence >= 0.5

    def test_document_type_is_aadhaar(self):
        result = self.parser.parse(SAMPLE_AADHAAR_TEXT)
        assert result.document_type == "aadhaar"

    def test_empty_input(self):
        result = self.parser.parse("")
        assert result.confidence == 0.0
        assert result.fields["aadhaar_number"] is None


# ===================================================================
# PAN Parser Tests
# ===================================================================
class TestPANParser:
    parser = PANParser()

    def test_extracts_pan_number(self):
        result = self.parser.parse(SAMPLE_PAN_TEXT)
        assert result.fields["pan_number"] == "ABCDE1234F"

    def test_extracts_dob(self):
        result = self.parser.parse(SAMPLE_PAN_TEXT)
        assert result.fields["dob"] == "15/03/1961"

    def test_document_type(self):
        result = self.parser.parse(SAMPLE_PAN_TEXT)
        assert result.document_type == "pan"

    def test_confidence(self):
        result = self.parser.parse(SAMPLE_PAN_TEXT)
        assert result.confidence >= 0.5


# ===================================================================
# Voter ID Parser Tests
# ===================================================================
class TestVoterIDParser:
    parser = VoterIDParser()

    def test_extracts_voter_id(self):
        result = self.parser.parse(SAMPLE_VOTER_ID_TEXT)
        assert result.fields["voter_id_number"] == "ABC1234567"

    def test_extracts_name(self):
        result = self.parser.parse(SAMPLE_VOTER_ID_TEXT)
        assert result.fields["name"] is not None
        assert "Lakshmi" in result.fields["name"]

    def test_extracts_father_name(self):
        result = self.parser.parse(SAMPLE_VOTER_ID_TEXT)
        assert result.fields["father_name"] is not None
        assert "Ramesh" in result.fields["father_name"]


# ===================================================================
# Ration Card Parser Tests
# ===================================================================
class TestRationCardParser:
    parser = RationCardParser()

    def test_extracts_card_number(self):
        result = self.parser.parse(SAMPLE_RATION_CARD_TEXT)
        assert result.fields["card_number"] == "KA-RC-123456"

    def test_extracts_category(self):
        result = self.parser.parse(SAMPLE_RATION_CARD_TEXT)
        assert result.fields["category"] == "BPL"

    def test_extracts_head(self):
        result = self.parser.parse(SAMPLE_RATION_CARD_TEXT)
        assert result.fields["head_of_family"] is not None


# ===================================================================
# Bank Passbook Parser Tests
# ===================================================================
class TestBankPassbookParser:
    parser = BankPassbookParser()

    def test_extracts_account_number(self):
        result = self.parser.parse(SAMPLE_BANK_TEXT)
        assert result.fields["account_number"] == "12345678901234"

    def test_extracts_ifsc(self):
        result = self.parser.parse(SAMPLE_BANK_TEXT)
        assert result.fields["ifsc"] == "SBIN0001234"

    def test_extracts_bank_name(self):
        result = self.parser.parse(SAMPLE_BANK_TEXT)
        assert result.fields["bank_name"] is not None
        bank = (result.fields["bank_name"] or "").lower()
        assert "state bank" in bank or "sbi" in bank


# ===================================================================
# Disability Certificate Parser Tests
# ===================================================================
class TestDisabilityCertParser:
    parser = DisabilityCertParser()

    def test_extracts_percentage(self):
        result = self.parser.parse(SAMPLE_DISABILITY_TEXT)
        assert result.fields["disability_percentage"] == "65"

    def test_extracts_type(self):
        result = self.parser.parse(SAMPLE_DISABILITY_TEXT)
        assert result.fields["disability_type"] == "Locomotor"

    def test_extracts_cert_number(self):
        result = self.parser.parse(SAMPLE_DISABILITY_TEXT)
        assert "UDID" in (result.fields["certificate_number"] or "")


# ===================================================================
# Document Classifier Tests
# ===================================================================
class TestDocumentClassifier:
    def test_aadhaar_classification(self):
        doc_type, conf = classify_document(SAMPLE_AADHAAR_TEXT)
        assert doc_type == "aadhaar"
        assert conf >= 0.4

    def test_pan_classification(self):
        doc_type, conf = classify_document(SAMPLE_PAN_TEXT)
        assert doc_type == "pan"
        assert conf >= 0.4

    def test_voter_id_classification(self):
        doc_type, conf = classify_document(SAMPLE_VOTER_ID_TEXT)
        assert doc_type == "voter_id"
        assert conf >= 0.4

    def test_ration_card_classification(self):
        doc_type, conf = classify_document(SAMPLE_RATION_CARD_TEXT)
        assert doc_type == "ration_card"
        assert conf >= 0.4

    def test_bank_classification(self):
        doc_type, conf = classify_document(SAMPLE_BANK_TEXT)
        assert doc_type == "bank_passbook"
        assert conf >= 0.4

    def test_disability_classification(self):
        doc_type, conf = classify_document(SAMPLE_DISABILITY_TEXT)
        assert doc_type == "disability_certificate"
        assert conf >= 0.4

    def test_unknown_text(self):
        doc_type, conf = classify_document("Hello world, nothing relevant here")
        assert doc_type == "unknown"
        assert conf == 0.0


# ===================================================================
# Registry / parse_document Tests
# ===================================================================
class TestParseDocument:
    def test_parse_aadhaar(self):
        result = parse_document("aadhaar", SAMPLE_AADHAAR_TEXT)
        assert result.document_type == "aadhaar"

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown document type"):
            parse_document("passport", "some text")


# ===================================================================
# Document Verification Tests
# ===================================================================
class TestVerification:
    def _make_docs(self):
        return [
            {
                "document_type": "aadhaar",
                "extracted_json": {
                    "fields": {
                        "name": "Lakshmi Devi",
                        "dob": "15/03/1961",
                        "gender": "Female",
                        "address": "House No 42, Kuvempunagar, Mysuru, Karnataka 570023",
                        "aadhaar_number": "1234 5678 9012",
                        "pincode": "570023",
                    }
                },
            },
            {
                "document_type": "bank_passbook",
                "extracted_json": {
                    "fields": {
                        "name": "Lakshmi Devi",
                        "account_number": "12345678901234",
                        "ifsc": "SBIN0001234",
                    }
                },
            },
        ]

    def test_matching_fields(self):
        profile = {"name": "Lakshmi Devi", "aadhaar_number": "1234 5678 9012"}
        result = verify_against_documents(profile, self._make_docs())
        assert result.matched >= 2
        assert result.overall_status == "verified"

    def test_mismatch_detected(self):
        profile = {"name": "Wrong Name", "aadhaar_number": "1234 5678 9012"}
        result = verify_against_documents(profile, self._make_docs())
        assert result.mismatched >= 1
        assert result.overall_status == "needs_review"

    def test_auto_fill_empty_fields(self):
        profile = {"name": None, "bank_account": ""}
        result = auto_fill_profile(profile, self._make_docs())
        assert "name" in result.fields_filled
        assert result.filled_profile["name"] == "Lakshmi Devi"

    def test_no_documents(self):
        profile = {"name": "Lakshmi"}
        result = verify_against_documents(profile, [])
        assert result.overall_status == "no_documents"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
