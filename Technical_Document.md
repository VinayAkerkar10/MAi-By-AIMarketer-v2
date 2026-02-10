# MAi by AIMarketer: Technical Documentation

## 1. Overview

**MAi by AIMarketer** is an AI-powered B2B Digital Marketing Platform designed to help businesses create intelligent, data-driven marketing strategies, enhance leads, and execute automated multi-channel campaigns. The app streamlines the process from business profiling and strategy recommendation through to campaign management, analytics, and enriched lead generation.

The active backend is the microservice stack fronted by the API Gateway. The API Gateway (port 8000) is the canonical entry point for all backend requests.

Legacy monolith endpoints and flows described below are deprecated and kept for reference only; where applicable, gateway paths are noted.

## 2. System Architecture

### 2.1 Backend

- **Framework:** FastAPI (Python 3.10+)
- **AI/ML Libraries:**
  - OpenAI GPT API (strategy and content generation)
  - Scikit-learn, TensorFlow (analytics and segmentation)
  - Pandas (data manipulation)
- **Task Queue:** Celery + Redis (asynchronous tasks—scraping, enrichment)
- **Databases:**
  - PostgreSQL (structured data)
  - MongoDB (unstructured and content blobs)
  - Redis (caching/session)
- **Deployment:** Docker containers, cloud services (AWS Lambda, Google Cloud Run, Kubernetes compatible)

### 2.2 Frontend

- **Prototype UI:** Streamlit (rapid MVP/prototype)
- **Production Ready:** React (Material-UI/Ant Design)
- **Hosting:** Vercel, Netlify, AWS Amplify

## 3. Modules & Features

**Note:** API paths listed in this section reflect legacy monolith routes (deprecated/reference-only). Use the API Gateway (`/api/{service}/{path}`) for the active backend.

### 3.1 User & Business Input

- Capture detailed business profile, objectives, and target audience.
- **Legacy API (deprecated):** `POST /business-profile`
- **Gateway (active):** Use `POST /api/strategy/generate` with `business_profile` payload
- **UI:** Forms with validation and helper text.

### 3.2 Strategy Generation

- Leverages GPT & ML for campaign/channel/timing/budget recommendations.
- **Legacy API (deprecated):** `POST /generate-strategy`
- **Gateway (active):** `POST /api/strategy/generate`
- **Frontend:** Dashboard showing actionable strategies and export options.

### 3.3 Google Maps Lead Scraper

- Automates B2B lead extraction (business name, address, phone, email, etc.).
- **Backend:** Celery + Selenium or third-party APIs (Outscraper, Apify)
- **Legacy APIs (deprecated):** `POST /scrape-leads`, `GET /get-leads`
- **Gateway (active):** `POST /api/leads/scrape` and `/api/leads/*`
- **Frontend:** Lead tables, exports (CSV/XLSX).

### 3.4 Customer Data Upload & Enrichment

- User uploads CRM or lead lists (CSV, XLSX).
- Asynchronous enrichment using Clearbit, Hunter.io, FullContact APIs, with fallback to Google Maps scraping.
- **Data Added:** Emails, phones, sites, social handles, company/industry info.
- **Legacy APIs (deprecated):** `POST /upload-customers`, `GET /enrichment-status`, `GET /download-enriched`
- **Gateway (active):** `/api/enrichment/*`
- **Frontend:** Table preview, download, campaign import.

### 3.5 Multi-Channel Campaign Manager

- Social (Facebook, Instagram, LinkedIn, Twitter/X), WhatsApp, Email (SMTP/Mailchimp/SendGrid/HubSpot).
- Create, schedule, send, and log campaigns from one place.
- **Legacy APIs (deprecated):** `POST /create-campaign`, `POST /schedule-campaign`, `GET /campaign-status`
- **Gateway (active):** `/api/campaigns/*`
- **Frontend:** Campaign wizard, log/status dashboard, content management.

