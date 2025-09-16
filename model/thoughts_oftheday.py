from sqlalchemy import Column, Integer, String, DateTime, func, Text
from db.database import Base

class ThoughtOfTheDay(Base):
    __tablename__ = "thoughts_of_the_day"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    thought = Column(Text, nullable=False)
    author_id = Column(Integer, nullable=False)
    author_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)