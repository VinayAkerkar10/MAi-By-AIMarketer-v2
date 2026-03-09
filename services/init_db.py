# Database Initialization Script
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

import sys
import os
import uuid
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import (
    init_db,
    FeatureMatrix,
    LicenseType,
    SessionLocal,
    Organization,
    User,
    License,
    LicenseStatus,
    LicensePeriod,
    UserRole,
    ContinentMaster,
)
from shared.config import LICENSE_FEATURES
from shared.auth import get_password_hash

def initialize_feature_matrix():
    """Initialize feature matrix table with default license configurations"""
    db = SessionLocal()
    try:
        # Check if feature matrix already exists
        existing = db.query(FeatureMatrix).first()
        if existing:
            print("Feature matrix already initialized")
            return
        
        # Create feature matrix entries
        for license_type, features in LICENSE_FEATURES.items():
            feature_matrix = FeatureMatrix(
                id=f"fm_{license_type}",
                license_type=LicenseType(license_type),
                features=features
            )
            db.add(feature_matrix)
        
        db.commit()
        print("Feature matrix initialized successfully")
    except Exception as e:
        print(f"Error initializing feature matrix: {e}")
        db.rollback()
    finally:
        db.close()


def initialize_continent_master():
    """Initialize continent master data if missing."""
    db = SessionLocal()
    try:
        existing = db.query(ContinentMaster).count()
        if existing > 0:
            print("Continent master already initialized")
            return

        continents = [
            "Asia",
            "Africa",
            "Europe",
            "MENA",
            "North America",
            "South America",
        ]
        for name in continents:
            db.add(ContinentMaster(name=name))

        db.commit()
        print("Continent master initialized successfully")
    except Exception as e:
        print(f"Error initializing continent master: {e}")
        db.rollback()
    finally:
        db.close()

def seed_default_org_user_license():
    """Seed a minimal default org/admin/license if enabled"""
    if os.getenv("ENABLE_SEED_DATA", "false").lower() != "true":
        print("Seed data disabled (ENABLE_SEED_DATA is not true); skipping seeding.")
        return

    db = SessionLocal()
    try:
        app_env = os.getenv("ENV", "production").lower()
        org_name = os.getenv("SEED_ORG_NAME", "DefaultOrg")
        org = db.query(Organization).filter(Organization.name == org_name).first()
        if org:
            print("Seed organization exists; checking for missing admin/license")
        else:
            org = Organization(
                id=str(uuid.uuid4()),
                name=org_name,
                status="active"
            )
            db.add(org)
            db.commit()
            db.refresh(org)

        admin_user_id = os.getenv("SEED_ADMIN_USER_ID", "admin")
        admin_password = os.getenv("SEED_ADMIN_PASSWORD")
        if not admin_password:
            if app_env == "development":
                admin_password = "admin123"
                print("WARNING: Using development fallback seed admin password.")
            else:
                raise RuntimeError(
                    "SEED_ADMIN_PASSWORD is required when ENABLE_SEED_DATA=true "
                    "outside development."
                )
        license_type_str = os.getenv("SEED_LICENSE_TYPE", "full_suite")
        license_period_str = os.getenv("SEED_LICENSE_PERIOD", "monthly")
        max_users = int(os.getenv("SEED_MAX_USERS", "10"))

        existing_user = db.query(User).filter(
            User.organization_id == org.id,
            User.user_id == admin_user_id
        ).first()
        if not existing_user:
            admin_user = User(
                id=str(uuid.uuid4()),
                organization_id=org.id,
                user_id=admin_user_id,
                email=None,
                password_hash=get_password_hash(admin_password),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin_user)

        existing_license = db.query(License).filter(
            License.organization_id == org.id,
            License.status == LicenseStatus.ACTIVE
        ).first()
        if existing_license:
            db.commit()
            print("Active license already exists; skipping license seed")
            return

        license_type = LicenseType(license_type_str)
        period = LicensePeriod(license_period_str)
        start_date = datetime.utcnow()
        end_date = None
        if period == LicensePeriod.MONTHLY:
            end_date = start_date + timedelta(days=30)
        elif period == LicensePeriod.YEARLY:
            end_date = start_date + timedelta(days=365)

        features = LICENSE_FEATURES.get(license_type.value, [])
        license = License(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            license_type=license_type,
            status=LicenseStatus.ACTIVE,
            period=period,
            start_date=start_date,
            end_date=end_date,
            max_users=max_users,
            features=features
        )
        db.add(license)

        db.commit()
        print("Seeded missing admin/license for organization")
    except Exception as e:
        print(f"Error seeding default org/user/license: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database tables created")
    
    print("Initializing feature matrix...")
    initialize_feature_matrix()

    print("Initializing continent master...")
    initialize_continent_master()

    if os.getenv("ENABLE_SEED_DATA", "false").lower() == "true":
        print("Seeding default org/admin/license...")
        seed_default_org_user_license()
    else:
        print("Skipping seed data (ENABLE_SEED_DATA is not true).")
    print("Database initialization complete!")
