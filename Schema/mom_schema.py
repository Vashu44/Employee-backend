from enum import Enum
from pydantic import BaseModel,Field
from typing import List, Optional, Dict, Any
from datetime import date, time
from Schema.mom_information_schema import MoMInformationResponse
from Schema.mom_decision_schema import MoMDecisionResponse
from Schema.mom_action_items_schema import MoMActionItemResponse

class MeetingType(str, Enum):
    Online = "Online"
    Offline = "Offline"
    Hybrid = "Hybrid"

class MoMStatus(str, Enum):
    Open = "Open"
    Closed = "Closed"
    Pending = "Pending"

class AgendaType(str, Enum):    
    Information = "Information"
    Decision = "Decision"
    ActionItem = "Action Item"

class MoMCreate(BaseModel):
    meeting_date: date 
    start_time: time  = Field(..., example="09:00")
    end_time: time = Field(..., example="10:00")
    attendees: List[str] = Field(..., example=["smriti", "hitesh"])
    absent: List[str] = Field(default=[], example=["john", "jane"], description="List of absent attendees")
    outer_attendees: List[str] = Field(..., example=["external@example.com"])
    project: str
    meeting_type: MeetingType
    location_link: str = Field(..., example="https://example.com/meeting", description="address of meeting location")
    status: str = 'open'
    created_by: int

class MoMUpdate(BaseModel):
    meeting_date: Optional[date] = None
    start_time: Optional[time] = Field(default=None, example="09:00")
    end_time: Optional[time] = Field(default=None, example="10:00")
    attendees: Optional[List[str]] = None
    absent: Optional[List[str]] = None
    outer_attendees: Optional[List[str]] = None
    project: Optional[str] = None
    meeting_type: Optional[MeetingType] = None
    location_link: Optional[str] = None
    status: Optional[MoMStatus] = None

class MoMResponse(BaseModel):
    id: int
    meeting_date: date
    start_time: time = Field(default=..., example="09:00")
    end_time: time = Field(default=..., example="10:00")
    attendees: List[str]
    absent: List[str] = []
    outer_attendees: List[str] = []
    project: str
    meeting_type: MeetingType
    location_link: str
    status: MoMStatus
    created_at: date
    created_by: int
    class Config:
        from_attributes = True

class MoMListResponse(BaseModel):
    moms: List[MoMResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class CompleteMoMResponse(BaseModel):
    """Complete MoM details including all related data"""
    # Basic MoM Information
    id: int
    meeting_date: date
    start_time: time
    end_time: time
    attendees: List[str]
    absent: List[str] = []
    outer_attendees: List[str] = []
    project: str
    meeting_type: MeetingType
    location_link: str
    status: MoMStatus
    created_at: date
    created_by: int
    
    # Related Information
    informations: List[MoMInformationResponse] = []
    decisions: List[MoMDecisionResponse] = []
    action_items: List[MoMActionItemResponse] = []
    
    # Summary counts
    total_informations: int = 0
    total_decisions: int = 0
    total_action_items: int = 0
    
    class Config:
        from_attributes = True

class MoMDeletionResponse(BaseModel):
    """Response schema for MoM deletion with summary"""
    mom_id: int
    deleted: bool
    summary: Dict[str, Any]
    message: str