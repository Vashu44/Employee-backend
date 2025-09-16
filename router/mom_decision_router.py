from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from db.database import get_db 
from Schema.mom_decision_schema import MoMDecisionCreate, MoMDecisionUpdate, MoMDecisionResponse, MoMDecisionListResponse
from service.mom_decision_service import MoMDecisionService

router = APIRouter(prefix="/mom-decision")

def get_decision_service(db: Session = Depends(get_db)) -> MoMDecisionService:
    return MoMDecisionService(db)

@router.post("/", response_model=MoMDecisionResponse, status_code=status.HTTP_201_CREATED)
async def create_decision(
    decision_data: MoMDecisionCreate,
    service: MoMDecisionService = Depends(get_decision_service)
):
    """Create a new MoM Decision"""
    try:
        return service.create_decision(decision_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating MoM Decision: {str(e)}"
        )

@router.get("/", response_model=MoMDecisionListResponse)
async def get_decisions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    mom_id: Optional[int] = Query(None, description="Filter by MoM ID"),
    service: MoMDecisionService = Depends(get_decision_service)
):
    """Get list of MoM Decisions with filters and pagination"""
    return service.get_decisions(
        skip=skip,
        limit=limit,
        mom_id=mom_id
    )

@router.get("/{decision_id}", response_model=MoMDecisionResponse)
async def get_decision_by_id(
    decision_id: int,
    service: MoMDecisionService = Depends(get_decision_service)
):
    """Get a specific MoM Decision by ID"""
    decision = service.get_decision_by_id(decision_id)
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MoM Decision not found"
        )
    return decision

@router.put("/{decision_id}", response_model=MoMDecisionResponse)
async def update_decision(
    decision_id: int,
    decision_data: MoMDecisionUpdate,
    service: MoMDecisionService = Depends(get_decision_service)
):
    """Update an existing MoM Decision"""
    decision = service.update_decision(decision_id, decision_data)
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MoM Decision not found"
        )
    return decision

@router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_decision(
    decision_id: int,
    service: MoMDecisionService = Depends(get_decision_service)
):
    """Delete a MoM Decision"""
    success = service.delete_decision(decision_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MoM Decision not found"
        )

@router.get("/mom/{mom_id}", response_model=List[MoMDecisionResponse])
async def get_decisions_by_mom_id(
    mom_id: int,
    service: MoMDecisionService = Depends(get_decision_service)
):
    """Get all decisions for a specific MoM"""
    return service.get_decisions_by_mom_id(mom_id)

@router.delete("/mom/{mom_id}", status_code=status.HTTP_200_OK)
async def delete_decisions_by_mom_id(
    mom_id: int,
    service: MoMDecisionService = Depends(get_decision_service)
):
    """Delete all decisions for a specific MoM"""
    count = service.delete_decisions_by_mom_id(mom_id)
    return {"message": f"Deleted {count} decision(s) for MoM ID {mom_id}"}