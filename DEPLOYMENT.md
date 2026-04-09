# Deployment Guide

## 1. Production Architecture

Current deployed request path:

`User -> Frontend (Vercel) -> API Gateway (Render) -> FastAPI microservices (Render) -> Neon PostgreSQL + provider APIs`

Current backend topology from the repository:

- Frontend is a static web app and points to the deployed API gateway at `https://api-gateway-1ug2.onrender.com` in [`frontend/config.js`](d:/marketing-app-main/frontend/config.js).
- Backend is split into seven Render web services defined in [`render.yaml`](d:/marketing-app-main/render.yaml):
  - `api-gateway`
  - `auth-service`
  - `licensing-service`
  - `strategy-ai-service`
  - `lead-enrichment-service`
  - `campaign-planner-service`
  - `analytics-service`
- PostgreSQL connectivity is driven by `DATABASE_URL` and all services share the same SQLAlchemy metadata/models from [`services/shared/database.py`](d:/marketing-app-main/services/shared/database.py).
- Celery is implemented for campaign execution and scheduling, with Redis used as broker/result backend, but the current `render.yaml` does not define a Redis service or a dedicated Celery worker service. Those are present only in local Docker Compose and code.

## 2. Infrastructure Overview

### Services

- API Gateway
  - Public ingress for frontend traffic.
  - Proxies `/api/auth`, `/api/licensing`, `/api/strategy`, `/api/leads`, `/api/campaigns`, and `/api/analytics`.
  - Adds CORS, retry logic, startup health checks, and periodic warmup.
- Auth Service
  - Org-first login, JWT issuance, logout/session invalidation, RBAC, org/user/license/API key admin.
- Licensing Service
  - License validation and feature availability checks.
- Strategy AI Service
  - LLM-backed strategy generation, provider inspection, master data, strategy history, and version detail.
- Lead Enrichment Service
  - Lead scraping, extension/direct URL ingestion, upload preview, enrichment jobs, and audit logging.
- Campaign Planner Service
  - Campaign CRUD, strategy-to-campaign mapping, scheduling, launching, lifecycle control, and email dispatch.
- Analytics Service
  - Campaign metrics, lead metrics, summary reports, and strategy performance.

### Service-to-service communication

- Frontend talks only to the API gateway.
- API gateway routes by environment-configured upstream URLs:
  - `AUTH_SERVICE_URL`
  - `LICENSING_SERVICE_URL`
  - `STRATEGY_SERVICE_URL`
  - `LEAD_SERVICE_URL`
  - `CAMPAIGN_SERVICE_URL`
  - `ANALYTICS_SERVICE_URL`
- Campaign Planner directly calls the Lead Enrichment service via `LEAD_SERVICE_URL` to fetch audiences for campaigns.
- Services share a single PostgreSQL database through `DATABASE_URL`.

### External dependencies

- Neon PostgreSQL
  - Shared transactional database for all services.
- Redis
  - Required for Celery broker/result backend.
- LLM providers
  - Ollama Cloud or local Ollama
  - OpenAI
- Lead/data providers
  - GitHub
  - Google Maps Places
  - LinkedIn/SerpAPI-style search path
  - Clearbit
  - Hunter
  - Outscraper
  - Volza placeholder integration
- Email providers
  - Mailrelay
  - Gmail SMTP
  - MailHog for local/dev safety

### Background job handling

- Implemented:
  - Celery app in [`services/shared/celery_app.py`](d:/marketing-app-main/services/shared/celery_app.py)
  - Campaign task in [`services/campaign_planner_service/tasks.py`](d:/marketing-app-main/services/campaign_planner_service/tasks.py)
  - Scheduling handoff in [`services/campaign_planner_service/campaign_scheduler.py`](d:/marketing-app-main/services/campaign_planner_service/campaign_scheduler.py)
- Current gap:
  - `render.yaml` does not provision a Celery worker service or Redis instance.
  - Lead scraping and enrichment still use FastAPI `BackgroundTasks`, not Celery.

## 3. Backend Deployment (Render)

### How Render is configured

