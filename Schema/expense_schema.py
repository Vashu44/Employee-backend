from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime, date

# Base Response Models
class EmployeeResponse(BaseModel):
    id: int
    employee_id: int
    full_name: str
    email: EmailStr
    phone: Optional[int] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: bool
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

class ExpenseCategoryResponse(BaseModel):
    id: int
    category_name: str
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

class SoftwareAssetResponse(BaseModel):
    id: int
    software_name: str
    vendor_name: Optional[str] = None
    license_type: str
    version: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[date] = None
    updated_at: Optional[date] = None

# Create/Update Models
class EmployeeCreate(BaseModel):
    employee_id: int
    full_name: str
    email: EmailStr
    phone: Optional[int] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    manager_id: Optional[int] = None

class EmployeeUpdate(BaseModel):
    employee_id: Optional[int] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[int] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None

class ExpenseCategoryCreate(BaseModel):
    category_name: str
    description: Optional[str] = None

class ExpenseCategoryUpdate(BaseModel):
    category_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class SoftwareAssetCreate(BaseModel):
    software_name: str
    vendor_name: Optional[str] = None
    license_type: str = "Individual"
    version: Optional[str] = None
    description: Optional[str] = None

class SoftwareAssetUpdate(BaseModel):
    software_name: Optional[str] = None
    vendor_name: Optional[str] = None
    license_type: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

# Expense Item Models
class ExpenseItemCreate(BaseModel):
    claim_id: int
    category_id: int
    software_asset_id: Optional[int] = None
    item_description: str
    expense_date: date
    amount: float
    currency: str = "INR"
    vendor_name: Optional[str] = None
    payment_method: str = "cash"
    receipt_number: Optional[str] = None
    tax_amount: float = 0.00
    is_billable: bool = False
    client_name: Optional[str] = None
    project_code: Optional[str] = None

    @validator('amount')
    def validate_amount(cls, v):
        if v < 0:
            raise ValueError('Amount must be non-negative')
        return v

    @validator('tax_amount')
    def validate_tax_amount(cls, v):
        if v < 0:
            raise ValueError('Tax amount must be non-negative')
        return v

class ExpenseItemUpdate(BaseModel):
    category_id: Optional[int] = None
    software_asset_id: Optional[int] = None
    item_description: Optional[str] = None
    expense_date: Optional[date] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    vendor_name: Optional[str] = None
    payment_method: Optional[str] = None
    receipt_number: Optional[str] = None
    tax_amount: Optional[float] = None
    is_billable: Optional[bool] = None
    client_name: Optional[str] = None
    project_code: Optional[str] = None
    status: Optional[str] = None
    approved_amount: Optional[float] = None
    rejection_reason: Optional[str] = None

class ExpenseItemResponse(BaseModel):
    id: int
    claim_id: int
    category_id: int
    software_asset_id: Optional[int] = None
    item_description: str
    expense_date: str
    amount: float
    currency: str
    vendor_name: Optional[str] = None
    payment_method: str
    receipt_number: Optional[str] = None
    tax_amount: float
    is_billable: bool
    client_name: Optional[str] = None
    project_code: Optional[str] = None
    status: str
    approved_amount: float
    rejection_reason: Optional[str] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None
    category_name: Optional[str] = None
    software_name: Optional[str] = None

# Expense Claim Models
class ExpenseClaimCreate(BaseModel):
    employee_id: int  # Can be used for admin submissions
    user_id: Optional[int] = None  # Used when submitting from frontend context
    title: str
    description: Optional[str] = None
    claim_date: date
    currency: str = "INR"

    @validator('user_id', pre=True)
    def set_employee_id_from_user_id(cls, v, values):
        """If user_id is provided and employee_id is not, use user_id as employee_id"""
        if v is not None and 'employee_id' not in values:
            values['employee_id'] = v
        return v
    
class ExpenseClaimUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    claim_date: Optional[date] = None
    status: Optional[str] = None
    approved_amount: Optional[float] = None
    approver_id: Optional[int] = None
    rejection_reason: Optional[str] = None

