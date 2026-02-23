# MAi Lead Enrichment Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid
import pandas as pd
import io
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from shared.database import get_db, UsageRecord, FeatureName
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

# In-memory storage (replace with database)
leads_data = {}
enriched_customers = {}

# ===== REQUEST MODELS =====


class LeadScrapingRequest(BaseModel):
    location: str = Field(..., description="Geographic location for lead search")
    business_type: str = Field(..., description="Type of businesses to search for")
    radius: Optional[int] = Field(10, description="Search radius in kilometers")
    max_results: Optional[int] = Field(100, description="Maximum number of results")
    sources: Optional[List[str]] = Field(None, description="Lead sources to query")

# ===== LEAD SCRAPING =====

SUPPORTED_SOURCES = ["github", "google_maps", "linkedin", "volza"]
SOURCE_API_KEY_ENV = {
    "google_maps": "GOOGLE_MAPS_API_KEY",
    "linkedin": "LINKEDIN_API_KEY",
    "volza": "VOLZA_API_KEY"
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

        # Create task record immediately so GET /api/leads/{task_id} never 404s due to timing
        search_params = request.dict()
        search_params["sources"] = selected_sources
        leads_data[task_id] = {
            "task_id": task_id,
            "organization_id": current_user["organization_id"],
            "status": "processing",
            "leads": [],
            "total_found": 0,
            "search_params": search_params,
            "created_at": datetime.utcnow().isoformat()
        }

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
    try:
        sources = _normalize_sources(request.sources)
        results: Dict[str, Dict[str, Any]] = {}
        all_leads: List[Dict[str, Any]] = []

        for source in sources:
            if source == "github":
                status, leads, message = await _scrape_github_leads(request)
                if status == "success":
                    results[source] = {
                        "status": "success",
                        "leads": leads,
                    }
                    all_leads.extend(leads)
                else:
                    results[source] = {
                        "status": "error",
                        "message": message or "GitHub scraping failed.",
                    }
                continue

            env_var = SOURCE_API_KEY_ENV.get(source)
            if env_var and not os.getenv(env_var):
                source_label = source.replace("_", " ").title()
                results[source] = {
                    "status": "error",
                    "message": f"{source_label} not configured. API key missing.",
                }
            else:
                source_label = source.replace("_", " ").title()
                results[source] = {
                    "status": "error",
                    "message": f"{source_label} source is not configured.",
                }

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

        leads_data[task_id] = task_payload
    except Exception as e:
        leads_data[task_id] = {
            "task_id": task_id,
            "organization_id": org_id,
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }

@app.get("/api/leads/{task_id}", tags=["Lead Generation"])
async def get_scraped_leads(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db)
):
    """Get scraped leads by task ID"""
    if task_id not in leads_data:
        raise HTTPException(status_code=404, detail="Task not found")

    task_data = leads_data[task_id]
    if task_data["organization_id"] != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "success": True,
        "data": task_data
    }

@app.get("/api/leads/tasks", tags=["Lead Generation"])
async def list_scraped_lead_tasks(
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db)
):
    """List all lead scraping tasks for organization"""
    org_id = current_user["organization_id"]
    tasks = [
        task_data
        for task_data in leads_data.values()
        if task_data.get("organization_id") == org_id
    ]

    return {
        "success": True,
        "tasks": tasks
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

        # Create task entry immediately and preserve original uploaded data
        enriched_customers[task_id] = {
            "task_id": task_id,
            "organization_id": current_user["organization_id"],
            "status": "processing",
            "original_count": len(original_rows),
            "enriched_count": 0,
            "original_data": original_rows,
            "enriched_data": [],
            "created_at": datetime.utcnow().isoformat()
        }
        
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
    try:
        enriched_data = []
        
        for customer in customer_data:
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
        
        enriched_customers[task_id] = {
            "task_id": task_id,
            "organization_id": org_id,
            "status": "completed",
            "original_count": len(customer_data),
            "enriched_count": len(enriched_data),
            "original_data": customer_data,
            "enriched_data": enriched_data,
            "completed_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        enriched_customers[task_id] = {
            "task_id": task_id,
            "organization_id": org_id,
            "status": "failed",
            "original_count": len(customer_data),
            "enriched_count": 0,
            "original_data": customer_data,
            "enriched_data": [],
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }

@app.get("/api/enrichment/status/{task_id}", tags=["Data Enrichment"])
async def get_enrichment_status(
    task_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db)
):
    """Get enrichment task status"""
    if task_id not in enriched_customers:
        raise HTTPException(status_code=404, detail="Enrichment task not found")
    
    task_data = enriched_customers[task_id]
    if task_data["organization_id"] != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
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
    tasks = [
        task_data
        for task_data in enriched_customers.values()
        if task_data.get("organization_id") == org_id
    ]

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
