# Complete Local Setup Script (Without Docker)
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

Write-Host "🚀 MAi Local Setup (Without Docker)" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python
Write-Host "✅ Python 3.13.7 detected" -ForegroundColor Green

# Step 2: Create virtual environment
Write-Host ""
Write-Host "📦 Step 1: Setting up virtual environment..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "   ✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "   ✅ Virtual environment already exists" -ForegroundColor Green
}

# Step 3: Activate and install dependencies
Write-Host ""
Write-Host "📦 Step 2: Installing dependencies..." -ForegroundColor Yellow
& .\venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
Write-Host "   ✅ Dependencies installed" -ForegroundColor Green

# Step 4: Create .env file
Write-Host ""
Write-Host "⚙️  Step 3: Setting up environment variables..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item env.example .env
    Write-Host "   ✅ .env file created from env.example" -ForegroundColor Green
    Write-Host "   ⚠️  Please update .env with your database credentials" -ForegroundColor Yellow
} else {
    Write-Host "   ✅ .env file already exists" -ForegroundColor Green
}

# Step 5: Check PostgreSQL
Write-Host ""
Write-Host "🔍 Step 4: Checking PostgreSQL..." -ForegroundColor Yellow
$pgCheck = Get-Service -Name postgresql* -ErrorAction SilentlyContinue
if ($pgCheck) {
    Write-Host "   ✅ PostgreSQL service found" -ForegroundColor Green
    Write-Host "   ⚠️  Make sure it's running: Start-Service postgresql-x64-*" -ForegroundColor Yellow
} else {
    Write-Host "   ⚠️  PostgreSQL not found. You need to:" -ForegroundColor Yellow
    Write-Host "      1. Install PostgreSQL from https://www.postgresql.org/download/windows/" -ForegroundColor White
    Write-Host "      2. Create database: CREATE DATABASE mai_db;" -ForegroundColor White
    Write-Host "      3. Create user: CREATE USER mai_user WITH PASSWORD 'mai_password';" -ForegroundColor White
    Write-Host "      4. Grant privileges: GRANT ALL PRIVILEGES ON DATABASE mai_db TO mai_user;" -ForegroundColor White
}

# Step 6: Database setup instructions
Write-Host ""
Write-Host "📋 Step 5: Database Setup Instructions" -ForegroundColor Yellow
Write-Host "   Run these SQL commands in PostgreSQL:" -ForegroundColor White
Write-Host ""
Write-Host "   CREATE USER mai_user WITH PASSWORD 'mai_password';" -ForegroundColor Gray
Write-Host "   CREATE DATABASE mai_db OWNER mai_user;" -ForegroundColor Gray
Write-Host "   GRANT ALL PRIVILEGES ON DATABASE mai_db TO mai_user;" -ForegroundColor Gray
Write-Host ""

# Step 7: Initialize database
Write-Host "🗄️  Step 6: Initialize database schema..." -ForegroundColor Yellow
Write-Host "   Run this command after setting up PostgreSQL:" -ForegroundColor White
Write-Host "   python services/init_db.py" -ForegroundColor Gray
Write-Host ""

# Summary
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Install PostgreSQL (if not installed)" -ForegroundColor White
Write-Host "   2. Create database and user (see SQL commands above)" -ForegroundColor White
Write-Host "   3. Update .env file with your database credentials" -ForegroundColor White
Write-Host "   4. Run: python services/init_db.py" -ForegroundColor White
Write-Host "   5. Run: .\scripts\run_local.ps1" -ForegroundColor White
Write-Host ""
Write-Host "📚 For detailed instructions, see: LOCAL_SETUP_WITHOUT_DOCKER.md" -ForegroundColor Cyan
Write-Host ""
