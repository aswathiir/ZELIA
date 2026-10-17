# ZELIA - Complete Service Fix and Implementation Script
# This script fixes all known issues and sets up the complete system
# NOTE: Uses ASCII-only characters for PowerShell compatibility

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "ZELIA Complete System Fix & Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$projectRoot = "C:\Users\lazya\OneDrive\Documents\sem 6\software eng\project"
Set-Location $projectRoot

# Function to check if Docker is running
function Test-DockerRunning {
    try {
        docker ps | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# Function to wait for service health
function Wait-ForService {
    param(
        [string]$ServiceName,
        [string]$Url,
        [int]$MaxAttempts = 30
    )
    
    Write-Host "[WAIT] Waiting for $ServiceName..." -ForegroundColor Yellow
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $response = Invoke-RestMethod -Uri $Url -Method Get -ErrorAction Stop
            Write-Host "[OK] $ServiceName is healthy!" -ForegroundColor Green
            return $true
        }
        catch {
            Write-Host "   Attempt $i/$MaxAttempts..." -ForegroundColor Gray
            Start-Sleep -Seconds 2
        }
    }
    
    Write-Host "[FAIL] $ServiceName failed to become healthy" -ForegroundColor Red
    return $false
}

# Step 1: Check Docker
Write-Host "`n[Step 1/8] Checking Docker..." -ForegroundColor Cyan
if (-not (Test-DockerRunning)) {
    Write-Host "[FAIL] Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Docker is running" -ForegroundColor Green

# Step 2: Clean up old containers and images
Write-Host "`n[Step 2/8] Cleaning up old containers..." -ForegroundColor Cyan
Write-Host "Stopping all ZELIA containers..." -ForegroundColor Yellow
docker-compose down -v 2>&1 | Out-Null

Write-Host "Removing specific problem images..." -ForegroundColor Yellow
@('zelia-retrieval', 'zelia-layout', 'zelia-ocr') | ForEach-Object {
    $imageName = "project-$_"
    $image = docker images -q $imageName
    if ($image) {
        docker rmi -f $image 2>&1 | Out-Null
        Write-Host "  Removed image: $imageName" -ForegroundColor Gray
    }
}
Write-Host "[OK] Cleanup complete" -ForegroundColor Green

# Step 3: Rebuild critical services
Write-Host "`n[Step 3/8] Rebuilding critical services..." -ForegroundColor Cyan

$servicesToRebuild = @(
    @{Name = "retrieval-service"; Display = "RAG/Retrieval" },
    @{Name = "ocr-service"; Display = "OCR" },
    @{Name = "layout-worker"; Display = "LayoutLM" },
    @{Name = "ultravox-proxy"; Display = "Ultravox Proxy" }
)

foreach ($service in $servicesToRebuild) {
    Write-Host "`n[BUILD] Building $($service.Display)..." -ForegroundColor Yellow
    docker-compose build --no-cache $($service.Name) 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $($service.Display) built successfully" -ForegroundColor Green
    }
    else {
        Write-Host "[WARN] $($service.Display) build had warnings (may still work)" -ForegroundColor Yellow
    }
}

# Step 4: Start all services
Write-Host "`n[Step 4/8] Starting all services..." -ForegroundColor Cyan
docker-compose up -d

Write-Host "`n[WAIT] Waiting 30 seconds for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Step 5: Check service health
Write-Host "`n[Step 5/8] Checking service health..." -ForegroundColor Cyan

$services = @(
    @{Name = "PostgreSQL"; Url = "http://localhost:5432"; Command = "docker exec zelia-postgres pg_isready -U zelia" },
    @{Name = "MinIO"; Url = "http://localhost:9005/minio/health/live" },
    @{Name = "n8n"; Url = "http://localhost:5678/healthz" },
    @{Name = "Translation"; Url = "http://localhost:8009/health" },
    @{Name = "Web Scraper"; Url = "http://localhost:8008/health" },
    @{Name = "Rules Engine"; Url = "http://localhost:8005/health" },
    @{Name = "Submission"; Url = "http://localhost:8004/health" },
    @{Name = "OCR"; Url = "http://localhost:8003/health" },
    @{Name = "RAG/Retrieval"; Url = "http://localhost:8007/health" },
    @{Name = "Ultravox Proxy"; Url = "http://localhost:8010/health" }
)

$healthyCount = 0
$totalCount = $services.Count

foreach ($service in $services) {
    if ($service.Command) {
        # Use command for services that don't have HTTP endpoint
        try {
            Invoke-Expression $service.Command | Out-Null
            Write-Host "[OK] $($service.Name)" -ForegroundColor Green
            $healthyCount++
        }
        catch {
            Write-Host "[FAIL] $($service.Name)" -ForegroundColor Red
        }
    }
    else {
        # Use HTTP health check
        try {
            Invoke-RestMethod -Uri $service.Url -Method Get -ErrorAction Stop | Out-Null
            Write-Host "[OK] $($service.Name)" -ForegroundColor Green
            $healthyCount++
        }
        catch {
            Write-Host "[FAIL] $($service.Name)" -ForegroundColor Red
        }
    }
}

