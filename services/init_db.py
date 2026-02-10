# Database Initialization Script
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database import init_db, FeatureMatrix, LicenseType, SessionLocal
from shared.config import LICENSE_FEATURES

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

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Database tables created")
    
    print("Initializing feature matrix...")
    initialize_feature_matrix()
    print("Database initialization complete!")
