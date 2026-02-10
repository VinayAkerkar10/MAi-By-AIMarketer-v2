# Local Setup Instructions (Without Docker)
## Step-by-Step Guide

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

---

## Prerequisites Checklist

- [ ] Python 3.11+ ✅ (You have 3.13.7)
- [ ] PostgreSQL (needs to be installed)
- [ ] MongoDB (optional)
- [ ] Redis (optional)
- [ ] Ollama (optional - for local AI)

---

## Step 1: Install PostgreSQL

### Windows

1. **Download PostgreSQL:**
   - Go to: https://www.postgresql.org/download/windows/
   - Download the installer
   - Run the installer

2. **During Installation:**
   - Remember the password you set for the `postgres` user
   - Default port: 5432
   - Install pgAdmin (optional but helpful)

3. **Verify Installation:**
   ```powershell
   # Check if PostgreSQL service is running
   Get-Service postgresql*
   ```

### Alternative: Use SQLite for Testing

If you want to test without PostgreSQL first, we can modify the code to use SQLite temporarily.

---

## Step 2: Create Database

1. **Open pgAdmin** or use `psql` command line

2. **Run these SQL commands:**
   ```sql
   -- Create user
   CREATE USER mai_user WITH PASSWORD 'mai_password';
   
   -- Create database
   CREATE DATABASE mai_db OWNER mai_user;
   
   -- Grant privileges
   GRANT ALL PRIVILEGES ON DATABASE mai_db TO mai_user;
   ```

3. **Or use psql command line:**
   ```powershell
   psql -U postgres
   ```
   Then run the SQL commands above.

---

## Step 3: Set Up Python Environment

1. **Create virtual environment:**
   ```powershell
   python -m venv venv
   ```

2. **Activate virtual environment:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   **Note:** If `psycopg2-binary` fails, install PostgreSQL first, then retry.

---

## Step 4: Configure Environment

1. **Create `.env` file:**
   ```powershell
   Copy-Item env.example .env
   ```

2. **Edit `.env` file** with your database credentials:
   ```bash
   DATABASE_URL=postgresql://mai_user:mai_password@localhost:5432/mai_db
   JWT_SECRET_KEY=your-secret-key-here
   STRATEGY_PROVIDER=ollama
   OLLAMA_BASE_URL=http://localhost:11434
   ```

---

## Step 5: Initialize Database

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Set database URL
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"

# Initialize database
python services/init_db.py
```

---

## Step 6: Start Services

### Option A: Use the Script

```powershell
.\scripts\run_local.ps1
```

### Option B: Manual Start

Open multiple terminal windows and run:

**Terminal 1 - Auth Service:**
```powershell
.\venv\Scripts\Activate.ps1
cd services\auth_service
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"
uvicorn main:app --reload --port 8001
```

**Terminal 2 - Licensing Service:**
```powershell
.\venv\Scripts\Activate.ps1
cd services\licensing_service
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"
uvicorn main:app --reload --port 8002
```

**Terminal 3 - StrategyAI Service:**
```powershell
.\venv\Scripts\Activate.ps1
cd services\strategy_ai_service
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"
uvicorn main:app --reload --port 8003
```

**Terminal 4 - Lead Enrichment Service:**
```powershell
.\venv\Scripts\Activate.ps1
cd services\lead_enrichment_service
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"
uvicorn main:app --reload --port 8004
```

**Terminal 5 - Campaign Planner Service:**
```powershell
.\venv\Scripts\Activate.ps1
cd services\campaign_planner_service
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"
uvicorn main:app --reload --port 8005
```

**Terminal 6 - Analytics Service:**
```powershell
.\venv\Scripts\Activate.ps1
cd services\analytics_service
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"
uvicorn main:app --reload --port 8006
```

**Terminal 7 - API Gateway:**
```powershell
.\venv\Scripts\Activate.ps1
cd api_gateway
uvicorn main:app --reload --port 8000
```

---

## Step 7: Create Admin User

```powershell
.\venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"
python scripts\create_admin.py
```

---

## Troubleshooting

### PostgreSQL Connection Error

**Error:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
1. Check if PostgreSQL is running:
   ```powershell
   Get-Service postgresql*
   ```
2. Start PostgreSQL if not running:
   ```powershell
   Start-Service postgresql-x64-*
   ```
3. Verify connection:
   ```powershell
   psql -U mai_user -d mai_db -h localhost
   ```

### psycopg2 Installation Error

**Error:** `pg_config executable not found`

**Solution:**
1. Install PostgreSQL (includes pg_config)
2. Add PostgreSQL bin directory to PATH:
   ```powershell
   $env:PATH += ";C:\Program Files\PostgreSQL\15\bin"
   ```
3. Retry installation:
   ```powershell
   pip install psycopg2-binary
   ```

### Port Already in Use

**Error:** `Address already in use`

**Solution:**
- Change port in the service command
- Or stop the service using that port

---

## Quick Test

Once all services are running:

1. **Check API Gateway:**
   ```
   http://localhost:8000/docs
   ```

2. **Check Auth Service:**
   ```
   http://localhost:8001/docs
   ```

3. **Test Health Endpoint:**
   ```powershell
   Invoke-WebRequest http://localhost:8000/health
   ```

---

## Next Steps

1. ✅ Install PostgreSQL
2. ✅ Create database and user
3. ✅ Install Python dependencies
4. ✅ Configure `.env` file
5. ✅ Initialize database
6. ✅ Start services
7. ✅ Create admin user
8. ✅ Test the API

---

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**
