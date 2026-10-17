# 🚀 ZELIA - 5 Minute Quick Start Guide

**Goal**: Get ZELIA running and test voice integration in 5 minutes.

---

## Step 1: Start All Services (2 minutes)

```powershell
# Open PowerShell as Administrator
cd "C:\Users\lazya\OneDrive\Documents\sem 6\software eng\project"

# Run automated setup
.\setup-complete-system.ps1
```

**What this does**:
- Rebuilds fixed services (OCR, Retrieval, Ultravox)
- Starts all 12 services
- Runs health checks
- Executes integration tests

**Expected output**: ✅ 12/12 services healthy

---

## Step 2: Import n8n Workflow (1 minute)

1. Open browser: http://localhost:5678
2. Login: `admin` / `<N8N_BASIC_AUTH_PASSWORD from .env>`
3. Click **"Import from File"**
4. Select: `n8n-workflows/production/zelia_voice_complete.json`
5. Click **"Activate"** toggle (switch should turn green)

**Done!** Workflow is now live.

---

## Step 3: Test Voice Session (1 minute)

```powershell
# Create a voice session
$session = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8010/create-session" `
  -ContentType "application/json" `
  -Body '{"language":"ta-IN","context":{"user":"test"}}'

# Display results
Write-Host "Call ID: $($session.call_id)" -ForegroundColor Green
Write-Host "Join URL: $($session.join_url)" -ForegroundColor Cyan
Write-Host "Status: $($session.status)" -ForegroundColor Yellow
```

**Expected output**:
```
Call ID: call_abc123def456...
Join URL: wss://api.ultravox.ai/join/...
Status: created
```

---

## Step 4: Test Voice Query (1 minute)

```powershell
# Simulate a voice query in Tamil
$query = @{
  transcript = "விதவை ஓய்வூதியம் பற்றி சொல்லுங்கள்"  # "Tell me about widow pension"
  language = "ta-IN"
  user_id = "test_user"
  query_type = "search"
} | ConvertTo-Json

# Send query to workflow
$response = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:5678/webhook/voice-query" `
  -ContentType "application/json" `
  -Body $query

# Display results
Write-Host ""
Write-Host "Response in Tamil:" -ForegroundColor Cyan
Write-Host $response.response_text -ForegroundColor White
Write-Host ""
Write-Host "Schemes Found: $($response.results.Count)" -ForegroundColor Green
```

**Expected output**:
```
Response in Tamil:
உங்களுக்கு 3 தொடர்புடைய திட்டங்கள் கண்டுபிடிக்கப்பட்டன...

Schemes Found: 3
```

---

## ✅ Success Checklist

- [ ] All services started without errors
- [ ] n8n workflow activated
- [ ] Voice session created successfully
- [ ] Voice query returned results in Tamil
- [ ] Response includes scheme details

**If all checked**: 🎉 **System is working!**

---

## 🎯 What to Test Next

### Test 1: Multilingual Query (Hindi)
```powershell
$hindiQuery = @{
  transcript = "विधवा पेंशन के लिए क्या दस्तावेज़ चाहिए?"
  language = "hi-IN"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
  -Uri "http://localhost:5678/webhook/voice-query" `
  -Body $hindiQuery -ContentType "application/json"
```

### Test 2: Document Upload
```powershell
# Upload a test document for OCR
$boundary = [System.Guid]::NewGuid().ToString()
$file = Get-Content "sample_form.jpg" -Raw -Encoding Byte

# (Full multipart/form-data code in VOICE_INTEGRATION_COMPLETE.md)
```

### Test 3: Check Database
```powershell
# List all schemes in database
docker exec zelia-postgres psql -U postgres -d postgres -c "SELECT title FROM schemes;"
```

---

## 🔍 Verify Services

Quick health check URLs:

```
✅ n8n:          http://localhost:5678/healthz
✅ Translation:  http://localhost:8009/health
✅ Web Scraper:  http://localhost:8008/health
✅ Ultravox:     http://localhost:8010/health
✅ OCR:          http://localhost:8003/health
✅ Retrieval:    http://localhost:8007/health
```

---

## 🆘 Quick Troubleshooting

### Problem: Service unreachable
```powershell
# Check if container is running
docker ps | Select-String "zelia"

# Restart specific service
docker-compose restart <service-name>

# View logs
docker-compose logs --tail=50 <service-name>
```

### Problem: Voice session creation fails
```powershell
# Check Ultravox API key
grep ULTRAVOX_API_KEY .env

# Test Ultravox service directly
curl http://localhost:8010/health
```

### Problem: Workflow returns error
1. Open n8n: http://localhost:5678
2. Click workflow → **"Executions"** tab
3. Click failed execution → View error details
4. Check which node failed

---

## 📚 Full Documentation

For detailed guides, see:

- **Complete Integration**: `VOICE_INTEGRATION_COMPLETE.md`
- **Ultravox Reference**: `ULTRAVOX_AGENT_REFERENCE.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **System Design**: `ZELIA.pdf`

---

## 🎬 Next Steps

### For Developers
1. Explore n8n workflows: http://localhost:5678
2. Read API docs: http://localhost:8XXX/docs (each service)
3. Customize voice prompts in `ultravox_proxy.py`
4. Add new schemes to database

### For CHWs
1. Watch training video (to be created)
2. Practice voice queries in different languages
3. Test document upload flow
4. Review scheme eligibility criteria

### For Administrators
1. Set up monitoring (Prometheus + Grafana)
2. Configure backups (database + MinIO)
3. Enable HTTPS/TLS
4. Create disaster recovery plan

---

## 🎉 You're Ready!

ZELIA is now running with:
- ✅ Voice AI integration (Ultravox)
- ✅ Multilingual translation (6 languages)
- ✅ Scheme search (MyScheme + RAG)
- ✅ Document processing (OCR + LayoutLM)
- ✅ Workflow automation (n8n)

**Time to deploy**: Ready for pilot with 10 CHWs and 200 households!

---

**Questions?** See full docs or check `docker-compose logs -f`
