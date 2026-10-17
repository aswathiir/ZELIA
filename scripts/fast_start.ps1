# ZELIA - FAST Start Without Rebuilding
# Use this when services are already built but not running
# NOTE: Uses ASCII-only characters for PowerShell compatibility

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ZELIA Fast Start (No Rebuild)        " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "C:\Users\lazya\OneDrive\Documents\sem 6\software eng\project"
Set-Location $projectRoot

# Step 1: Check Docker
Write-Host "[1/3] Checking Docker..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Docker is running" -ForegroundColor Green

# Step 2: Start services (no rebuild)
Write-Host ""
Write-Host "[2/3] Starting all services..." -ForegroundColor Yellow
Write-Host "      (Using existing images - no download)" -ForegroundColor Gray
docker-compose up -d

Write-Host ""
Write-Host "[WAIT] Waiting 20 seconds for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

# Step 3: Quick health check
Write-Host ""
Write-Host "[3/3] Checking service health..." -ForegroundColor Yellow

$services = @(
    @{Name = "n8n"; Url = "http://localhost:5678/healthz" },
    @{Name = "Translation"; Url = "http://localhost:8009/health" },
    @{Name = "Web Scraper"; Url = "http://localhost:8008/health" },
    @{Name = "RAG/Retrieval"; Url = "http://localhost:8007/health" },
    @{Name = "Ultravox Proxy"; Url = "http://localhost:8010/health" }
)

$healthy = 0
foreach ($service in $services) {
    try {
        Invoke-RestMethod -Uri $service.Url -Method Get -TimeoutSec 3 -ErrorAction Stop | Out-Null
        Write-Host "   [OK] $($service.Name)" -ForegroundColor Green
        $healthy++
    }
    catch {
        Write-Host "   [FAIL] $($service.Name)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  $healthy/$($services.Count) core services healthy" -ForegroundColor $(if ($healthy -eq $services.Count) { "Green" } else { "Yellow" })
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "   - n8n: http://localhost:5678" -ForegroundColor Gray
Write-Host "   - Health check: .\scripts\health_check.ps1" -ForegroundColor Gray
Write-Host ""
