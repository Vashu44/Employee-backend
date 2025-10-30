from fastapi import HTTPException, Depends,APIRouter
from sqlalchemy.orm import Session
from typing import List, Optional
from Schema.leave_management_schema import LeaveApplicationResponse,LeaveApplicationCreate,LeaveStatusUpdate,CalendarLeaveDay
from db.database import get_db
import logging
from model.leave_model import LeaveApplication

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# API Endpoints
@router.post("/leave-applications/", response_model= LeaveApplicationResponse )
def create_leave_application(leave: LeaveApplicationCreate, db: Session = Depends(get_db)):
    """Create a new leave application"""
    db_leave = LeaveApplication(**leave.dict())
    db.add(db_leave)
    db.commit()
    db.refresh(db_leave)
    return db_leave

@router.get("/leave-applications/", response_model=List[LeaveApplicationResponse])
def get_leave_applications(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all leave applications with optional filtering"""
    query = db.query(LeaveApplication)

    if user_id:
        query = query.filter(LeaveApplication.user_id == user_id)
    if status:
        query = query.filter(LeaveApplication.status == status)
    
    return query.all()

@router.get("/leave-applications/{leave_id}", response_model=LeaveApplicationResponse)
def get_leave_application(leave_id: int, db: Session = Depends(get_db)):
    """Get a specific leave application"""
    leave = db.query(LeaveApplication).filter(LeaveApplication.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave application not found")
    return leave

@router.put("/leave-applications/{leave_id}/status")
def update_leave_status(
    leave_id: int,
    status_update: LeaveStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update leave application status"""
    try:
        logger.info(
            "Updating leave status",
            extra={
                "leave_id": leave_id,
                "new_status": status_update.status,
                "approved_by": status_update.approved_by,
            },
        )

        valid_statuses = {"pending", "approved", "rejected"}
        if status_update.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status value '{status_update.status}'. Allowed: {', '.join(valid_statuses)}",
            )

        leave = db.query(LeaveApplication).filter(LeaveApplication.id == leave_id).first()
        if not leave:
            raise HTTPException(status_code=404, detail="Leave application not found")

        leave.status = status_update.status
        if status_update.approved_by:
            leave.approved_by = status_update.approved_by

        db.commit()
        db.refresh(leave)

        logger.info(
            "Leave status updated successfully",
            extra={
                "leave_id": leave_id,
                "persisted_status": leave.status,
                "persisted_approved_by": leave.approved_by,
            },
        )

        return {"message": "Status updated successfully", "leave_id": leave_id, "status": leave.status}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update leave status", extra={"leave_id": leave_id})
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update leave status")

@router.get("/calendar/leave-days/", response_model=List[CalendarLeaveDay])
def get_calendar_leave_days(
    user_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get leave days for calendar display"""
    from datetime import date as date_obj
    
    query = db.query(LeaveApplication)

    if user_id:
        query = query.filter(LeaveApplication.user_id == user_id)

    if year and month:
        start_of_month = date_obj(year, month, 1)
        if month == 12:
            end_of_month = date_obj(year + 1, 1, 1)
        else:
            end_of_month = date_obj(year, month + 1, 1)
        
        query = query.filter(
            LeaveApplication.start_date < end_of_month,
            LeaveApplication.end_date >= start_of_month
        )
    
    leave_applications = query.all()
    
    leave_days = []
    for leave_app in leave_applications:
        current_date = leave_app.start_date
        while current_date <= leave_app.end_date: # type: ignore
            # Only include if within the requested month (if specified)
            if not (year and month) or (current_date.year == year and current_date.month == month):
                leave_days.append(CalendarLeaveDay(
                    date=current_date.isoformat(),
                    leave_type=leave_app.leave_type, # type: ignore
                    status=leave_app.status # type: ignore
                ))
            
            # Move to next day
            from datetime import timedelta
            current_date += timedelta(days=1)
    
    return leave_days

@router.delete("/leave-applications/{leave_id}")
def delete_leave_application(leave_id: int, db: Session = Depends(get_db)):
    """Delete a leave application"""
    leave = db.query(LeaveApplication).filter(LeaveApplication.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave application not found")
    
    db.delete(leave)
    db.commit()
    return {"message": "Leave application deleted successfully"}

@router.get("/leave-applications/hr-view/", response_model=List[LeaveApplicationResponse])
def hr_view_leave_applications(
    current_user_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """HR view for leave applications with filtering by user and status"""
    query = db.query(LeaveApplication)
    if current_user_id:
        # Exclude HR's own leaves, show all other employees' leaves
        query = query.filter(LeaveApplication.user_id != current_user_id)
    if status:
        query = query.filter(LeaveApplication.status == status)
    return query.all()