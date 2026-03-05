# MAi API Gateway
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import re

app = FastAPI(
    title="MAi API Gateway",
    description="API Gateway for MAi Microservices - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
SERVICE_URLS = {
    "auth": os.environ["AUTH_SERVICE_URL"],
    "licensing": os.environ["LICENSING_SERVICE_URL"],
    "strategy": os.environ["STRATEGY_SERVICE_URL"],
    "leads": os.environ["LEAD_SERVICE_URL"],
    "campaigns": os.environ["CAMPAIGN_SERVICE_URL"],
    "analytics": os.environ["ANALYTICS_SERVICE_URL"],
}

print("Gateway service routing:")
for name, url in SERVICE_URLS.items():
    print(f"{name} -> {url}")

SERVICE_ALIASES = {
    "admin": "auth",
    "enrichment": "leads",
}

ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://localhost:8000",
}
VERCEL_ORIGIN_REGEX = re.compile(r"^https://.*\.vercel\.app$")


def _resolve_cors_origin(request: Request) -> str:
    origin = request.headers.get("origin", "")
    if origin in ALLOWED_ORIGINS or VERCEL_ORIGIN_REGEX.match(origin):
        return origin
    # Safe default for explicit frontend deployment.
    return "https://mai-by-ai-marketer-v2.vercel.app"


def _cors_headers(request: Request) -> dict:
    return {
        "Access-Control-Allow-Origin": _resolve_cors_origin(request),
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Methods": "*",
        "Vary": "Origin",
    }

@app.api_route("/api/{service}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_request(service: str, request: Request, path: str = ""):
    """Proxy requests to appropriate microservice. Path is preserved so that
    /api/auth/org-login reaches the auth service at /api/auth/org-login."""
    resolved_service = SERVICE_ALIASES.get(service, service)

    if resolved_service in SERVICE_URLS:
        service_url = SERVICE_URLS[resolved_service]
    else:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")

    # Preserve route shape without forcing a trailing slash when path is empty
    if path:
        url = f"{service_url}/api/{resolved_service}/{path}"
    else:
        url = f"{service_url}/api/{resolved_service}"

    if request.method == "OPTIONS":
        return Response(status_code=200, headers=_cors_headers(request))

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
    print("[Gateway Routing]")
    print(f"Incoming service={service}")
    print(f"Resolved service={resolved_service}")
    print(f"Service URL={service_url}")
    print(f"Forwarding to URL={url}")

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
            print(f"[Gateway Error] {str(e)}")
            raise HTTPException(status_code=503, detail="Upstream service unreachable")

    # Upstream diagnostics
    print(f"[Gateway Upstream] status={response.status_code}")
    print(f"[Gateway Upstream] body={response.text[:500]}")

    # Forward status/body and preserve upstream headers while ensuring CORS headers are present.
    response_headers = dict(response.headers)
    for hop_by_hop_header in ["content-length", "transfer-encoding", "connection", "keep-alive"]:
        response_headers.pop(hop_by_hop_header, None)
    response_headers.update(_cors_headers(request))

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type", "application/json"),
        headers=response_headers,
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


