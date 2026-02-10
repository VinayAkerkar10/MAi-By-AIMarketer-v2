# PowerShell script to run all services locally without Docker
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

Write-Host "🚀 Starting MAi Services Locally (Without Docker)..." -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "⚠️  Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    .\venv\Scripts\activate
    pip install -r requirements.txt
}

# Activate virtual environment
Write-Host "🔌 Activating virtual environment..." -ForegroundColor Yellow
. .\venv\Scripts\activate

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found. Creating from env.example..." -ForegroundColor Yellow
    Copy-Item env.example .env
    Write-Host "✅ .env file created. Please update it with your configuration." -ForegroundColor Green
}

# Check if database is accessible
Write-Host "🔍 Checking database connection..." -ForegroundColor Yellow
$dbUrl = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { "postgresql://mai_user:mai_password@postgres:5432/mai_db" }
Write-Host "   Database URL: $dbUrl" -ForegroundColor Gray

# Start services
Write-Host ""
Write-Host "📡 Starting services..." -ForegroundColor Cyan
Write-Host ""

# Function to start service in new window
function Start-Service {
    param(
        [string]$ServiceName,
        [string]$Path,
        [int]$Port
    )
    
    $script = @"
cd '$PWD\$Path'
`$env:DATABASE_URL = '$dbUrl'
uvicorn main:app --reload --port $Port
"@
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $script
    Write-Host "   ✅ $ServiceName starting on port $Port" -ForegroundColor Green
    Start-Sleep -Milliseconds 500
}

# Start all services
Start-Service "Auth Service" "services\auth_service" 8001
Start-Service "Licensing Service" "services\licensing_service" 8002
Start-Service "StrategyAI Service" "services\strategy_ai_service" 8003
Start-Service "Lead Enrichment Service" "services\lead_enrichment_service" 8004
Start-Service "Campaign Planner Service" "services\campaign_planner_service" 8005
Start-Service "Analytics Service" "services\analytics_service" 8006
Start-Service "API Gateway" "api_gateway" 8000

Write-Host ""
Write-Host "✅ All services started!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Service URLs:" -ForegroundColor Cyan
Write-Host "   API Gateway:      http://localhost:8000" -ForegroundColor White
Write-Host "   Auth Service:     http://localhost:8001/docs" -ForegroundColor White
Write-Host "   Licensing:        http://localhost:8002/docs" -ForegroundColor White
Write-Host "   StrategyAI:      http://localhost:8003/docs" -ForegroundColor White
Write-Host "   Lead Enrichment:  http://localhost:8004/docs" -ForegroundColor White
Write-Host "   Campaign Planner: http://localhost:8005/docs" -ForegroundColor White
Write-Host "   Analytics:        http://localhost:8006/docs" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  Make sure PostgreSQL, MongoDB, and Redis are running!" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
