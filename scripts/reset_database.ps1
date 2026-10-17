# ZELIA - Complete Database Reset and Fix Script
# Run this AFTER restarting Docker Desktop
# NOTE: Uses ASCII-only characters for PowerShell compatibility

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ZELIA Database Reset & Full Fix      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "C:\Users\lazya\OneDrive\Documents\sem 6\software eng\project"
Set-Location $projectRoot

# Step 1: Check Docker
Write-Host "[1/6] Checking Docker..." -ForegroundColor Yellow
$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Docker is not running!" -ForegroundColor Red
    Write-Host "       Please start Docker Desktop first, then run this script again." -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Docker is running" -ForegroundColor Green

# Step 2: Stop all containers
Write-Host ""
Write-Host "[2/6] Stopping all containers (this may take a minute)..." -ForegroundColor Yellow
docker-compose down --remove-orphans 2>&1 | Out-Null
docker container prune -f 2>&1 | Out-Null
Write-Host "[OK] Containers stopped" -ForegroundColor Green

# Step 3: Remove old postgres data to allow fresh init
Write-Host ""
Write-Host "[3/6] Removing old PostgreSQL data..." -ForegroundColor Yellow

$confirm = $true
if (-not $Force) {
    $title = "Confirm Database Reset"
    $message = "WARNING: This will PERMANENTLY DELETE all your database storage (schemes, households, and submissions). Are you sure you want to continue?"
    $choices = [Management.Automation.Host.ChoiceDescription[]] @(
        New-Object Management.Automation.Host.ChoiceDescription "&Yes", "Delete all database volumes and start fresh."
        New-Object Management.Automation.Host.ChoiceDescription "&No", "Keep existing data and exit script."
    )
    $decision = $host.UI.PromptForChoice($title, $message, $choices, 1)
    if ($decision -ne 0) {
        Write-Host "Reset cancelled by user. Data preserved." -ForegroundColor Green
        exit 0
    }
}

docker volume rm project_postgres_data 2>&1 | Out-Null
Write-Host "[OK] Old data removed (will reinitialize with zelia user)" -ForegroundColor Green

# Step 4: Start PostgreSQL first
Write-Host ""
Write-Host "[4/6] Starting PostgreSQL with correct credentials..." -ForegroundColor Yellow
docker-compose up -d postgres
Start-Sleep -Seconds 15

# Check postgres is ready
$maxAttempts = 10
$attempt = 1
$pgReady = $false
while ($attempt -le $maxAttempts) {
    $result = docker exec zelia-postgres pg_isready -U zelia 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pgReady = $true
        break
    }
    Write-Host "   Waiting for PostgreSQL... ($attempt/$maxAttempts)" -ForegroundColor Gray
    Start-Sleep -Seconds 3
    $attempt++
}

if ($pgReady) {
    Write-Host "[OK] PostgreSQL ready with 'zelia' user" -ForegroundColor Green
}
else {
    Write-Host "[WARN] PostgreSQL may need more time to start" -ForegroundColor Yellow
}

# Step 5: Start all other services
Write-Host ""
Write-Host "[5/6] Starting all services..." -ForegroundColor Yellow
docker-compose up -d
Start-Sleep -Seconds 30
Write-Host "[OK] Services started" -ForegroundColor Green

# Step 6: Health check
Write-Host ""
Write-Host "[6/6] Quick health check..." -ForegroundColor Yellow

$healthChecks = @(
    @{Name = "PostgreSQL"; Check = { docker exec zelia-postgres pg_isready -U zelia 2>&1; $LASTEXITCODE -eq 0 } },
    @{Name = "n8n"; Url = "http://localhost:5678/healthz" },
    @{Name = "OCR"; Url = "http://localhost:8003/health" },
    @{Name = "Translation"; Url = "http://localhost:8009/health" },
    @{Name = "Ultravox"; Url = "http://localhost:8010/health" }
)

$healthy = 0
foreach ($svc in $healthChecks) {
    try {
        if ($svc.Url) {
            Invoke-RestMethod -Uri $svc.Url -TimeoutSec 5 -ErrorAction Stop | Out-Null
        }
        else {
            & $svc.Check | Out-Null
        }
        Write-Host "   [OK] $($svc.Name)" -ForegroundColor Green
        $healthy++
    }
    catch {
        Write-Host "   [FAIL] $($svc.Name)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  $healthy/$($healthChecks.Count) core services healthy" -ForegroundColor $(if ($healthy -ge 4) { "Green" } else { "Yellow" })
Write-Host "========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "PostgreSQL Credentials:" -ForegroundColor White
Write-Host "   User:     zelia" -ForegroundColor Gray
Write-Host "   Password: zelia_secure_2024" -ForegroundColor Gray
Write-Host "   Database: zelia" -ForegroundColor Gray

Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "   - Full health check: .\scripts\health_check.ps1" -ForegroundColor Gray
Write-Host "   - n8n: http://localhost:5678 (admin/<N8N_BASIC_AUTH_PASSWORD from .env>)" -ForegroundColor Gray
Write-Host ""