All backend services are defined in [`render.yaml`](d:/marketing-app-main/render.yaml) as `type: web`, `runtime: docker`, with:

- `dockerfilePath: ./Dockerfile`
- `dockerContext: .`
- `autoDeploy: true`
- `plan: free`

This means Render will build each service from the same repository and Docker image definition, then start each one with a service-specific command via `SERVICE_COMMAND`.

### Docker runtime

The shared Docker image in [`Dockerfile`](d:/marketing-app-main/Dockerfile):

- Uses `python:3.11-slim`
- Installs Python dependencies from `requirements.txt`
- Copies the full repository into the container
- Runs as a non-root user
- Starts the app with:

```sh
sh -c "$SERVICE_COMMAND"
```

### Per-service startup commands

Configured in `render.yaml`:

- Auth
  - `uvicorn services.auth_service.main:app --host 0.0.0.0 --port $PORT`
- Licensing
  - `uvicorn services.licensing_service.main:app --host 0.0.0.0 --port $PORT`
- Strategy AI
  - `uvicorn services.strategy_ai_service.main:app --host 0.0.0.0 --port $PORT`
- Lead Enrichment
  - `uvicorn services.lead_enrichment_service.main:app --host 0.0.0.0 --port $PORT`
- Campaign Planner
  - `uvicorn services.campaign_planner_service.main:app --host 0.0.0.0 --port $PORT`
- Analytics
  - `uvicorn services.analytics_service.main:app --host 0.0.0.0 --port $PORT`
- API Gateway
  - `uvicorn api_gateway.main:app --host 0.0.0.0 --port $PORT`

### Render environment handling

- Service URLs are injected into the gateway through environment variables.
- Shared secrets such as `DATABASE_URL` and `JWT_SECRET_KEY` are marked with `sync: false` in `render.yaml`, meaning they must be entered in Render manually.
- Strategy AI has additional Render-level defaults:
  - `ENV=staging`
  - `CONFIG_DIR=/opt/render/project/src/config`
  - `LLM_PROVIDER=ollama_cloud`
  - `OLLAMA_BASE_URL=https://ollama.com/api`
  - `MODEL_NAME=kimi-k2:1t`
- Gateway upstreams on Render point to:
  - `https://auth-service.onrender.com`
  - `https://licensing-service.onrender.com`
  - `https://strategy-ai-service.onrender.com`
  - `https://lead-enrichment-service.onrender.com`
  - `https://campaign-planner-service.onrender.com`
  - `https://analytics-service.onrender.com`

### Render scaling and plan limitations

- Every service in `render.yaml` is configured with `plan: free`.
- Free-tier web services are convenient for preview/staging-style deployments, but they are not ideal for latency-sensitive production workloads.
- The gateway includes warmup logic, which strongly suggests the deployment is compensating for cold-start behavior on low-cost/free hosting.
- The current Render manifest does not include:
  - a Redis instance
  - a Celery worker
  - Flower

For a fully reproducible production backend, those missing services should also be provisioned on Render or through equivalent external infrastructure.

## 4. Database Setup (Neon)

### Database model

- The code expects a single PostgreSQL connection string in `DATABASE_URL`.
- SQLAlchemy initialization is in [`services/shared/database.py`](d:/marketing-app-main/services/shared/database.py):

