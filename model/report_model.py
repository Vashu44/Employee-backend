# model/report_model.py - Enhanced for all MySQL query types
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime

class HRReport(Base):
    __tablename__ = "hr_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    query_category = Column(String(10), nullable=False)  # DDL, DML, DQL, DCL, TCL
    query_type = Column(String(20), nullable=False)  # SELECT, INSERT, UPDATE, DELETE, etc.
    sql_query = Column(Text, nullable=False)
    result_data = Column(Text, nullable=True)  # JSON string of results
    affected_rows = Column(Integer, default=0)
    execution_time = Column(String(20), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_approved = Column(Boolean, default=False)  # For dangerous operations
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String(20), default="pending")  # pending, completed, failed, requires_approval
    
    # Relationships
    user = relationship("User", back_populates="hr_reports", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
