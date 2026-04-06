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
import logging

# Add parent directory to path for shared imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import (
    get_db, Organization, User, License, UserRole, LicenseStatus, LicenseType, LicensePeriod, OrganizationApiKey
)
from shared.auth import (
    get_password_hash, verify_password, create_access_token, get_current_user,
    get_current_super_admin, get_current_org_admin
)
from shared.api_keys import encrypt_api_key, decrypt_api_key, mask_api_key

app = FastAPI(
    title="MAi Auth & Organization Service",
    description="Authentication and Organization Management - Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.",
    version="1.0.0"
)

logger = logging.getLogger(__name__)

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

class UpdateUserRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="Updated user ID within organization")
    email: Optional[EmailStr] = Field(None, description="Updated user email")
    is_active: Optional[bool] = Field(None, description="Whether the user is active")

class UpdateUserRoleRequest(BaseModel):
    role: UserRole = Field(..., description="Updated user role")

class ResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8, description="New password")

class AssignLicenseRequest(BaseModel):
    organization_id: str = Field(..., description="Organization ID")
    license_type: LicenseType = Field(..., description="License type")
    period: LicensePeriod = Field(..., description="License period")
    max_users: int = Field(1, description="Maximum users allowed")

class UpdateLicenseRequest(BaseModel):
    license_type: Optional[LicenseType] = Field(None, description="Updated license type")
    period: Optional[LicensePeriod] = Field(None, description="Updated billing period")
    max_users: Optional[int] = Field(None, description="Maximum users allowed")
    start_date: Optional[datetime] = Field(None, description="Updated license start date")
    end_date: Optional[datetime] = Field(None, description="Updated license end date")

class UpdateLicenseStatusRequest(BaseModel):
    status: LicenseStatus = Field(..., description="Updated license status")


class OrgApiKeyRequest(BaseModel):
    provider_name: str = Field(..., description="Provider name")
    api_key: Optional[str] = Field(None, description="Provider API key")
    status: Optional[str] = Field("active", description="active or disabled")


def _is_super_admin(current_user: Dict[str, Any]) -> bool:
    return str(current_user.get("role") or "").strip().lower() == UserRole.SUPER_ADMIN.value


def _enforce_org_scope(
    current_user: Dict[str, Any],
    requested_organization_id: Optional[str] = None,
    *,
    allow_super_admin_override: bool = True,
) -> str:
    current_org_id = str(current_user.get("organization_id") or "").strip()
    requested_org_id = str(requested_organization_id or "").strip()

    if _is_super_admin(current_user) and allow_super_admin_override:
        return requested_org_id or current_org_id

    if requested_org_id and requested_org_id != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-organization access is not allowed"
        )

    return current_org_id


def _ensure_assignable_role(current_user: Dict[str, Any], requested_role: UserRole) -> None:
    if _is_super_admin(current_user):
        return

    if requested_role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot create or assign super_admin role"
        )


def _ensure_manageable_user(current_user: Dict[str, Any], target_user: User) -> None:
    if _is_super_admin(current_user):
        return

    if target_user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot manage super_admin accounts"
        )


def _serialize_user(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "user_id": user.user_id,
        "organization_id": user.organization_id,
        "email": user.email,
        "role": user.role.value,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def _get_scoped_user(db: Session, current_user: Dict[str, Any], user_id: str) -> User:
    query = db.query(User).filter(User.id == user_id)
    if not _is_super_admin(current_user):
        query = query.filter(User.organization_id == current_user["organization_id"])
    user = query.first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _ensure_manageable_user(current_user, user)
    return user


def _calculate_license_dates(period: LicensePeriod, start_date: datetime) -> Optional[datetime]:
    if period == LicensePeriod.MONTHLY:
        return start_date + timedelta(days=30)
    if period == LicensePeriod.YEARLY:
        return start_date + timedelta(days=365)
    return None


def _serialize_license(license_row: License) -> Dict[str, Any]:
    return {
        "id": license_row.id,
        "organization_id": license_row.organization_id,
        "type": license_row.license_type.value,
        "status": license_row.status.value,
        "period": license_row.period.value,
        "features": license_row.features,
        "max_users": license_row.max_users,
        "start_date": license_row.start_date.isoformat() if license_row.start_date else None,
        "end_date": license_row.end_date.isoformat() if license_row.end_date else None,
        "created_at": license_row.created_at.isoformat() if license_row.created_at else None,
        "updated_at": license_row.updated_at.isoformat() if license_row.updated_at else None,
    }


def _get_scoped_license(db: Session, current_user: Dict[str, Any], license_id: str) -> License:
    query = db.query(License).filter(License.id == license_id)
    if not _is_super_admin(current_user):
        query = query.filter(License.organization_id == current_user["organization_id"])
    license_row = query.first()
    if not license_row:
        raise HTTPException(status_code=404, detail="License not found")
    return license_row

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
        "user_db_id": user.id,
        "sv": int(user.session_version or 0),
    }
    access_token = create_access_token(token_data)
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Determine redirect based on role
    redirect_to = (
        "admin_panel"
        if user.role in {UserRole.SUPER_ADMIN, UserRole.ADMIN}
        else "strategy_flow"
    )
    
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

