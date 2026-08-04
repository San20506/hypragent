# HyprAgent Windows dependency installer
# Run in PowerShell: .\install-deps.ps1

Write-Host "HyprAgent Windows Setup" -ForegroundColor Cyan
Write-Host "=" * 50

# Check if winget is available
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: winget not found. Install from Microsoft Store (App Installer)." -ForegroundColor Red
    exit 1
}

# Install Tesseract OCR
Write-Host "`nInstalling Tesseract OCR..." -ForegroundColor Yellow
winget install UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Tesseract installed." -ForegroundColor Green
} else {
    Write-Host "  Tesseract installation failed or already installed." -ForegroundColor Yellow
}

# Install Python dependencies
Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
uv pip install pytesseract Pillow
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Python packages installed." -ForegroundColor Green
}

# Optional: Playwright browsers
$installPlaywright = Read-Host "`nInstall Playwright browsers? (y/n)"
if ($installPlaywright -eq "y") {
    uv run playwright install chromium
    Write-Host "  Playwright Chromium installed." -ForegroundColor Green
}

# Verify
Write-Host "`nVerifying installation..." -ForegroundColor Yellow

$tess = Get-Command tesseract -ErrorAction SilentlyContinue
if ($tess) {
    Write-Host "  Tesseract: $($tess.Source)" -ForegroundColor Green
} else {
    Write-Host "  Tesseract: NOT FOUND (add to PATH or reinstall)" -ForegroundColor Red
}

try {
    python -c "from PIL import ImageGrab; print('  Pillow/ImageGrab: OK')" 2>$null
    Write-Host "  Pillow/ImageGrab: OK" -ForegroundColor Green
} catch {
    Write-Host "  Pillow/ImageGrab: MISSING" -ForegroundColor Red
}

try {
    python -c "import pytesseract; print('  pytesseract: OK')" 2>$null
    Write-Host "  pytesseract: OK" -ForegroundColor Green
} catch {
    Write-Host "  pytesseract: MISSING" -ForegroundColor Red
}

Write-Host "`nSetup complete. Run 'uv run hypragent --doctor' to verify." -ForegroundColor Cyan
