from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from db.database import Base

class Policy(Base):
    __tablename__ = "policies"
   
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    department = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    policy_category = Column(String(100), nullable=True)
    effective_date = Column(DateTime, nullable=True)
    applicable_roles = Column(JSON, nullable=True)  # Store array of applicable role levels
    pdf_filename = Column(String(255), nullable=True)
    pdf_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
