# MAi Lead Enrichment Service - Playwright-ready Docker image

FROM mcr.microsoft.com/playwright/python:v1.52.0-jammy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Keep only app/runtime packages that are still needed on top of the
# Playwright base image. Browser dependencies are already included.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8004

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/api/health || exit 1

CMD ["uvicorn", "services.lead_enrichment_service.main:app", "--host", "0.0.0.0", "--port", "8004", "--reload"]
