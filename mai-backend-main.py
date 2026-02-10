# MAi by AIMarketer - Backend API
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import uuid
import pandas as pd
import io
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="MAi by AIMarketer API",
    description="AI-powered B2B Digital Marketing Platform Backend - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# In-memory storage (replace with actual database in production)
business_profiles = {}
leads_data = {}
campaigns_data = {}
enriched_customers = {}
templates_data = {
    "email": [
        {"id": "email_1", "name": "B2B Cold Outreach", "content": "Hi {name}, I noticed your company..."},
        {"id": "email_2", "name": "Follow-up Sequence", "content": "Following up on our previous..."}
    ],
    "linkedin": [
        {"id": "linkedin_1", "name": "Connection Request", "content": "Hi {name}, I'd love to connect..."},
        {"id": "linkedin_2", "name": "Industry Insight Post", "content": "Industry trends show that..."}
    ],
    "whatsapp": [
        {"id": "whatsapp_1", "name": "Customer Service", "content": "Hi {name}, thanks for reaching out..."}
    ]
}

# === DATA MODELS ===

class BusinessProfile(BaseModel):
    business_name: str = Field(..., description="Name of the business")
    industry: str = Field(..., description="Industry vertical")
    company_size: str = Field(..., description="Company size category")
    revenue: Optional[float] = Field(None, description="Annual revenue")
    geography: str = Field(..., description="Geographic market")
    marketing_goals: List[str] = Field(..., description="List of marketing objectives")
    budget_range: Optional[str] = Field(None, description="Marketing budget range")
    target_audience: Optional[str] = Field(None, description="Target audience description")

class StrategyRequest(BaseModel):
    business_profile: BusinessProfile
    additional_context: Optional[str] = None

class LeadScrapingRequest(BaseModel):
    location: str = Field(..., description="Geographic location for lead search")
    business_type: str = Field(..., description="Type of businesses to search for")
    radius: Optional[int] = Field(10, description="Search radius in kilometers")
    max_results: Optional[int] = Field(100, description="Maximum number of results")

class CampaignRequest(BaseModel):
    campaign_name: str = Field(..., description="Name of the campaign")
    channels: List[str] = Field(..., description="Marketing channels to use")
    target_audience: str = Field(..., description="Target audience for the campaign")
    content: Optional[str] = Field(None, description="Campaign content")
    schedule_date: Optional[datetime] = Field(None, description="When to schedule the campaign")
    budget: Optional[float] = Field(None, description="Campaign budget")

class EnrichmentRequest(BaseModel):
    customer_data: List[Dict[str, Any]] = Field(..., description="Customer data to enrich")

# === AUTHENTICATION ===

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Placeholder authentication function.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    # In production, validate JWT token here
    if not credentials.credentials or credentials.credentials == "":
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return {"user_id": "demo_user", "company": "AIMarketer Pvt. Ltd."}

# === BUSINESS PROFILE MODULE ===

@app.post("/api/business-profile", tags=["Business Profile"])
async def create_business_profile(profile: BusinessProfile, user: dict = Depends(get_current_user)):
    """
    Create or update business profile.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    try:
        profile_id = str(uuid.uuid4())
        business_profiles[profile_id] = {
            "id": profile_id,
            "user_id": user["user_id"],
            "profile": profile.dict(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Business profile created: {profile_id}")
        return {
            "success": True,
            "message": "Business profile created successfully",
            "profile_id": profile_id,
            "created_by": "Mrityunjay Pandey, AIMarketer Pvt. Ltd."
        }
    except Exception as e:
        logger.error(f"Error creating business profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create business profile")

@app.get("/api/business-profile", tags=["Business Profile"])
async def get_business_profiles(user: dict = Depends(get_current_user)):
    """
    Get all business profiles for the current user.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    user_profiles = [
        profile for profile in business_profiles.values() 
        if profile["user_id"] == user["user_id"]
    ]
    return {
        "success": True,
        "profiles": user_profiles,
        "created_by": "Mrityunjay Pandey, AIMarketer Pvt. Ltd."
    }

# === AI STRATEGY GENERATOR MODULE ===

