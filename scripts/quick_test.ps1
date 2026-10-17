# Quick Test - Check if workflow is imported and test basic functionality

Write-Host "Testing ZELIA Workflow..." -ForegroundColor Cyan
Write-Host ""

$WEBHOOK = "http://localhost:5678/webhook/zelia-assist"

# Test 1: Simple text query
Write-Host "Test: Basic Text Query" -ForegroundColor Yellow
$body = @{
    query = "widow pension scheme"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $WEBHOOK `
        -Method POST `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 30
    
    Write-Host "[SUCCESS] Workflow responded!" -ForegroundColor Green
    Write-Host "Language detected: $($response.detected_language)" -ForegroundColor Gray
    Write-Host "Schemes found: $($response.total_schemes)" -ForegroundColor Gray
    
    if ($response.schemes_found -and $response.schemes_found.Count -gt 0) {
        Write-Host "Top scheme: $($response.schemes_found[0].title)" -ForegroundColor Gray
    }
    
}
catch {
    Write-Host "[ERROR] Workflow test failed" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "1. Is the workflow imported in n8n?" -ForegroundColor Gray
    Write-Host "2. Is the workflow ACTIVATED (toggle on)?" -ForegroundColor Gray
    Write-Host "3. Are all services running?" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Check n8n at: http://localhost:5678" -ForegroundColor Cyan
}

Write-Host ""
