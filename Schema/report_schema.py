# Schema/report_schema.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class ReportCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Report title")
    description: str = Field(..., min_length=1, max_length=2000, description="Report description")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    user_id: int = Field(..., gt=0, description="User ID")
    
    class Config:
        from_attributes = True

class ReportUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)
    month: Optional[int] = Field(None, ge=1, le=12)
    status: Optional[str] = None
    
    class Config:
        from_attributes = True

class ReportResponse(BaseModel):
    id: int
    title: str
    description: str
    month: int
    user_id: int
    username: str
    document_path: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ReportListResponse(BaseModel):
    id: int
    title: str
    description: str
    month: int
    user_id: int
    username: str
    status: str
    created_at: datetime
    has_document: bool
    
    class Config:
        from_attributes = True
