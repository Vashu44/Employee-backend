from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, extract, desc
from typing import List, Optional
from datetime import datetime, date, timedelta
import uuid
import os
from pathlib import Path

# Import database and models
from db.database import get_db
from model.usermodels import User
from model.expense_model import (
    ExpenseCategory, SoftwareAsset, ExpenseClaim, 
    ExpenseItem, SoftwareLicense, ExpenseDocument, ExpenseApproval,
    ExpenseReimbursement, DepartmentBudget, ExpenseAuditLog
)
from Schema.expense_schema import (
    ExpenseCategoryCreate, ExpenseCategoryUpdate, ExpenseCategoryResponse,
    SoftwareAssetCreate, SoftwareAssetUpdate, SoftwareAssetResponse,
    ExpenseClaimCreate, ExpenseClaimUpdate, ExpenseClaimResponse, ExpenseClaimDraft,
    ExpenseItemCreate, ExpenseItemUpdate, ExpenseItemResponse,
    SoftwareLicenseCreate, SoftwareLicenseUpdate, SoftwareLicenseResponse,
    DocumentUpload, DocumentResponse, ApprovalRequest, ApprovalResponse,
    ReimbursementCreate, ReimbursementResponse, DepartmentBudgetCreate,
    DepartmentBudgetUpdate, DepartmentBudgetResponse, ExpenseFilter,
    SoftwareLicenseFilter, ExpenseStatistics, DepartmentExpenseStats,
    CategoryExpenseStats, MonthlyExpenseReport, AuditLogResponse,
    ExpenseClaimSummary, ExpenseItemSummary, SoftwareLicenseSummary
)

router = APIRouter(
    prefix="/api/expense",
    tags=["Expense Management"]
)

# Helper function to generate unique claim number
def generate_claim_number():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"EXP-{timestamp}-{str(uuid.uuid4())[:8].upper()}"

# Helper function to update claim total amount
def update_claim_totals(db: Session, claim_id: int):
    """Update total and approved amounts for a claim based on its items"""
    items = db.query(ExpenseItem).filter(ExpenseItem.claim_id == claim_id).all()
    
    total_amount = sum(float(item.amount) for item in items)
    approved_amount = sum(float(item.approved_amount) for item in items)
    
    claim = db.query(ExpenseClaim).filter(ExpenseClaim.id == claim_id).first()
    if claim:
        claim.total_amount = total_amount
        claim.approved_amount = approved_amount
        db.commit()

# Health Check
@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with DB test"""
    try:
        from sqlalchemy import text
        
        # Try to execute a simple query using text()
        db.execute(text("SELECT 1"))
        
        # Try to check if expense_categories table exists and get count
        try:
            category_count = db.query(ExpenseCategory).count()
            table_status = f"expense_categories table exists and has {category_count} entries"
        except Exception as table_error:
            import traceback
            table_status = f"Error accessing expense_categories table: {str(table_error)}\n{traceback.format_exc()}"
        
        return {
            "status": "ok",
            "message": "Expense Management API is healthy",
            "database": "connected",
            "table_status": table_status
        }
    except Exception as e:
        import traceback
        return {
            "status": "error",
            "message": f"Database connection error: {str(e)}\n{traceback.format_exc()}",
            "database": "disconnected"
        }

# ==================== EXPENSE CATEGORY ENDPOINTS ====================
@router.get("/categories", response_model=List[ExpenseCategoryResponse])
async def get_categories(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all expense categories"""
    try:
        # Query categories from database
        query = db.query(ExpenseCategory)
        if is_active is not None:
            query = query.filter(ExpenseCategory.is_active == is_active)
            
        categories = query.all()
        
        # Convert to response format
        return [
            ExpenseCategoryResponse(
                id=category.id,
                category_name=category.category_name,
                description=category.description,
                is_active=category.is_active,
                created_at=category.created_at,
                updated_at=category.updated_at
            ) for category in categories
        ]
    except Exception as e:
        import traceback
        print(f"Error in get_categories: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving categories: {str(e)}"
        )

