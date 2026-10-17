# ZELIA COMPLETE DEPLOYMENT GUIDE
## Voice-First, Zero-Literacy, Privacy-Preserving Government Scheme Platform

---

## 🎯 WHAT IS ZELIA?

**ZELIA (Zero-Literacy Eligibility & Livelihood Intelligence Assistant)** is a voice-first AI platform that helps India's 300+ million zero-literacy citizens access 1,000+ government welfare schemes through:

✅ **Voice-Only** - No reading or typing required  
✅ **Native Languages** - Tamil, Hindi, Kannada, Telugu, Malayalam, English  
✅ **Privacy-Preserving** - Cryptographic hashing, no raw PII storage  
✅ **Culturally-Aware** - Understands local terms and social context  
✅ **Action-Oriented** - Auto-fills forms, not just information  

---

## 🏗️ ARCHITECTURE

### Old Approach (Complex, Broke)
```
8 microservices + Docker + MinIO + Complex networking
= Configuration hell, cascade failures
```

### New Approach (Simple, Works)
```
Ultravox (Voice) → n8n (Orchestration) → Supabase (Database + Storage)
+ Sarvam AI (Translation) + OpenAI (Intelligence)
= 15-minute setup, $20/month, production-ready
```

### Complete Flow
```
1. User speaks in Tamil: "நான் 65 வயது விதவை"
2. Ultravox captures voice + paralinguistics (tone, confidence)
3. Sarvam AI translates: "I am 65 year old widow"
4. GPT-4 extracts: {age: 65, marital_status: "widowed"}
5. PostgreSQL + pgvector checks eligibility (RAG + SQL)
6. Records consent with tone verification
7. Sarvam AI translates response back to Tamil
8. Ultravox speaks response
9. PDF auto-generated and stored
10. Data saved with SHA-256 hashing (privacy)
```

---

## 📦 WHAT YOU GET

### 1. n8n Workflow (`zelia-complete-voice-first-v11.json`)
- **15 nodes** covering complete voice pipeline
- Voice capture → Translation → AI → Eligibility → Response
- Privacy-preserving household hashing
- Consent ledger with paralinguistic verification
- Bilingual response generation

### 2. Database Schema (`zelia-complete-schema.sql`)
- **3 core tables**: schemes, households (privacy-preserving), submissions
- **pgvector enabled** for RAG similarity search
- **8 schemes pre-loaded**: 5 Karnataka + 3 National
- **RLS policies** for privacy protection
- **Consent ledger** for GDPR compliance

### 3. Documentation
- **ZELIA_MAGIC_PROMPT_V2.md** - Complete context for LLMs
- **This guide** - Step-by-step deployment
- **Testing scripts** - Validate everything works

---

## ⚡ QUICK START (15 MINUTES)

### Step 1: Supabase Setup (5 min)

```bash
1. Go to https://supabase.com
2. Create project: "zelia-production"
3. Wait 2 minutes for initialization
4. SQL Editor → Run zelia-complete-schema.sql
5. Success message: "8 schemes populated"
6. Settings → API → Copy:
   - Project URL: https://xxx.supabase.co
   - anon key: eyJ...
   - service_role key: eyJ...
```

### Step 2: Enable pgvector (2 min)

```bash
1. In Supabase dashboard: Database → Extensions
2. Search "vector"
3. Enable "vector" extension
4. Verify: SQL Editor → SELECT * FROM pg_extension WHERE extname = 'vector';
```

### Step 3: n8n Setup (3 min)

**Option A: n8n Cloud (Recommended)**
```bash
1. https://n8n.io/cloud → Sign up
2. Create workspace
3. Done!
```

**Option B: Self-Hosted**
```bash
docker run -d --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

### Step 4: API Keys (3 min)

Get these API keys:

```bash
1. OpenAI: https://platform.openai.com/api-keys
   Copy: sk-...

2. Sarvam AI: https://www.sarvam.ai/
   Sign up → API Keys → Copy

3. Ultravox: https://ultravox.ai/
   Sign up → Get API key
