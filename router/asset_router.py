from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from model.asset_model import Asset, AssetClaim, AssetStatusHistory
from model.usermodels import User
from Schema.asset_schema import (
    AssetCreate, AssetResponse,
    AssetClaimCreate, AssetClaimProcess, AssetClaimResponse,
    AssetStatusUpdate, AssetStatusHistoryResponse,
    AssetCategoryEnum
)
from db.database import get_db

router = APIRouter(
    prefix="/api/assets",
)

@router.get("/health")
async def health_check():
    """Health check endpoint for asset management"""
    return {"status": "ok", "message": "Asset management system is healthy"}

@router.get("/categories")
async def get_asset_categories():
    """Get all available asset categories"""
    return [{"value": category.value, "label": category.value.replace('_', ' ').title()}
            for category in AssetCategoryEnum]

@router.post("/create", response_model=AssetResponse)
async def create_asset(asset_data: AssetCreate, db: Session = Depends(get_db)):
    """Create a new asset"""
    try:
        existing_asset = db.query(Asset).filter(Asset.asset_code == asset_data.asset_code).first()
        if existing_asset:
            raise HTTPException(status_code=400, detail="Asset code already exists")

        if asset_data.serial_number:
            existing_serial = db.query(Asset).filter(Asset.serial_number == asset_data.serial_number).first()
            if existing_serial:
                raise HTTPException(status_code=400, detail="Serial number already exists")

        asset_dict = asset_data.model_dump()
        db_asset = Asset(**asset_dict)
        db.add(db_asset)
        db.commit()
        db.refresh(db_asset)

        # Create initial status history record
        status_history = AssetStatusHistory(
            asset_id=db_asset.id,
            previous_status=None,
            new_status="available",
            previous_approval_status=None,
            new_approval_status="pending",
            changed_by=1,  # System user or admin
            remarks="Asset created",
            action_type="creation"
        )
        db.add(status_history)
        db.commit()

        return AssetResponse(**db_asset.to_dict())

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating asset: {str(e)}")

@router.get("/list", response_model=List[AssetResponse])
async def get_all_assets(
    category: Optional[str] = None,
    status: Optional[str] = None,
    approval_status: Optional[str] = None,
    provided_to_employee: Optional[str] = None,
    available_only: Optional[bool] = False,
    db: Session = Depends(get_db)
):
    """Get all assets with optional filters"""
    try:
        query = db.query(Asset)

        if category:
            query = query.filter(Asset.category == category)

        if status:
            query = query.filter(Asset.status == status)

        if approval_status:
            query = query.filter(Asset.approval_status == approval_status)

        if provided_to_employee:
            query = query.filter(Asset.provided_to_employee == provided_to_employee)

        if available_only:
            query = query.filter(Asset.status == "available")

        assets = query.order_by(Asset.created_at.desc()).all()
        return [AssetResponse(**asset.to_dict()) for asset in assets]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving assets: {str(e)}")

@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset_by_id(asset_id: int, db: Session = Depends(get_db)):
    """Get detailed asset information by ID"""
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        return AssetResponse(**asset.to_dict())

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving asset: {str(e)}")

