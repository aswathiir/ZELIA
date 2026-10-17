# ZELIA - Docker Cache Clean & Fix
# Run this to fix the "failed to extract layer" error
# NOTE: Uses ASCII-only characters for PowerShell compatibility

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  ZELIA Docker Cache Fix" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = "C:\Users\lazya\OneDrive\Documents\sem 6\software eng\project"
Set-Location $projectRoot

# Step 1: Prune Build Cache (Fixes the "no such file" error)
Write-Host "[1/3] Cleaning Docker Build Cache..." -ForegroundColor Yellow
Write-Host "      This fixes the corrupted layer..." -ForegroundColor Gray
docker builder prune -f
Write-Host "[OK] Cache cleaned." -ForegroundColor Green

# Step 2: Remove partial containers
Write-Host ""
Write-Host "[2/3] Removing old containers..." -ForegroundColor Yellow
docker rm -f zelia-retrieval 2>$null
Write-Host "[OK] Cleanup complete." -ForegroundColor Green

# Step 3: Run the fix script
Write-Host ""
Write-Host "[3/3] Restarting Build Process..." -ForegroundColor Yellow
.\scripts\fix_rag_search.ps1