```

### Step 5: Configure n8n Credentials (2 min)

```bash
In n8n:

1. PostgreSQL Credential:
   Name: "Supabase ZELIA"
   Host: db.xxx.supabase.co  (extract from Supabase URL)
   Port: 5432
   Database: postgres
   User: postgres
   Password: [Your Supabase password]
   SSL: Enable
   Test → Save

2. OpenAI Credential:
   Name: "OpenAI GPT-4"
   API Key: sk-...
   Test → Save

3. HTTP Header Auth (Sarvam AI):
   Name: "Sarvam AI"
   Header Name: "api-subscription-key"
   Header Value: [Your Sarvam API key]
   Save

4. Supabase API:
   Name: "Supabase API"
   Host: https://xxx.supabase.co
   Service Role Key: [From Step 1]
   Save
```

### Step 6: Import Workflow (2 min)

```bash
1. n8n → Workflows → "Add workflow" → "Import from file"
2. Select: zelia-complete-voice-first-v11.json
3. Click nodes and connect credentials:
   - "Check Eligibility (RAG + SQL)" → Supabase ZELIA
   - "Extract Profile (GPT-4)" → OpenAI GPT-4
   - "Translate (Sarvam AI)" → Sarvam AI
   - "Store Household" → Supabase ZELIA
4. Save workflow
5. Toggle "Active" (green)
```

---

## 🧪 TESTING

### Test 1: Basic Voice Input (Simulate Ultravox)

```bash
curl -X POST [YOUR_N8N_WEBHOOK_URL] \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "test_voice_001",
    "customer_number": "+919876543210",
    "language": "hi",
    "messages": [
      {
        "role": "user",
        "text": "Main 65 saal ki vidhva hoon, mahine ke 3000 rupay kamaati hoon"
      }
    ],
    "metadata": {
      "tone": "positive",
      "confidence": 0.85,
      "urgency": "normal",
      "chw_id": "CHW_KA_001",
      "location": "Karnataka"
    }
  }'
```

**Expected Response:**
```json
{
  "status": "success",
  "household_id": "a3f8c9d2",
  "eligible_schemes": 2,
  "response_native": "बहुत अच्छी खबर! आप 2 योजनाओं के लिए पात्र हैं...",
  "response_english": "Excellent news! You qualify for 2 schemes...",
  "consent_recorded": true,
  "next_step": "pdf_generation_queued"
}
```

### Test 2: Tamil Language

```bash
curl -X POST [YOUR_N8N_WEBHOOK_URL] \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "test_tamil_001",
    "customer_number": "+919876543211",
    "language": "ta",
    "messages": [
      {
        "role": "user",
        "text": "நான் 68 வயது, மாதம் 2000 ரூபாய் சம்பாதிக்கிறேன்"
      }
    ],
    "metadata": {
      "tone": "neutral",
      "confidence": 0.75
    }
  }'
```

**Expected**: Old age pension eligibility in Tamil

### Test 3: Verify Database

```sql
-- In Supabase SQL Editor

-- Check households stored
SELECT 
    household_id_hash,
    profile_json->>'age' as age,
    profile_json->>'marital_status' as marital_status,
    consent_ledger_json->>'consent_verified' as consent,
    created_at
FROM households
ORDER BY created_at DESC
LIMIT 5;

-- Expected: 2 rows with hashed IDs

-- Check submissions
SELECT 
    call_id,
    household_id_hash,
    schemes_applied,
    status,
    created_at
FROM submissions
ORDER BY created_at DESC
LIMIT 5;

-- Expected: 2 rows with scheme applications
```

---

## 🔐 PRIVACY & SECURITY

### Privacy Features Implemented

1. **Cryptographic Hashing**
```javascript
// In n8n: Extract Voice & Privacy Data node
const crypto = require('crypto');
const householdIdHash = crypto
  .createHash('sha256')
  .update(phoneNumber + process.env.HASH_SALT)
  .digest('hex');