@router.put("/{asset_id}/approve")
async def approve_reject_asset(
    asset_id: int,
    approval_status: str,
    hr_id: int,
    rejection_reason: Optional[str] = None,
    remarks: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """HR approves or rejects an asset"""
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        if approval_status not in ["approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Invalid approval status")

        # Store previous status for history
        previous_approval_status = asset.approval_status

        # Update asset approval status
        asset.approval_status = approval_status
        asset.approved_by = hr_id
        asset.approved_at = datetime.utcnow()
        asset.updated_at = datetime.utcnow()

        if approval_status == "rejected":
            asset.rejection_reason = rejection_reason

        # Create status history record
        status_history = AssetStatusHistory(
            asset_id=asset_id,
            previous_approval_status=previous_approval_status,
            new_approval_status=approval_status,
            previous_status=asset.status,
            new_status=asset.status,
            changed_by=hr_id,
            remarks=remarks,
            action_type="approval" if approval_status == "approved" else "rejection"
        )

        db.add(status_history)
        db.commit()
        db.refresh(asset)

        return {
            "message": f"Asset {approval_status} successfully",
            "asset_id": asset_id,
            "approval_status": asset.approval_status,
            "approved_at": asset.approved_at.isoformat() if asset.approved_at else None
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing approval: {str(e)}")

@router.put("/{asset_id}/provision")
async def mark_asset_provision(
    asset_id: int,
    provided_to_employee: str,
    hr_id: int,
    remarks: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """HR marks whether asset has been provided to employee"""
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        if asset.approval_status != "approved":
            raise HTTPException(status_code=400, detail="Asset must be approved before provision")

        if provided_to_employee not in ["yes", "no"]:
            raise HTTPException(status_code=400, detail="Invalid provision status")

        # Store previous status for history
        previous_provision_status = asset.provided_to_employee
        previous_asset_status = asset.status

        # Update provision status
        asset.provided_to_employee = provided_to_employee
        asset.updated_at = datetime.utcnow()

        # If provided to employee, update asset status to assigned
        if provided_to_employee == "yes":
            asset.status = "assigned"

        # Create status history record
        status_history = AssetStatusHistory(
            asset_id=asset_id,
            previous_approval_status=asset.approval_status,
            new_approval_status=asset.approval_status,
            previous_status=previous_asset_status,
            new_status=asset.status,
            changed_by=hr_id,
            remarks=remarks,
            action_type="provision"
        )

        db.add(status_history)
        db.commit()
        db.refresh(asset)

        return {
            "message": f"Asset provision status updated to {provided_to_employee}",
            "asset_id": asset_id,
            "provided_to_employee": asset.provided_to_employee,
            "status": asset.status
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating provision status: {str(e)}")

@router.put("/{asset_id}/status")
async def update_asset_status(
    asset_id: int,
    status_data: AssetStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update asset approval status and provision status"""
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Store previous statuses for history
        previous_approval_status = asset.approval_status
        previous_provision_status = asset.provided_to_employee
        previous_asset_status = asset.status

        # Update approval status
        asset.approval_status = status_data.approval_status
        asset.updated_at = datetime.utcnow()

        # Update provision status if provided
        if status_data.provided_to_employee:
            asset.provided_to_employee = status_data.provided_to_employee
            
            # If provided to employee, update asset status to assigned
            if status_data.provided_to_employee == "yes":
                asset.status = "assigned"

        # Create status history record
        status_history = AssetStatusHistory(
            asset_id=asset_id,
            previous_approval_status=previous_approval_status,
            new_approval_status=status_data.approval_status,
            previous_status=previous_asset_status,
            new_status=asset.status,
            changed_by=status_data.changed_by,
            remarks=status_data.remarks,
            action_type="status_update"
        )

        db.add(status_history)
        db.commit()
        db.refresh(asset)

        return AssetResponse(**asset.to_dict())

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating asset status: {str(e)}")

@router.get("/{asset_id}/history", response_model=List[AssetStatusHistoryResponse])
async def get_asset_status_history(
    asset_id: int,
    db: Session = Depends(get_db)
):
    """Get complete status history for an asset"""
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        history = db.query(AssetStatusHistory).filter(
            AssetStatusHistory.asset_id == asset_id
        ).order_by(AssetStatusHistory.changed_at.desc()).all()

        return [AssetStatusHistoryResponse(**record.to_dict()) for record in history]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving asset history: {str(e)}")

@router.get("/pending-approval", response_model=List[AssetResponse])
async def get_pending_approval_assets(db: Session = Depends(get_db)):
    """Get all assets pending approval"""
    try:
        assets = db.query(Asset).filter(
            Asset.approval_status == "pending"
        ).order_by(Asset.created_at.desc()).all()

        return [AssetResponse(**asset.to_dict()) for asset in assets]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving pending assets: {str(e)}")

@router.get("/approved-not-provided", response_model=List[AssetResponse])
async def get_approved_not_provided_assets(db: Session = Depends(get_db)):
    """Get all approved assets not yet provided to employees"""
    try:
        assets = db.query(Asset).filter(
            Asset.approval_status == "approved",
            Asset.provided_to_employee == "no"
        ).order_by(Asset.approved_at.desc()).all()

        return [AssetResponse(**asset.to_dict()) for asset in assets]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving approved assets: {str(e)}")

@router.post("/claims/create", response_model=AssetClaimResponse)
async def create_asset_claim(
    claim_data: AssetClaimCreate,
    employee_id: int,
    db: Session = Depends(get_db)
):
    """Employee creates an asset claim"""
    try:
        asset = db.query(Asset).filter(Asset.id == claim_data.asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        if asset.status != "available":
            raise HTTPException(status_code=400, detail="Asset is not available for claiming")

        if asset.approval_status != "approved":
            raise HTTPException(status_code=400, detail="Asset must be approved before claiming")

        employee = db.query(User).filter(User.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")

        existing_claim = db.query(AssetClaim).filter(
            AssetClaim.asset_id == claim_data.asset_id,
            AssetClaim.employee_id == employee_id,
            AssetClaim.status == "pending"
        ).first()

        if existing_claim:
            raise HTTPException(status_code=400, detail="You already have a pending claim for this asset")

        db_claim = AssetClaim(
            **claim_data.model_dump(),
            employee_id=employee_id
        )

        db.add(db_claim)
        db.commit()
        db.refresh(db_claim)

        return AssetClaimResponse(**db_claim.to_dict())

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating claim: {str(e)}")

@router.get("/claims/list", response_model=List[AssetClaimResponse])
async def get_all_claims(
    status: Optional[str] = None,
    employee_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all asset claims with optional filters"""
    try:
        query = db.query(AssetClaim)

        if status:
            query = query.filter(AssetClaim.status == status)

        if employee_id:
            query = query.filter(AssetClaim.employee_id == employee_id)

        claims = query.order_by(AssetClaim.claimed_at.desc()).all()
        return [AssetClaimResponse(**claim.to_dict()) for claim in claims]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving claims: {str(e)}")

@router.put("/claims/{claim_id}/process")
async def process_claim(
    claim_id: int,
    process_data: AssetClaimProcess,
    hr_id: int,
    db: Session = Depends(get_db)
):
    """HR approves or rejects an asset claim"""
    try:
        claim = db.query(AssetClaim).filter(AssetClaim.id == claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")

        if claim.status != "pending":
            raise HTTPException(status_code=400, detail="Claim has already been processed")

        claim.status = process_data.status
        claim.processed_by = hr_id
        claim.processed_at = datetime.utcnow()
        claim.hr_remarks = process_data.hr_remarks

        if process_data.status == "approved":
            asset = db.query(Asset).filter(Asset.id == claim.asset_id).first()
            if asset:
                asset.status = "assigned"
                asset.assigned_to = claim.employee_id
                asset.provided_to_employee = "yes"
                asset.updated_at = datetime.utcnow()

                # Create status history record for asset assignment
                status_history = AssetStatusHistory(
                    asset_id=asset.id,
                    previous_approval_status=asset.approval_status,
                    new_approval_status=asset.approval_status,
                    previous_status="available",
                    new_status="assigned",
                    changed_by=hr_id,
                    remarks=f"Asset assigned to employee via claim {claim_id}",
                    action_type="assignment"
                )
                db.add(status_history)

        db.commit()
        db.refresh(claim)

        return {
            "message": f"Claim {process_data.status} successfully",
            "claim_id": claim_id,
            "status": claim.status
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing claim: {str(e)}")

@router.get("/stats/dashboard")
async def get_asset_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics for asset management"""
    try:
        total_assets = db.query(Asset).count()
        available_assets = db.query(Asset).filter(Asset.status == "available").count()
        assigned_assets = db.query(Asset).filter(Asset.status == "assigned").count()
        maintenance_assets = db.query(Asset).filter(Asset.status == "maintenance").count()

        # Approval statistics
        pending_approval = db.query(Asset).filter(Asset.approval_status == "pending").count()
        approved_assets = db.query(Asset).filter(Asset.approval_status == "approved").count()
        rejected_assets = db.query(Asset).filter(Asset.approval_status == "rejected").count()

        # Provision statistics
        approved_not_provided = db.query(Asset).filter(
            Asset.approval_status == "approved",
            Asset.provided_to_employee == "no"
        ).count()
        
        approved_and_provided = db.query(Asset).filter(
            Asset.approval_status == "approved",
            Asset.provided_to_employee == "yes"
        ).count()

        # Claims statistics
        pending_claims = db.query(AssetClaim).filter(AssetClaim.status == "pending").count()
        approved_claims = db.query(AssetClaim).filter(AssetClaim.status == "approved").count()
        rejected_claims = db.query(AssetClaim).filter(AssetClaim.status == "rejected").count()

        # Get all unique categories
        categories = db.query(Asset.category).distinct().all()
        category_stats = []
        for (category,) in categories:
            count = db.query(Asset).filter(Asset.category == category).count()
            if count > 0:
                category_stats.append({
                    "category": category,
                    "count": count
                })

        return {
            "total_assets": total_assets,
            "available_assets": available_assets,
            "assigned_assets": assigned_assets,
            "maintenance_assets": maintenance_assets,
            "pending_approval": pending_approval,
            "approved_assets": approved_assets,
            "rejected_assets": rejected_assets,
            "approved_not_provided": approved_not_provided,
            "approved_and_provided": approved_and_provided,
            "pending_claims": pending_claims,
            "approved_claims": approved_claims,
            "rejected_claims": rejected_claims,
            "category_stats": category_stats,
            "approval_rate": round((approved_assets / total_assets * 100), 2) if total_assets > 0 else 0,
            "provision_rate": round((approved_and_provided / approved_assets * 100), 2) if approved_assets > 0 else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard stats: {str(e)}")

@router.get("/stats/approval-dashboard")
async def get_approval_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics for asset approval workflow"""
    try:
        total_assets = db.query(Asset).count()
        pending_approval = db.query(Asset).filter(Asset.approval_status == "pending").count()
        approved_assets = db.query(Asset).filter(Asset.approval_status == "approved").count()
        rejected_assets = db.query(Asset).filter(Asset.approval_status == "rejected").count()
        
        approved_not_provided = db.query(Asset).filter(
            Asset.approval_status == "approved",
            Asset.provided_to_employee == "no"
        ).count()
        
        approved_and_provided = db.query(Asset).filter(
            Asset.approval_status == "approved",
            Asset.provided_to_employee == "yes"
        ).count()

        return {
            "total_assets": total_assets,
            "pending_approval": pending_approval,
            "approved_assets": approved_assets,
            "rejected_assets": rejected_assets,
            "approved_not_provided": approved_not_provided,
            "approved_and_provided": approved_and_provided,
            "approval_rate": round((approved_assets / total_assets * 100), 2) if total_assets > 0 else 0,
            "provision_rate": round((approved_and_provided / approved_assets * 100), 2) if approved_assets > 0 else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving approval dashboard stats: {str(e)}")
