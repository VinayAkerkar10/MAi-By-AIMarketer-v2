# MAi Platform - Quick Start Guide
## Microservices Architecture

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

---

## Prerequisites

**Choose your setup method:**

### Option A: With Docker (Recommended) ✅
- Docker & Docker Compose
- Python 3.11+ (for scripts)
- Git

### Option B: Without Docker
- Python 3.11+
- PostgreSQL (database)
- MongoDB (optional)
- Redis (optional)
- Git

**See `LOCAL_SETUP_WITHOUT_DOCKER.md` for manual setup instructions.**

---

## Quick Start with Docker (5 Minutes)

### 1. Clone and Navigate

```bash
cd marketing-app-main
```

### 2. Set Environment Variables

Create a `.env` file (or use `env.example`):

```bash
JWT_SECRET_KEY=your-secret-key-here

# Strategy Provider (choose one)
STRATEGY_PROVIDER=ollama  # or 'openai' or 'auto'

# For Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_STRATEGY_MODEL=llama2

# For OpenAI (API) - optional
OPENAI_API_KEY=your-openai-key
```

### 2a. Setup Ollama (Recommended for Local Development)

**Linux/Mac:**
```bash
chmod +x scripts/setup_ollama.sh
./scripts/setup_ollama.sh
```

**Windows:**
```powershell
.\scripts\setup_ollama.ps1
```

**Or manually:**
```bash
# Start Ollama
docker-compose --profile ollama up ollama -d

# Pull a model
docker exec -it ollama ollama pull llama2
```

### 3. Initialize Database

```bash
# Start database
docker-compose up postgres -d

# Wait for database to be ready (10-15 seconds)
# Then initialize schema
docker-compose --profile init run init_db
```

### 4. Start All Services

```bash
docker-compose up --build
```

This will start:
- PostgreSQL database
- MongoDB
- Redis
- 7 Microservices
- API Gateway
- Celery workers

### 5. Access Services

- **API Gateway**: http://localhost:8000/docs
- **Auth Service**: http://localhost:8001/docs
- **StrategyAI Service**: http://localhost:8003/docs

---

## Quick Start Without Docker

If you prefer not to use Docker, see `LOCAL_SETUP_WITHOUT_DOCKER.md` for detailed instructions.

**Quick version:**
1. Install PostgreSQL, MongoDB, Redis locally
2. Create database: `CREATE DATABASE mai_db;`
3. Set environment variables in `.env`
4. Run: `python services/init_db.py`
5. Start services: Use `scripts/run_local.ps1` (Windows) or `scripts/run_local.sh` (Mac/Linux)

---

## First-Time Setup

### Create First Organization and Admin User

1. **Start services** (as above)

2. **Create organization via API**:

```bash
# First, you'll need to create an initial admin user
# This can be done by directly inserting into database or via a setup script

# Option 1: Use Python script (create after services are running)
python scripts/create_admin.py
```

3. **Login as Admin**:

```bash
curl -X POST "http://localhost:8000/api/auth/org-login" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_name": "YourOrg",
    "user_id": "admin",
    "password": "admin123"
  }'
```

4. **Create Users and Assign Licenses**:

Use the admin endpoints to:
- Create users: `POST /api/admin/users`
- Assign licenses: `POST /api/admin/licenses`

---

## Service Ports

| Service | Port | URL |
|---------|------|-----|
| API Gateway | 8000 | http://localhost:8000 |
| Auth Service | 8001 | http://localhost:8001 |
| Licensing Service | 8002 | http://localhost:8002 |
| StrategyAI Service | 8003 | http://localhost:8003 |
| Lead Enrichment Service | 8004 | http://localhost:8004 |
| Campaign Planner Service | 8005 | http://localhost:8005 |
| Analytics Service | 8006 | http://localhost:8006 |

---

## Common Commands

### Start Services
```bash
docker-compose up
```

### Start in Background
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f [service_name]
```

### Stop Services
```bash
docker-compose down
```

### Rebuild Services
```bash
docker-compose up --build
```

### Initialize Database Only
```bash
docker-compose --profile init run init_db
```

---

## Testing the API

### 1. Health Check

```bash
curl http://localhost:8000/health
```

### 2. Org-First Login

```bash
curl -X POST "http://localhost:8000/api/auth/org-login" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_name": "TestOrg",
    "user_id": "user1",
    "password": "password123"
  }'
```

### 3. Generate Strategy (requires JWT token)

```bash
curl -X POST "http://localhost:8000/api/strategy/generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "business_profile": {
      "business_name": "Tech Solutions",
      "industry": "technology",
      "company_size": "Medium",
      "geography": "North America",
      "marketing_goals": ["Lead Generation"],
      "budget_range": "$10k-$50k"
    }
  }'
```

---

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres
```

### Service Not Starting

```bash
# Check service logs
docker-compose logs [service_name]

# Rebuild service
docker-compose up --build [service_name]
```

### Port Already in Use

If a port is already in use, modify `docker-compose.yml` to use different ports.

---

## Development Mode

For local development without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://mai_user:mai_password@localhost:5432/mai_db
export JWT_SECRET_KEY=your-secret-key

# Run individual services
cd services/auth_service
uvicorn main:app --reload --port 8001
```

---

## Next Steps

1. Read `REFACTORING_GUIDE.md` for detailed documentation
2. Review `REFACTORING_SUMMARY.md` for architecture overview
3. Check `ALIGNMENT_ANALYSIS.md` for original design comparison

---

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**