class ExpenseClaimResponse(BaseModel):
    id: int
    claim_number: str
    employee_id: int
    title: str
    description: Optional[str] = None
    total_amount: float
    currency: str
    claim_date: str
    submission_date: Optional[str] = None
    status: str
    approved_amount: float
    approver_id: Optional[int] = None
    approval_date: Optional[date] = None
    rejection_reason: Optional[str] = None
    reimbursement_date: Optional[str] = None
    reimbursement_reference: Optional[str] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None
    employee_name: Optional[str] = None
    approver_name: Optional[str] = None

# Software License Models
class SoftwareLicenseCreate(BaseModel):
    employee_id: int
    software_asset_id: int
    expense_item_id: Optional[int] = None
    license_key: Optional[str] = None
    purchase_date: date
    expiry_date: Optional[date] = None
    cost: float
    currency: str = "INR"
    license_duration_months: int = 12
    is_recurring: bool = False
    recurring_cycle: Optional[str] = None
    auto_renewal: bool = False
    vendor_contact_email: Optional[EmailStr] = None
    vendor_contact_phone: Optional[int] = None
    notes: Optional[str] = None

    @validator('cost')
    def validate_cost(cls, v):
        if v < 0:
            raise ValueError('Cost must be non-negative')
        return v

class SoftwareLicenseUpdate(BaseModel):
    license_key: Optional[str] = None
    expiry_date: Optional[date] = None
    cost: Optional[float] = None
    currency: Optional[str] = None
    license_duration_months: Optional[int] = None
    is_recurring: Optional[bool] = None
    recurring_cycle: Optional[str] = None
    auto_renewal: Optional[bool] = None
    status: Optional[str] = None
    vendor_contact_email: Optional[EmailStr] = None
    vendor_contact_phone: Optional[int] = None
    notes: Optional[str] = None

class SoftwareLicenseResponse(BaseModel):
    id: int
    employee_id: int
    software_asset_id: int
    expense_item_id: Optional[int] = None
    license_key: Optional[str] = None
    purchase_date: str
    expiry_date: Optional[str] = None
    cost: float
    currency: str
    license_duration_months: int
    is_recurring: bool
    recurring_cycle: Optional[str] = None
    auto_renewal: bool
    status: str
    vendor_contact_email: Optional[str] = None
    vendor_contact_phone: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None
    employee_name: Optional[str] = None
    software_name: Optional[str] = None

# Document Models
class DocumentUpload(BaseModel):
    expense_item_id: Optional[int] = None
    claim_id: Optional[int] = None
    software_license_id: Optional[int] = None
    document_type: str
    description: Optional[str] = None
    is_primary: bool = False

class DocumentResponse(BaseModel):
    id: int
    expense_item_id: Optional[int] = None
    claim_id: Optional[int] = None
    software_license_id: Optional[int] = None
    document_type: str
    original_filename: str
    stored_filename: str
    file_path: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    upload_date: Optional[date] = None
    uploaded_by: int
    description: Optional[str] = None
    is_primary: bool
    created_at: Optional[date] = None

# Approval Models
class ApprovalRequest(BaseModel):
    action: str  # "approve" or "reject"
    approved_amount: Optional[float] = None
    comments: Optional[str] = None
    
    @validator('action')
    def validate_action(cls, v):
        if v not in ["approve", "reject"]:
            raise ValueError('Action must be "approve" or "reject"')
        return v

class ApprovalResponse(BaseModel):
    id: int
    claim_id: int
    approver_id: int
    approval_level: int
    status: str
    approved_amount: float
    comments: Optional[str] = None
    approval_date: Optional[date] = None
    delegation_to: Optional[int] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None
    approver_name: Optional[str] = None

# Reimbursement Models
class ReimbursementCreate(BaseModel):
    claim_id: int
    reimbursement_amount: float
    reimbursement_date: date
    payment_method: str = "bank_transfer"
    transaction_id: Optional[str] = None
    bank_reference: Optional[str] = None
    notes: Optional[str] = None

    @validator('reimbursement_amount')
    def validate_reimbursement_amount(cls, v):
        if v <= 0:
            raise ValueError('Reimbursement amount must be positive')
        return v

