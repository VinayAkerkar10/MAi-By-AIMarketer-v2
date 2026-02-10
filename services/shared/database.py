# MAi Shared Database Models
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, ForeignKey, JSON, Float, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum
import os

Base = declarative_base()

# Database connection
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://mai_user:mai_password@postgres:5432/mai_db",
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ===== ENUMS =====

class LicenseType(str, enum.Enum):
    STRATEGY_ONLY = "strategy_only"
    STRATEGY_LEADS = "strategy_leads"
    FULL_SUITE = "full_suite"

class LicenseStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"

class LicensePeriod(str, enum.Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class FeatureName(str, enum.Enum):
    STRATEGY_AI = "strategy_ai"
    LEAD_ENRICHMENT = "lead_enrichment"
    CONTENT_AI = "content_ai"
    CAMPAIGN_PLANNER = "campaign_planner"
    ANALYTICS = "analytics"
    MULTI_CHANNEL = "multi_channel"
    TEMPLATE_LIBRARY = "template_library"

# ===== DATABASE MODELS =====

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    domain = Column(String, nullable=True)
    status = Column(String, default="active")  # active, suspended, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization")
    licenses = relationship("License", back_populates="organization")
    usage_records = relationship("UsageRecord", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False)  # User's identifier within org
    email = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    
    # Unique constraint on org_id + user_id
    __table_args__ = (
        UniqueConstraint('organization_id', 'user_id', name='uq_org_user'),
    )

class License(Base):
    __tablename__ = "licenses"
    
    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    license_type = Column(SQLEnum(LicenseType), nullable=False)
    status = Column(SQLEnum(LicenseStatus), default=LicenseStatus.ACTIVE, nullable=False)
    period = Column(SQLEnum(LicensePeriod), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)  # None for one-time licenses
    max_users = Column(Integer, default=1)
    features = Column(JSON, nullable=False)  # List of enabled features
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="licenses")

class FeatureMatrix(Base):
    __tablename__ = "feature_matrix"
    
    id = Column(String, primary_key=True, index=True)
    license_type = Column(SQLEnum(LicenseType), nullable=False, unique=True)
    features = Column(JSON, nullable=False)  # List of features enabled for this license type
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UsageRecord(Base):
    __tablename__ = "usage_records"
    
    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    feature = Column(SQLEnum(FeatureName), nullable=False)
    usage_count = Column(Integer, default=0)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    meta_data = Column("metadata", JSON, nullable=True)  # Python attr meta_data; DB column "metadata"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="usage_records")

# ===== HELPER FUNCTIONS =====

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
