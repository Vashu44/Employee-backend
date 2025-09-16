from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from fastapi import Body

from db.database import get_db
from Schema.mom_action_items_schema import (
    MoMActionItemCreate,
    MoMActionItemUpdate,
    MoMActionItemResponse,
    MoMActionItemListResponse,
    ReassignedActionItemListResponse
)
from service.mom_action_item_service import MoMActionItemService

router = APIRouter(prefix="/mom/action-items")

def get_action_item_service(db: Session = Depends(get_db)) -> MoMActionItemService:
    """Dependency to get MoM Action Item service"""
    return MoMActionItemService(db)

@router.post("/", response_model=MoMActionItemResponse, status_code=201)
def create_action_item(
    action_data: MoMActionItemCreate,
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Create a new MoM Action Item"""
    try:
        return service.create_action_item(action_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create action item: {str(e)}")

@router.get("/{action_id}", response_model=MoMActionItemResponse)
def get_action_item(
    action_id: int = Path(..., gt=0, description="Action item ID"),
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Get a specific MoM Action Item by ID"""
    action_item = service.get_action_item_by_id(action_id)
    if not action_item:
        raise HTTPException(status_code=404, detail="Action item not found")
    return action_item

@router.get("/", response_model=MoMActionItemListResponse)
def get_action_items(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    mom_id: Optional[int] = Query(None, gt=0, description="Filter by MoM ID"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned fullname"),
    due_date: Optional[date] = Query(None, description="Filter by due date (YYYY-MM-DD)"),
    updated_at: Optional[date] = Query(None, description="Filter by last updated date (YYYY-MM-DD)"),
    remark: Optional[str] = Query(None, description="Filter by remark content"),
    re_assigned_to: Optional[str] = Query(None, description="Filter by reassigned fullname"),
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Get list of MoM Action Items with optional filters and pagination"""
    return service.get_action_items(
        skip=skip,
        limit=limit,
        mom_id=mom_id,
        assigned_to=assigned_to,
        due_date=due_date,
        updated_at=updated_at,
        remark=remark,
        re_assigned_to=re_assigned_to
    )

@router.get("/mom/{mom_id}", response_model=List[MoMActionItemResponse])
def get_action_items_by_mom(
    mom_id: int = Path(..., gt=0, description="MoM ID"),
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Get all action items for a specific MoM"""
    return service.get_action_items_by_mom_id(mom_id)

@router.get("/user/{username}", response_model=List[MoMActionItemResponse])
def get_action_items_by_username(
    username: str = Path(..., description="Username"),
    sort_by: str = Query("due_date", description="Sort by field"),
    order: str = Query("asc", description="Sort order"),
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Get action items by username"""
    return service.get_action_items_by_assigned_username(username, sort_by, order)

@router.get("/overdue/all", response_model=List[MoMActionItemResponse])
def get_overdue_action_items(
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Get all overdue action items"""
    return service.get_overdue_action_items()

@router.get("/due-soon/all", response_model=List[MoMActionItemResponse])
def get_action_items_due_soon(
    days: int = Query(7, ge=1, le=30, description="Number of days to look ahead"),
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Get action items due within specified number of days"""
    return service.get_action_items_due_soon(days)


@router.put("/{action_id}", response_model=MoMActionItemResponse)
def update_action_item(
    action_id: int = Path(..., gt=0, description="Action item ID"),
    action_data: MoMActionItemUpdate = Body(...),
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Update an action item"""
    try:
        # Add current date to the update data
        update_dict = action_data.model_dump(exclude_unset=True)
        update_dict['updated_at'] = date.today()
        
        # Create new update object with updated_at
        updated_action_data = MoMActionItemUpdate(**update_dict)
        
        updated_action = service.update_action_item(action_id, updated_action_data)
        return updated_action
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{action_id}", status_code=204)
def delete_action_item(
    action_id: int = Path(..., gt=0, description="Action item ID"),
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Delete a specific MoM Action Item"""
    if not service.delete_action_item(action_id):
        raise HTTPException(status_code=404, detail="Action item not found")
    return None

@router.delete("/mom/{mom_id}", response_model=dict)
def delete_action_items_by_mom(
    mom_id: int = Path(..., gt=0, description="MoM ID"),
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Delete all action items for a specific MoM"""
    deleted_count = service.delete_action_items_by_mom_id(mom_id)
    return {"message": f"Deleted {deleted_count} action items for MoM {mom_id}"}

# Additional utility endpoints
@router.get("/stats/summary", response_model=dict)
def get_action_items_summary(
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Get summary statistics for action items"""
    overdue = service.get_overdue_action_items()
    due_soon = service.get_action_items_due_soon(7)
    
    return {
        "overdue_count": len(overdue),
        "due_soon_count": len(due_soon),
        "overdue_items": overdue,
        "due_soon_items": due_soon
    }

@router.post("/{action_id}/remark", response_model=MoMActionItemResponse)
async def add_remark_to_action_item(
    action_id: int = Path(..., gt=0, description="Action item ID"),
    remark_data: dict = Body(..., example={"text": "Task completed successfully"}),
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """Add a remark to an action item"""
    try:
        print(f"🚀 Router: Adding remark to action item {action_id}")
        # print(f"👤 Current user: {username}")
        print(f"📝 Remark data: {remark_data}")
        
        # Extract remark text
        remark_text = remark_data.get("text", "").strip()
        if not remark_text:
            raise HTTPException(status_code=400, detail="Remark text is required")
        
        print(f"📝 Processing remark: '{remark_text}'")
        username = remark_data.get("username", " ").strip()  # Use space if no username provided
        
        if not username:
            raise HTTPException(status_code=400, detail="Username is required")
        
        # Add remark
        updated_item = service.add_remark_to_action_item(
            action_id=action_id,
            remark_text=remark_text,
            username=username
        )
        
        if not updated_item:
            raise HTTPException(status_code=404, detail="Action item not found")
        
        print(f"✅ Successfully added remark, returning: {updated_item}")
        return updated_item
        
    except Exception as e:
        print(f"❌ Router error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    



# NEW: Route to get a specific reassigned action item
@router.get("/reassigned/{username}", response_model=ReassignedActionItemListResponse)
def get_reassigned_action_items_by_username(
    username: str = Path(..., description="Username of the person to whom action items are reassigned"),
    sort_by: str = Query("due_date", description="Sort by field (due_date, status, updated_at, meeting_date)"),
    order: str = Query("asc", description="Sort order (asc, desc)"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Number of records to return"),
    service: MoMActionItemService = Depends(get_action_item_service)
):
    """
    Get all action items reassigned to a specific username with detailed remark breakdown.
    
    This endpoint returns:
    - All action items where re_assigned_to matches the username
    - Complete action item details including original assignee
    - All remarks in JSON format with detailed breakdown
    - Remark count and latest remark
    - Remarks grouped by user
    - Pagination support
    """
    try:
        print(f"🚀 Router: Getting reassigned action items for {username}")
        result = service.get_action_items_by_reassigned_username(
            username=username,
            sort_by=sort_by,
            order=order,
            skip=skip,
            limit=limit
        )
        
        print(f"✅ Router: Found {result.total} reassigned action items")
        return result
        
    except Exception as e:
        print(f"❌ Router error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get reassigned action items: {str(e)}"
        )