@app.post("/api/auth/logout", tags=["Authentication"])
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invalidate current JWT session by bumping session version"""
    user = db.query(User).filter(
        User.organization_id == current_user["organization_id"],
        User.user_id == current_user["user_id"],
        User.is_active == True
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    user.session_version = int(user.session_version or 0) + 1
    db.commit()

    return {
        "success": True,
        "message": "Logged out successfully"
    }

# ===== ORGANIZATION MANAGEMENT (Admin Only) =====

@app.post("/api/admin/organizations", tags=["Admin - Organizations"])
async def create_organization(
    request: CreateOrgRequest,
    current_admin: Dict[str, Any] = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """Create a new organization (Super Admin only)"""
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
    current_admin: Dict[str, Any] = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all organizations (Super Admin only)"""
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
    current_admin: Dict[str, Any] = Depends(get_current_super_admin),
    db: Session = Depends(get_db)
):
    """Get organization details (Super Admin only)"""
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
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Create a new user with org-scoped RBAC."""
    target_org_id = _enforce_org_scope(
        current_admin,
        request.organization_id,
        allow_super_admin_override=True,
    )
    _ensure_assignable_role(current_admin, request.role)

    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == target_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Check if user already exists in org
    existing = db.query(User).filter(
        User.organization_id == target_org_id,
        User.user_id == request.user_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User ID already exists in this organization"
        )
    
    user = User(
        id=str(uuid.uuid4()),
        organization_id=target_org_id,
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
        "user": _serialize_user(user)
    }

@app.get("/api/admin/users", tags=["Admin - Users"])
async def list_users(
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
    organization_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """List users with tenant isolation."""
    query = db.query(User)
    target_org_id = _enforce_org_scope(
        current_admin,
        organization_id,
        allow_super_admin_override=True,
    )
    if target_org_id:
        query = query.filter(User.organization_id == target_org_id)
    
    users = query.offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "users": [_serialize_user(user) for user in users],
        "total": len(users)
    }


@app.get("/api/admin/users/{user_id}", tags=["Admin - Users"])
async def get_user(
    user_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Get a single user with tenant isolation."""
    user = _get_scoped_user(db, current_admin, user_id)
    return {
        "success": True,
        "user": _serialize_user(user)
    }


@app.put("/api/admin/users/{user_id}", tags=["Admin - Users"])
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Update a user with tenant isolation."""
    user = _get_scoped_user(db, current_admin, user_id)

    next_user_id = str(request.user_id or user.user_id).strip()
    if not next_user_id:
        raise HTTPException(status_code=422, detail="user_id is required")

    if next_user_id != user.user_id:
        conflict = db.query(User).filter(
            User.organization_id == user.organization_id,
            User.user_id == next_user_id,
            User.id != user.id,
        ).first()
        if conflict:
            raise HTTPException(status_code=409, detail="User ID already exists in this organization")
        user.user_id = next_user_id

    if request.email is not None:
        user.email = request.email
    if request.is_active is not None:
        user.is_active = request.is_active

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "User updated successfully",
        "user": _serialize_user(user)
    }


@app.delete("/api/admin/users/{user_id}", tags=["Admin - Users"])
async def delete_user(
    user_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Soft delete a user by setting is_active to false."""
    user = _get_scoped_user(db, current_admin, user_id)

    if not user.is_active:
        return {
            "success": True,
            "message": "User already inactive",
            "user": _serialize_user(user)
        }

    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "User deactivated successfully",
        "user": _serialize_user(user)
    }


@app.patch("/api/admin/users/{user_id}/role", tags=["Admin - Users"])
async def update_user_role(
    user_id: str,
    request: UpdateUserRoleRequest,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Update a user's role with role ceiling enforcement."""
    _ensure_assignable_role(current_admin, request.role)
    user = _get_scoped_user(db, current_admin, user_id)
    user.role = request.role
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "User role updated successfully",
        "user": _serialize_user(user)
    }


@app.patch("/api/admin/users/{user_id}/reset-password", tags=["Admin - Users"])
async def reset_user_password(
    user_id: str,
    request: ResetPasswordRequest,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Reset a user's password and invalidate existing sessions."""
    user = _get_scoped_user(db, current_admin, user_id)
    user.password_hash = get_password_hash(request.password)
    user.session_version = int(user.session_version or 0) + 1
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": "Password reset successfully",
        "user": _serialize_user(user)
    }

# ===== LICENSE MANAGEMENT (Admin Only) =====

