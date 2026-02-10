# MAi Refactoring Guide
## Microservices Architecture Implementation

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

---

## Overview

This document describes the refactored MAi platform architecture, aligned with the original design specifications.

---

## Architecture

### Microservices Structure

```
MAi Platform
├── API Gateway (Port 8000)
├── Auth & Organization Service (Port 8001)
├── Licensing Service (Port 8002)
├── StrategyAI Service (Port 8003)
├── Lead Enrichment Service (Port 8004)
├── Campaign Planner Service (Port 8005)
└── Analytics Service (Port 8006)
```

### Shared Components

- **Database Models** (`services/shared/database.py`)
- **Authentication** (`services/shared/auth.py`)
- **Configuration** (`services/shared/config.py`)
- **Celery App** (`services/shared/celery_app.py`)

---

## Key Features Implemented

### ✅ 1. Microservice Architecture
- Each service is independently deployable
- Services communicate via API Gateway
- Separate ports for each service

### ✅ 2. Org-First Authentication
- **Endpoint**: `POST /api/auth/org-login`
- Flow:
  1. User enters Organization Name
  2. System validates org and checks licenses
  3. User enters User ID and Password
  4. Returns JWT with role and redirect path

### ✅ 3. Admin Panel Backend
- **Endpoints**:
  - `POST /api/admin/organizations` - Create organization
  - `GET /api/admin/organizations` - List organizations
  - `POST /api/admin/users` - Create user
  - `GET /api/admin/users` - List users
  - `POST /api/admin/licenses` - Assign license
  - `GET /api/admin/licenses` - List licenses

### ✅ 4. Licensing Module
- **License Types**:
  - `strategy_only` - Strategy AI + Templates
  - `strategy_leads` - Strategy + Lead Enrichment
  - `full_suite` - All features
- **Feature Gating**: API-level via `require_feature()` dependency
- **Endpoints**:
  - `GET /api/licensing/validate/{feature}` - Validate feature access
  - `GET /api/licensing/features` - Get available features
  - `GET /api/licensing/status` - Get license status

### ✅ 5. Role-Based Routing
- **Admin** → Redirected to Admin Panel
- **User** → Redirected to Strategy Flow
- Implemented in auth service login response

### ✅ 6. Strategy-First Approach
- **Primary Endpoint**: `POST /api/strategy/generate`
- Strategy generation is the main entry point for users
- Config-driven channel recommendations

### ✅ 7. Config-Driven
- Channel mappings: `config/channels.json`
- Budget allocation: `config/budget.json`
- Target segments: `config/segments.json`
- Content strategy: `config/content_strategy.json`
- KPIs: `config/kpis.json`

### ✅ 8. Multi-Tenant Database
- **Tables**:
  - `organizations` - Organization data
  - `users` - User accounts (org-scoped)
  - `licenses` - License assignments
  - `feature_matrix` - License type → Features mapping
  - `usage_records` - Feature usage tracking

---

## Setup Instructions

### 1. Initialize Database

```bash
# Start database only
docker-compose up postgres -d

# Initialize database schema and feature matrix
docker-compose --profile init run init_db
```

### 2. Start All Services

```bash
docker-compose up --build
```

### 3. Access Services

- **API Gateway**: http://localhost:8000
- **Auth Service**: http://localhost:8001/docs
- **Licensing Service**: http://localhost:8002/docs
- **StrategyAI Service**: http://localhost:8003/docs
- **Lead Enrichment Service**: http://localhost:8004/docs
- **Campaign Planner Service**: http://localhost:8005/docs
- **Analytics Service**: http://localhost:8006/docs

---

## Usage Examples

### 1. Create Organization (Admin)

```bash
curl -X POST "http://localhost:8000/api/auth/org-login" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_name": "TestOrg",
    "user_id": "admin",
    "password": "admin123"
  }'
```

First, create an organization via admin panel (requires initial admin setup).

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

Response includes:
- `access_token` - JWT token
- `redirect_to` - "admin_panel" or "strategy_flow"
- `licenses` - Active licenses

### 3. Generate Strategy (User)

```bash
curl -X POST "http://localhost:8000/api/strategy/generate" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "business_profile": {
      "business_name": "Tech Solutions Inc",
      "industry": "technology",
      "company_size": "Medium",
      "geography": "North America",
      "marketing_goals": ["Lead Generation"],
      "budget_range": "$10k-$50k"
    }
  }'
```

### 4. Assign License (Admin)

```bash
curl -X POST "http://localhost:8000/api/admin/licenses" \
  -H "Authorization: Bearer ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "org-id",
    "license_type": "full_suite",
    "period": "monthly",
    "max_users": 10
  }'
```

---

## Migration from Old Code

The old monolithic code (`mai-backend-main.py`, `mai-backend-modules.py`) has been refactored into:

- **Auth Service**: Authentication and org management
- **Licensing Service**: License validation
- **StrategyAI Service**: Strategy generation (from `generate-strategy` endpoint)
- **Lead Enrichment Service**: Lead scraping and enrichment (from `scrape-leads`, `upload-customers` endpoints)
- **Campaign Planner Service**: Campaign management (from `create-campaign` endpoint)
- **Analytics Service**: Analytics and reporting (from `campaign-metrics` endpoint)

---

## Next Steps

1. **Database Persistence**: Replace in-memory storage with database models
2. **OpenAI Integration**: Connect StrategyAI service to OpenAI GPT API
3. **Third-Party APIs**: Integrate Clearbit, Hunter.io, SendGrid, etc.
4. **Frontend Integration**: Update frontend to use new API endpoints
5. **Testing**: Add comprehensive test suite
6. **Monitoring**: Add logging and monitoring for each service

---

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Main entry point |
| Auth Service | 8001 | Authentication & Org Management |
| Licensing Service | 8002 | License validation |
| StrategyAI Service | 8003 | Strategy generation |
| Lead Enrichment Service | 8004 | Lead scraping & enrichment |
| Campaign Planner Service | 8005 | Campaign management |
| Analytics Service | 8006 | Analytics & reporting |

---

## Environment Variables

Key environment variables (set in `.env` or `docker-compose.yml`):

```bash
# Database
DATABASE_URL=postgresql://mai_user:mai_password@postgres:5432/mai_db

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_EXPIRE_MINUTES=30

# API Keys
OPENAI_API_KEY=your-openai-key
SENDGRID_API_KEY=your-sendgrid-key
CLEARBIT_API_KEY=your-clearbit-key
```

---

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**
