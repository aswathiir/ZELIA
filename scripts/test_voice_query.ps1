# ZELIA - Simple Voice Query Test
# Tests the complete voice query pipeline

Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║        ZELIA Voice Query Test                           ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$n8nWebhook = "http://localhost:5678/webhook/voice-query"

# Test 1: Simple Tamil Query
Write-Host "[Test 1/3] Tamil widow pension query..." -ForegroundColor Yellow
try {
    $query = @{
        transcript = "விதவை ஓய்வூதியம் பற்றி சொல்லுங்கள்"
        language = "ta-IN"
        query_type = "scheme_search"
    } | ConvertTo-Json
    
    Write-Host "  Query: விதவை ஓய்வூதியம் பற்றி சொல்லுங்கள்" -ForegroundColor Gray
    Write-Host "  (Tell me about widow pension)`n" -ForegroundColor Gray
    
    $result = Invoke-RestMethod -Uri $n8nWebhook `
        -Method POST `
        -ContentType "application/json" `
        -Body $query `
        -TimeoutSec 30 `
        -ErrorAction Stop
    
    Write-Host "✅ Success!" -ForegroundColor Green
    Write-Host "  Schemes found: $($result.schemes.Count)" -ForegroundColor White
    
    if ($result.schemes -and $result.schemes.Count -gt 0) {
        Write-Host "`n  Top schemes:" -ForegroundColor Cyan
        $result.schemes | Select-Object -First 3 | ForEach-Object {
            Write-Host "   • $($_.title)" -ForegroundColor White
        }
    }
    
    if ($result.response) {
        Write-Host "`n  Response: $($result.response.Substring(0, [Math]::Min(100, $result.response.Length)))..." -ForegroundColor Gray
    }
    
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "⚠️  Make sure n8n workflow is imported and activated!" -ForegroundColor Yellow
}

Start-Sleep -Seconds 2

# Test 2: Hindi Query
Write-Host "`n[Test 2/3] Hindi pension query..." -ForegroundColor Yellow
try {
    $query = @{
        transcript = "विधवा पेंशन योजना के बारे में बताइए"
        language = "hi-IN"
        query_type = "scheme_search"
    } | ConvertTo-Json
    
    Write-Host "  Query: विधवा पेंशन योजना के बारे में बताइए" -ForegroundColor Gray
    Write-Host "  (Tell about widow pension scheme)`n" -ForegroundColor Gray
    
    $result = Invoke-RestMethod -Uri $n8nWebhook `
        -Method POST `
        -ContentType "application/json" `
        -Body $query `
        -TimeoutSec 30 `
        -ErrorAction Stop
    
    Write-Host "✅ Success!" -ForegroundColor Green
    Write-Host "  Schemes found: $($result.schemes.Count)" -ForegroundColor White
    
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

Start-Sleep -Seconds 2

# Test 3: Profile Creation
Write-Host "`n[Test 3/3] Profile creation from voice..." -ForegroundColor Yellow
try {
    $query = @{
        transcript = "My name is Kumar. I am 65 years old. I am widowed. My monthly income is 8000 rupees."
        language = "en-IN"
        query_type = "profile_creation"
        extracted_entities = @{
            head_name = "Kumar"
            age = 65
            marital_status = "widowed"
            monthly_income = 8000
        }
    } | ConvertTo-Json -Depth 4
    
    Write-Host "  Profile: Kumar, 65, Widowed, Income: 8000" -ForegroundColor Gray
    
    $result = Invoke-RestMethod -Uri $n8nWebhook `
        -Method POST `
        -ContentType "application/json" `
        -Body $query `
        -TimeoutSec 30 `
        -ErrorAction Stop
    
    Write-Host "✅ Success!" -ForegroundColor Green
    Write-Host "  Eligible schemes: $($result.schemes.Count)" -ForegroundColor White
    
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Summary
Write-Host "`n╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              Test Complete                              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

Write-Host "📖 Next Steps:" -ForegroundColor Cyan
Write-Host "   • If tests failed: Make sure n8n workflow is activated" -ForegroundColor White
Write-Host "   • Check workflow execution logs at: http://localhost:5678/executions" -ForegroundColor White
Write-Host "   • View service logs: docker-compose logs -f [service-name]`n" -ForegroundColor White
