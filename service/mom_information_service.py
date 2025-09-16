from sqlalchemy.orm import Session
from typing import List, Optional
from math import ceil

from model.mom_model import MoMInformation
from Schema.mom_information_schema import MoMInformationCreate, MoMInformationUpdate, MoMInformationResponse, MoMInformationListResponse

class MoMInformationService:
    def __init__(self, db: Session):
        self.db = db

    def create_information(self, info_data: MoMInformationCreate) -> MoMInformationResponse:
        """Create a new MoM Information"""
        info_dict = info_data.model_dump()
        
        db_info = MoMInformation(**info_dict)
        self.db.add(db_info)
        self.db.commit()
        self.db.refresh(db_info)
        
        return MoMInformationResponse.model_validate(db_info)

    def get_information_by_id(self, info_id: int) -> Optional[MoMInformationResponse]:
        """Get Information by ID"""
        db_info = self.db.query(MoMInformation).filter(MoMInformation.id == info_id).first()
        if db_info:
            return MoMInformationResponse.model_validate(db_info)
        return None

    def get_informations(
        self,
        skip: int = 0,
        limit: int = 10,
        mom_id: Optional[int] = None
    ) -> MoMInformationListResponse:
        """Get list of MoM Informations with filters and pagination"""
        query = self.db.query(MoMInformation)
        
        # Apply filters
        if mom_id:
            query = query.filter(MoMInformation.mom_id == mom_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and order
        db_informations = query.order_by(MoMInformation.id.desc()).offset(skip).limit(limit).all()
        
        # Convert to response models
        informations = [MoMInformationResponse.model_validate(info) for info in db_informations]
        
        return MoMInformationListResponse(
            informations=informations,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            total_pages=ceil(total / limit) if total > 0 else 0
        )

    def get_informations_by_mom_id(self, mom_id: int) -> List[MoMInformationResponse]:
        """Get all informations for a specific MoM"""
        db_informations = self.db.query(MoMInformation).filter(MoMInformation.mom_id == mom_id).all()
        return [MoMInformationResponse.model_validate(info) for info in db_informations]

    def update_information(self, info_id: int, info_data: MoMInformationUpdate) -> Optional[MoMInformationResponse]:
        """Update an existing MoM Information"""
        db_info = self.db.query(MoMInformation).filter(MoMInformation.id == info_id).first()
        if not db_info:
            return None
        
        # Update only provided fields
        for field, value in info_data.model_dump(exclude_unset=True).items():
            setattr(db_info, field, value)
        
        self.db.commit()
        self.db.refresh(db_info)
        
        return MoMInformationResponse.model_validate(db_info)

    def delete_information(self, info_id: int) -> bool:
        """Delete a MoM Information"""
        db_info = self.db.query(MoMInformation).filter(MoMInformation.id == info_id).first()
        if not db_info:
            return False
        
        self.db.delete(db_info)
        self.db.commit()
        return True

    def delete_informations_by_mom_id(self, mom_id: int) -> int:
        """Delete all informations for a specific MoM"""
        count = self.db.query(MoMInformation).filter(MoMInformation.mom_id == mom_id).count()
        self.db.query(MoMInformation).filter(MoMInformation.mom_id == mom_id).delete()
        self.db.commit()
        return count