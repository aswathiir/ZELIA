$ErrorActionPreference = "Stop"

Write-Host "Building ZELIA Stack..." -ForegroundColor Cyan
docker-compose build ocr-service

Write-Host "`nRunning Internal OCR Test..." -ForegroundColor Cyan
try {
    docker-compose run --rm ocr-service python test_ocr_internal.py
    Write-Host "`nTest Passed!" -ForegroundColor Green
}
catch {
    Write-Host "`nTest Failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`nStarting Full Stack..." -ForegroundColor Cyan
docker-compose up -d

Write-Host "`nStack is running." -ForegroundColor Green
docker-compose ps