@app.post("/api/generate-strategy", tags=["AI Strategy"])
async def generate_marketing_strategy(request: StrategyRequest, user: dict = Depends(get_current_user)):
    """
    Generate AI-powered marketing strategy based on business profile.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    try:
        profile = request.business_profile
        
        # Placeholder AI strategy generation logic
        # In production, integrate with OpenAI GPT API and ML models
        
        strategy = {
            "strategy_id": str(uuid.uuid4()),
            "business_name": profile.business_name,
            "recommended_channels": _get_recommended_channels(profile.industry, profile.marketing_goals),
            "budget_allocation": _calculate_budget_allocation(profile.budget_range),
            "target_segments": _identify_target_segments(profile.target_audience),
            "campaign_timeline": _generate_campaign_timeline(),
            "content_strategy": _generate_content_strategy(profile.industry),
            "kpis": _define_kpis(profile.marketing_goals),
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Strategy generated for: {profile.business_name}")
        return {
            "success": True,
            "strategy": strategy,
            "created_by": "Mrityunjay Pandey, AIMarketer Pvt. Ltd."
        }
    except Exception as e:
        logger.error(f"Error generating strategy: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate marketing strategy")

def _get_recommended_channels(industry: str, goals: List[str]) -> List[str]:
    """Helper function to recommend marketing channels"""
    channel_mapping = {
        "technology": ["LinkedIn", "Email", "Content Marketing", "Webinars"],
        "healthcare": ["Email", "LinkedIn", "Industry Publications", "Conferences"],
        "finance": ["LinkedIn", "Email", "Thought Leadership", "Referrals"],
        "manufacturing": ["LinkedIn", "Trade Shows", "Email", "Direct Sales"]
    }
    return channel_mapping.get(industry.lower(), ["Email", "LinkedIn", "Social Media"])

def _calculate_budget_allocation(budget_range: Optional[str]) -> Dict[str, int]:
    """Helper function to allocate budget across channels"""
    return {
        "paid_advertising": 40,
        "content_marketing": 25,
        "email_marketing": 15,
        "social_media": 10,
        "events_webinars": 10
    }

def _identify_target_segments(target_audience: Optional[str]) -> List[str]:
    """Helper function to identify target segments"""
    return ["Decision Makers", "Influencers", "End Users", "Technical Evaluators"]

def _generate_campaign_timeline() -> Dict[str, str]:
    """Helper function to generate campaign timeline"""
    return {
        "phase_1": "Awareness Building (Months 1-2)",
        "phase_2": "Lead Generation (Months 2-4)",
        "phase_3": "Nurturing & Conversion (Months 4-6)",
        "phase_4": "Retention & Expansion (Months 6+)"
    }

def _generate_content_strategy(industry: str) -> List[str]:
    """Helper function to generate content strategy"""
    return [
        "Thought leadership articles",
        "Case studies and success stories",
        "Industry trend reports",
        "Educational webinars",
        "Product demonstrations"
    ]

def _define_kpis(goals: List[str]) -> List[str]:
    """Helper function to define KPIs"""
    return [
        "Lead generation rate",
        "Cost per acquisition (CPA)",
        "Conversion rate",
        "Email open rates",
        "Social media engagement",
        "ROI on marketing spend"
    ]

# === GOOGLE MAPS LEAD SCRAPER MODULE ===

@app.post("/api/scrape-leads", tags=["Lead Generation"])
async def start_lead_scraping(request: LeadScrapingRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    """
    Start Google Maps lead scraping task.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    try:
        task_id = str(uuid.uuid4())
        
        # Start background task for lead scraping
        background_tasks.add_task(
            _scrape_leads_task, 
            task_id, 
            request, 
            user["user_id"]
        )
        
        return {
            "success": True,
            "message": "Lead scraping task started",
            "task_id": task_id,
            "estimated_completion": "5-10 minutes",
            "created_by": "Mrityunjay Pandey, AIMarketer Pvt. Ltd."
        }
    except Exception as e:
        logger.error(f"Error starting lead scraping: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start lead scraping")

async def _scrape_leads_task(task_id: str, request: LeadScrapingRequest, user_id: str):
    """
    Background task for lead scraping.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    try:
        # Placeholder lead scraping logic
        # In production, integrate with Google Maps API, Outscraper, or Apify
        
        sample_leads = [
            {
                "business_name": f"Tech Solutions {i}",
                "address": f"{100 + i} Business St, {request.location}",
                "phone": f"+1-555-{1000 + i}",
                "email": f"contact@techsolutions{i}.com",
                "website": f"https://techsolutions{i}.com",
                "rating": round(3.5 + (i % 2) * 0.8, 1),
                "category": request.business_type,
                "scraped_at": datetime.now().isoformat()
            }
            for i in range(min(request.max_results, 25))
        ]
        
        leads_data[task_id] = {
            "task_id": task_id,
            "user_id": user_id,
            "status": "completed",
            "leads": sample_leads,
            "total_found": len(sample_leads),
            "search_params": request.dict(),
            "completed_at": datetime.now().isoformat()
        }
        
        logger.info(f"Lead scraping completed: {task_id}")
        
    except Exception as e:
        logger.error(f"Error in lead scraping task: {str(e)}")
        leads_data[task_id] = {
            "task_id": task_id,
            "user_id": user_id,
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }

@app.get("/api/leads/{task_id}", tags=["Lead Generation"])
async def get_scraped_leads(task_id: str, user: dict = Depends(get_current_user)):
    """
    Get scraped leads by task ID.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    if task_id not in leads_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = leads_data[task_id]
    if task_data["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "success": True,
        "data": task_data,
        "created_by": "Mrityunjay Pandey, AIMarketer Pvt. Ltd."
    }