### 3.6 Analytics & Reporting

- KPI dashboards: campaign performance, lead status, ROI, attribution models.
- Downloadable reports (CSV/PDF), scheduled emails.
- **Legacy APIs (deprecated):** `GET /campaign-metrics`, `GET /lead-metrics`, `GET /download-report`
- **Gateway (active):** `/api/analytics/*`
- **Frontend:** Analytics tables, charts, downloadable summaries.

### 3.7 Template Library (Optional)

- Editable assets for emails, posts, and channel-specific campaigns.
- Industry/channel wise templates in MongoDB.
- **Frontend:** Browse, edit, and apply templates.

## 4. Data Flow (Summary Diagram)

1. User inputs business info → AI strategy generator.  
2. Lead scraping/CRM upload → Data enrichment (APIs + scraping).  
3. Campaigns set up (assets, target lists) → Scheduled via API integrations.  
4. Analytics/metrics polled automatically; shown in dashboards.  

## 5. API Endpoints (Key)

**Legacy monolith endpoints (deprecated/reference-only).** Use the API Gateway on port 8000 for active routes.

| Endpoint               | Method | Description                                  | Gateway path (active) |
|------------------------|--------|----------------------------------------------|------------------------|
| `/login`               | POST   | Authenticate users                           | `/api/auth/org-login` |
| `/business-profile`    | POST   | Add/update business details                  | Use `/api/strategy/generate` with `business_profile` payload |
| `/generate-strategy`   | POST   | Get AI-driven marketing strategy             | `/api/strategy/generate` |
| `/scrape-leads`        | POST   | Start Google Maps-based lead scraping        | `/api/leads/scrape` |
| `/get-leads`           | GET    | Download/view scraped lead list              | `/api/leads/*` |
| `/upload-customers`    | POST   | Upload customer data for enrichment          | `/api/enrichment/*` |
| `/enrichment-status`   | GET    | Check enrichment progress                    | `/api/enrichment/*` |
| `/download-enriched`   | GET    | Download enriched data                       | `/api/enrichment/*` |
| `/create-campaign`     | POST   | New multi-channel campaign                   | `/api/campaigns/*` |
| `/schedule-campaign`   | POST   | Schedule campaign deployment                 | `/api/campaigns/*` |
| `/campaign-status`     | GET    | Get logs/status of campaigns                 | `/api/campaigns/*` |
| `/campaign-metrics`    | GET    | Pull campaign analytics                      | `/api/analytics/*` |
| `/lead-metrics`        | GET    | Lead analytics                               | `/api/analytics/*` |
| `/download-report`     | GET    | Download analytics/report                    | `/api/analytics/*` |

## 6. Security & Compliance

- JWT or OAuth2 authentication, role-based permissions.
- Data encrypted in transit (TLS) and at rest (AES-256).
- GDPR/CCPA compliant, with user consent and PII handling.
- API security (rate limiting, input validation, logging).

## 7. Development & Deployment Notes

- Everything is Dockerized—run locally or deploy with Compose/cloud.
- Celery for async jobs; Redis as broker and cache.
- Code standards: Use pytest for unit/integration testing, flake8/black for linting.
- Continuous Integration: Optional with GitHub Actions or similar.
- API auto-docs at `/docs` endpoint via OpenAPI/Swagger.

## 8. Extensibility & Roadmap

- Easily add new channels (API modularity).
- Flexible to support white-label and multi-tenant (SaaS) deployments.
- Future: Mobile app, advanced analytics, CRM integration, deeper AI modeling.

## 9. Setup Instructions (Summary)

Clone repo, copy `.env.sample` to `.env` and fill in API keys.  
Build/start with:  
Docs:  
- Backend OpenAPI/Swagger at `/docs`

## 10. Contact & Internal Support

- **API Documentation:** `/docs` endpoint  
- **Development Lead:** Mrityunjay Pandey  
- **Support:** See README in repo  

