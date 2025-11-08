# Start SLMS Server
# This script starts the FastAPI server with the correct configuration

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "  SLMS - Smart Library Management System" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (Test-Path ".env") {
    Write-Host "✓ Found .env file" -ForegroundColor Green
} else {
    Write-Host "⚠ Warning: .env file not found" -ForegroundColor Yellow
    Write-Host "  Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "  Please edit .env and set your DATABASE_URL" -ForegroundColor Yellow
    Write-Host ""
}

# Check if virtual environment is activated
if ($env:VIRTUAL_ENV) {
    Write-Host "✓ Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "⚠ Virtual environment not activated" -ForegroundColor Yellow
    Write-Host "  Activating venv..." -ForegroundColor Yellow
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & "venv\Scripts\Activate.ps1"
        Write-Host "✓ Virtual environment activated" -ForegroundColor Green
    } else {
        Write-Host "✗ venv not found. Please create it first:" -ForegroundColor Red
        Write-Host "  python -m venv venv" -ForegroundColor White
        exit 1
    }
}

Write-Host ""
Write-Host "Starting server..." -ForegroundColor Cyan
Write-Host "  URL: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  ReDoc: http://127.0.0.1:8000/redoc" -ForegroundColor White
Write-Host ""
Write-Host "Press CTRL+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the server
uvicorn main:app --reload --host 127.0.0.1 --port 8000
