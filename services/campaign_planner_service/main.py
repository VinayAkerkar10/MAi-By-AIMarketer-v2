# MAi Campaign Planner Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid
import sys
import os
import httpx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, FeatureName
from shared.auth import require_feature

app = FastAPI(
    title="MAi Campaign Planner Service",
    description="Multi-Channel Campaign Management - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (replace with database)
campaigns_data: Dict[str, Dict[str, Any]] = {}
campaign_analytics: Dict[str, Dict[str, Any]] = {}

LEAD_SERVICE_URL = os.getenv("LEAD_SERVICE_URL", "http://lead_enrichment_service:8004")
LEAD_SERVICE_TIMEOUT = httpx.Timeout(10.0, connect=10.0)
ALLOWED_AUDIENCE_SOURCES = {"scraped_leads", "customer_upload", "manual_selection"}


# ===== REQUEST MODELS =====

class CampaignRequest(BaseModel):
    campaign_name: str = Field(..., description="Name of the campaign")
    channels: List[str] = Field(..., description="Marketing channels to use")
    target_audience: str = Field(..., description="Target audience for the campaign")
    content: Optional[str] = Field(None, description="Campaign content")
    schedule_date: Optional[datetime] = Field(None, description="When to schedule the campaign")
    budget: Optional[float] = Field(None, description="Campaign budget")
    audience_source: Optional[str] = Field("scraped_leads", description="Audience source")
    manual_selection: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Manual selected leads")

class CampaignUpdateRequest(BaseModel):
    campaign_name: Optional[str] = None
    channels: Optional[List[str]] = None
    target_audience: Optional[str] = None
    content: Optional[str] = None
    schedule_date: Optional[datetime] = None
    budget: Optional[float] = None




def _default_metrics() -> Dict[str, int]:
    return {
        "sent": 0,
        "opened": 0,
        "clicked": 0,
        "converted": 0,
    }


def _ensure_campaign_defaults(campaign: Dict[str, Any]) -> Dict[str, Any]:
    if "metrics" not in campaign or not isinstance(campaign.get("metrics"), dict):
        campaign["metrics"] = _default_metrics()
    else:
        defaults = _default_metrics()
        for key, fallback in defaults.items():
            metric_val = campaign["metrics"].get(key, fallback)
            campaign["metrics"][key] = int(metric_val) if isinstance(metric_val, (int, float)) else fallback

    if "deployed_at" not in campaign:
        campaign["deployed_at"] = None

    if "updated_at" not in campaign:
        campaign["updated_at"] = datetime.utcnow().isoformat()

    if "audience_source" not in campaign:
        campaign["audience_source"] = "scraped_leads"

    if "manual_selection" not in campaign or not isinstance(campaign.get("manual_selection"), list):
        campaign["manual_selection"] = []

    return campaign


def _coerce_string(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if isinstance(value, list):
            for item in value:
                text = _coerce_string(item, "")
                if text:
                    return text
        else:
            text = _coerce_string(value, "")
            if text:
                return text
    return ""


def _normalize_lead(raw_lead: Dict[str, Any], audience_source: str) -> Dict[str, Any]:
    if not isinstance(raw_lead, dict):
        raw_lead = {}

    lead_id = _first_non_empty(raw_lead.get("id"), raw_lead.get("lead_id"), raw_lead.get("_id"))
    if not lead_id:
        lead_id = str(uuid.uuid4())

    name = _first_non_empty(
        raw_lead.get("name"),
        raw_lead.get("business_name"),
        raw_lead.get("company"),
        raw_lead.get("company_name"),
    ) or "Unknown"

    email = _first_non_empty(
        raw_lead.get("email"),
        raw_lead.get("emails"),
        raw_lead.get("contact_email"),
    )

    phone = _first_non_empty(
        raw_lead.get("phone"),
        raw_lead.get("phones"),
        raw_lead.get("contact_numbers"),
        raw_lead.get("mobile"),
    )

    return {
        "id": lead_id,
        "name": name,
        "email": email,
        "phone": phone,
        "source": audience_source,
    }


async def _fetch_lead_tasks(path: str, organization_id: str, auth_header: Optional[str] = None) -> List[Dict[str, Any]]:
    url = f"{LEAD_SERVICE_URL}{path}"
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header

    print(f"[campaign_debug] _fetch_lead_tasks path={path} org={organization_id} auth_header_present={bool(auth_header)}")

    try:
        async with httpx.AsyncClient(timeout=LEAD_SERVICE_TIMEOUT) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException:
        print(f"[campaign_debug] _fetch_lead_tasks timeout path={path}")
        raise HTTPException(status_code=503, detail="Lead service timeout")
    except httpx.RequestError as exc:
        print(f"[campaign_debug] _fetch_lead_tasks request_error path={path} error={exc}")
        return []

    print(f"[campaign_debug] _fetch_lead_tasks status_code={response.status_code} path={path}")

    if 400 <= response.status_code < 500:
        print(f"[campaign_debug] _fetch_lead_tasks client_error status_code={response.status_code} path={path}")
        return []

    if response.status_code >= 500:
        print(f"[campaign_debug] _fetch_lead_tasks server_error status_code={response.status_code} path={path}")
        return []

    try:
        payload = response.json()
    except ValueError:
        print(f"[campaign_debug] _fetch_lead_tasks invalid_json path={path}")
        return []

    payload_keys = list(payload.keys()) if isinstance(payload, dict) else []
    print(f"[campaign_debug] _fetch_lead_tasks payload_keys={payload_keys}")

    if isinstance(payload, list):
        tasks = [item for item in payload if isinstance(item, dict)]
        print(f"[campaign_debug] _fetch_lead_tasks tasks_returned={len(tasks)} source=list")
        return tasks

    if not isinstance(payload, dict):
        print(f"[campaign_debug] _fetch_lead_tasks unexpected_payload_type={type(payload)}")
        return []

    for key in ("tasks", "data", "results"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            tasks = [item for item in candidate if isinstance(item, dict)]
            print(f"[campaign_debug] _fetch_lead_tasks tasks_returned={len(tasks)} source_key={key}")
            return tasks

    print("[campaign_debug] _fetch_lead_tasks tasks_returned=0 (no tasks/data/results list)")
    return []


async def get_audience_leads(
    organization_id: str,
    audience_source: str,
    manual_selection: Optional[List[Dict[str, Any]]] = None,
    auth_header: Optional[str] = None,
) -> List[Dict[str, Any]]:
    print(f"[campaign_debug] get_audience_leads source={audience_source!r} org={organization_id}")

    if audience_source == "manual_selection":
        selected = manual_selection or []
        print(f"[campaign_debug] get_audience_leads manual_selection_count={len(selected)}")
        return [_normalize_lead(lead, "manual_selection") for lead in selected if isinstance(lead, dict)]

    if audience_source == "scraped_leads":
        tasks = await _fetch_lead_tasks("/api/leads/tasks", organization_id, auth_header=auth_header)
        completed_tasks = [t for t in tasks if t.get("status") == "completed"]
        org_match_tasks = [t for t in tasks if t.get("organization_id") == organization_id]
        flattened: List[Dict[str, Any]] = []
        for task in completed_tasks:
            if isinstance(task.get("leads"), list):
                flattened.extend(task["leads"])

        non_empty_lead_tasks = [t for t in completed_tasks if isinstance(t.get("leads"), list) and len(t.get("leads")) > 0]

        print(f"[campaign_debug] get_audience_leads scraped_tasks_fetched={len(tasks)}")
        print(f"[campaign_debug] get_audience_leads scraped_completed_tasks={len(completed_tasks)}")
        print(f"[campaign_debug] get_audience_leads scraped_org_match_tasks={len(org_match_tasks)}")
        print(f"[campaign_debug] get_audience_leads scraped_non_empty_lead_tasks={len(non_empty_lead_tasks)}")
        print(f"[campaign_debug] get_audience_leads scraped_flattened_leads_before_normalization={len(flattened)}")

        return [_normalize_lead(lead, "scraped_leads") for lead in flattened]

    if audience_source == "customer_upload":
        tasks = await _fetch_lead_tasks("/api/enrichment/tasks", organization_id, auth_header=auth_header)
        completed_tasks = [t for t in tasks if t.get("status") == "completed"]
        org_match_tasks = [t for t in tasks if t.get("organization_id") == organization_id]
        flattened = []
        for task in completed_tasks:
            if isinstance(task.get("enriched_data"), list):
                flattened.extend(task["enriched_data"])

        non_empty_enriched_tasks = [
            t for t in completed_tasks if isinstance(t.get("enriched_data"), list) and len(t.get("enriched_data")) > 0
        ]

        print(f"[campaign_debug] get_audience_leads enrichment_tasks_fetched={len(tasks)}")
        print(f"[campaign_debug] get_audience_leads enrichment_completed_tasks={len(completed_tasks)}")
        print(f"[campaign_debug] get_audience_leads enrichment_org_match_tasks={len(org_match_tasks)}")
        print(f"[campaign_debug] get_audience_leads enrichment_non_empty_tasks={len(non_empty_enriched_tasks)}")
        print(f"[campaign_debug] get_audience_leads enrichment_flattened_leads_before_normalization={len(flattened)}")

        return [_normalize_lead(lead, "customer_upload") for lead in flattened]

    print(f"[campaign_debug] get_audience_leads unsupported_source={audience_source!r}")
    return []


def send_email_via_smtp(to_email: str, subject: str, body: str) -> bool:
    from email.mime.text import MIMEText
    import smtplib

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = "noreply@aimarketer.local"
        msg["To"] = to_email

        with smtplib.SMTP("mailhog", 1025, timeout=10) as smtp:
            smtp.sendmail(msg["From"], [to_email], msg.as_string())

        return True
    except Exception:
        return False


async def execute_campaign(campaign_id: str, auth_header: Optional[str] = None) -> Dict[str, Any]:
    campaign = campaigns_data.get(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    audience_source = campaign.get("audience_source", "scraped_leads")
    manual_selection = campaign.get("manual_selection", [])

    print(
        f"[campaign_debug] execute_campaign campaign_id={campaign_id} "
        f"org={campaign.get('organization_id')} source={audience_source!r}"
    )

    try:
        leads = await get_audience_leads(
            organization_id=campaign["organization_id"],
            audience_source=audience_source,
            manual_selection=manual_selection,
            auth_header=auth_header,
        )
    except HTTPException as exc:
        if exc.status_code == 503:
            print(f"[campaign_debug] execute_campaign lead_service_timeout campaign_id={campaign_id}")
            leads = []
        else:
            raise

    print(f"[campaign_debug] execute_campaign campaign_id={campaign_id} leads_returned={len(leads)}")

    sent = 0
    if audience_source == "customer_upload":
        subject = f"Campaign: {campaign.get('campaign_name', 'Marketing Campaign')}"
        body = campaign.get("content") or "Hello, this is a campaign outreach message."
        for lead in leads:
            email = (lead.get("email") or "").strip()
            if not email:
                continue
            print("[smtp_debug] sending to", email)
            success = send_email_via_smtp(email, subject, body)
            print("[smtp_debug] send_success", success)
            if success:
                sent += 1

    # Real interaction tracking endpoints are not implemented yet.
    # Keep engagement metrics at zero until actual events are recorded.
    opened = 0
    clicked = 0
    converted = 0

    now = datetime.utcnow().isoformat()
    campaign["metrics"] = {
        "sent": sent,
        "opened": opened,
        "clicked": clicked,
        "converted": converted,
    }
    campaign["status"] = "active"
    campaign["deployed_at"] = now
    campaign["updated_at"] = now

    campaigns_data[campaign_id] = _ensure_campaign_defaults(campaign)

    if campaign_id not in campaign_analytics:
        campaign_analytics[campaign_id] = {
            "campaign_id": campaign_id,
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
            "cost": 0.0,
            "ctr": 0.0,
            "conversion_rate": 0.0,
            "cpa": 0.0,
            "roi": 0.0,
        }

    campaign_analytics[campaign_id]["clicks"] = clicked
    campaign_analytics[campaign_id]["conversions"] = converted

    return campaigns_data[campaign_id]


# ===== CAMPAIGN MANAGEMENT =====

@app.post("/api/campaigns/create", tags=["Campaigns"])
async def create_campaign(
    campaign: CampaignRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Create a new marketing campaign"""
    try:
        audience_source = campaign.audience_source or "scraped_leads"
        if audience_source not in ALLOWED_AUDIENCE_SOURCES:
            raise HTTPException(
                status_code=400,
                detail="Invalid audience_source. Allowed: scraped_leads, customer_upload, manual_selection",
            )

        campaign_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        auth_header = request.headers.get("authorization")
        manual_count = len(campaign.manual_selection or [])

        print(
            f"[campaign_debug] create_campaign campaign_id={campaign_id} "
            f"org={current_user.get('organization_id')} source={audience_source!r} "
            f"manual_selection_len={manual_count} auth_header_present={bool(auth_header)}"
        )

        campaign_data = {
            "campaign_id": campaign_id,
            "organization_id": current_user["organization_id"],
            "campaign_name": campaign.campaign_name,
            "channels": campaign.channels,
            "target_audience": campaign.target_audience,
            "content": campaign.content,
            "schedule_date": campaign.schedule_date.isoformat() if campaign.schedule_date else None,
            "budget": campaign.budget,
            "audience_source": audience_source,
            "manual_selection": campaign.manual_selection or [],
            "status": "draft",
            "metrics": _default_metrics(),
            "created_at": now,
            "updated_at": now,
            "deployed_at": None,
        }

        campaigns_data[campaign_id] = campaign_data

        campaign_analytics[campaign_id] = {
            "campaign_id": campaign_id,
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
            "cost": 0.0,
            "ctr": 0.0,
            "conversion_rate": 0.0,
            "cpa": 0.0,
            "roi": 0.0,
        }

        updated_campaign = await execute_campaign(campaign_id, auth_header=auth_header)

        return {
            "success": True,
            "campaign": updated_campaign,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {str(e)}")


@app.post("/api/campaigns/{campaign_id}/schedule", tags=["Campaigns"])
async def schedule_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Schedule campaign for deployment"""
    if campaign_id not in campaigns_data:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign = campaigns_data[campaign_id]
    if campaign["organization_id"] != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    background_tasks.add_task(_deploy_campaign_task, campaign_id)

    campaigns_data[campaign_id]["status"] = "scheduled"
    campaigns_data[campaign_id]["updated_at"] = datetime.utcnow().isoformat()

    return {
        "success": True,
        "message": "Campaign scheduled successfully",
        "campaign_id": campaign_id,
    }


async def _deploy_campaign_task(campaign_id: str):
    """Background task for campaign deployment"""
    try:
        campaign = campaigns_data[campaign_id]

        for channel in campaign["channels"]:
            await _deploy_to_channel(campaign_id, channel, campaign)

        campaigns_data[campaign_id]["status"] = "active"
        campaigns_data[campaign_id]["deployed_at"] = datetime.utcnow().isoformat()
        campaigns_data[campaign_id]["updated_at"] = datetime.utcnow().isoformat()
        campaigns_data[campaign_id] = _ensure_campaign_defaults(campaigns_data[campaign_id])
    except Exception as e:
        campaigns_data[campaign_id]["status"] = "failed"
        campaigns_data[campaign_id]["error"] = str(e)
        campaigns_data[campaign_id]["updated_at"] = datetime.utcnow().isoformat()
        campaigns_data[campaign_id] = _ensure_campaign_defaults(campaigns_data[campaign_id])


async def _deploy_to_channel(campaign_id: str, channel: str, campaign_data: dict):
    """Deploy campaign to specific channel"""
    pass


@app.get("/api/campaigns", tags=["Campaigns"])
async def get_campaigns(
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Get all campaigns for the organization"""
    org_campaigns = [
        _ensure_campaign_defaults(campaign.copy())
        for campaign in campaigns_data.values()
        if campaign["organization_id"] == current_user["organization_id"]
    ]

    return {
        "success": True,
        "campaigns": org_campaigns,
    }


@app.get("/api/campaigns/{campaign_id}", tags=["Campaigns"])
async def get_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Get campaign details"""
    if campaign_id not in campaigns_data:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign = campaigns_data[campaign_id]
    if campaign["organization_id"] != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    campaign = _ensure_campaign_defaults(campaign.copy())

    return {
        "success": True,
        "campaign": campaign,
    }


@app.put("/api/campaigns/{campaign_id}", tags=["Campaigns"])
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Update campaign details"""
    if campaign_id not in campaigns_data:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign = campaigns_data[campaign_id]
    if campaign.get("organization_id") != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if payload.campaign_name is not None:
        campaign["campaign_name"] = payload.campaign_name
    if payload.channels is not None:
        campaign["channels"] = payload.channels
    if payload.target_audience is not None:
        campaign["target_audience"] = payload.target_audience
    if payload.content is not None:
        campaign["content"] = payload.content
    if payload.schedule_date is not None:
        campaign["schedule_date"] = payload.schedule_date.isoformat()
    if payload.budget is not None:
        campaign["budget"] = payload.budget

    campaign["updated_at"] = datetime.utcnow().isoformat()
    campaigns_data[campaign_id] = _ensure_campaign_defaults(campaign)

    return {
        "success": True,
        "campaign": campaigns_data[campaign_id],
    }


@app.post("/api/campaigns/{campaign_id}/pause", tags=["Campaigns"])
async def pause_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Pause/unpause campaign"""
    if campaign_id not in campaigns_data:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign = campaigns_data[campaign_id]
    if campaign.get("organization_id") != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    current_status = str(campaign.get("status", "")).lower()
    campaign["status"] = "active" if current_status == "paused" else "paused"
    campaign["updated_at"] = datetime.utcnow().isoformat()

    campaigns_data[campaign_id] = _ensure_campaign_defaults(campaign)

    return {
        "success": True,
        "campaign": campaigns_data[campaign_id],
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "campaign_planner_service",
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8005, reload=True)

