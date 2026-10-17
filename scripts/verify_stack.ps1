$ErrorActionPreference = "Stop"

Write-Host "=== ZELIA Stack Verification ===" -ForegroundColor Cyan

function Test-ServiceHealth {
    param ($Name, $Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -ErrorAction Stop -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "OK $Name is UP ($Url)" -ForegroundColor Green
            return $true
        }
        else {
            Write-Host "FAIL $Name returned $($response.StatusCode)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "FAIL $Name is DOWN ($Url) - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

Write-Host ""
Write-Host "Checking HTTP Health Endpoints..." -ForegroundColor Yellow

# Core ML Services
Write-Host ""
Write-Host "--- Core ML Services ---" -ForegroundColor Magenta
Test-ServiceHealth "Embedding Service" "http://localhost:8001/health"
Test-ServiceHealth "OCR Service" "http://localhost:8002/health"
Test-ServiceHealth "Layout Service" "http://localhost:8003/health"

# Backend Services
Write-Host ""
Write-Host "--- Backend Services ---" -ForegroundColor Magenta
Test-ServiceHealth "API Gateway" "http://localhost:8000/health"
Test-ServiceHealth "Submission Service" "http://localhost:8004/health"

# Infrastructure
Write-Host ""
Write-Host "--- Infrastructure ---" -ForegroundColor Magenta
Test-ServiceHealth "n8n" "http://localhost:5678"
Test-ServiceHealth "MinIO Console" "http://localhost:9001/login"
Test-ServiceHealth "MinIO API" "http://localhost:9005/minio/health/live"

# Postgres check via docker
Write-Host ""
Write-Host "--- Database ---" -ForegroundColor Magenta
try {
    docker compose exec -T postgres pg_isready -U zelia 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK PostgreSQL is Ready" -ForegroundColor Green
    }
    else {
        Write-Host "FAIL PostgreSQL check failed" -ForegroundColor Red
    }
}
catch {
    Write-Host "FAIL PostgreSQL container not running" -ForegroundColor Red
}

Write-Host ""
Write-Host "Verification Complete." -ForegroundColor Cyan
