# MAi by AIMarketer

MAi is a multi-service B2B marketing platform that takes an organization from business profiling to AI strategy generation, lead discovery, customer data enrichment, campaign execution, and analytics. The active system is a FastAPI microservice stack behind a single API gateway, with a static frontend and an optional Chrome extension for website lead capture.

## Overview

- Built for B2B teams that want a single workflow for strategy, lead generation, enrichment, outreach, and reporting.
- Supports organization-first authentication, license-based feature access, and admin controls for users, licenses, organizations, and provider API keys.
- Uses code-backed strategy versioning, campaign persistence, multi-source lead ingestion, and provider-based email delivery.

## Architecture

High-level flow:

`Frontend / Browser Extension -> API Gateway -> FastAPI services -> PostgreSQL / Redis / Celery / external APIs`

### Components

- `frontend/`
  - Static HTML/CSS/JS application.
  - Uses `frontend/config.js` to talk to the API gateway locally or to the deployed Render gateway.
  - Includes a standalone demo UI in `frontend/standalone.html`.
- `api_gateway/`
  - Reverse proxy for all `/api/{service}` routes.
  - Adds CORS handling, retries, startup connectivity checks, and periodic health warmup.
- `services/auth_service/`
  - Org-first login.
  - JWT issuance, session invalidation, RBAC, org/user/license CRUD, and org-scoped API key management.
- `services/licensing_service/`
  - Feature validation and license status APIs.
- `services/strategy_ai_service/`
  - Strategy generation, provider selection, provider diagnostics, master data, strategy history, and version retrieval.
- `services/lead_enrichment_service/`
  - Lead scraping, browser-extension and direct-URL ingestion, CSV/XLSX enrichment, task tracking, and provider usage audit logging.
- `services/campaign_planner_service/`
  - Campaign creation, strategy-to-campaign auto-mapping, scheduling, launch/pause/resume/stop/delete flows, and provider-based email sending.
- `services/analytics_service/`
  - Campaign, lead, report, and strategy performance analytics.
- `services/shared/`
  - Shared SQLAlchemy models, auth helpers, Celery app, config loading, and encrypted org API key helpers.
- `lead-scraper-extension/`
  - Chrome extension that extracts headings, links, contacts, and table-like content from pages and pushes payloads into the web app.

### Data and infrastructure

- PostgreSQL is the active system of record for organizations, users, licenses, strategies, strategy versions, campaigns, metrics, lead tasks, scrape results, enrichment tasks, enrichment rows, org API keys, and API usage audits.
- Redis is used by Celery for broker/result backend.
- Celery currently handles campaign execution and scheduled delivery.
- Docker Compose also provisions MailHog, Flower, pgAdmin, PostgreSQL, Redis, and optional Ollama.

## Tech Stack

- Backend: Python 3.11, FastAPI, Uvicorn, SQLAlchemy, Alembic
- Auth/security: JWT (`python-jose`), Passlib bcrypt
- Async/background: Celery, Redis, FastAPI `BackgroundTasks`
- Data processing: Pandas, OpenPyXL, NumPy
- AI providers: Ollama local, Ollama cloud, OpenAI
- Scraping/enrichment: Playwright, httpx, provider-based enrichment/scraping
- Frontend: static HTML, CSS, vanilla JavaScript, Chart.js
- Deployment: Docker Compose, Render (`render.yaml`), Vercel-friendly frontend CORS/gateway setup
- Testing: pytest, pytest-asyncio

## Features

### Core Features

- Organization-first authentication with JWT-based sessions and logout invalidation.
- License-based feature gating across strategy, lead enrichment, campaign planner, analytics, and templates.
- AI marketing strategy generation with persistence and version history.
- Lead scraping tasks with organization scoping and task/result persistence.
- Customer CSV/XLSX enrichment with preview, column mapping, and task tracking.
- Multi-channel campaign management with campaign CRUD, scheduling, launch, lifecycle controls, and metrics.
- Analytics dashboards for campaign summaries, lead metrics, and strategy-linked performance.
- Admin dashboard support for users, licenses, provider API keys, and organizations.

### Recently Added Features

- Provider-based strategy generation with `ollama`, `ollama_cloud`, `openai`, and `auto` selection.
- Strategy history and version retrieval APIs backed by `strategies` and `strategy_versions`.
- Multi-source lead scraping with `github`, `google_maps`, `linkedin`, `browser_extension`, and `direct_url` providers.
- Browser extension ingestion and Playwright-powered direct URL scraping.
- Organization-scoped encrypted API key storage and provider usage audit logging.
- Campaign manager v2 workflow improvements: strategy linkage, version linkage, schedule/start/end dates, explicit pause/resume/stop/delete actions, and idempotent campaign creation.
- Provider-based email system with MailHog, Gmail, and Mailrelay, including retry and recipient validation.
- Strategy-to-campaign auto-mapping for channels, target audience, budget, schedule window, content strategy, and KPI metadata.
- Analytics support for strategy performance by strategy version.
- Frontend upgrades including autosuggest inputs, accessible loading states, strategy history/version selectors, admin dashboard UI, and improved campaign cards/status badges.

