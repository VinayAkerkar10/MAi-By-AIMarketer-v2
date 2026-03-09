# MAi API Gateway
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import re
import asyncio
import time

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
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs (env overrides for production, Docker-safe host fallback for local)
SERVICE_ENV_KEYS = {
    "auth": "AUTH_SERVICE_URL",
    "strategy": "STRATEGY_SERVICE_URL",
    "campaigns": "CAMPAIGN_SERVICE_URL",
    "analytics": "ANALYTICS_SERVICE_URL",
    "licensing": "LICENSING_SERVICE_URL",
    "leads": "LEAD_SERVICE_URL",
}

SERVICE_FALLBACKS = {
    "auth": "http://host.docker.internal:8001",
    "strategy": "http://host.docker.internal:8003",
    "campaigns": "http://host.docker.internal:8005",
    "analytics": "http://host.docker.internal:8006",
    "licensing": "http://host.docker.internal:8002",
    "leads": "http://host.docker.internal:8004",
}

SERVICE_URLS = {
    name: os.getenv(SERVICE_ENV_KEYS[name], SERVICE_FALLBACKS[name])
    for name in SERVICE_ENV_KEYS
}

print("Gateway service routing:")
for name, url in SERVICE_URLS.items():
    env_key = SERVICE_ENV_KEYS[name]
    if os.getenv(env_key):
        print(f"{name} -> {url} (source=env:{env_key})")
    else:
        print(f"{name} -> {url} (source=fallback)")

SERVICE_ALIASES = {
    "admin": "auth",
}

ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:5500",
    "http://localhost:5500"
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


async def keep_services_warm():
    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for name, service_url in SERVICE_URLS.items():
                    health_url = f"{service_url}/api/health"
                    try:
                        r = await client.get(health_url)
                        print(f"[Gateway Warmup] {name} -> {r.status_code}")
                    except Exception as e:
                        print(f"[Gateway Warmup Error] {name}: {e}")
        except Exception as e:
            print(f"[Gateway Warmup Loop Error] {e}")

        await asyncio.sleep(300)


async def startup_connectivity_checks():
    """Run one-time connectivity checks for all configured services on startup."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, service_url in SERVICE_URLS.items():
            health_url = f"{service_url}/api/health"
            try:
                response = await client.get(health_url)
                print(f"[Gateway Startup Check] {name} -> {health_url} -> {response.status_code}")
            except httpx.ConnectTimeout as exc:
                print(f"[Gateway Startup Check] {name} -> {health_url} -> connection timeout ({type(exc).__name__})")
            except httpx.ConnectError as exc:
                print(f"[Gateway Startup Check] {name} -> {health_url} -> connection failed ({type(exc).__name__})")
            except httpx.RequestError as exc:
                print(f"[Gateway Startup Check] {name} -> {health_url} -> request failed ({type(exc).__name__})")
            except Exception as exc:
                print(f"[Gateway Startup Check] {name} -> {health_url} -> unexpected error ({type(exc).__name__})")

@app.api_route("/api/{service}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
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
        max_retries = 3
        retry_delay = 2
        response = None
        for attempt in range(max_retries):
            try:
                request_started_at = time.perf_counter()
                print("[Gateway Request]")
                print(f"method={request.method}")
                print(f"url={url}")
                response = await client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                    params=dict(request.query_params),
                )
                elapsed_ms = round((time.perf_counter() - request_started_at) * 1000, 2)
                print("[Gateway Response]")
                print(f"status={response.status_code}")
                print(f"duration_ms={elapsed_ms}")
                break
            except httpx.RequestError as e:
                print(f"[Gateway Retry] attempt {attempt + 1} failed: {e}")
                error_kind = "request_error"
                if isinstance(e, httpx.ConnectTimeout):
                    error_kind = "connection_timeout"
                elif isinstance(e, httpx.ReadTimeout):
                    error_kind = "read_timeout"
                elif isinstance(e, httpx.WriteTimeout):
                    error_kind = "write_timeout"
                elif isinstance(e, httpx.ConnectError):
                    error_text = str(e).lower()
                    if "name or service not known" in error_text or "nodename nor servname provided" in error_text:
                        error_kind = "dns_error"
                    elif "getaddrinfo failed" in error_text:
                        error_kind = "dns_error"
                    else:
                        error_kind = "connection_error"
                if attempt == max_retries - 1:
                    print("[Gateway Error]")
                    print(f"service={resolved_service}")
                    print(f"url={url}")
                    print(f"error_type={type(e).__name__}")
                    print(f"error_kind={error_kind}")
                    print(f"error={str(e)}")
                    raise HTTPException(status_code=503, detail="Upstream service unreachable")
                await asyncio.sleep(retry_delay)

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


@app.get("/debug/services")
async def debug_services():
    """Debug endpoint exposing configured upstream service URLs."""
    return {
        "services": SERVICE_URLS
    }


@app.on_event("startup")
async def start_keepalive():
    await startup_connectivity_checks()
    asyncio.create_task(keep_services_warm())

@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
