# Email Campaign Audit and Mailrelay Redesign

## Current Audit

### Email sending logic
- Email sending was triggered inside `POST /api/campaigns/create`, which persisted the campaign and immediately called `execute_campaign`.
- Sending was effectively synchronous from the API caller's perspective during creation.
- The implementation used raw `smtplib` against `mailhog:1025`, so it was a local development stub instead of a production provider.
- There was no provider abstraction, no structured retry policy, and failure handling was reduced to boolean returns plus `print()` statements.

### Campaign flow
- Campaigns were stored in PostgreSQL via SQLAlchemy `Campaign` and `CampaignMetric`.
- Campaign creation and execution were tightly coupled.
- The separate schedule endpoint marked the campaign `scheduled` but then used a FastAPI background task, which runs only in-process and is not durable across restarts.
- There was Celery infrastructure in the repo, but the campaign flow did not use it.

### Recipient handling
- Recipients came from:
  - scraped leads via `lead_scrape_results`
  - enriched uploads via `enrichment_rows.enriched_data`
  - manual selection payloads stored on campaigns
- Missing emails were skipped, but there was no campaign-level validation layer.
- Invalid placeholders like `Not Available` could still flow in from enrichment normalization.
- Deduplication existed only during the SMTP loop and only by lowercase email string.

### Scheduling
- `schedule_date` existed in the schema.
- The execution path ignored `schedule_date` during campaign creation because the create route launched immediately.
- FastAPI background tasks were not reliable for scheduled delivery, horizontal scaling, or worker restarts.

### Email templates
- Templates were stored as raw strings or JSON-like channel payloads.
- HTML rendering quality was minimal.
- Personalization support was effectively absent.

## Key Issues

### Bottlenecks
- API request path performed campaign execution work directly.
- One monolithic route owned persistence, recipient fetching, and sending.

### Failure points
- MailHog-only SMTP integration cannot deliver production traffic.
- In-process background tasks are lost on restarts.
- No durable task queue ownership for scheduled execution.

### Missing validations
- No canonical recipient validation layer before provider handoff.
- No MX-aware validation option.
- No structured rejection reasons for invalid or duplicate recipients.

### Scalability risks
- Request/response lifecycle blocked on outbound sending.
- No provider abstraction for failover or future providers.
- No durable retry orchestration.

## Mailrelay Research

### Findings
- Mailrelay offers a free account with up to 80,000 monthly emails, subject to account conditions.
- Mailrelay supports transactional sending through both SMTP and API.
- The official transactional email page documents API auth using `x-auth-token` and an endpoint shaped like `https://youraccount/api/v1/send_emails`.
- Mailrelay is presented as a commercial hosted service operated by CPC Servicios Informaticos Aplicados a Nuevas Tecnologias S.L.

### API vs SMTP
- API advantages:
  - structured JSON payloads
  - clearer application-level error handling
  - better fit for retries, provider logging, and future analytics correlation
- SMTP advantages:
  - simpler migration from legacy SMTP code
  - works with generic mail libraries
- Recommendation:
  - use Mailrelay API as the primary integration
  - keep SMTP only as an optional debug or fallback path

## Refactored Architecture

```text
FastAPI Campaign API
  -> Campaign persistence (PostgreSQL / SQLAlchemy)
  -> Scheduler handoff
     -> Celery + Redis
        -> campaign execute task
           -> lead source fetch
           -> recipient validation layer
           -> email service
              -> Mailrelay provider
           -> metric/status update
```

## Execution Flow

1. Create campaign with status `pending` or `scheduled`.
2. If `scheduled_at` is in the future, enqueue Celery task with ETA.
3. Worker fetches campaign and audience.
4. Validation layer rejects null, invalid, and duplicate emails.
5. Email service renders HTML/text with personalization.
6. Mailrelay API sends emails with retries.
7. Status becomes `sent`, `completed`, or `failed`.

## Option A: Celery + Redis

- Best for reliable scheduling and horizontal scale.
- Supports ETA-based delivery and retry orchestration.
- Now implemented in this repo.

## Option B: Cron + DB polling

```text
cron job every minute
  -> SELECT campaigns
     WHERE status = 'scheduled'
     AND scheduled_at <= now()
  -> mark sending
  -> execute
  -> update sent/failed
```

- Simpler operational model.
- Lower reliability than Celery ETA unless locking and idempotency are added carefully.

## Implementation Plan

1. Apply the Alembic migration adding `scheduled_at`, provider metadata, and error tracking.
2. Configure Mailrelay credentials in environment variables.
3. Run Celery worker with Redis enabled.
4. Update campaign creation flows to stop auto-sending on create.
5. Launch or schedule campaigns explicitly.
6. Add provider webhooks or polling later for opens, clicks, and bounces.

## Risks

- Mailrelay API payload details may vary by account configuration, so staging verification is still required.
- Passing raw authorization headers into delayed tasks should be revisited if tokens are short-lived.
- Current metrics still cover send counts only; engagement metrics need webhook ingestion.

## Official Sources

- Mailrelay signup/free tier: https://mailrelay.com/en/signup/
- Mailrelay transactional email/API overview: https://mailrelay.com/en/emails-transaccionales/
- Mailrelay terms of use / service ownership: https://mailrelay.com/en/terms-of-use/