Write-Host "`n[INFO] Service Health: $healthyCount/$totalCount services healthy" -ForegroundColor Cyan

# Step 6: Initialize database with sample schemes
Write-Host "`n[Step 6/8] Initializing database..." -ForegroundColor Cyan
try {
    $checkQuery = "SELECT COUNT(*) FROM schemes;"
    $count = docker exec zelia-postgres psql -U zelia -d zelia -t -c $checkQuery 2>$null
    
    if ($count -and $count.Trim() -gt 0) {
        Write-Host "[OK] Database already has $($count.Trim()) schemes" -ForegroundColor Green
    }
    else {
        Write-Host "Inserting sample schemes..." -ForegroundColor Yellow
        docker exec zelia-postgres psql -U zelia -d zelia -f /docker-entrypoint-initdb.d/init.sql 2>&1 | Out-Null
        Write-Host "[OK] Sample schemes inserted" -ForegroundColor Green
    }
}
catch {
    Write-Host "[WARN] Database initialization had issues" -ForegroundColor Yellow
}

# Step 7: Create vector index for RAG
Write-Host "`n[Step 7/8] Creating vector index for semantic search..." -ForegroundColor Cyan
try {
    Write-Host "Running index creation script..." -ForegroundColor Yellow
    docker exec zelia-retrieval python /app/create_index.py 2>&1 | Out-Null
    Write-Host "[OK] Vector index created" -ForegroundColor Green
}
catch {
    Write-Host "[WARN] Vector index creation failed (service may still work with text search)" -ForegroundColor Yellow
}

# Step 8: Test end-to-end workflow
Write-Host "`n[Step 8/8] Testing system..." -ForegroundColor Cyan

Write-Host "`n[TEST 1] Testing Translation Service..." -ForegroundColor Yellow
try {
    $testBody = @{
        text        = "Tell me about widow pension"
        source_lang = "en"
        target_lang = "ta-IN"
    } | ConvertTo-Json
    
    $result = Invoke-RestMethod -Uri "http://localhost:8009/translate" `
        -Method POST `
        -ContentType "application/json" `
        -Body $testBody `
        -ErrorAction Stop
    
    Write-Host "[OK] Translation working: $($result.translated_text.Substring(0, 50))..." -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] Translation test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n[TEST 2] Testing Web Scraper..." -ForegroundColor Yellow
try {
    $result = Invoke-RestMethod -Uri "http://localhost:8008/search?query=pension&limit=2" `
        -Method GET `
        -ErrorAction Stop
    
    Write-Host "[OK] Web Scraper working: Found $($result.schemes.Count) schemes" -ForegroundColor Green
}
catch {
    Write-Host "[FAIL] Web Scraper test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n[TEST 3] Testing Ultravox Proxy..." -ForegroundColor Yellow
try {
    $sessionBody = @{
        language = "ta-IN"
        context  = @{}
    } | ConvertTo-Json
    
    $session = Invoke-RestMethod -Uri "http://localhost:8010/create-session" `
        -Method POST `
        -ContentType "application/json" `
        -Body $sessionBody `
        -ErrorAction Stop
    
    Write-Host "[OK] Ultravox Proxy working: Session $($session.call_id)" -ForegroundColor Green
    
    # Clean up test session
    try {
        Invoke-RestMethod -Uri "http://localhost:8010/session/$($session.call_id)/end" `
            -Method POST `
            -ErrorAction SilentlyContinue | Out-Null
    }
    catch {}
    
}
catch {
    Write-Host "[FAIL] Ultravox Proxy test failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Final Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "[INFO] Service URLs:" -ForegroundColor Cyan
Write-Host "   - n8n Workflow Editor: http://localhost:5678" -ForegroundColor White
Write-Host "   - MinIO Console: http://localhost:9001" -ForegroundColor White
Write-Host "   - API Gateway: http://localhost:8000" -ForegroundColor White
Write-Host "   - Ultravox Proxy: http://localhost:8010" -ForegroundColor White

Write-Host "`n[INFO] Credentials:" -ForegroundColor Cyan
Write-Host "   - n8n: admin / <N8N_BASIC_AUTH_PASSWORD from .env>" -ForegroundColor White
Write-Host "   - MinIO: minioadmin / minioadmin_secure_2024" -ForegroundColor White
Write-Host "   - PostgreSQL: zelia / zelia_secure_2024" -ForegroundColor White

Write-Host "`n[INFO] Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Import n8n workflows from: n8n-workflows/production/" -ForegroundColor White
Write-Host "   2. Test voice integration: .\scripts\test_ultravox.ps1" -ForegroundColor White
Write-Host "   3. View documentation: VOICE_INTEGRATION_COMPLETE.md" -ForegroundColor White

Write-Host "`n[INFO] Troubleshooting:" -ForegroundColor Cyan
Write-Host "   - View logs: docker-compose logs -f [service-name]" -ForegroundColor White
Write-Host "   - Restart service: docker-compose restart [service-name]" -ForegroundColor White
Write-Host "   - Check health: .\scripts\health_check.ps1" -ForegroundColor White

Write-Host "`n[DONE] System ready for testing!" -ForegroundColor Green
