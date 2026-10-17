# Canonical Workflow Paths

## Canonical file
- `zeliaintegration_v28b_fresh.json`

## Required node contracts
- `Extract Profile (Groq)`
- Output JSON must support profile extraction prompt for all fields consumed downstream.

- `Parse Profile + Hash`
- Must emit `user_profile` with fields consumed by PDF generator.

- `Check Eligibility (SQL)`
- Must select `s.pdf_template_key` and propagate it through downstream nodes.

- `Store in Supabase`
- Must persist stable `user_profile` and scheme mapping context for PDF generation.

- `Fetch Template`
- Must use dynamic file key from mapped `pdf_template_key`.
- Must not fallback to placeholder files from `data/forms`.

- `Generate PDF (pdf-lib)`
- Must avoid consuming missing fields from `user_profile`.
- Must render rich data page and only priority overlays on template page.

- `Upload to MinIO`
- Must have explicit bucket and filename path evidence.
