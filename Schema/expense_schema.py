from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

# Enum for expense status
class ExpenseStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REIMBURSED = "reimbursed"

# Base schemas
class ExpenseCategoryBase(BaseModel):
    category_name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = True

class ExpenseCategoryCreate(ExpenseCategoryBase):
    pass

class ExpenseCategoryUpdate(BaseModel):
    category_name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

class ExpenseCategoryResponse(ExpenseCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Expense Claim schemas
class ExpenseClaimBase(BaseModel):
    user_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    claim_date: date
    total_amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field("USD", min_length=3, max_length=3)

class ExpenseClaimCreate(ExpenseClaimBase):
    pass

class ExpenseClaimUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    claim_date: Optional[date]
    total_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)

class ExpenseClaimResponse(ExpenseClaimBase):
    id: int
    approver_id: Optional[int] = None
    approved_amount: Optional[Decimal] = None
    status: str
    rejection_reason: Optional[str] = None
    submission_date: Optional[datetime] = None
    approval_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    employee_name: Optional[str] = None
    items_count: Optional[int] = None
    items: Optional[List["ExpenseItemResponse"]] = None
    
    class Config:
        from_attributes = True

# Expense Item schemas
class ExpenseItemBase(BaseModel):
    category_id: int
    item_description: str = Field(..., min_length=1, max_length=500)
    expense_date: date
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field("USD", min_length=3, max_length=3)
    vendor_name: Optional[str] = Field(None, max_length=200)
    payment_method: Optional[str] = Field(None, max_length=50)
    receipt_number: Optional[str] = Field(None, max_length=100)
    business_purpose: Optional[str] = Field(None, max_length=500)
    is_billable: bool = False
    client_name: Optional[str] = Field(None, max_length=200)
    project_code: Optional[str] = Field(None, max_length=50)

class ExpenseItemCreate(ExpenseItemBase):
    pass

class ExpenseItemUpdate(BaseModel):
    category_id: Optional[int] = None
    item_description: Optional[str] = Field(None, min_length=1, max_length=500)
    expense_date: Optional[date] = None
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    vendor_name: Optional[str] = Field(None, max_length=200)
    payment_method: Optional[str] = Field(None, max_length=50)
    receipt_number: Optional[str] = Field(None, max_length=100)
    business_purpose: Optional[str] = Field(None, max_length=500)
    is_billable: Optional[bool] = None
    client_name: Optional[str] = Field(None, max_length=200)
    project_code: Optional[str] = Field(None, max_length=50)
    approved_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)

class ExpenseItemResponse(ExpenseItemBase):
    id: int
    claim_id: Optional[int] = None
    approved_amount: Optional[Decimal] = None
    category_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class BulkExpenseItemCreate(BaseModel):
    items: List[ExpenseItemCreate]

# Document schemas
class DocumentUploadResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    file_size: int
    mime_type: str
    document_type: str
    claim_id: Optional[int] = None
    expense_item_id: Optional[int] = None
    uploaded_by: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

class ExpenseDocumentResponse(BaseModel):
    id: int
    document_type: str = Field(default="receipt", max_length=50)
    file_name: str = Field(..., max_length=255)
    file_path: str
    file_size: int
    mime_type: str
    claim_id: Optional[int] = None
    expense_item_id: Optional[int] = None
    uploaded_by: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

# Approval schemas
class ExpenseApprovalCreate(BaseModel):
    approver_id: int
    action: str = Field(..., pattern="^(approve|reject|pending)$")
    remarks: Optional[str] = Field(None, max_length=500)
    approved_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)

class ExpenseApprovalResponse(BaseModel):
    id: int
    claim_id: int
    approver_id: int
    action: str
    remarks: Optional[str]
    approved_amount: Optional[Decimal]
    approval_date: datetime
    
    class Config:
        from_attributes = True

class ApprovalRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|pending)$")
    approved_amount: Optional[Decimal] = None
    comments: Optional[str] = None
    remarks: Optional[str] = None

class ApprovalResponse(BaseModel):
    message: str
    claim_id: int
    status: str
    approval_id: int
    approved_amount: Optional[float] = None

# Reimbursement schemas
class ExpenseReimbursementCreate(BaseModel):
    claim_id: int
    reimbursement_amount: Decimal = Field(..., ge=0)
    payment_method: str = Field(default="bank_transfer", max_length=50)
    payment_reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None

class ExpenseReimbursementResponse(BaseModel):
    id: int
    claim_id: int
    reimbursement_amount: Decimal
    payment_method: str
    payment_reference: Optional[str] = None
    status: str
    processed_by: int
    processed_date: datetime
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True

class ReimbursementRequest(BaseModel):
    claim_id: int
    payment_method: str = Field(default="bank_transfer", max_length=50)
    payment_reference: Optional[str] = None
    notes: Optional[str] = None

# Software License schemas
class SoftwareLicenseCreate(BaseModel):
    user_id: int
    software_name: str = Field(..., max_length=200)
    vendor_name: str = Field(..., max_length=200)
    license_type: str = Field(..., max_length=50)
    purchase_date: date
    expiry_date: Optional[date] = None
    cost: Decimal = Field(..., ge=0)
    is_recurring: bool = False
    recurring_cycle: Optional[str] = Field(None, max_length=20)
    status: str = Field(default="active", pattern="^(active|expired|cancelled)$")
    notes: Optional[str] = None

class SoftwareLicenseUpdate(BaseModel):
    software_name: Optional[str] = Field(None, max_length=200)
    vendor_name: Optional[str] = Field(None, max_length=200)
    license_type: Optional[str] = Field(None, max_length=50)
    purchase_date: Optional[date] = None
    expiry_date: Optional[date] = None
    cost: Optional[Decimal] = Field(None, ge=0)
    is_recurring: Optional[bool] = None
    recurring_cycle: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, pattern="^(active|expired|cancelled)$")
    notes: Optional[str] = None

class SoftwareLicenseResponse(BaseModel):
    id: int
    user_id: int
    software_name: str
    vendor_name: str
    license_type: str
    purchase_date: date
    expiry_date: Optional[date] = None
    cost: Decimal
    is_recurring: bool
    recurring_cycle: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    employee_name: Optional[str] = None
    days_to_expiry: Optional[int] = None
    
    class Config:
        from_attributes = True

class UserProfile(BaseModel):
    user_id: int
    username: str
    email: str
    role: str
    department: Optional[str] = None
    manager_id: Optional[int] = None

class AuditLogResponse(BaseModel):
    id: int
    action: str
    user_id: int
    user_name: str
    entity_type: str
    entity_id: int
    details: Optional[str] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True

class BulkApprovalRequest(BaseModel):
    item_ids: List[int]
    approved_amounts: List[Decimal] = Field(..., min_items=1)
    comments: Optional[str] = Field(None, max_length=500)
    
    @validator('approved_amounts')
    def validate_amounts(cls, v):
        if any(amount <= 0 for amount in v):
            raise ValueError("All approved amounts must be greater than zero")
        return v

# Update forward references
ExpenseClaimResponse.model_rebuild()
