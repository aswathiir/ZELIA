"""
ZELIA Document Parsers
Structured field extraction from Indian government ID documents.
Each parser takes raw OCR text and extracts typed fields using
regex patterns specific to each document type.
"""

import re
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ExtractionResult:
    """Standardised output from every document parser."""
    document_type: str
    fields: Dict[str, Optional[str]]
    confidence: float
    raw_text: str
    parser_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", text).strip()


def _find(pattern: str, text: str, group: int = 1,
           flags: int = re.IGNORECASE) -> Optional[str]:
    """Return first match group or None."""
    m = re.search(pattern, text, flags)
    return m.group(group).strip() if m else None


def _field_confidence(fields: Dict[str, Optional[str]],
                      required: List[str]) -> float:
    """Fraction of *required* fields that were populated."""
    if not required:
        return 0.0
    filled = sum(1 for k in required if fields.get(k))
    return round(filled / len(required), 2)


# =========================================================================
# 1. Aadhaar Card Parser
# =========================================================================
class AadhaarParser:
    """
    Extracts: name, dob, gender, address, aadhaar_number
    Aadhaar format: 12 digits, often printed as XXXX XXXX XXXX
    """
    DOC_TYPE = "aadhaar"
    REQUIRED = ["name", "aadhaar_number"]

    # Patterns ---------------------------------------------------------------
    _AADHAAR_RE = re.compile(r"\b(\d{4}\s?\d{4}\s?\d{4})\b")
    _DOB_RE = re.compile(
        r"(?:DOB|Date\s*of\s*Birth|Birth|जन्म\s*तिथि)[:\s]*"
        r"(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})",
        re.IGNORECASE,
    )
    _GENDER_RE = re.compile(
        r"\b(Male|Female|MALE|FEMALE|पुरुष|महिला|Transgender)\b",
        re.IGNORECASE,
    )
    _NAME_RE = re.compile(
        r"(?:Name|नाम)[:\s]*([A-Za-z\s\.]+?)(?:\n|$)", re.IGNORECASE
    )
    _ADDRESS_RE = re.compile(
        r"(?:Address|पता|S/O|D/O|W/O|C/O)[:\s]*([\s\S]{10,120}?)(?:\d{4}\s?\d{4}|\n\n)",
        re.IGNORECASE,
    )
    _PINCODE_RE = re.compile(r"\b(\d{6})\b")
    _VID_RE = re.compile(r"\b(\d{4}\s?\d{4}\s?\d{4}\s?\d{4})\b")

    def parse(self, text: str) -> ExtractionResult:
        warnings: List[str] = []
        text_clean = _clean(text)

        # Aadhaar number
        aadhaar_match = self._AADHAAR_RE.search(text)
        aadhaar_number = None
        if aadhaar_match:
            raw = aadhaar_match.group(1).replace(" ", "")
            if len(raw) == 12:
                aadhaar_number = f"{raw[:4]} {raw[4:8]} {raw[8:12]}"

        # Name
        name = _find(self._NAME_RE.pattern, text)
        if not name:
            # Fallback: line after "Government of India" that looks like a name
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            for i, line in enumerate(lines):
                if re.search(r"government\s*of\s*india|भारत\s*सरकार", line, re.I):
                    # Next non-empty, non-date, non-number line is likely the name
                    for j in range(i + 1, min(i + 4, len(lines))):
                        candidate = lines[j]
                        if (len(candidate) > 3
                                and not re.match(r"^\d", candidate)
                                and "aadhaar" not in candidate.lower()):
                            name = candidate
                            break
                    break

        # DOB
        dob = _find(self._DOB_RE.pattern, text)

        # Gender
        gender_m = self._GENDER_RE.search(text)
        gender = gender_m.group(1).capitalize() if gender_m else None

        # Address
        address = _find(self._ADDRESS_RE.pattern, text)
        if address:
            address = _clean(address)

        # Pincode
        pincode = None
        if address:
            pm = self._PINCODE_RE.search(address)
            if pm:
                pincode = pm.group(1)

        fields = {
            "name": name,
            "dob": dob,
            "gender": gender,
            "address": address,
            "aadhaar_number": aadhaar_number,
            "pincode": pincode,
        }

        if not aadhaar_number:
            warnings.append("Could not extract 12-digit Aadhaar number")
        if not name:
            warnings.append("Name extraction uncertain")

        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# 2. PAN Card Parser
