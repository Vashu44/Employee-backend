from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import date as date_type

class HolidayResponse(BaseModel):
    id: int
    date: date_type
    name: str
    type: str
    description: Optional[str] = None
    is_public: bool
    calendar_id: Optional[int] = None 
    
    class Config:
        from_attributes = True

# models for CRUD operations
class HolidayEventCreate(BaseModel):
    name: str
    date: date_type
    description: Optional[str] = None
    country_code: str = "IN"  # Default to India
    calendar_id: Optional[int] = None

class HolidayEventUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[date_type] = None
    description: Optional[str] = None


class RegionResponse(BaseModel):
    id: int
    name: str
    code: str
    country: str
    
    class Config:
        from_attributes = True

class HolidayCalendarResponse(BaseModel):
    # Request inf
    request_type: str
    
    # Filter parameters
    year: Optional[int] = None
    month: Optional[int] = None
    date: Optional[int] = None
    search_term: Optional[str] = None
    all_years: Optional[bool] = None
    
    # Response data
    filter_description: str
    calendar_grid: Optional[List[List[int]]] = None
    holidays: Optional[List[HolidayResponse]] = None
    holidays_by_year: Optional[Dict] = None
    total_holidays: int
    
    # Meta information
    api_source: str
    available_years: List[int]