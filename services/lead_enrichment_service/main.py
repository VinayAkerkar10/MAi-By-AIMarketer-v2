# MAi Lead Enrichment Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import time
import uuid
from uuid import UUID
import pandas as pd
import io
import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from shared.database import (
    get_db,
    SessionLocal,
    UsageRecord,
    FeatureName,
    LeadScrapeTask,
    LeadSourceRun,
    LeadScrapeResult,
    EnrichmentTask,
    EnrichmentRow,
    TaskStatus,
    LeadSource,
    Strategy,
    StrategyVersion,
    ApiUsageAuditLog,
    Organization,
    User,
    UserRole,
)
from shared.auth import get_current_user, require_feature
from services.lead_enrichment_service.relevance_ranker import rank_posts_for_lead
from services.lead_enrichment_service.providers.provider_registry import get_provider

app = FastAPI(
    title="MAi Lead Enrichment Service",
    description="Lead Scraping and Data Enrichment - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lead scraping and enrichment now use PostgreSQL persistence.

# ===== REQUEST MODELS =====


class LeadScrapingRequest(BaseModel):
    location: Optional[Union[str, Dict[str, Any]]] = Field(None, description="Geographic location for lead search")
    business_type: Optional[str] = Field(None, description="Type of businesses to search for")
    radius: Optional[int] = Field(10, description="Search radius in kilometers")
    max_results: Optional[int] = Field(100, description="Maximum number of results")
    sources: Optional[List[str]] = Field(None, description="Lead sources to query")
    website_url: Optional[str] = Field(None, description="Website URL for browser-extension based scraping")
    extension_payload: Optional[Dict[str, Any]] = Field(None, description="Structured payload from browser extension")

    @model_validator(mode="after")
    def validate_search_input(self) -> "LeadScrapingRequest":
        # Allow either the legacy search fields or browser-extension context.
        location_text = _extract_location_text(self.location)
        business_type = str(self.business_type or "").strip()
        website_url = str(self.website_url or "").strip()
        extension_payload = self.extension_payload

        has_existing_search_fields = bool(location_text and business_type)
        has_browser_context = bool(website_url or extension_payload)

        if not has_existing_search_fields and not has_browser_context:
            raise ValueError(
                "Provide either location and business_type, or website_url/extension_payload."
            )

        if extension_payload is not None and not isinstance(extension_payload, dict):
            raise ValueError("extension_payload must be an object.")

        return self


class StrategyLeadRequest(BaseModel):
    strategy_id: str = Field(..., description="Source strategy ID")

# ===== LEAD SCRAPING =====

SUPPORTED_SOURCES = ["github", "google_maps", "linkedin", "volza", "browser_extension"]


def _to_task_status(value: str) -> TaskStatus:
    status_map = {
        "pending": TaskStatus.PENDING,
        "processing": TaskStatus.RUNNING,
        "running": TaskStatus.RUNNING,
        "completed": TaskStatus.COMPLETED,
        "failed": TaskStatus.FAILED,
        "partial": TaskStatus.PARTIAL,
        "cancelled": TaskStatus.CANCELLED,
    }
    return status_map.get(str(value or "").lower(), TaskStatus.FAILED)


def _to_legacy_task_status(status: TaskStatus) -> str:
    if status == TaskStatus.RUNNING:
        return "processing"
    if status == TaskStatus.COMPLETED:
        return "completed"
    if status == TaskStatus.FAILED:
        return "failed"
    if status == TaskStatus.PENDING:
        return "processing"
    if status == TaskStatus.PARTIAL:
        return "completed"
    if status == TaskStatus.CANCELLED:
        return "failed"
    return "failed"


def _to_lead_source(source: str) -> LeadSource:
    source_map = {
        "github": LeadSource.GITHUB,
        "google_maps": LeadSource.GOOGLE_MAPS,
        "linkedin": LeadSource.LINKEDIN,
        "volza": LeadSource.VOLZA,
        "browser_extension": LeadSource.BROWSER_EXTENSION,
    }
    return source_map[str(source or "").lower()]


def _source_enum_to_key(source: LeadSource) -> str:
    return str(source.value if isinstance(source, LeadSource) else source)


def _enrichment_status_to_legacy(status: TaskStatus) -> str:
    if status == TaskStatus.RUNNING:
        return "processing"
    if status == TaskStatus.COMPLETED:
        return "completed"
    if status == TaskStatus.FAILED:
        return "failed"
    if status == TaskStatus.PENDING:
        return "processing"
    if status == TaskStatus.PARTIAL:
        return "completed"
    if status == TaskStatus.CANCELLED:
        return "failed"
    return "failed"


def _enrichment_task_to_legacy_payload(task: EnrichmentTask, rows: List[EnrichmentRow]) -> Dict[str, Any]:
    ordered_rows = sorted(rows, key=lambda row: row.row_index if isinstance(row.row_index, int) else 0)
    original_data = [row.original_data for row in ordered_rows]
    enriched_data = [row.enriched_data for row in ordered_rows if row.enriched_data is not None]

    return {
        "task_id": task.id,
        "organization_id": task.organization_id,
        "status": _enrichment_status_to_legacy(task.status),
        "original_count": int(task.original_count or len(original_data)),
        "enriched_count": int(task.enriched_count or len(enriched_data)),
        "original_data": original_data,
        "enriched_data": enriched_data,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error": task.error,
    }


def _lead_row_to_payload(row: LeadScrapeResult) -> Dict[str, Any]:
    if isinstance(row.raw_payload, dict):
        return row.raw_payload

    payload = {
        "business_name": row.business_name,
        "contact_name": row.contact_name,
        "email": row.email,
        "phone": row.phone,
        "website": row.website,
        "address": row.address,
        "source": _source_enum_to_key(row.source),
        "category": row.category,
        "metadata": row.meta_data or {},
        "scraped_at": row.created_at.isoformat() if row.created_at else datetime.utcnow().isoformat(),
    }
    return payload


def _build_results_from_runs(
    source_runs: List[LeadSourceRun],
    source_to_leads: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    results: Dict[str, Dict[str, Any]] = {}
    for run in source_runs:
        source_key = _source_enum_to_key(run.source)
        run_status = _to_legacy_task_status(run.status)
        if run_status == "completed":
            results[source_key] = {
                "status": "success",
                "leads": source_to_leads.get(source_key, []),
            }
        else:
            results[source_key] = {
                "status": "error",
                "message": run.message or "Source scraping failed.",
            }
    return results


def _lead_scrape_task_to_legacy_payload(
    task: LeadScrapeTask,
    source_runs: List[LeadSourceRun],
    lead_rows: List[LeadScrapeResult],
) -> Dict[str, Any]:
    leads_payload = [_lead_row_to_payload(row) for row in lead_rows]

    source_to_leads: Dict[str, List[Dict[str, Any]]] = {}
    for lead in leads_payload:
        source_key = str(lead.get("source") or "")
        source_to_leads.setdefault(source_key, []).append(lead)

    results_payload = (
        task.source_results
        if isinstance(task.source_results, dict)
        else _build_results_from_runs(source_runs, source_to_leads)
    )

    summary_payload = (
        task.summary
        if isinstance(task.summary, dict)
        else {
            "total_sources_requested": len(task.requested_sources or []),
            "successful_sources": sum(1 for r in results_payload.values() if r.get("status") == "success"),
            "failed_sources": sum(1 for r in results_payload.values() if r.get("status") == "error"),
        }
    )

    return {
        "task_id": task.id,
        "organization_id": task.organization_id,
        "status": _to_legacy_task_status(task.status),
        "leads": leads_payload,
        "total_found": int(task.total_found or len(leads_payload)),
        "search_params": {
            "location": task.location,
            "business_type": task.business_type,
            "radius": task.radius,
            "max_results": task.max_results,
            "sources": task.requested_sources if isinstance(task.requested_sources, list) else [],
            "website_url": task.location if "browser_extension" in (task.requested_sources or []) else None,
            "has_extension_payload": "browser_extension" in (task.requested_sources or []),
        },
        "results": results_payload,
        "summary": summary_payload,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error": task.error,
    }


def _normalize_sources(sources: Optional[List[str]]) -> List[str]:
    if not sources:
        return ["github"]

    normalized: List[str] = []
    for source in sources:
        value = str(source or "").strip().lower()
        if not value:
            continue
        if value == "all":
            return SUPPORTED_SOURCES.copy()
        if value in SUPPORTED_SOURCES and value not in normalized:
            normalized.append(value)

    return normalized


def _extract_location_text(location_value: Union[str, Dict[str, Any]]) -> str:
    if isinstance(location_value, dict):
        text = str(location_value.get("text") or "").strip()
        return text
    return str(location_value or "").strip()


def _has_browser_extension_context(request: LeadScrapingRequest) -> bool:
    return bool(str(request.website_url or "").strip() or request.extension_payload)


def _resolve_sources_for_request(request: LeadScrapingRequest) -> List[str]:
    if _has_browser_extension_context(request):
        return ["browser_extension"]
    return _normalize_sources(request.sources)


def _build_normalized_scrape_request(request: LeadScrapingRequest) -> LeadScrapingRequest:
    location_text = _extract_location_text(request.location)
    business_type = str(request.business_type or "").strip() or "Website Leads"
    extension_payload = request.extension_payload if isinstance(request.extension_payload, dict) else None
    website_url = (
        str(request.website_url or "").strip()
        or str((extension_payload or {}).get("website_url") or (extension_payload or {}).get("page_url") or "").strip()
        or None
    )

    return LeadScrapingRequest(
        location=location_text or None,
        business_type=business_type,
        radius=request.radius,
        max_results=request.max_results,
        sources=request.sources,
        website_url=website_url,
        extension_payload=extension_payload,
    )


def _task_location_value(request: LeadScrapingRequest) -> str:
    if _has_browser_extension_context(request):
        extension_payload = request.extension_payload if isinstance(request.extension_payload, dict) else {}
        return str(
            request.website_url
            or extension_payload.get("website_url")
            or extension_payload.get("page_url")
            or _extract_location_text(request.location)
            or "browser_extension"
        ).strip()
    return _extract_location_text(request.location)


def _task_business_type_value(request: LeadScrapingRequest) -> str:
    return str(request.business_type or "").strip() or "Website Leads"


def _create_scrape_task_record(
    db: Session,
    request: LeadScrapingRequest,
    organization_id: str,
) -> str:
    selected_sources = _resolve_sources_for_request(request)
    if not selected_sources:
        raise HTTPException(status_code=422, detail="At least one valid source is required")

    task_id = str(uuid.uuid4())
    _record_usage(db, organization_id, FeatureName.LEAD_ENRICHMENT)

    try:
        db_task = LeadScrapeTask(
            id=task_id,
            organization_id=organization_id,
            location=_task_location_value(request),
            business_type=_task_business_type_value(request),
            radius=request.radius,
            max_results=request.max_results,
            requested_sources=selected_sources,
            status=TaskStatus.RUNNING,
            total_found=0,
            source_results=None,
            summary=None,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(db_task)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to persist scrape task: {str(exc)}")

    return task_id


def _apply_column_mapping_to_rows(
    rows: List[Dict[str, Any]],
    mapping: Optional[Dict[str, str]],
) -> List[Dict[str, Any]]:
    if not mapping:
        return rows

    normalized_mapping: Dict[str, str] = {}
    for src, dst in mapping.items():
        src_key = str(src or "").strip()
        dst_key = str(dst or "").strip()
        if src_key and dst_key and dst_key.lower() != "none":
            normalized_mapping[src_key] = dst_key

    if not normalized_mapping:
        return rows

    transformed_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            transformed_rows.append(row)
            continue

        # Preserve original keys for backward compatibility, while adding canonical mapped keys.
        mapped_row = dict(row)
        for src_key, dst_key in normalized_mapping.items():
            if src_key in row:
                mapped_row[dst_key] = row.get(src_key)
        transformed_rows.append(mapped_row)

    return transformed_rows


def _send_api_usage_email_alert(
    organization_name: str,
    recipients: List[str],
    user_id: str,
    provider_name: str,
    timestamp: datetime,
    duration: float,
) -> None:
    if not recipients:
        return

    from email.mime.text import MIMEText
    import smtplib

    subject = "API Usage Notification"
    body = (
        f"User: {user_id}\n"
        f"Organization: {organization_name}\n"
        f"Provider: {provider_name}\n"
        f"Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Duration: {round(duration, 3)} seconds\n"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = "noreply@aimarketer.local"
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP("mailhog", 1025, timeout=10) as smtp:
            smtp.sendmail(msg["From"], recipients, msg.as_string())
    except Exception:
        # Notification failures should not block scraping.
        pass


def _build_location_from_profile(profile: Dict[str, Any]) -> str:
    region = str(profile.get("region") or "").strip()
    country = str(profile.get("country") or "").strip()
    continent = str(profile.get("continent") or "").strip()
    parts = [part for part in [region, country, continent] if part]
    return ", ".join(parts) if parts else "Global"


@app.post("/api/leads/from-strategy", tags=["Lead Generation"])
async def start_lead_scraping_from_strategy(
    payload: StrategyLeadRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db),
):
    strategy_id = str(payload.strategy_id or "").strip()
    if not strategy_id:
        raise HTTPException(status_code=422, detail="strategy_id is required")

    strategy = (
        db.query(Strategy)
        .filter(
            Strategy.id == strategy_id,
            Strategy.organization_id == current_user["organization_id"],
        )
        .first()
    )
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    version = (
        db.query(StrategyVersion)
        .filter(
            StrategyVersion.strategy_id == strategy_id,
            StrategyVersion.organization_id == current_user["organization_id"],
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
                StrategyVersion.organization_id == current_user["organization_id"],
            )
            .order_by(StrategyVersion.version_no.desc())
            .first()
        )
    if not version:
        raise HTTPException(status_code=404, detail="Strategy version not found")

    business_profile = version.business_profile_json if isinstance(version.business_profile_json, dict) else {}
    industry = str(business_profile.get("industry") or strategy.industry or "").strip() or "B2B Services"
    location = _build_location_from_profile(business_profile)
    selected_sources = ["github"]

    request_model = LeadScrapingRequest(
        location=location,
        business_type=industry,
        radius=10,
        max_results=100,
        sources=selected_sources,
    )
    task_id = _create_scrape_task_record(db, request_model, current_user["organization_id"])

    background_tasks.add_task(
        _scrape_leads_task,
        task_id,
        request_model,
        current_user["organization_id"],
        current_user["user_id"],
    )

    return {
        "success": True,
        "job_id": task_id,
        "message": "Lead generation started from strategy",
    }


@app.post("/api/leads/scrape", tags=["Lead Generation"])
async def start_lead_scraping(
    request: LeadScrapingRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db)
):
    """Start lead scraping task"""
    try:
        normalized_request = _build_normalized_scrape_request(request)
        task_id = _create_scrape_task_record(db, normalized_request, current_user["organization_id"])

        background_tasks.add_task(
            _scrape_leads_task,
            task_id,
            normalized_request,
            current_user["organization_id"],
            current_user["user_id"],
        )

        return {
            "success": True,
            "message": "Lead scraping task started",
            "task_id": task_id,
            "estimated_completion": "5-10 minutes"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start lead scraping: {str(e)}")


@app.post("/api/leads/from-extension", tags=["Lead Generation"])
async def start_lead_scraping_from_extension(
    request: LeadScrapingRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db),
):
    normalized_request = _build_normalized_scrape_request(request)
    if not _has_browser_extension_context(normalized_request):
        raise HTTPException(
            status_code=422,
            detail="website_url or extension_payload is required for extension scraping",
        )

    task_id = _create_scrape_task_record(db, normalized_request, current_user["organization_id"])
    background_tasks.add_task(
        _scrape_leads_task,
        task_id,
        normalized_request,
        current_user["organization_id"],
        current_user["user_id"],
    )

    return {
        "success": True,
        "message": "Lead scraping task started from extension payload",
        "task_id": task_id,
        "estimated_completion": "1-2 minutes",
    }


async def _scrape_leads_task(
    task_id: str,
    request: LeadScrapingRequest,
    org_id: str,
    user_id: str,
):
    """Background task for multi-source lead scraping"""
    db = SessionLocal()
    try:
        sources = _resolve_sources_for_request(request)
        results: Dict[str, Dict[str, Any]] = {}
        all_leads: List[Dict[str, Any]] = []

        for source in sources:
            db_source_run = (
                db.query(LeadSourceRun)
                .filter(
                    LeadSourceRun.task_id == task_id,
                    LeadSourceRun.organization_id == org_id,
                    LeadSourceRun.source == _to_lead_source(source),
                )
                .first()
            )
            if not db_source_run:
                db_source_run = LeadSourceRun(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    organization_id=org_id,
                    source=_to_lead_source(source),
                    status=TaskStatus.RUNNING,
                    message=None,
                    leads_count=0,
                    created_at=datetime.utcnow(),
                    completed_at=None,
                )
                db.add(db_source_run)
            else:
                db_source_run.status = TaskStatus.RUNNING
                db_source_run.message = None
                db_source_run.completed_at = None
            try:
                db.commit()
            except Exception:
                db.rollback()
                raise

            source_label = source.replace("_", " ").title()
            org_context = {
                "organization_id": org_id,
                "source": source,
                "db_session": db,
                "request": request,
            }

            provider = get_provider(source)
            provider_started_at = datetime.utcnow()
            provider_started_ts = time.perf_counter()
            if not provider:
                status = "error"
                leads = []
                message = f"{source_label} source is not configured."
            else:
                is_configured = provider.validate_config(org_context)
                if not is_configured:
                    status = "error"
                    leads = []
                    message = "Provider not configured for this organization."
                else:
                    status, leads, message = await provider.scrape(request, org_context)
            provider_duration = max(0.0, time.perf_counter() - provider_started_ts)

            try:
                db.add(
                    ApiUsageAuditLog(
                        id=str(uuid.uuid4()),
                        organization_id=org_id,
                        task_id=task_id,
                        user_id=str(user_id or ""),
                        provider_name=source,
                        timestamp=provider_started_at,
                        duration=provider_duration,
                        success=status == "success",
                        error_message=None if status == "success" else (message or f"{source_label} scraping failed."),
                        lead_count=len(leads) if isinstance(leads, list) else 0,
                    )
                )
                db.commit()
            except Exception:
                db.rollback()

            try:
                org_row = db.query(Organization).filter(Organization.id == org_id).first()
                organization_name = org_row.name if org_row else org_id
                admin_rows = (
                    db.query(User)
                    .filter(
                        User.organization_id == org_id,
                        User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]),
                        User.is_active == True,  # noqa: E712
                        User.email.isnot(None),
                    )
                    .all()
                )
                recipients = [
                    str(admin.email).strip()
                    for admin in admin_rows
                    if str(admin.email or "").strip()
                ]
                _send_api_usage_email_alert(
                    organization_name=organization_name,
                    recipients=recipients,
                    user_id=str(user_id or ""),
                    provider_name=source,
                    timestamp=provider_started_at,
                    duration=provider_duration,
                )
            except Exception:
                pass

            if status == "success":
                results[source] = {
                    "status": "success",
                    "leads": leads,
                }
                all_leads.extend(leads)
                db_source_run.status = TaskStatus.COMPLETED
                db_source_run.leads_count = len(leads)
                db_source_run.completed_at = datetime.utcnow()
                db_source_run.message = None
                lead_rows = []
                for lead in leads:
                    lead_rows.append(
                        LeadScrapeResult(
                            id=str(uuid.uuid4()),
                            task_id=task_id,
                            organization_id=org_id,
                            source=_to_lead_source(source),
                            business_name=lead.get("business_name"),
                            contact_name=lead.get("contact_name"),
                            email=lead.get("email"),
                            phone=lead.get("phone"),
                            website=lead.get("website"),
                            address=lead.get("address"),
                            category=lead.get("category"),
                            meta_data=lead.get("metadata"),
                            raw_payload=lead,
                            created_at=datetime.utcnow(),
                        )
                    )
                db.add_all(lead_rows)
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
            else:
                failure_message = message or f"{source_label} scraping failed."
                results[source] = {
                    "status": "error",
                    "message": failure_message,
                }
                db_source_run.status = TaskStatus.FAILED
                db_source_run.leads_count = len(leads) if isinstance(leads, list) else 0
                db_source_run.message = failure_message
                db_source_run.completed_at = datetime.utcnow()
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    raise

        successful_sources = sum(1 for data in results.values() if data.get("status") == "success")
        failed_sources = len(results) - successful_sources

        task_status = "completed" if successful_sources > 0 else "failed"
        task_payload = {
            "task_id": task_id,
            "organization_id": org_id,
            "status": task_status,
            "leads": all_leads,
            "total_found": len(all_leads),
            "search_params": {
                **request.dict(),
                "sources": sources,
            },
            "results": results,
            "summary": {
                "total_sources_requested": len(sources),
                "successful_sources": successful_sources,
                "failed_sources": failed_sources,
            },
            "completed_at": datetime.utcnow().isoformat(),
        }

        if task_status == "failed":
            task_payload["error"] = "All selected sources failed."

        try:
            db_task = (
                db.query(LeadScrapeTask)
                .filter(
                    LeadScrapeTask.id == task_id,
                    LeadScrapeTask.organization_id == org_id,
                )
                .first()
            )
            if db_task:
                db_task.status = _to_task_status(task_status)
                db_task.total_found = len(all_leads)
                db_task.source_results = results
                db_task.summary = task_payload["summary"]
                db_task.error = task_payload.get("error")
                db_task.completed_at = datetime.utcnow()
                db_task.updated_at = datetime.utcnow()
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
            raise
    except Exception as e:
        try:
            db_task = (
                db.query(LeadScrapeTask)
                .filter(
                    LeadScrapeTask.id == task_id,
                    LeadScrapeTask.organization_id == org_id,
                )
                .first()
            )
            if db_task:
                db_task.status = TaskStatus.FAILED
                db_task.error = str(e)
                db_task.completed_at = datetime.utcnow()
                db_task.updated_at = datetime.utcnow()
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
    finally:
        db.close()

