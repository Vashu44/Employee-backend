from pydantic import BaseModel
from datetime import date

class TimesheetCreate(BaseModel):
    user_id: int
    sheet_date: date
    project_name: str
    task_name: str
    task_description: str
    time_hour: int
    status: str = "pending"  # Default status is 'pending'

class TimesheetOut(TimesheetCreate):
    id: int

    model_config={
        "from_attributes": True
    }