@app.get("/api/leads", tags=["Lead Generation"])
async def get_all_leads(user: dict = Depends(get_current_user)):
    """
    Get all leads for the current user.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    user_leads = [
        task_data for task_data in leads_data.values()
        if task_data["user_id"] == user["user_id"]
    ]
    
    return {
        "success": True,
        "tasks": user_leads,
        "created_by": "Mrityunjay Pandey, AIMarketer Pvt. Ltd."
    }

# === CUSTOMER DATA ENRICHMENT MODULE ===

@app.post("/api/upload-customers", tags=["Data Enrichment"])
async def upload_customer_data(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    user: dict = Depends(get_current_user)
):
    """
    Upload customer data file for enrichment.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    try:
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
        
        # Read uploaded file
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        task_id = str(uuid.uuid4())
        
        # Start enrichment task
        background_tasks.add_task(
            _enrich_customer_data_task,
            task_id,
            df.to_dict('records'),
            user["user_id"]
        )
        
        return {
            "success": True,
            "message": "Customer data uploaded successfully. Enrichment started.",
            "task_id": task_id,
            "records_count": len(df),
            "created_by": "Mrityunjay Pandey, AIMarketer Pvt. Ltd."
        }
        
    except Exception as e:
        logger.error(f"Error uploading customer data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload customer data")

async def _enrich_customer_data_task(task_id: str, customer_data: List[Dict], user_id: str):
    """
    Background task for customer data enrichment.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    try:
        enriched_data = []
        
        for customer in customer_data:
            # Placeholder enrichment logic
            # In production, integrate with Clearbit, Hunter.io, FullContact APIs
            
            enriched_customer = customer.copy()
            
            # Simulate data enrichment
            if 'business_name' in customer:
                company_name = customer['business_name']
                enriched_customer.update({
                    'email': f"info@{company_name.lower().replace(' ', '')}.com",
                    'phone': f"+1-555-{hash(company_name) % 9000 + 1000}",
                    'website': f"https://{company_name.lower().replace(' ', '')}.com",
                    'linkedin': f"https://linkedin.com/company/{company_name.lower().replace(' ', '-')}",
                    'industry_enriched': _guess_industry(company_name),
                    'employee_count': _estimate_employees(company_name),
                    'enrichment_confidence': 0.75,
                    'enriched_at': datetime.now().isoformat()
                })
            
            enriched_data.append(enriched_customer)
        
        enriched_customers[task_id] = {
            "task_id": task_id,
            "user_id": user_id,
            "status": "completed",
            "original_count": len(customer_data),
            "enriched_count": len(enriched_data),
            "enriched_data": enriched_data,
            "completed_at": datetime.now().isoformat()
        }
        
        logger.info(f"Customer enrichment completed: {task_id}")
        
    except Exception as e:
        logger.error(f"Error in enrichment task: {str(e)}")
        enriched_customers[task_id] = {
            "task_id": task_id,
            "user_id": user_id,
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }

def _guess_industry(company_name: str) -> str:
    """Helper function to guess industry from company name"""
    name_lower = company_name.lower()
    if any(word in name_lower for word in ['tech', 'software', 'digital']):
        return 'Technology'
    elif any(word in name_lower for word in ['health', 'medical', 'pharma']):
        return 'Healthcare'
    elif any(word in name_lower for word in ['finance', 'bank', 'capital']):
        return 'Finance'
    else:
        return 'Other'

def _estimate_employees(company_name: str) -> str:
    """Helper function to estimate employee count"""
    # Placeholder logic
    return f"{hash(company_name) % 500 + 10}-{hash(company_name) % 500 + 100}"

@app.get("/api/enrichment-status/{task_id}", tags=["Data Enrichment"])
async def get_enrichment_status(task_id: str, user: dict = Depends(get_current_user)):
    """
    Get enrichment task status.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    if task_id not in enriched_customers:
        raise HTTPException(status_code=404, detail="Enrichment task not found")
    
    task_data = enriched_customers[task_id]
    if task_data["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "success": True,
        "status": task_data,
        "created_by": "Mrityunjay Pandey, AIMarketer Pvt. Ltd."
    }

@app.get("/api/download-enriched/{task_id}", tags=["Data Enrichment"])
async def download_enriched_data(task_id: str, user: dict = Depends(get_current_user)):
    """
    Download enriched customer data.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    if task_id not in enriched_customers:
        raise HTTPException(status_code=404, detail="Enrichment task not found")
    
    task_data = enriched_customers[task_id]
    if task_data["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if task_data["status"] != "completed":
        raise HTTPException(status_code=400, detail="Enrichment task not completed")
    
    return {
        "success": True,
        "data": task_data["enriched_data"],
        "created_by": "Mrityunjay Pandey, AIMarketer Pvt. Ltd."
    }

# Health check endpoint
@app.get("/api/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "created_by": "Mrityunjay Pandey, AIMarketer Pvt. Ltd."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)