# Generate Vector Index for RAG Search
# This script creates the Annoy index for semantic search

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   Creating Vector Index for Scheme Search" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[Step 1/3] Building retrieval service with new dependencies..." -ForegroundColor Yellow
Write-Host "  This will install sentence-transformers, annoy, and psycopg2" -ForegroundColor Gray
Write-Host ""

docker-compose up -d --build retrieval-service

Write-Host ""
Write-Host "[Step 2/3] Waiting for service to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "[Step 3/3] Generating embeddings and building index..." -ForegroundColor Yellow
Write-Host "  This will:" -ForegroundColor Gray
Write-Host "    - Load all schemes from database" -ForegroundColor Gray
Write-Host "    - Generate 384-dim sentence embeddings" -ForegroundColor Gray
Write-Host "    - Build Annoy index for fast search" -ForegroundColor Gray
Write-Host "    - Save to /app/data/scheme_vectors.ann" -ForegroundColor Gray
Write-Host ""

docker exec zelia-retrieval python create_index.py

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   Index Generation Complete!" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The retrieval service now supports 3 search modes:" -ForegroundColor Green
Write-Host "  1. /search          - Text-based search (PostgreSQL)" -ForegroundColor White
Write-Host "  2. /search/vector   - Semantic vector search (Annoy)" -ForegroundColor White
Write-Host "  3. /search/hybrid   - Combined (recommended)" -ForegroundColor White
Write-Host ""
Write-Host "Test it:" -ForegroundColor Yellow
Write-Host '  Invoke-RestMethod -Uri "http://localhost:8007/search/hybrid" `' -ForegroundColor Gray
Write-Host '    -Method POST -Body ''{"query":"widow pension","k":5}'' `' -ForegroundColor Gray
Write-Host '    -ContentType "application/json"' -ForegroundColor Gray
Write-Host ""
