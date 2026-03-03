# MAi Shared Database Models
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Float,
    Text,
    Enum as SQLEnum,
    UniqueConstraint,
    CheckConstraint,
    Index,
    desc,
)
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


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class LeadSource(str, enum.Enum):
    GITHUB = "github"
    GOOGLE_MAPS = "google_maps"
    LINKEDIN = "linkedin"
    VOLZA = "volza"

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
    campaigns = relationship("Campaign", back_populates="organization")
    campaign_metrics = relationship("CampaignMetric", back_populates="organization")
    strategies = relationship("Strategy", back_populates="organization")
    lead_scrape_tasks = relationship("LeadScrapeTask", back_populates="organization")
    lead_source_runs = relationship("LeadSourceRun", back_populates="organization")
    lead_scrape_results = relationship("LeadScrapeResult", back_populates="organization")
    enrichment_tasks = relationship("EnrichmentTask", back_populates="organization")
    enrichment_rows = relationship("EnrichmentRow", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False)  # User's identifier within org
    email = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    session_version = Column(Integer, nullable=False, default=0)
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


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    strategy_id = Column(String, ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True)
    strategy_version_no = Column(Integer, nullable=True)
    campaign_name = Column(String, nullable=False, index=True)
    channels = Column(JSON, nullable=False, default=list)
    target_audience = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    schedule_date = Column(DateTime, nullable=True)
    budget = Column(Float, nullable=True)
    audience_source = Column(String, nullable=False, default="scraped_leads")
    manual_selection = Column(JSON, nullable=False, default=list)
    status = Column(String, nullable=False, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deployed_at = Column(DateTime, nullable=True)

    organization = relationship("Organization", back_populates="campaigns")
    metrics = relationship(
        "CampaignMetric",
        uselist=False,
        back_populates="campaign",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("budget IS NULL OR budget >= 0", name="ck_campaign_budget_non_negative"),
        CheckConstraint(
            "status IN ('draft','scheduled','active','paused','failed','completed')",
            name="ck_campaign_status",
        ),
        CheckConstraint(
            "audience_source IN ('scraped_leads','customer_upload','manual_selection')",
            name="ck_campaign_audience_source",
        ),
        Index("ix_campaign_org_status", "organization_id", "status"),
        Index("ix_campaign_org_created", "organization_id", "created_at"),
        Index("ix_campaigns_org_strategy", "organization_id", "strategy_id"),
        Index("ix_campaigns_org_strategy_version", "organization_id", "strategy_id", "strategy_version_no"),
    )


class CampaignMetric(Base):
    __tablename__ = "campaign_metrics"

    campaign_id = Column(String, ForeignKey("campaigns.id"), primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    sent = Column(Integer, nullable=False, default=0)
    opened = Column(Integer, nullable=False, default=0)
    clicked = Column(Integer, nullable=False, default=0)
    converted = Column(Integer, nullable=False, default=0)
    impressions = Column(Integer, nullable=False, default=0)
    cost = Column(Float, nullable=False, default=0.0)
    ctr = Column(Float, nullable=False, default=0.0)
    conversion_rate = Column(Float, nullable=False, default=0.0)
    cpa = Column(Float, nullable=False, default=0.0)
    roi = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    campaign = relationship("Campaign", back_populates="metrics")
    organization = relationship("Organization", back_populates="campaign_metrics")

    __table_args__ = (
        CheckConstraint("sent >= 0", name="ck_campaign_metrics_sent_non_negative"),
        CheckConstraint("opened >= 0", name="ck_campaign_metrics_opened_non_negative"),
        CheckConstraint("clicked >= 0", name="ck_campaign_metrics_clicked_non_negative"),
        CheckConstraint("converted >= 0", name="ck_campaign_metrics_converted_non_negative"),
        CheckConstraint("impressions >= 0", name="ck_campaign_metrics_impressions_non_negative"),
        CheckConstraint("cost >= 0", name="ck_campaign_metrics_cost_non_negative"),
        CheckConstraint("ctr >= 0", name="ck_campaign_metrics_ctr_non_negative"),
        CheckConstraint("conversion_rate >= 0", name="ck_campaign_metrics_conversion_rate_non_negative"),
        CheckConstraint("cpa >= 0", name="ck_campaign_metrics_cpa_non_negative"),
        Index("ix_campaign_metrics_org_campaign", "organization_id", "campaign_id"),
    )


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    business_name = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="strategies")
    versions = relationship(
        "StrategyVersion",
        back_populates="strategy",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_strategies_org_created", "organization_id", "created_at"),
        Index("ix_strategies_org_status", "organization_id", "status"),
    )


class StrategyVersion(Base):
    __tablename__ = "strategy_versions"

    id = Column(String, primary_key=True, index=True)
    strategy_id = Column(String, ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    business_profile_json = Column(JSON, nullable=True)
    additional_context = Column(Text, nullable=True)
    strategy_output_json = Column(JSON, nullable=False)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False)

    strategy = relationship("Strategy", back_populates="versions")
    organization = relationship("Organization")

    __table_args__ = (
        UniqueConstraint("strategy_id", "version_no", name="uq_strategy_version"),
        Index("ix_strategy_versions_strategy_version_desc", "strategy_id", desc("version_no")),
        Index("ix_strategy_versions_org_generated_desc", "organization_id", desc("generated_at")),
    )


class LeadScrapeTask(Base):
    __tablename__ = "lead_scrape_tasks"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    location = Column(String, nullable=False)
    business_type = Column(String, nullable=False)
    radius = Column(Integer, nullable=True)
    max_results = Column(Integer, nullable=True)
    requested_sources = Column(JSON, nullable=False, default=list)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    total_found = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    source_results = Column(JSON, nullable=True)
    summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="lead_scrape_tasks")
    leads = relationship("LeadScrapeResult", back_populates="task", cascade="all, delete-orphan")
    source_runs = relationship("LeadSourceRun", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("radius IS NULL OR radius >= 0", name="ck_lead_scrape_task_radius_non_negative"),
        CheckConstraint("max_results IS NULL OR max_results > 0", name="ck_lead_scrape_task_max_results_positive"),
        CheckConstraint("total_found >= 0", name="ck_lead_scrape_task_total_found_non_negative"),
        Index("ix_lead_scrape_task_org_created", "organization_id", "created_at"),
        Index("ix_lead_scrape_task_org_status", "organization_id", "status"),
    )


