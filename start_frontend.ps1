# Start Frontend Server Script
# This script starts the frontend HTTP server on port 3000

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Starting SLMS Frontend Server" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if port 3000 is already in use
$port3000 = netstat -ano | findstr :3000 | findstr LISTENING
if ($port3000) {
    Write-Host "[WARNING] Port 3000 is already in use!" -ForegroundColor Yellow
    Write-Host "Killing existing processes on port 3000..." -ForegroundColor Yellow
    
    $pids = $port3000 | ForEach-Object {
        if ($_ -match '\s+(\d+)$') {
            $matches[1]
        }
    }
    
    foreach ($processId in $pids) {
        if ($processId) {
            Write-Host "  Killing process PID: $processId" -ForegroundColor Yellow
            taskkill /PID $processId /F 2>$null
        }
    }
    
    Start-Sleep -Seconds 2
    Write-Host ""
}

# Navigate to frontend directory
$frontendDir = Join-Path $PSScriptRoot "slms-frontend"
if (-not (Test-Path $frontendDir)) {
    Write-Host "[ERROR] Frontend directory not found: $frontendDir" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

Write-Host "Frontend directory: $frontendDir" -ForegroundColor Green
Write-Host ""
Write-Host "Starting HTTP server on port 3000..." -ForegroundColor Green
Write-Host "  URL: http://127.0.0.1:3000" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Change to frontend directory and start server
Set-Location $frontendDir
python -m http.server 3000 --bind 127.0.0.1

