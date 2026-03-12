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
import time
import json
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, SessionLocal, FeatureName, Campaign, CampaignMetric, Strategy, StrategyVersion
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

LEAD_SERVICE_URL = os.getenv("LEAD_SERVICE_URL", "http://lead_enrichment_service:8004")
LEAD_SERVICE_TIMEOUT = httpx.Timeout(10.0, connect=10.0)
ALLOWED_AUDIENCE_SOURCES = {"scraped_leads", "customer_upload", "manual_selection"}
IDEMPOTENCY_TTL_SECONDS = int(os.getenv("CAMPAIGN_IDEMPOTENCY_TTL_SECONDS", "3600"))
_IDEMPOTENCY_CACHE: Dict[str, Dict[str, Any]] = {}


def _build_idempotency_cache_key(organization_id: str, idempotency_key: str) -> str:
    return f"{organization_id}:{idempotency_key}"


def _prune_idempotency_cache() -> None:
    if not _IDEMPOTENCY_CACHE:
        return
    cutoff = time.time() - IDEMPOTENCY_TTL_SECONDS
    stale_keys = [k for k, v in _IDEMPOTENCY_CACHE.items() if float(v.get("ts", 0.0)) < cutoff]
    for key in stale_keys:
        _IDEMPOTENCY_CACHE.pop(key, None)


def _get_cached_campaign_id(organization_id: str, idempotency_key: str) -> Optional[str]:
    if not idempotency_key:
        return None
    _prune_idempotency_cache()
    cache_key = _build_idempotency_cache_key(organization_id, idempotency_key)
    row = _IDEMPOTENCY_CACHE.get(cache_key) or {}
    campaign_id = str(row.get("campaign_id") or "").strip()
    return campaign_id or None


def _cache_campaign_id(organization_id: str, idempotency_key: str, campaign_id: str) -> None:
    if not idempotency_key or not campaign_id:
        return
    _prune_idempotency_cache()
    cache_key = _build_idempotency_cache_key(organization_id, idempotency_key)
    _IDEMPOTENCY_CACHE[cache_key] = {
        "campaign_id": campaign_id,
        "ts": time.time(),
    }


# ===== REQUEST MODELS =====

class CampaignRequest(BaseModel):
    campaign_name: str = Field(..., description="Name of the campaign")
    channels: List[str] = Field(..., description="Marketing channels to use")
    target_audience: str = Field(..., description="Target audience for the campaign")
    content: Optional[str] = Field(None, description="Campaign content")
    schedule_date: Optional[datetime] = Field(None, description="When to schedule the campaign")
    start_date: Optional[datetime] = Field(None, description="Campaign start date")
    end_date: Optional[datetime] = Field(None, description="Campaign end date")
    budget: Optional[float] = Field(None, description="Campaign budget")
    audience_source: Optional[str] = Field("scraped_leads", description="Audience source")
    manual_selection: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Manual selected leads")
    strategy_id: Optional[str] = Field(None, description="Origin strategy ID")
    strategy_version_no: Optional[int] = Field(None, description="Origin strategy version number")

class CampaignUpdateRequest(BaseModel):
    campaign_name: Optional[str] = None
    channels: Optional[List[str]] = None
    target_audience: Optional[str] = None
    content: Optional[str] = None
    schedule_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    budget: Optional[float] = None
    strategy_id: Optional[str] = None
    strategy_version_no: Optional[int] = None


class StrategyCampaignRequest(BaseModel):
    strategy_id: str = Field(..., description="Source strategy ID")
    strategy_version_no: Optional[int] = Field(None, description="Optional strategy version to map from")
    auto_map: Optional[bool] = Field(True, description="Auto-map strategy outputs to campaign fields")


def _validate_strategy_link(
    db: Session,
    organization_id: str,
    strategy_id: Optional[str],
    strategy_version_no: Optional[int],
) -> None:
    if strategy_id is None and strategy_version_no is None:
        return

    if strategy_id is None and strategy_version_no is not None:
        raise HTTPException(status_code=400, detail="strategy_id is required when strategy_version_no is provided")

    strategy = (
        db.query(Strategy)
        .filter(
            Strategy.id == strategy_id,
            Strategy.organization_id == organization_id,
        )
        .first()
    )
    if not strategy:
        raise HTTPException(status_code=400, detail="Invalid strategy_id for organization")

    if strategy_version_no is not None:
        version = (
            db.query(StrategyVersion)
            .filter(
                StrategyVersion.strategy_id == strategy_id,
                StrategyVersion.organization_id == organization_id,
                StrategyVersion.version_no == strategy_version_no,
            )
            .first()
        )
        if not version:
            raise HTTPException(status_code=400, detail="Invalid strategy_version_no for strategy")


