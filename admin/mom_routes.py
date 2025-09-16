from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from sqlalchemy.orm import Session
from db.database import get_db
from model.mom_model import MoMInformation,MoMDecision,MoMActionItem,MoM
from service.mom_service import MoMService
from service.mom_information_service import MoMInformationService
from service.mom_decision_service import MoMDecisionService
from service.mom_action_item_service import MoMActionItemService
from model.mom_model import MoM, MoMStatus, MeetingType
from Schema.mom_schema import (
    MoMCreate, MoMUpdate, MoMResponse, CompleteMoMResponse
)
from Schema.mom_action_items_schema import MoMActionItemResponse
from .auth_utils import admin_required
import logging

router = APIRouter()

# Configure templates
templates = Jinja2Templates(directory="templates")

def get_mom_service(db: Session = Depends(get_db)) -> MoMService:
    return MoMService(db)

def get_all_services(db: Session = Depends(get_db)):
    return {
        'mom_service': MoMService(db),
        'information_service': MoMInformationService(db),
        'decision_service': MoMDecisionService(db),
        'action_item_service': MoMActionItemService(db)
    }

@router.get("/ai-tracker", response_class=HTMLResponse)
async def get_mom_page(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    project: Optional[str] = Query(None),
    status: Optional[MoMStatus] = Query(None),
    meeting_type: Optional[MeetingType] = Query(None),
    services: dict = Depends(get_all_services),
    admin_username: str = Depends(admin_required)
):
    """Render the MOM management page with initial data"""    
    try:
        # Get initial MoMs with pagination
        mom_list = services['mom_service'].get_moms(
            skip=skip,
            limit=limit,
            project=project,
            status=status,
            meeting_type=meeting_type
        )
        
        # Get complete details for each MoM including related data
        complete_moms = []
        for mom in mom_list.moms:
            # Get related data
            informations = services['information_service'].get_informations_by_mom_id(mom.id)
            decisions = services['decision_service'].get_decisions_by_mom_id(mom.id)
            action_items = services['action_item_service'].get_action_items_by_mom_id(mom.id)
            
            # Create complete MoM object
            complete_mom = {
                **mom.dict(),
                "informations": informations,
                "decisions": decisions,
                "action_items": action_items,
                "total_informations": len(informations),
                "total_decisions": len(decisions),
                "total_action_items": len(action_items)
            }
            complete_moms.append(complete_mom)

        logging.info(f"Found {len(complete_moms)} MoMs with complete data")
        
        return templates.TemplateResponse(
            "admin/ai-tracker.html",
            {
                "request": request,
                "admin_name": admin_username,
                "moms": complete_moms,
                "total": mom_list.total,
                "page": (skip // limit) + 1,
                "total_pages": (mom_list.total + limit - 1) // limit,
                "filters": {
                    "project": project,
                    "status": status,
                    "meeting_type": meeting_type
                }
            }
        )
    except Exception as e:
        logging.error(f"Error loading MoM page: {str(e)}")
        return templates.TemplateResponse(
            "admin/ai-tracker.html",
            {
                "request": request,
                "admin_name": admin_username,
                "moms": [],
                "error": str(e),
                "page": 1,
                "total_pages": 1
            }
        )

@router.post("/create", response_model=MoMResponse)
async def create_mom(
    mom: MoMCreate, 
    request: Request, 
    db: Session = Depends(get_db),
    admin_username: str = Depends(admin_required)
):
    """Create a new MOM"""
    db_mom = MoM(**mom.dict())
    db.add(db_mom)
    db.commit()
    db.refresh(db_mom)
    return MoMResponse.from_orm(db_mom)

@router.get("/{mom_id}/complete", response_model=CompleteMoMResponse)
async def get_mom_complete(
    mom_id: int, 
    request: Request, 
    db: Session = Depends(get_db),
    admin_username: str = Depends(admin_required)
):
    """Get complete MoM details including all related data"""
    # Get basic MoM info
    mom = db.query(MoM).filter(MoM.id == mom_id).first()
    if not mom:
        raise HTTPException(status_code=404, detail="MOM not found")

    # Get all related data
    informations = db.query(MoMInformation).filter(MoMInformation.mom_id == mom_id).all()
    decisions = db.query(MoMDecision).filter(MoMDecision.mom_id == mom_id).all()
    action_items = db.query(MoMActionItem).filter(MoMActionItem.mom_id == mom_id).all()

    # Create complete response
    response = {
        "id": mom.id,
        "meeting_date": mom.meeting_date,
        "start_time": mom.start_time,
        "end_time": mom.end_time,
        "attendees": mom.attendees,
        "absent": mom.absent,
        "outer_attendees": mom.outer_attendees,
        "project": mom.project,
        "meeting_type": mom.meeting_type,
        "location_link": mom.location_link,
        "status": mom.status,
        "created_at": mom.created_at,
        "created_by": mom.created_by,
        "informations": [
            {"id": info.id, "information": info.information}
            for info in informations
        ],
        "decisions": [
            {"id": decision.id, "decision": decision.decision}
            for decision in decisions
        ],
        "action_items": [
            {
                "id": item.id,
                "action_item": item.action_item,
                "assigned_to": item.assigned_to,
                "due_date": item.due_date,
                "status": item.status,
                "remark": item.remark,
                "project": item.project,
                "updated_at": item.updated_at,
                "re_assigned_to": item.re_assigned_to,
                "meeting_date": item.meeting_date
            }
            for item in action_items
        ],
        "total_informations": len(informations),
        "total_decisions": len(decisions),
        "total_action_items": len(action_items)
    }
    
    return response

@router.put("/{mom_id}", response_model=MoMResponse)
async def update_mom(
    mom_id: int, 
    mom_update: MoMUpdate, 
    request: Request, 
    db: Session = Depends(get_db),
    admin_username: str = Depends(admin_required)
):
    """Update a MOM"""
    mom = db.query(MoM).filter(MoM.id == mom_id).first()
    if not mom:
        raise HTTPException(status_code=404, detail="MOM not found")
    
    for key, value in mom_update.dict(exclude_unset=True).items():
        setattr(mom, key, value)
    
    db.commit()
    db.refresh(mom)
    return MoMResponse.from_orm(mom)

@router.delete("/{mom_id}")
async def delete_mom(
    mom_id: int, 
    request: Request, 
    db: Session = Depends(get_db),
    admin_username: str = Depends(admin_required)
):
    """Delete a MOM"""
    mom = db.query(MoM).filter(MoM.id == mom_id).first()
    if not mom:
        raise HTTPException(status_code=404, detail="MOM not found")
    
    db.delete(mom)
    db.commit()
    return {"message": "MOM deleted successfully"}

# MOM Action Item routes
@router.get("/action-items/mom/{mom_id}", response_model=List[MoMActionItemResponse])
async def get_mom_action_items(
    mom_id: int, 
    request: Request, 
    db: Session = Depends(get_db),
    admin_username: str = Depends(admin_required)
):
    """Get all action items for a specific MOM"""
    items = db.query(MoMActionItem).filter(MoMActionItem.mom_id == mom_id).all()
    return [MoMActionItemResponse.from_orm(item) for item in items]
