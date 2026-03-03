# MAi Shared Authentication & Authorization
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
import os

from .database import get_db, User, Organization, License, LicenseStatus, UserRole, FeatureName

# JWT Configuration
APP_ENV = os.getenv("ENV", "production").lower()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is required and must be set in environment.")

INSECURE_JWT_SECRETS = {
    "your-secret-key",
    "your-secret-key-change-in-production",
    "your-jwt-secret-key-here",
    "changeme",
    "default",
    "secret",
}
if APP_ENV != "development" and JWT_SECRET_KEY in INSECURE_JWT_SECRETS:
    raise RuntimeError(
        "JWT_SECRET_KEY is insecure for non-development environments. "
        "Set a strong secret value."
    )

JWT_ALGORITHM = "HS256"

jwt_expire_raw = os.getenv("JWT_EXPIRE_MINUTES")
if jwt_expire_raw is None:
    raise RuntimeError("JWT_EXPIRE_MINUTES is required and must be set in environment.")
try:
    JWT_EXPIRE_MINUTES = int(jwt_expire_raw)
    if JWT_EXPIRE_MINUTES <= 0:
        raise ValueError
except ValueError:
    raise RuntimeError("JWT_EXPIRE_MINUTES must be a positive integer.")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ===== PASSWORD UTILITIES =====

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

# ===== JWT UTILITIES =====

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# ===== AUTHENTICATION DEPENDENCIES =====

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.
    Returns user info with organization and role.
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    user_id: str = payload.get("sub")
    org_id: str = payload.get("org_id")
    token_session_version = payload.get("sv")
    
    if not user_id or not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Fetch user from database
    user = db.query(User).filter(
        User.organization_id == org_id,
        User.user_id == user_id,
        User.is_active == True
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    try:
        token_session_version_int = int(token_session_version if token_session_version is not None else 0)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user_session_version_int = int(user.session_version or 0)
    if token_session_version_int != user_session_version_int:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been invalidated"
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "user_id": user.user_id,
        "user_db_id": user.id,
        "organization_id": user.organization_id,
        "role": user.role.value,
        "email": user.email
    }

async def get_current_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Ensure current user is an admin"""
    if current_user["role"] != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# ===== LICENSE VALIDATION =====

def check_license_feature(
    db: Session,
    organization_id: str,
    feature: FeatureName
) -> bool:
    """
    Check if organization has active license with the requested feature.
    Returns True if feature is available, False otherwise.
    """
    # Get active licenses for organization
    active_licenses = db.query(License).filter(
        License.organization_id == organization_id,
        License.status == LicenseStatus.ACTIVE
    ).all()
    
    if not active_licenses:
        return False
    
    # Check if any license has expired
    now = datetime.utcnow()
    for license in active_licenses:
        if license.end_date and license.end_date < now:
            # License expired
            license.status = LicenseStatus.EXPIRED
            db.commit()
            continue
        
        # Check if feature is in license features
        if feature.value in license.features:
            return True
    
    return False

def require_feature(feature: FeatureName):
    """
    Dependency factory that returns a dependency function to require a specific feature.
    Usage: Depends(require_feature(FeatureName.STRATEGY_AI))
    Raises 403 if feature is not available.
    """
    async def _require_feature_dependency(
        current_user: Dict[str, Any] = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> Dict[str, Any]:
        has_feature = check_license_feature(
            db,
            current_user["organization_id"],
            feature
        )
        
        if not has_feature:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature.value}' is not available in your license"
            )
        
        return current_user
    
    return _require_feature_dependency
