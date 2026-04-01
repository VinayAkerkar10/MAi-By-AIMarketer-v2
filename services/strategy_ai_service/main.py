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
import time

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import func
from shared.database import get_db, Strategy, StrategyVersion, ContinentMaster, BusinessCategoryMaster
from shared.auth import get_current_user, require_feature, FeatureName
from shared.strategy_providers import StrategyProviderFactory, LLMProviderError
from shared.config import (
    load_channel_config, load_budget_config, load_segments_config,
    load_content_strategy_config, load_kpi_config, load_timeline_config
)

if os.getenv("ENV", "development").lower() in {"development", "dev", "local"}:
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except Exception:
        pass

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
    continent: str = Field(..., description="Continent")
    country: Optional[str] = Field(None, description="Country")
    region: Optional[str] = Field(None, description="Region")
    marketing_goals: List[str] = Field(..., description="List of marketing objectives")
    budget_range: Optional[str] = Field(None, description="Marketing budget range")
    target_audience: Optional[str] = Field(None, description="Target audience description")
    website_link: Optional[str] = Field(None, description="Business website URL")

class StrategyRequest(BaseModel):
    business_profile: BusinessProfile
    additional_context: Optional[str] = None


class LLMTestRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000, description="Prompt text for provider connectivity test")

# ===== STRATEGY GENERATION =====


def _build_geography_context(continent: str, country: Optional[str], region: Optional[str]) -> Dict[str, Any]:
    """Build structured geography context for provider prompts and persistence."""
    continent_text = str(continent or "").strip()
    country_text = str(country or "").strip()
    region_text = str(region or "").strip()

    geography_label_parts = [continent_text]
    if country_text:
        geography_label_parts.append(country_text)
    if region_text:
        geography_label_parts.append(region_text)

    return {
        "continent": continent_text,
        "country": country_text or None,
        "region": region_text or None,
        "geography": ", ".join([part for part in geography_label_parts if part]),
    }


@app.get("/api/strategy/master/continents", tags=["Master Data"])
@app.get("/api/master/continents", tags=["Master Data"])
async def get_continent_master(
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.STRATEGY_AI)),
    db: Session = Depends(get_db)
):
    rows = db.query(ContinentMaster).order_by(ContinentMaster.name.asc()).all()
    return {
        "continents": [
            {
                "id": row.id,
                "name": row.name,
            }
            for row in rows
        ]
    }