def _as_non_negative_int(value: Any) -> int:
    if isinstance(value, (int, float)):
        return max(0, int(value))
    return 0


def _campaign_row_to_response(campaign: Campaign, metric: Optional[CampaignMetric]) -> Dict[str, Any]:
    metrics = {
        "sent": _as_non_negative_int(metric.sent) if metric else 0,
        "opened": _as_non_negative_int(metric.opened) if metric else 0,
        "clicked": _as_non_negative_int(metric.clicked) if metric else 0,
        "converted": _as_non_negative_int(metric.converted) if metric else 0,
    }

    return {
        "campaign_id": campaign.id,
        "organization_id": campaign.organization_id,
        "campaign_name": campaign.campaign_name,
        "channels": campaign.channels if isinstance(campaign.channels, list) else [],
        "target_audience": campaign.target_audience,
        "content": campaign.content,
        "schedule_date": campaign.schedule_date.isoformat() if campaign.schedule_date else None,
        "start_date": campaign.start_date.isoformat() if campaign.start_date else None,
        "end_date": campaign.end_date.isoformat() if campaign.end_date else None,
        "budget": campaign.budget,
        "audience_source": campaign.audience_source or "scraped_leads",
        "manual_selection": campaign.manual_selection if isinstance(campaign.manual_selection, list) else [],
        "status": campaign.status,
        "metrics": metrics,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "updated_at": campaign.updated_at.isoformat() if campaign.updated_at else None,
        "deployed_at": campaign.deployed_at.isoformat() if campaign.deployed_at else None,
    }


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


def _parse_campaign_content(raw_content: Any) -> Dict[str, Any]:
    """
    Normalize stored campaign content into a dictionary structure.
    Supported inputs:
    1) Channel-structured JSON object:
       {"email":{"subject":"","body":""},"linkedin":{"post":""},...}
    2) Legacy manual array format:
       [{"channel":"Email","subject":"...","content":"..."}]
    3) Plain string content
    """
    if isinstance(raw_content, dict):
        return raw_content

    if isinstance(raw_content, list):
        # Keep the legacy array under a namespaced key.
        return {"legacy_channels": raw_content}

    if isinstance(raw_content, str):
        text = raw_content.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return {"legacy_channels": parsed}
            if isinstance(parsed, str):
                return {"text": parsed}
            return {"text": text}
        except Exception:
            return {"text": text}

    return {}


def _extract_channel_payload(content_obj: Dict[str, Any], channel: str) -> Dict[str, str]:
    channel_key = str(channel or "").strip().lower()
    if not channel_key:
        return {}

    channel_data = content_obj.get(channel_key)
    if isinstance(channel_data, dict):
        return {k: str(v) for k, v in channel_data.items() if isinstance(k, str)}

    # Legacy array format support: [{"channel":"Email","subject":"...","content":"..."}]
    legacy_items = content_obj.get("legacy_channels")
    if isinstance(legacy_items, list):
        for item in legacy_items:
            if not isinstance(item, dict):
                continue
            item_channel = str(item.get("channel", "")).strip().lower()
            if item_channel == channel_key:
                return {k: str(v) for k, v in item.items() if isinstance(k, str) and v is not None}

    return {}


def _resolve_email_subject_body(campaign_name: str, content_obj: Dict[str, Any], raw_content: Any) -> Dict[str, str]:
    default_subject = f"Campaign: {campaign_name or 'Marketing Campaign'}"
    default_body = "Hello, this is a campaign outreach message."

    email_payload = _extract_channel_payload(content_obj, "email")

    subject = _coerce_string(
        email_payload.get("subject"),
        default_subject,
    )
    body = _coerce_string(
        email_payload.get("body") or email_payload.get("content") or email_payload.get("message"),
        "",
    )

    if not body:
        # Channel-structured fallback text
        body = _coerce_string(content_obj.get("text"), "")

    if not body and isinstance(raw_content, str):
        # Raw string fallback for older rows
        body = _coerce_string(raw_content, "")

    if not body:
        body = default_body

    return {
        "subject": subject,
        "body": body,
    }


def _resolve_channel_message(content_obj: Dict[str, Any], channel: str, fallback_keys: List[str]) -> str:
    payload = _extract_channel_payload(content_obj, channel)
    for key in fallback_keys:
        value = _coerce_string(payload.get(key), "")
        if value:
            return value
    return _coerce_string(content_obj.get("text"), "")


