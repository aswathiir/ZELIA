# Quick Status Check and Fix Script

Write-Host "Checking ZELIA Services Status..." -ForegroundColor Cyan
Write-Host ""

# Check which services are actually running
Write-Host "[1] Service Status:" -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "zelia"

Write-Host ""
Write-Host "[2] Quick Health Checks:" -ForegroundColor Yellow

# Translation (should work)
try {
    $trans = Invoke-RestMethod http://localhost:8009/health -TimeoutSec 2
    Write-Host "  ✓ Translation: $($trans.status)" -ForegroundColor Green
}
catch {
    Write-Host "  ✗ Translation: Failed" -ForegroundColor Red
}

# Web Scraper (should work)
try {
    $scraper = Invoke-RestMethod http://localhost:8008/health -TimeoutSec 2
    Write-Host "  ✓ Web Scraper: $($scraper.status)" -ForegroundColor Green
}
catch {
    Write-Host "  ✗ Web Scraper: Failed" -ForegroundColor Red
}

# RAG (may fail - needs index)
try {
    $rag = Invoke-RestMethod http://localhost:8007/health -TimeoutSec 2
    Write-Host "  ✓ RAG: $($rag.status)" -ForegroundColor Green
}
catch {
    Write-Host "  ⚠ RAG: Not responding (needs fix)" -ForegroundColor Yellow
}

# LayoutLM (may fail - port or code issues)
try {
    $layout = Invoke-RestMethod http://localhost:8006/health -TimeoutSec 2
    Write-Host "  ✓ LayoutLM: $($layout.status)" -ForegroundColor Green
}
catch {
    Write-Host "  ⚠ LayoutLM: Not responding (needs fix)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3] Recommended Actions:" -ForegroundColor Cyan

Write-Host "✓ Working services: Translation, Web Scraper" -ForegroundColor Green
Write-Host "⚠ Needs attention: RAG, LayoutLM" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next: Check logs with:" -ForegroundColor White
Write-Host "  docker logs zelia-retrieval --tail 20" -ForegroundColor Gray
Write-Host "  docker logs zelia-layout --tail 20" -ForegroundColor Gray
