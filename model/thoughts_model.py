from sqlalchemy import Column, Integer, Text, String, DateTime
from sqlalchemy.sql import func
from db.database import Base

class Thought(Base):
    __tablename__ = "thoughts"

    id = Column(Integer, primary_key=True, index=True)
    thoughts = Column(Text, nullable=False)
    author = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, nullable=False)