def _dispatch_email_channel(
    campaign: Campaign,
    leads: List[Dict[str, Any]],
    content_obj: Dict[str, Any],
) -> int:
    email_content = _resolve_email_subject_body(
        campaign_name=campaign.campaign_name,
        content_obj=content_obj,
        raw_content=campaign.content,
    )
    subject = email_content["subject"]
    body = email_content["body"]

    sent = 0
    seen_emails = set()
    for lead in leads:
        email = (lead.get("email") or "").strip()
        if not email:
            print("[smtp_debug] skip_missing_email", lead.get("id"), lead.get("source"))
            continue
        email_key = email.lower()
        if email_key in seen_emails:
            print("[smtp_debug] skip_duplicate_email", email)
            continue
        seen_emails.add(email_key)
        print("[smtp_debug] sending to", email)
        success = send_email_via_smtp(email, subject, body)
        print("[smtp_debug] send_success", success)
        if success:
            sent += 1
    return sent


def _dispatch_linkedin_channel(campaign: Campaign, content_obj: Dict[str, Any]) -> int:
    post = _resolve_channel_message(content_obj, "linkedin", ["post", "content", "message"])
    if not post:
        print(f"[channel_dispatch] linkedin_skipped campaign_id={campaign.id} reason=no_content")
        return 0
    print(f"[channel_dispatch] linkedin_placeholder campaign_id={campaign.id} content_len={len(post)}")
    return 0


def _dispatch_facebook_channel(campaign: Campaign, content_obj: Dict[str, Any]) -> int:
    post = _resolve_channel_message(content_obj, "facebook", ["post", "content", "message"])
    if not post:
        print(f"[channel_dispatch] facebook_skipped campaign_id={campaign.id} reason=no_content")
        return 0
    print(f"[channel_dispatch] facebook_placeholder campaign_id={campaign.id} content_len={len(post)}")
    return 0


def _dispatch_twitter_channel(campaign: Campaign, content_obj: Dict[str, Any]) -> int:
    tweet = _resolve_channel_message(content_obj, "twitter", ["tweet", "post", "content", "message"])
    if not tweet:
        print(f"[channel_dispatch] twitter_skipped campaign_id={campaign.id} reason=no_content")
        return 0
    print(f"[channel_dispatch] twitter_placeholder campaign_id={campaign.id} content_len={len(tweet)}")
    return 0


def _dispatch_whatsapp_channel(campaign: Campaign, content_obj: Dict[str, Any]) -> int:
    message = _resolve_channel_message(content_obj, "whatsapp", ["message", "content", "post"])
    if not message:
        print(f"[channel_dispatch] whatsapp_skipped campaign_id={campaign.id} reason=no_content")
        return 0
    print(f"[channel_dispatch] whatsapp_placeholder campaign_id={campaign.id} content_len={len(message)}")
    return 0