# =========================================================================
class PANParser:
    """
    Extracts: name, dob, pan_number, father_name
    PAN format: ABCDE1234F  (5 alpha + 4 digit + 1 alpha)
    """
    DOC_TYPE = "pan"
    REQUIRED = ["name", "pan_number"]

    _PAN_RE = re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b")
    _DOB_RE = re.compile(
        r"(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})", re.IGNORECASE
    )

    def parse(self, text: str) -> ExtractionResult:
        warnings: List[str] = []
        text_clean = _clean(text)

        # PAN number
        pan_match = self._PAN_RE.search(text.upper())
        pan_number = pan_match.group(1) if pan_match else None

        # DOB
        dob = _find(self._DOB_RE.pattern, text)

        # Name and Father's name - PAN cards have a specific layout:
        # Line 1: INCOME TAX DEPARTMENT / भारत सरकार
        # Line 2: Name
        # Line 3: Father's Name
        # Line 4: DOB
        # Line 5: PAN Number
        name = None
        father_name = None
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        name_candidates = []
        for line in lines:
            # Skip header lines and number lines
            if re.search(r"income\s*tax|permanent|govt|india|भारत", line, re.I):
                continue
            if self._PAN_RE.search(line.upper()):
                continue
            if re.match(r"^\d{2}[/\-]", line):
                continue
            if len(line) > 3 and re.match(r"^[A-Za-z\s\.]+$", line):
                name_candidates.append(line)

        if len(name_candidates) >= 2:
            name = name_candidates[0]
            father_name = name_candidates[1]
        elif len(name_candidates) == 1:
            name = name_candidates[0]

        fields = {
            "name": name,
            "father_name": father_name,
            "dob": dob,
            "pan_number": pan_number,
        }

        if not pan_number:
            warnings.append("Could not extract PAN number (XXXXX0000X format)")

        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# 3. Voter ID (EPIC) Parser
# =========================================================================
class VoterIDParser:
    """
    Extracts: name, father_name, dob, address, voter_id_number, gender
    EPIC format: 3 alpha + 7 digits  (e.g. ABC1234567)
    """
    DOC_TYPE = "voter_id"
    REQUIRED = ["name", "voter_id_number"]

    _EPIC_RE = re.compile(r"\b([A-Z]{3}\d{7})\b")
    _DOB_RE = re.compile(r"(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})")
    _GENDER_RE = re.compile(r"\b(Male|Female|MALE|FEMALE)\b", re.I)
    _NAME_RE = re.compile(
        r"(?:Elector(?:'s)?\s*Name|Name)[:\s]*([A-Za-z\s\.]+?)(?:\n|$)",
        re.IGNORECASE,
    )
    _FATHER_RE = re.compile(
        r"(?:Father(?:'s)?\s*Name|Husband(?:'s)?\s*Name)[:\s]*"
        r"([A-Za-z\s\.]+?)(?:\n|$)",
        re.IGNORECASE,
    )
    _ADDRESS_RE = re.compile(
        r"(?:Address)[:\s]*([\s\S]{10,150}?)(?:\n\n|$)", re.IGNORECASE
    )

    def parse(self, text: str) -> ExtractionResult:
        warnings: List[str] = []

        voter_id = None
        epic_m = self._EPIC_RE.search(text.upper())
        if epic_m:
            voter_id = epic_m.group(1)

        name = _find(self._NAME_RE.pattern, text)
        father_name = _find(self._FATHER_RE.pattern, text)
        dob = _find(self._DOB_RE.pattern, text)
        gender_m = self._GENDER_RE.search(text)
        gender = gender_m.group(1).capitalize() if gender_m else None
        address = _find(self._ADDRESS_RE.pattern, text)
        if address:
            address = _clean(address)

        fields = {
            "name": name,
            "father_name": father_name,
            "dob": dob,
            "gender": gender,
            "address": address,
            "voter_id_number": voter_id,
        }

        if not voter_id:
            warnings.append("Could not extract EPIC number (XXX0000000 format)")

        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# 4. Ration Card Parser
