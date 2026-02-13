# MAi StrategyAI Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import sys
import os
import logging

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from shared.database import get_db
from shared.auth import get_current_user, require_feature, FeatureName
from shared.strategy_providers import StrategyProviderFactory
from shared.config import (
    load_channel_config, load_budget_config, load_segments_config,
    load_content_strategy_config, load_kpi_config, load_timeline_config
)

app = FastAPI(
    title="MAi StrategyAI Service",
    description="AI-Powered Marketing Strategy Generation - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== REQUEST MODELS =====

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

# ===== STRATEGY GENERATION =====

@app.post("/api/strategy/generate", tags=["Strategy"])
async def generate_marketing_strategy(
    request: StrategyRequest,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.STRATEGY_AI)),
    db: Session = Depends(get_db)
):
    """
    Generate AI-powered marketing strategy based on business profile.
    This is the PRIMARY entry point for non-admin users (Strategy-First approach).
    
    Uses configurable strategy provider (Ollama local or OpenAI API).
    Set STRATEGY_PROVIDER env var to 'ollama' or 'openai', or 'auto' for auto-detection.
    """
    try:
        profile = request.business_profile
        
        # Get strategy provider (Ollama or OpenAI)
        provider = StrategyProviderFactory.create_provider()
        
        # Prepare business profile dict
        profile_dict = {
            "business_name": profile.business_name,
            "industry": profile.industry,
            "company_size": profile.company_size,
            "revenue": profile.revenue,
            "geography": profile.geography,
            "marketing_goals": profile.marketing_goals,
            "budget_range": profile.budget_range,
            "target_audience": profile.target_audience
        }
        
        # Generate strategy using AI provider
        ai_strategy = await provider.generate_strategy(
            business_profile=profile_dict,
            additional_context=request.additional_context
        )
        
        # Build complete strategy response with AI-generated data
        strategy = {
            "strategy_id": str(uuid.uuid4()),
            "organization_id": current_user["organization_id"],
            "business_name": profile.business_name,
            "industry": profile.industry,
            "recommended_channels": ai_strategy.get("recommended_channels", []),
            "budget_allocation": ai_strategy.get("budget_allocation", {}),
            "budget_analysis": ai_strategy.get("budget_analysis", {}),  # AI-generated budget analysis
            "target_segments": ai_strategy.get("target_segments", []),
            "campaign_timeline": ai_strategy.get("campaign_timeline", {}),  # AI-generated timeline
            "content_strategy": ai_strategy.get("content_strategy", []),
            "kpis": ai_strategy.get("kpis", []),
            "insights": ai_strategy.get("insights", ""),
            "risk_assessment": ai_strategy.get("risk_assessment", ""),
            "marketing_goals": profile.marketing_goals,
            "generated_at": datetime.utcnow().isoformat(),
            "provider_info": {
                "provider": ai_strategy.get("provider", "unknown"),
                "model": ai_strategy.get("model", "unknown")
            }
        }

        return {
            "success": True,
            "strategy": strategy,
            "next_steps": [
                "Review and customize the strategy",
                "Proceed to lead generation (if licensed)",
                "Create content campaigns (if licensed)",
                "Set up campaign automation (if licensed)"
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate marketing strategy: {str(e)}"
        )

@app.get("/api/strategy/providers", tags=["Strategy"])
async def get_available_providers(
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.STRATEGY_AI)),
    db: Session = Depends(get_db)
):
    """Get list of available strategy providers"""
    available = StrategyProviderFactory.get_available_providers()
    current_provider = os.getenv("STRATEGY_PROVIDER", "auto")
    
    return {
        "success": True,
        "available_providers": available,
        "current_provider": current_provider,
        "provider_info": {
            "ollama": {
                "type": "local",
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
                "model": os.getenv("OLLAMA_STRATEGY_MODEL", "llama2")
            },
            "openai": {
                "type": "api",
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
                "configured": bool(os.getenv("OPENAI_API_KEY"))
            }
        }
    }

@app.get("/api/strategy/history", tags=["Strategy"])
async def get_strategy_history(
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.STRATEGY_AI)),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10
):
    """Get strategy generation history for the organization"""
    # TODO: Store strategies in database
    # For now, return placeholder
    return {
        "success": True,
        "strategies": [],
        "message": "Strategy history will be stored in database"
    }

# Timeline generation removed - now using config-driven approach via load_timeline_config()

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        logger.debug("[HEALTH_DEBUG] Health check requested")
    except Exception:
        pass
    return {
        "status": "healthy",
        "service": "strategy_ai_service",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)
