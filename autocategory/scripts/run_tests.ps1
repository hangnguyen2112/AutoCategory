# Run all tests for AutoCategory (Windows)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Running AutoCategory Test Suite" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Change to API directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptDir\..\api"

Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt -q

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "1. Backend Unit Tests" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
pytest tests/ -v --ignore=tests/test_e2e.py --ignore=tests/test_performance.py --ignore=tests/test_security.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Unit tests passed" -ForegroundColor Green
} else {
    Write-Host "❌ Unit tests failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "2. End-to-End Tests" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
pytest tests/test_e2e.py -v

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ E2E tests passed" -ForegroundColor Green
} else {
    Write-Host "❌ E2E tests failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "3. Security Tests" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
pytest tests/test_security.py -v

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Security tests passed" -ForegroundColor Green
} else {
    Write-Host "❌ Security tests failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "4. Performance Tests" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "⚠️  Running performance tests (may take a few minutes)" -ForegroundColor Yellow
pytest tests/test_performance.py -v -m performance

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Performance tests passed" -ForegroundColor Green
} else {
    Write-Host "⚠️  Performance tests had issues (non-blocking)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "5. Test Coverage Report" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
pytest tests/ --cov=. --cov-report=term-missing --cov-report=html

Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host "✅ All tests completed!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""

$coveragePath = Join-Path (Get-Location) "htmlcov\index.html"
Write-Host "Coverage report: file:///$coveragePath" -ForegroundColor Cyan