@router.post("/categories", response_model=ExpenseCategoryResponse)
async def create_category(category: ExpenseCategoryCreate, db: Session = Depends(get_db)):
    """Create a new expense category"""
    try:
        # Check if category name already exists
        existing = db.query(ExpenseCategory).filter(
            ExpenseCategory.category_name == category.category_name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Category name already exists")
        
        db_category = ExpenseCategory(**category.dict())
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        
        return db_category.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating category: {str(e)}")

@router.get("/categories", response_model=List[ExpenseCategoryResponse])
async def get_categories(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all expense categories"""
    try:
        query = db.query(ExpenseCategory)
        if is_active is not None:
            query = query.filter(ExpenseCategory.is_active == is_active)
        
        categories = query.all()
        return [cat.to_dict() for cat in categories]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving categories: {str(e)}")

@router.put("/categories/{category_id}", response_model=ExpenseCategoryResponse)
async def update_category(
    category_id: int,
    category_update: ExpenseCategoryUpdate,
    db: Session = Depends(get_db)
):
    """Update expense category"""
    try:
        category = db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        for field, value in category_update.dict(exclude_unset=True).items():
            setattr(category, field, value)
        
        db.commit()
        db.refresh(category)
        return category.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating category: {str(e)}")

# ==================== SOFTWARE ASSET ENDPOINTS ====================
@router.post("/software-assets", response_model=SoftwareAssetResponse)
async def create_software_asset(asset: SoftwareAssetCreate, db: Session = Depends(get_db)):
    """Create a new software asset"""
    try:
        db_asset = SoftwareAsset(**asset.dict())
        db.add(db_asset)
        db.commit()
        db.refresh(db_asset)
        
        return db_asset.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating software asset: {str(e)}")

@router.get("/software-assets", response_model=List[SoftwareAssetResponse])
async def get_software_assets(
    is_active: Optional[bool] = None,
    vendor_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all software assets"""
    try:
        query = db.query(SoftwareAsset)
        
        if is_active is not None:
            query = query.filter(SoftwareAsset.is_active == is_active)
        if vendor_name:
            query = query.filter(SoftwareAsset.vendor_name.ilike(f"%{vendor_name}%"))
        
        assets = query.all()
        return [asset.to_dict() for asset in assets]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving software assets: {str(e)}")

# ==================== EXPENSE CLAIM ENDPOINTS ====================
@router.post("/claims", response_model=ExpenseClaimResponse)
async def create_expense_claim(claim: ExpenseClaimCreate, db: Session = Depends(get_db)):
    """Create a new expense claim"""
    try:
        # Get user_id from either user_id or employee_id field
        user_id = claim.user_id if claim.user_id else claim.employee_id
        
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate unique claim number
        claim_number = generate_claim_number()
        
        # Create claim data with user_id properly set
        claim_data = claim.dict(exclude={'user_id'})  # Exclude user_id since we use employee_id
        claim_data['employee_id'] = user_id  # Ensure employee_id is set from user_id
        
        db_claim = ExpenseClaim(
            claim_number=claim_number,
            **claim_data
        )
        db.add(db_claim)
        db.commit()
        db.refresh(db_claim)
        
        return db_claim.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating expense claim: {str(e)}")

@router.get("/claims/pending-approval", response_model=List[ExpenseClaimSummary])
async def get_pending_approvals(
    db: Session = Depends(get_db)
):
    """Get claims pending approval"""
    try:
        query = db.query(ExpenseClaim).options(joinedload(ExpenseClaim.user)).filter(
            ExpenseClaim.status == "pending"
        )
        
        claims = query.order_by(ExpenseClaim.submission_date).all()
        
        return [
            ExpenseClaimSummary(
                id=claim.id,
                claim_number=claim.claim_number,
                employee_name=claim.user.username,
                title=claim.title,
                total_amount=float(claim.total_amount),
                approved_amount=float(claim.approved_amount),
                status=claim.status,
                claim_date=claim.claim_date.isoformat(),
                submission_date=claim.submission_date.isoformat() if claim.submission_date else None,
                created_at=claim.created_at.isoformat() if claim.created_at else None
            ) for claim in claims
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving pending approvals: {str(e)}")

@router.get("/claims", response_model=List[ExpenseClaimSummary])
async def get_expense_claims(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get expense claims with filters"""
    try:
        query = db.query(ExpenseClaim).options(joinedload(ExpenseClaim.user))
        
        if status:
            query = query.filter(ExpenseClaim.status == status)
        if user_id:
            query = query.filter(ExpenseClaim.employee_id == user_id)
        if start_date:
            query = query.filter(ExpenseClaim.claim_date >= start_date)
        if end_date:
            query = query.filter(ExpenseClaim.claim_date <= end_date)
        
        claims = query.order_by(desc(ExpenseClaim.created_at)).offset(skip).limit(limit).all()
        
        return [
            ExpenseClaimSummary(
                id=claim.id,
                claim_number=claim.claim_number,
                employee_name=claim.user.username,
                title=claim.title,
                total_amount=float(claim.total_amount),
                approved_amount=float(claim.approved_amount),
                status=claim.status,
                claim_date=claim.claim_date.isoformat(),
                submission_date=claim.submission_date.isoformat() if claim.submission_date else None,
                created_at=claim.created_at.isoformat() if claim.created_at else None
            ) for claim in claims
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving claims: {str(e)}")

@router.get("/claims/{claim_id}", response_model=ExpenseClaimResponse)
async def get_expense_claim(claim_id: int, db: Session = Depends(get_db)):
    """Get expense claim by ID with full details"""
    try:
        claim = db.query(ExpenseClaim).options(
            joinedload(ExpenseClaim.user),
            joinedload(ExpenseClaim.approver),
            joinedload(ExpenseClaim.expense_items)
        ).filter(ExpenseClaim.id == claim_id).first()
        
        if not claim:
            raise HTTPException(status_code=404, detail="Expense claim not found")
        
        return claim.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving claim: {str(e)}")

@router.put("/claims/{claim_id}", response_model=ExpenseClaimResponse)
async def update_expense_claim(
    claim_id: int,
    claim_update: ExpenseClaimUpdate,
    db: Session = Depends(get_db)
):
    """Update expense claim"""
    try:
        claim = db.query(ExpenseClaim).filter(ExpenseClaim.id == claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Expense claim not found")
        
        for field, value in claim_update.dict(exclude_unset=True).items():
            setattr(claim, field, value)
        
        db.commit()
        db.refresh(claim)
        return claim.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating claim: {str(e)}")

@router.delete("/claims/{claim_id}")
async def delete_expense_claim(claim_id: int, db: Session = Depends(get_db)):
    """Delete expense claim"""
    try:
        claim = db.query(ExpenseClaim).filter(ExpenseClaim.id == claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Expense claim not found")
        
        db.delete(claim)
        db.commit()
        return {"message": "Expense claim deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting claim: {str(e)}")

# ==================== EXPENSE ITEM ENDPOINTS ====================
@router.post("/items", response_model=ExpenseItemResponse)
async def create_expense_item(item: ExpenseItemCreate, db: Session = Depends(get_db)):
    """Create a new expense item"""
    try:
        # Verify claim exists
        claim = db.query(ExpenseClaim).filter(ExpenseClaim.id == item.claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Expense claim not found")
        
        # Verify category exists
        category = db.query(ExpenseCategory).filter(ExpenseCategory.id == item.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Expense category not found")
        
        db_item = ExpenseItem(**item.dict())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        
        # Update claim totals
        update_claim_totals(db, item.claim_id)
        
        return db_item.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating expense item: {str(e)}")

@router.get("/items", response_model=List[ExpenseItemResponse])
async def get_expense_items(
    skip: int = 0,
    limit: int = 100,
    claim_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get expense items with filters"""
    try:
        query = db.query(ExpenseItem).options(
            joinedload(ExpenseItem.category),
            joinedload(ExpenseItem.software_asset)
        )
        
        if claim_id:
            query = query.filter(ExpenseItem.claim_id == claim_id)
        if category_id:
            query = query.filter(ExpenseItem.category_id == category_id)
        if status:
            query = query.filter(ExpenseItem.status == status)
        if start_date:
            query = query.filter(ExpenseItem.expense_date >= start_date)
        if end_date:
            query = query.filter(ExpenseItem.expense_date <= end_date)
        
        items = query.order_by(desc(ExpenseItem.expense_date)).offset(skip).limit(limit).all()
        return [item.to_dict() for item in items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving expense items: {str(e)}")

@router.get("/items/{item_id}", response_model=ExpenseItemResponse)
async def get_expense_item(item_id: int, db: Session = Depends(get_db)):
    """Get expense item by ID"""
    try:
        item = db.query(ExpenseItem).options(
            joinedload(ExpenseItem.category),
            joinedload(ExpenseItem.software_asset),
            joinedload(ExpenseItem.claim)
        ).filter(ExpenseItem.id == item_id).first()
        
        if not item:
            raise HTTPException(status_code=404, detail="Expense item not found")
        
        return item.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving expense item: {str(e)}")

@router.put("/items/{item_id}", response_model=ExpenseItemResponse)
async def update_expense_item(
    item_id: int,
    item_update: ExpenseItemUpdate,
    db: Session = Depends(get_db)
):
    """Update expense item"""
    try:
        item = db.query(ExpenseItem).filter(ExpenseItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Expense item not found")
        
        for field, value in item_update.dict(exclude_unset=True).items():
            setattr(item, field, value)
        
        db.commit()
        db.refresh(item)
        
        # Update claim totals
        update_claim_totals(db, item.claim_id)
        
        return item.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating expense item: {str(e)}")

@router.delete("/items/{item_id}")
async def delete_expense_item(item_id: int, db: Session = Depends(get_db)):
    """Delete expense item"""
    try:
        item = db.query(ExpenseItem).filter(ExpenseItem.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Expense item not found")
        
        claim_id = item.claim_id
        db.delete(item)
        db.commit()
        
        # Update claim totals
        update_claim_totals(db, claim_id)
        
        return {"message": "Expense item deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting expense item: {str(e)}")

# ==================== SOFTWARE LICENSE ENDPOINTS ====================
@router.post("/software-licenses", response_model=SoftwareLicenseResponse)
async def create_software_license(license: SoftwareLicenseCreate, db: Session = Depends(get_db)):
    """Create a new software license"""
    try:
        # Verify user and software asset exist
        user = db.query(User).filter(User.id == license.employee_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        software_asset = db.query(SoftwareAsset).filter(SoftwareAsset.id == license.software_asset_id).first()
        if not software_asset:
            raise HTTPException(status_code=404, detail="Software asset not found")
        
        db_license = SoftwareLicense(**license.dict())
        db.add(db_license)
        db.commit()
        db.refresh(db_license)
        
        return db_license.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating software license: {str(e)}")

@router.get("/software-licenses", response_model=List[SoftwareLicenseSummary])
async def get_software_licenses(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    software_asset_id: Optional[int] = None,
    status: Optional[str] = None,
    expiring_in_days: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get software licenses with filters"""
    try:
        query = db.query(SoftwareLicense).options(
            joinedload(SoftwareLicense.user),
            joinedload(SoftwareLicense.software_asset)
        )
        
        if user_id:
            query = query.filter(SoftwareLicense.employee_id == user_id)
        if software_asset_id:
            query = query.filter(SoftwareLicense.software_asset_id == software_asset_id)
        if status:
            query = query.filter(SoftwareLicense.status == status)
        if expiring_in_days:
            expiry_date = date.today() + timedelta(days=expiring_in_days)
            query = query.filter(
                SoftwareLicense.expiry_date.isnot(None),
                SoftwareLicense.expiry_date <= expiry_date,
                SoftwareLicense.status == 'active'
            )
        
        licenses = query.order_by(SoftwareLicense.expiry_date).offset(skip).limit(limit).all()
        
        result = []
        for license in licenses:
            days_to_expiry = None
            if license.expiry_date:
                days_to_expiry = (license.expiry_date - date.today()).days
            
            result.append(SoftwareLicenseSummary(
                id=license.id,
                employee_name=license.user.username,
                software_name=license.software_asset.software_name,
                vendor_name=license.software_asset.vendor_name,
                purchase_date=license.purchase_date.isoformat(),
                expiry_date=license.expiry_date.isoformat() if license.expiry_date else None,
                cost=float(license.cost),
                status=license.status,
                days_to_expiry=days_to_expiry
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving software licenses: {str(e)}")

@router.get("/software-licenses/expiring")
async def get_expiring_licenses(
    days: int = Query(30, description="Number of days to check for expiring licenses"),
    db: Session = Depends(get_db)
):
    """Get software licenses expiring within specified days"""
    try:
        expiry_date = date.today() + timedelta(days=days)
        
        licenses = db.query(SoftwareLicense).options(
            joinedload(SoftwareLicense.user),
            joinedload(SoftwareLicense.software_asset)
        ).filter(
            SoftwareLicense.expiry_date.isnot(None),
            SoftwareLicense.expiry_date <= expiry_date,
            SoftwareLicense.expiry_date >= date.today(),
            SoftwareLicense.status == 'active'
        ).order_by(SoftwareLicense.expiry_date).all()
        
        result = []
        for license in licenses:
            days_to_expiry = (license.expiry_date - date.today()).days
            result.append({
                "id": license.id,
                "employee_name": license.user.username,
                "employee_email": license.user.email,
                "software_name": license.software_asset.software_name,
                "vendor_name": license.software_asset.vendor_name,
                "expiry_date": license.expiry_date.isoformat(),
                "days_to_expiry": days_to_expiry,
                "cost": float(license.cost),
                "is_recurring": license.is_recurring,
                "auto_renewal": license.auto_renewal
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving expiring licenses: {str(e)}")

# ==================== APPROVAL ENDPOINTS ====================
@router.post("/claims/{claim_id}/approve")
async def process_claim_approval(
    claim_id: int,
    approval_data: ApprovalRequest,
    approver_id: int = Query(..., description="ID of the approver"),
    db: Session = Depends(get_db)
):
    """Approve or reject an expense claim"""
    try:
        claim = db.query(ExpenseClaim).filter(
            ExpenseClaim.id == claim_id,
            ExpenseClaim.status == "pending"
        ).first()
        
        if not claim:
            raise HTTPException(status_code=404, detail="Expense claim not found or not pending approval")
        
        # Verify approver exists
        approver = db.query(User).filter(User.id == approver_id).first()
        if not approver:
            raise HTTPException(status_code=404, detail="Approver not found")
        
        # Update claim status
        if approval_data.action == "approve":
            claim.status = "approved"
            claim.approved_amount = approval_data.approved_amount or claim.total_amount
        else:
            claim.status = "rejected"
            claim.rejection_reason = approval_data.comments
        
        claim.approver_id = approver_id
        claim.approval_date = datetime.utcnow()
        
        # Create approval record
        approval = ExpenseApproval(
            claim_id=claim_id,
            approver_id=approver_id,
            status="approved" if approval_data.action == "approve" else "rejected",
            approved_amount=approval_data.approved_amount or 0,
            comments=approval_data.comments,
            approval_date=datetime.utcnow()
        )
        db.add(approval)
        
        db.commit()
        db.refresh(claim)
        
        return {
            "message": f"Claim {approval_data.action}d successfully",
            "claim_id": claim_id,
            "status": claim.status,
            "approved_amount": float(claim.approved_amount),
            "approval_date": claim.approval_date.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing approval: {str(e)}")

# ==================== REIMBURSEMENT ENDPOINTS ====================
@router.post("/reimbursements", response_model=ReimbursementResponse)
async def create_reimbursement(
    reimbursement: ReimbursementCreate,
    processed_by: int = Query(..., description="ID of the processor"),
    db: Session = Depends(get_db)
):
    """Create a new reimbursement"""
    try:
        # Verify claim exists and is approved
        claim = db.query(ExpenseClaim).filter(
            ExpenseClaim.id == reimbursement.claim_id,
            ExpenseClaim.status == "approved"
        ).first()
        
        if not claim:
            raise HTTPException(status_code=404, detail="Approved claim not found")
        
        # Verify processor exists
        processor = db.query(User).filter(User.id == processed_by).first()
        if not processor:
            raise HTTPException(status_code=404, detail="Processor not found")
        
        db_reimbursement = ExpenseReimbursement(
            **reimbursement.dict(),
            processed_by=processed_by
        )
        db.add(db_reimbursement)
        
        # Update claim status to reimbursed
        claim.status = "reimbursed"
        claim.reimbursement_date = datetime.utcnow()
        if reimbursement.transaction_id:
            claim.reimbursement_reference = reimbursement.transaction_id
        
        db.commit()
        db.refresh(db_reimbursement)
        
        return db_reimbursement.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating reimbursement: {str(e)}")

@router.get("/reimbursements", response_model=List[ReimbursementResponse])
async def get_reimbursements(
    skip: int = 0,
    limit: int = 100,
    claim_id: Optional[int] = None,
    processed_by: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get reimbursements with filters"""
    try:
        query = db.query(ExpenseReimbursement).options(joinedload(ExpenseReimbursement.processor))
        
        if claim_id:
            query = query.filter(ExpenseReimbursement.claim_id == claim_id)
        if processed_by:
            query = query.filter(ExpenseReimbursement.processed_by == processed_by)
        if start_date:
            query = query.filter(ExpenseReimbursement.reimbursement_date >= start_date)
        if end_date:
            query = query.filter(ExpenseReimbursement.reimbursement_date <= end_date)
        
        reimbursements = query.order_by(desc(ExpenseReimbursement.reimbursement_date)).offset(skip).limit(limit).all()
        return [reimb.to_dict() for reimb in reimbursements]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving reimbursements: {str(e)}")

# ==================== BUDGET ENDPOINTS ====================
@router.post("/budgets", response_model=DepartmentBudgetResponse)
async def create_department_budget(budget: DepartmentBudgetCreate, db: Session = Depends(get_db)):
    """Create department budget"""
    try:
        # Check if budget already exists for this combination
        existing = db.query(DepartmentBudget).filter(
            DepartmentBudget.department_name == budget.department_name,
            DepartmentBudget.category_id == budget.category_id,
            DepartmentBudget.fiscal_year == budget.fiscal_year,
            DepartmentBudget.quarter == budget.quarter
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Budget already exists for this combination")
        
        db_budget = DepartmentBudget(**budget.dict())
        db.add(db_budget)
        db.commit()
        db.refresh(db_budget)
        
        return db_budget.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating budget: {str(e)}")

@router.get("/budgets", response_model=List[DepartmentBudgetResponse])
async def get_department_budgets(
    department: Optional[str] = None,
    fiscal_year: Optional[int] = None,
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get department budgets with filters"""
    try:
        query = db.query(DepartmentBudget).options(joinedload(DepartmentBudget.category))
        
        if department:
            query = query.filter(DepartmentBudget.department_name == department)
        if fiscal_year:
            query = query.filter(DepartmentBudget.fiscal_year == fiscal_year)
        if category_id:
            query = query.filter(DepartmentBudget.category_id == category_id)
        
        budgets = query.all()
        return [budget.to_dict() for budget in budgets]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving budgets: {str(e)}")

# ==================== STATISTICS ENDPOINTS ====================
@router.get("/statistics", response_model=ExpenseStatistics)
async def get_expense_statistics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get expense statistics"""
    try:
        query = db.query(ExpenseClaim)
        
        if start_date:
            query = query.filter(ExpenseClaim.claim_date >= start_date)
        if end_date:
            query = query.filter(ExpenseClaim.claim_date <= end_date)
        
        claims = query.all()
        
        total_claims = len(claims)
        total_amount = sum(float(claim.total_amount) for claim in claims)
        approved_amount = sum(float(claim.approved_amount) for claim in claims if claim.status == "approved")
        pending_claims = len([c for c in claims if c.status == "pending"])
        approved_claims = len([c for c in claims if c.status == "approved"])
        rejected_claims = len([c for c in claims if c.status == "rejected"])
        average_claim_amount = total_amount / total_claims if total_claims > 0 else 0
        
        return ExpenseStatistics(
            total_claims=total_claims,
            total_amount=total_amount,
            approved_amount=approved_amount,
            pending_claims=pending_claims,
            approved_claims=approved_claims,
            rejected_claims=rejected_claims,
            average_claim_amount=average_claim_amount
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")

@router.get("/statistics/category", response_model=List[CategoryExpenseStats])
async def get_category_statistics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get expense statistics by category"""
    try:
        query = db.query(
            ExpenseCategory.category_name,
            func.sum(ExpenseItem.amount).label('total_amount'),
            func.sum(ExpenseItem.approved_amount).label('approved_amount'),
            func.count(ExpenseItem.id).label('item_count')
        ).join(ExpenseItem).join(ExpenseClaim)
        
        if start_date:
            query = query.filter(ExpenseItem.expense_date >= start_date)
        if end_date:
            query = query.filter(ExpenseItem.expense_date <= end_date)
        
        query = query.group_by(ExpenseCategory.category_name)
        results = query.all()
        
        return [
            CategoryExpenseStats(
                category_name=result.category_name,
                total_amount=float(result.total_amount or 0),
                approved_amount=float(result.approved_amount or 0),
                item_count=result.item_count
            ) for result in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving category statistics: {str(e)}")

# ==================== REPORT ENDPOINTS ====================
@router.get("/reports/monthly", response_model=List[MonthlyExpenseReport])
async def get_monthly_expense_report(
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get monthly expense report"""
    try:
        query = db.query(
            extract('year', ExpenseClaim.claim_date).label('year'),
            extract('month', ExpenseClaim.claim_date).label('month'),
            ExpenseCategory.category_name,
            func.count(ExpenseItem.id).label('total_items'),
            func.sum(ExpenseItem.amount).label('total_amount'),
            func.sum(ExpenseItem.approved_amount).label('total_approved_amount')
        ).join(ExpenseItem).join(ExpenseCategory).filter(
            ExpenseClaim.status.in_(['approved', 'reimbursed'])
        )
        
        if year:
            query = query.filter(extract('year', ExpenseClaim.claim_date) == year)
        
        query = query.group_by(
            extract('year', ExpenseClaim.claim_date),
            extract('month', ExpenseClaim.claim_date),
            ExpenseCategory.category_name
        ).order_by('year', 'month', ExpenseCategory.category_name)
        
        results = query.all()
        
        return [
            MonthlyExpenseReport(
                year=int(result.year),
                month=int(result.month),
                category_name=result.category_name,
                total_items=result.total_items,
                total_amount=float(result.total_amount or 0),
                total_approved_amount=float(result.total_approved_amount or 0)
            ) for result in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating monthly report: {str(e)}")

@router.get("/reports/employee/{user_id}")
async def get_user_expense_report(
    user_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get detailed expense report for a user"""
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        query = db.query(ExpenseClaim).options(
            joinedload(ExpenseClaim.expense_items).joinedload(ExpenseItem.category)
        ).filter(ExpenseClaim.employee_id == user_id)
        
        if start_date:
            query = query.filter(ExpenseClaim.claim_date >= start_date)
        if end_date:
            query = query.filter(ExpenseClaim.claim_date <= end_date)
        
        claims = query.order_by(desc(ExpenseClaim.claim_date)).all()
        
        # Calculate summary
        total_claims = len(claims)
        total_amount = sum(float(claim.total_amount) for claim in claims)
        approved_amount = sum(float(claim.approved_amount) for claim in claims)
        
        return {
            "user": user.to_dict(),
            "summary": {
                "total_claims": total_claims,
                "total_amount": total_amount,
                "approved_amount": approved_amount,
                "pending_amount": sum(float(c.total_amount) for c in claims if c.status == "pending")
            },
            "claims": [claim.to_dict() for claim in claims]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating user report: {str(e)}")

# ==================== DRAFT ENDPOINTS ====================
@router.post("/claims/save-draft")
async def save_expense_claim_draft(
    draft_data: ExpenseClaimDraft,
    user_email: str = Query(..., description="Email of the user saving the draft"),
    db: Session = Depends(get_db)
):
    """Save expense claim as draft"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found with this email")
        
        # Check if draft already exists for this user
        existing_draft = db.query(ExpenseClaim).filter(
            ExpenseClaim.employee_id == user.id,
            ExpenseClaim.status == "draft"
        ).first()
        
        if existing_draft:
            # Update existing draft
            for field, value in draft_data.dict(exclude_unset=True).items():
                if value is not None:
                    setattr(existing_draft, field, value)
            
            existing_draft.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_draft)
            
            return {
                "message": "Draft updated successfully",
                "draft_id": existing_draft.id,
                "claim_number": existing_draft.claim_number,
                "status": "draft"
            }
        else:
            # Create new draft
            claim_number = generate_claim_number()
            
            db_draft = ExpenseClaim(
                claim_number=claim_number,
                employee_id=user.id,
                title=draft_data.title or "Draft Claim",
                description=draft_data.description,
                claim_date=draft_data.claim_date or date.today(),
                currency=draft_data.currency or "INR",
                status="draft"
            )
            db.add(db_draft)
            db.commit()
            db.refresh(db_draft)
            
            return {
                "message": "Draft saved successfully",
                "draft_id": db_draft.id,
                "claim_number": db_draft.claim_number,
                "status": "draft"
            }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving draft: {str(e)}")

@router.get("/claims/drafts")
async def get_expense_claim_drafts(
    user_email: str = Query(..., description="Email of the user"),
    db: Session = Depends(get_db)
):
    """Get all drafts for a user"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found with this email")
        
        drafts = db.query(ExpenseClaim).filter(
            ExpenseClaim.employee_id == user.id,
            ExpenseClaim.status == "draft"
        ).order_by(desc(ExpenseClaim.updated_at)).all()
        
        return [
            {
                "id": draft.id,
                "claim_number": draft.claim_number,
                "title": draft.title,
                "description": draft.description,
                "claim_date": draft.claim_date.isoformat() if draft.claim_date else None,
                "total_amount": float(draft.total_amount),
                "currency": draft.currency,
                "created_at": draft.created_at.isoformat() if draft.created_at else None,
                "updated_at": draft.updated_at.isoformat() if draft.updated_at else None
            } for draft in drafts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving drafts: {str(e)}")

@router.put("/claims/{claim_id}/submit-draft")
async def submit_draft_claim(claim_id: int, db: Session = Depends(get_db)):
    """Submit a draft claim"""
    try:
        claim = db.query(ExpenseClaim).filter(
            ExpenseClaim.id == claim_id,
            ExpenseClaim.status == "draft"
        ).first()
        
        if not claim:
            raise HTTPException(status_code=404, detail="Draft claim not found")
        
        # Validate that claim has at least one expense item
        items_count = db.query(ExpenseItem).filter(ExpenseItem.claim_id == claim_id).count()
        if items_count == 0:
            raise HTTPException(status_code=400, detail="Cannot submit claim without expense items")
        
        # Update status to pending
        claim.status = "pending"
        claim.submission_date = datetime.utcnow()
        
        db.commit()
        db.refresh(claim)
        
        return {
            "message": "Draft submitted successfully",
            "claim_id": claim.id,
            "claim_number": claim.claim_number,
            "status": claim.status,
            "submission_date": claim.submission_date.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting draft: {str(e)}")

@router.delete("/claims/drafts/{draft_id}")
async def delete_draft_claim(draft_id: int, db: Session = Depends(get_db)):
    """Delete a draft claim"""
    try:
        draft = db.query(ExpenseClaim).filter(
            ExpenseClaim.id == draft_id,
            ExpenseClaim.status == "draft"
        ).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        db.delete(draft)
        db.commit()
        return {"message": "Draft deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting draft: {str(e)}")

# ==================== DOCUMENT UPLOAD ENDPOINTS ====================
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    expense_item_id: Optional[int] = None,
    claim_id: Optional[int] = None,
    software_license_id: Optional[int] = None,
    document_type: str = "receipt",
    description: Optional[str] = None,
    is_primary: bool = False,
    uploaded_by: int = Query(..., description="ID of the uploader"),
    db: Session = Depends(get_db)
):
    """Upload document for expense item, claim, or software license"""
    try:
        # Verify uploader exists
        uploader = db.query(User).filter(User.id == uploaded_by).first()
        if not uploader:
            raise HTTPException(status_code=404, detail="Uploader not found")
        
        # Verify at least one parent entity is provided
        if not any([expense_item_id, claim_id, software_license_id]):
            raise HTTPException(status_code=400, detail="Must specify expense_item_id, claim_id, or software_license_id")
        
        # Create upload directory if it doesn't exist
        upload_dir = Path("uploads/expense_documents")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = Path(file.filename).suffix
        stored_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_dir / stored_filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create database record
        document = ExpenseDocument(
            expense_item_id=expense_item_id,
            claim_id=claim_id,
            software_license_id=software_license_id,
            document_type=document_type,
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            file_size_bytes=len(content),
            mime_type=file.content_type,
            uploaded_by=uploaded_by,
            description=description,
            is_primary=is_primary
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        return {
            "message": "Document uploaded successfully",
            "document_id": document.id,
            "filename": document.original_filename,
            "file_size": document.file_size_bytes
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(
    expense_item_id: Optional[int] = None,
    claim_id: Optional[int] = None,
    software_license_id: Optional[int] = None,
    document_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get documents with filters"""
    try:
        query = db.query(ExpenseDocument)
        
        if expense_item_id:
            query = query.filter(ExpenseDocument.expense_item_id == expense_item_id)
        if claim_id:
            query = query.filter(ExpenseDocument.claim_id == claim_id)
        if software_license_id:
            query = query.filter(ExpenseDocument.software_license_id == software_license_id)
        if document_type:
            query = query.filter(ExpenseDocument.document_type == document_type)
        
        documents = query.order_by(desc(ExpenseDocument.upload_date)).all()
        return [doc.to_dict() for doc in documents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")

# ==================== AUDIT LOG ENDPOINTS ====================
@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    table_name: Optional[str] = None,
    record_id: Optional[int] = None,
    action: Optional[str] = None,
    changed_by: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Get audit logs with filters"""
    try:
        query = db.query(ExpenseAuditLog).options(joinedload(ExpenseAuditLog.changer))
        
        if table_name:
            query = query.filter(ExpenseAuditLog.table_name == table_name)
        if record_id:
            query = query.filter(ExpenseAuditLog.record_id == record_id)
        if action:
            query = query.filter(ExpenseAuditLog.action == action)
        if changed_by:
            query = query.filter(ExpenseAuditLog.changed_by == changed_by)
        if start_date:
            query = query.filter(ExpenseAuditLog.created_at >= start_date)
        if end_date:
            query = query.filter(ExpenseAuditLog.created_at <= end_date)
        
        logs = query.order_by(desc(ExpenseAuditLog.created_at)).offset(skip).limit(limit).all()
        return [log.to_dict() for log in logs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")

# ==================== DASHBOARD ENDPOINTS ====================
@router.get("/dashboard/overview")
async def get_dashboard_overview(
    user_email: str = Query(..., description="Email of the user"),
    db: Session = Depends(get_db)
):
    """Get dashboard overview for user"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found with this email")
        
        # Get user's claims statistics
        user_claims = db.query(ExpenseClaim).filter(ExpenseClaim.employee_id == user.id).all()
        
        # Get pending claims count (for managers/approvers)
        pending_approvals = 0
        if user.role and 'manager' in user.role.lower():
            pending_approvals = db.query(ExpenseClaim).filter(
                ExpenseClaim.status == "pending"
            ).count()
        
        # Get software licenses expiring soon
        expiring_licenses = db.query(SoftwareLicense).filter(
            SoftwareLicense.employee_id == user.id,
            SoftwareLicense.status == "active",
            SoftwareLicense.expiry_date.isnot(None),
            SoftwareLicense.expiry_date <= date.today() + timedelta(days=30)
        ).count()
        
        # Calculate statistics
        total_claims = len(user_claims)
        total_amount = sum(float(claim.total_amount) for claim in user_claims)
        approved_amount = sum(float(claim.approved_amount) for claim in user_claims if claim.status == "approved")
        pending_claims = len([c for c in user_claims if c.status == "pending"])
        
        return {
            "user": user.to_dict(),
            "statistics": {
                "total_claims": total_claims,
                "total_amount": total_amount,
                "approved_amount": approved_amount,
                "pending_claims": pending_claims,
                "pending_approvals": pending_approvals,
                "expiring_licenses": expiring_licenses
            },
            "recent_claims": [
                {
                    "id": claim.id,
                    "claim_number": claim.claim_number,
                    "title": claim.title,
                    "total_amount": float(claim.total_amount),
                    "status": claim.status,
                    "claim_date": claim.claim_date.isoformat()
                } for claim in sorted(user_claims, key=lambda x: x.created_at, reverse=True)[:5]
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard overview: {str(e)}")

# ==================== BULK OPERATIONS ====================
@router.post("/claims/{claim_id}/items/bulk")
async def bulk_create_expense_items(
    claim_id: int,
    items: List[ExpenseItemCreate],
    db: Session = Depends(get_db)
):
    """Create multiple expense items for a claim"""
    try:
        # Verify claim exists
        claim = db.query(ExpenseClaim).filter(ExpenseClaim.id == claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Expense claim not found")
        
        created_items = []
        for item_data in items:
            # Override claim_id to ensure consistency
            item_data.claim_id = claim_id
            
            # Verify category exists
            category = db.query(ExpenseCategory).filter(ExpenseCategory.id == item_data.category_id).first()
            if not category:
                raise HTTPException(status_code=404, detail=f"Category {item_data.category_id} not found")
            
            db_item = ExpenseItem(**item_data.dict())
            db.add(db_item)
            created_items.append(db_item)
        
        db.commit()
        
        # Update claim totals
        update_claim_totals(db, claim_id)
        
        # Refresh all created items
        for item in created_items:
            db.refresh(item)
        
        return {
            "message": f"Created {len(created_items)} expense items successfully",
            "claim_id": claim_id,
            "items": [item.to_dict() for item in created_items]
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating bulk expense items: {str(e)}")

@router.put("/items/bulk-approve")
async def bulk_approve_items(
    item_ids: List[int],
    approver_id: int = Query(..., description="ID of the approver"),
    approved_amounts: Optional[List[float]] = None,
    comments: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Bulk approve expense items"""
    try:
        # Verify approver exists
        approver = db.query(User).filter(User.id == approver_id).first()
        if not approver:
            raise HTTPException(status_code=404, detail="Approver not found")
        
        items = db.query(ExpenseItem).filter(ExpenseItem.id.in_(item_ids)).all()
        
        if len(items) != len(item_ids):
            raise HTTPException(status_code=404, detail="Some expense items not found")
        
        updated_claims = set()
        
        for i, item in enumerate(items):
            item.status = "approved"
            if approved_amounts and i < len(approved_amounts):
                item.approved_amount = approved_amounts[i]
            else:
                item.approved_amount = item.amount
            
            updated_claims.add(item.claim_id)
        
        db.commit()
        
        # Update claim totals for affected claims
        for claim_id in updated_claims:
            update_claim_totals(db, claim_id)
        
        return {
            "message": f"Approved {len(items)} expense items successfully",
            "approved_items": len(items),
            "updated_claims": len(updated_claims)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error bulk approving items: {str(e)}")

# ==================== ADVANCED SEARCH ENDPOINTS ====================
@router.post("/search/advanced")
async def advanced_expense_search(
    filters: ExpenseFilter,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Advanced search for expense claims with multiple filters"""
    try:
        query = db.query(ExpenseClaim).options(
            joinedload(ExpenseClaim.user),
            joinedload(ExpenseClaim.expense_items).joinedload(ExpenseItem.category)
        )
        
        if filters.start_date:
            query = query.filter(ExpenseClaim.claim_date >= filters.start_date)
        if filters.end_date:
            query = query.filter(ExpenseClaim.claim_date <= filters.end_date)
        if filters.employee_id:
            query = query.filter(ExpenseClaim.employee_id == filters.employee_id)
        if filters.status:
            query = query.filter(ExpenseClaim.status == filters.status)
        if filters.min_amount:
            query = query.filter(ExpenseClaim.total_amount >= filters.min_amount)
        if filters.max_amount:
            query = query.filter(ExpenseClaim.total_amount <= filters.max_amount)
        if filters.category_id:
            query = query.join(ExpenseItem).filter(ExpenseItem.category_id == filters.category_id)
        
        claims = query.distinct().order_by(desc(ExpenseClaim.claim_date)).offset(skip).limit(limit).all()
        
        return {
            "total_results": len(claims),
            "claims": [claim.to_dict() for claim in claims]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing advanced search: {str(e)}")

# ==================== BUDGET TRACKING ENDPOINTS ====================
@router.get("/budgets/tracking/{department}")
async def track_department_budget(
    department: str,
    fiscal_year: int = Query(..., description="Fiscal year for budget tracking"),
    db: Session = Depends(get_db)
):
    """Track budget utilization for a department"""
    try:
        # Get budget allocations
        budgets = db.query(DepartmentBudget).options(
            joinedload(DepartmentBudget.category)
        ).filter(
            DepartmentBudget.department_name == department,
            DepartmentBudget.fiscal_year == fiscal_year
        ).all()
        
        if not budgets:
            raise HTTPException(status_code=404, detail="No budget found for this department and fiscal year")
        
        # Calculate actual spending
        spending_query = db.query(
            ExpenseCategory.id,
            ExpenseCategory.category_name,
            func.sum(ExpenseItem.approved_amount).label('spent_amount')
        ).join(ExpenseItem).join(ExpenseClaim).join(User).filter(
            ExpenseClaim.status.in_(['approved', 'reimbursed']),
            extract('year', ExpenseClaim.claim_date) == fiscal_year
        ).group_by(ExpenseCategory.id, ExpenseCategory.category_name)
        
        spending_results = spending_query.all()
        spending_dict = {result.id: float(result.spent_amount or 0) for result in spending_results}
        
        # Prepare response
        budget_tracking = []
        for budget in budgets:
            spent = spending_dict.get(budget.category_id, 0)
            budget.spent_amount = spent  # Update the model
            
            budget_tracking.append({
                "category_id": budget.category_id,
                "category_name": budget.category.category_name,
                "allocated_amount": float(budget.allocated_amount),
                "spent_amount": spent,
                "remaining_amount": float(budget.allocated_amount) - spent,
                "utilization_percentage": (spent / float(budget.allocated_amount)) * 100 if budget.allocated_amount > 0 else 0,
                "quarter": budget.quarter
            })
        
        # Update spent amounts in database
        db.commit()
        
        return {
            "department": department,
            "fiscal_year": fiscal_year,
            "budget_tracking": budget_tracking,
            "total_allocated": sum(float(b.allocated_amount) for b in budgets),
            "total_spent": sum(spending_dict.values()),
            "overall_utilization": (sum(spending_dict.values()) / sum(float(b.allocated_amount) for b in budgets)) * 100 if budgets else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error tracking budget: {str(e)}")

# ==================== USER INTEGRATION ENDPOINTS ====================
@router.get("/user-profile/{user_email}")
async def get_user_expense_profile(user_email: str, db: Session = Depends(get_db)):
    """Get user expense profile by integrating with User model"""
    try:
        # Find user first
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's expense statistics
        claims = db.query(ExpenseClaim).filter(ExpenseClaim.employee_id == user.id).all()
        
        # Get software licenses
        licenses = db.query(SoftwareLicense).options(
            joinedload(SoftwareLicense.software_asset)
        ).filter(SoftwareLicense.employee_id == user.id).all()
        
        return {
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
            "expense_summary": {
                "total_claims": len(claims),
                "total_amount": sum(float(claim.total_amount) for claim in claims),
                "approved_amount": sum(float(claim.approved_amount) for claim in claims),
                "pending_claims": len([c for c in claims if c.status == "pending"]),
                "draft_claims": len([c for c in claims if c.status == "draft"])
            },
            "software_licenses": {
                "total_licenses": len(licenses),
                "active_licenses": len([l for l in licenses if l.status == "active"]),
                "expiring_soon": len([l for l in licenses if l.expiry_date and l.expiry_date <= date.today() + timedelta(days=30)]),
                "licenses": [license.to_dict() for license in licenses[:10]]  # Latest 10
            },
            "recent_claims": [claim.to_dict() for claim in sorted(claims, key=lambda x: x.created_at, reverse=True)[:5]]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user profile: {str(e)}")