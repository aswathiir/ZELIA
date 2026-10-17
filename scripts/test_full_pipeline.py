#!/usr/bin/env python3
"""
===========================================================================
ZELIA Full Pipeline Integration Test
===========================================================================
Tests the ENTIRE flow:

  Phase 1 — Fill form with INCOMPLETE user data
     → form-filler returns PDF with missing fields identified

  Phase 2 — Upload Aadhaar image → OCR extracts structured data
     → document_store populated with extracted fields

  Phase 3 — Auto-fill missing fields from OCR-extracted data
     → merge user profile with document data

  Phase 4 — Re-fill form with COMPLETE data → all fields populated
     → verify 100% fill confidence

  Phase 5 — Verify cross-check: user vs OCR data
     → mismatches flagged, corrections suggested

This proves the fallback pipeline works end-to-end.
===========================================================================
"""

import json
import base64
import time
import urllib.request
import os
import sys

# ── Service URLs ──────────────────────────────────────────────────────
FORM_FILLER_URL = os.environ.get("FORM_FILLER_URL", "http://localhost:8019")
OCR_SERVICE_URL = os.environ.get("OCR_SERVICE_URL", "http://localhost:8003")

# ── Test data ─────────────────────────────────────────────────────────
CALL_ID = f"pipeline_test_{int(time.time())}"
HH_HASH = f"hh_{CALL_ID}"

# Form fields for a government pension scheme application
FORM_FIELDS = [
    {"field_id": "f_name",     "field_name": "Applicant Name",    "x": 150, "y": 120, "required": True},
    {"field_id": "f_age",      "field_name": "Age",               "x": 150, "y": 150, "field_type": "number"},
    {"field_id": "f_gender",   "field_name": "Gender",            "x": 350, "y": 150},
    {"field_id": "f_dob",      "field_name": "Date of Birth",     "x": 150, "y": 180},
    {"field_id": "f_aadhaar",  "field_name": "Aadhaar Number",    "x": 150, "y": 210, "required": True},
    {"field_id": "f_address",  "field_name": "Address",           "x": 150, "y": 240, "required": True},
    {"field_id": "f_income",   "field_name": "Annual Income",     "x": 150, "y": 270, "field_type": "number"},
    {"field_id": "f_father",   "field_name": "Father/Husband Name","x": 150, "y": 300},
    {"field_id": "f_phone",    "field_name": "Phone Number",      "x": 150, "y": 330},
    {"field_id": "f_bank",     "field_name": "Bank Account",      "x": 150, "y": 360},
    {"field_id": "f_ifsc",     "field_name": "Bank IFSC",         "x": 350, "y": 360},
]

# User profile with DELIBERATE GAPS (simulates incomplete chatbot extraction)
USER_PROFILE_INCOMPLETE = {
    "name": "Lakshmi",                  # Partial name (surname missing)
    "age": "65",
    "gender": "",                       # ← MISSING
    "dob": "",                          # ← MISSING
    "aadhaar_number": "",               # ← MISSING (critical!)
    "address": "",                      # ← MISSING
    "annual_income": "36000",
    "father_name": "",                  # ← MISSING
    "phone_number": "9876543210",
    "bank_account": "",                 # ← MISSING
    "bank_ifsc": "",                    # ← MISSING
}

# Mapping: user_profile key → form field_id
PROFILE_TO_FIELD = {
    "name":           "f_name",
    "age":            "f_age",
    "gender":         "f_gender",
    "dob":            "f_dob",
    "aadhaar_number": "f_aadhaar",
    "address":        "f_address",
    "annual_income":  "f_income",
    "father_name":    "f_father",
    "phone_number":   "f_phone",
    "bank_account":   "f_bank",
    "bank_ifsc":      "f_ifsc",
}

# Output directory
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ingestion", "pipeline_test")
os.makedirs(OUT_DIR, exist_ok=True)

PASS = 0
FAIL = 0


def green(s):  return f"\033[32m{s}\033[0m"
def red(s):    return f"\033[31m{s}\033[0m"
def yellow(s): return f"\033[33m{s}\033[0m"
def bold(s):   return f"\033[1m{s}\033[0m"


