-- ZELIA Sample Scheme Data Population (Schema-Compatible)
-- Matches actual database schema: title, state_code, category, description, eligibility_rules

-- Karnataka State Schemes
INSERT INTO schemes (title, state_code, category, description, eligibility_rules) VALUES
('Karnataka Vidhva Pattiya Sahayavani (Widow Pension)', 'KA', 'pension',
 'Monthly pension scheme for widows aged 18-60 years with annual family income below ₹50,000. Provides financial assistance of ₹1,000 per month. Benefits: ₹1,000 per month. Apply at: https://sevasindhu.karnataka.gov.in',
 '[
   {"field": "age", "operator": ">=", "value": 18},
   {"field": "age", "operator": "<=", "value": 100},
   {"field": "monthly_income", "operator": "<=", "value": 4166},
   {"field": "marital_status", "operator": "==", "value": "widowed"}
 ]'),

('Karnataka Vriddha Pattiya Sahaya (Old Age Pension)', 'KA', 'pension',
 'Pension scheme for senior citizens above 60 years with annual income below ₹25,000. Monthly pension of ₹1,000. Benefits: ₹1,000 per month. Apply at: https://sevasindhu.karnataka.gov.in',
 '[
   {"field": "age", "operator": ">=", "value": 60},
   {"field": "monthly_income", "operator": "<=", "value": 2083}
 ]'),

('Karnataka Viklanga Pattiya (Disability Pension)', 'KA', 'pension',
 'Monthly pension for disabled persons with 40% or more disability certified by competent medical authority. Annual income limit ₹50,000. Benefits: ₹1,000 per month. Apply at: https://sevasindhu.karnataka.gov.in',
 '[
   {"field": "disability_status", "operator": "==", "value": true},
   {"field": "disability_percentage", "operator": ">=", "value": 40},
   {"field": "monthly_income", "operator": "<=", "value": 4166}
 ]'),

('Karnataka Raitha Vidya Nidhi (Farmer Pension)', 'KA', 'pension',
 'Pension scheme for farmers above 60 years who own agricultural land. No income limit. Provides ₹3,000 per month. Benefits: ₹3,000 per month. Apply at: https://sevasindhu.karnataka.gov.in',
 '[
   {"field": "age", "operator": ">=", "value": 60},
   {"field": "occupation", "operator": "==", "value": "farmer"}
 ]'),

('Sandhya Suraksha Scheme (Destitute Women)', 'KA', 'welfare',
 'Welfare scheme for destitute women above 55 years. Provides shelter, food, and medical care. Benefits: Shelter + ₹1,500/month. Apply at: https://ahara.kar.nic.in',
 '[
   {"field": "age", "operator": ">=", "value": 55},
   {"field": "gender", "operator": "==", "value": "female"},
   {"field": "monthly_income", "operator": "<=", "value": 1000}
 ]');

-- National Schemes (ALL states)
INSERT INTO schemes (title, state_code, category, description, eligibility_rules) VALUES
('Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (PM-JAY)', 'ALL', 'health',
 'National health insurance scheme providing coverage up to ₹5 lakh per family per year for secondary and tertiary care hospitalization. For families with annual income below ₹1 lakh. Benefits: Health coverage ₹5 lakh/year. Apply at: https://pmjay.gov.in',
 '[
   {"field": "monthly_income", "operator": "<=", "value": 8333}
 ]'),

('PM Kisan Samman Nidhi Yojana', 'ALL', 'agriculture',
 'Direct income support of ₹6,000 per year to farmer families owning cultivable land. Paid in three equal installments of ₹2,000 each. Benefits: ₹6,000 per year (₹2,000 x 3). Apply at: https://pmkisan.gov.in',
 '[
   {"field": "occupation", "operator": "==", "value": "farmer"}
 ]'),

('Atal Pension Yojana', 'ALL', 'pension',
 'Pension scheme for unorganized sector workers aged 18-40 years. Guaranteed pension of ₹1,000 to ₹5,000 per month after age 60. Benefits: ₹1,000-₹5,000/month after 60. Apply at: https://npscra.nsdl.co.in/atal-pension',
 '[
   {"field": "age", "operator": ">=", "value": 18},
   {"field": "age", "operator": "<=", "value": 40},
   {"field": "occupation", "operator": "!=", "value": "government_employee"}
 ]'),

