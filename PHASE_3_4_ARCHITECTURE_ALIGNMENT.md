# Phase 3 and 4 Architecture Alignment

## Executive Summary

- This document covers Phase 3 and Phase 4 architecture alignment and is DESIGN-ONLY.
- No implementation changes are included.
- No database schemas are defined.
- No API renames are proposed.
- No business logic changes are proposed.
- This document is intended for architectural review and approval.

## Phase 3.1 – Persistence Design

**StrategyAI Service**
- Strategy (generated strategy payload, provider info, timestamps): PostgreSQL, owned by StrategyAI.
- StrategyHistory entry (organization-scoped record of strategy generations): PostgreSQL, owned by StrategyAI.
- BusinessProfile snapshot used for generation (stored with strategy/history): PostgreSQL, owned by StrategyAI.

**Lead Enrichment Service**
- LeadScrapeTask (search params, status, timestamps): PostgreSQL, owned by Lead Enrichment.
- Lead (scraped lead record linked to task and org): PostgreSQL, owned by Lead Enrichment.
- EnrichmentTask (upload metadata, status, counts, timestamps): PostgreSQL, owned by Lead Enrichment.
- EnrichedCustomerRecord (original + enriched fields linked to task and org): PostgreSQL, owned by Lead Enrichment.

**Campaign Planner Service**
- Campaign (definition, channels, content, budget, status, timestamps): PostgreSQL, owned by Campaign Planner.
- CampaignSchedule/Deployment status (scheduled/active/failed, timestamps): PostgreSQL, owned by Campaign Planner.
- CampaignAnalytics (impressions/clicks/conversions/ROI, etc.): PostgreSQL, owned by Campaign Planner.

**Analytics Service**
- CampaignMetricsAggregate (campaign-level analytics metrics): PostgreSQL, owned by Analytics.
- LeadMetricsAggregate (lead funnel/quality metrics): PostgreSQL, owned by Analytics.
- AnalyticsReport (report metadata and generated payload reference): PostgreSQL, owned by Analytics.

## Phase 3.2 – Frontend Integration Contract

**1. Org login**
- UI action name: Org login
- Current behavior: Simulated/static auth flow
- Target API Gateway endpoint: `/api/auth/org-login`
- HTTP method: `POST`
- High-level request payload: organization name, user ID, password
- High-level response shape: success flag, JWT token, user role, redirect path, active licenses

**2. Save business profile**
- UI action name: Save business profile
- Current behavior: Simulated/static (no persisted profile)
- Target API Gateway endpoint: `/api/strategy/generate`
- HTTP method: `POST`
- High-level request payload: `business_profile` fields (name, industry, size, geography, goals, budget, target audience) and optional `additional_context`
- High-level response shape: success flag, generated strategy object, next steps

**3. Generate strategy**
- UI action name: Generate strategy
- Current behavior: Simulated/static strategy generation
- Target API Gateway endpoint: `/api/strategy/generate`
- HTTP method: `POST`
- High-level request payload: `business_profile` and optional `additional_context`
- High-level response shape: success flag, strategy object (channels, budget, timeline, content, KPIs, insights, provider info), next steps

**4. Scrape leads**
- UI action name: Scrape leads
- Current behavior: Simulated/static lead scraping
- Target API Gateway endpoint: `/api/leads/scrape`
- HTTP method: `POST`
- High-level request payload: location, business type, radius, max results
- High-level response shape: success flag, task ID, estimated completion

**5. Upload customers for enrichment**
- UI action name: Upload customers for enrichment
- Current behavior: Simulated/static enrichment
- Target API Gateway endpoint: `/api/enrichment/upload`
- HTTP method: `POST`
- High-level request payload: file upload (CSV/XLSX)
- High-level response shape: success flag, task ID, record count, status message