@app.get("/api/strategy/master/business-categories", tags=["Master Data"])
@app.get("/api/master/business-categories", tags=["Master Data"])
async def get_business_category_master(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rows = (
        db.query(BusinessCategoryMaster)
        .order_by(BusinessCategoryMaster.category_name.asc())
        .all()
    )
    return {
        "business_categories": [
            {
                "id": row.id,
                "category_name": row.category_name,
                "parent_category": row.parent_category,
            }
            for row in rows
        ]
    }

def normalize_website_link(website_link: Optional[str]) -> str:
    """Normalize and validate website link for strategy context."""
    normalized = (website_link or '').strip()
    if not normalized:
        raise HTTPException(status_code=422, detail='website_link is required')

    if len(normalized) > 500:
        raise HTTPException(status_code=422, detail='website_link must be 500 characters or fewer')

    if not normalized.startswith(('http://', 'https://')):
        normalized = f'https://{normalized}'

    return normalized


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
        normalized_website_link = normalize_website_link(profile.website_link)

        continent_name = str(profile.continent or "").strip()
        continent_exists = (
            db.query(ContinentMaster)
            .filter(func.lower(ContinentMaster.name) == continent_name.lower())
            .first()
        )
        if not continent_exists:
            raise HTTPException(status_code=422, detail="Invalid continent. Use /api/strategy/master/continents")
        
        # Get strategy provider (Ollama or OpenAI)
        provider = StrategyProviderFactory.create_provider()
        
        # Prepare business profile dict
        geography_context = _build_geography_context(
            continent=profile.continent,
            country=profile.country,
            region=profile.region,
        )
        profile_dict = {
            "business_name": profile.business_name,
            "industry": profile.industry,
            "company_size": profile.company_size,
            "revenue": profile.revenue,
            "continent": geography_context["continent"],
            "country": geography_context["country"],
            "region": geography_context["region"],
            "geography": geography_context["geography"],
            "marketing_goals": profile.marketing_goals,
            "budget_range": profile.budget_range,
            "target_audience": profile.target_audience,
            "website_link": normalized_website_link
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

        # Dual-write persistence (DB) without changing API response shape.
        try:
            org_id = current_user["organization_id"]

            strategy_row = (
                db.query(Strategy)
                .filter(
                    Strategy.organization_id == org_id,
                    Strategy.business_name == profile.business_name,
                )
                .with_for_update()
                .first()
            )

            if not strategy_row:
                strategy_row = Strategy(
                    id=str(uuid.uuid4()),
                    organization_id=org_id,
                    business_name=profile.business_name,
                    industry=profile.industry,
                    status="active",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(strategy_row)
                db.flush()
            else:
                strategy_row.industry = profile.industry
                strategy_row.updated_at = datetime.utcnow()

            db.query(StrategyVersion).filter(
                StrategyVersion.strategy_id == strategy_row.id,
                StrategyVersion.organization_id == org_id,
                StrategyVersion.is_current == True,
            ).update(
                {StrategyVersion.is_current: False},
                synchronize_session=False,
            )

            max_version = (
                db.query(func.max(StrategyVersion.version_no))
                .filter(
                    StrategyVersion.strategy_id == strategy_row.id,
                    StrategyVersion.organization_id == org_id,
                )
                .scalar()
            )
            next_version = (int(max_version) if max_version else 0) + 1

            db_version = StrategyVersion(
                id=str(uuid.uuid4()),
                strategy_id=strategy_row.id,
                organization_id=org_id,
                version_no=next_version,
                business_profile_json=profile_dict,
                additional_context=request.additional_context,
                strategy_output_json=strategy,
                provider=ai_strategy.get("provider", "unknown"),
                model=ai_strategy.get("model", "unknown"),
                generated_at=datetime.utcnow(),
                is_current=True,
            )
            db.add(db_version)
            db.commit()
        except Exception as persist_error:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to persist strategy: {str(persist_error)}",
            )

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


@app.post("/llm/test", tags=["Strategy"])
async def llm_test(
    request: LLMTestRequest,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.STRATEGY_AI)),
):
    started_at = time.perf_counter()
    try:
        provider = StrategyProviderFactory.create_provider()
        test_profile = {
            "business_name": "LLM Connectivity Test",
            "industry": "Technology",
            "company_size": "1-10",
            "revenue": None,
            "continent": "North America",
            "country": "United States",
            "region": "Global",
            "geography": "Global",
            "marketing_goals": ["Validation"],
            "budget_range": "N/A",
            "target_audience": "N/A",
            "website_link": "https://example.com"
        }
        result = await provider.generate_strategy(
            business_profile=test_profile,
            additional_context=request.prompt
        )
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "provider": result.get("provider", "unknown"),
            "model": result.get("model", "unknown"),
            "text_preview": (result.get("insights", "") or "")[:250],
            "latency_ms": latency_ms
        }
    except LLMProviderError as e:
        raise HTTPException(status_code=502, detail=f"LLM provider error: {str(e)}")
    except Exception:
        raise HTTPException(status_code=500, detail="LLM test failed")

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
    org_id = current_user["organization_id"]

    strategy_rows = (
        db.query(Strategy)
        .filter(Strategy.organization_id == org_id)
        .order_by(Strategy.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    strategies = []
    for strategy in strategy_rows:
        latest_version_no = (
            db.query(func.max(StrategyVersion.version_no))
            .filter(
                StrategyVersion.strategy_id == strategy.id,
                StrategyVersion.organization_id == org_id,
            )
            .scalar()
        )

        strategies.append(
            {
                "strategy_id": strategy.id,
                "business_name": strategy.business_name,
                "industry": strategy.industry,
                "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
                "latest_version_no": int(latest_version_no) if latest_version_no else 0,
                "status": strategy.status,
            }
        )

    return {
        "success": True,
        "strategies": strategies,
        "message": "Strategy history loaded from database"
    }


@app.get("/api/strategy/{strategy_id}/versions", tags=["Strategy"])
async def get_strategy_versions(
    strategy_id: str,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.STRATEGY_AI)),
    db: Session = Depends(get_db),
):
    """Get all versions for a strategy"""
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

    version_rows = (
        db.query(StrategyVersion)
        .filter(
            StrategyVersion.strategy_id == strategy_id,
            StrategyVersion.organization_id == org_id,
        )
        .order_by(StrategyVersion.version_no.desc())
        .all()
    )

    return {
        "success": True,
        "strategy_id": strategy_id,
        "versions": [
            {
                "version_no": version.version_no,
                "generated_at": version.generated_at.isoformat() if version.generated_at else None,
                "is_current": version.is_current,
                "provider": version.provider,
                "model": version.model,
            }
            for version in version_rows
        ],
    }


@app.get("/api/strategy/{strategy_id}/versions/{version_no}", tags=["Strategy"])
async def get_strategy_version_detail(
    strategy_id: str,
    version_no: int,
    current_user: Dict[str, Any] = Depends(require_feature(FeatureName.STRATEGY_AI)),
    db: Session = Depends(get_db),
):
    """Get full strategy output for a specific version"""
    org_id = current_user["organization_id"]

    version_row = (
        db.query(StrategyVersion)
        .filter(
            StrategyVersion.strategy_id == strategy_id,
            StrategyVersion.version_no == version_no,
            StrategyVersion.organization_id == org_id,
        )
        .first()
    )

    if not version_row:
        raise HTTPException(status_code=404, detail="Strategy version not found")

    return {
        "success": True,
        "strategy_id": strategy_id,
        "version_no": version_row.version_no,
        "strategy_output": version_row.strategy_output_json,
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


@app.on_event("startup")
async def validate_provider_configuration():
    provider_mode = StrategyProviderFactory.validate_environment()
    provider = StrategyProviderFactory.create_provider(provider_mode)
    app.state.strategy_provider = provider
    logger.info("Strategy provider mode active: %s", provider_mode)
    if provider_mode == "ollama_cloud":
        base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com/api")
        if not base_url.startswith("https://"):
            raise RuntimeError("OLLAMA_BASE_URL must use https in ollama_cloud mode")
        if os.getenv("ENV", "").lower() in {"development", "dev", "debug"} or os.getenv("LOG_LEVEL", "").upper() == "DEBUG":
            logger.warning("Ollama cloud provider is running in DEBUG mode")

@app.get("/health", tags=["Health"])
async def basic_health_check():
    """Basic unauthenticated health check endpoint"""
    return {
        "status": "healthy",
        "service": "strategy_ai_service"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003, reload=True)
