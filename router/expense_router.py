from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, date, timedelta
import os
import uuid
from decimal import Decimal

from db.database import get_db
from model.expense_model import (
    ExpenseCategory, ExpenseClaim, ExpenseItem, ExpenseDocument,
    ExpenseApproval, ExpenseReimbursement, SoftwareLicense, AuditLog
)

from model.usermodels import User
from Schema.expense_schema import (
    ExpenseCategoryCreate, ExpenseCategoryResponse, ExpenseCategoryUpdate,
    ExpenseClaimCreate, ExpenseClaimResponse, ExpenseItemResponse, BulkExpenseItemCreate, ExpenseReimbursementResponse,
    SoftwareLicenseCreate, SoftwareLicenseResponse, SoftwareLicenseUpdate,
    UserProfile, AuditLogResponse,
    DocumentUploadResponse, BulkApprovalRequest
)

router = APIRouter(
    prefix="/api/expense",
)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = "uploads/expense_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Utility function for creating audit logs
def create_audit_log(db: Session, action: str, user_id: int, user_name: str, 
                    entity_type: str, entity_id: int, details: str):
    audit_log = AuditLog(
        action=action,
        user_id=user_id,
        user_name=user_name,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        timestamp=datetime.utcnow()
    )
    db.add(audit_log)

# Health Check
@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "Expense management service is healthy"}

