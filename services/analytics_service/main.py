# MAi Analytics Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
import sys
import os
import httpx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, FeatureName
from shared.auth import get_current_user, require_feature

app = FastAPI(
    title="MAi Analytics Service",
    description="Analytics & Reporting - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CAMPAIGN_SERVICE_URL = os.getenv("CAMPAIGN_SERVICE_URL", "http://campaign_planner_service:8005")
CAMPAIGN_HTTP_TIMEOUT = httpx.Timeout(8.0, connect=5.0)

def _default_metrics() -> Dict[str, int]:
    return {"sent": 0, "opened": 0, "clicked": 0, "converted": 0}

def _ensure_metrics(campaign: Dict[str, Any]) -> Dict[str, int]:
    metrics = campaign.get("metrics")
    if not isinstance(metrics, dict):
        return _default_metrics()

    defaults = _default_metrics()
    normalized = {}
    for k, v in defaults.items():
        mv = metrics.get(k, v)
        normalized[k] = mv if isinstance(mv, (int, float)) else v
    return normalized

def _safe_rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)

async def _campaign_service_get(path: str, auth_header: Optional[str]) -> Dict[str, Any]:
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    url = f"{CAMPAIGN_SERVICE_URL}{path}"
    try:
        async with httpx.AsyncClient(timeout=CAMPAIGN_HTTP_TIMEOUT) as client:
            response = await client.get(url, headers=headers)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Campaign service unavailable")

    if response.status_code == 503:
        raise HTTPException(status_code=503, detail="Campaign service unavailable")

    if response.status_code >= 400:
        detail = "Failed to fetch campaign data"
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("message") or detail
        except Exception:
            pass
        raise HTTPException(status_code=response.status_code, detail=detail)

    try:
        return response.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Invalid response from campaign service")

@app.get("/api/analytics/campaign/{campaign_id}", tags=["Analytics"])
async def get_campaign_metrics(
    campaign_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.ANALYTICS)),
    db: Session = Depends(get_db)
):
    """Get analytics metrics for a specific campaign from campaign_planner_service"""
    auth_header = request.headers.get("authorization")
    payload = await _campaign_service_get(f"/api/campaigns/{campaign_id}", auth_header)

    campaign = payload.get("campaign")
    if not isinstance(campaign, dict):
        raise HTTPException(status_code=502, detail="Campaign service returned invalid campaign payload")

    # Organization-level filtering enforcement
    if campaign.get("organization_id") != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    metrics = _ensure_metrics(campaign)
    sent = metrics["sent"]
    opened = metrics["opened"]
    clicked = metrics["clicked"]
    converted = metrics["converted"]

    return {
        "success": True,
        "campaign_id": campaign_id,
        "metrics": {
            "sent": sent,
            "opened": opened,
            "clicked": clicked,
            "converted": converted,
            "open_rate": _safe_rate(opened, sent),
            "click_rate": _safe_rate(clicked, sent),
            "conversion_rate": _safe_rate(converted, sent)
        }
    }

@app.get("/api/analytics/leads", tags=["Analytics"])
async def get_lead_metrics(
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.ANALYTICS)),
    db: Session = Depends(get_db)
):
    """Get lead management metrics"""
    # TODO: Fetch from database
    return {
        "success": True,
        "metrics": {
            "total_leads": 0,
            "qualified_leads": 0,
            "converted_leads": 0,
            "lead_quality_score": 0.0
        }
    }

@app.get("/api/analytics/report", tags=["Analytics"])
async def download_report(
    report_type: str = "campaign_summary",
    campaign_id: Optional[str] = None,
    request: Request = None,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.ANALYTICS)),
    db: Session = Depends(get_db)
):
    """Download analytics report (aggregated from campaign_planner_service)"""
    auth_header = request.headers.get("authorization") if request else None
    payload = await _campaign_service_get("/api/campaigns", auth_header)

    campaigns: List[Dict[str, Any]] = payload.get("campaigns", [])
    if not isinstance(campaigns, list):
        raise HTTPException(status_code=502, detail="Campaign service returned invalid campaigns payload")

    # Organization-level filtering enforcement
    campaigns = [c for c in campaigns if isinstance(c, dict) and c.get("organization_id") == current_user["organization_id"]]

    total_sent = 0
    total_opened = 0
    total_clicked = 0
    total_converted = 0

    for campaign in campaigns:
        m = _ensure_metrics(campaign)
        total_sent += m["sent"]
        total_opened += m["opened"]
        total_clicked += m["clicked"]
        total_converted += m["converted"]

    data = {
        "total_campaigns": len(campaigns),
        "totals": {
            "sent": total_sent,
            "opened": total_opened,
            "clicked": total_clicked,
            "converted": total_converted
        },
        "rates": {
            "open_rate": _safe_rate(total_opened, total_sent),
            "click_rate": _safe_rate(total_clicked, total_sent),
            "conversion_rate": _safe_rate(total_converted, total_sent)
        }
    }

    return {
        "success": True,
        "report_type": report_type,
        "data": data,
        "generated_at": datetime.utcnow().isoformat()
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "analytics_service",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006, reload=True)
