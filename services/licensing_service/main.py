# MAi Licensing Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import get_db, Organization, License, LicenseStatus, FeatureMatrix, FeatureName
from shared.auth import get_current_user, check_license_feature

app = FastAPI(
    title="MAi Licensing Service",
    description="License validation and feature gating - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/licensing/validate/{feature}", tags=["Licensing"])
async def validate_feature(
    feature: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate if organization has access to a specific feature.
    Used by other services for feature gating.
    """
    try:
        feature_enum = FeatureName(feature)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feature name: {feature}"
        )
    
    has_access = check_license_feature(
        db,
        current_user["organization_id"],
        feature_enum
    )
    
    return {
        "success": True,
        "feature": feature,
        "has_access": has_access,
        "organization_id": current_user["organization_id"]
    }

@app.get("/api/licensing/features", tags=["Licensing"])
async def get_available_features(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all features available to the organization"""
    org_id = current_user["organization_id"]
    
    # Get active licenses
    active_licenses = db.query(License).filter(
        License.organization_id == org_id,
        License.status == LicenseStatus.ACTIVE
    ).all()
    
    # Collect all features from active licenses
    all_features = set()
    for license in active_licenses:
        # Check if license is still valid
        if license.end_date and license.end_date < datetime.utcnow():
            continue
        all_features.update(license.features)
    
    return {
        "success": True,
        "organization_id": org_id,
        "available_features": list(all_features),
        "licenses": [
            {
                "type": lic.license_type.value,
                "status": lic.status.value,
                "features": lic.features
            }
            for lic in active_licenses
        ]
    }

@app.get("/api/licensing/status", tags=["Licensing"])
async def get_license_status(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed license status for organization"""
    org_id = current_user["organization_id"]
    
    licenses = db.query(License).filter(
        License.organization_id == org_id
    ).all()
    
    active_count = sum(1 for lic in licenses if lic.status == LicenseStatus.ACTIVE)
    expired_count = sum(1 for lic in licenses if lic.status == LicenseStatus.EXPIRED)
    
    return {
        "success": True,
        "organization_id": org_id,
        "total_licenses": len(licenses),
        "active_licenses": active_count,
        "expired_licenses": expired_count,
        "licenses": [
            {
                "id": lic.id,
                "type": lic.license_type.value,
                "status": lic.status.value,
                "period": lic.period.value,
                "start_date": lic.start_date.isoformat() if lic.start_date else None,
                "end_date": lic.end_date.isoformat() if lic.end_date else None,
                "features": lic.features
            }
            for lic in licenses
        ]
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "licensing_service",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)
