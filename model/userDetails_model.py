from sqlalchemy import Column, Integer, String, DateTime,Date, func, ForeignKey, LargeBinary,Text
from db.database import Base
from sqlalchemy.orm import relationship

class UserDetails(Base):
    __tablename__ = "user_details"  # Table for storing additional user details
    
    user_id = Column(Integer, ForeignKey('users.id',onupdate="CASCADE", ondelete="CASCADE"), primary_key=True, index=True)
    full_name = Column(String(100), nullable=True)  
    nickname = Column(String(100), nullable=True)
    bio = Column(Text)
    personal_email = Column(String(50), unique=True, index=True)
    created_at = Column(DateTime, default=func.now(), server_default=func.now())
    date_of_joining = Column(DateTime, default=func.now(), server_default=func.now())

    working_region_id =  Column(Integer,  ForeignKey("regions.id"), nullable = True)
    home_region_id = Column(Integer, ForeignKey("regions.id"), nullable = True)

    manager_name = Column(String(30), nullable = True)
    current_Department = Column(String(30), nullable=True) 
    current_role = Column(String(30), nullable = True)
    profile_pic = Column(LargeBinary, nullable=True)
    project_name = Column(String(50), nullable=True)

    user = relationship("User", back_populates="user_details")

    # Relationships with regions
    working_region = relationship("Region", foreign_keys=[working_region_id])
    home_region = relationship("Region", foreign_keys=[home_region_id])
    