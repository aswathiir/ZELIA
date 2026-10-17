Write-Host "ZELIA System Verification" -ForegroundColor Cyan
Write-Host "=" * 80
Write-Host ""

Write-Host "Docker Services:" -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "zelia"
Write-Host ""

Write-Host "Health Checks:" -ForegroundColor Yellow
Write-Host "API Gateway (8000):" -NoNewline
$r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
if ($r) { Write-Host " OK" -ForegroundColor Green } else { Write-Host " FAIL" -ForegroundColor Red }

Write-Host "Embedding (8001):" -NoNewline
$r = Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
if ($r) { Write-Host " OK" -ForegroundColor Green } else { Write-Host " FAIL" -ForegroundColor Red }

Write-Host "OCR (8002):" -NoNewline
$r = Invoke-WebRequest -Uri "http://localhost:8002/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
if ($r) { Write-Host " OK" -ForegroundColor Green } else { Write-Host " FAIL" -ForegroundColor Red }

Write-Host "Layout (8003):" -NoNewline
$r = Invoke-WebRequest -Uri "http://localhost:8003/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
if ($r) { Write-Host " OK" -ForegroundColor Green } else { Write-Host " FAIL" -ForegroundColor Red }

Write-Host "Submission (8004):" -NoNewline
$r = Invoke-WebRequest -Uri "http://localhost:8004/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
if ($r) { Write-Host " OK" -ForegroundColor Green } else { Write-Host " FAIL" -ForegroundColor Red }

Write-Host "Rules Engine (8005):" -NoNewline
$r = Invoke-WebRequest -Uri "http://localhost:8005/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
if ($r) { Write-Host " OK" -ForegroundColor Green } else { Write-Host " FAIL" -ForegroundColor Red }

Write-Host "PDF Service (8006):" -NoNewline
$r = Invoke-WebRequest -Uri "http://localhost:8006/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction SilentlyContinue
if ($r) { Write-Host " OK" -ForegroundColor Green } else { Write-Host " FAIL" -ForegroundColor Red }

Write-Host "Retrieval (8007):" -NoNewline
$r = Invoke-RestMethod -Uri "http://localhost:8007/health" -TimeoutSec 3 -ErrorAction SilentlyContinue
if ($r) { Write-Host " OK (Index: $($r.index_size) docs)" -ForegroundColor Green } else { Write-Host " FAIL" -ForegroundColor Red }

Write-Host ""
Write-Host "Embedding /embed endpoint:" -NoNewline
$body = '{"text":"test"}'
$r = Invoke-RestMethod -Uri "http://localhost:8001/embed" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5 -ErrorAction SilentlyContinue
if ($r -and $r.embedding) { Write-Host " OK (dim: $($r.dimension))" -ForegroundColor Green } else { Write-Host " FAIL" -ForegroundColor Red }

Write-Host ""
Write-Host "=" * 80
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. python scripts/ingest_real_data.py"
Write-Host "2. python scripts/test_retrieval.py"
Write-Host "3. Open http://localhost:5678 for n8n"
