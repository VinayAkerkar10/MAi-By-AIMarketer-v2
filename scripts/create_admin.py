# Script to create initial admin user
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

import sys
import os
import uuid
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.shared.database import SessionLocal, Organization, User, License, LicenseType, LicenseStatus, LicensePeriod, UserRole
from services.shared.auth import get_password_hash
from services.shared.config import LICENSE_FEATURES

def create_admin():
    """Create initial organization and admin user"""
    db = SessionLocal()
    
    try:
        # Create organization
        org_name = input("Enter organization name: ").strip()
        if not org_name:
            print("Organization name is required")
            return
        
        # Check if org exists
        existing_org = db.query(Organization).filter(Organization.name == org_name).first()
        if existing_org:
            print(f"Organization '{org_name}' already exists")
            org = existing_org
        else:
            org = Organization(
                id=str(uuid.uuid4()),
                name=org_name,
                status="active"
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"Organization '{org_name}' created with ID: {org.id}")
        
        # Create admin user
        user_id = input("Enter admin user ID: ").strip()
        if not user_id:
            print("User ID is required")
            return
        
        password = input("Enter admin password: ").strip()
        if not password:
            print("Password is required")
            return
        
        # Check if user exists
        existing_user = db.query(User).filter(
            User.organization_id == org.id,
            User.user_id == user_id
        ).first()
        
        if existing_user:
            print(f"User '{user_id}' already exists in organization")
            return
        
        # Create admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            user_id=user_id,
            email=input("Enter admin email (optional): ").strip() or None,
            password_hash=get_password_hash(password),
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print(f"Admin user '{user_id}' created successfully")
        
        # Assign license
        print("\nLicense types:")
        print("1. strategy_only - Strategy AI + Templates")
        print("2. strategy_leads - Strategy + Lead Enrichment")
        print("3. full_suite - All features")
        
        license_choice = input("Select license type (1-3): ").strip()
        license_map = {
            "1": LicenseType.STRATEGY_ONLY,
            "2": LicenseType.STRATEGY_LEADS,
            "3": LicenseType.FULL_SUITE
        }
        
        license_type = license_map.get(license_choice, LicenseType.FULL_SUITE)
        
        period_choice = input("License period (monthly/yearly/one_time): ").strip().lower()
        period_map = {
            "monthly": LicensePeriod.MONTHLY,
            "yearly": LicensePeriod.YEARLY,
            "one_time": LicensePeriod.ONE_TIME
        }
        period = period_map.get(period_choice, LicensePeriod.MONTHLY)
        
        # Calculate end date
        start_date = datetime.utcnow()
        end_date = None
        if period == LicensePeriod.MONTHLY:
            end_date = start_date + timedelta(days=30)
        elif period == LicensePeriod.YEARLY:
            end_date = start_date + timedelta(days=365)
        
        # Get features for license type
        features = LICENSE_FEATURES.get(license_type.value, [])
        
        license = License(
            id=str(uuid.uuid4()),
            organization_id=org.id,
            license_type=license_type,
            status=LicenseStatus.ACTIVE,
            period=period,
            start_date=start_date,
            end_date=end_date,
            max_users=10,
            features=features
        )
        db.add(license)
        db.commit()
        
        print(f"\n✅ Setup complete!")
        print(f"Organization: {org.name} (ID: {org.id})")
        print(f"Admin User: {user_id}")
        print(f"License: {license_type.value} ({period.value})")
        print(f"\nYou can now login at: http://localhost:8000/api/auth/org-login")
        print(f"Organization Name: {org.name}")
        print(f"User ID: {user_id}")
        print(f"Password: [the password you entered]")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