```python
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

- All services use the same shared models and the same database.

### Neon guidance

- Neon is a serverless PostgreSQL platform with autoscaling and connection string-based access.
- In production, `DATABASE_URL` should be a Neon-issued connection string.
- Keep `DATABASE_URL` in Render environment variables only. Never commit it to the repo.

Typical structure:

```text
postgresql://<user>:<password>@<host>/<database>?sslmode=require
```

For Neon, the exact host, database name, and optional pooling suffix come from the Neon dashboard.

### Migrations

Alembic is configured in [`alembic/env.py`](d:/marketing-app-main/alembic/env.py):

- `DATABASE_URL` is mandatory for migrations.
- Alembic refuses to run without it.
- Migrations use `pool.NullPool`, which avoids persistent migration-time pooling.

Run migrations with:

```bash
set DATABASE_URL=<your-neon-url>
alembic upgrade head
```

PowerShell:

```powershell
$env:DATABASE_URL="<your-neon-url>"
alembic upgrade head
```

### Initialization and seeding

Optional initialization script:

- [`services/init_db.py`](d:/marketing-app-main/services/init_db.py)

It can:

- create tables through shared metadata
- seed feature matrix data
- seed continent master data
- optionally seed an org/admin/license if `ENABLE_SEED_DATA=true`

### Pooling and performance considerations

- The current application code uses `create_engine(DATABASE_URL)` with no explicit pool tuning.
- For Neon, use Neon’s recommended pooled connection endpoint when concurrency grows or when many Render services share one database.
- Use SSL-enabled connection strings and keep connection counts under control, especially with multiple always-on services.

## 5. Frontend Deployment (Vercel)

### Current frontend behavior

Frontend API routing is hard-coded in [`frontend/config.js`](d:/marketing-app-main/frontend/config.js):

- Production/default gateway:
  - `https://api-gateway-1ug2.onrender.com`
- Local override:
  - `http://localhost:8000`

This is not currently driven by a Vercel environment variable; it is embedded in the frontend code.

### Deployment model

- The frontend is a static HTML/CSS/JS app in `frontend/`.
- No Vercel config file is present in the repo.
- The most likely deployment shape is Git-based Vercel deployment pointing at the frontend output as static files.
- Because there is no build pipeline config in-repo, the deployment should be treated as a static-site import unless the Vercel project has dashboard-only settings.

### CORS

The API gateway allows:

- localhost development origins
- any `https://*.vercel.app` origin
- fallback/default explicit origin:
  - `https://mai-by-ai-marketer-v2.vercel.app`

That behavior is implemented in [`api_gateway/main.py`](d:/marketing-app-main/api_gateway/main.py).

## 6. Environment Variables

This section consolidates variables from `.env.example`, `docker-compose.yml`, and service configs. Values below are names and purposes only.

### Core

- `ENV`
  - Purpose: runtime mode such as development or staging.
  - Used in: auth validation rules, strategy provider boot behavior, Celery logging, seed behavior.
- `DATABASE_URL`
  - Purpose: shared PostgreSQL connection string.
  - Used in: all backend services, SQLAlchemy, Alembic, init script.
- `REDIS_URL`
  - Purpose: Redis location for Celery and related components.
  - Used in: `services/shared/celery_app.py`, Docker Compose worker/Flower.
- `CELERY_BROKER_URL`
  - Purpose: Celery broker endpoint.
  - Used in: `services/shared/celery_app.py`.
- `CELERY_RESULT_BACKEND`
  - Purpose: Celery result store.
  - Used in: `services/shared/celery_app.py`.
- `JWT_SECRET_KEY`
  - Purpose: JWT signing secret and fallback API key encryption derivation source.
  - Used in: `services/shared/auth.py`, `services/shared/api_keys.py`, all authenticated services.
- `JWT_EXPIRE_MINUTES`
  - Purpose: token TTL in minutes.
  - Used in: `services/shared/auth.py`.
- `LOG_LEVEL`
  - Purpose: logging verbosity.
  - Used in: strategy service startup/logging.
- `CONFIG_DIR`
  - Purpose: path to config JSON files.
  - Used in: `services/shared/config.py`, strategy service on Render.
- `API_KEY_ENCRYPTION_KEY`
  - Purpose: explicit key for encrypting org-scoped provider keys.
  - Used in: `services/shared/api_keys.py`.
- `ENABLE_SEED_DATA`
  - Purpose: enable optional seed data initialization.
  - Used in: `services/init_db.py`.
- `SEED_ORG_NAME`
  - Purpose: seed organization name.
  - Used in: `services/init_db.py`.
- `SEED_ADMIN_USER_ID`
  - Purpose: seed admin login ID.
  - Used in: `services/init_db.py`.
- `SEED_ADMIN_PASSWORD`
  - Purpose: seed admin password.
  - Used in: `services/init_db.py`.
