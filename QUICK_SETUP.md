# Quick Setup Summary
## What You Need to Do Right Now

**Current Status:**
- ✅ Python 3.13.7 installed
- ✅ Virtual environment created
- ❌ PostgreSQL not installed (needed for database)
- ❌ Dependencies not fully installed (waiting for PostgreSQL)

---

## Immediate Next Steps

### 1. Install PostgreSQL (Required)

**Download:** https://www.postgresql.org/download/windows/

**During installation:**
- Remember the password for `postgres` user
- Default port: 5432
- Install pgAdmin (recommended)

**After installation:**
- PostgreSQL service should start automatically
- You can verify with: `Get-Service postgresql*`

### 2. Create Database

Open **pgAdmin** or **psql** and run:

```sql
CREATE USER mai_user WITH PASSWORD 'mai_password';
CREATE DATABASE mai_db OWNER mai_user;
GRANT ALL PRIVILEGES ON DATABASE mai_db TO mai_user;
```

### 3. Install Python Dependencies

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies (should work after PostgreSQL is installed)
pip install -r requirements.txt
```

### 4. Configure Environment

```powershell
# Create .env file
Copy-Item env.example .env

# Edit .env and set:
# DATABASE_URL=postgresql://mai_user:mai_password@localhost:5432/mai_db
# JWT_SECRET_KEY=your-secret-key
```

### 5. Initialize Database

```powershell
.\venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"
python services/init_db.py
```

### 6. Start Services

```powershell
.\scripts\run_local.ps1
```

Or manually start each service in separate terminals.

---

## Alternative: Test Without PostgreSQL First

If you want to test the code structure first without PostgreSQL, I can help you:
1. Modify the code to use SQLite temporarily
2. Or create a mock database layer

Let me know which approach you prefer!

---

**See `SETUP_INSTRUCTIONS.md` for detailed instructions.**
