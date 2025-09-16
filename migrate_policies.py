#!/usr/bin/env python3
"""
Database migration script to add new columns to policies table
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment variables"""
    MYSQL_URL_DATABASE = os.getenv("DATABASE_URL")
    
    if not MYSQL_URL_DATABASE:
        # Fallback: construct URL if DATABASE_URL not found
        DB_USER = os.getenv("DB_USER")
        DB_PASSWORD = os.getenv("DB_PASSWORD")
        DB_HOST = os.getenv("DB_HOST")
        DB_PORT = os.getenv("DB_PORT")
        DB_NAME = os.getenv("DB_NAME")
        
        MYSQL_URL_DATABASE = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    return MYSQL_URL_DATABASE

def migrate_policies_table():
    """Add new columns to policies table"""
    session = None
    try:
        # Get database URL
        database_url = get_database_url()
        logger.info(f"Connecting to database...")
        
        # Create engine and session
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Check existing columns first
        result = session.execute(text("DESCRIBE policies"))
        existing_columns = [col[0] for col in result.fetchall()]
        
        # List of columns to add with their definitions
        columns_to_add = [
            ("policy_category", "VARCHAR(100)"),
            ("effective_date", "DATETIME"),
            ("applicable_roles", "JSON"),
            ("pdf_filename", "VARCHAR(255)"),
            ("pdf_path", "VARCHAR(512)")
        ]
        
        logger.info("Adding new columns to policies table...")
        
        for column_name, column_type in columns_to_add:
            if column_name not in existing_columns:
                sql_command = f"ALTER TABLE policies ADD COLUMN {column_name} {column_type}"
                try:
                    logger.info(f"Executing: {sql_command}")
                    session.execute(text(sql_command))
                    session.commit()
                    logger.info(f"✓ Column '{column_name}' added successfully")
                except Exception as e:
                    logger.error(f"✗ Error adding column '{column_name}': {e}")
                    session.rollback()
            else:
                logger.info(f"✓ Column '{column_name}' already exists, skipping")
        
        logger.info("Migration completed successfully!")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    
    finally:
        if session:
            session.close()
    
    return True

def verify_table_structure():
    """Verify that all columns exist in the policies table"""
    session = None
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Check table structure
        result = session.execute(text("DESCRIBE policies"))
        columns = result.fetchall()
        
        logger.info("Current policies table structure:")
        for column in columns:
            logger.info(f"  {column[0]} - {column[1]}")
        
        # Check if all required columns exist
        required_columns = ['policy_category', 'effective_date', 'applicable_roles', 'pdf_filename', 'pdf_path']
        existing_columns = [col[0] for col in columns]
        
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            logger.warning(f"Missing columns: {missing_columns}")
            return False
        else:
            logger.info("✓ All required columns exist")
            return True
            
    except Exception as e:
        logger.error(f"Error verifying table structure: {e}")
        return False
    finally:
        if session:
            session.close()

if __name__ == "__main__":
    logger.info("Starting policies table migration...")
    
    # First verify current structure
    logger.info("Checking current table structure...")
    verify_table_structure()
    
    # Run migration
    if migrate_policies_table():
        logger.info("Migration completed successfully!")
        
        # Verify the migration
        logger.info("Verifying migration...")
        if verify_table_structure():
            logger.info("✓ Migration verified successfully!")
            sys.exit(0)
        else:
            logger.error("✗ Migration verification failed!")
            sys.exit(1)
    else:
        logger.error("✗ Migration failed!")
        sys.exit(1)
