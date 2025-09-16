from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class AwardTypeEnum(str, Enum):
    EMPLOYEE_OF_THE_MONTH = "Employee of the Month"
    BEST_PERFORMER = "Best Performer"
    INNOVATION_CHAMPION = "Innovation Champion"
    TEAM_PLAYER = "Team Player"
    CUSTOMER_EXCELLENCE = "Customer Excellence"
    LEADERSHIP_EXCELLENCE = "Leadership Excellence"

class BadgeLevelEnum(str, Enum):
    GOLD = "gold"
    SILVER = "silver"
    BRONZE = "bronze"

class AppreciationCreate(BaseModel):
    employee_id: int
    given_by_id: int 
    award_type: AwardTypeEnum
    badge_level: BadgeLevelEnum
    appreciation_message: str
    month: str 
    year: int
    
    @validator('appreciation_message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Appreciation message cannot be empty')
        if len(v) > 1000:
            raise ValueError('Appreciation message cannot exceed 1000 characters')
        return v.strip()

class AppreciationUpdate(BaseModel):
    appreciation_message: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('appreciation_message')
    def validate_message(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Appreciation message cannot be empty')
            if len(v) > 1000:
                raise ValueError('Appreciation message cannot exceed 1000 characters')
            return v.strip()
        return v

class AppreciationResponse(BaseModel):
    id: int
    employee_id: int
    employee_username: str
    employee_email: str
    given_by_id: int
    given_by_username: str
    award_type: str
    badge_level: str
    appreciation_message: str
    month: str
    year: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class EmployeeAppreciationSummary(BaseModel):
    employee_id: int
    employee_username: str
    employee_email: str
    total_appreciations: int
    gold_badges: int
    silver_badges: int
    bronze_badges: int
    latest_appreciation: Optional[AppreciationResponse] = None

class DashboardAppreciation(BaseModel):
    id: int
    employee_username: str
    award_type: str
    badge_level: str
    appreciation_message: str
    month: str
    year: int
    created_at: datetime

class MonthlyHighlightResponse(BaseModel):
    id: int
    employee_name: str
    award_type: str
    badge_level: str
    month: str
    year: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class CommentResponse(BaseModel):
    id: int
    user_id: int
    username: str
    text: str
    created_at: datetime

    class Config:
        from_attributes = True

# FIXED: Added user_id field to CommentCreate as required by the router
class CommentCreate(BaseModel):
    text: str
    user_id: int  # This field was missing and is required by the router
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Comment text cannot be empty')
        if len(v) > 500:
            raise ValueError('Comment text cannot exceed 500 characters')
        return v.strip()

class LikeResponse(BaseModel):
    total_likes: int
    is_liked_by_user: bool