# Categories Management
@router.get("/categories", response_model=List[ExpenseCategoryResponse])
async def get_categories(
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get all expense categories"""
    try:
        query = db.query(ExpenseCategory)
        if active_only:
            query = query.filter(ExpenseCategory.is_active == True)
        
        categories = query.order_by(ExpenseCategory.category_name).all()
        return categories
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving categories: {str(e)}"
        )

@router.post("/categories", response_model=ExpenseCategoryResponse)
async def create_category(
    category_data: ExpenseCategoryCreate,
    db: Session = Depends(get_db)
):
    """Create a new expense category"""
    try:
        existing = db.query(ExpenseCategory).filter(
            ExpenseCategory.category_name == category_data.category_name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Category already exists")
        
        db_category = ExpenseCategory(**category_data.model_dump())
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        
        return db_category
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating category: {str(e)}")

@router.put("/categories/{category_id}", response_model=ExpenseCategoryResponse)
async def update_category(
    category_id: int,
    category_data: ExpenseCategoryUpdate,
    db: Session = Depends(get_db)
):
    """Update an expense category"""
    try:
        category = db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        update_data = category_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        
        db.commit()
        db.refresh(category)
        return category
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating category: {str(e)}")

@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """Delete an expense category"""
    try:
        category = db.query(ExpenseCategory).filter(ExpenseCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Check if category is being used
        items_count = db.query(ExpenseItem).filter(ExpenseItem.category_id == category_id).count()
        if items_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete category that has expense items")
        
        db.delete(category)
        db.commit()
        return {"message": "Category deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting category: {str(e)}")

# User Profile Management
@router.get("/user-profile/{email}", response_model=UserProfile)
async def get_user_profile(email: str, db: Session = Depends(get_db)):
    """Get user profile by email"""
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserProfile(
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            department=getattr(user, 'department', None),
            manager_id=getattr(user, 'manager_id', None)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user profile: {str(e)}")

# Claims Management
@router.get("/claims", response_model=List[ExpenseClaimResponse])
async def get_expense_claims(
    submitter_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    department: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    """Get expense claims with optional filters"""
    try:
        query = db.query(ExpenseClaim).options(
            joinedload(ExpenseClaim.user),
            joinedload(ExpenseClaim.items).joinedload(ExpenseItem.category),
            joinedload(ExpenseClaim.documents)
        )
        
        # Apply filters
        if submitter_id:
            query = query.filter(ExpenseClaim.user_id == submitter_id)
        if status:
            query = query.filter(ExpenseClaim.status == status)
        if start_date:
            query = query.filter(ExpenseClaim.claim_date >= start_date)
        if end_date:
            query = query.filter(ExpenseClaim.claim_date <= end_date)
        if min_amount:
            query = query.filter(ExpenseClaim.total_amount >= min_amount)
        if max_amount:
            query = query.filter(ExpenseClaim.total_amount <= max_amount)
        if department:
            query = query.join(User).filter(User.department.ilike(f"%{department}%"))
        
        claims = query.order_by(desc(ExpenseClaim.created_at)).all()
        
        # Format response with computed fields
        result = []
        for claim in claims:
            # Manual user lookup to avoid relationship issues
            user = db.query(User).filter(User.id == claim.user_id).first()
            
            claim_dict = {
                "id": claim.id,
                "user_id": claim.user_id,
                "approver_id": claim.approver_id,
                "title": claim.title,
                "description": claim.description,
                "claim_date": claim.claim_date,
                "total_amount": claim.total_amount,
                "approved_amount": claim.approved_amount or Decimal("0.00"),
                "currency": claim.currency,
                "status": claim.status,
                "rejection_reason": claim.rejection_reason,
                "submission_date": claim.submission_date,
                "approval_date": claim.approval_date,
                "created_at": claim.created_at,
                "updated_at": claim.updated_at,
                "employee_name": user.username if user else None,
                "items_count": len(claim.items),
                "items": [
                    {
                        "id": item.id,
                        "claim_id": item.claim_id,
                        "category_id": item.category_id,
                        "category_name": item.category.category_name if item.category else None,
                        "item_description": item.item_description,
                        "expense_date": item.expense_date,
                        "amount": item.amount,
                        "approved_amount": item.approved_amount,
                        "currency": item.currency,
                        "vendor_name": item.vendor_name,
                        "payment_method": item.payment_method,
                        "receipt_number": item.receipt_number,
                        "business_purpose": item.business_purpose,
                        "is_billable": item.is_billable,
                        "client_name": item.client_name,
                        "project_code": item.project_code,
                        "created_at": item.created_at,
                        "updated_at": item.updated_at
                    }
                    for item in claim.items
                ] if claim.items else []
            }
            result.append(ExpenseClaimResponse(**claim_dict))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving claims: {str(e)}")

@router.get("/claims/{claim_id}", response_model=ExpenseClaimResponse)
async def get_expense_claim_by_id(claim_id: int, db: Session = Depends(get_db)):
    """Get a specific expense claim by ID with full details"""
    try:
        claim = db.query(ExpenseClaim).options(
            joinedload(ExpenseClaim.items).joinedload(ExpenseItem.category),
            joinedload(ExpenseClaim.documents),
            joinedload(ExpenseClaim.approvals)
        ).filter(ExpenseClaim.id == claim_id).first()
        
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Manual user lookup
        user = db.query(User).filter(User.id == claim.user_id).first()
        
        claim_dict = {
            "id": claim.id,
            "user_id": claim.user_id,
            "approver_id": claim.approver_id,
            "title": claim.title,
            "description": claim.description,
            "claim_date": claim.claim_date,
            "total_amount": claim.total_amount,
            "approved_amount": claim.approved_amount or Decimal("0.00"),
            "currency": claim.currency,
            "status": claim.status,
            "rejection_reason": claim.rejection_reason,
            "submission_date": claim.submission_date,
            "approval_date": claim.approval_date,
            "created_at": claim.created_at,
            "updated_at": claim.updated_at,
            "employee_name": user.username if user else None,
            "items_count": len(claim.items),
            "items": [{
                "id": item.id,
                "claim_id": item.claim_id,
                "category_id": item.category_id,
                "category_name": item.category.category_name if item.category else None,
                "item_description": item.item_description,
                "expense_date": item.expense_date,
                "amount": item.amount,
                "approved_amount": item.approved_amount,
                "currency": item.currency,
                "vendor_name": item.vendor_name,
                "payment_method": item.payment_method,
                "receipt_number": item.receipt_number,
                "business_purpose": item.business_purpose,
                "is_billable": item.is_billable,
                "client_name": item.client_name,
                "project_code": item.project_code,
                "created_at": item.created_at,
                "updated_at": item.updated_at
            } for item in claim.items] if claim.items else []
        }
        
        return ExpenseClaimResponse(**claim_dict)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving claim: {str(e)}")

@router.post("/claims", response_model=ExpenseClaimResponse)
async def create_expense_claim(
    claim_data: ExpenseClaimCreate,
    db: Session = Depends(get_db)
):
    """Create a new expense claim"""
    try:
        user = db.query(User).filter(User.id == claim_data.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db_claim = ExpenseClaim(**claim_data.model_dump())
        db_claim.submission_date = datetime.utcnow()
        db_claim.status = "pending"
        
        db.add(db_claim)
        db.commit()
        db.refresh(db_claim)
        
        # Create audit log
        create_audit_log(
            db, "CREATE_CLAIM", claim_data.user_id, user.username,
            "ExpenseClaim", db_claim.id, f"Created claim: {claim_data.title}"
        )
        
        claim_dict = {
            "id": db_claim.id,
            "user_id": db_claim.user_id,
            "approver_id": db_claim.approver_id,
            "title": db_claim.title,
            "description": db_claim.description,
            "claim_date": db_claim.claim_date,
            "total_amount": db_claim.total_amount,
            "approved_amount": db_claim.approved_amount or Decimal('0.00'),
            "currency": db_claim.currency,
            "status": db_claim.status,
            "rejection_reason": db_claim.rejection_reason,
            "submission_date": db_claim.submission_date,
            "approval_date": db_claim.approval_date,
            "created_at": db_claim.created_at,
            "updated_at": db_claim.updated_at,
            "employee_name": user.username,
            "items_count": 0,
            "items": []
        }
        
        return ExpenseClaimResponse(**claim_dict)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating claim: {str(e)}")

@router.put("/claims/{claim_id}/approve")
async def approve_expense_claim(
    claim_id: int,
    approval_request: dict,
    approver_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Approve or reject an expense claim"""
    try:
        claim = db.query(ExpenseClaim).filter(ExpenseClaim.id == claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        action = approval_request.get('action')
        approved_amount = approval_request.get('approved_amount')
        remarks = approval_request.get('remarks') or approval_request.get('comments')
        
        if not action:
            raise HTTPException(status_code=400, detail="Action is required")
        
        if action not in ["approve", "reject", "pending"]:
            raise HTTPException(status_code=400, detail="Invalid action. Must be 'approve', 'reject', or 'pending'")
        
        final_approver_id = approver_id or approval_request.get('approver_id')
        if not final_approver_id:
            raise HTTPException(status_code=400, detail="Approver ID is required")
        
        # Update claim based on action
        if action == "approve":
            if not approved_amount:
                approved_amount = claim.total_amount
            claim.status = "approved"
            claim.approved_amount = Decimal(str(approved_amount))
            claim.approval_date = datetime.utcnow()
        elif action == "reject":
            claim.status = "rejected"
            claim.rejection_reason = remarks
            claim.approval_date = datetime.utcnow()
        elif action == "pending":
            claim.status = "pending"
            claim.approved_amount = None
            claim.approval_date = None
        
        claim.approver_id = final_approver_id
        
        # Create approval record
        db_approval = ExpenseApproval(
            claim_id=claim_id,
            approver_id=final_approver_id,
            action=action,
            remarks=remarks,
            approved_amount=Decimal(str(approved_amount)) if action == "approve" and approved_amount else None
        )
        db.add(db_approval)
        
        # Create audit log
        approver = db.query(User).filter(User.id == final_approver_id).first()
        create_audit_log(
            db, f"CLAIM_{action.upper()}", final_approver_id,
            approver.username if approver else f"User {final_approver_id}",
            "ExpenseClaim", claim_id, f"Claim {action}d: {remarks or 'No comments'}"
        )
        
        db.commit()
        
        return {
            "message": f"Claim {action}d successfully",
            "claim_id": claim_id,
            "status": claim.status,
            "approval_id": db_approval.id,
            "approved_amount": float(claim.approved_amount) if claim.approved_amount else None
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing approval: {str(e)}")

@router.get("/claims/pending-approval", response_model=List[ExpenseClaimResponse])
async def get_pending_approvals(db: Session = Depends(get_db)):
    """Get all claims pending approval"""
    try:
        claims = db.query(ExpenseClaim).options(
            joinedload(ExpenseClaim.items)
        ).filter(ExpenseClaim.status == "pending").order_by(desc(ExpenseClaim.submission_date)).all()
        
        result = []
        for claim in claims:
            user = db.query(User).filter(User.id == claim.user_id).first()
            
            claim_dict = {
                "id": claim.id,
                "user_id": claim.user_id,
                "approver_id": claim.approver_id,
                "title": claim.title,
                "description": claim.description,
                "claim_date": claim.claim_date,
                "total_amount": claim.total_amount,
                "approved_amount": claim.approved_amount or Decimal('0.00'),
                "currency": claim.currency,
                "status": claim.status,
                "rejection_reason": claim.rejection_reason,
                "submission_date": claim.submission_date,
                "approval_date": claim.approval_date,
                "created_at": claim.created_at,
                "updated_at": claim.updated_at,
                "employee_name": user.username if user else None,
                "items_count": len(claim.items),
                "items": None
            }
            result.append(ExpenseClaimResponse(**claim_dict))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving pending approvals: {str(e)}")

# Expense Items Management
@router.get("/claims/{claim_id}/items")
async def get_expense_items_by_claim_id(
    claim_id: int,
    db: Session = Depends(get_db)
):
    """Get expense items for a specific claim with documents"""
    try:
        # Get all items for this claim
        items = db.query(ExpenseItem).options(
            joinedload(ExpenseItem.category)
        ).filter(ExpenseItem.claim_id == claim_id).all()
        
        # Get all documents for this claim in one query
        all_claim_documents = db.query(ExpenseDocument).filter(
            ExpenseDocument.claim_id == claim_id
        ).all()
        
        result = []
        for item in items:
            # Filter documents for this specific item and general claim documents
            item_documents = [
                doc for doc in all_claim_documents 
                if doc.expense_item_id == item.id or doc.expense_item_id is None
            ]
            
            item_response = ExpenseItemResponse(
                id=item.id,
                claim_id=item.claim_id,
                category_id=item.category_id,
                category_name=item.category.category_name if item.category else None,
                item_description=item.item_description,
                expense_date=item.expense_date,
                amount=item.amount,
                approved_amount=item.approved_amount,
                currency=item.currency,
                vendor_name=item.vendor_name,
                payment_method=item.payment_method,
                receipt_number=item.receipt_number,
                business_purpose=item.business_purpose,
                is_billable=item.is_billable,
                client_name=item.client_name,
                project_code=item.project_code,
                created_at=item.created_at,
                updated_at=item.updated_at
            )
            
            # Add documents info to the response
            item_dict = item_response.model_dump()
            item_dict['documents'] = [
                {
                    'id': doc.id,
                    'file_name': doc.file_name,
                    'file_path': doc.file_path,
                    'file_size': doc.file_size,
                    'mime_type': doc.mime_type,
                    'document_type': doc.document_type,
                    'uploaded_at': doc.uploaded_at,
                    'notes': doc.notes
                } for doc in item_documents
            ]
            item_dict['has_documents'] = len(item_documents) > 0
            item_dict['document_count'] = len(item_documents)
            
            result.append(item_dict)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving claim items: {str(e)}")

@router.get("/items", response_model=List[ExpenseItemResponse])
async def get_expense_items(
    claim_id: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """Get expense items with optional filters"""
    try:
        query = db.query(ExpenseItem).options(
            joinedload(ExpenseItem.category),
            joinedload(ExpenseItem.claim)
        )
        
        if claim_id:
            query = query.filter(ExpenseItem.claim_id == claim_id)
        if category_id:
            query = query.filter(ExpenseItem.category_id == category_id)
        if start_date:
            query = query.filter(ExpenseItem.expense_date >= start_date)
        if end_date:
            query = query.filter(ExpenseItem.expense_date <= end_date)
        
        items = query.order_by(desc(ExpenseItem.created_at)).all()
        
        result = []
        for item in items:
            item_dict = {
                "id": item.id,
                "claim_id": item.claim_id,
                "category_id": item.category_id,
                "category_name": item.category.category_name if item.category else None,
                "item_description": item.item_description,
                "expense_date": item.expense_date,
                "amount": item.amount,
                "approved_amount": item.approved_amount,
                "currency": item.currency,
                "vendor_name": item.vendor_name,
                "payment_method": item.payment_method,
                "receipt_number": item.receipt_number,
                "business_purpose": item.business_purpose,
                "is_billable": item.is_billable,
                "client_name": item.client_name,
                "project_code": item.project_code,
                "created_at": item.created_at,
                "updated_at": item.updated_at
            }
            result.append(item_dict)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving items: {str(e)}")

@router.post("/claims/{claim_id}/items/bulk", response_model=List[ExpenseItemResponse])
async def bulk_create_expense_items(
    claim_id: int,
    items_data: BulkExpenseItemCreate,
    db: Session = Depends(get_db)
):
    """Create multiple expense items for a claim"""
    try:
        claim = db.query(ExpenseClaim).filter(ExpenseClaim.id == claim_id).first()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        db_items = []
        total_amount = Decimal('0.00')
        
        for item_data in items_data.items:
            db_item = ExpenseItem(**item_data.model_dump(), claim_id=claim_id)
            db_items.append(db_item)
            total_amount += item_data.amount
            db.add(db_item)
        
        # Update claim total amount
        claim.total_amount = total_amount
        
        # Create audit log
        user = db.query(User).filter(User.id == claim.user_id).first()
        create_audit_log(
            db, "CREATE_ITEMS", claim.user_id,
            user.username if user else f"User {claim.user_id}",
            "ExpenseItem", claim_id,
            f"Created {len(items_data.items)} items for claim {claim_id}"
        )
        
        db.commit()
        
        # Format response
        result = []
        for item in db_items:
            db.refresh(item)
            category = db.query(ExpenseCategory).filter(ExpenseCategory.id == item.category_id).first()
            
            item_dict = {
                "id": item.id,
                "claim_id": item.claim_id,
                "category_id": item.category_id,
                "category_name": category.category_name if category else None,
                "item_description": item.item_description,
                "expense_date": item.expense_date,
                "amount": item.amount,
                "approved_amount": item.approved_amount,
                "currency": item.currency,
                "vendor_name": item.vendor_name,
                "payment_method": item.payment_method,
                "receipt_number": item.receipt_number,
                "business_purpose": item.business_purpose,
                "is_billable": item.is_billable,
                "client_name": item.client_name,
                "project_code": item.project_code,
                "created_at": item.created_at,
                "updated_at": item.updated_at
            }
            result.append(item_dict)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating items: {str(e)}")

# Document Management
@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    uploaded_by: int = Form(...),
    claim_id: Optional[int] = Form(None),
    expense_item_id: Optional[int] = Form(None),
    document_type: str = Form("receipt"),
    db: Session = Depends(get_db)
):
    """Upload a document for expense claim or item"""
    try:
        # Validate file
        allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, JPG, and PNG files are allowed.")
        
        # Check file size (5MB limit)
        max_size = 5 * 1024 * 1024  # 5MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="File size must be less than 5MB")
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Create document record
        db_document = ExpenseDocument(
            claim_id=claim_id,
            expense_item_id=expense_item_id,
            document_type=document_type,
            file_name=file.filename,
            file_path=file_path,
            file_size=len(file_content),
            mime_type=file.content_type,
            uploaded_by=uploaded_by
        )
        db.add(db_document)
        
        # Create audit log
        user = db.query(User).filter(User.id == uploaded_by).first()
        create_audit_log(
            db, "UPLOAD_DOCUMENT", uploaded_by,
            user.username if user else f"User {uploaded_by}",
            "ExpenseDocument", claim_id or expense_item_id or 0,
            f"Uploaded document: {file.filename}"
        )
        
        db.commit()
        db.refresh(db_document)
        
        return DocumentUploadResponse(
            id=db_document.id,
            file_name=db_document.file_name,
            file_path=db_document.file_path,
            file_size=db_document.file_size,
            mime_type=db_document.mime_type,
            document_type=db_document.document_type,
            claim_id=db_document.claim_id,
            expense_item_id=db_document.expense_item_id,
            uploaded_by=db_document.uploaded_by,
            uploaded_at=db_document.uploaded_at
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # Clean up file if it was created
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error uploading document: {str(e)}")

@router.get("/documents/{claim_id}/", response_model=List[DocumentUploadResponse])
async def get_documents_by_claim_id(
    claim_id: int,
    db: Session = Depends(get_db)
):
    """Get documents for a specific claim"""
    try:
        documents = db.query(ExpenseDocument).filter(
            ExpenseDocument.claim_id == claim_id
        ).all()
        
        return [DocumentUploadResponse(
            id=doc.id,
            claim_id=doc.claim_id,
            expense_item_id=doc.expense_item_id,
            file_name=doc.file_name,
            file_path=doc.file_path,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            document_type=doc.document_type,
            uploaded_by=doc.uploaded_by,
            uploaded_at=doc.uploaded_at,
            notes=doc.notes
        ) for doc in documents]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")

@router.get("/documents", response_model=List[DocumentUploadResponse])
async def get_documents(
    claim_id: Optional[int] = Query(None),
    expense_item_id: Optional[int] = Query(None),
    document_type: Optional[str] = Query(None),
    uploaded_by: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get documents with optional filters"""
    try:
        query = db.query(ExpenseDocument)
        
        if claim_id:
            query = query.filter(ExpenseDocument.claim_id == claim_id)
        if expense_item_id:
            query = query.filter(ExpenseDocument.expense_item_id == expense_item_id)
        if document_type:
            query = query.filter(ExpenseDocument.document_type == document_type)
        if uploaded_by:
            query = query.filter(ExpenseDocument.uploaded_by == uploaded_by)
        
        documents = query.order_by(desc(ExpenseDocument.uploaded_at)).all()
        
        return [
            DocumentUploadResponse(
                id=doc.id,
                file_name=doc.file_name,
                file_path=doc.file_path,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                document_type=doc.document_type,
                claim_id=doc.claim_id,
                expense_item_id=doc.expense_item_id,
                uploaded_by=doc.uploaded_by,
                uploaded_at=doc.uploaded_at
            ) for doc in documents
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Delete a document"""
    try:
        document = db.query(ExpenseDocument).filter(ExpenseDocument.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete file from filesystem
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Create audit log
        user = db.query(User).filter(User.id == document.uploaded_by).first()
        create_audit_log(
            db, "DELETE_DOCUMENT", document.uploaded_by,
            user.username if user else f"User {document.uploaded_by}",
            "ExpenseDocument", document_id, f"Deleted document: {document.file_name}"
        )
        
        db.delete(document)
        db.commit()
        
        return {"message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")

# Reimbursements Management
@router.get("/reimbursements", response_model=List[ExpenseReimbursementResponse])
async def get_reimbursements(
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    claim_id: Optional[int] = Query(None),
    processed_by: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get reimbursements with optional filters"""
    try:
        query = db.query(ExpenseReimbursement).options(
            joinedload(ExpenseReimbursement.claim),
            joinedload(ExpenseReimbursement.processor)
        )
        
        if user_id:
            query = query.join(ExpenseClaim).filter(ExpenseClaim.user_id == user_id)
        if status:
            query = query.filter(ExpenseReimbursement.status == status)
        if claim_id:
            query = query.filter(ExpenseReimbursement.claim_id == claim_id)
        if processed_by:
            query = query.filter(ExpenseReimbursement.processed_by == processed_by)
        
        reimbursements = query.order_by(desc(ExpenseReimbursement.processed_date)).all()
        
        result = []
        for reimb in reimbursements:
            result.append(ExpenseReimbursementResponse(
                id=reimb.id,
                claim_id=reimb.claim_id,
                reimbursement_amount=reimb.reimbursement_amount,
                payment_method=reimb.payment_method,
                payment_reference=reimb.payment_reference,
                status=reimb.status,
                processed_by=reimb.processed_by,
                processed_date=reimb.processed_date,
                payment_date=reimb.payment_date,
                notes=reimb.notes
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving reimbursements: {str(e)}")

@router.post("/reimbursements")
async def create_reimbursement(
    reimbursement_data: dict,
    processed_by: int = Query(...),
    db: Session = Depends(get_db)
):
    """Create a reimbursement for an approved claim"""
    try:
        claim_id = reimbursement_data.get("claim_id")
        if not claim_id:
            raise HTTPException(status_code=400, detail="claim_id is required")
        
        claim = db.query(ExpenseClaim).filter(
            ExpenseClaim.id == claim_id,
            ExpenseClaim.status == "approved"
        ).first()
        
        if not claim:
            raise HTTPException(status_code=404, detail="Approved claim not found")
        
        existing = db.query(ExpenseReimbursement).filter(
            ExpenseReimbursement.claim_id == claim_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Reimbursement already exists for this claim")
        
        db_reimbursement = ExpenseReimbursement(
            claim_id=claim_id,
            reimbursement_amount=claim.approved_amount or claim.total_amount,
            payment_method=reimbursement_data.get("payment_method", "bank_transfer"),
            payment_reference=reimbursement_data.get("payment_reference"),
            status="pending",
            processed_by=processed_by,
            notes=reimbursement_data.get("notes")
        )
        
        # Update claim status
        claim.status = "reimbursed"
        db.add(db_reimbursement)
        
        # Create audit log
        processor = db.query(User).filter(User.id == processed_by).first()
        create_audit_log(
            db, "CREATE_REIMBURSEMENT", processed_by,
            processor.username if processor else f"User {processed_by}",
            "ExpenseReimbursement", claim_id,
            f"Created reimbursement for claim {claim_id}: {db_reimbursement.reimbursement_amount}"
        )
        
        db.commit()
        db.refresh(db_reimbursement)
        
        return ExpenseReimbursementResponse(
            id=db_reimbursement.id,
            claim_id=db_reimbursement.claim_id,
            reimbursement_amount=db_reimbursement.reimbursement_amount,
            payment_method=db_reimbursement.payment_method,
            payment_reference=db_reimbursement.payment_reference,
            status=db_reimbursement.status,
            processed_by=db_reimbursement.processed_by,
            processed_date=db_reimbursement.processed_date,
            payment_date=db_reimbursement.payment_date,
            notes=db_reimbursement.notes
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating reimbursement: {str(e)}")

@router.put("/reimbursements/{reimbursement_id}/status")
async def update_reimbursement_status(
    reimbursement_id: int,
    status_data: dict,
    db: Session = Depends(get_db)
):
    """Update reimbursement status"""
    try:
        reimbursement = db.query(ExpenseReimbursement).filter(
            ExpenseReimbursement.id == reimbursement_id
        ).first()
        
        if not reimbursement:
            raise HTTPException(status_code=404, detail="Reimbursement not found")
        
        new_status = status_data.get("status")
        if new_status:
            reimbursement.status = new_status
            if new_status == "paid":
                reimbursement.payment_date = datetime.utcnow()
        
        if status_data.get("payment_reference"):
            reimbursement.payment_reference = status_data["payment_reference"]
        
        if status_data.get("notes"):
            reimbursement.notes = status_data["notes"]
        
        # Create audit log
        create_audit_log(
            db, "UPDATE_REIMBURSEMENT_STATUS", reimbursement.processed_by,
            f"User {reimbursement.processed_by}",
            "ExpenseReimbursement", reimbursement_id,
            f"Updated status to: {new_status}"
        )
        
        db.commit()
        
        return {"message": "Reimbursement status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating reimbursement: {str(e)}")

# Software Licenses Management
@router.get("/software-licenses", response_model=List[SoftwareLicenseResponse])
async def get_software_licenses(
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: Optional[int] = Query(None),
    vendor_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get software licenses with optional filters"""
    try:
        query = db.query(SoftwareLicense).options(joinedload(SoftwareLicense.user))
        
        if user_id:
            query = query.filter(SoftwareLicense.user_id == user_id)
        if status:
            query = query.filter(SoftwareLicense.status == status)
        if vendor_name:
            query = query.filter(SoftwareLicense.vendor_name.ilike(f"%{vendor_name}%"))
        
        query = query.order_by(desc(SoftwareLicense.created_at))
        
        if limit:
            query = query.limit(limit)
        
        licenses = query.all()
        
        result = []
        today = date.today()
        
        for license in licenses:
            days_to_expiry = None
            if license.expiry_date:
                days_to_expiry = (license.expiry_date - today).days
            
            result.append(SoftwareLicenseResponse(
                id=license.id,
                user_id=license.user_id,
                software_name=license.software_name,
                vendor_name=license.vendor_name,
                license_type=license.license_type,
                purchase_date=license.purchase_date,
                expiry_date=license.expiry_date,
                cost=license.cost,
                is_recurring=license.is_recurring,
                recurring_cycle=license.recurring_cycle,
                status=license.status,
                notes=license.notes,
                created_at=license.created_at,
                employee_name=license.user.username if license.user else None,
                days_to_expiry=days_to_expiry
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving licenses: {str(e)}")

@router.get("/software-licenses/expiring", response_model=List[SoftwareLicenseResponse])
async def get_expiring_licenses(
    days: int = Query(30, description="Number of days to check for expiration"),
    db: Session = Depends(get_db)
):
    """Get software licenses expiring within specified days"""
    try:
        today = date.today()
        expiry_date = today + timedelta(days=days)
        
        licenses = db.query(SoftwareLicense).options(
            joinedload(SoftwareLicense.user)
        ).filter(
            SoftwareLicense.expiry_date.between(today, expiry_date),
            SoftwareLicense.status == "active"
        ).order_by(SoftwareLicense.expiry_date).all()
        
        result = []
        for license in licenses:
            days_to_expiry = (license.expiry_date - today).days
            
            result.append(SoftwareLicenseResponse(
                id=license.id,
                user_id=license.user_id,
                software_name=license.software_name,
                vendor_name=license.vendor_name,
                license_type=license.license_type,
                purchase_date=license.purchase_date,
                expiry_date=license.expiry_date,
                cost=license.cost,
                is_recurring=license.is_recurring,
                recurring_cycle=license.recurring_cycle,
                status=license.status,
                notes=license.notes,
                created_at=license.created_at,
                employee_name=license.user.username if license.user else None,
                days_to_expiry=days_to_expiry
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving expiring licenses: {str(e)}")

@router.post("/software-licenses", response_model=SoftwareLicenseResponse)
async def create_software_license(
    license_data: SoftwareLicenseCreate,
    db: Session = Depends(get_db)
):
    """Create a new software license"""
    try:
        db_license = SoftwareLicense(**license_data.model_dump())
        db.add(db_license)
        
        # Create audit log
        user = db.query(User).filter(User.id == license_data.user_id).first()
        create_audit_log(
            db, "CREATE_LICENSE", license_data.user_id,
            user.username if user else f"User {license_data.user_id}",
            "SoftwareLicense", 0,
            f"Created license: {license_data.software_name} from {license_data.vendor_name}"
        )
        
        db.commit()
        db.refresh(db_license)
        
        # Calculate days to expiry
        days_to_expiry = None
        if db_license.expiry_date:
            days_to_expiry = (db_license.expiry_date - date.today()).days
        
        return SoftwareLicenseResponse(
            id=db_license.id,
            user_id=db_license.user_id,
            software_name=db_license.software_name,
            vendor_name=db_license.vendor_name,
            license_type=db_license.license_type,
            purchase_date=db_license.purchase_date,
            expiry_date=db_license.expiry_date,
            cost=db_license.cost,
            is_recurring=db_license.is_recurring,
            recurring_cycle=db_license.recurring_cycle,
            status=db_license.status,
            notes=db_license.notes,
            created_at=db_license.created_at,
            employee_name=user.username if user else None,
            days_to_expiry=days_to_expiry
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating license: {str(e)}")

@router.put("/software-licenses/{license_id}", response_model=SoftwareLicenseResponse)
async def update_software_license(
    license_id: int,
    license_data: SoftwareLicenseUpdate,
    db: Session = Depends(get_db)
):
    """Update a software license"""
    try:
        license = db.query(SoftwareLicense).filter(SoftwareLicense.id == license_id).first()
        if not license:
            raise HTTPException(status_code=404, detail="License not found")
        
        update_data = license_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(license, field, value)
        
        # Create audit log
        user = db.query(User).filter(User.id == license.user_id).first()
        create_audit_log(
            db, "UPDATE_LICENSE", license.user_id,
            user.username if user else f"User {license.user_id}",
            "SoftwareLicense", license_id, f"Updated license: {license.software_name}"
        )
        
        db.commit()
        db.refresh(license)
        
        days_to_expiry = None
        if license.expiry_date:
            days_to_expiry = (license.expiry_date - date.today()).days
        
        return SoftwareLicenseResponse(
            id=license.id,
            user_id=license.user_id,
            software_name=license.software_name,
            vendor_name=license.vendor_name,
            license_type=license.license_type,
            purchase_date=license.purchase_date,
            expiry_date=license.expiry_date,
            cost=license.cost,
            is_recurring=license.is_recurring,
            recurring_cycle=license.recurring_cycle,
            status=license.status,
            notes=license.notes,
            created_at=license.created_at,
            employee_name=user.username if user else None,
            days_to_expiry=days_to_expiry
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating license: {str(e)}")

@router.delete("/software-licenses/{license_id}")
async def delete_software_license(
    license_id: int,
    db: Session = Depends(get_db)
):
    """Delete a software license"""
    try:
        license = db.query(SoftwareLicense).filter(SoftwareLicense.id == license_id).first()
        if not license:
            raise HTTPException(status_code=404, detail="License not found")
        
        # Create audit log
        user = db.query(User).filter(User.id == license.user_id).first()
        create_audit_log(
            db, "DELETE_LICENSE", license.user_id,
            user.username if user else f"User {license.user_id}",
            "SoftwareLicense", license_id, f"Deleted license: {license.software_name}"
        )
        
        db.delete(license)
        db.commit()
        
        return {"message": "License deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting license: {str(e)}")

# Audit Logs
@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    user_id: Optional[int] = Query(None),
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: Optional[int] = Query(100),
    db: Session = Depends(get_db)
):
    """Get audit logs with optional filters"""
    try:
        query = db.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if action:
            query = query.filter(AuditLog.action.ilike(f"%{action}%"))
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        
        query = query.order_by(desc(AuditLog.timestamp))
        
        if limit:
            query = query.limit(limit)
        
        logs = query.all()
        
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving audit logs: {str(e)}")

# Bulk Operations
@router.put("/items/bulk-approve")
async def bulk_approve_items(
    approval_request: BulkApprovalRequest,
    approver_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """Bulk approve expense items"""
    try:
        items = db.query(ExpenseItem).filter(
            ExpenseItem.id.in_(approval_request.item_ids)
        ).all()
        
        if not items:
            raise HTTPException(status_code=404, detail="No items found")
        
        for i, item in enumerate(items):
            if i < len(approval_request.approved_amounts):
                item.approved_amount = approval_request.approved_amounts[i]
            else:
                item.approved_amount = item.amount
        
        # Create audit log
        approver = db.query(User).filter(User.id == approver_id).first()
        create_audit_log(
            db, "BULK_APPROVE_ITEMS", approver_id,
            approver.username if approver else f"User {approver_id}",
            "ExpenseItem", 0,
            f"Bulk approved {len(items)} items. Comments: {approval_request.comments or 'None'}"
        )
        
        db.commit()
        
        return {
            "message": f"Successfully approved {len(items)} items",
            "approved_items": len(items)
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error bulk approving items: {str(e)}")