@app.get("/api/leads/tasks", tags=["Lead Generation"])
async def list_scraped_lead_tasks(
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db)
):
    """List all lead scraping tasks for organization"""
    org_id = current_user["organization_id"]
    db_tasks = (
        db.query(LeadScrapeTask)
        .filter(LeadScrapeTask.organization_id == org_id)
        .order_by(LeadScrapeTask.created_at.desc())
        .all()
    )

    tasks = []
    for task in db_tasks:
        source_runs = (
            db.query(LeadSourceRun)
            .filter(
                LeadSourceRun.task_id == task.id,
                LeadSourceRun.organization_id == org_id,
            )
            .all()
        )
        lead_rows = (
            db.query(LeadScrapeResult)
            .filter(
                LeadScrapeResult.task_id == task.id,
                LeadScrapeResult.organization_id == org_id,
            )
            .all()
        )
        tasks.append(_lead_scrape_task_to_legacy_payload(task, source_runs, lead_rows))

    return {
        "success": True,
        "tasks": tasks
    }

@app.get("/api/leads/{task_id}", tags=["Lead Generation"])
async def get_scraped_leads(
    # task_id: str,
    task_id: UUID,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db)
):
    """Get scraped leads by task ID"""
    org_id = current_user["organization_id"]
    task_id = str(task_id)
    db_task = (
        db.query(LeadScrapeTask)
        .filter(
            LeadScrapeTask.id == task_id,
            LeadScrapeTask.organization_id == org_id,
        )
        .first()
    )
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    source_runs = (
        db.query(LeadSourceRun)
        .filter(
            LeadSourceRun.task_id == task_id,
            LeadSourceRun.organization_id == org_id,
        )
        .all()
    )
    lead_rows = (
        db.query(LeadScrapeResult)
        .filter(
            LeadScrapeResult.task_id == task_id,
            LeadScrapeResult.organization_id == org_id,
        )
        .all()
    )
    task_data = _lead_scrape_task_to_legacy_payload(db_task, source_runs, lead_rows)

    return {
        "success": True,
        "data": task_data
    }

