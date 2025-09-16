from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
import os
from dotenv import load_dotenv
import urllib.parse

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT") 
DB_NAME = os.getenv("DB_NAME")

# dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Use the DATABASE_URL directly from .env file (already URL encoded)
MYSQL_URL_DATABASE = os.getenv("DATABASE_URL")

# Fallback: construct URL if DATABASE_URL not found
if not MYSQL_URL_DATABASE:
    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME]):
        raise ValueError("Database configuration incomplete. Please check your .env file.")
    
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    MYSQL_URL_DATABASE = f"mysql+pymysql://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
# Create the database/SQLAlchemy engine with additional configurations
engine = create_engine(
    MYSQL_URL_DATABASE,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    pool_size=5,         # Connection pool size
    max_overflow=10      # Max overflow connections
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#base class for declarative models
Base = declarative_base()