@app.post("/api/admin/licenses", tags=["Admin - Licenses"])
async def assign_license(
    request: AssignLicenseRequest,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Assign license to organization with tenant isolation."""
    target_org_id = _enforce_org_scope(
        current_admin,
        request.organization_id,
        allow_super_admin_override=True,
    )
    # Verify organization exists
    org = db.query(Organization).filter(Organization.id == target_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get feature list for license type
    from shared.config import LICENSE_FEATURES
    features = LICENSE_FEATURES.get(request.license_type.value, [])
    
    # Calculate end date based on period
    start_date = datetime.utcnow()
    end_date = _calculate_license_dates(request.period, start_date)
    
    license = License(
        id=str(uuid.uuid4()),
        organization_id=target_org_id,
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
        "license": _serialize_license(license)
    }

@app.get("/api/admin/licenses", tags=["Admin - Licenses"])
async def list_licenses(
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
    organization_id: Optional[str] = None
):
    """List licenses with tenant isolation."""
    query = db.query(License)
    target_org_id = _enforce_org_scope(
        current_admin,
        organization_id,
        allow_super_admin_override=True,
    )
    if target_org_id:
        query = query.filter(License.organization_id == target_org_id)
    
    licenses = query.all()
    
    return {
        "success": True,
        "licenses": [_serialize_license(lic) for lic in licenses]
    }


@app.get("/api/admin/licenses/{license_id}", tags=["Admin - Licenses"])
async def get_license(
    license_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Get a single license with tenant isolation."""
    license_row = _get_scoped_license(db, current_admin, license_id)
    return {
        "success": True,
        "license": _serialize_license(license_row)
    }


@app.put("/api/admin/licenses/{license_id}", tags=["Admin - Licenses"])
async def update_license(
    license_id: str,
    request: UpdateLicenseRequest,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Update a license with tenant isolation."""
    from shared.config import LICENSE_FEATURES

    license_row = _get_scoped_license(db, current_admin, license_id)
    next_license_type = request.license_type or license_row.license_type
    next_period = request.period or license_row.period
    next_start_date = request.start_date or license_row.start_date or datetime.utcnow()
    next_end_date = request.end_date if request.end_date is not None else _calculate_license_dates(next_period, next_start_date)

    if request.max_users is not None:
        if request.max_users < 1:
            raise HTTPException(status_code=422, detail="max_users must be at least 1")
        license_row.max_users = request.max_users

    license_row.license_type = next_license_type
    license_row.period = next_period
    license_row.start_date = next_start_date
    license_row.end_date = next_end_date
    license_row.features = LICENSE_FEATURES.get(next_license_type.value, license_row.features)
    license_row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(license_row)

    return {
        "success": True,
        "message": "License updated successfully",
        "license": _serialize_license(license_row)
    }


@app.patch("/api/admin/licenses/{license_id}/status", tags=["Admin - Licenses"])
async def update_license_status(
    license_id: str,
    request: UpdateLicenseStatusRequest,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Update license status."""
    allowed_statuses = {
        LicenseStatus.ACTIVE,
        LicenseStatus.SUSPENDED,
        LicenseStatus.CANCELLED,
    }
    if request.status not in allowed_statuses:
        raise HTTPException(status_code=422, detail="status must be active, suspended, or cancelled")

    license_row = _get_scoped_license(db, current_admin, license_id)
    license_row.status = request.status
    license_row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(license_row)

    return {
        "success": True,
        "message": "License status updated successfully",
        "license": _serialize_license(license_row)
    }


@app.delete("/api/admin/licenses/{license_id}", tags=["Admin - Licenses"])
async def delete_license(
    license_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db)
):
    """Delete a license with tenant isolation."""
    license_row = _get_scoped_license(db, current_admin, license_id)
    license_snapshot = _serialize_license(license_row)
    db.delete(license_row)
    db.commit()

    return {
        "success": True,
        "message": "License deleted successfully",
        "license": license_snapshot
    }


# ===== API KEY MANAGEMENT (Organization Admin) =====

def _normalize_provider_name(provider_name: str) -> str:
    return str(provider_name or "").strip().lower()


def _normalize_api_key_status(status_value: Optional[str]) -> str:
    value = str(status_value or "active").strip().lower()
    return "disabled" if value == "disabled" else "active"


@app.get("/api/admin/api-keys", tags=["Admin - API Keys"])
async def list_org_api_keys(
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
):
    try:
        org_id = str(current_admin.get("organization_id") or "").strip()
        if not org_id:
            return {
                "success": True,
                "api_keys": [],
            }

        rows = (
            db.query(OrganizationApiKey)
            .filter(OrganizationApiKey.organization_id == org_id)
            .order_by(OrganizationApiKey.provider_name.asc())
            .all()
        )

        api_keys = []
        for row in rows:
            try:
                masked_key = mask_api_key(decrypt_api_key(row.api_key))
            except Exception as exc:
                print("API KEYS ERROR:", f"Failed to decrypt API key {row.id}: {str(exc)}")
                masked_key = "****"

            api_keys.append(
                {
                    "id": row.id,
                    "organization_id": row.organization_id,
                    "provider": row.provider_name,
                    "provider_name": row.provider_name,
                    "api_key": masked_key,
                    "api_key_masked": masked_key,
                    "status": row.status,
                    "created_by": row.created_by,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }
            )

        return {
            "success": True,
            "api_keys": api_keys,
        }
    except Exception as e:
        print("API KEYS ERROR:", str(e))
        raise


@app.post("/api/admin/api-keys", tags=["Admin - API Keys"])
async def create_org_api_key(
    payload: OrgApiKeyRequest,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
):
    org_id = current_admin["organization_id"]
    provider_name = _normalize_provider_name(payload.provider_name)
    if not provider_name:
        raise HTTPException(status_code=422, detail="provider_name is required")
    if not str(payload.api_key or "").strip():
        raise HTTPException(status_code=422, detail="api_key is required")

    existing = (
        db.query(OrganizationApiKey)
        .filter(
            OrganizationApiKey.organization_id == org_id,
            OrganizationApiKey.provider_name == provider_name,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="API key already configured for provider")

    now = datetime.utcnow()
    row = OrganizationApiKey(
        id=str(uuid.uuid4()),
        organization_id=org_id,
        provider_name=provider_name,
        api_key=encrypt_api_key(payload.api_key),
        created_by=current_admin["user_id"],
        created_at=now,
        updated_at=now,
        status=_normalize_api_key_status(payload.status),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "success": True,
        "message": "API key created successfully",
        "api_key": {
            "id": row.id,
            "organization_id": row.organization_id,
            "provider_name": row.provider_name,
            "api_key_masked": mask_api_key(decrypt_api_key(row.api_key)),
            "created_by": row.created_by,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "status": row.status,
        },
    }


@app.put("/api/admin/api-keys/{key_id}", tags=["Admin - API Keys"])
async def update_org_api_key(
    key_id: str,
    payload: OrgApiKeyRequest,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
):
    org_id = current_admin["organization_id"]
    fields_set = getattr(payload, "__fields_set__", set())
    row = (
        db.query(OrganizationApiKey)
        .filter(
            OrganizationApiKey.id == key_id,
            OrganizationApiKey.organization_id == org_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="API key not found")

    provider_name = _normalize_provider_name(payload.provider_name)
    if not provider_name:
        raise HTTPException(status_code=422, detail="provider_name is required")
    if provider_name != row.provider_name:
        conflict = (
            db.query(OrganizationApiKey)
            .filter(
                OrganizationApiKey.organization_id == org_id,
                OrganizationApiKey.provider_name == provider_name,
                OrganizationApiKey.id != key_id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(status_code=409, detail="API key already configured for provider")
        row.provider_name = provider_name

    new_api_key_value = str(payload.api_key or "").strip()
    had_disabled_status = row.status == "disabled"
    if new_api_key_value:
        row.api_key = encrypt_api_key(payload.api_key)
        row.status = "active"
        if had_disabled_status:
            logger.info("[Auth Admin Debug] API key reactivated")
    elif "status" in fields_set:
        row.status = _normalize_api_key_status(payload.status)

    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    logger.info("[Auth Admin Debug] API key updated")

    return {
        "success": True,
        "message": "API key updated successfully",
        "api_key": {
            "id": row.id,
            "organization_id": row.organization_id,
            "provider_name": row.provider_name,
            "api_key_masked": mask_api_key(decrypt_api_key(row.api_key)),
            "created_by": row.created_by,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "status": row.status,
        },
    }


@app.delete("/api/admin/api-keys/{key_id}", tags=["Admin - API Keys"])
async def disable_org_api_key(
    key_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_org_admin),
    db: Session = Depends(get_db),
):
    org_id = current_admin["organization_id"]
    row = (
        db.query(OrganizationApiKey)
        .filter(
            OrganizationApiKey.id == key_id,
            OrganizationApiKey.organization_id == org_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="API key not found")

    if row.status == "disabled":
        logger.info("[Auth Admin Debug] API key already disabled")
        return {
            "success": True,
            "message": "API key already disabled",
            "api_key": {
                "id": row.id,
                "provider_name": row.provider_name,
                "status": row.status,
            },
        }

    row.status = "disabled"
    row.updated_at = datetime.utcnow()
    provider = row.provider_name
    db.commit()
    logger.info("[Auth Admin Debug] API key disabled successfully")

    return {
        "success": True,
        "message": "API key disabled successfully",
        "api_key": {
            "id": key_id,
            "provider_name": provider,
            "status": "disabled",
        },
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