class ReimbursementResponse(BaseModel):
    id: int
    claim_id: int
    reimbursement_amount: float
    reimbursement_date: str
    payment_method: str
    transaction_id: Optional[str] = None
    bank_reference: Optional[str] = None
    processed_by: int
    notes: Optional[str] = None
    created_at: Optional[date] = None
    processor_name: Optional[str] = None

# Budget Models
class DepartmentBudgetCreate(BaseModel):
    department_name: str
    category_id: int
    fiscal_year: int
    allocated_amount: float
    quarter: Optional[str] = None

    @validator('allocated_amount')
    def validate_allocated_amount(cls, v):
        if v <= 0:
            raise ValueError('Allocated amount must be positive')
        return v

    @validator('fiscal_year')
    def validate_fiscal_year(cls, v):
        current_year = datetime.now().year
        if v < 2020 or v > current_year + 5:
            raise ValueError(f'Fiscal year must be between 2020 and {current_year + 5}')
        return v

class DepartmentBudgetUpdate(BaseModel):
    allocated_amount: Optional[float] = None
    spent_amount: Optional[float] = None
    quarter: Optional[str] = None

class DepartmentBudgetResponse(BaseModel):
    id: int
    department_name: str
    category_id: int
    fiscal_year: int
    allocated_amount: float
    spent_amount: float
    remaining_amount: float
    quarter: Optional[str] = None
    created_at: Optional[date] = None
    updated_at: Optional[date] = None
    category_name: Optional[str] = None

# Draft Models for Expense Claims
class ExpenseClaimDraft(BaseModel):
    employee_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    claim_date: Optional[date] = None
    currency: Optional[str] = "INR"

# Response Models for Lists
class ExpenseClaimSummary(BaseModel):
    id: int
    claim_number: str
    employee_name: str
    department: Optional[str] = None
    title: str
    total_amount: float
    approved_amount: float
    status: str
    claim_date: str
    submission_date: Optional[str] = None
    created_at: Optional[date] = None

class ExpenseItemSummary(BaseModel):
    id: int
    claim_number: str
    employee_name: str
    category_name: str
    item_description: str
    expense_date: str
    amount: float
    approved_amount: float
    status: str

class SoftwareLicenseSummary(BaseModel):
    id: int
    employee_name: str
    software_name: str
    vendor_name: Optional[str] = None
    purchase_date: str
    expiry_date: Optional[str] = None
    cost: float
    status: str
    days_to_expiry: Optional[int] = None

# Filter Models
class ExpenseFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    department: Optional[str] = None
    employee_id: Optional[int] = None
    category_id: Optional[int] = None
    status: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None

class SoftwareLicenseFilter(BaseModel):
    employee_id: Optional[int] = None
    software_asset_id: Optional[int] = None
    status: Optional[str] = None
    expiring_in_days: Optional[int] = None
    department: Optional[str] = None

# Statistics Models
class ExpenseStatistics(BaseModel):
    total_claims: int
    total_amount: float
    approved_amount: float
    pending_claims: int
    approved_claims: int
    rejected_claims: int
    average_claim_amount: float
    
class DepartmentExpenseStats(BaseModel):
    department: str
    total_amount: float
    approved_amount: float
    claim_count: int
    average_amount: float

class CategoryExpenseStats(BaseModel):
    category_name: str
    total_amount: float
    approved_amount: float
    item_count: int
    
class MonthlyExpenseReport(BaseModel):
    year: int
    month: str
    department: str
    category_name: str
    total_items: int
    total_amount: float
    total_approved_amount: float

# Audit Log Models
class AuditLogResponse(BaseModel):
    id: int
    table_name: str
    record_id: int
    action: str
    old_values: Optional[dict] = None
    new_values: Optional[dict] = None
    changed_by: int
    change_reason: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[date] = None
    changer_name: Optional[str] = None