async def execute_campaign(
    campaign_id: str,
    db: Session,
    organization_id: str,
    auth_header: Optional[str] = None,
) -> Dict[str, Any]:
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.organization_id == organization_id,
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    metric = (
        db.query(CampaignMetric)
        .filter(
            CampaignMetric.campaign_id == campaign_id,
            CampaignMetric.organization_id == organization_id,
        )
        .first()
    )
    if not metric:
        metric = CampaignMetric(
            campaign_id=campaign_id,
            organization_id=organization_id,
            sent=0,
            opened=0,
            clicked=0,
            converted=0,
            impressions=0,
            cost=0.0,
            ctr=0.0,
            conversion_rate=0.0,
            cpa=0.0,
            roi=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(metric)

    audience_source = campaign.audience_source or "scraped_leads"
    manual_selection = campaign.manual_selection if isinstance(campaign.manual_selection, list) else []

    print(
        f"[campaign_debug] execute_campaign campaign_id={campaign_id} "
        f"org={organization_id} source={audience_source!r}"
    )

    try:
        leads = await get_audience_leads(
            organization_id=organization_id,
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
    if audience_source in {"customer_upload", "scraped_leads"}:
        content_obj = _parse_campaign_content(campaign.content)

        selected_channels = campaign.channels if isinstance(campaign.channels, list) else []
        normalized_channels = [str(ch).strip().lower() for ch in selected_channels if str(ch).strip()]
        if not normalized_channels:
            normalized_channels = ["email"]

        if "email" in normalized_channels:
            sent += _dispatch_email_channel(campaign, leads, content_obj)
        if "linkedin" in normalized_channels:
            _dispatch_linkedin_channel(campaign, content_obj)
        if "facebook" in normalized_channels:
            _dispatch_facebook_channel(campaign, content_obj)
        if "twitter" in normalized_channels:
            _dispatch_twitter_channel(campaign, content_obj)
        if "whatsapp" in normalized_channels:
            _dispatch_whatsapp_channel(campaign, content_obj)

    # Real interaction tracking endpoints are not implemented yet.
    # Keep engagement metrics at zero until actual events are recorded.
    opened = 0
    clicked = 0
    converted = 0

    try:
        now = datetime.utcnow()
        campaign.status = "active"
        campaign.deployed_at = now
        campaign.updated_at = now

        metric.sent = sent
        metric.opened = opened
        metric.clicked = clicked
        metric.converted = converted
        metric.updated_at = now

        db.commit()
        db.refresh(campaign)
        db.refresh(metric)
    except Exception:
        db.rollback()
        raise

    return _campaign_row_to_response(campaign, metric)


# ===== CAMPAIGN MANAGEMENT =====

def _get_strategy_context_for_campaign(
    db: Session,
    organization_id: str,
    strategy_id: str,
    strategy_version_no: Optional[int] = None,
) -> Dict[str, Any]:
    strategy = (
        db.query(Strategy)
        .filter(
            Strategy.id == strategy_id,
            Strategy.organization_id == organization_id,
        )
        .first()
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    version = None
    if strategy_version_no is not None:
        version = (
            db.query(StrategyVersion)
            .filter(
                StrategyVersion.strategy_id == strategy_id,
                StrategyVersion.organization_id == organization_id,
                StrategyVersion.version_no == strategy_version_no,
            )
            .first()
        )
        if not version:
            raise HTTPException(status_code=404, detail="Strategy version not found")
    else:
        version = (
            db.query(StrategyVersion)
            .filter(
                StrategyVersion.strategy_id == strategy_id,
                StrategyVersion.organization_id == organization_id,
                StrategyVersion.is_current == True,  # noqa: E712
            )
            .order_by(StrategyVersion.version_no.desc())
            .first()
        )
    if not version:
        version = (
            db.query(StrategyVersion)
            .filter(
                StrategyVersion.strategy_id == strategy_id,
                StrategyVersion.organization_id == organization_id,
            )
            .order_by(StrategyVersion.version_no.desc())
            .first()
        )
    if not version:
        raise HTTPException(status_code=404, detail="Strategy version not found")

    business_profile = version.business_profile_json if isinstance(version.business_profile_json, dict) else {}
    strategy_output = version.strategy_output_json if isinstance(version.strategy_output_json, dict) else {}
    return {
        "strategy": strategy,
        "version_no": int(version.version_no),
        "business_profile": business_profile,
        "strategy_output": strategy_output,
    }


def _parse_possible_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    text = _coerce_string(value, "")
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except Exception:
        return None


def _extract_schedule_window_from_timeline(timeline: Any) -> Dict[str, Optional[datetime]]:
    if not isinstance(timeline, dict):
        return {"schedule_date": None, "start_date": None, "end_date": None}

    all_dates: List[datetime] = []
    start_candidates: List[datetime] = []
    end_candidates: List[datetime] = []

    for key in ("start_date", "start", "launch_date", "scheduled_at"):
        dt = _parse_possible_datetime(timeline.get(key))
        if dt:
            start_candidates.append(dt)
            all_dates.append(dt)
    for key in ("end_date", "end", "finish_date"):
        dt = _parse_possible_datetime(timeline.get(key))
        if dt:
            end_candidates.append(dt)
            all_dates.append(dt)

    for _, phase_value in timeline.items():
        if isinstance(phase_value, dict):
            for key in ("start_date", "start", "date", "launch_date", "scheduled_at"):
                dt = _parse_possible_datetime(phase_value.get(key))
                if dt:
                    start_candidates.append(dt)
                    all_dates.append(dt)
            for key in ("end_date", "end", "finish_date"):
                dt = _parse_possible_datetime(phase_value.get(key))
                if dt:
                    end_candidates.append(dt)
                    all_dates.append(dt)

    start_date = min(start_candidates) if start_candidates else (min(all_dates) if all_dates else None)
    end_date = max(end_candidates) if end_candidates else (max(all_dates) if len(all_dates) > 1 else None)

    if start_date and end_date and end_date < start_date:
        start_date, end_date = end_date, start_date

    schedule_date = start_date
    return {
        "schedule_date": schedule_date,
        "start_date": start_date,
        "end_date": end_date,
    }


def _build_content_prefill_from_strategy(content_strategy: Any) -> Optional[str]:
    if isinstance(content_strategy, list):
        cleaned = [str(item).strip() for item in content_strategy if str(item).strip()]
        if cleaned:
            return json.dumps({"content_strategy": cleaned})
    elif isinstance(content_strategy, dict):
        return json.dumps({"content_strategy": content_strategy})
    elif isinstance(content_strategy, str):
        text = content_strategy.strip()
        if text:
            return json.dumps({"content_strategy": [text]})
    return None


def _derive_budget_from_strategy(strategy_output: Dict[str, Any], business_profile: Dict[str, Any]) -> Optional[float]:
    budget_allocation = strategy_output.get("budget_allocation")
    if isinstance(budget_allocation, dict):
        direct_keys = ("total_budget", "budget", "recommended_budget", "monthly_budget")
        for key in direct_keys:
            raw = budget_allocation.get(key)
            if isinstance(raw, (int, float)) and float(raw) > 0:
                return float(raw)
            if isinstance(raw, str):
                match = re.search(r"(\d+(?:\.\d+)?)", raw.replace(",", ""))
                if match:
                    value = float(match.group(1))
                    if value > 0:
                        return value

    budget_range = _coerce_string(business_profile.get("budget_range"), "")
    if budget_range:
        numbers = re.findall(r"(\d+(?:\.\d+)?)", budget_range.replace(",", ""))
        if len(numbers) == 1:
            value = float(numbers[0])
            if value > 0:
                return value
        if len(numbers) >= 2:
            low = float(numbers[0])
            high = float(numbers[1])
            if low > 0 and high > 0:
                return (low + high) / 2.0
            if high > 0:
                return high
            if low > 0:
                return low
    return None


@app.post("/api/campaigns/from-strategy", tags=["Campaigns"])
async def create_campaign_from_strategy(
    payload: StrategyCampaignRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    strategy_id = str(payload.strategy_id or "").strip()
    auto_map = True if payload.auto_map is None else bool(payload.auto_map)
    if not strategy_id:
        raise HTTPException(status_code=422, detail="strategy_id is required")

    idempotency_key = _coerce_string(request.headers.get("idempotency-key"), "")
    if idempotency_key:
        cached_campaign_id = _get_cached_campaign_id(current_user["organization_id"], idempotency_key)
        if cached_campaign_id:
            return {
                "success": True,
                "campaign_id": cached_campaign_id,
                "message": "Campaign created from strategy (idempotent replay)",
                "idempotent_replay": True,
            }

    context = _get_strategy_context_for_campaign(
        db=db,
        organization_id=current_user["organization_id"],
        strategy_id=strategy_id,
        strategy_version_no=payload.strategy_version_no,
    )

    strategy = context["strategy"]
    version_no = context["version_no"]
    business_profile = context["business_profile"]
    strategy_output = context["strategy_output"]

    channels: List[str] = ["Email", "LinkedIn"]
    target_audience = "General B2B audience"
    schedule_date = None
    start_date = None
    end_date = None
    content = None
    budget = None
    kpis: List[str] = []

    if auto_map:
        channels_raw = strategy_output.get("recommended_channels")
        mapped_channels: List[str] = []
        if isinstance(channels_raw, list):
            mapped_channels = [str(item).strip() for item in channels_raw if str(item).strip()]
        if mapped_channels:
            channels = mapped_channels

        target_audience = _coerce_string(business_profile.get("target_audience"), "")
        if not target_audience:
            segments = strategy_output.get("target_segments")
            if isinstance(segments, list) and segments:
                mapped_segments = [str(item).strip() for item in segments if str(item).strip()]
                if mapped_segments:
                    target_audience = ", ".join(mapped_segments)
        if not target_audience:
            target_audience = "General B2B audience"

        schedule_window = _extract_schedule_window_from_timeline(strategy_output.get("campaign_timeline"))
        schedule_date = schedule_window.get("schedule_date")
        start_date = schedule_window.get("start_date")
        end_date = schedule_window.get("end_date")
        content = _build_content_prefill_from_strategy(strategy_output.get("content_strategy"))
        budget = _derive_budget_from_strategy(strategy_output, business_profile)

        kpis_raw = strategy_output.get("kpis")
        if isinstance(kpis_raw, list):
            kpis = [str(item).strip() for item in kpis_raw if str(item).strip()]
    else:
        # Preserve existing defaulting behavior when auto_map is disabled.
        channels_raw = strategy_output.get("recommended_channels")
        default_channels = []
        if isinstance(channels_raw, list):
            default_channels = [str(item).strip() for item in channels_raw if str(item).strip()]
        if default_channels:
            channels = default_channels

        target_audience = _coerce_string(business_profile.get("target_audience"), "")
        if not target_audience:
            segments = strategy_output.get("target_segments")
            if isinstance(segments, list) and segments:
                target_audience = ", ".join([str(item).strip() for item in segments if str(item).strip()])
        if not target_audience:
            target_audience = "General B2B audience"

    campaign_id = str(uuid.uuid4())
    now = datetime.utcnow()
    campaign_name = f"{strategy.business_name} AI Strategy Campaign"

    try:
        db_campaign = Campaign(
            id=campaign_id,
            organization_id=current_user["organization_id"],
            strategy_id=strategy.id,
            strategy_version_no=version_no,
            campaign_name=campaign_name,
            channels=channels,
            target_audience=target_audience,
            content=content,
            schedule_date=schedule_date,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            audience_source="scraped_leads",
            manual_selection=[],
            status="draft",
            created_at=now,
            updated_at=now,
            deployed_at=None,
        )
        db.add(db_campaign)

        db_metric = CampaignMetric(
            campaign_id=campaign_id,
            organization_id=current_user["organization_id"],
            sent=0,
            opened=0,
            clicked=0,
            converted=0,
            impressions=0,
            cost=0.0,
            ctr=0.0,
            conversion_rate=0.0,
            cpa=0.0,
            roi=0.0,
            created_at=now,
            updated_at=now,
        )
        db.add(db_metric)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create campaign from strategy: {str(exc)}")

    _cache_campaign_id(current_user["organization_id"], idempotency_key, campaign_id)

    return {
        "success": True,
        "campaign_id": campaign_id,
        "message": "Campaign created from strategy",
        "strategy_metadata": {
            "strategy_id": strategy.id,
            "strategy_version_no": version_no,
            "kpis": kpis,
            "auto_map": auto_map,
        },
    }

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
        idempotency_key = _coerce_string(request.headers.get("idempotency-key"), "")
        manual_count = len(campaign.manual_selection or [])

        if idempotency_key:
            cached_campaign_id = _get_cached_campaign_id(current_user["organization_id"], idempotency_key)
            if cached_campaign_id:
                cached_row = (
                    db.query(Campaign, CampaignMetric)
                    .outerjoin(CampaignMetric, CampaignMetric.campaign_id == Campaign.id)
                    .filter(
                        Campaign.id == cached_campaign_id,
                        Campaign.organization_id == current_user["organization_id"],
                    )
                    .first()
                )
                if cached_row:
                    cached_campaign, cached_metric = cached_row
                    return {
                        "success": True,
                        "campaign": _campaign_row_to_response(cached_campaign, cached_metric),
                        "idempotent_replay": True,
                    }

        print(
            f"[campaign_debug] create_campaign campaign_id={campaign_id} "
            f"org={current_user.get('organization_id')} source={audience_source!r} "
            f"manual_selection_len={manual_count} auth_header_present={bool(auth_header)}"
        )

        try:
            _validate_strategy_link(
                db=db,
                organization_id=current_user["organization_id"],
                strategy_id=campaign.strategy_id,
                strategy_version_no=campaign.strategy_version_no,
            )

            db_campaign = Campaign(
                id=campaign_id,
                organization_id=current_user["organization_id"],
                strategy_id=campaign.strategy_id,
                strategy_version_no=campaign.strategy_version_no,
                campaign_name=campaign.campaign_name,
                channels=campaign.channels,
                target_audience=campaign.target_audience,
                content=campaign.content,
                schedule_date=campaign.schedule_date,
                start_date=campaign.start_date,
                end_date=campaign.end_date,
                budget=campaign.budget,
                audience_source=audience_source,
                manual_selection=campaign.manual_selection or [],
                status="draft",
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
                deployed_at=None,
            )
            db.add(db_campaign)

            db_metric = CampaignMetric(
                campaign_id=campaign_id,
                organization_id=current_user["organization_id"],
                sent=0,
                opened=0,
                clicked=0,
                converted=0,
                impressions=0,
                cost=0.0,
                ctr=0.0,
                conversion_rate=0.0,
                cpa=0.0,
                roi=0.0,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
            )
            db.add(db_metric)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to persist campaign: {str(e)}")

        updated_campaign = await execute_campaign(
            campaign_id,
            db=db,
            organization_id=current_user["organization_id"],
            auth_header=auth_header,
        )
        _cache_campaign_id(current_user["organization_id"], idempotency_key, campaign_id)

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
    request: Request,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Schedule campaign for deployment"""
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user["organization_id"],
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.status = "scheduled"
    campaign.updated_at = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    background_tasks.add_task(
        _deploy_campaign_task,
        campaign_id,
        current_user["organization_id"],
        request.headers.get("authorization"),
    )

    return {
        "success": True,
        "message": "Campaign scheduled successfully",
        "campaign_id": campaign_id,
    }


@app.post("/api/campaigns/{campaign_id}/launch", tags=["Campaigns"])
async def launch_campaign(
    campaign_id: str,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Explicitly launch a campaign (strategy-first flow)."""
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user["organization_id"],
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    current_status = str(campaign.status or "").lower()
    if current_status not in {"draft", "scheduled"}:
        raise HTTPException(
            status_code=409,
            detail=f"Campaign cannot be launched from status '{current_status}'",
        )

    updated_campaign = await execute_campaign(
        campaign_id=campaign_id,
        db=db,
        organization_id=current_user["organization_id"],
        auth_header=request.headers.get("authorization"),
    )

    return {
        "success": True,
        "message": "Campaign launched successfully",
        "campaign": updated_campaign,
    }


async def _deploy_campaign_task(campaign_id: str, organization_id: str, auth_header: Optional[str] = None):
    """Background task for campaign deployment"""
    db = SessionLocal()
    try:
        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == campaign_id,
                Campaign.organization_id == organization_id,
            )
            .first()
        )
        if not campaign:
            return

        await execute_campaign(
            campaign_id=campaign_id,
            db=db,
            organization_id=organization_id,
            auth_header=auth_header,
        )
    except Exception as e:
        db.rollback()
        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == campaign_id,
                Campaign.organization_id == organization_id,
            )
            .first()
        )
        if campaign:
            campaign.status = "failed"
            campaign.updated_at = datetime.utcnow()
            db.commit()
        print(f"[campaign_debug] deploy_task_failed campaign_id={campaign_id} error={str(e)}")
    finally:
        db.close()


