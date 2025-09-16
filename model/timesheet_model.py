from sqlalchemy import Column, Integer, String, Date,ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base

class Timesheet(Base):
    __tablename__ = "timesheet"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id",onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    sheet_date = Column(Date, nullable=False, index=True)
    project_name = Column(String(255),  nullable=False)
    task_name = Column(String(255), nullable=False)
    task_description = Column(String(500), nullable=True)
    time_hour = Column(Integer)
    status = Column(String(10)) # pending Approved

    user = relationship("User", back_populates="timesheets")