('Pradhan Mantri Ujjwala Yojana', 'ALL', 'welfare',
 'Free LPG connection to women from BPL households. Includes first refill free and EMI facility for stove and regulator. Benefits: Free LPG connection + ₹1,600 deposit. Apply at: https://pmuy.gov.in',
 '[
   {"field": "gender", "operator": "==", "value": "female"},
   {"field": "monthly_income", "operator": "<=", "value": 2500}
 ]'),

('Pradhan Mantri Awas Yojana - Gramin', 'ALL', 'housing',
 'Housing scheme for rural homeless and those living in kutcha houses. Provides ₹1.2 lakh for construction in plain areas and ₹1.3 lakh in hilly areas. Benefits: ₹1.2-1.3 lakh for house. Apply at: https://pmayg.nic.in',
 '[
   {"field": "monthly_income", "operator": "<=", "value": 10000}
 ]');

-- Tamil Nadu Schemes
INSERT INTO schemes (title, state_code, category, description, eligibility_rules) VALUES
('Tamil Nadu Widow Pension Scheme', 'TN', 'pension',
 'Monthly pension for widows aged 20-60 years. Income limit ₹24,000 per annum. Pension amount ₹1,000 per month. Benefits: ₹1,000 per month. Apply at: https://www.tnpds.gov.in',
 '[
   {"field": "age", "operator": ">=", "value": 20},
   {"field": "age", "operator": "<=", "value": 100},
   {"field": "monthly_income", "operator": "<=", "value": 2000},
   {"field": "marital_status", "operator": "==", "value": "widowed"}
 ]'),

('Tamil Nadu Old Age Pension', 'TN', 'pension',
 'Monthly pension for senior citizens above 60 years with income below ₹24,000 per annum. Pension ₹1,000/month. Benefits: ₹1,000 per month. Apply at: https://www.tnpds.gov.in',
 '[
   {"field": "age", "operator": ">=", "value": 60},
   {"field": "monthly_income", "operator": "<=", "value": 2000}
 ]'),

('Tamil Nadu Farmer Relief Fund', 'TN', 'agriculture',
 'Relief fund for farmers affected by natural calamities. One-time compensation based on extent of damage. Benefits: ₹50,000-₹2 lakh (damage-based). Apply at: https://tn.gov.in',
 '[
   {"field": "occupation", "operator": "==", "value": "farmer"}
 ]');

-- Disability Schemes
INSERT INTO schemes (title, state_code, category, description, eligibility_rules) VALUES
('Unique Disability ID Card (UDID)', 'ALL', 'disability',
 'National-level ID card for persons with disabilities. Provides access to various government schemes and concessions. Benefits: UDID Card + scheme access. Apply at: https://www.swavlambancard.gov.in',
 '[
   {"field": "disability_status", "operator": "==", "value": true},
   {"field": "disability_percentage", "operator": ">=", "value": 40}
 ]'),

('Indira Gandhi National Disability Pension (Karnataka)', 'KA', 'pension',
 'Monthly pension for persons with severe disability (80%+) aged 18-80 years. Income limit ₹48,000 per annum. Benefits: ₹500 per month. Apply at: https://sevasindhu.karnataka.gov.in',
 '[
   {"field": "age", "operator": ">=", "value": 18},
   {"field": "age", "operator": "<=", "value": 80},
   {"field": "disability_status", "operator": "==", "value": true},
   {"field": "disability_percentage", "operator": ">=", "value": 80},
   {"field": "monthly_income", "operator": "<=", "value": 4000}
 ]');

-- Verify insertion
SELECT 
    state_code,
    COUNT(*) as scheme_count,
    STRING_AGG(title, ', ') as schemes
FROM schemes
GROUP BY state_code
ORDER BY state_code;

-- Show total count
SELECT COUNT(*) as total_schemes FROM schemes;
