from sqlalchemy import Column, Integer, String, Date, Text, Boolean, DECIMAL, Enum, ForeignKey, JSON, BIGINT
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base
import enum

# Enum classes for various status fields
class ClaimStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PARTIALLY_APPROVED = "partially_approved"
    REIMBURSED = "reimbursed"


class ItemStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LicenseType(str, enum.Enum):
    INDIVIDUAL = "Individual"
    TEAM = "Team"
    ENTERPRISE = "Enterprise"
    SUBSCRIPTION = "Subscription"
    ONETIME = "One-time"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    UPI = "upi"
    OTHER = "other"


class LicenseStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class RecurringCycle(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class DocumentType(str, enum.Enum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    BILL = "bill"
    CONTRACT = "contract"
    LICENSE_AGREEMENT = "license_agreement"
    OTHER = "other"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELEGATED = "delegated"


class ReimbursementMethod(str, enum.Enum):
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    CASH = "cash"
    SALARY_ADJUSTMENT = "salary_adjustment"


class Quarter(str, enum.Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"


class AuditAction(str, enum.Enum):
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


# Expense Category Model
class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(Date, default=func.current_date())
    updated_at = Column(Date, default=func.current_date(), onupdate=func.current_date())

    # Relationships
    expense_items = relationship("ExpenseItem", back_populates="category")
    department_budgets = relationship("DepartmentBudget", back_populates="category")

    def to_dict(self):
        return {
            "id": self.id,
            "category_name": self.category_name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# Software Asset Model
class SoftwareAsset(Base):
    __tablename__ = "software_assets"

    id = Column(Integer, primary_key=True, index=True)
    software_name = Column(String(200), nullable=False)
    vendor_name = Column(String(200))
    license_type = Column(Enum(LicenseType), default=LicenseType.INDIVIDUAL)
    version = Column(String(50))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(Date, default=func.current_date())
    updated_at = Column(Date, default=func.current_date(), onupdate=func.current_date())

    # Relationships
    software_licenses = relationship("SoftwareLicense", back_populates="software_asset")
    expense_items = relationship("ExpenseItem", back_populates="software_asset")

    def to_dict(self):
        return {
            "id": self.id,
            "software_name": self.software_name,
            "vendor_name": self.vendor_name,
            "license_type": self.license_type.value if self.license_type else None,
            "version": self.version,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# Expense Claim Model
class ExpenseClaim(Base):
    __tablename__ = "expense_claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_number = Column(String(50), unique=True, nullable=False)
    employee_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    total_amount = Column(DECIMAL(15,2), default=0.00)
    currency = Column(String(3), default='INR')
    claim_date = Column(Date, nullable=False)
    submission_date = Column(Date, default=func.current_date())
    status = Column(Enum(ClaimStatus), default=ClaimStatus.DRAFT)
    approved_amount = Column(DECIMAL(15,2), default=0.00)
    approver_id = Column(Integer, ForeignKey('users.id'))
    approval_date = Column(Date)
    rejection_reason = Column(Text)
    reimbursement_date = Column(Date)
    reimbursement_reference = Column(String(100))
    created_at = Column(Date, default=func.current_date())
    updated_at = Column(Date, default=func.current_date(), onupdate=func.current_date())

    # Relationships
    user = relationship("User", back_populates="expense_claims", foreign_keys=[employee_id])
    approver = relationship("User", back_populates="approved_claims", foreign_keys=[approver_id])
    expense_items = relationship("ExpenseItem", back_populates="claim", cascade="all, delete-orphan")
    approvals = relationship("ExpenseApproval", back_populates="claim", cascade="all, delete-orphan")
    reimbursements = relationship("ExpenseReimbursement", back_populates="claim", cascade="all, delete-orphan")
    documents = relationship("ExpenseDocument", back_populates="claim")

    def to_dict(self):
        return {
            "id": self.id,
            "claim_number": self.claim_number,
            "employee_id": self.employee_id,
            "title": self.title,
            "description": self.description,
            "total_amount": float(self.total_amount) if self.total_amount else 0.0,
            "currency": self.currency,
            "claim_date": self.claim_date.isoformat() if self.claim_date else None,
            "submission_date": self.submission_date.isoformat() if self.submission_date else None,
            "status": self.status.value if self.status else None,
            "approved_amount": float(self.approved_amount) if self.approved_amount else 0.0,
            "approver_id": self.approver_id,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None,
            "rejection_reason": self.rejection_reason,
            "reimbursement_date": self.reimbursement_date.isoformat() if self.reimbursement_date else None,
            "reimbursement_reference": self.reimbursement_reference,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "employee_name": self.user.username if self.user else None,
            "approver_name": self.approver.username if self.approver else None
        }


# Expense Item Model
class ExpenseItem(Base):
    __tablename__ = "expense_items"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey('expense_claims.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('expense_categories.id'), nullable=False)
    software_asset_id = Column(Integer, ForeignKey('software_assets.id'))
    item_description = Column(String(500), nullable=False)
    expense_date = Column(Date, nullable=False)
    amount = Column(DECIMAL(12,2), nullable=False)
    currency = Column(String(3), default='INR')
    vendor_name = Column(String(200))
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH)
    receipt_number = Column(String(100))
    tax_amount = Column(DECIMAL(12,2), default=0.00)
    is_billable = Column(Boolean, default=False)
    client_name = Column(String(200))
    project_code = Column(String(50))
    status = Column(Enum(ItemStatus), default=ItemStatus.PENDING)
    approved_amount = Column(DECIMAL(12,2), default=0.00)
    rejection_reason = Column(String(500))
    created_at = Column(Date, default=func.current_date())
    updated_at = Column(Date, default=func.current_date(), onupdate=func.current_date())

    # Relationships
    claim = relationship("ExpenseClaim", back_populates="expense_items")
    category = relationship("ExpenseCategory", back_populates="expense_items")
    software_asset = relationship("SoftwareAsset", back_populates="expense_items")
    documents = relationship("ExpenseDocument", back_populates="expense_item")
    software_licenses = relationship("SoftwareLicense", back_populates="expense_item")

    def to_dict(self):
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "category_id": self.category_id,
            "software_asset_id": self.software_asset_id,
            "item_description": self.item_description,
            "expense_date": self.expense_date.isoformat() if self.expense_date else None,
            "amount": float(self.amount) if self.amount else 0.0,
            "currency": self.currency,
            "vendor_name": self.vendor_name,
            "payment_method": self.payment_method.value if self.payment_method else None,
            "receipt_number": self.receipt_number,
            "tax_amount": float(self.tax_amount) if self.tax_amount else 0.0,
            "is_billable": self.is_billable,
            "client_name": self.client_name,
            "project_code": self.project_code,
            "status": self.status.value if self.status else None,
            "approved_amount": float(self.approved_amount) if self.approved_amount else 0.0,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "category_name": self.category.category_name if self.category else None,
            "software_name": self.software_asset.software_name if self.software_asset else None
        }


# Software License Model
class SoftwareLicense(Base):
    __tablename__ = "software_licenses"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    software_asset_id = Column(Integer, ForeignKey('software_assets.id'), nullable=False)
    expense_item_id = Column(Integer, ForeignKey('expense_items.id'))
    license_key = Column(String(500))
    purchase_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    cost = Column(DECIMAL(12,2), nullable=False)
    currency = Column(String(3), default='INR')
    license_duration_months = Column(Integer, default=12)
    is_recurring = Column(Boolean, default=False)
    recurring_cycle = Column(Enum(RecurringCycle))
    auto_renewal = Column(Boolean, default=False)
    status = Column(Enum(LicenseStatus), default=LicenseStatus.ACTIVE)
    vendor_contact_email = Column(String(255))
    vendor_contact_phone = Column(String(20))
    notes = Column(Text)
    created_at = Column(Date, default=func.current_date())
    updated_at = Column(Date, default=func.current_date(), onupdate=func.current_date())

    # Relationships
    user = relationship("User", back_populates="software_licenses")
    software_asset = relationship("SoftwareAsset", back_populates="software_licenses")
    expense_item = relationship("ExpenseItem", back_populates="software_licenses")
    documents = relationship("ExpenseDocument", back_populates="software_license")

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "software_asset_id": self.software_asset_id,
            "expense_item_id": self.expense_item_id,
            "license_key": self.license_key,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "cost": float(self.cost) if self.cost else 0.0,
            "currency": self.currency,
            "license_duration_months": self.license_duration_months,
            "is_recurring": self.is_recurring,
            "recurring_cycle": self.recurring_cycle.value if self.recurring_cycle else None,
            "auto_renewal": self.auto_renewal,
            "status": self.status.value if self.status else None,
            "vendor_contact_email": self.vendor_contact_email,
            "vendor_contact_phone": self.vendor_contact_phone,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "employee_name": self.user.username if self.user else None,
            "software_name": self.software_asset.software_name if self.software_asset else None
        }


# Expense Document Model
class ExpenseDocument(Base):
    __tablename__ = "expense_documents"

    id = Column(Integer, primary_key=True, index=True)
    expense_item_id = Column(Integer, ForeignKey('expense_items.id'))
    claim_id = Column(Integer, ForeignKey('expense_claims.id'))
    software_license_id = Column(Integer, ForeignKey('software_licenses.id'))
    document_type = Column(Enum(DocumentType), nullable=False)
    original_filename = Column(String(500), nullable=False)
    stored_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size_bytes = Column(BIGINT)
    mime_type = Column(String(100))
    upload_date = Column(Date, default=func.current_date())
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    description = Column(String(500))
    is_primary = Column(Boolean, default=False)
    created_at = Column(Date, default=func.current_date())

    # Relationships
    expense_item = relationship("ExpenseItem", back_populates="documents")
    claim = relationship("ExpenseClaim", back_populates="documents")
    software_license = relationship("SoftwareLicense", back_populates="documents")
    uploader = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "expense_item_id": self.expense_item_id,
            "claim_id": self.claim_id,
            "software_license_id": self.software_license_id,
            "document_type": self.document_type.value if self.document_type else None,
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "mime_type": self.mime_type,
            "upload_date": self.upload_date.isoformat() if self.upload_date else None,
            "uploaded_by": self.uploaded_by,
            "description": self.description,
            "is_primary": self.is_primary,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# Expense Approval Model
class ExpenseApproval(Base):
    __tablename__ = "expense_approvals"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey('expense_claims.id'), nullable=False)
    approver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING)
    approved_amount = Column(DECIMAL(15,2), default=0.00)
    comments = Column(Text)
    approval_date = Column(Date, default=func.current_date())
    delegation_to = Column(Integer, ForeignKey('users.id'))
    created_at = Column(Date, default=func.current_date())
    updated_at = Column(Date, default=func.current_date(), onupdate=func.current_date())

    # Relationships
    claim = relationship("ExpenseClaim", back_populates="approvals")
    approver = relationship("User", back_populates="expense_approvals", foreign_keys=[approver_id])
    delegatee = relationship("User", foreign_keys=[delegation_to])

    def to_dict(self):
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "approver_id": self.approver_id,
            "status": self.status.value if self.status else None,
            "approved_amount": float(self.approved_amount) if self.approved_amount else 0.0,
            "comments": self.comments,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None,
            "delegation_to": self.delegation_to,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "approver_name": self.approver.username if self.approver else None,
            "delegatee_name": self.delegatee.username if self.delegatee else None
        }


