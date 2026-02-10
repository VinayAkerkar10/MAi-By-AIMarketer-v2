# Running MAi Locally Without Docker
## Alternative Setup Guide

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

---

## Overview

You can run MAi locally **without Docker**, but you'll need to set up the required services manually.

---

## Option 1: With Docker (Recommended) ✅

**Pros:**
- ✅ Everything runs in containers
- ✅ No manual service setup
- ✅ Easy to start/stop
- ✅ Consistent environment

**Cons:**
- ❌ Requires Docker Desktop installed

**Setup:**
```bash
docker-compose up --build
```

---

## Option 2: Without Docker (Manual Setup)

### Prerequisites

You'll need to install and run these services manually:

1. **PostgreSQL** (Database)
2. **MongoDB** (Optional - for templates)
3. **Redis** (Optional - for caching/tasks)
4. **Ollama** (Optional - for local AI strategy)

### Step-by-Step Setup

#### 1. Install PostgreSQL

**Windows:**
- Download from https://www.postgresql.org/download/windows/
- Or use Chocolatey: `choco install postgresql`

**Mac:**
```bash
brew install postgresql
brew services start postgresql
```

**Linux:**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Create Database:**
```sql
CREATE USER mai_user WITH PASSWORD 'mai_password';
CREATE DATABASE mai_db OWNER mai_user;
```

#### 2. Install MongoDB (Optional)

**Windows:**
- Download from https://www.mongodb.com/try/download/community

**Mac:**
```bash
brew install mongodb-community
brew services start mongodb-community
```

**Linux:**
```bash
sudo apt-get install mongodb
sudo systemctl start mongodb
```

#### 3. Install Redis (Optional)

**Windows:**
- Download from https://github.com/microsoftarchive/redis/releases
- Or use WSL

**Mac:**
```bash
brew install redis
brew services start redis
```

**Linux:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

#### 4. Install Ollama (Optional - for local AI)

**All Platforms:**
- Download from https://ollama.ai/download
- Or use Docker: `docker run -d -p 11434:11434 ollama/ollama`

#### 5. Install Python Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 6. Set Environment Variables

Create a `.env` file:

```bash
# Database
DATABASE_URL=postgresql://mai_user:mai_password@localhost:5432/mai_db
MONGODB_URI=mongodb://localhost:27017/mai_templates
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_EXPIRE_MINUTES=30

# Strategy Provider
STRATEGY_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_STRATEGY_MODEL=llama2

# Or use OpenAI
# STRATEGY_PROVIDER=openai
# OPENAI_API_KEY=sk-your-key
```

#### 7. Initialize Database

```bash
# Set environment variables
export DATABASE_URL=postgresql://mai_user:mai_password@localhost:5432/mai_db

# Run initialization script
python services/init_db.py
```

#### 8. Run Services

**Terminal 1 - Auth Service:**
```bash
cd services/auth_service
uvicorn main:app --reload --port 8001
```

**Terminal 2 - Licensing Service:**
```bash
cd services/licensing_service
uvicorn main:app --reload --port 8002
```

**Terminal 3 - StrategyAI Service:**
```bash
cd services/strategy_ai_service
uvicorn main:app --reload --port 8003
```

**Terminal 4 - Lead Enrichment Service:**
```bash
cd services/lead_enrichment_service
uvicorn main:app --reload --port 8004
```

**Terminal 5 - Campaign Planner Service:**
```bash
cd services/campaign_planner_service
uvicorn main:app --reload --port 8005
```

**Terminal 6 - Analytics Service:**
```bash
cd services/analytics_service
uvicorn main:app --reload --port 8006
```

**Terminal 7 - API Gateway:**
```bash
cd api_gateway
uvicorn main:app --reload --port 8000
```

---

## Simplified Setup Script

I can create a script to help you run all services. Here's a simple approach:

### Windows (PowerShell)

Create `run_local.ps1`:

```powershell
# Start all services in background
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd services/auth_service; uvicorn main:app --reload --port 8001"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd services/licensing_service; uvicorn main:app --reload --port 8002"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd services/strategy_ai_service; uvicorn main:app --reload --port 8003"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd services/lead_enrichment_service; uvicorn main:app --reload --port 8004"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd services/campaign_planner_service; uvicorn main:app --reload --port 8005"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd services/analytics_service; uvicorn main:app --reload --port 8006"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd api_gateway; uvicorn main:app --reload --port 8000"

Write-Host "All services starting..."
Write-Host "API Gateway: http://localhost:8000"
```

### Mac/Linux (Bash)

Create `run_local.sh`:

```bash
#!/bin/bash

# Start all services in background
cd services/auth_service && uvicorn main:app --reload --port 8001 &
cd services/licensing_service && uvicorn main:app --reload --port 8002 &
cd services/strategy_ai_service && uvicorn main:app --reload --port 8003 &
cd services/lead_enrichment_service && uvicorn main:app --reload --port 8004 &
cd services/campaign_planner_service && uvicorn main:app --reload --port 8005 &
cd services/analytics_service && uvicorn main:app --reload --port 8006 &
cd api_gateway && uvicorn main:app --reload --port 8000 &

echo "All services starting..."
echo "API Gateway: http://localhost:8000"
```

---

## Comparison

| Aspect | With Docker | Without Docker |
|--------|------------|----------------|
| **Setup Time** | 5 minutes | 30-60 minutes |
| **Complexity** | Low | Medium-High |
| **Dependencies** | Docker only | PostgreSQL, MongoDB, Redis, Python |
| **Portability** | High | Low |
| **Resource Usage** | Higher (containers) | Lower (native) |
| **Debugging** | Easy | More complex |
| **Recommended For** | Development, Production | Advanced users |

---

## Recommendation

**For most users: Use Docker** ✅

- Faster setup
- Easier to manage
- Consistent environment
- Less configuration

**Without Docker if:**
- You prefer native services
- You need fine-grained control
- You're already running these services
- Docker isn't available

---

## Quick Decision Guide

**Do you have Docker installed?**
- ✅ Yes → Use Docker (recommended)
- ❌ No → Choose:
  - Install Docker (easier) OR
  - Manual setup (more work)

---

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**
