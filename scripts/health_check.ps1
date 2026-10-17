# ZELIA - Quick Health Check Script
# Checks all services and displays status dashboard
# NOTE: Uses ASCII-only characters for PowerShell compatibility

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  ZELIA System Health Check Dashboard  " -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$services = @(
    @{Name = "PostgreSQL"; Port = "5432"; Type = "DB"; Command = "docker exec zelia-postgres pg_isready -U zelia" },
    @{Name = "MinIO"; Port = "9005"; Type = "Storage"; Url = "http://localhost:9005/minio/health/live" },
    @{Name = "n8n"; Port = "5678"; Type = "Orchestration"; Url = "http://localhost:5678/healthz" },
    @{Name = "API Gateway"; Port = "8000"; Type = "Core"; Url = "http://localhost:8000/health" },
    @{Name = "Embedding"; Port = "8001"; Type = "AI"; Url = "http://localhost:8001/health" },
    @{Name = "OCR"; Port = "8003"; Type = "AI"; Url = "http://localhost:8003/health" },
    @{Name = "Submission"; Port = "8004"; Type = "Core"; Url = "http://localhost:8004/health" },
    @{Name = "Rules Engine"; Port = "8005"; Type = "Core"; Url = "http://localhost:8005/health" },
    @{Name = "LayoutLM"; Port = "8006"; Type = "AI"; Url = "http://localhost:8006/health" },
    @{Name = "RAG/Retrieval"; Port = "8007"; Type = "AI"; Url = "http://localhost:8007/health" },
    @{Name = "Web Scraper"; Port = "8008"; Type = "Data"; Url = "http://localhost:8008/health" },
    @{Name = "Translation"; Port = "8009"; Type = "AI"; Url = "http://localhost:8009/health" },
    @{Name = "Ultravox Proxy"; Port = "8010"; Type = "Voice"; Url = "http://localhost:8010/health" }
)

$healthy = 0
$unhealthy = 0
$unknown = 0

Write-Host "Service Status:" -ForegroundColor White
Write-Host "-------------------------------------------------" -ForegroundColor Gray

foreach ($service in $services) {
    $status = "[?] Unknown"
    $color = "Yellow"
    $details = ""
    
    try {
        if ($service.Command) {
            # Use command for services without HTTP endpoint
            $result = Invoke-Expression $service.Command 2>&1
            if ($LASTEXITCODE -eq 0) {
                $status = "[OK] Healthy"
                $color = "Green"
                $healthy++
            }
            else {
                $status = "[FAIL] Unhealthy"
                $color = "Red"
                $unhealthy++
            }
        }
        else {
            # Use HTTP health check
            $response = Invoke-RestMethod -Uri $service.Url -Method Get -TimeoutSec 3 -ErrorAction Stop
            $status = "[OK] Healthy"
            $color = "Green"
            $healthy++
            
            # Get additional details if available
            if ($response.status) {
                $details = " ($($response.status))"
            }
            elseif ($response.version) {
                $details = " (v$($response.version))"
            }
        }
    }
    catch {
        $status = "[FAIL] Unhealthy"
        $color = "Red"
        $unhealthy++
        $details = " ($($_.Exception.Message.Substring(0, [Math]::Min(30, $_.Exception.Message.Length)))...)"
    }
    
    $serviceName = $service.Name.PadRight(18)
    $port = "Port $($service.Port)".PadRight(10)
    $type = "[$($service.Type)]".PadRight(15)
    
    Write-Host "$status $serviceName $port $type$details" -ForegroundColor $color
}

Write-Host "-------------------------------------------------" -ForegroundColor Gray

# Summary
$total = $services.Count
$healthPercent = [math]::Round(($healthy / $total) * 100, 1)

Write-Host "`nOverall Health: " -NoNewline -ForegroundColor White
if ($healthPercent -ge 90) {
    Write-Host "EXCELLENT" -ForegroundColor Green
}
elseif ($healthPercent -ge 70) {
    Write-Host "GOOD" -ForegroundColor Yellow
}
else {
    Write-Host "NEEDS ATTENTION" -ForegroundColor Red
}

