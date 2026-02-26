# MAi Analytics Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import (
    get_db,
    FeatureName,
    Campaign,
    CampaignMetric,
    LeadScrapeResult,
    EnrichmentRow,
    Strategy,
    StrategyVersion,
)
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
    org_id = current_user["organization_id"]

    scraped_total = (
        db.query(func.coalesce(func.count(LeadScrapeResult.id), 0))
        .filter(LeadScrapeResult.organization_id == org_id)
        .scalar()
    ) or 0
    enriched_total = (
        db.query(func.coalesce(func.count(EnrichmentRow.id), 0))
        .filter(EnrichmentRow.organization_id == org_id)
        .scalar()
    ) or 0

    scraped_qualified = (
        db.query(func.coalesce(func.count(LeadScrapeResult.id), 0))
        .filter(
            LeadScrapeResult.organization_id == org_id,
            LeadScrapeResult.email.isnot(None),
            LeadScrapeResult.email != ""
        )
        .scalar()
    ) or 0
    enriched_qualified = (
        db.query(func.coalesce(func.count(EnrichmentRow.id), 0))
        .filter(
            EnrichmentRow.organization_id == org_id,
            EnrichmentRow.enriched_data.isnot(None)
        )
        .scalar()
    ) or 0

    total_leads = int(scraped_total) + int(enriched_total)
    qualified_leads = int(scraped_qualified) + int(enriched_qualified)
    converted_leads = int(
        (db.query(func.coalesce(func.sum(CampaignMetric.converted), 0))
         .filter(CampaignMetric.organization_id == org_id)
         .scalar()) or 0
    )

    return {
        "success": True,
        "metrics": {
            "total_leads": total_leads,
            "qualified_leads": qualified_leads,
            "converted_leads": converted_leads,
            "lead_quality_score": _safe_rate(qualified_leads, total_leads)
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
    org_id = current_user["organization_id"]
    agg = (
        db.query(
            func.coalesce(func.count(Campaign.id), 0).label("total_campaigns"),
            func.coalesce(func.sum(CampaignMetric.sent), 0).label("total_sent"),
            func.coalesce(func.sum(CampaignMetric.opened), 0).label("total_opened"),
            func.coalesce(func.sum(CampaignMetric.clicked), 0).label("total_clicked"),
            func.coalesce(func.sum(CampaignMetric.converted), 0).label("total_converted"),
            func.coalesce(func.avg(CampaignMetric.roi), 0.0).label("avg_roi"),
        )
        .outerjoin(
            CampaignMetric,
            and_(
                CampaignMetric.campaign_id == Campaign.id,
                CampaignMetric.organization_id == Campaign.organization_id,
            ),
        )
        .filter(Campaign.organization_id == org_id)
        .one()
    )

    total_sent = int(agg.total_sent or 0)
    total_opened = int(agg.total_opened or 0)
    total_clicked = int(agg.total_clicked or 0)
    total_converted = int(agg.total_converted or 0)

    data = {
        "total_campaigns": int(agg.total_campaigns or 0),
        "totals": {
            "sent": total_sent,
            "opened": total_opened,
            "clicked": total_clicked,
            "converted": total_converted
        },
        "rates": {
            "open_rate": _safe_rate(total_opened, total_sent),
            "click_rate": _safe_rate(total_clicked, total_sent),
            "conversion_rate": _safe_rate(total_converted, total_sent),
            "roi": float(agg.avg_roi or 0.0),
        }
    }

    return {
        "success": True,
        "report_type": report_type,
        "data": data,
        "generated_at": datetime.utcnow().isoformat()
    }


@app.get("/api/analytics/strategy/{strategy_id}", tags=["Analytics"])
async def get_strategy_performance(
    strategy_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.ANALYTICS)),
    db: Session = Depends(get_db)
):
    """Get aggregated strategy performance overall and by strategy version."""
    org_id = current_user["organization_id"]

    strategy = (
        db.query(Strategy)
        .filter(
            Strategy.id == strategy_id,
            Strategy.organization_id == org_id,
        )
        .first()
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    overall = (
        db.query(
            func.coalesce(func.count(Campaign.id), 0).label("campaign_count"),
            func.coalesce(func.sum(CampaignMetric.sent), 0).label("total_sent"),
            func.coalesce(func.sum(CampaignMetric.opened), 0).label("total_opened"),
            func.coalesce(func.sum(CampaignMetric.clicked), 0).label("total_clicked"),
            func.coalesce(func.sum(CampaignMetric.converted), 0).label("total_converted"),
            func.coalesce(func.avg(CampaignMetric.ctr), 0.0).label("avg_ctr"),
            func.coalesce(func.avg(CampaignMetric.conversion_rate), 0.0).label("avg_conversion_rate"),
            func.coalesce(func.avg(CampaignMetric.roi), 0.0).label("avg_roi"),
        )
        .outerjoin(
            CampaignMetric,
            and_(
                CampaignMetric.campaign_id == Campaign.id,
                CampaignMetric.organization_id == Campaign.organization_id,
            ),
        )
        .filter(
            Campaign.organization_id == org_id,
            Campaign.strategy_id == strategy_id,
        )
        .one()
    )

    by_version_rows = (
        db.query(
            StrategyVersion.version_no.label("strategy_version_no"),
            func.coalesce(func.count(Campaign.id), 0).label("campaign_count"),
            func.coalesce(func.sum(CampaignMetric.sent), 0).label("total_sent"),
            func.coalesce(func.sum(CampaignMetric.opened), 0).label("total_opened"),
            func.coalesce(func.sum(CampaignMetric.clicked), 0).label("total_clicked"),
            func.coalesce(func.sum(CampaignMetric.converted), 0).label("total_converted"),
            func.coalesce(func.avg(CampaignMetric.ctr), 0.0).label("avg_ctr"),
            func.coalesce(func.avg(CampaignMetric.conversion_rate), 0.0).label("avg_conversion_rate"),
            func.coalesce(func.avg(CampaignMetric.roi), 0.0).label("avg_roi"),
        )
        .outerjoin(
            Campaign,
            and_(
                Campaign.strategy_id == StrategyVersion.strategy_id,
                Campaign.strategy_version_no == StrategyVersion.version_no,
                Campaign.organization_id == StrategyVersion.organization_id,
            ),
        )
        .outerjoin(
            CampaignMetric,
            and_(
                CampaignMetric.campaign_id == Campaign.id,
                CampaignMetric.organization_id == Campaign.organization_id,
            ),
        )
        .filter(
            StrategyVersion.organization_id == org_id,
            StrategyVersion.strategy_id == strategy_id,
        )
        .group_by(StrategyVersion.version_no)
        .order_by(StrategyVersion.version_no.asc())
        .all()
    )

    return {
        "success": True,
        "strategy_id": strategy_id,
        "overall": {
            "campaign_count": int(overall.campaign_count or 0),
            "total_sent": int(overall.total_sent or 0),
            "total_opened": int(overall.total_opened or 0),
            "total_clicked": int(overall.total_clicked or 0),
            "total_converted": int(overall.total_converted or 0),
            "avg_ctr": float(overall.avg_ctr or 0.0),
            "avg_conversion_rate": float(overall.avg_conversion_rate or 0.0),
            "avg_roi": float(overall.avg_roi or 0.0),
        },
        "by_version": [
            {
                "strategy_version_no": int(row.strategy_version_no),
                "campaign_count": int(row.campaign_count or 0),
                "total_sent": int(row.total_sent or 0),
                "total_opened": int(row.total_opened or 0),
                "total_clicked": int(row.total_clicked or 0),
                "total_converted": int(row.total_converted or 0),
                "avg_ctr": float(row.avg_ctr or 0.0),
                "avg_conversion_rate": float(row.avg_conversion_rate or 0.0),
                "avg_roi": float(row.avg_roi or 0.0),
            }
            for row in by_version_rows
        ],
        "generated_at": datetime.utcnow().isoformat(),
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
