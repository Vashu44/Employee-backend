from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class QueryStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class QueryPriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class QueryCategoryEnum(str, Enum):
    GENERAL = "general"
    TECHNICAL = "technical"
    HR = "hr"
    PAYROLL = "payroll"
    LEAVE = "leave"
    SYSTEM = "system"

class QueryCreate(BaseModel):
    subject: str
    message: str
    category: QueryCategoryEnum = QueryCategoryEnum.GENERAL
    priority: QueryPriorityEnum = QueryPriorityEnum.MEDIUM

    @validator('subject')
    def validate_subject(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Subject cannot be empty')
        if len(v) > 200:
            raise ValueError('Subject cannot exceed 200 characters')
        return v.strip()

    @validator('message')
    def validate_message(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Message cannot be empty')
        if len(v) > 1000:
            raise ValueError('Message cannot exceed 1000 characters')
        return v.strip()
    
    # Add validators to handle string to enum conversion
    @validator('category', pre=True)
    def validate_category(cls, v):
        if isinstance(v, str):
            # Convert string to enum
            v = v.lower()
            if v in ['general', 'technical', 'hr', 'payroll', 'leave', 'system']:
                return v
        return v
    
    @validator('priority', pre=True)  
    def validate_priority(cls, v):
        if isinstance(v, str):
            # Convert string to enum
            v = v.lower()
            if v in ['low', 'medium', 'high', 'urgent']:
                return v
        return v

class QueryResponse(BaseModel):
    id: int
    user_id: int
    subject: str
    message: str
    category: QueryCategoryEnum
    priority: QueryPriorityEnum
    status: QueryStatusEnum
    user_email: str
    user_name: str
    response: Optional[str] = None
    responded_by: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class QueryUpdate(BaseModel):
    status: Optional[QueryStatusEnum] = None
    response: Optional[str] = None
        
    @validator('response')
    def validate_response(cls, v):
        if v and len(v.strip()) == 0:
            return None
        if v and len(v) > 2000:
            raise ValueError('Response cannot exceed 2000 characters')
        return v.strip() if v else v

class QueryResponseCreate(BaseModel):
    response_text: str
    is_internal_note: bool = False

    @validator('response_text')
    def validate_response_text(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Response text cannot be empty')
        if len(v) > 2000:
            raise ValueError('Response text cannot exceed 2000 characters')
        return v.strip()

class QueryListResponse(BaseModel):
    id: int
    subject: str
    category: QueryCategoryEnum
    priority: QueryPriorityEnum
    status: QueryStatusEnum
    user_name: str
    user_email: str
    created_at: datetime
    has_response: bool = False

    class Config:
        from_attributes = True

class QueryStatsResponse(BaseModel):
    total_queries: int
    pending_queries: int
    in_progress_queries: int
    resolved_queries: int
    queries_by_category: dict
    queries_by_priority: dict