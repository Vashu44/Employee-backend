from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from db.database import get_db 
from model import usermodels
from model.mom_model import MoMStatus,MeetingType
from Schema.mom_schema import MoMCreate, MoMUpdate, MoMResponse, MoMListResponse, MeetingType,CompleteMoMResponse, MoMDeletionResponse
from service.mom_service import MoMService
from service.mom_information_service import MoMInformationService
from service.mom_decision_service import MoMDecisionService
from service.mom_action_item_service import MoMActionItemService
from sqlalchemy.orm import Session


router = APIRouter(prefix="/mom")

def get_mom_service(db: Session = Depends(get_db)) -> MoMService:
    return MoMService(db)

@router.post("/", response_model=MoMResponse, status_code=status.HTTP_201_CREATED)
async def create_mom(
    mom_data: MoMCreate,
    service: MoMService = Depends(get_mom_service)
):
    """Create a new Minutes of Meeting"""
    try:
        return service.create_mom(mom_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating MoM: {str(e)}"
        )

@router.get("/", response_model=MoMListResponse)
async def get_moms(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    project: Optional[str] = Query(None, description="Filter by project name"),
    status: Optional[MoMStatus] = Query(None, description="Filter by status"),
    meeting_type: Optional[MeetingType] = Query(None, description="Filter by meeting type"),
    
    meeting_date: Optional[date] = Query(None, description="Filter by meeting date"),
    created_by: Optional[int] = Query(None, description="Filter by creator user ID"),
    service: MoMService = Depends(get_mom_service)
):
    """Get list of Minutes of Meeting with filters and pagination"""
    return service.get_moms(
        skip=skip,
        limit=limit,
        project=project,
        status=status,
        meeting_date=meeting_date,
        created_by=created_by
    )

@router.get("/{mom_id}", response_model=MoMResponse)
async def get_mom_by_id(
    mom_id: int,
    service: MoMService = Depends(get_mom_service)
):
    """Get a specific Minutes of Meeting by ID"""
    mom = service.get_mom_by_id(str(mom_id))
    if not mom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MoM not found"
        )
    return mom

@router.put("/{mom_id}", response_model=MoMResponse)
async def update_mom(
    mom_id: str,
    mom_data: MoMUpdate,
    service: MoMService = Depends(get_mom_service)
):
    """Update an existing Minutes of Meeting"""
    mom = service.update_mom(mom_id, mom_data)
    if not mom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MoM not found"
        )
    return mom

@router.delete("/{mom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mom(
    mom_id: str,
    service: MoMService = Depends(get_mom_service)
):
    """Delete a Minutes of Meeting"""
    success = service.delete_mom(mom_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MoM not found"
        )

@router.patch("/{mom_id}/status", response_model=MoMResponse)
async def update_mom_status(
    mom_id: int,
    mom_status: MoMStatus,
    service: MoMService = Depends(get_mom_service)
):
    """Update only the status of a Minutes of Meeting"""
    mom = service.update_mom_status(str(mom_id), mom_status)
    if not mom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MoM not found"
        )
    return mom

@router.get("/project/{project}", response_model=List[MoMResponse])
async def get_moms_by_project(
    project: str,
    service: MoMService = Depends(get_mom_service)
):
    """Get all Minutes of Meeting for a specific project"""
    return service.get_moms_by_project(project)



def get_deletion_services(db: Session = Depends(get_db)):
        """Get all required services for deletion"""
        return {
            'mom_service': MoMService(db),
            'information_service': MoMInformationService(db),
            'decision_service': MoMDecisionService(db),
            'action_item_service': MoMActionItemService(db)
        }
def get_services(db: Session = Depends(get_db)):
        """Get all required services"""
        return {
            'mom_service': MoMService(db),
            'information_service': MoMInformationService(db),
            'decision_service': MoMDecisionService(db),
            'action_item_service': MoMActionItemService(db)
        }  

