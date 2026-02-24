# MAi Analytics Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, FeatureName, Campaign, CampaignMetric
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

def _default_metrics() -> Dict[str, int]:
    return {"sent": 0, "opened": 0, "clicked": 0, "converted": 0}

def _ensure_metrics(metric_row: Optional[CampaignMetric]) -> Dict[str, int]:
    if not metric_row:
        return _default_metrics()

    return {
        "sent": int(metric_row.sent) if isinstance(metric_row.sent, (int, float)) else 0,
        "opened": int(metric_row.opened) if isinstance(metric_row.opened, (int, float)) else 0,
        "clicked": int(metric_row.clicked) if isinstance(metric_row.clicked, (int, float)) else 0,
        "converted": int(metric_row.converted) if isinstance(metric_row.converted, (int, float)) else 0,
    }

def _safe_rate(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)

@app.get("/api/analytics/campaign/{campaign_id}", tags=["Analytics"])
async def get_campaign_metrics(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.ANALYTICS)),
    db: Session = Depends(get_db)
):
    """Get analytics metrics for a specific campaign from database."""
    row = (
        db.query(Campaign, CampaignMetric)
        .outerjoin(CampaignMetric, CampaignMetric.campaign_id == Campaign.id)
        .filter(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user["organization_id"],
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")

    _, metric_row = row
    metrics = _ensure_metrics(metric_row)
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
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.ANALYTICS)),
    db: Session = Depends(get_db)
):
    """Download analytics report (aggregated from campaign + campaign_metrics tables)."""
    rows = (
        db.query(Campaign, CampaignMetric)
        .outerjoin(CampaignMetric, CampaignMetric.campaign_id == Campaign.id)
        .filter(Campaign.organization_id == current_user["organization_id"])
        .all()
    )

    total_sent = 0
    total_opened = 0
    total_clicked = 0
    total_converted = 0

    for _, metric_row in rows:
        m = _ensure_metrics(metric_row)
        total_sent += m["sent"]
        total_opened += m["opened"]
        total_clicked += m["clicked"]
        total_converted += m["converted"]

    data = {
        "total_campaigns": len(rows),
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