- `SEED_LICENSE_TYPE`
  - Purpose: seed license type.
  - Used in: `services/init_db.py`.
- `SEED_LICENSE_PERIOD`
  - Purpose: seed license period.
  - Used in: `services/init_db.py`.
- `SEED_MAX_USERS`
  - Purpose: seed max user count.
  - Used in: `services/init_db.py`.

### AI providers

- `LLM_PROVIDER`
  - Purpose: choose provider mode, including `ollama_cloud`.
  - Used in: `services/shared/strategy_providers.py`, Render strategy service config.
- `STRATEGY_PROVIDER`
  - Purpose: strategy provider selection or fallback mode.
  - Used in: `services/shared/strategy_providers.py`, strategy service provider reporting.
- `OLLAMA_BASE_URL`
  - Purpose: Ollama endpoint, local or cloud.
  - Used in: `services/shared/strategy_providers.py`, strategy service startup checks.
- `OLLAMA_API_KEY`
  - Purpose: auth for Ollama cloud mode.
  - Used in: `services/shared/strategy_providers.py`.
- `MODEL_NAME`
  - Purpose: cloud/default model selection.
  - Used in: `services/shared/strategy_providers.py`.
- `REQUEST_TIMEOUT`
  - Purpose: request timeout for strategy provider calls.
  - Used in: `services/shared/strategy_providers.py`.
- `OLLAMA_TIMEOUT`
  - Purpose: Ollama-specific timeout.
  - Used in: `services/shared/strategy_providers.py`.
- `OLLAMA_STRATEGY_MODEL`
  - Purpose: local Ollama model name.
  - Used in: `services/shared/strategy_providers.py`, strategy provider reporting.
- `OPENAI_API_KEY`
  - Purpose: OpenAI auth.
  - Used in: strategy providers and browser-extension lead enhancement.
- `OPENAI_MODEL`
  - Purpose: OpenAI model name.
  - Used in: strategy providers, browser-extension lead enhancement.
- `OPENAI_MAX_TOKENS`
  - Purpose: output cap for OpenAI strategy responses.
  - Used in: `services/shared/strategy_providers.py`.
- `OPENAI_BASE_URL`
  - Purpose: OpenAI-compatible API base URL.
  - Used in: strategy providers, browser-extension lead enhancement.

### Lead scraping and enrichment providers

- `GITHUB_API_TOKEN`
  - Purpose: GitHub provider token fallback for lead operations.
  - Declared in: `.env.example`, `docker-compose.yml`, `render.yaml`.
- `GOOGLE_MAPS_API_KEY`
  - Purpose: Google Maps Places API access.
  - Used in: `services/lead_enrichment_service/providers/google_maps_provider.py`.
- `LINKEDIN_API_KEY`
  - Purpose: LinkedIn/Serp-based provider fallback key.
  - Used in: `services/lead_enrichment_service/providers/linkedin_provider.py`.
- `SERPAPI_API_KEY`
  - Purpose: alternate key path for LinkedIn scraping/enrichment.
  - Used in: `services/lead_enrichment_service/providers/linkedin_provider.py`.
- `VOLZA_API_KEY`
  - Purpose: reserved for Volza integration.
  - Declared in env/config, but provider is currently unavailable.
- `CLEARBIT_API_KEY`
  - Purpose: enrichment provider credential.
  - Declared in env/config and Render.
- `HUNTER_IO_API_KEY`
  - Purpose: enrichment provider credential.
  - Declared in env/config and Render.
- `HUNTER_API_KEY`
  - Purpose: email enrichment provider lookup key name used in code.
  - Used in: `services/lead_enrichment_service/providers/email_provider.py`.
- `OUTSCRAPER_API_KEY`
  - Purpose: enrichment provider credential.
  - Declared in env/config and Render.

### Email providers

- `EMAIL_PROVIDER`
  - Purpose: choose `mailhog`, `gmail`, or `mailrelay`.
  - Used in: `services/campaign_planner_service/email_provider_factory.py`.
- `EMAIL_FROM`
  - Purpose: sender email address override.
  - Used in: SMTP-based email providers.