async def _deploy_to_channel(campaign_id: str, channel: str, campaign_data: dict):
    """Deploy campaign to specific channel"""
    pass


def _set_campaign_status(
    db: Session,
    campaign_id: str,
    organization_id: str,
    target_status: str,
    allowed_from: Optional[set] = None,
    already_message: Optional[str] = None,
    success_message: Optional[str] = None,
) -> Dict[str, Any]:
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.organization_id == organization_id,
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    current_status = str(campaign.status or "").lower()
    normalized_target = str(target_status or "").lower()

    if current_status == normalized_target:
        metric = (
            db.query(CampaignMetric)
            .filter(
                CampaignMetric.campaign_id == campaign_id,
                CampaignMetric.organization_id == organization_id,
            )
            .first()
        )
        return {
            "success": True,
            "message": already_message or f"Campaign already {normalized_target}",
            "campaign": _campaign_row_to_response(campaign, metric),
        }

    if allowed_from and current_status not in allowed_from:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change campaign from '{current_status}' to '{normalized_target}'",
        )

    campaign.status = normalized_target
    campaign.updated_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(campaign)
    except Exception as exc:
        db.rollback()
        # Additive safeguard for environments where 'stopped' constraint migration isn't applied yet.
        if normalized_target == "stopped":
            raise HTTPException(
                status_code=409,
                detail="Campaign status 'stopped' is not enabled in database yet. Apply migration first.",
            )
        raise HTTPException(status_code=500, detail=f"Failed to update campaign status: {str(exc)}")

    metric = (
        db.query(CampaignMetric)
        .filter(
            CampaignMetric.campaign_id == campaign_id,
            CampaignMetric.organization_id == organization_id,
        )
        .first()
    )
    return {
        "success": True,
        "message": success_message or f"Campaign {normalized_target} successfully",
        "campaign": _campaign_row_to_response(campaign, metric),
    }