# Expense Reimbursement Model
class ExpenseReimbursement(Base):
    __tablename__ = "expense_reimbursements"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey('expense_claims.id'), nullable=False)
    reimbursement_amount = Column(DECIMAL(15,2), nullable=False)
    reimbursement_date = Column(Date, nullable=False, default=func.current_date())
    payment_method = Column(Enum(ReimbursementMethod), nullable=False, default=ReimbursementMethod.BANK_TRANSFER)
    transaction_id = Column(String(100))
    bank_reference = Column(String(100))
    processed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    notes = Column(Text)
    created_at = Column(Date, default=func.current_date())

    # Relationships
    claim = relationship("ExpenseClaim", back_populates="reimbursements")
    processor = relationship("User", back_populates="expense_reimbursements")

    def to_dict(self):
        return {
            "id": self.id,
            "claim_id": self.claim_id,
            "reimbursement_amount": float(self.reimbursement_amount),
            "reimbursement_date": self.reimbursement_date.isoformat() if self.reimbursement_date else None,
            "payment_method": self.payment_method.value if self.payment_method else None,
            "transaction_id": self.transaction_id,
            "bank_reference": self.bank_reference,
            "processed_by": self.processed_by,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processor_name": self.processor.username if self.processor else None
        }


# Department Budget Model
class DepartmentBudget(Base):
    __tablename__ = "department_budgets"

    id = Column(Integer, primary_key=True, index=True)
    department_name = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey('expense_categories.id'), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    allocated_amount = Column(DECIMAL(15,2), nullable=False)
    spent_amount = Column(DECIMAL(15,2), default=0.00)
    remaining_amount = Column(DECIMAL(15,2), default=0.00)
    quarter = Column(Enum(Quarter))
    created_at = Column(Date, default=func.current_date())
    updated_at = Column(Date, default=func.current_date(), onupdate=func.current_date())

    # Relationships
    category = relationship("ExpenseCategory", back_populates="department_budgets")

    def to_dict(self):
        return {
            "id": self.id,
            "department_name": self.department_name,
            "category_id": self.category_id,
            "fiscal_year": self.fiscal_year,
            "allocated_amount": float(self.allocated_amount) if self.allocated_amount else 0.0,
            "spent_amount": float(self.spent_amount) if self.spent_amount else 0.0,
            "remaining_amount": float(self.remaining_amount) if self.remaining_amount else 0.0,
            "quarter": self.quarter.value if self.quarter else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "category_name": self.category.category_name if self.category else None
        }


# Expense Audit Log Model
class ExpenseAuditLog(Base):
    __tablename__ = "expense_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(50), nullable=False)
    record_id = Column(Integer, nullable=False)
    action = Column(Enum(AuditAction), nullable=False)
    old_values = Column(JSON)
    new_values = Column(JSON)
    changed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    change_reason = Column(Text)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    created_at = Column(Date, default=func.current_date())

    # Relationships
    changer = relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "table_name": self.table_name,
            "record_id": self.record_id,
            "action": self.action.value if self.action else None,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "changed_by": self.changed_by,
            "change_reason": self.change_reason,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "changer_name": self.changer.username if self.changer else None
        }