// Result: "a3f8c9d2e4f5..." (irreversible)
```

2. **Consent Ledger**
```json
{
  "timestamp": "2026-02-14T10:30:00Z",
  "consent_verified": true,
  "tone": "positive",
  "confidence": 0.89,
  "schemes_consented": ["ka-widow-pension"],
  "chw_witness": "CHW_12345",
  "valid_for_days": 90
}
```

3. **Row Level Security**
```sql
-- CHWs can only see their own households
CREATE POLICY "CHWs see own data"
ON households FOR SELECT
USING (chw_id = current_user_chw_id());
```

4. **No PII in Logs**
- n8n executions auto-deleted after 7 days
- Logs contain only hashed IDs
- Phone numbers never logged

### GDPR Compliance

✅ **Right to Access**: Query by household_id_hash  
✅ **Right to Erasure**: DELETE FROM households WHERE household_id_hash = '...'  
✅ **Right to Portability**: Export profile_json as JSON  
✅ **Consent Management**: Consent ledger with expiry (90 days)  
✅ **Data Minimization**: Only essential fields stored  
✅ **Purpose Limitation**: Data used only for scheme applications  

---

## 🌐 MULTI-LANGUAGE SETUP

### Add New Language (Example: Punjabi)

```bash
1. Update Sarvam AI call in n8n:
   - "target_language_code": "pa"  (Punjabi)

2. Update GPT-4 system prompt:
   - Add: "Punjabi terms: 'vidhava' means widow, 'patta' means pension"

3. Test:
   curl -X POST [WEBHOOK_URL] \
     -d '{"language": "pa", "messages": [{"text": "Main vidhva haan"}]}'
```

### Supported Languages (Sarvam AI)

| Language | Code | Status |
|----------|------|--------|
| Hindi | hi | ✅ Tested |
| Tamil | ta | ✅ Tested |
| Telugu | te | ✅ Ready |
| Kannada | kn | ✅ Ready |
| Malayalam | ml | ✅ Ready |
| Gujarati | gu | ✅ Ready |
| Marathi | mr | ✅ Ready |
| Bengali | bn | ✅ Ready |
| Punjabi | pa | ⏳ Coming |
| Odia | or | ⏳ Coming |

---

## 📱 OFFLINE CAPABILITY (Phase 2)

### Architecture for Offline CHW Tablets

```
┌─────────────────────────────────────┐
│   CHW Android Tablet (Offline)      │
│  ┌──────────────────────────────┐   │
│  │  Local SQLite Database       │   │
│  │  - Schemes cache (updated    │   │
│  │    weekly when online)       │   │
│  │  - Pending submissions       │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  Offline Ultravox SDK        │   │
│  │  - Voice capture & basic STT │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  Sync Service                │   │
│  │  - Uploads when WiFi found   │   │
│  │  - Downloads new schemes     │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
                 │
          When WiFi available
                 │
                 ▼
┌─────────────────────────────────────┐
│     n8n + Supabase (Cloud)          │
│  - Full processing                  │
│  - PDF generation                   │
│  - Government API integration       │
└─────────────────────────────────────┘
```

### Implementation Plan
1. **SQLite schema mirror** (same as Supabase)
2. **Local voice capture** (Ultravox SDK for Android)
3. **Basic eligibility check** (cached rules)
4. **Queue submissions** (upload when online)
5. **Conflict resolution** (last-write-wins with timestamps)

---

## 🎨 CUSTOMIZATION GUIDE

### Add New State Schemes

```sql
-- Add Uttar Pradesh schemes
INSERT INTO schemes (
  scheme_id, scheme_name, state_code, category, 
  description, benefits, eligibility_rules
) VALUES (
  'up-kanya-sumangala', 
  'UP Kanya Sumangala Yojana (Girl Child Welfare)', 
  'UP', 
  'child_welfare',
  'Financial assistance for girl child education and marriage',
  '₹15,000 in installments',
  '{"gender": "female", "age_max": 25, "family_income_max": 300000}'::jsonb
);

