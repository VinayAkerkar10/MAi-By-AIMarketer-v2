# MAi Auth & Organization Management Service
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import uuid
import sys
import os

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.init_db import initialize_feature_matrix, seed_default_org_user_license
from shared.database import (
    get_db, Organization, User, License, UserRole, LicenseStatus, LicenseType, LicensePeriod
)
from shared.auth import (
    get_password_hash, verify_password, create_access_token, get_current_user, get_current_admin
)

app = FastAPI(
    title="MAi Auth & Organization Service",
    description="Authentication and Organization Management - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
    version="1.0.0"
)

@app.on_event("startup")
def ensure_db_initialized():
    # Create tables if missing and ensure baseline seed data exists
    from shared.database import init_db
    init_db()
    initialize_feature_matrix()
    if os.getenv("ENABLE_SEED_DATA", "false").lower() == "true":
        seed_default_org_user_license()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== REQUEST MODELS =====

class OrgLoginRequest(BaseModel):
    organization_name: str = Field(..., description="Organization name")
    user_id: str = Field(..., description="User ID within organization")
    password: str = Field(..., description="User password")

class CreateOrgRequest(BaseModel):
    name: str = Field(..., description="Organization name")
    domain: Optional[str] = Field(None, description="Organization domain")

class CreateUserRequest(BaseModel):
    organization_id: str = Field(..., description="Organization ID")
    user_id: str = Field(..., description="User ID within organization")
    email: Optional[EmailStr] = Field(None, description="User email")
    password: str = Field(..., description="User password")
    role: UserRole = Field(UserRole.USER, description="User role")

class AssignLicenseRequest(BaseModel):
    organization_id: str = Field(..., description="Organization ID")
    license_type: LicenseType = Field(..., description="License type")
    period: LicensePeriod = Field(..., description="License period")
    max_users: int = Field(1, description="Maximum users allowed")

# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/api/auth/org-login", tags=["Authentication"])
async def org_first_login(
    request: OrgLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Org-first login flow:
    1. Lookup organization
    2. Check active licenses
    3. Authenticate user
    4. Return JWT with role and org info
    """
    # Step 1: Find organization
    org = db.query(Organization).filter(
        Organization.name == request.organization_name,
        Organization.status == "active"
    ).first()
    
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found or inactive"
        )
    
    # Step 2: Check active licenses
    active_licenses = db.query(License).filter(
        License.organization_id == org.id,
        License.status == LicenseStatus.ACTIVE
    ).all()
    
    if not active_licenses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active license found for this organization"
        )
    
    # Check if any license is expired
    now = datetime.utcnow()
    has_valid_license = False
    for license in active_licenses:
        if license.end_date is None or license.end_date > now:
            has_valid_license = True
            break
    
    if not has_valid_license:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="All licenses have expired"
        )
    
    # Step 3: Authenticate user
    user = db.query(User).filter(
        User.organization_id == org.id,
        User.user_id == request.user_id,
        User.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user credentials"
        )
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user credentials"
        )
    
    # Step 4: Create JWT token
    token_data = {
        "sub": user.user_id,
        "org_id": org.id,
        "role": user.role.value,
        "user_db_id": user.id
    }
    access_token = create_access_token(token_data)
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Determine redirect based on role
    redirect_to = "admin_panel" if user.role == UserRole.ADMIN else "strategy_flow"
    
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user.user_id,
            "organization_id": org.id,
            "organization_name": org.name,
            "role": user.role.value
        },
        "redirect_to": redirect_to,
        "licenses": [
            {
                "type": lic.license_type.value,
                "status": lic.status.value,
                "features": lic.features
            }
            for lic in active_licenses
        ]
    }

@app.get("/api/auth/me", tags=["Authentication"])
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current authenticated user information"""
    org = db.query(Organization).filter(Organization.id == current_user["organization_id"]).first()
    
    return {
        "success": True,
        "user": current_user,
        "organization": {
            "id": org.id,
            "name": org.name,
            "status": org.status
        } if org else None
    }

# ===== ORGANIZATION MANAGEMENT (Admin Only) =====

@app.post("/api/admin/organizations", tags=["Admin - Organizations"])
async def create_organization(
    request: CreateOrgRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new organization (Admin only)"""
    # Check if org name already exists
    existing = db.query(Organization).filter(Organization.name == request.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name already exists"
        )
    
    org = Organization(
        id=str(uuid.uuid4()),
        name=request.name,
        domain=request.domain,
        status="active"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    return {
        "success": True,
        "message": "Organization created successfully",
        "organization": {
            "id": org.id,
            "name": org.name,
            "domain": org.domain,
            "status": org.status
        }
    }

@app.get("/api/admin/organizations", tags=["Admin - Organizations"])
async def list_organizations(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all organizations (Admin only)"""
    orgs = db.query(Organization).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "organizations": [
            {
                "id": org.id,
                "name": org.name,
                "domain": org.domain,
                "status": org.status,
                "created_at": org.created_at.isoformat() if org.created_at else None
            }
            for org in orgs
        ],
        "total": len(orgs)
    }

@app.get("/api/admin/organizations/{org_id}", tags=["Admin - Organizations"])
async def get_organization(
    org_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get organization details (Admin only)"""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    users = db.query(User).filter(User.organization_id == org_id).all()
    licenses = db.query(License).filter(License.organization_id == org_id).all()
    
    return {
        "success": True,
        "organization": {
            "id": org.id,
            "name": org.name,
            "domain": org.domain,
            "status": org.status,
            "created_at": org.created_at.isoformat() if org.created_at else None
        },
        "users_count": len(users),
        "licenses": [
            {
                "id": lic.id,
                "type": lic.license_type.value,
                "status": lic.status.value,
                "period": lic.period.value,
                "features": lic.features
            }
            for lic in licenses
        ]
    }

# ===== USER MANAGEMENT (Admin Only) =====

@app.post("/api/admin/users", tags=["Admin - Users"])
async def create_user(
    request: CreateUserRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create a new user (Admin only)"""
    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == request.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check if user already exists in org
    existing = db.query(User).filter(
        User.organization_id == request.organization_id,
        User.user_id == request.user_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User ID already exists in this organization"
        )
    
    user = User(
        id=str(uuid.uuid4()),
        organization_id=request.organization_id,
        user_id=request.user_id,
        email=request.email,
        password_hash=get_password_hash(request.password),
        role=request.role,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": "User created successfully",
        "user": {
            "id": user.id,
            "user_id": user.user_id,
            "organization_id": user.organization_id,
            "role": user.role.value
        }
    }

@app.get("/api/admin/users", tags=["Admin - Users"])
async def list_users(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
    organization_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """List users (Admin only)"""
    query = db.query(User)
    if organization_id:
        query = query.filter(User.organization_id == organization_id)
    
    users = query.offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "users": [
            {
                "id": user.id,
                "user_id": user.user_id,
                "organization_id": user.organization_id,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active
            }
            for user in users
        ],
        "total": len(users)
    }

# ===== LICENSE MANAGEMENT (Admin Only) =====

@app.post("/api/admin/licenses", tags=["Admin - Licenses"])
async def assign_license(
    request: AssignLicenseRequest,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Assign license to organization (Admin only)"""
    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == request.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get feature list for license type
    from shared.config import LICENSE_FEATURES
    features = LICENSE_FEATURES.get(request.license_type.value, [])
    
    # Calculate end date based on period
    start_date = datetime.utcnow()
    end_date = None
    if request.period == LicensePeriod.MONTHLY:
        end_date = start_date + timedelta(days=30)
    elif request.period == LicensePeriod.YEARLY:
        end_date = start_date + timedelta(days=365)
    # ONE_TIME licenses have no end_date
    
    license = License(
        id=str(uuid.uuid4()),
        organization_id=request.organization_id,
        license_type=request.license_type,
        status=LicenseStatus.ACTIVE,
        period=request.period,
        start_date=start_date,
        end_date=end_date,
        max_users=request.max_users,
        features=features
    )
    db.add(license)
    db.commit()
    db.refresh(license)
    
    return {
        "success": True,
        "message": "License assigned successfully",
        "license": {
            "id": license.id,
            "organization_id": license.organization_id,
            "type": license.license_type.value,
            "status": license.status.value,
            "period": license.period.value,
            "features": license.features,
            "end_date": license.end_date.isoformat() if license.end_date else None
        }
    }

@app.get("/api/admin/licenses", tags=["Admin - Licenses"])
async def list_licenses(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    db: Session = Depends(get_db),
    organization_id: Optional[str] = None
):
    """List licenses (Admin only)"""
    query = db.query(License)
    if organization_id:
        query = query.filter(License.organization_id == organization_id)
    
    licenses = query.all()
    
    return {
        "success": True,
        "licenses": [
            {
                "id": lic.id,
                "organization_id": lic.organization_id,
                "type": lic.license_type.value,
                "status": lic.status.value,
                "period": lic.period.value,
                "features": lic.features,
                "start_date": lic.start_date.isoformat() if lic.start_date else None,
                "end_date": lic.end_date.isoformat() if lic.end_date else None
            }
            for lic in licenses
        ]
    }

@app.get("/api/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "auth_service",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
