from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import date
from enum import Enum

class ActionItemStatus(str, Enum):
    Pending = "Pending"
    InProgress = "In Progress"
    Completed = "Completed"
    Cancelled = "Cancelled"

class RemarkItem(BaseModel):
    text: str = Field(..., description="Remark text")
    by: str = Field(..., description="Person who added the remark")
    remark_date: date = Field(..., description="Date of the remark")

class MoMActionItemCreate(BaseModel):
    mom_id: int = Field(..., description="ID of the MoM this action item belongs to")
    action_item: str = Field(..., max_length=255, description="Action item content")
    assigned_to: str = Field(..., description="Username of the person assigned to this action item")
    due_date: date = Field(..., description="Due date for the action item")
    status: ActionItemStatus = Field(default=ActionItemStatus.Pending, description="Status of the action item")
    project: str = Field(..., description="Project associated with the action item")
    meeting_date: date = Field(..., description="Date when the action item was assigned")

class MoMActionItemUpdate(BaseModel):
    action_item: Optional[str] = Field(None, max_length=255, description="Action item content")
    assigned_to: Optional[str] = Field(None, description="Username of the person assigned to this action item")
    due_date: Optional[date] = Field(None, description="Due date for the action item")
    status: Optional[ActionItemStatus] = Field(None, description="Status of the action item")
    remark: Optional[List[Dict[str, Any]]] = Field(None, description="List of remarks (JSON array)")
    updated_at: Optional[date] = Field(None, description="Date of the the completion task")
    re_assigned_to: Optional[str] = Field(None, description="Username of the person to whom the action item is reassigned")

class MoMActionItemResponse(BaseModel):
    id: int
    mom_id: int
    project: str
    action_item: str
    assigned_to: str
    due_date: date
    status: ActionItemStatus
    remark: Optional[List[Dict[str, Any]]] = None
    updated_at: Optional[date] = None
    re_assigned_to: Optional[str] = None
    meeting_date: date = Field(..., description="Date when the action item was assigned")

    class Config:
        from_attributes = True

class MoMActionItemListResponse(BaseModel):
    action_items: List[MoMActionItemResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

    class Config:
        from_attributes = True

class ReassignedActionItemResponse(BaseModel):
    id: int
    mom_id: int
    project: str
    action_item: str
    assigned_to: str  # Original assignee
    re_assigned_to: str  # Current assignee (from re_assigned_to column)
    due_date: date
    status: ActionItemStatus
    updated_at: Optional[date] = None
    meeting_date: date = Field(..., description="Date when the action item was assigned")
    
    # Detailed remark breakdown
    all_remarks: Optional[List[Dict[str, Any]]] = Field(None, description="All remarks as stored in JSON")
    remark_count: int = Field(0, description="Total number of remarks")
    latest_remark: Optional[Dict[str, Any]] = Field(None, description="Most recent remark")
    remarks_by_user: Optional[Dict[str, List[Dict[str, Any]]]] = Field(None, description="Remarks grouped by user")

    class Config:
        from_attributes = True

class ReassignedActionItemListResponse(BaseModel):
    action_items: List[ReassignedActionItemResponse]
    total: int
    page: int
    per_page: int
    total_pages: int
    
    class Config:
        from_attributes = True

class MoMActionItemListResponse(BaseModel):
    action_items: List[MoMActionItemResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

    class Config:
        from_attributes = True