-- Update n8n eligibility node to include UP schemes
```

### Add Custom Eligibility Rules

```sql
-- Complex rule example: widow + SC/ST + below poverty line
UPDATE schemes 
SET eligibility_rules = '{
  "AND": [
    {"marital_status": "widowed"},
    {"caste_category": ["SC", "ST"]},
    {"annual_income": {"$lte": 12000}}
  ]
}'::jsonb
WHERE scheme_id = 'special-widow-scheme';
```

### Customize Response Templates

```javascript
// In "Generate Response (English)" node

// Add cultural variations
if (household.state_code === 'TN') {
  response = `வணக்கம்! You qualify for ${schemes.length} schemes...`;
} else if (household.state_code === 'MH') {
  response = `नमस्कार! You qualify for ${schemes.length} schemes...`;
}

// Add empathy for urgency
if (household.paralinguistic.urgency === 'high') {
  response = `I understand this is urgent. ${response}`;
}
```

---

## 📊 MONITORING & ANALYTICS

### Key Metrics Dashboard

**In Supabase SQL Editor**, create this view:

```sql
CREATE VIEW zelia_dashboard AS
SELECT 
    -- Daily stats
    COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE) as calls_today,
    COUNT(DISTINCT household_id_hash) as unique_households,
    
    -- Language distribution
    jsonb_object_agg(
        paralinguistic_json->>'original_language', 
        COUNT(*)
    ) as languages,
    
    -- Top schemes
    (
        SELECT jsonb_agg(jsonb_build_object(
            'scheme', scheme_id, 
            'applications', count
        ))
        FROM (
            SELECT 
                jsonb_array_elements_text(schemes_applied) as scheme_id,
                COUNT(*) as count
            FROM submissions
            GROUP BY scheme_id
            ORDER BY count DESC
            LIMIT 5
        ) top_schemes
    ) as top_5_schemes,
    
    -- Consent quality
    AVG((consent_ledger_json->>'confidence')::float) as avg_consent_confidence,
    COUNT(*) FILTER (
        WHERE (consent_ledger_json->>'consent_verified')::boolean = true
    ) as verified_consents
FROM households
WHERE created_at > NOW() - INTERVAL '30 days';
```

### Grafana Dashboard (Optional)

```bash
1. Add Supabase as data source in Grafana
2. Create panels:
   - Calls per day (time series)
   - Schemes applied (pie chart)
   - Language distribution (bar chart)
   - Consent verification rate (gauge)
```

---

## 🚨 TROUBLESHOOTING

### Issue: Sarvam AI Translation Fails

```bash
Error: "Invalid API key"

Fix:
1. Check API key is correct
2. Verify header name is "api-subscription-key" (not "Authorization")
3. Test directly:
   curl -H "api-subscription-key: YOUR_KEY" \
     https://api.sarvam.ai/translate \
     -d '{"input": "test", "source_language_code": "en", "target_language_code": "hi"}'
```

### Issue: pgvector Not Working

```bash
Error: "operator does not exist: vector <=> vector"

Fix:
1. Enable extension: CREATE EXTENSION vector;
2. Verify: SELECT * FROM pg_extension WHERE extname = 'vector';
3. Restart Supabase project (dashboard → Settings → Restart)
```

### Issue: Consent Not Recording

```bash
Error: Consent ledger empty

Fix:
1. Check "Record Verbal Consent" node
2. Verify tone is being passed from Ultravox
3. Manual test:
   paralinguistic_features: {
     tone: "positive",
     confidence: 0.8
   }
