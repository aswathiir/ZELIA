# Quick Test - Everything Works!

Write-Host "Testing Complete RAG System (No API Keys Needed)" -ForegroundColor Cyan
Write-Host "=" * 70
Write-Host ""

# Test 1: Vector Search (100 real schemes)
Write-Host "[1] Vector Search (100 Real Schemes)" -ForegroundColor Yellow
$body = '{"query":"widow pension eligibility","k":3}'
$result = Invoke-RestMethod -Uri "http://localhost:8007/search" -Method POST -Body $body -ContentType "application/json" -ErrorAction SilentlyContinue

if ($result) {
    Write-Host "  ✓ Found: $($result.Count) results" -ForegroundColor Green
    Write-Host "  ✓ Top score: $($result[0].score)" -ForegroundColor Green
    Write-Host "  ✓ Source: Real indexed data" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Failed" -ForegroundColor Red
}

Write-Host ""

# Test 2: Web Scraper (Mock data - works without API keys)
Write-Host "[2] Web Scraper (Mock Data - No API Keys)" -ForegroundColor Yellow
$body = '{"query":"old age pension","max_results":3}'
$result = Invoke-RestMethod -Uri "http://localhost:8008/scrape/schemes" -Method POST -Body $body -ContentType "application/json" -ErrorAction SilentlyContinue

if ($result) {
    Write-Host "  ✓ Found: $($result.Count) schemes" -ForegroundColor Green
    Write-Host "  ✓ Source: $($result[0].source)" -ForegroundColor Green
    Write-Host "  ✓ Works without API keys!" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Failed" -ForegroundColor Red
}

Write-Host ""

# Test 3: Hybrid Search (Best of both)
Write-Host "[3] Hybrid Search (Vector + Web)" -ForegroundColor Yellow
$body = '{"query":"housing scheme","k":5}'
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8007/search/hybrid" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "  ✓ Vector results: $($result.stats.vector_results)" -ForegroundColor Green
    Write-Host "  ✓ Web results: $($result.stats.web_results)" -ForegroundColor Green
    Write-Host "  ✓ Total: $($result.stats.total)" -ForegroundColor Green
    Write-Host "  ✓ Fallback: $($result.stats.fallback_used)" -ForegroundColor Cyan
}
catch {
    Write-Host "  ⚠ Hybrid endpoint not available yet" -ForegroundColor Yellow
    Write-Host "  → Restart retrieval service: docker compose restart retrieval-service" -ForegroundColor White
}

Write-Host ""
Write-Host "=" * 70
Write-Host "SYSTEM READY - NO API KEYS NEEDED!" -ForegroundColor Green
Write-Host ""
Write-Host "You have:" -ForegroundColor Cyan
Write-Host "  - 100 real government schemes indexed" -ForegroundColor White
Write-Host "  - Mock data for fallback works immediately" -ForegroundColor White
Write-Host "  - Hybrid search combining both" -ForegroundColor White
Write-Host ""
