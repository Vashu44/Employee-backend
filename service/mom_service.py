from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime
from math import ceil
from fastapi import Depends
from db.database import get_db
from model.mom_model import MoM, MoMStatus, MeetingType
from model.mom_model import MoMInformation 
from model.mom_model import MoMDecision 
from model.mom_model import MoMActionItem
from Schema.mom_schema import MoMCreate, MoMUpdate, MoMResponse, MoMListResponse


class MoMService:
    def __init__(self, db: Session):
        self.db = db

    def create_mom(self, mom_data: MoMCreate) -> MoMResponse:
        """Create a new MoM"""
        mom_dict = mom_data.model_dump()
        mom_dict['created_at'] = datetime.utcnow().date()  # Ensure created_at is set to current date
        
        db_mom = MoM(**mom_dict)
        self.db.add(db_mom)
        self.db.commit()
        self.db.refresh(db_mom)
        
        return MoMResponse.model_validate(db_mom)

    def get_mom_by_id(self, mom_id: int) -> Optional[MoMResponse]:
        """Get MoM by ID"""
        db_mom = self.db.query(MoM).filter(MoM.id == mom_id).first()
        if db_mom:
            return MoMResponse.model_validate(db_mom)
        return None

    def get_moms(
        self,
        skip: int = 0,
        limit: int = 10,
        project: Optional[str] = None,
        status: Optional[MoMStatus] = None,
        meeting_type: Optional[MeetingType] = None,
        meeting_date: Optional[date] = None,
        created_by: Optional[int] = None
    ) -> MoMListResponse:
        """Get list of MoMs with filters and pagination"""
        query = self.db.query(MoM)
        
        # Apply filters
        if project:
            query = query.filter(MoM.project.ilike(f"%{project}%"))
        if status:
            query = query.filter(MoM.status == status)
        if meeting_type:
            query = query.filter(MoM.meeting_type == meeting_type)
        if meeting_date:
            query = query.filter(MoM.meeting_date == meeting_date)
        if created_by:
            query = query.filter(MoM.created_by == created_by)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and order
        db_moms = query.order_by(MoM.meeting_date.desc(), MoM.created_at.desc()).offset(skip).limit(limit).all()
        
        # Convert to response models
        moms = [MoMResponse.model_validate(mom) for mom in db_moms]
        
        return MoMListResponse(
            moms=moms,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            total_pages=ceil(total / limit) if total > 0 else 0
        )

    def update_mom(self, mom_id: int, mom_data: MoMUpdate) -> Optional[MoMResponse]:
        """Update an existing MoM"""
        db_mom = self.db.query(MoM).filter(MoM.id == mom_id).first()
        if not db_mom:
            return None
        
        # Update only provided fields
        for field, value in mom_data.model_dump(exclude_unset=True).items():
            setattr(db_mom, field, value)
        
        self.db.commit()
        self.db.refresh(db_mom)
        
        return MoMResponse.model_validate(db_mom)

    def delete_mom(self, mom_id: int) -> bool:
        """Delete a MoM"""
        db_mom = self.db.query(MoM).filter(MoM.id == mom_id).first()
        if not db_mom:
            return False
        
        self.db.delete(db_mom)
        self.db.commit()
        return True

    def get_moms_by_project(self, project: str) -> List[MoMResponse]:
        """Get all MoMs for a specific project"""
        db_moms = self.db.query(MoM).filter(MoM.project.ilike(f"%{project}%")).order_by(MoM.meeting_date.desc()).all()
        return [MoMResponse.model_validate(mom) for mom in db_moms]

    def get_moms_by_status(self, status: MoMStatus) -> List[MoMResponse]:
        """Get all MoMs with specific status"""
        db_moms = self.db.query(MoM).filter(MoM.status == status).order_by(MoM.meeting_date.desc()).all()
        return [MoMResponse.model_validate(mom) for mom in db_moms]

    def update_mom_status(self, mom_id: int, status: MoMStatus) -> Optional[MoMResponse]:
        """Update only the status of a MoM"""
        db_mom = self.db.query(MoM).filter(MoM.id == mom_id).first()
        if not db_mom:
            return None

        db_mom.status = status
        self.db.commit()
        self.db.refresh(db_mom)
        
        return MoMResponse.model_validate(db_mom)

    