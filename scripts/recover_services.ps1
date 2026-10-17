# Service Recovery Script - Restart failing services

Write-Host "Restarting failing services..." -ForegroundColor Yellow
Write-Host ""

docker-compose restart ocr-service
Write-Host "OCR restarted" -ForegroundColor Gray

docker-compose restart layout-worker  
Write-Host "LayoutLM restarted" -ForegroundColor Gray

docker-compose restart retrieval-service
Write-Host "RAG restarted" -ForegroundColor Gray

docker-compose restart embedding-service
Write-Host "Embedding restarted" -ForegroundColor Gray

docker-compose restart translation-service
Write-Host "Translation restarted" -ForegroundColor Gray

Write-Host ""
Write-Host "Waiting 20 seconds for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

Write-Host ""
Write-Host "Checking status..." -ForegroundColor Yellow
docker-compose ps

Write-Host ""
Write-Host "Now run: .\scripts\debug_workflow.ps1" -ForegroundColor Cyan