# =========================================================================
class RationCardParser:
    """
    Extracts: head_of_family, card_number, category, members_count, address
    """
    DOC_TYPE = "ration_card"
    REQUIRED = ["head_of_family", "card_number"]

    _CARD_NUM_RE = re.compile(r"(?:Card\s*No|RC\s*No)[.:\s]*(\S+)", re.I)
    _CATEGORY_RE = re.compile(
        r"\b(APL|BPL|AAY|PHH|NPHH|Antyodaya|Priority)\b", re.I
    )
    _HEAD_RE = re.compile(
        r"(?:Head\s*of\s*(?:the\s*)?Family|HOF|Name\s*of\s*Head)[:\s]*"
        r"([A-Za-z\s\.]+?)(?:\n|$)",
        re.IGNORECASE,
    )
    _MEMBERS_RE = re.compile(
        r"(?:No\.?\s*of\s*Members|Total\s*Members|Members)[:\s]*(\d+)", re.I
    )
    _ADDRESS_RE = re.compile(
        r"(?:Address)[:\s]*([\s\S]{10,120}?)(?:\n\n|$)", re.I
    )

    def parse(self, text: str) -> ExtractionResult:
        warnings: List[str] = []

        card_number = _find(self._CARD_NUM_RE.pattern, text)
        category_m = self._CATEGORY_RE.search(text)
        category = category_m.group(1).upper() if category_m else None
        head_of_family = _find(self._HEAD_RE.pattern, text)
        members_count = _find(self._MEMBERS_RE.pattern, text)
        address = _find(self._ADDRESS_RE.pattern, text)
        if address:
            address = _clean(address)

        fields = {
            "head_of_family": head_of_family,
            "card_number": card_number,
            "category": category,
            "members_count": members_count,
            "address": address,
        }

        if not card_number:
            warnings.append("Could not extract ration card number")

        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# 5. Bank Passbook Parser
# =========================================================================
class BankPassbookParser:
    """
    Extracts: name, account_number, ifsc, branch, bank_name
    """
    DOC_TYPE = "bank_passbook"
    REQUIRED = ["name", "account_number", "ifsc"]

    _ACCOUNT_RE = re.compile(r"(?:A/?c\s*No|Account\s*(?:No|Number))[.:\s]*(\d{9,18})", re.I)
    _IFSC_RE = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")
    _BRANCH_RE = re.compile(
        r"(?:Branch)[:\s]*([A-Za-z\s,\.]+?)(?:\n|$)", re.I
    )
    _NAME_RE = re.compile(
        r"(?:Name|Account\s*Holder)[:\s]*([A-Za-z\s\.]+?)(?:\n|$)", re.I
    )
    _BANK_RE = re.compile(
        r"(State\s*Bank|SBI|HDFC|ICICI|Punjab\s*National|PNB|"
        r"Bank\s*of\s*Baroda|BOB|Canara\s*Bank|Union\s*Bank|"
        r"Indian\s*(?:Overseas\s*)?Bank|IOB|Central\s*Bank|"
        r"Axis\s*Bank|Kotak\s*Mahindra|IDBI|UCO\s*Bank|"
        r"Karnataka\s*Bank|South\s*Indian\s*Bank|Federal\s*Bank|"
        r"Indian\s*Bank|Syndicate\s*Bank|Allahabad\s*Bank)",
        re.I,
    )

    def parse(self, text: str) -> ExtractionResult:
        warnings: List[str] = []

        account_number = _find(self._ACCOUNT_RE.pattern, text)
        ifsc = None
        ifsc_m = self._IFSC_RE.search(text.upper())
        if ifsc_m:
            ifsc = ifsc_m.group(1)

        branch = _find(self._BRANCH_RE.pattern, text)
        name = _find(self._NAME_RE.pattern, text)

        bank_m = self._BANK_RE.search(text)
        bank_name = bank_m.group(1).strip() if bank_m else None

        # Fallback account number: longest digit sequence > 9 digits
        if not account_number:
            digits = re.findall(r"\b(\d{9,18})\b", text)
            if digits:
                account_number = max(digits, key=len)
                warnings.append("Account number extracted by heuristic (longest digit sequence)")

        fields = {
            "name": name,
            "account_number": account_number,
            "ifsc": ifsc,
            "branch": branch,
            "bank_name": bank_name,
        }

        if not ifsc:
            warnings.append("Could not extract IFSC code (XXXX0XXXXXX format)")

        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# 6. Disability Certificate Parser