# ===== DATA ENRICHMENT =====

@app.post("/api/enrichment/upload", tags=["Data Enrichment"])
async def upload_customer_data(
    file: UploadFile = File(...),
    column_mapping: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db)
):
    """Upload customer data file for enrichment"""
    try:
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
        
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        parsed_mapping: Optional[Dict[str, str]] = None
        if column_mapping:
            try:
                candidate_mapping = json.loads(column_mapping)
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid column_mapping JSON")
            if not isinstance(candidate_mapping, dict):
                raise HTTPException(status_code=422, detail="column_mapping must be a JSON object")
            parsed_mapping = {str(k): str(v) for k, v in candidate_mapping.items()}

        task_id = str(uuid.uuid4())
        original_rows = df.to_dict('records')
        original_rows = _apply_column_mapping_to_rows(original_rows, parsed_mapping)
        
        # Record usage
        _record_usage(db, current_user["organization_id"], FeatureName.LEAD_ENRICHMENT)

        try:
            db_task = EnrichmentTask(
                id=task_id,
                organization_id=current_user["organization_id"],
                status=TaskStatus.RUNNING,
                original_count=len(original_rows),
                enriched_count=0,
                error=None,
                created_at=datetime.utcnow(),
                started_at=datetime.utcnow(),
                completed_at=None,
                updated_at=datetime.utcnow(),
            )
            db.add(db_task)
            db.commit()
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to persist enrichment task: {str(e)}")
        
        # Start enrichment task
        background_tasks.add_task(
            _enrich_customer_data_task,
            task_id,
            original_rows,
            current_user["organization_id"]
        )
        
        return {
            "success": True,
            "message": "Customer data uploaded successfully. Enrichment started.",
            "task_id": task_id,
            "records_count": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload customer data: {str(e)}")


@app.post("/api/enrichment/preview-csv", tags=["Data Enrichment"])
async def preview_csv_columns(
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
):
    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file.file, nrows=5)
        else:
            df = pd.read_excel(file.file, nrows=5)

        df = df.where(pd.notna(df), None)
        return {
            "columns": [str(column) for column in list(df.columns)],
            "preview": df.to_dict("records"),
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse file preview: {str(exc)}")

async def _enrich_customer_data_task(task_id: str, customer_data: List[Dict], org_id: str):
    """Background task for customer data enrichment"""
    db = SessionLocal()
    try:
        db_task = (
            db.query(EnrichmentTask)
            .filter(
                EnrichmentTask.id == task_id,
                EnrichmentTask.organization_id == org_id,
            )
            .first()
        )
        if db_task:
            db_task.status = TaskStatus.RUNNING
            db_task.updated_at = datetime.utcnow()
            db.commit()

        enriched_data = []
        
        for idx, customer in enumerate(customer_data):
            enriched_customer = customer.copy()
            
            # TODO: Integrate with Clearbit, Hunter.io, FullContact APIs
            if 'business_name' in customer:
                company_name = customer['business_name']
                enriched_customer.update({
                    'email': f"info@{company_name.lower().replace(' ', '')}.com",
                    'phone': f"+1-555-{hash(company_name) % 9000 + 1000}",
                    'website': f"https://{company_name.lower().replace(' ', '')}.com",
                    'linkedin': f"https://linkedin.com/company/{company_name.lower().replace(' ', '-')}",
                    'enriched_at': datetime.utcnow().isoformat()
                })
            
            enriched_data.append(enriched_customer)

            db.add(
                EnrichmentRow(
                    id=str(uuid.uuid4()),
                    task_id=task_id,
                    organization_id=org_id,
                    row_index=idx,
                    original_data=customer,
                    enriched_data=enriched_customer,
                    created_at=datetime.utcnow(),
                )
            )
        
        if db_task:
            db_task.status = TaskStatus.COMPLETED
            db_task.enriched_count = len(enriched_data)
            db_task.error = None
            db_task.completed_at = datetime.utcnow()
            db_task.updated_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        db.rollback()
        try:
            db_task = (
                db.query(EnrichmentTask)
                .filter(
                    EnrichmentTask.id == task_id,
                    EnrichmentTask.organization_id == org_id,
                )
                .first()
            )
            if db_task:
                db_task.status = TaskStatus.FAILED
                db_task.enriched_count = 0
                db_task.error = str(e)
                db_task.completed_at = datetime.utcnow()
                db_task.updated_at = datetime.utcnow()
                db.commit()
        except Exception:
            db.rollback()

    finally:
        db.close()

@app.get("/api/enrichment/status/{task_id}", tags=["Data Enrichment"])
async def get_enrichment_status(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db)
):
    """Get enrichment task status"""
    org_id = current_user["organization_id"]
    db_task = (
        db.query(EnrichmentTask)
        .filter(
            EnrichmentTask.id == task_id,
            EnrichmentTask.organization_id == org_id,
        )
        .first()
    )
    if not db_task:
        raise HTTPException(status_code=404, detail="Enrichment task not found")

    db_rows = (
        db.query(EnrichmentRow)
        .filter(
            EnrichmentRow.task_id == task_id,
            EnrichmentRow.organization_id == org_id,
        )
        .all()
    )
    task_data = _enrichment_task_to_legacy_payload(db_task, db_rows)
    
    return {
        "success": True,
        "status": task_data
    }

@app.get("/api/enrichment/tasks", tags=["Data Enrichment"])
async def list_enrichment_tasks(
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db)
):
    """List all enrichment tasks for organization"""
    org_id = current_user["organization_id"]
    db_tasks = (
        db.query(EnrichmentTask)
        .filter(EnrichmentTask.organization_id == org_id)
        .order_by(EnrichmentTask.created_at.desc())
        .all()
    )
    tasks = []
    for task in db_tasks:
        db_rows = (
            db.query(EnrichmentRow)
            .filter(
                EnrichmentRow.task_id == task.id,
                EnrichmentRow.organization_id == org_id,
            )
            .all()
        )
        tasks.append(_enrichment_task_to_legacy_payload(task, db_rows))

    return {
        "success": True,
        "tasks": tasks
    }

def _record_usage(db: Session, org_id: str, feature: FeatureName):
    """Record feature usage"""
    # TODO: Implement usage tracking
    pass

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "lead_enrichment_service",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004, reload=True)
