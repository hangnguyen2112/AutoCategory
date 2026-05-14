"""
Initialize database and create admin user
Run this script once to set up the database
"""
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base, SessionLocal
from models import User
from auth import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Create all database tables"""
    logger.info("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables created successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create database tables: {e}")
        return False


def create_admin_user():
    """Create default admin user if not exists"""
    db = SessionLocal()
    try:
        # Check if admin user already exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        
        if existing_admin:
            logger.info("✓ Admin user already exists")
            return True
        
        # Create admin user
        logger.info("Creating admin user...")
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("admin123"),
            full_name="System Administrator",
            role="admin",
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        
        logger.info("✓ Admin user created successfully")
        logger.info("  Username: admin")
        logger.info("  Password: admin123")
        logger.warning("  ⚠️  Please change the admin password after first login!")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to create admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    """Main initialization function"""
    logger.info("=" * 60)
    logger.info("AutoCategory Database Initialization")
    logger.info("=" * 60)
    
    # Step 1: Create tables
    if not init_database():
        logger.error("Database initialization failed. Exiting.")
        return False
    
    # Step 2: Create admin user
    if not create_admin_user():
        logger.error("Admin user creation failed. Exiting.")
        return False
    
    logger.info("=" * 60)
    logger.info("✓ Database initialization completed successfully!")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