**6. Create campaign**
- UI action name: Create campaign
- Current behavior: Simulated/static campaign creation
- Target API Gateway endpoint: `/api/campaigns/create`
- HTTP method: `POST`
- High-level request payload: campaign name, channels, target audience, content, schedule date (optional), budget (optional)
- High-level response shape: success flag, campaign ID, status message

**7. Schedule campaign**
- UI action name: Schedule campaign
- Current behavior: Simulated/static scheduling
- Target API Gateway endpoint: `/api/campaigns/{campaign_id}/schedule`
- HTTP method: `POST`
- High-level request payload: campaign ID in path
- High-level response shape: success flag, campaign ID, status message

**8. View campaign analytics**
- UI action name: View campaign analytics
- Current behavior: Simulated/static metrics
- Target API Gateway endpoint: `/api/analytics/campaign/{campaign_id}`
- HTTP method: `GET`
- High-level request payload: campaign ID in path
- High-level response shape: success flag, campaign ID, metrics summary (impressions, clicks, conversions, rates, ROI)

**9. View lead analytics**
- UI action name: View lead analytics
- Current behavior: Simulated/static metrics
- Target API Gateway endpoint: `/api/analytics/leads`
- HTTP method: `GET`
- High-level request payload: none
- High-level response shape: success flag, lead metrics summary (total, qualified, converted, quality score)

**10. Download reports**
- UI action name: Download reports
- Current behavior: Simulated/static report
- Target API Gateway endpoint: `/api/analytics/report`
- HTTP method: `GET`
- High-level request payload: query params such as report type and optional campaign ID
- High-level response shape: success flag, report type, generated data payload, generated timestamp

## Phase 4 – Future Architecture Alignment (Design Only)

**Content AI Service – Architectural Options**
- Current state in repository: No dedicated Content AI microservice; strategy generation lives in StrategyAI with provider abstraction.
- Option A: Merge into StrategyAI: Content generation remains a module inside StrategyAI.
- Option A pros: Fewer services to operate, simpler deployment, shared prompt/context reuse.
- Option A cons: StrategyAI becomes a broad surface area, less isolation for content-specific scaling and compliance.
- Option B: Separate Content AI microservice: Content generation becomes its own service behind the API Gateway.
- Option B pros: Clear separation of concerns, independent scaling, isolated provider and prompt management.
- Option B cons: More services to operate, additional inter-service coordination.
- Decision status: No final decision has been made.

**Business Profile Ownership**
- Logical ownership: Business profile is the canonical input for StrategyAI and should be owned by the service responsible for strategy generation or by a dedicated profile domain if introduced later.
- Current implementation state: Business profile is passed as request payload into strategy generation; no dedicated persistence ownership is enforced.
- Architectural ownership considerations:
- StrategyAI ownership keeps the strategy workflow centralized and avoids cross-service coupling.
- Dedicated profile ownership improves reuse across downstream services but introduces coordination and consistency requirements.
- API impact: No API changes are proposed in this phase.

**Third-Party Integration Boundaries**
- Lead scraping integrations: Owned by Lead Enrichment Service.
- Data enrichment providers: Owned by Lead Enrichment Service.
- Email and social campaign integrations: Owned by Campaign Planner Service.
- Strategy provider integrations (Ollama/OpenAI): Owned by StrategyAI Service.
- Boundary principle: Each external integration is owned by the service that exposes the corresponding domain capability through the API Gateway.
- Implementation detail: No provider-specific or integration implementation details are defined here.

**Production Readiness Alignment**
- Logging and monitoring: Standardize structured logs and trace correlation IDs across services.
- Rate limiting: Apply gateway-level rate limiting and service-level guardrails for expensive operations.
- Feature gating validation coverage: Ensure feature checks cover all entry points for licensed features, including background tasks.
- Service-to-service communication hardening: Use explicit timeouts, retries, and circuit-breaking conventions for internal calls.
- Observability and scaling: Define service metrics, dashboarding, and horizontal scaling considerations per service domain.
- Decision status: These are alignment considerations only; no changes are finalized.
