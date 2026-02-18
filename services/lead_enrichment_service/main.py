# MAi Lead Enrichment Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any
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

from typing import Optional

class LeadScrapingRequest(BaseModel):
    location: str = Field(..., description="Geographic location for lead search")
    business_type: str = Field(..., description="Type of businesses to search for")
    radius: Optional[int] = Field(10, description="Search radius in kilometers")
    max_results: Optional[int] = Field(100, description="Maximum number of results")

# ===== LEAD SCRAPING =====

@app.post("/api/leads/scrape", tags=["Lead Generation"])
async def start_lead_scraping(
    request: LeadScrapingRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.LEAD_ENRICHMENT)),
    db: Session = Depends(get_db)
):
    """Start Google Maps lead scraping task"""
    try:
        task_id = str(uuid.uuid4())
        
        # Record usage
        _record_usage(db, current_user["organization_id"], FeatureName.LEAD_ENRICHMENT)
        
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start lead scraping: {str(e)}")

async def _scrape_leads_task(task_id: str, request: LeadScrapingRequest, org_id: str):
    """Background task for lead scraping"""
    try:
        import httpx


        try:
            github_status_code = None
            max_results = max(1, min(int(request.max_results or 1), 100))

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.github.com/search/users",
                    params={"q": request.business_type, "per_page": max_results},
                )
                github_status_code = response.status_code

                if response.status_code in (403, 429):
                    raise Exception(f"GitHub API rate-limited or forbidden: {response.status_code}")
                if response.status_code != 200:
                    raise Exception(f"GitHub API returned status {response.status_code}")

                response_json = response.json()
                items = response_json.get("items", []) if isinstance(response_json, dict) else []

                sample_leads = []
                for user in items:
                    if not isinstance(user, dict):
                        continue

                    login = user.get("login")
                    html_url = user.get("html_url")
                    if not login or not html_url:
                        continue

                    posts = []

                    user_details_response = await client.get(
                        f"https://api.github.com/users/{login}"
                    )
                    if user_details_response.status_code == 200:
                        user_details = user_details_response.json()
                        if isinstance(user_details, dict):
                            bio = user_details.get("bio")
                            if bio:
                                posts.append({"text": bio, "source": "bio"})

                    repos_response = await client.get(
                        f"https://api.github.com/users/{login}/repos",
                        params={"per_page": 5},
                    )
                    if repos_response.status_code == 200:
                        repos_data = repos_response.json()
                        if isinstance(repos_data, list):
                            for repo in repos_data:
                                if not isinstance(repo, dict):
                                    continue
                                description = repo.get("description")
                                if description:
                                    posts.append({"text": description, "source": "repo"})

                    ranked_posts = rank_posts_for_lead(
                        {"business_name": login},
                        posts,
                        request.location,
                        request.business_type,
                    )

                    sample_leads.append(
                        {
                            "business_name": login,
                            "address": "N/A",
                            "phone": "N/A",
                            "email": "N/A",
                            "website": html_url,
                            "rating": None,
                            "category": request.business_type,
                            "scraped_at": datetime.utcnow().isoformat(),
                            "ranked_posts": ranked_posts,
                        }
                    )

            if not sample_leads:
                raise Exception("No valid users returned from GitHub API")

        except Exception as e:
            # TODO: Integrate with Google Maps API, Outscraper, or Apify
            # Placeholder implementation
            sample_leads = [
                {
                    "business_name": f"Tech Solutions {i}",
                    "address": f"{100 + i} Business St, {request.location}",
                    "phone": f"+1-555-{1000 + i}",
                    "email": f"contact@techsolutions{i}.com",
                    "website": f"https://techsolutions{i}.com",
                    "rating": round(3.5 + (i % 2) * 0.8, 1),
                    "category": request.business_type,
                    "scraped_at": datetime.utcnow().isoformat()
                }
                for i in range(min(request.max_results, 25))
            ]

        leads_data[task_id] = {
            "task_id": task_id,
            "organization_id": org_id,
            "status": "completed",
            "leads": sample_leads,
            "total_found": len(sample_leads),
            "search_params": request.dict(),
            "completed_at": datetime.utcnow().isoformat()
        }
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
        
        # Record usage
        _record_usage(db, current_user["organization_id"], FeatureName.LEAD_ENRICHMENT)
        
        # Start enrichment task
        background_tasks.add_task(
            _enrich_customer_data_task,
            task_id,
            df.to_dict('records'),
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
            "enriched_data": enriched_data,
            "completed_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        enriched_customers[task_id] = {
            "task_id": task_id,
            "organization_id": org_id,
            "status": "failed",
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
