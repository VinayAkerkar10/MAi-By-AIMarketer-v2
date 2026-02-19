# MAi API Gateway
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

app = FastAPI(
    title="MAi API Gateway",
    description="API Gateway for MAi Microservices - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
SERVICE_URLS = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://auth_service:8001"),
    "licensing": os.getenv("LICENSING_SERVICE_URL", "http://licensing_service:8002"),
    "strategy": os.getenv("STRATEGY_SERVICE_URL", "http://strategy_ai_service:8003"),
    "leads": os.getenv("LEAD_SERVICE_URL", "http://lead_enrichment_service:8004"),
    "campaigns": os.getenv("CAMPAIGN_SERVICE_URL", "http://campaign_planner_service:8005"),
    "analytics": os.getenv("ANALYTICS_SERVICE_URL", "http://analytics_service:8006"),
}

SERVICE_ALIASES = {
    "admin": "auth",
}

@app.api_route("/api/{service}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(service: str, request: Request, path: str = ""):
    """Proxy requests to appropriate microservice. Path is preserved so that
    /api/auth/org-login reaches the auth service at /api/auth/org-login."""
    resolved_service = SERVICE_ALIASES.get(service, service)

    if resolved_service == "enrichment":
        service_url = SERVICE_URLS["leads"]
    elif resolved_service in SERVICE_URLS:
        service_url = SERVICE_URLS[resolved_service]
    else:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")

    # Preserve route shape without forcing a trailing slash when path is empty
    if path:
        url = f"{service_url}/api/{resolved_service}/{path}"
    else:
        url = f"{service_url}/api/{resolved_service}"

    # Forward headers
    headers = dict(request.headers)
    headers.pop("host", None)

    # Redact authorization value for logs
    logged_headers = {}
    for key, value in headers.items():
        if key.lower() == "authorization":
            logged_headers[key] = "[REDACTED]"
        else:
            logged_headers[key] = value

    # Inter-service routing diagnostics
    print(f"[Gateway Routing] service={service}")
    print(f"[Gateway Routing] resolved_service={resolved_service}")
    print(f"[Gateway Routing] service_url={service_url}")
    print(f"[Gateway Routing] upstream_url={url}")

    # Get request body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()

    # Make request to microservice
    timeout = httpx.Timeout(
        timeout=None,
        connect=30.0,
        read=None,
        write=30.0,
        pool=None
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

    # Upstream diagnostics
    print(f"[Gateway Upstream] status={response.status_code}")
    print(f"[Gateway Upstream] body={response.text[:500]}")

    # Forward status code and body; support both JSON and non-JSON responses
    status_code = response.status_code
    content_type = response.headers.get("content-type", "")

    if "application/json" in content_type:
        try:
            content = response.json()
            return JSONResponse(content=content, status_code=status_code)
        except Exception:
            pass  # fall through to raw content
    return Response(
        content=response.content,
        status_code=status_code,
        media_type=content_type or "application/octet-stream",
    )

@app.get("/health")
async def health_check():
    """Health check for API Gateway"""
    return {
        "status": "healthy",
        "service": "api_gateway",
        "services": list(SERVICE_URLS.keys())
    }

@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)


