from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from db.database import get_db 
from Schema.mom_information_schema import MoMInformationCreate, MoMInformationUpdate, MoMInformationResponse, MoMInformationListResponse
from service.mom_information_service import MoMInformationService

router = APIRouter(prefix="/mom/mom-information")

def get_information_service(db: Session = Depends(get_db)) -> MoMInformationService:
    return MoMInformationService(db)

@router.post("/", response_model=MoMInformationResponse, status_code=status.HTTP_201_CREATED)
async def create_information(
    info_data: MoMInformationCreate,
    service: MoMInformationService = Depends(get_information_service)
):
    """Create a new MoM Information"""
    try:
        return service.create_information(info_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating MoM Information: {str(e)}"
        )

@router.get("/", response_model=MoMInformationListResponse)
async def get_informations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    mom_id: Optional[int] = Query(None, description="Filter by MoM ID"),
    service: MoMInformationService = Depends(get_information_service)
):
    """Get list of MoM Informations with filters and pagination"""
    return service.get_informations(
        skip=skip,
        limit=limit,
        mom_id=mom_id
    )

@router.get("/{info_id}", response_model=MoMInformationResponse)
async def get_information_by_id(
    info_id: int,
    service: MoMInformationService = Depends(get_information_service)
):
    """Get a specific MoM Information by ID"""
    info = service.get_information_by_id(info_id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MoM Information not found"
        )
    return info

@router.put("/{info_id}", response_model=MoMInformationResponse)
async def update_information(
    info_id: int,
    info_data: MoMInformationUpdate,
    service: MoMInformationService = Depends(get_information_service)
):
    """Update an existing MoM Information"""
    info = service.update_information(info_id, info_data)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MoM Information not found"
        )
    return info

@router.delete("/{info_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_information(
    info_id: int,
    service: MoMInformationService = Depends(get_information_service)
):
    """Delete a MoM Information"""
    success = service.delete_information(info_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MoM Information not found"
        )

@router.get("/mom/{mom_id}", response_model=List[MoMInformationResponse])
async def get_informations_by_mom_id(
    mom_id: int,
    service: MoMInformationService = Depends(get_information_service)
):
    """Get all informations for a specific MoM"""
    return service.get_informations_by_mom_id(mom_id)

@router.delete("/mom/{mom_id}", status_code=status.HTTP_200_OK)
async def delete_informations_by_mom_id(
    mom_id: int,
    service: MoMInformationService = Depends(get_information_service)
):
    """Delete all informations for a specific MoM"""
    count = service.delete_informations_by_mom_id(mom_id)
    return {"message": f"Deleted {count} information(s) for MoM ID {mom_id}"}