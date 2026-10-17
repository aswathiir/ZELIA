# Remediation Playbook

## Order of operations
1. Apply schema migration.
- Run `references/sql/001_add_pdf_template_key.sql`.

2. Upload real templates to MinIO `templates` bucket.
- Use `dataset/govt/templates` (default strict scope excludes `formsandregister.pdf`).

3. Confirm scheme-to-template mapping.
- Verify no active scheme has null/empty `pdf_template_key`.

4. Generate and complete field maps.
- Start from stubs and adjust priority field coordinates by visual checks.

5. Patch workflow logic.
- Remove placeholder/hardcoded fallbacks.
- Ensure extraction contract includes consumed profile fields.

6. Re-run audit and gates.
- Block release until all strict gate checks pass.
