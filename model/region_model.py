from sqlalchemy import Column, Integer, String
from db.database import Base 

class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    country_code = Column(String(10), nullable=True)

    # relationship with holiday
    # holidays = relationship("Holiday", back_populates="region", cascade="all, delete", passive_deletes=True)
