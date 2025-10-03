from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Date, ForeignKey
import model.usermodels as usermodels
from db.database import Base,engine


# Database Models
class LeaveApplication(Base):
    __tablename__ = "leave_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer,ForeignKey("users.id",onupdate="CASCADE", ondelete="CASCADE"), index=True)
    leave_type = Column(String(10))  # Annual, Sick, Personal, etc.
    start_date = Column(Date)
    end_date = Column(Date)
    reason = Column(String(100))
    status = Column(String(10), default="pending")  # pending, approved, rejected
    applied_date = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(String(50), nullable=True) # HR MR