@app.get("/api/campaigns", tags=["Campaigns"])
async def get_campaigns(
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Get all campaigns for the organization"""
    rows = (
        db.query(Campaign, CampaignMetric)
        .outerjoin(CampaignMetric, CampaignMetric.campaign_id == Campaign.id)
        .filter(Campaign.organization_id == current_user["organization_id"])
        .order_by(Campaign.created_at.desc())
        .all()
    )

    org_campaigns = [_campaign_row_to_response(campaign, metric) for campaign, metric in rows]

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

    campaign, metric = row
    campaign_payload = _campaign_row_to_response(campaign, metric)

    return {
        "success": True,
        "campaign": campaign_payload,
    }


@app.put("/api/campaigns/{campaign_id}", tags=["Campaigns"])
async def update_campaign(
    campaign_id: str,
    payload: CampaignUpdateRequest,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Update campaign details"""
    try:
        db_campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == campaign_id,
                Campaign.organization_id == current_user["organization_id"],
            )
            .first()
        )
        if db_campaign:
            strategy_id_to_validate = payload.strategy_id if payload.strategy_id is not None else db_campaign.strategy_id
            strategy_version_to_validate = (
                payload.strategy_version_no if payload.strategy_version_no is not None else db_campaign.strategy_version_no
            )
            _validate_strategy_link(
                db=db,
                organization_id=current_user["organization_id"],
                strategy_id=strategy_id_to_validate,
                strategy_version_no=strategy_version_to_validate,
            )

            if payload.campaign_name is not None:
                db_campaign.campaign_name = payload.campaign_name
            if payload.channels is not None:
                db_campaign.channels = payload.channels
            if payload.target_audience is not None:
                db_campaign.target_audience = payload.target_audience
            if payload.content is not None:
                db_campaign.content = payload.content
            if payload.schedule_date is not None:
                db_campaign.schedule_date = payload.schedule_date
            if payload.start_date is not None:
                db_campaign.start_date = payload.start_date
            if payload.end_date is not None:
                db_campaign.end_date = payload.end_date
            if payload.budget is not None:
                db_campaign.budget = payload.budget
            if payload.strategy_id is not None:
                db_campaign.strategy_id = payload.strategy_id
            if payload.strategy_version_no is not None:
                db_campaign.strategy_version_no = payload.strategy_version_no
            db_campaign.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(db_campaign)
        else:
            db.rollback()
            raise HTTPException(status_code=404, detail="Campaign not found")
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update campaign persistence: {str(e)}")

    db_metric = (
        db.query(CampaignMetric)
        .filter(
            CampaignMetric.campaign_id == campaign_id,
            CampaignMetric.organization_id == current_user["organization_id"],
        )
        .first()
    )

    return {
        "success": True,
        "campaign": _campaign_row_to_response(db_campaign, db_metric),
    }


