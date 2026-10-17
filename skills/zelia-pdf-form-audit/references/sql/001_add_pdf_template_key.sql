-- Add template mapping support to schemes
ALTER TABLE schemes
ADD COLUMN IF NOT EXISTS pdf_template_key VARCHAR(255);

-- Seed mappings for currently active ZELIA scheme IDs
UPDATE schemes SET pdf_template_key = 'pension1.pdf' WHERE scheme_id = 'ka-widow-pension';
UPDATE schemes SET pdf_template_key = 'pension1.pdf' WHERE scheme_id = 'ka-old-age-pension';
UPDATE schemes SET pdf_template_key = 'disabledgovt.pdf' WHERE scheme_id = 'ka-disability-pension';
UPDATE schemes SET pdf_template_key = 'Application_for_assiatance.pdf' WHERE scheme_id = 'pmjay';
UPDATE schemes SET pdf_template_key = 'jobskilltraining.pdf' WHERE scheme_id = 'pm-kisan';
UPDATE schemes SET pdf_template_key = 'intimationform.pdf' WHERE scheme_id = 'ka-destitute-pension';
UPDATE schemes SET pdf_template_key = 'swasraya.pdf' WHERE scheme_id = 'pm-ujjwala';
UPDATE schemes SET pdf_template_key = 'niramaya.pdf' WHERE scheme_id = 'nsap-ignoaps';

-- Validation query: identify active schemes with missing template mapping
SELECT scheme_id, scheme_name
FROM schemes
WHERE COALESCE(pdf_template_key, '') = ''
ORDER BY scheme_id;