@router.get("/{mom_id}/complete", response_model=CompleteMoMResponse)
async def get_complete_mom_details(
    mom_id: int,
    services: dict = Depends(get_services)
):
    """
    Get complete MoM details including:
    - Basic MoM information
    - All information items
    - All decisions
    - All action items
    """
    try:
        # Get basic MoM details
        mom = services['mom_service'].get_mom_by_id(mom_id)
        if not mom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MoM with ID {mom_id} not found"
            )
        
        # Get related information
        informations = services['information_service'].get_informations_by_mom_id(mom_id)
        decisions = services['decision_service'].get_decisions_by_mom_id(mom_id)
        action_items = services['action_item_service'].get_action_items_by_mom_id(mom_id)
        
        # Create complete response
        complete_mom = CompleteMoMResponse(
            # Basic MoM fields
            id=mom.id,
            meeting_date=mom.meeting_date,
            start_time=mom.start_time,
            end_time=mom.end_time,
            attendees=mom.attendees,
            absent=mom.absent,
            outer_attendees=mom.outer_attendees,
            project=mom.project,
            meeting_type=mom.meeting_type,
            location_link=mom.location_link,
            status=mom.status,
            created_at=mom.created_at,
            created_by=mom.created_by,
            
            # Related data
            informations=informations,
            decisions=decisions,
            action_items=action_items,
            
            # Summary counts
            total_informations=len(informations),
            total_decisions=len(decisions),
            total_action_items=len(action_items)
        )
        
        return complete_mom
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching complete MoM details: {str(e)}"
        )

@router.delete("/{mom_id}/complete", response_model=MoMDeletionResponse)
async def delete_complete_mom(
    mom_id: int,
    services: dict = Depends(get_deletion_services)
):
    """
    Delete complete MoM and all related data:
    - Basic MoM record
    - All information items
    - All decisions  
    - All action items
    
    Returns deletion summary with counts
    """
    try:
        # First check if MoM exists
        mom = services['mom_service'].get_mom_by_id(mom_id)
        if not mom:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"MoM with ID {mom_id} not found"
            )
        
        # Get counts before deletion for summary
        informations = services['information_service'].get_informations_by_mom_id(mom_id)
        decisions = services['decision_service'].get_decisions_by_mom_id(mom_id)
        action_items = services['action_item_service'].get_action_items_by_mom_id(mom_id)
        
        info_count = len(informations)
        decision_count = len(decisions)
        action_item_count = len(action_items)
        
        # Delete all related data first (due to foreign key constraints)
        deleted_informations = services['information_service'].delete_informations_by_mom_id(mom_id)
        deleted_decisions = services['decision_service'].delete_decisions_by_mom_id(mom_id)
        deleted_action_items = services['action_item_service'].delete_action_items_by_mom_id(mom_id)
        
        # Finally delete the main MoM record
        mom_deleted = services['mom_service'].delete_mom(mom_id)
        
        if not mom_deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete MoM record"
            )
        
        # Prepare summary
        deletion_summary = {
            "mom_details": {
                "project": mom.project,
                "meeting_date": mom.meeting_date.isoformat(),
                "status": mom.status.value,
                "created_by": mom.created_by
            },
            "deleted_counts": {
                "informations": deleted_informations,
                "decisions": deleted_decisions,
                "action_items": deleted_action_items,
                "total_items": deleted_informations + deleted_decisions + deleted_action_items
            },
            "verification": {
                "expected_informations": info_count,
                "expected_decisions": decision_count,
                "expected_action_items": action_item_count,
                "all_deleted_successfully": (
                    deleted_informations == info_count and
                    deleted_decisions == decision_count and
                    deleted_action_items == action_item_count
                )
            }
        }
        
        return MoMDeletionResponse(
            mom_id=mom_id,
            deleted=True,
            summary=deletion_summary,
            message=f"Successfully deleted MoM {mom_id} and all related data"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting complete MoM: {str(e)}"
        )
