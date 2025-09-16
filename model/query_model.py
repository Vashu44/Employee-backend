from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base

class Query(Base):
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(200), nullable=False)

    message = Column(Text, nullable=False)
    category = Column(String(50), default="general")
    priority = Column(String(50), default="medium")
    status = Column(String(50), default="pending")
    
    user_email = Column(String(255), nullable=False)
    user_name = Column(String(255), nullable=False)

    response = Column(Text, nullable=True)
    responded_by = Column(String(255), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # FIX: Add server_default to prevent 'updated_at' from being null on INSERT
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="queries")
    responses = relationship("QueryResponse", back_populates="query", cascade="all, delete-orphan")

class QueryResponse(Base):
    __tablename__ = "query_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False)
    response_message = Column(Text, nullable=False)
    responded_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    query = relationship("Query", back_populates="responses")