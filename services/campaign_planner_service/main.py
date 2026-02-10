# MAi Campaign Planner Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
import uuid
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, FeatureName
from shared.auth import get_current_user, require_feature

app = FastAPI(
    title="MAi Campaign Planner Service",
    description="Multi-Channel Campaign Management - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
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
campaigns_data = {}
campaign_analytics = {}

# ===== REQUEST MODELS =====

class CampaignRequest(BaseModel):
    campaign_name: str = Field(..., description="Name of the campaign")
    channels: List[str] = Field(..., description="Marketing channels to use")
    target_audience: str = Field(..., description="Target audience for the campaign")
    content: Optional[str] = Field(None, description="Campaign content")
    schedule_date: Optional[datetime] = Field(None, description="When to schedule the campaign")
    budget: Optional[float] = Field(None, description="Campaign budget")

# ===== CAMPAIGN MANAGEMENT =====

@app.post("/api/campaigns/create", tags=["Campaigns"])
async def create_campaign(
    campaign: CampaignRequest,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db)
):
    """Create a new marketing campaign"""
    try:
        campaign_id = str(uuid.uuid4())
        
        campaign_data = {
            "campaign_id": campaign_id,
            "organization_id": current_user["organization_id"],
            "campaign_name": campaign.campaign_name,
            "channels": campaign.channels,
            "target_audience": campaign.target_audience,
            "content": campaign.content,
            "schedule_date": campaign.schedule_date.isoformat() if campaign.schedule_date else None,
            "budget": campaign.budget,
            "status": "draft",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        campaigns_data[campaign_id] = campaign_data
        
        # Initialize analytics
        campaign_analytics[campaign_id] = {
            "campaign_id": campaign_id,
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
            "cost": 0.0,
            "ctr": 0.0,
            "conversion_rate": 0.0,
            "cpa": 0.0,
            "roi": 0.0
        }
        
        return {
            "success": True,
            "message": "Campaign created successfully",
            "campaign_id": campaign_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {str(e)}")

@app.post("/api/campaigns/{campaign_id}/schedule", tags=["Campaigns"])
async def schedule_campaign(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db)
):
    """Schedule campaign for deployment"""
    if campaign_id not in campaigns_data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = campaigns_data[campaign_id]
    if campaign["organization_id"] != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Start deployment task
    background_tasks.add_task(_deploy_campaign_task, campaign_id)
    
    campaigns_data[campaign_id]["status"] = "scheduled"
    campaigns_data[campaign_id]["updated_at"] = datetime.utcnow().isoformat()
    
    return {
        "success": True,
        "message": "Campaign scheduled successfully",
        "campaign_id": campaign_id
    }

async def _deploy_campaign_task(campaign_id: str):
    """Background task for campaign deployment"""
    try:
        campaign = campaigns_data[campaign_id]
        
        # TODO: Integrate with actual channel APIs
        # For now, simulate deployment
        for channel in campaign["channels"]:
            await _deploy_to_channel(campaign_id, channel, campaign)
        
        campaigns_data[campaign_id]["status"] = "active"
        campaigns_data[campaign_id]["deployed_at"] = datetime.utcnow().isoformat()
    except Exception as e:
        campaigns_data[campaign_id]["status"] = "failed"
        campaigns_data[campaign_id]["error"] = str(e)

async def _deploy_to_channel(campaign_id: str, channel: str, campaign_data: dict):
    """Deploy campaign to specific channel"""
    # TODO: Integrate with channel APIs
    pass

@app.get("/api/campaigns", tags=["Campaigns"])
async def get_campaigns(
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db)
):
    """Get all campaigns for the organization"""
    org_campaigns = [
        campaign for campaign in campaigns_data.values()
        if campaign["organization_id"] == current_user["organization_id"]
    ]
    
    return {
        "success": True,
        "campaigns": org_campaigns
    }

@app.get("/api/campaigns/{campaign_id}", tags=["Campaigns"])
async def get_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.CAMPAIGN_PLANNER)),
    db: Session = Depends(get_db)
):
    """Get campaign details"""
    if campaign_id not in campaigns_data:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign = campaigns_data[campaign_id]
    if campaign["organization_id"] != current_user["organization_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "success": True,
        "campaign": campaign
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "campaign_planner_service",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005, reload=True)
