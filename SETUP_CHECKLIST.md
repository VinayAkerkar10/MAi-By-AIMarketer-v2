# MAi Local Setup Checklist
## Follow These Steps in Order

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

---

## ✅ Step 1: Install PostgreSQL

**Status:** ❌ Not installed yet

**Action Required:**
1. Download from: https://www.postgresql.org/download/windows/
2. Run installer
3. **Remember the password** you set for `postgres` user
4. Keep default port: 5432

**Detailed guide:** See `POSTGRESQL_SETUP_GUIDE.md`

**After installation, verify:**
```powershell
Get-Service postgresql*
```

---

## ✅ Step 2: Create Database and User

**Status:** ⏳ Waiting for PostgreSQL

**After PostgreSQL is installed, run these SQL commands:**

**Option A: Using pgAdmin (Easier)**
1. Open pgAdmin 4
2. Connect to localhost server (password: the one you set during installation)
3. Create user: `mai_user` with password: `mai_password`
4. Create database: `mai_db` owned by `mai_user`

**Option B: Using psql**
```powershell
psql -U postgres
# Enter your postgres password, then:
CREATE USER mai_user WITH PASSWORD 'mai_password';
CREATE DATABASE mai_db OWNER mai_user;
GRANT ALL PRIVILEGES ON DATABASE mai_db TO mai_user;
\q
```

---

## ✅ Step 3: Install Python Dependencies

**Status:** ⏳ Waiting for PostgreSQL

**After PostgreSQL is installed, run:**
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

**Expected:** Should install successfully now that PostgreSQL is available.

---

## ✅ Step 4: Configure Environment

**Status:** ✅ Ready

**Create .env file:**
```powershell
Copy-Item env.example .env
```

**Edit `.env` file and set:**
```bash
DATABASE_URL=postgresql://mai_user:mai_password@localhost:5432/mai_db
JWT_SECRET_KEY=your-secret-key-change-this
STRATEGY_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

---

## ✅ Step 5: Initialize Database

**Status:** ⏳ Waiting for previous steps

**After Steps 1-4 are complete:**
```powershell
.\venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"
python services/init_db.py
```

**Expected output:**
```
Initializing database...
Database tables created
Initializing feature matrix...
Feature matrix initialized successfully
Database initialization complete!
```

---

## ✅ Step 6: Create Admin User

**Status:** ⏳ Waiting for previous steps

**After database is initialized:**
```powershell
.\venv\Scripts\Activate.ps1
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"
python scripts\create_admin.py
```

**Follow the prompts:**
- Enter organization name
- Enter admin user ID
- Enter admin password
- Select license type (1, 2, or 3)

---

## ✅ Step 7: Start Services

**Status:** ⏳ Waiting for previous steps

**Option A: Use Script (Easier)**
```powershell
.\scripts\run_local.ps1
```

**Option B: Manual Start**
Open 7 separate terminal windows and start each service (see `SETUP_INSTRUCTIONS.md`)

---

## ✅ Step 8: Test the API

**Status:** ⏳ Waiting for services to start

**After services are running:**

1. **Check API Gateway:**
   ```
   http://localhost:8000/docs
   ```

2. **Test Health:**
   ```powershell
   Invoke-WebRequest http://localhost:8000/health
   ```

3. **Login:**
   ```powershell
   $body = @{
       organization_name = "YourOrg"
       user_id = "admin"
       password = "your-password"
   } | ConvertTo-Json

   Invoke-WebRequest -Uri "http://localhost:8000/api/auth/org-login" `
       -Method POST `
       -ContentType "application/json" `
       -Body $body
   ```

---

## Quick Reference Commands

**After PostgreSQL is installed:**

```powershell
# 1. Activate venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set database URL
$env:DATABASE_URL="postgresql://mai_user:mai_password@localhost:5432/mai_db"

# 4. Initialize database
python services/init_db.py

# 5. Create admin
python scripts\create_admin.py

# 6. Start services
.\scripts\run_local.ps1
```

---

## Current Progress

- ✅ Python 3.13.7 installed
- ✅ Virtual environment created
- ❌ PostgreSQL - **NEXT STEP**
- ⏳ Database setup
- ⏳ Dependencies installation
- ⏳ Environment configuration
- ⏳ Database initialization
- ⏳ Admin user creation
- ⏳ Services startup

---

**Next Action:** Install PostgreSQL (see `POSTGRESQL_SETUP_GUIDE.md`)

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**
