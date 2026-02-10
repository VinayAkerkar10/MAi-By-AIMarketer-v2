# Continue Setup After PostgreSQL Installation
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

Write-Host "🚀 Continuing MAi Setup After PostgreSQL Installation" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host ""

# Check if PostgreSQL is installed
Write-Host "🔍 Checking PostgreSQL installation..." -ForegroundColor Yellow
$pgService = Get-Service -Name postgresql* -ErrorAction SilentlyContinue

if (-not $pgService) {
    Write-Host "❌ PostgreSQL service not found!" -ForegroundColor Red
    Write-Host "   Please install PostgreSQL first." -ForegroundColor Yellow
    Write-Host "   See: POSTGRESQL_SETUP_GUIDE.md" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ PostgreSQL service found: $($pgService.Name)" -ForegroundColor Green

# Check if service is running
if ($pgService.Status -ne "Running") {
    Write-Host "⚠️  PostgreSQL service is not running. Starting..." -ForegroundColor Yellow
    Start-Service $pgService.Name
    Start-Sleep -Seconds 3
    Write-Host "✅ PostgreSQL service started" -ForegroundColor Green
} else {
    Write-Host "✅ PostgreSQL service is running" -ForegroundColor Green
}

# Step 1: Install Python dependencies
Write-Host ""
Write-Host "📦 Step 1: Installing Python dependencies..." -ForegroundColor Yellow

if (-not (Test-Path "venv")) {
    Write-Host "   Creating virtual environment..." -ForegroundColor Gray
    python -m venv venv
}

.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    Write-Host "   Make sure PostgreSQL is properly installed" -ForegroundColor Yellow
    exit 1
}

# Step 2: Create .env file
Write-Host ""
Write-Host "⚙️  Step 2: Setting up environment variables..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Copy-Item env.example .env
    Write-Host "✅ .env file created from env.example" -ForegroundColor Green
    Write-Host "   ⚠️  Please edit .env and set your database credentials" -ForegroundColor Yellow
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

# Step 3: Database setup reminder
Write-Host ""
Write-Host "🗄️  Step 3: Database Setup" -ForegroundColor Yellow
Write-Host "   Make sure you've created:" -ForegroundColor White
Write-Host "   - User: mai_user with password: mai_password" -ForegroundColor Gray
Write-Host "   - Database: mai_db owned by mai_user" -ForegroundColor Gray
Write-Host ""

$continue = Read-Host "Have you created the database and user? (y/n)"
if ($continue -ne "y" -and $continue -ne "Y") {
    Write-Host ""
    Write-Host "📋 Run these SQL commands in pgAdmin or psql:" -ForegroundColor Cyan
    Write-Host "   CREATE USER mai_user WITH PASSWORD 'mai_password';" -ForegroundColor Gray
    Write-Host "   CREATE DATABASE mai_db OWNER mai_user;" -ForegroundColor Gray
    Write-Host "   GRANT ALL PRIVILEGES ON DATABASE mai_db TO mai_user;" -ForegroundColor Gray
    Write-Host ""
    Write-Host "   Then run this script again." -ForegroundColor Yellow
    exit 0
}

# Step 4: Initialize database
Write-Host ""
Write-Host "🗄️  Step 4: Initializing database..." -ForegroundColor Yellow

$dbUrl = if ($env:DATABASE_URL) { 
    $env:DATABASE_URL 
} else { 
    "postgresql://mai_user:mai_password@postgres:5432/mai_db" 
}

$env:DATABASE_URL = $dbUrl
python services/init_db.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Database initialized successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Database initialization failed" -ForegroundColor Red
    Write-Host "   Check your database connection settings" -ForegroundColor Yellow
    exit 1
}

# Step 5: Create admin user
Write-Host ""
Write-Host "👤 Step 5: Create admin user..." -ForegroundColor Yellow
Write-Host "   (You'll be prompted for details)" -ForegroundColor Gray
Write-Host ""

python scripts\create_admin.py

# Summary
Write-Host ""
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Start services: .\scripts\run_local.ps1" -ForegroundColor White
Write-Host "   2. Access API Gateway: http://localhost:8000/docs" -ForegroundColor White
Write-Host "   3. Login with the admin credentials you just created" -ForegroundColor White
Write-Host ""
Write-Host "🎉 You're ready to go!" -ForegroundColor Green
Write-Host ""