# =========================================================================
class DisabilityCertParser:
    """
    Extracts: name, disability_type, disability_percentage,
              issuing_authority, certificate_number, dob
    """
    DOC_TYPE = "disability_certificate"
    REQUIRED = ["name", "disability_percentage"]

    _PERCENTAGE_RE = re.compile(r"(\d{1,3})\s*%")
    _DISABILITY_TYPES = re.compile(
        r"\b(locomotor|visual|hearing|speech|mental|"
        r"intellectual|cerebral\s*palsy|autism|"
        r"multiple\s*disabilities|leprosy\s*cured|"
        r"dwarfism|muscular\s*dystrophy|"
        r"blindness|low\s*vision|deaf|"
        r"specific\s*learning|acid\s*attack)\b",
        re.I,
    )
    _NAME_RE = re.compile(
        r"(?:Name\s*of\s*(?:the\s*)?(?:person|candidate|applicant|patient))"
        r"[:\s]*([A-Za-z\s\.]+?)(?:\n|$)",
        re.I,
    )
    _CERT_NO_RE = re.compile(
        r"(?:Certificate\s*No|Cert\s*No|UDID\s*No)[.:\s]*(\S+)", re.I
    )
    _DOB_RE = re.compile(r"(\d{2}[/\-\.]\d{2}[/\-\.]\d{4})")

    def parse(self, text: str) -> ExtractionResult:
        warnings: List[str] = []

        name = _find(self._NAME_RE.pattern, text)
        dob = _find(self._DOB_RE.pattern, text)
        cert_no = _find(self._CERT_NO_RE.pattern, text)

        # Disability percentage (take the last match, usually the final %)
        pct_matches = self._PERCENTAGE_RE.findall(text)
        disability_percentage = None
        if pct_matches:
            # Pick the value between 1-100
            for p in reversed(pct_matches):
                val = int(p)
                if 1 <= val <= 100:
                    disability_percentage = str(val)
                    break

        # Disability type
        dtype_m = self._DISABILITY_TYPES.search(text)
        disability_type = dtype_m.group(1).strip().title() if dtype_m else None

        # Issuing authority
        issuing = _find(
            r"(?:Issuing\s*Authority|Issued\s*by|Authority)[:\s]*"
            r"([A-Za-z\s,\.]+?)(?:\n|$)",
            text,
        )

        fields = {
            "name": name,
            "dob": dob,
            "disability_type": disability_type,
            "disability_percentage": disability_percentage,
            "certificate_number": cert_no,
            "issuing_authority": issuing,
        }

        if not disability_percentage:
            warnings.append("Could not extract disability percentage")

        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# 7. Income Certificate Parser
# =========================================================================
class IncomeCertificateParser:
    """
    Extracts: name, annual_income, certificate_number, validity_period
    """
    DOC_TYPE = "income_certificate"
    REQUIRED = ["name", "annual_income"]

    _INCOME_RE = re.compile(r"(?:Annual\s*Income|Total\s*Income|Income)[:\s]*Rs\.?\s*(\d+(?:,\d+)*)", re.I)
    _NAME_RE = re.compile(r"(?:Name\s*of\s*Applicant|Name)[:\s]*([A-Za-z\s\.]+?)(?:\n|$)", re.I)
    _CERT_RE = re.compile(r"(?:Certificate\s*No|RD\s*Number)[:\s]*(\S+)", re.I)

    def parse(self, text: str) -> ExtractionResult:
        warnings = []
        income_match = self._INCOME_RE.search(text)
        annual_income = income_match.group(1).replace(",", "") if income_match else None
        name = _find(self._NAME_RE.pattern, text)
        cert_no = _find(self._CERT_RE.pattern, text)

        fields = {
            "name": name,
            "annual_income": annual_income,
            "certificate_number": cert_no,
        }
        if not annual_income:
            warnings.append("Could not extract income amount")
        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# 8. Caste Certificate Parser
# =========================================================================
class CasteCertificateParser:
    """
    Extracts: name, caste, category, certificate_number
    """
    DOC_TYPE = "caste_certificate"
    REQUIRED = ["name", "caste"]

    _CASTE_RE = re.compile(r"(?:Caste|Community)[:\s]*([A-Za-z\s\-]+?)(?:\n|$)", re.I)
    _CATEGORY_RE = re.compile(r"(?:Category|Class)[:\s]*([A-Z\d]+)", re.I)
    _NAME_RE = re.compile(r"(?:Name)[:\s]*([A-Za-z\s\.]+?)(?:\n|$)", re.I)

    def parse(self, text: str) -> ExtractionResult:
        warnings = []
        caste = _find(self._CASTE_RE.pattern, text)
        category = _find(self._CATEGORY_RE.pattern, text)
        name = _find(self._NAME_RE.pattern, text)

        fields = {
            "name": name,
            "caste": caste,
            "category": category,
        }
        if not caste:
            warnings.append("Could not extract caste/community name")
        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# 9. Residence Proof / Domicile Parser
