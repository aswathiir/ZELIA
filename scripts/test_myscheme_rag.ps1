# ZELIA RAG Search Test - Enhanced with MyScheme Dataset
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "ZELIA RAG SEARCH TEST - MyScheme Dataset Integration" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Web Scraper Stats
Write-Host "[1] Web Scraper Statistics" -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod -Uri "http://localhost:8008/stats" -ErrorAction Stop
    Write-Host "  Total Schemes: $($stats.total_schemes)" -ForegroundColor Green
    Write-Host "  Categories: $($stats.categories -join ', ')" -ForegroundColor Green
    Write-Host "  Data Source: $($stats.data_source)" -ForegroundColor Green
}
catch {
    Write-Host "  Failed to get stats" -ForegroundColor Red
}
Write-Host ""

# Test 2: Scheme Search - Pension
Write-Host "[2] Search Test: Pension Schemes" -ForegroundColor Yellow
$body = '{"query":"widow pension eligibility","max_results":3}'
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8008/scrape/schemes" -Method POST -Body $body -ContentType "application/json" -ErrorAction Stop
    Write-Host "  Found: $($result.Count) schemes" -ForegroundColor Green
    foreach ($scheme in $result) {
        Write-Host "    - $($scheme.title)" -ForegroundColor Cyan
        Write-Host "      Score: $($scheme.relevance_score)" -ForegroundColor Gray
    }
}
catch {
    Write-Host "  Search failed" -ForegroundColor Red
}
Write-Host ""

# Test 3: Scheme Search - Housing
Write-Host "[3] Search Test: Housing Schemes" -ForegroundColor Yellow
$body = '{"query":"housing subsidy pmay","max_results":2}'
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8008/scrape/schemes" -Method POST -Body $body -ContentType "application/json" -ErrorAction Stop
    Write-Host "  Found: $($result.Count) schemes" -ForegroundColor Green
    foreach ($scheme in $result) {
        Write-Host "    - $($scheme.title)" -ForegroundColor Cyan
    }
}
catch {
    Write-Host "  Search failed" -ForegroundColor Red
}
Write-Host ""

# Test 4: Hybrid Search
Write-Host "[4] Hybrid Search Test" -ForegroundColor Yellow
$body = '{"query":"farmer agriculture scheme","k":5}'
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8007/search/hybrid" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "  Vector results: $($result.stats.vector_results)" -ForegroundColor Green
    Write-Host "  Web results: $($result.stats.web_results)" -ForegroundColor Green
    Write-Host "  Total: $($result.stats.total)" -ForegroundColor Green
}
catch {
    Write-Host "  Hybrid search not available" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "TEST COMPLETE!" -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Cyan