## Project Structure

```text
.
|-- api_gateway/                    # Gateway / reverse proxy
|-- services/
|   |-- auth_service/              # Auth, RBAC, org/user/license/API key admin
|   |-- licensing_service/         # License validation/status
|   |-- strategy_ai_service/       # Strategy generation + history/versioning
|   |-- lead_enrichment_service/   # Lead scraping + enrichment + provider integrations
|   |-- campaign_planner_service/  # Campaign lifecycle + email delivery + scheduling
|   |-- analytics_service/         # Analytics/reporting APIs
|   `-- shared/                    # Shared DB models, auth, config, Celery, helpers
|-- frontend/                      # Static frontend and standalone demo
|-- lead-scraper-extension/        # Chrome extension for website lead extraction
|-- alembic/                       # Database migrations
|-- config/                        # JSON config for channels, budgets, KPIs, etc.
|-- docs/                          # Supplemental design notes and audits
|-- scripts/                       # Local run/setup helpers
|-- tests/                         # Email provider and email service tests
|-- docker-compose.yml             # Full local stack
|-- docker-compose.staging.yml     # Staging overlay for strategy provider config
|-- Dockerfile                     # Shared image for services
`-- render.yaml                    # Render deployment definitions
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- Docker Desktop and Docker Compose for the easiest local setup
- Optional:
  - Ollama for local strategy generation
  - Playwright browser binaries for direct URL scraping
  - Mailrelay/Gmail credentials for non-local email delivery

### Environment Variables

Use `.env.example` as the current baseline. Key variables:

- Core
  - `ENV`
  - `DATABASE_URL`
  - `REDIS_URL`
  - `CELERY_BROKER_URL`
  - `CELERY_RESULT_BACKEND`
  - `JWT_SECRET_KEY`
  - `JWT_EXPIRE_MINUTES`
  - `LOG_LEVEL`
  - `CONFIG_DIR`
- Strategy providers
  - `LLM_PROVIDER`
  - `STRATEGY_PROVIDER`
  - `OLLAMA_BASE_URL`
  - `OLLAMA_API_KEY`
  - `MODEL_NAME`
  - `REQUEST_TIMEOUT`
  - `OLLAMA_TIMEOUT`
  - `OLLAMA_STRATEGY_MODEL`
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`
  - `OPENAI_MAX_TOKENS`
  - `OPENAI_BASE_URL`
- Lead/enrichment providers
  - `GITHUB_API_TOKEN`
  - `GOOGLE_MAPS_API_KEY`
  - `LINKEDIN_API_KEY`
  - `VOLZA_API_KEY`
  - `CLEARBIT_API_KEY`
  - `HUNTER_IO_API_KEY`
  - `OUTSCRAPER_API_KEY`
- Email delivery
  - `EMAIL_PROVIDER`
  - `EMAIL_FROM`
  - `EMAIL_FROM_NAME`
  - `EMAIL_MAX_RETRIES`
  - `EMAIL_RETRY_BASE_DELAY_SECONDS`
  - `EMAIL_VALIDATE_MX`
  - `EMAIL_COMPANY_NAME`
  - `GMAIL_SMTP_*`
  - `MAILHOG_SMTP_*`
  - `MAILRELAY_SMTP_*`
  - `MAILRELAY_API_BASE_URL`
  - `MAILRELAY_API_TOKEN`
  - `MAILRELAY_USE_API`
- Seeding
  - `ENABLE_SEED_DATA`
  - `SEED_ORG_NAME`
  - `SEED_ADMIN_USER_ID`
  - `SEED_ADMIN_PASSWORD`
  - `SEED_LICENSE_TYPE`
  - `SEED_LICENSE_PERIOD`
  - `SEED_MAX_USERS`
- Optional security helper
  - `API_KEY_ENCRYPTION_KEY`
    - Optional. If omitted, org API key encryption is derived from `JWT_SECRET_KEY`.

### Local Development

#### Option A: Docker Compose

1. Copy `.env.example` to `.env` and fill required values.
2. Start the stack:

```bash
docker compose up --build
```

3. Optional services:

```bash
docker compose --profile local-llm up ollama -d
docker compose --profile init up init_db
```

4. Access points:
  - API gateway: `http://localhost:8000`
  - Service docs: ports `8001` to `8006`
  - MailHog UI: `http://localhost:8025`
  - Flower: `http://localhost:5555`
  - pgAdmin: `http://localhost:5050`