@app.post("/api/campaigns/{campaign_id}/pause", tags=["Campaigns"])
async def pause_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Pause/unpause campaign"""
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user["organization_id"],
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    current_status = str(campaign.status or "").lower()
    campaign.status = "active" if current_status == "paused" else "paused"
    campaign.updated_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(campaign)
    except Exception:
        db.rollback()
        raise

    metric = (
        db.query(CampaignMetric)
        .filter(
            CampaignMetric.campaign_id == campaign_id,
            CampaignMetric.organization_id == current_user["organization_id"],
        )
        .first()
    )

    return {
        "success": True,
        "campaign": _campaign_row_to_response(campaign, metric),
    }


@app.patch("/api/campaigns/{campaign_id}/pause", tags=["Campaigns"])
async def pause_campaign_explicit(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Explicit pause endpoint (additive, legacy POST toggle remains unchanged)."""
    return _set_campaign_status(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user["organization_id"],
        target_status="paused",
        allowed_from={"active", "scheduled"},
        already_message="Campaign already paused",
        success_message="Campaign paused successfully",
    )


@app.patch("/api/campaigns/{campaign_id}/resume", tags=["Campaigns"])
async def resume_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Resume paused campaign to active."""
    return _set_campaign_status(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user["organization_id"],
        target_status="active",
        allowed_from={"paused", "stopped"},
        already_message="Campaign already active",
        success_message="Campaign resumed successfully",
    )


@app.patch("/api/campaigns/{campaign_id}/stop", tags=["Campaigns"])
async def stop_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Stop campaign execution."""
    return _set_campaign_status(
        db=db,
        campaign_id=campaign_id,
        organization_id=current_user["organization_id"],
        target_status="stopped",
        allowed_from={"draft", "scheduled", "active", "paused"},
        already_message="Campaign already stopped",
        success_message="Campaign stopped successfully",
    )


@app.delete("/api/campaigns/{campaign_id}", tags=["Campaigns"])
async def delete_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db),
):
    """Delete campaign (additive endpoint, no changes to existing flows)."""
    campaign = (
        db.query(Campaign)
        .filter(
            Campaign.id == campaign_id,
            Campaign.organization_id == current_user["organization_id"],
        )
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    metric = (
        db.query(CampaignMetric)
        .filter(
            CampaignMetric.campaign_id == campaign_id,
            CampaignMetric.organization_id == current_user["organization_id"],
        )
        .first()
    )

    try:
        if metric:
            db.delete(metric)
        db.delete(campaign)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete campaign: {str(exc)}")

    return {
        "success": True,
        "message": "Campaign deleted successfully",
        "campaign_id": campaign_id,
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