Write-Host "  Healthy:   $healthy/$total ($healthPercent%)" -ForegroundColor Green
Write-Host "  Unhealthy: $unhealthy/$total" -ForegroundColor Red

# Quick Tests
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "       Quick Functional Tests          " -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test 1: Database
Write-Host "[Test 1/4] Database..." -NoNewline
try {
    $schemeCount = docker exec zelia-postgres psql -U zelia -d zelia -t -c "SELECT COUNT(*) FROM schemes;" 2>$null
    if ($schemeCount -and $schemeCount.Trim() -gt 0) {
        Write-Host " [OK] ($($schemeCount.Trim()) schemes)" -ForegroundColor Green
    }
    else {
        Write-Host " [WARN] No schemes found" -ForegroundColor Yellow
    }
}
catch {
    Write-Host " [FAIL] Failed" -ForegroundColor Red
}

# Test 2: Translation
Write-Host "[Test 2/4] Translation..." -NoNewline
try {
    $testBody = @{text = "hello"; source_lang = "en"; target_lang = "ta-IN" } | ConvertTo-Json
    $result = Invoke-RestMethod -Uri "http://localhost:8009/translate" `
        -Method POST -ContentType "application/json" -Body $testBody `
        -TimeoutSec 5 -ErrorAction Stop
    Write-Host " [OK]" -ForegroundColor Green
}
catch {
    Write-Host " [FAIL]" -ForegroundColor Red
}

# Test 3: Web Scraper
Write-Host "[Test 3/4] Scheme Search..." -NoNewline
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8008/search?query=pension&limit=1" `
        -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host " [OK] ($($result.schemes.Count) found)" -ForegroundColor Green
}
catch {
    Write-Host " [FAIL]" -ForegroundColor Red
}

# Test 4: Ultravox
Write-Host "[Test 4/4] Ultravox Proxy..." -NoNewline
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8010/agent/info" `
        -Method GET -TimeoutSec 5 -ErrorAction Stop
    Write-Host " [OK] (Agent: $($result.agent_id.Substring(0,8))...)" -ForegroundColor Green
}
catch {
    Write-Host " [FAIL]" -ForegroundColor Red
}

# URLs
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "           Access URLs                 " -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Web Interfaces:" -ForegroundColor White
Write-Host "   - n8n Workflows:    http://localhost:5678" -ForegroundColor Gray
Write-Host "   - MinIO Console:    http://localhost:9001" -ForegroundColor Gray
Write-Host "   - API Gateway:      http://localhost:8000" -ForegroundColor Gray
Write-Host "`nAPI Documentation:" -ForegroundColor White
Write-Host "   - Ultravox API:     http://localhost:8010/docs" -ForegroundColor Gray
Write-Host "   - Translation API:  http://localhost:8009/docs" -ForegroundColor Gray
Write-Host "   - Web Scraper API:  http://localhost:8008/docs" -ForegroundColor Gray

Write-Host "`nCredentials:" -ForegroundColor White
Write-Host "   - n8n:       admin / <N8N_BASIC_AUTH_PASSWORD from .env>" -ForegroundColor Gray
Write-Host "   - MinIO:     minioadmin / minioadmin_secure_2024" -ForegroundColor Gray
Write-Host "   - PostgreSQL: zelia / zelia_secure_2024" -ForegroundColor Gray

Write-Host "`nQuick Actions:" -ForegroundColor White
Write-Host "   - Restart all:      docker-compose restart" -ForegroundColor Gray
Write-Host "   - View logs:        docker-compose logs -f [service]" -ForegroundColor Gray
Write-Host "   - Run tests:        .\scripts\test_ultravox.ps1" -ForegroundColor Gray
Write-Host "   - Rebuild:          .\scripts\fix_all_services.ps1" -ForegroundColor Gray

Write-Host ""