#### Option B: Run services directly

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure `.env`.
4. Run database migrations and/or initialization:

```bash
alembic upgrade head
python services/init_db.py
```

5. Start services with the helper script:

```bash
powershell -ExecutionPolicy Bypass -File scripts/run_local.ps1
```

or

```bash
bash scripts/run_local.sh
```

6. Serve the frontend from `frontend/` with a static server, for example:

```bash
cd frontend
python -m http.server 5500
```

The frontend is configured to use `http://localhost:8000` when opened locally on a non-gateway port.

### Docker Setup

- `docker-compose.yml` is the main local environment.
- `docker-compose.staging.yml` overrides strategy provider settings for staging-style Ollama cloud usage.
- The shared `Dockerfile` is used by most services; `services/lead_enrichment_service/Dockerfile` is the lead service-specific image path in Compose.

### Production Deployment

- `render.yaml` defines separate Render web services for:
  - `auth-service`
  - `licensing-service`
  - `strategy-ai-service`
  - `lead-enrichment-service`
  - `campaign-planner-service`
  - `analytics-service`
  - `api-gateway`
- Each service runs from the shared Docker image with a `SERVICE_COMMAND`.
- The frontend is set up to work with a deployed gateway URL and Vercel origins.
- For production, provide strong `JWT_SECRET_KEY`, a real `DATABASE_URL`, Redis for Celery, and real provider credentials.

## API / System Flow

1. User logs in through `POST /api/auth/org-login`.
2. Frontend stores the JWT and calls the API gateway.
3. The gateway proxies requests to the appropriate microservice.
4. Services validate JWTs and gate routes by licensed feature.
5. Strategy generation persists a strategy plus a new strategy version.
6. Lead scraping creates a task, runs provider scraping in background, stores results/source runs, and exposes task APIs.
7. Customer enrichment uploads create enrichment tasks and rows, then enrich records provider-by-provider.
8. Campaign creation persists campaigns and metrics; scheduled campaigns are enqueued via Celery, while explicit launches execute immediately.
9. Analytics reads persisted campaigns, metrics, leads, enrichment rows, strategies, and versions to produce dashboard/report payloads.

## Integrations

- AI/LLM: Ollama local, Ollama cloud, OpenAI
- Lead sources/enrichment: GitHub API, Google Maps Places API, SerpAPI/LinkedIn search, browser extension payloads, Playwright direct URL scraping
- Email: MailHog, Gmail SMTP, Mailrelay SMTP/API
- Infra: PostgreSQL, Redis, Celery, Flower, pgAdmin
- Deployment/runtime: Render, Vercel-compatible frontend origins

## Known Issues / Limitations

- Lead scraping and enrichment use FastAPI `BackgroundTasks`, so those jobs are not durable across service restarts. Only campaign execution is currently Celery-backed.
- `_record_usage()` in the lead enrichment service is still a TODO, so usage tracking is incomplete.
- Campaign engagement metrics are mostly placeholders today: sent counts update, but opens/clicks/conversions are not yet populated by real tracking/webhooks.
- `VolzaProvider` is stubbed and returns `unavailable` until API access is implemented.
- Google Maps and LinkedIn scraping can fall back to mock/sample data when provider keys are missing; this is useful for demos but not production-grade lead quality.
- MongoDB appears in legacy docs and Docker Compose, but the active code paths rely on PostgreSQL and do not currently use Mongo-backed data flows.
- Direct URL scraping requires Playwright and installed browser binaries.
- API usage alert emails in lead scraping are routed through MailHog host assumptions in the current implementation.

## Improvements Made Recently

- Replaced legacy synchronous/local-only email sending with provider-based email delivery and retry handling.
- Added strategy persistence, versioning, history APIs, and strategy-linked campaign analytics.
- Added org-scoped encrypted provider API key storage plus admin UI support.
- Added browser-extension and Playwright-based website scraping flows.
- Added campaign lifecycle controls (`schedule`, `launch`, `pause`, `resume`, `stop`, `delete`) and idempotent create flows.
- Added master-data endpoints for continents and business categories.
- Added frontend autosuggest, strategy version selection, admin dashboard sections, and strategy-to-execution flow improvements.

## Future Improvements

- Move lead scraping and enrichment to Celery for durable job execution.
- Implement real usage tracking and quota enforcement.
- Add webhook/event ingestion for email engagement metrics.
- Finish Volza integration.
- Remove or formally retire unused MongoDB setup paths if they are no longer part of the product direction.

## Testing

Run the existing tests with:

```bash
pytest
```

Current automated coverage in-repo is focused on the email provider factory and campaign email validation/sending flow.
