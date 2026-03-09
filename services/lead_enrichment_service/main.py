# MAi Lead Enrichment Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
from uuid import UUID
import pandas as pd
import io
import sys
import os

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
)
from shared.auth import get_current_user, require_feature
from services.lead_enrichment_service.relevance_ranker import rank_posts_for_lead

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
    location: str = Field(..., description="Geographic location for lead search")
    business_type: str = Field(..., description="Type of businesses to search for")
    radius: Optional[int] = Field(10, description="Search radius in kilometers")
    max_results: Optional[int] = Field(100, description="Maximum number of results")
    sources: Optional[List[str]] = Field(None, description="Lead sources to query")


class StrategyLeadRequest(BaseModel):
    strategy_id: str = Field(..., description="Source strategy ID")

# ===== LEAD SCRAPING =====

SUPPORTED_SOURCES = ["github", "google_maps", "linkedin", "volza"]
SOURCE_API_KEY_ENV = {
    "google_maps": "GOOGLE_MAPS_API_KEY",
    "linkedin": "LINKEDIN_API_KEY",
    "volza": "VOLZA_API_KEY"
}


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


async def _scrape_github_leads(request: LeadScrapingRequest) -> Tuple[str, List[Dict[str, Any]], str]:
    token = os.getenv("GITHUB_API_TOKEN")
    if not token:
        return "error", [], "GitHub API token not configured."

    max_results = max(1, min(int(request.max_results or 30), 30))
    query = f"location:{request.location} {request.business_type} in:bio"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        import httpx

        async with httpx.AsyncClient(timeout=15) as client:
            search_response = await client.get(
                "https://api.github.com/search/users",
                params={
                    "q": query,
                    "per_page": max_results,
                    "page": 1,
                    "type": "Users",
                },
                headers=headers,
            )

            if search_response.status_code == 403:
                remaining = search_response.headers.get("X-RateLimit-Remaining", "")
                if remaining == "0":
                    return "error", [], "GitHub API rate limit exceeded."
                return "error", [], "GitHub API access forbidden."

            if search_response.status_code != 200:
                return "error", [], f"GitHub API returned status {search_response.status_code}."

            search_json = search_response.json() if search_response.content else {}
            items = search_json.get("items", []) if isinstance(search_json, dict) else []

            leads: List[Dict[str, Any]] = []
            for item in items:
                if not isinstance(item, dict):
                    continue

                username = item.get("login")
                if not username:
                    continue

                user_response = await client.get(
                    f"https://api.github.com/users/{username}",
                    headers=headers,
                )
                if user_response.status_code == 403 and user_response.headers.get("X-RateLimit-Remaining") == "0":
                    return "error", leads, "GitHub API rate limit exceeded."
                if user_response.status_code != 200:
                    continue

                user_data = user_response.json() if user_response.content else {}
                if not isinstance(user_data, dict):
                    continue

                repos_response = await client.get(
                    f"https://api.github.com/users/{username}/repos",
                    params={"sort": "updated", "per_page": 5},
                    headers=headers,
                )

                repos_data = repos_response.json() if repos_response.status_code == 200 and repos_response.content else []
                top_repos = [
                    repo.get("name")
                    for repo in repos_data[:3]
                    if isinstance(repo, dict) and repo.get("name")
                ]

                business_name = user_data.get("company") or user_data.get("login") or username
                website = user_data.get("blog") or user_data.get("html_url") or "N/A"

                lead = {
                    "business_name": business_name,
                    "contact_name": user_data.get("name") or "N/A",
                    "email": user_data.get("email") or "N/A",
                    "phone": None,
                    "website": website,
                    "address": user_data.get("location") or request.location,
                    "source": "github",
                    "category": request.business_type,
                    "scraped_at": datetime.utcnow().isoformat(),
                    "metadata": {
                        "followers": user_data.get("followers", 0),
                        "public_repos": user_data.get("public_repos", 0),
                        "top_repos": top_repos,
                        "bio": user_data.get("bio") or "",
                    },
                }
                leads.append(lead)

            return "success", leads, ""
    except Exception as e:
        return "error", [], f"GitHub scraping failed: {str(e)}"


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

    task_id = str(uuid.uuid4())
    _record_usage(db, current_user["organization_id"], FeatureName.LEAD_ENRICHMENT)

    try:
        db_task = LeadScrapeTask(
            id=task_id,
            organization_id=current_user["organization_id"],
            location=request_model.location,
            business_type=request_model.business_type,
            radius=request_model.radius,
            max_results=request_model.max_results,
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
        raise HTTPException(status_code=500, detail=f"Failed to persist strategy lead task: {str(exc)}")

    background_tasks.add_task(
        _scrape_leads_task,
        task_id,
        request_model,
        current_user["organization_id"],
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
        selected_sources = _normalize_sources(request.sources)
        if not selected_sources:
            raise HTTPException(status_code=422, detail="At least one valid source is required")

        task_id = str(uuid.uuid4())

        # Record usage
        _record_usage(db, current_user["organization_id"], FeatureName.LEAD_ENRICHMENT)

        try:
            db_task = LeadScrapeTask(
                id=task_id,
                organization_id=current_user["organization_id"],
                location=request.location,
                business_type=request.business_type,
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
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to persist scrape task: {str(e)}")

        # Start background task
        background_tasks.add_task(
            _scrape_leads_task,
            task_id,
            request,
            current_user["organization_id"]
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


async def _scrape_leads_task(task_id: str, request: LeadScrapingRequest, org_id: str):
    """Background task for multi-source lead scraping"""
    db = SessionLocal()
    try:
        sources = _normalize_sources(request.sources)
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

            if source == "github":
                status, leads, message = await _scrape_github_leads(request)
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
                    results[source] = {
                        "status": "error",
                        "message": message or "GitHub scraping failed.",
                    }
                    db_source_run.status = TaskStatus.FAILED
                    db_source_run.leads_count = len(leads) if isinstance(leads, list) else 0
                    db_source_run.message = message or "GitHub scraping failed."
                    db_source_run.completed_at = datetime.utcnow()
                    try:
                        db.commit()
                    except Exception:
                        db.rollback()
                        raise
                continue

            env_var = SOURCE_API_KEY_ENV.get(source)
            if env_var and not os.getenv(env_var):
                source_label = source.replace("_", " ").title()
                results[source] = {
                    "status": "error",
                    "message": f"{source_label} not configured. API key missing.",
                }
                db_source_run.status = TaskStatus.FAILED
                db_source_run.leads_count = 0
                db_source_run.message = f"{source_label} not configured. API key missing."
                db_source_run.completed_at = datetime.utcnow()
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
            else:
                source_label = source.replace("_", " ").title()
                results[source] = {
                    "status": "error",
                    "message": f"{source_label} source is not configured.",
                }
                db_source_run.status = TaskStatus.FAILED
                db_source_run.leads_count = 0
                db_source_run.message = f"{source_label} source is not configured."
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
        
        task_id = str(uuid.uuid4())
        original_rows = df.to_dict('records')
        
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
