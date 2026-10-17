# Runbook

## 1) Create template manifest
```bash
python3 skills/zelia-pdf-form-audit/scripts/generate_template_manifest.py \
  --templates-dir dataset/govt/templates \
  --out /tmp/zelia_template_manifest.json
```

## 2) Create field map stubs
```bash
python3 skills/zelia-pdf-form-audit/scripts/generate_field_map_stubs.py \
  --manifest /tmp/zelia_template_manifest.json \
  --out /tmp/zelia_field_map.json
```

## 3) Run audit
```bash
python3 skills/zelia-pdf-form-audit/scripts/audit_pdf_pipeline.py \
  --workflow zeliaintegration_v28b_fresh.json \
  --schema schema_v28_upgrade.sql,supabase_Schema.sql \
  --templates-dir dataset/govt/templates \
  --placeholders-dir data/forms \
  --out /tmp/zelia_audit.json
```

## 4) Validate strict gates
```bash
python3 skills/zelia-pdf-form-audit/scripts/validate_gate.py \
  --audit /tmp/zelia_audit.json \
  --field-map /tmp/zelia_field_map.json \
  --fail-on PLACEHOLDER_FALLBACK,HARDCODED_TEMPLATE_KEY,MISSING_PDF_TEMPLATE_KEY_SCHEMA,MISSING_EXTRACTED_FIELDS,FIELD_MAP_MISSING_PRIORITY,UPLOAD_PATH_VERIFICATION_MISSING
```

## Gate interpretation
- `pass`: strict checks passed for configured rules.
- `fail`: at least one configured rule violated; treat as release blocker.