```

---

## 💰 COST BREAKDOWN

### Monthly (1000 calls)

| Service | Free Tier | Paid |
|---------|-----------|------|
| n8n.cloud | 5K executions free | $20 (20K executions) |
| Supabase | 500MB free | $25 (8GB) |
| OpenAI GPT-4 | Pay-per-use | ~$10 (1000 calls × $0.01) |
| Sarvam AI | 1K requests free | $5 (5K requests) |
| Ultravox | 100 mins free | $10 (varies) |
| **Total** | **~$5-10** | **~$70** |

### Scaling (10,000 calls/month)

| Service | Cost |
|---------|------|
| n8n | $50 (200K executions) |
| Supabase | $25 (8GB) |
| OpenAI | ~$100 |
| Sarvam AI | ~$50 |
| Ultravox | ~$100 |
| **Total** | **~$325/month** |

**Compare**: AWS EC2 + RDS + S3 = ~$500/month + DevOps time

---

## 🎓 TRAINING MATERIALS

### For CHWs (Community Health Workers)

**Pictogram-Based Quick Guide:**
```
📱 1. Tap "Start Call" → Green button
🎤 2. Speak clearly → User tells their situation
✅ 3. Confirm → System reads back details
📄 4. Print forms → Automatic, just press "Print"
📮 5. Help submit → Take to government office
```

### For Administrators

```sql
-- Check today's activity
SELECT * FROM zelia_dashboard;

-- Find households needing follow-up
SELECT 
    household_id_hash,
    profile_json,
    created_at
FROM households
WHERE NOT EXISTS (
    SELECT 1 FROM submissions 
    WHERE submissions.household_id_hash = households.household_id_hash
);
```

---

## 🚀 NEXT STEPS

### Phase 1: Core Platform (Complete ✅)
- Voice capture
- Translation
- AI extraction
- Eligibility checking
- Privacy-preserving storage
- Consent management

### Phase 2: Enhanced Features (In Progress ⏳)
- PDF auto-fill and generation
- SMS notifications
- Offline CHW tablets
- Government API integration

### Phase 3: Scale (Planned 📅)
- 10+ state support
- 100+ schemes
- 10K+ daily users
- Real-time dashboards

### Phase 4: Advanced (Future 🔮)
- Biometric authentication
- Blockchain consent ledger
- ML fraud detection
- Predictive eligibility

---

## 📚 RESOURCES

### Documentation
- **ZELIA_MAGIC_PROMPT_V2.md** - Context for LLMs
- **zelia-complete-voice-first-v11.json** - n8n workflow
- **zelia-complete-schema.sql** - Database schema

### External Docs
- **Ultravox**: https://docs.ultravox.ai
- **Sarvam AI**: https://docs.sarvam.ai
- **n8n**: https://docs.n8n.io
- **Supabase**: https://supabase.com/docs

### Community
- **n8n Community**: https://community.n8n.io
- **Supabase Discord**: https://discord.supabase.com

---

## 📞 SUPPORT

For issues:
1. Check troubleshooting section above
2. Review n8n execution logs
3. Query Supabase tables for data issues
4. Test with simplified payloads

---

## ✅ PRODUCTION CHECKLIST

Before going live:

**Technical**
- [ ] All n8n nodes tested individually
- [ ] Database schema matches workflow
- [ ] API keys valid and funded
- [ ] Error handling tested (timeout, invalid input)
- [ ] Privacy hashing working (household_id_hash generated)
- [ ] Consent ledger recording properly

**Security**
- [ ] RLS policies enabled
- [ ] Webhook authenticated (optional: add API key check)
- [ ] API keys in environment variables (not hardcoded)
- [ ] Logs don't contain PII
- [ ] Backups enabled (Supabase auto-backs up)

**Compliance**
- [ ] Consent expiry configured (90 days)
- [ ] Privacy policy drafted
- [ ] Data retention policy set
- [ ] CHW training completed

**Operational**
- [ ] Monitoring dashboard created
- [ ] Error alerts configured (n8n → email/Slack)
- [ ] On-call rotation defined
- [ ] CHW helpline number published

---

**ZELIA is now ready to serve India's most vulnerable populations. Deploy with care, test thoroughly, and remember: every line of code protects someone's dignity.**

🙏

---

**Version**: 11.0 Complete Production  
**Status**: Ready for Deployment  
**Setup Time**: 15 minutes  
**Monthly Cost**: $20-70 (based on volume)  
**Impact**: Dignified access to government schemes for zero-literacy citizens
