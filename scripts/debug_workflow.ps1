# Debug ZELIA Workflow - Detailed Error Reporting

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   ZELIA Workflow Debug Test" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check service health
Write-Host "[1] Checking Service Health..." -ForegroundColor Yellow
Write-Host ""

$services = @(
    @{name = "Translation"; url = "http://localhost:8009/health" },
    @{name = "OCR"; url = "http://localhost:8003/health" },
    @{name = "LayoutLM"; url = "http://localhost:8006/health" },
    @{name = "Web Scraper"; url = "http://localhost:8008/health" },
    @{name = "RAG"; url = "http://localhost:8007/health" },
    @{name = "Rules Engine"; url = "http://localhost:8005/health" },
    @{name = "Submission"; url = "http://localhost:8004/health" }
)

foreach ($service in $services) {
    try {
        $health = Invoke-RestMethod -Uri $service.url -Method GET -TimeoutSec 3 -ErrorAction Stop
        Write-Host "  [OK] $($service.name)" -ForegroundColor Green
    }
    catch {
        Write-Host "  [FAIL] $($service.name) - $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "[2] Testing Workflow with Detailed Error..." -ForegroundColor Yellow
Write-Host ""

$WEBHOOK = "http://localhost:5678/webhook/zelia-assist"

$testBody = @{
    query = "pension scheme"
} | ConvertTo-Json

Write-Host "Sending request to: $WEBHOOK" -ForegroundColor Gray
Write-Host "Body: $testBody" -ForegroundColor Gray
Write-Host ""

try {
    $response = Invoke-RestMethod -Uri $WEBHOOK `
        -Method POST `
        -Body $testBody `
        -ContentType "application/json" `
        -TimeoutSec 30 `
        -ErrorAction Stop
    
    Write-Host "[SUCCESS] Workflow responded!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Response:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 5
    
}
catch {
    Write-Host "[ERROR] Workflow request failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Yellow
    Write-Host "Status Description: $($_.Exception.Response.StatusDescription)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Error Details:" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Gray
    Write-Host ""
    
    # Try to get response body
    if ($_.Exception.Response) {
        try {
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $responseBody = $reader.ReadToEnd()
            Write-Host "Response Body:" -ForegroundColor Yellow
            Write-Host $responseBody -ForegroundColor Gray
        }
        catch {
            Write-Host "Could not read response body" -ForegroundColor Gray
        }
    }
    
    Write-Host ""
    Write-Host "Troubleshooting Steps:" -ForegroundColor Yellow
    Write-Host "1. Check n8n execution logs at: http://localhost:5678/executions" -ForegroundColor White
    Write-Host "2. Click on the failed execution to see which node failed" -ForegroundColor White
    Write-Host "3. Check if all services above are [OK]" -ForegroundColor White
    Write-Host "4. Verify webhook URL in workflow matches: /webhook/zelia-assist" -ForegroundColor White
}

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
