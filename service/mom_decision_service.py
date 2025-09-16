from sqlalchemy.orm import Session
from typing import List, Optional
from math import ceil

from model.mom_model import MoMDecision
from Schema.mom_decision_schema import MoMDecisionCreate, MoMDecisionUpdate, MoMDecisionResponse, MoMDecisionListResponse

class MoMDecisionService:
    def __init__(self, db: Session):
        self.db = db

    def create_decision(self, decision_data: MoMDecisionCreate) -> MoMDecisionResponse:
        """Create a new MoM Decision"""
        decision_dict = decision_data.model_dump()
        
        db_decision = MoMDecision(**decision_dict)
        self.db.add(db_decision)
        self.db.commit()
        self.db.refresh(db_decision)
        
        return MoMDecisionResponse.model_validate(db_decision)

    def get_decision_by_id(self, decision_id: int) -> Optional[MoMDecisionResponse]:
        """Get Decision by ID"""
        db_decision = self.db.query(MoMDecision).filter(MoMDecision.id == decision_id).first()
        if db_decision:
            return MoMDecisionResponse.model_validate(db_decision)
        return None

    def get_decisions(
        self,
        skip: int = 0,
        limit: int = 10,
        mom_id: Optional[int] = None
    ) -> MoMDecisionListResponse:
        """Get list of MoM Decisions with filters and pagination"""
        query = self.db.query(MoMDecision)
        
        # Apply filters
        if mom_id:
            query = query.filter(MoMDecision.mom_id == mom_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and order
        db_decisions = query.order_by(MoMDecision.id.desc()).offset(skip).limit(limit).all()
        
        # Convert to response models
        decisions = [MoMDecisionResponse.model_validate(decision) for decision in db_decisions]
        
        return MoMDecisionListResponse(
            decisions=decisions,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
            total_pages=ceil(total / limit) if total > 0 else 0
        )

    def get_decisions_by_mom_id(self, mom_id: int) -> List[MoMDecisionResponse]:
        """Get all decisions for a specific MoM"""
        db_decisions = self.db.query(MoMDecision).filter(MoMDecision.mom_id == mom_id).all()
        return [MoMDecisionResponse.model_validate(decision) for decision in db_decisions]

    def update_decision(self, decision_id: int, decision_data: MoMDecisionUpdate) -> Optional[MoMDecisionResponse]:
        """Update an existing MoM Decision"""
        db_decision = self.db.query(MoMDecision).filter(MoMDecision.id == decision_id).first()
        if not db_decision:
            return None
        
        # Update only provided fields
        for field, value in decision_data.model_dump(exclude_unset=True).items():
            setattr(db_decision, field, value)
        
        self.db.commit()
        self.db.refresh(db_decision)
        
        return MoMDecisionResponse.model_validate(db_decision)

    def delete_decision(self, decision_id: int) -> bool:
        """Delete a MoM Decision"""
        db_decision = self.db.query(MoMDecision).filter(MoMDecision.id == decision_id).first()
        if not db_decision:
            return False
        
        self.db.delete(db_decision)
        self.db.commit()
        return True

    def delete_decisions_by_mom_id(self, mom_id: int) -> int:
        """Delete all decisions for a specific MoM"""
        count = self.db.query(MoMDecision).filter(MoMDecision.mom_id == mom_id).count()
        self.db.query(MoMDecision).filter(MoMDecision.mom_id == mom_id).delete()
        self.db.commit()
        return count