- `EMAIL_FROM_NAME`
  - Purpose: sender display name.
  - Used in: SMTP-based email providers.
- `EMAIL_MAX_RETRIES`
  - Purpose: email retry count.
  - Used in: `services/campaign_planner_service/email_service.py`.
- `EMAIL_RETRY_BASE_DELAY_SECONDS`
  - Purpose: retry backoff base.
  - Used in: `services/campaign_planner_service/email_service.py`.
- `EMAIL_VALIDATE_MX`
  - Purpose: optional MX validation toggle.
  - Used in: `services/campaign_planner_service/email_service.py`.
- `EMAIL_COMPANY_NAME`
  - Purpose: branding in generated email templates.
  - Used in: `services/campaign_planner_service/email_service.py`.
- `EMAIL_USER`
  - Purpose: generic SMTP username fallback.
  - Used in: Gmail provider.
- `EMAIL_PASSWORD`
  - Purpose: generic SMTP password fallback.
  - Used in: Gmail provider.
- `GMAIL_SMTP_HOST`
  - Purpose: Gmail SMTP host.
  - Used in: `gmail_provider.py`.
- `GMAIL_SMTP_PORT`
  - Purpose: Gmail SMTP port.
  - Used in: `gmail_provider.py`.
- `GMAIL_SMTP_USER`
  - Purpose: Gmail SMTP username.
  - Used in: `gmail_provider.py`.
- `GMAIL_SMTP_PASSWORD`
  - Purpose: Gmail SMTP password.
  - Used in: `gmail_provider.py`.
- `MAILHOG_SMTP_HOST`
  - Purpose: MailHog SMTP host.
  - Used in: `mailhog_provider.py`.
- `MAILHOG_SMTP_PORT`
  - Purpose: MailHog SMTP port.
  - Used in: `mailhog_provider.py`.
- `MAILRELAY_SMTP_HOST`
  - Purpose: Mailrelay SMTP host.
  - Used in: `mailrelay_provider.py`.
- `MAILRELAY_SMTP_PORT`
  - Purpose: Mailrelay SMTP port.
  - Used in: `mailrelay_provider.py`.
- `MAILRELAY_SMTP_USER`
  - Purpose: Mailrelay SMTP username.
  - Used in: `mailrelay_provider.py`.
- `MAILRELAY_SMTP_PASSWORD`
  - Purpose: Mailrelay SMTP password.
  - Used in: `mailrelay_provider.py`.
- `MAILRELAY_FROM_EMAIL`
  - Purpose: Mailrelay sender address.
  - Used in: `mailrelay_provider.py`.
- `MAILRELAY_FROM_NAME`
  - Purpose: Mailrelay sender name.
  - Used in: `mailrelay_provider.py`.
- `MAILRELAY_API_BASE_URL`
  - Purpose: Mailrelay API base URL.
  - Used in: `mailrelay_provider.py`.
- `MAILRELAY_API_TOKEN`
  - Purpose: Mailrelay API auth token.
  - Used in: `mailrelay_provider.py`.
- `MAILRELAY_USE_API`
  - Purpose: toggle Mailrelay API mode before SMTP fallback.
  - Used in: `mailrelay_provider.py`.
- `SENDGRID_API_KEY`
  - Purpose: declared legacy/provider credential.
  - Present in env/config and Render campaign service.

### Social/channel provider tokens

- `FACEBOOK_ACCESS_TOKEN`
  - Purpose: reserved token for campaign dispatch/channel integration.
  - Declared in env/config and Render campaign service.
- `LINKEDIN_ACCESS_TOKEN`
  - Purpose: reserved token for campaign dispatch/channel integration.
  - Declared in env/config and Render campaign service.
- `TWITTER_ACCESS_TOKEN`
  - Purpose: reserved token for campaign dispatch/channel integration.
  - Declared in env/config and Render campaign service.
- `WHATSAPP_ACCESS_TOKEN`
  - Purpose: reserved token for campaign dispatch/channel integration.
  - Declared in env/config and Render campaign service.