class LeadSourceRun(Base):
    __tablename__ = "lead_source_runs"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("lead_scrape_tasks.id"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    source = Column(SQLEnum(LeadSource), nullable=False)
    status = Column(SQLEnum(TaskStatus), nullable=False)
    message = Column(Text, nullable=True)
    leads_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    task = relationship("LeadScrapeTask", back_populates="source_runs")
    organization = relationship("Organization", back_populates="lead_source_runs")

    __table_args__ = (
        CheckConstraint("leads_count >= 0", name="ck_lead_source_run_leads_count_non_negative"),
        UniqueConstraint("task_id", "source", name="uq_lead_source_run_task_source"),
        Index("ix_lead_source_run_org_task", "organization_id", "task_id"),
    )


class LeadScrapeResult(Base):
    __tablename__ = "lead_scrape_results"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("lead_scrape_tasks.id"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    source = Column(SQLEnum(LeadSource), nullable=False, index=True)
    business_name = Column(String, nullable=True)
    contact_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    address = Column(String, nullable=True)
    category = Column(String, nullable=True)
    meta_data = Column("metadata", JSON, nullable=True)
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("LeadScrapeTask", back_populates="leads")
    organization = relationship("Organization", back_populates="lead_scrape_results")

    __table_args__ = (
        Index("ix_lead_scrape_result_org_task", "organization_id", "task_id"),
        Index("ix_lead_scrape_result_org_source", "organization_id", "source"),
    )


class EnrichmentTask(Base):
    __tablename__ = "enrichment_tasks"

    id = Column(String, primary_key=True, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    original_count = Column(Integer, nullable=False, default=0)
    enriched_count = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="enrichment_tasks")
    rows = relationship("EnrichmentRow", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("original_count >= 0", name="ck_enrichment_task_original_count_non_negative"),
        CheckConstraint("enriched_count >= 0", name="ck_enrichment_task_enriched_count_non_negative"),
        Index("ix_enrichment_task_org_created", "organization_id", "created_at"),
        Index("ix_enrichment_task_org_status", "organization_id", "status"),
    )


class EnrichmentRow(Base):
    __tablename__ = "enrichment_rows"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("enrichment_tasks.id"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    row_index = Column(Integer, nullable=False)
    original_data = Column(JSON, nullable=False)
    enriched_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    task = relationship("EnrichmentTask", back_populates="rows")
    organization = relationship("Organization", back_populates="enrichment_rows")

    __table_args__ = (
        CheckConstraint("row_index >= 0", name="ck_enrichment_row_row_index_non_negative"),
        UniqueConstraint("task_id", "row_index", name="uq_enrichment_row_task_index"),
        Index("ix_enrichment_row_org_task", "organization_id", "task_id"),
    )

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
