# ZELIA RAG Search with Web Fallback - Quick Test

Write-Host "Testing RAG Search with Web Fallback..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Regular search
Write-Host "[1] Vector Search Test" -ForegroundColor Yellow
$body = '{"query":"widow pension eligibility","k":3}'
$result = Invoke-RestMethod -Uri "http://localhost:8007/search" -Method POST -Body $body -ContentType "application/json" -ErrorAction SilentlyContinue

if ($result) {
    Write-Host "  Found: $($result.Count) results" -ForegroundColor Green
    if ($result.Count -gt 0) {
        Write-Host "  Top score: $($result[0].score)" -ForegroundColor Cyan
    }
}
else {
    Write-Host "  Failed" -ForegroundColor Red
}

Write-Host ""

# Test 2: Hybrid search (if web scraper is running)
Write-Host "[2] Hybrid Search Test (Vector + Web)" -ForegroundColor Yellow
$body = '{"query":"pradhan mantri awas yojana","k":5}'
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8007/search/hybrid" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "  Vector results: $($result.stats.vector_results)" -ForegroundColor Cyan
    Write-Host "  Web results: $($result.stats.web_results)" -ForegroundColor Cyan
    Write-Host "  Fallback used: $($result.stats.fallback_used)" -ForegroundColor Cyan
    Write-Host "  Total: $($result.stats.total)" -ForegroundColor Green
}
catch {
    Write-Host "  Hybrid search not available (web scraper may not be running)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Test complete!" -ForegroundColor Green