### Gateway and service routing

- `AUTH_SERVICE_URL`
  - Purpose: gateway upstream for auth requests.
  - Used in: `api_gateway/main.py`.
- `LICENSING_SERVICE_URL`
  - Purpose: gateway upstream for licensing requests.
  - Used in: `api_gateway/main.py`.
- `STRATEGY_SERVICE_URL`
  - Purpose: gateway upstream for strategy requests.
  - Used in: `api_gateway/main.py`.
- `LEAD_SERVICE_URL`
  - Purpose: gateway upstream for lead requests and direct campaign service lead lookup.
  - Used in: `api_gateway/main.py`, `services/campaign_planner_service/main.py`.
- `CAMPAIGN_SERVICE_URL`
  - Purpose: gateway upstream for campaign requests.
  - Used in: `api_gateway/main.py`.
- `ANALYTICS_SERVICE_URL`
  - Purpose: gateway upstream for analytics requests.
  - Used in: `api_gateway/main.py`.
- `CAMPAIGN_IDEMPOTENCY_TTL_SECONDS`
  - Purpose: TTL for in-memory idempotency cache.
  - Used in: `services/campaign_planner_service/main.py`.

### Frontend config

- No dedicated frontend environment-variable system is implemented in-repo.
- Production API base URL is hard-coded in:
  - [`frontend/config.js`](d:/marketing-app-main/frontend/config.js)
- Current values:
  - production: `https://api-gateway-1ug2.onrender.com`
  - local: `http://localhost:8000`

## 7. Service Endpoints

### Public frontend

- Vercel frontend
  - Deployed Vercel URL is not defined in repository config.
  - Gateway CORS code explicitly recognizes `https://mai-by-ai-marketer-v2.vercel.app` and `*.vercel.app`.

### API Gateway

- Base URL
  - `https://api-gateway-1ug2.onrender.com`
- Health
  - `https://api-gateway-1ug2.onrender.com/health`
- Docs
  - `https://api-gateway-1ug2.onrender.com/docs`

### Auth Service

- Base URL
  - `https://auth-service-5glt.onrender.com`
- Health
  - `https://auth-service-5glt.onrender.com/api/health`
- Docs
  - `https://auth-service-5glt.onrender.com/docs`

### Licensing Service

- Base URL
  - `hhttps://licensing-service-vboy.onrender.com`
- Health
  - `https://licensing-service-vboy.onrender.com/api/health`
- Docs
  - `https://licensing-service-vboy.onrender.com/docs`

### Strategy AI Service

- Base URL
  - `https://strategy-ai-service.onrender.com`
- Health
  - `https://strategy-ai-service.onrender.com/api/health`
- Basic health
  - `https://strategy-ai-service.onrender.com/health`
- Docs
  - `https://strategy-ai-service.onrender.com/docs`

### Lead Enrichment Service

- Base URL
  - `https://lead-enrichment-service.onrender.com`
- Health
  - `https://lead-enrichment-service.onrender.com/api/health`
- Docs
  - `https://lead-enrichment-service.onrender.com/docs`

### Campaign Planner Service

- Base URL
  - `https://campaign-planner-service.onrender.com`
- Health
  - `https://campaign-planner-service.onrender.com/api/health`
- Docs
  - `https://campaign-planner-service.onrender.com/docs`

### Analytics Service

- Base URL
  - `https://analytics-service-d851.onrender.com`
- Health
  - `https://analytics-service-d851.onrender.com/api/health`
- Docs
  - `https://analytics-service-d851.onrender.com/docs`

## 8. Deployment Steps

### Backend (Render)

1. Push the repository to GitHub.
2. In Render, create a Blueprint deployment from the repo.
3. Use [`render.yaml`](d:/marketing-app-main/render.yaml) as the source of service definitions.
4. Create or update the following required secrets in Render:
   - `DATABASE_URL`
   - `JWT_SECRET_KEY`
   - provider keys required by the services you plan to use
5. Verify `SERVICE_COMMAND` is present for every service from the blueprint.
6. Deploy the seven web services.
7. Add or provision the missing production dependencies not defined in `render.yaml`:
   - Redis
   - Celery worker service
   - optional Flower monitoring service
