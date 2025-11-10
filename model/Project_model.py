from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from db.database import Base
from datetime import datetime

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String(50), unique=True, index=True, nullable=False)
    description = Column(String(500), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    client_name = Column(String(100), nullable=True)
    project_code = Column(String(50), unique=True, index=True, nullable=False)
    status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)