# =========================================================================
class ResidenceProofParser:
    """
    Extracts: name, address, certificate_number, period_of_residence
    """
    DOC_TYPE = "residence_proof"
    REQUIRED = ["name", "address"]

    _NAME_RE = re.compile(r"(?:Name)[:\s]*([A-Za-z\s\.]+?)(?:\n|$)", re.I)
    _ADDRESS_RE = re.compile(r"(?:Address)[:\s]*([\s\S]{10,150}?)(?:\n\n|$)", re.I)

    def parse(self, text: str) -> ExtractionResult:
        warnings = []
        name = _find(self._NAME_RE.pattern, text)
        address = _find(self._ADDRESS_RE.pattern, text)
        if address:
            address = _clean(address)

        fields = {
            "name": name,
            "address": address,
        }
        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# 10. Land Records Parser
# =========================================================================
class LandRecordsParser:
    """
    Extracts: owner_name, survey_number, area, document_id
    """
    DOC_TYPE = "land_records"
    REQUIRED = ["owner_name", "survey_number"]

    _OWNER_RE = re.compile(r"(?:Owner|Pattadar|Name)[:\s]*([A-Za-z\s\.]+?)(?:\n|$)", re.I)
    _SURVEY_RE = re.compile(r"(?:Survey\s*No|Khata\s*No)[:\s]*([\d\-\/]+)", re.I)
    _AREA_RE = re.compile(r"(?:Area|Extent)[:\s]*([\d\.]+\s*(?:Acres|Hectares|sq\s*ft))", re.I)

    def parse(self, text: str) -> ExtractionResult:
        warnings = []
        name = _find(self._OWNER_RE.pattern, text)
        survey = _find(self._SURVEY_RE.pattern, text)
        area = _find(self._AREA_RE.pattern, text)

        fields = {
            "owner_name": name,
            "survey_number": survey,
            "area": area,
        }
        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# 11. Birth Certificate Parser
# =========================================================================
class BirthCertificateParser:
    """
    Extracts: name, gender, dob, father_name, mother_name, certificate_number
    """
    DOC_TYPE = "birth_certificate"
    REQUIRED = ["name", "dob"]

    _NAME_RE = re.compile(r"(?:Name)[:\s]*([A-Za-z\s\.]+?)(?:\n|$)", re.I)
    _DOB_RE = re.compile(r"(?:Date\s*of\s*Birth|DOB)[:\s]*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})", re.I)
    _GENDER_RE = re.compile(r"(?:Sex|Gender)[:\s]*(Male|Female|M|F)", re.I)
    _FATHER_RE = re.compile(r"(?:Father|Name\s*of\s*Father)[:\s]*([A-Za-z\s\.]+?)(?:\n|$)", re.I)
    _MOTHER_RE = re.compile(r"(?:Mother|Name\s*of\s*Mother)[:\s]*([A-Za-z\s\.]+?)(?:\n|$)", re.I)

    def parse(self, text: str) -> ExtractionResult:
        warnings = []
        name = _find(self._NAME_RE.pattern, text)
        dob = _find(self._DOB_RE.pattern, text)
        gender = _find(self._GENDER_RE.pattern, text)
        father = _find(self._FATHER_RE.pattern, text)
        mother = _find(self._MOTHER_RE.pattern, text)

        fields = {
            "name": name,
            "dob": dob,
            "gender": gender,
            "father_name": father,
            "mother_name": mother,
        }
        return ExtractionResult(
            document_type=self.DOC_TYPE,
            fields=fields,
            confidence=_field_confidence(fields, self.REQUIRED),
            raw_text=text,
            parser_warnings=warnings,
        )


# =========================================================================
# Registry – maps document_type string → parser instance
# =========================================================================
PARSER_REGISTRY: Dict[str, Any] = {
    "aadhaar": AadhaarParser(),
    "pan": PANParser(),
    "voter_id": VoterIDParser(),
    "ration_card": RationCardParser(),
    "bank_passbook": BankPassbookParser(),
    "disability_certificate": DisabilityCertParser(),
    "income_certificate": IncomeCertificateParser(),
    "caste_certificate": CasteCertificateParser(),
    "residence_proof": ResidenceProofParser(),
    "land_records": LandRecordsParser(),
    "birth_certificate": BirthCertificateParser(),
}


def parse_document(document_type: str, text: str) -> ExtractionResult:
    """
    Convenience entry-point.
    Raises ValueError if document_type is unknown.
    """
    parser = PARSER_REGISTRY.get(document_type)
    if parser is None:
        raise ValueError(
            f"Unknown document type '{document_type}'. "
            f"Supported: {list(PARSER_REGISTRY.keys())}"
        )
    return parser.parse(text)