8. If campaigns must be scheduled reliably, deploy a dedicated worker using:

```bash
celery -A services.shared.celery_app worker --loglevel=info
```

### Database (Neon)

1. Create a Neon project and database.
2. Copy the connection string from Neon.
3. Store it as `DATABASE_URL` in Render.
4. Ensure the connection string uses Neon’s recommended SSL settings.
5. Run migrations:

```bash
alembic upgrade head
```

6. Optionally run initialization/seeding:

```bash
python services/init_db.py
```

### Frontend (Vercel)

1. Import the repository into Vercel.
2. Configure the project as a static frontend deployment rooted at the frontend files, or use the dashboard build/output settings already in use for the project.
3. Confirm the frontend serves the app files from `frontend/`.
4. If you want environment-driven API routing in the future, refactor `frontend/config.js`; currently the production gateway URL is hard-coded.
5. Deploy and verify the frontend can call the Render gateway.

## 9. Verification Checklist

### Health checks

- Gateway:
  - `GET /health`
- Services:
  - `GET /api/health`

### Docs availability

- Confirm `/docs` loads on:
  - gateway
  - auth
  - licensing
  - strategy
  - lead enrichment
  - campaign planner
  - analytics

### Frontend connectivity

- Load the Vercel frontend.
- Open the browser network tab.
- Confirm API requests are going to `https://api-gateway-1ug2.onrender.com`.
- Confirm CORS headers are present and requests are not blocked.

### Authentication

- Call `POST /api/auth/org-login` through the frontend or gateway.
- Confirm a JWT is returned and stored client-side.
- Confirm protected routes work after login.

### Database validation

- Run `alembic upgrade head` successfully against Neon.
- Verify strategies, campaigns, or admin entities can be created and persisted.
- Confirm all services using `DATABASE_URL` can start cleanly.

### Background job validation

- Launch a campaign and confirm campaign execution updates persisted campaign status/metrics.
- If scheduled campaigns are required, verify a Celery worker and Redis are actually running in production.

## 10. Known Limitations

- `render.yaml` currently provisions only web services. It does not provision Redis, Celery worker, or Flower.
- Lead scraping and enrichment are still handled with FastAPI `BackgroundTasks`, which are not durable across restarts.
- Campaign execution is Celery-ready, but reliable production scheduling depends on infrastructure that is not fully defined in the Render blueprint.
- All Render web services are set to `plan: free`, which is not ideal for production latency and availability.
- SQLAlchemy engine configuration does not currently include explicit Neon-oriented pool tuning or connection limit safeguards.
- Frontend production API URL is hard-coded in `frontend/config.js`, which is workable but less flexible than env-based configuration.
- Engagement metrics such as opens, clicks, and conversions are not fully implemented with production-grade tracking/webhook ingestion.
- Volza integration is declared but not implemented.

## 11. Best Practices

- Keep all secrets in environment variables only. Never hardcode credentials in code or config files.
- Use a strong `JWT_SECRET_KEY`; the auth layer explicitly rejects insecure defaults outside development.
- Store the Neon connection string in `DATABASE_URL` and rotate it through your deployment platform, not through source control.
- Prefer Neon’s pooled connection endpoint when service count or concurrency increases.
- Use SSL-enabled Neon URLs and monitor connection usage closely when many microservices share one database.
- Run Alembic migrations before or during deployment in a controlled release step.
- Treat Render Blueprint config as infrastructure-as-code, but extend it to include Redis and a dedicated worker for true production readiness.
- Use Vercel’s Git-based deployment flow so pushes to the deployment branch produce repeatable frontend releases.
- Keep frontend-to-gateway origin handling aligned with gateway CORS rules whenever Vercel domains change.
- Separate local-only safety providers from production providers:
  - MailHog for local/dev
  - Mailrelay or Gmail only when properly configured
- Add monitoring around:
  - gateway health
  - DB connectivity
  - worker availability
  - email failures
  - provider rate limits and fallbacks
