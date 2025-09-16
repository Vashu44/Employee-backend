from pydantic import BaseModel
from datetime import date
from typing import Optional

class HolidayOut(BaseModel):
    id: int
    date: date
    name: str
    description: Optional[str]
    is_active: bool
    country_code: str
    calendar_id: Optional[int]

    class Config:
        orm_mode = True