---
name: zelia-pdf-form-audit
description: Audit, gate, and remediate ZELIA PDF form autofill pipelines that use n8n, Supabase/Postgres, and MinIO. Use when working on government PDF template selection, scheme-to-template mapping, profile-data propagation into PDF generation, field-coordinate map coverage, and production-readiness validation with strict fail gates.
---

# ZELIA PDF Form Audit

## Overview
Run a deterministic audit for ZELIA's PDF autofill workflow, generate machine-readable findings, and enforce strict production gates before rollout.

## Inputs
- Workflow JSON: default `zeliaintegration_v28b_fresh.json`
- Schema SQL: one or more SQL files used to define or upgrade ZELIA tables
- Real templates directory: default `dataset/govt/templates`
- Placeholder templates directory: default `data/forms`

## Workflow
1. Build template manifest.
- Run `scripts/generate_template_manifest.py --templates-dir dataset/govt/templates --out /tmp/template_manifest.json`
- Exclude `formsandregister.pdf` by default. Include it only with `--include-bundle`.

2. Generate field map stubs.
- Run `scripts/generate_field_map_stubs.py --manifest /tmp/template_manifest.json --out /tmp/field_map.json`
- Fill coordinates later per template; keep page-2 rich summary as default strategy.

3. Audit workflow and schema.
- Run `scripts/audit_pdf_pipeline.py --workflow zeliaintegration_v28b_fresh.json --schema schema_v28_upgrade.sql --templates-dir dataset/govt/templates --placeholders-dir data/forms --out /tmp/audit.json`
- Review high and critical findings first.

4. Run strict gates.
- Run `scripts/validate_gate.py --audit /tmp/audit.json --field-map /tmp/field_map.json --fail-on PLACEHOLDER_FALLBACK,HARDCODED_TEMPLATE_KEY,MISSING_PDF_TEMPLATE_KEY_SCHEMA,MISSING_EXTRACTED_FIELDS,FIELD_MAP_MISSING_PRIORITY,UPLOAD_PATH_VERIFICATION_MISSING`
- Treat any non-zero exit as release-blocking.

5. Apply remediation in fixed order.
- Schema migration first.
- Template upload and DB mapping next.
- Field map completion after mapping.
- Workflow code/node fixes last.

## Required Rules
- Never use placeholder templates in production.
- Require `schemes.pdf_template_key` and mapped keys for active schemes.
- Require extracted profile fields that PDF renderer consumes.
- Require field-map coverage for priority fields: `name`, `age`, `address`, `gender`.
- Require upload path verification evidence in workflow or checks.

## Resources
- SQL migration: `references/sql/001_add_pdf_template_key.sql`
- Contracts:
- `references/schemas/audit_report.schema.json`
- `references/schemas/template_manifest.schema.json`
- `references/schemas/field_map.schema.json`
- Operational references:
- `references/workflow-paths.md`
- `references/remediation-playbook.md`
- `references/runbook.md`
