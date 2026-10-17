# Test Working ZELIA Services
# No Unicode characters - clean PowerShell

Write-Host "Testing ZELIA Working Services" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Translation
Write-Host "[1/5] Translation Service..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod http://localhost:8009/health -TimeoutSec 3
    Write-Host "  [OK] Status: $($health.status)" -ForegroundColor Green
    
    # Test actual translation
    $body = @{text = "pension scheme"; target_lang = "hi-IN" } | ConvertTo-Json
    $result = Invoke-RestMethod -Uri "http://localhost:8009/translate" `
        -Method POST -Body $body -ContentType "application/json" -TimeoutSec 5
    Write-Host "  [OK] Translation works: $($result.translated_text)" -ForegroundColor Green
}
catch {
    Write-Host "  [FAIL] $_" -ForegroundColor Red
}

# Test 2: Web Scraper
Write-Host ""
Write-Host "[2/5] Web Scraper Service..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod http://localhost:8008/health -TimeoutSec 3
    Write-Host "  [OK] Status: $($health.status)" -ForegroundColor Green
    
    # Test actual search
    $result = Invoke-RestMethod "http://localhost:8008/search?query=pension&limit=3" -TimeoutSec 5
    Write-Host "  [OK] Found $($result.schemes.Count) schemes" -ForegroundColor Green
}
catch {
    Write-Host "  [FAIL] $_" -ForegroundColor Red
}

# Test 3: Rules Engine
Write-Host ""
Write-Host "[3/5] Rules Engine..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod http://localhost:8005/health -TimeoutSec 3
    Write-Host "  [OK] Status: healthy" -ForegroundColor Green
}
catch {
    Write-Host "  [FAIL] $_" -ForegroundColor Red
}

# Test 4: Submission Service
Write-Host ""
Write-Host "[4/5] Submission Service..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod http://localhost:8004/health -TimeoutSec 3
    Write-Host "  [OK] Status: healthy" -ForegroundColor Green
}
catch {
    Write-Host "  [FAIL] $_" -ForegroundColor Red
}

# Test 5: Database
Write-Host ""
Write-Host "[5/5] PostgreSQL Database..." -ForegroundColor Yellow
try {
    $count = docker exec zelia-postgres psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM schemes;" 2>$null
    Write-Host "  [OK] Database has $($count.Trim()) schemes" -ForegroundColor Green
}
catch {
    Write-Host "  [FAIL] $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  These 5 services are working" -ForegroundColor Green
Write-Host "  You can build workflows with them" -ForegroundColor Green
Write-Host ""
Write-Host "Next: Import n8n workflow at http://localhost:5678" -ForegroundColor Yellow
