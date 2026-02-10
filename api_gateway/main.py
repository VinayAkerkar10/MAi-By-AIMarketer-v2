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

@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(service: str, path: str, request: Request):
    """Proxy requests to appropriate microservice. Path is preserved so that
    /api/auth/org-login reaches the auth service at /api/auth/org-login."""
    if service not in SERVICE_URLS:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")
    
    service_url = SERVICE_URLS[service]
    # Preserve full path: /api/{service}/{path} -> service_url/api/{service}/{path}
    url = f"{service_url}/api/{service}/{path}"
    
    # Forward headers
    headers = dict(request.headers)
    headers.pop("host", None)
    
    # Get request body if present
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
    
    # Make request to microservice
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                params=dict(request.query_params),
                timeout=30.0
            )
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    
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
