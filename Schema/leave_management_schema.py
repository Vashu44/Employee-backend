from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

# Pydantic Models
class LeaveApplicationCreate(BaseModel):
    user_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str

class LeaveApplicationResponse(BaseModel):
    id: int
    user_id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    status: str
    applied_date: datetime
    approved_by: Optional[str]

    class Config:
        from_attributes = True

class LeaveStatusUpdate(BaseModel):
    status: str
    approved_by: Optional[str] = None

class CalendarLeaveDay(BaseModel):
    date: str
    leave_type: str
    status: str
