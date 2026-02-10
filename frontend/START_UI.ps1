Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MAi UI - Starting Web Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting server on http://localhost:8080" -ForegroundColor Green
Write-Host ""
Write-Host "Once you see 'Serving HTTP on 0.0.0.0 port 8080'" -ForegroundColor Yellow
Write-Host "Open your browser and go to:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  http://localhost:8080/standalone.html" -ForegroundColor White -BackgroundColor DarkBlue
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get the directory where this script is located
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Start the server
python -m http.server 8080
