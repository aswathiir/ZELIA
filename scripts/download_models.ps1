# PowerShell script to download ZELIA models
$ErrorActionPreference = "Stop"

$DataDir = Join-Path (Get-Location) "data"
$TessDataDir = Join-Path $DataDir "tessdata"
$LayoutModelDir = Join-Path $DataDir "layoutlm-model"

# Create directories
New-Item -ItemType Directory -Force -Path $TessDataDir | Out-Null
New-Item -ItemType Directory -Force -Path $LayoutModelDir | Out-Null

Write-Host "Checking Tesseract Models..." -ForegroundColor Cyan

# Function to download if not exists
function Download-File {
    param ($Url, $Dest)
    if (-not (Test-Path $Dest)) {
        Write-Host "Downloading $Dest..."
        Invoke-WebRequest -Uri $Url -OutFile $Dest
    }
    else {
        Write-Host "Exists: $Dest" -ForegroundColor DarkGray
    }
}

# 1. Download Tesseract Data
$TessBaseUrl = "https://github.com/tesseract-ocr/tessdata_fast/raw/main"
Download-File "$TessBaseUrl/eng.traineddata" (Join-Path $TessDataDir "eng.traineddata")
Download-File "$TessBaseUrl/tam.traineddata" (Join-Path $TessDataDir "tam.traineddata")
# Create a local osd file if needed, or download
Download-File "$TessBaseUrl/osd.traineddata" (Join-Path $TessDataDir "osd.traineddata")

Write-Host "`nTesseract models ready in $TessDataDir" -ForegroundColor Green

# 2. LayoutLMv2 Placeholder
# Real LayoutLMv2 requires `transformers` to download. 
# We will create a small python script to fetch it so we use the proper huggingface cache structure or local save.
Write-Host "`nChecking LayoutLMv2..." -ForegroundColor Cyan

$DownloaderScript = @"
import os
from transformers import LayoutLMv2Processor, LayoutLMv2ForTokenClassification

save_dir = r'$LayoutModelDir'
model_name = 'microsoft/layoutlmv2-base-uncased'

if not os.path.exists(os.path.join(save_dir, 'config.json')):
    print(f'Downloading {model_name} to {save_dir}...')
    try:
        processor = LayoutLMv2Processor.from_pretrained(model_name)
        model = LayoutLMv2ForTokenClassification.from_pretrained(model_name)
        processor.save_pretrained(save_dir)
        model.save_pretrained(save_dir)
        print('Download complete.')
    except Exception as e:
        print(f'Error downloading model: {e}')
else:
    print('LayoutLMv2 model already exists locally.')
"@

$ScriptPath = Join-Path $DataDir "download_hf.py"
$DownloaderScript | Out-File -Encoding utf8 $ScriptPath

# We assume the user has a venv active or python installed
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "Running python download script..."
    
    # Unconditionally ensure dependencies are installed with KNOWN COMPATIBLE versions.
    # We pin torch==2.1.0 and transformers==4.35.0 to avoid breaking changes in newer torch versions (like _pytree).
    Write-Host "Installing compatible torch/transformers versions..." -ForegroundColor Yellow
    cmd /c "pip install torch==2.1.0 transformers==4.35.0 --no-cache-dir"
    
    python $ScriptPath
}
else {
    Write-Host "Python not found! Please run 'python $ScriptPath' manually after activating your venv." -ForegroundColor Red
}

Write-Host "`nSetup Complete." -ForegroundColor Green