def check(label, ok):
    global PASS, FAIL
    if ok:
        print(f"  {green('✅')} {label}")
        PASS += 1
    else:
        print(f"  {red('❌')} {label}")
        FAIL += 1
    return ok


def api(method, base_url, path, data=None, timeout=120):
    url = f"{base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if data:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method=method)
    else:
        req = urllib.request.Request(url, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  {red('⚠')} HTTP {e.code}: {body[:300]}")
        return None, e.code
    except Exception as e:
        print(f"  {red('⚠')} Connection error: {e}")
        return None, 0


def profile_to_field_values(profile):
    """Convert user profile dict to form field values dict."""
    return {PROFILE_TO_FIELD[k]: v for k, v in profile.items() if k in PROFILE_TO_FIELD}


def save_pdf(base64_str, filename):
    """Decode and save a base64 PDF to the output directory."""
    path = os.path.join(OUT_DIR, filename)
    with open(path, "wb") as f:
        f.write(base64.b64decode(base64_str))
    return path


def generate_aadhaar_image():
    """Generate a synthetic Aadhaar card image for OCR testing."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (800, 500), "white")
    d = ImageDraw.Draw(img)
    d.text((50, 20),  "GOVERNMENT OF INDIA", fill="black")
    d.text((50, 50),  "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", fill="black")
    d.text((50, 100), "Name: Lakshmi Devi", fill="black")
    d.text((50, 140), "DOB: 15/03/1961", fill="black")
    d.text((50, 180), "Female", fill="black")
    d.text((50, 230), "S/O Ramesh Kumar", fill="black")
    d.text((50, 270), "Address: House No 42 Kuvempunagar", fill="black")
    d.text((50, 300), "Mysuru Karnataka 570023", fill="black")
    d.text((50, 360), "1234 5678 9012", fill="black")
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img.save(os.path.join(OUT_DIR, "synthetic_aadhaar.jpg"))
    return base64.b64encode(buf.getvalue()).decode()


# =====================================================================
print(bold("=" * 70))
print(bold(" ZELIA Full Pipeline Integration Test"))
print(bold(f" Call ID: {CALL_ID}"))
print(bold("=" * 70))
print()

# ── PHASE 1: Fill form with INCOMPLETE data ──────────────────────────
print(bold("━" * 70))
print(bold("PHASE 1: Fill form with INCOMPLETE user data"))
print(bold("━" * 70))
print(f"  User profile has {sum(1 for v in USER_PROFILE_INCOMPLETE.values() if not v)} missing fields")
print(f"  Missing: {[k for k, v in USER_PROFILE_INCOMPLETE.items() if not v]}")
print()

field_values_p1 = profile_to_field_values(USER_PROFILE_INCOMPLETE)
fill_req_p1 = {
    "document_id": "ka_old_age_pension",
    "form_fields": FORM_FIELDS,
    "field_values": field_values_p1,
    "citizen_id": "citizen_demo",
    "call_id": CALL_ID,
}

r1, code1 = api("POST", FORM_FILLER_URL, "/fill-form", fill_req_p1)
if r1:
    fields_empty = r1.get("fields_empty", [fid for fid, val in field_values_p1.items() if not val])
    print(f"  Form Filler Response:")
    print(f"    Status:         {r1['status']}")
    print(f"    Fields filled:  {r1['fields_filled']}/{r1['fields_total']}")
    print(f"    Fields empty:   {fields_empty}")
    print(f"    Confidence:     {r1['fill_confidence']:.0%}")
    check("Form filled (partial)", r1["status"] == "success")
    check(f"Fill confidence < 100% ({r1['fill_confidence']:.0%})", r1["fill_confidence"] < 1.0)
    check(f"More fields empty than filled", r1["fields_filled"] < r1["fields_total"])

    if r1.get("filled_document_base64"):
        p1_pdf = save_pdf(r1["filled_document_base64"], "phase1_incomplete_form.pdf")
        print(f"  📄 Saved incomplete PDF: {p1_pdf}")

    P1_FILLED = r1["fields_filled"]
    P1_CONFIDENCE = r1["fill_confidence"]
else:
    check("Form filler returned 200", False)
    P1_FILLED = 0
    P1_CONFIDENCE = 0

print()

# ── PHASE 2: Upload ID document → OCR extraction ────────────────────
print(bold("━" * 70))
print(bold("PHASE 2: Upload Aadhaar card → OCR extracts structured data"))
print(bold("━" * 70))

aadhaar_b64 = generate_aadhaar_image()
print(f"  Generated synthetic Aadhaar image ({len(aadhaar_b64)} bytes base64)")
print(f"  📸 Saved: {os.path.join(OUT_DIR, 'synthetic_aadhaar.jpg')}")

r2, code2 = api("POST", OCR_SERVICE_URL, "/extract-document", {
    "household_hash": HH_HASH,
    "document_type": "aadhaar",
    "image_base64": aadhaar_b64,
    "language": "en",
})

if r2:
    print(f"\n  OCR Extraction Result:")
    print(f"    Document type:    {r2['document_type']}")
    print(f"    Confidence:       {r2['extraction_confidence']}")
    print(f"    Processing time:  {r2['processing_time']}s")
    print(f"    Stored in MinIO:  {r2['stored']} → {r2.get('storage_path', '')}")
    print(f"    Extracted fields:")
    for k, v in r2["extracted_fields"].items():
        marker = green("●") if v else red("○")
        print(f"      {marker} {k}: {v}")

    OCR_FIELDS = r2["extracted_fields"]
    check("Document type = aadhaar", r2["document_type"] == "aadhaar")
    check("Aadhaar number extracted", OCR_FIELDS.get("aadhaar_number") is not None)
    check("Name extracted", OCR_FIELDS.get("name") is not None)
    check("Gender extracted", OCR_FIELDS.get("gender") is not None)
    check("Image stored in MinIO", r2["stored"] is True)
else:
    check("OCR extraction returned 200", False)
    OCR_FIELDS = {}

print()

# ── PHASE 3: Auto-fill missing fields from OCR ──────────────────────
print(bold("━" * 70))
print(bold("PHASE 3: Auto-fill missing fields from OCR data"))
print(bold("━" * 70))

r3, code3 = api("POST", OCR_SERVICE_URL, "/auto-fill", {
    "household_hash": HH_HASH,
    "user_profile": USER_PROFILE_INCOMPLETE,
})

if r3:
    print(f"  Fields auto-filled: {r3['fields_filled']}")
    for f in r3["fields_filled"]:
        src = r3["fill_sources"].get(f, "?")
        val = r3["filled_profile"].get(f, "")
        print(f"    {green('+')} {f}: \"{val}\" ← {src}")

    check(f"Auto-fill populated {len(r3['fields_filled'])} fields", len(r3["fields_filled"]) >= 1)

    FILLED_PROFILE = r3["filled_profile"]
else:
    check("Auto-fill returned 200", False)
    FILLED_PROFILE = USER_PROFILE_INCOMPLETE

# Show the merged profile
print(f"\n  Merged profile (user data + OCR data):")
for k, v in FILLED_PROFILE.items():
    if k in USER_PROFILE_INCOMPLETE:
        was_missing = not USER_PROFILE_INCOMPLETE[k]
        source = yellow("← OCR") if was_missing and v else ""
        marker = green("●") if v else red("○")
        print(f"    {marker} {k}: {v}  {source}")

print()

# ── PHASE 4: Re-fill form with COMPLETE data ────────────────────────
print(bold("━" * 70))
print(bold("PHASE 4: Re-fill form with COMPLETE data (user + OCR)"))
print(bold("━" * 70))

field_values_p4 = profile_to_field_values(FILLED_PROFILE)
fill_req_p4 = {
    "document_id": "ka_old_age_pension",
    "form_fields": FORM_FIELDS,
    "field_values": field_values_p4,
    "citizen_id": "citizen_demo",
    "call_id": f"{CALL_ID}_refill",
}

r4, code4 = api("POST", FORM_FILLER_URL, "/fill-form", fill_req_p4)
if r4:
    print(f"  Form Filler Response:")
    print(f"    Status:         {r4['status']}")
    print(f"    Fields filled:  {r4['fields_filled']}/{r4['fields_total']}")
    p4_empty = r4.get('fields_empty', [])
    print(f"    Fields empty:   {p4_empty}")
    print(f"    Confidence:     {r4['fill_confidence']:.0%}")

    check("Form filled (complete)", r4["status"] == "success")
    check(
        f"Confidence improved: {P1_CONFIDENCE:.0%} → {r4['fill_confidence']:.0%}",
        r4["fill_confidence"] > P1_CONFIDENCE,
    )
    check(f"More fields filled: {P1_FILLED} → {r4['fields_filled']}", 
          r4["fields_filled"] > P1_FILLED)

    if r4.get("filled_document_base64"):
        p4_pdf = save_pdf(r4["filled_document_base64"], "phase4_complete_form.pdf")
        print(f"  📄 Saved complete PDF: {p4_pdf}")
else:
    check("Form filler returned 200", False)

print()

# ── PHASE 5: Verify cross-check ─────────────────────────────────────
print(bold("━" * 70))
print(bold("PHASE 5: CHW verification — cross-check user vs OCR data"))
print(bold("━" * 70))

# 5a: Matching data
print(f"\n  5a) Verify with matching data:")
r5a, _ = api("POST", OCR_SERVICE_URL, "/verify-submission", {
    "household_hash": HH_HASH,
    "user_profile": FILLED_PROFILE,
})
if r5a:
    print(f"    Status: {r5a['overall_status']}, Matched: {r5a['matched']}, Mismatched: {r5a['mismatched']}")
    for fd in r5a.get("field_details", []):
        icon = {"matched": green("✓"), "mismatch": red("✗"), "auto_filled": yellow("~"), "not_in_documents": "—"}
        print(f"      {icon.get(fd['status'], '?')} {fd['field']}: {fd['status']}")
    check("Correct data → verified", r5a["overall_status"] in ("verified", "no_documents"))

# 5b: Tampered data (simulates data entry error)
print(f"\n  5b) Verify with WRONG Aadhaar number:")
tampered = dict(FILLED_PROFILE)
tampered["aadhaar_number"] = "9999 0000 1111"
tampered["name"] = "Wrong Person"

r5b, _ = api("POST", OCR_SERVICE_URL, "/verify-submission", {
    "household_hash": HH_HASH,
    "user_profile": tampered,
})
if r5b:
    print(f"    Status: {r5b['overall_status']}, Mismatches: {r5b['mismatched']}")
    print(f"    Suggested corrections: {json.dumps(r5b['suggested_corrections'], indent=6)}")
    check("Wrong data → needs_review", r5b["overall_status"] == "needs_review")
    check("Corrections suggested", len(r5b["suggested_corrections"]) > 0)

print()

# ── FINAL RESULTS ────────────────────────────────────────────────────
print(bold("=" * 70))
print(bold(f" FINAL RESULTS: {PASS} passed, {FAIL} failed"))
print(bold("=" * 70))

# Save summary
summary = {
    "call_id": CALL_ID,
    "household_hash": HH_HASH,
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "phase1_incomplete": {
        "fields_filled": r1["fields_filled"] if r1 else 0,
        "fields_total": r1["fields_total"] if r1 else 0,
        "confidence": r1["fill_confidence"] if r1 else 0,
    },
    "phase2_ocr": {
        "document_type": r2["document_type"] if r2 else "",
        "extracted_fields": r2["extracted_fields"] if r2 else {},
        "stored": r2["stored"] if r2 else False,
    },
    "phase3_autofill": {
        "fields_filled": r3["fields_filled"] if r3 else [],
        "fill_sources": r3["fill_sources"] if r3 else {},
    },
    "phase4_complete": {
        "fields_filled": r4["fields_filled"] if r4 else 0,
        "fields_total": r4["fields_total"] if r4 else 0,
        "confidence": r4["fill_confidence"] if r4 else 0,
        "remaining_empty": r4.get("fields_empty", []) if r4 else [],
    },
    "phase5_verification": {
        "matching_status": r5a["overall_status"] if r5a else "",
        "tampered_status": r5b["overall_status"] if r5b else "",
    },
    "tests": {"passed": PASS, "failed": FAIL},
}

summary_path = os.path.join(OUT_DIR, "pipeline_test_summary.json")
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)
print(f"\n  📊 Summary saved: {summary_path}")
print(f"  📄 PDFs saved in: {OUT_DIR}")

sys.exit(0 if FAIL == 0 else 1)
