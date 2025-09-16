from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, Boolean, Text, DateTime
from db.database import Base

    

class Holiday(Base):
    __tablename__ = "holidays"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)

    # region_id = Column(Integer, nullable = True)            # ForeignKey("regions.id")
    country_code = Column(String(10), nullable=False, index=True)
    calendar_id = Column(Integer, default= 000)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # region = relationship("Region", back_populates="holidays")
    