# PostgreSQL Setup Guide for MAi
## Step-by-Step Installation

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

---

## Installation Steps

### 1. Download PostgreSQL

1. **Go to:** https://www.postgresql.org/download/windows/
2. **Click:** "Download the installer"
3. **Choose:** Latest version (PostgreSQL 15 or 16)
4. **Download:** Windows x86-64 installer

### 2. Run the Installer

1. **Double-click** the downloaded `.exe` file
2. **Click:** "Next" through the welcome screen
3. **Choose installation directory:** (Default is fine)
4. **Select components:** (All are selected by default - keep them)
   - PostgreSQL Server
   - pgAdmin 4
   - Stack Builder
   - Command Line Tools
5. **Click:** "Next"

### 3. Data Directory

- **Default location:** `C:\Program Files\PostgreSQL\15\data`
- **Click:** "Next" (default is fine)

### 4. Set Password

**IMPORTANT:** Set a password for the `postgres` superuser
- **Remember this password!** You'll need it later
- **Click:** "Next"

### 5. Port Configuration

- **Default port:** 5432
- **Click:** "Next" (keep default)

### 6. Advanced Options

- **Locale:** Default (usually "C")
- **Click:** "Next"

### 7. Ready to Install

- **Review** the summary
- **Click:** "Next" to begin installation

### 8. Installation Complete

- **Uncheck** "Launch Stack Builder" (not needed)
- **Click:** "Finish"

---

## Post-Installation Setup

### 1. Verify Installation

Open PowerShell and run:

```powershell
# Check if PostgreSQL service is running
Get-Service postgresql*

# Should show something like:
# Status   Name               DisplayName
# ------   ----               -----------
# Running  postgresql-x64-15  postgresql-x64-15 - PostgreSQL Server 15
```

### 2. Start PostgreSQL Service (if not running)

```powershell
# Find the service name
Get-Service postgresql*

# Start the service (replace with your actual service name)
Start-Service postgresql-x64-15
```

### 3. Add PostgreSQL to PATH (Optional but Recommended)

```powershell
# Add to PATH for current session
$env:PATH += ";C:\Program Files\PostgreSQL\15\bin"

# Or add permanently (requires admin):
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";C:\Program Files\PostgreSQL\15\bin", "User")
```

### 4. Create Database and User

**Option A: Using pgAdmin (GUI - Easier)**

1. **Open pgAdmin 4** (from Start Menu)
2. **Connect to server:**
   - Right-click "Servers" → "Create" → "Server"
   - Name: `localhost`
   - Host: `localhost`
   - Port: `5432`
   - Username: `postgres`
   - Password: (the password you set during installation)
3. **Create User:**
   - Expand "localhost" → "Login/Group Roles"
   - Right-click → "Create" → "Login/Group Role"
   - Name: `mai_user`
   - Password: `mai_password`
   - Privileges: Check "Can login?"
   - Click "Save"
4. **Create Database:**
   - Right-click "Databases" → "Create" → "Database"
   - Database: `mai_db`
   - Owner: `mai_user`
   - Click "Save"

**Option B: Using psql (Command Line)**

```powershell
# Connect to PostgreSQL
psql -U postgres

# Enter your postgres password when prompted
# Then run these SQL commands:

CREATE USER mai_user WITH PASSWORD 'mai_password';
CREATE DATABASE mai_db OWNER mai_user;
GRANT ALL PRIVILEGES ON DATABASE mai_db TO mai_user;
\q
```

---

## Verify Database Setup

```powershell
# Test connection
psql -U mai_user -d mai_db -h localhost

# If it connects successfully, you're good!
# Type \q to exit
```

---

## Troubleshooting

### Service Won't Start

```powershell
# Check service status
Get-Service postgresql*

# Try starting manually
Start-Service postgresql-x64-15

# Check logs
Get-Content "C:\Program Files\PostgreSQL\15\data\log\*.log" -Tail 20
```

### Connection Refused

1. **Check if service is running:**
   ```powershell
   Get-Service postgresql*
   ```

2. **Check if port 5432 is in use:**
   ```powershell
   netstat -an | findstr 5432
   ```

3. **Verify firewall settings:**
   - Windows Firewall should allow PostgreSQL

### Password Issues

- If you forgot the postgres password, you can reset it:
  1. Stop PostgreSQL service
  2. Edit `pg_hba.conf` (in data directory)
  3. Change authentication method to `trust` temporarily
  4. Restart service
  5. Connect without password and reset it
  6. Change `pg_hba.conf` back

---

## Next Steps After PostgreSQL Setup

1. ✅ PostgreSQL installed
2. ✅ Database and user created
3. **Continue with Python setup:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
4. **Configure .env file**
5. **Initialize database:**
   ```powershell
   python services/init_db.py
   ```
6. **Start services:**
   ```powershell
   .\scripts\run_local.ps1
   ```

---

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**
