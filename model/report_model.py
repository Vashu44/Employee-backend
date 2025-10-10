# model/report_model.py - COMPLETE VERSION WITH BOTH NAMES
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class HRReport(Base):
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    month = Column(Integer, nullable=False, index=True)
    report_type = Column(String(50), nullable=False, default="monthly")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_path = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="submitted", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # One-way relationship (no back_populates to avoid User model issues)
    user = relationship("User")
    
    def __repr__(self):
        return f"<HRReport(id={self.id}, title='{self.title}', user_id={self.user_id}, month={self.month})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "month": self.month,
            "report_type": self.report_type,
            "user_id": self.user_id,
            "document_path": self.document_path,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "username": self.user.username if self.user else None,
            "has_document": bool(self.document_path)
        }

# Create alias for backward compatibility
Report = HRReport  # This allows importing both 'Report' and 'HRReport'
