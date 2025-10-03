from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, ForeignKey, Boolean, text
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class ExpenseCategory(Base):
    __tablename__ = "expense_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(100), nullable=False, unique=True)
    description = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, 
                       server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(DateTime, nullable=False,
                       server_default=text('CURRENT_TIMESTAMP'))
    
    # Relationships
    items = relationship("ExpenseItem", back_populates="category")
    # REMOVED: budgets = relationship("ExpenseBudget", back_populates="category")

class ExpenseClaim(Base):
    __tablename__ = "expense_claims"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    approver_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(String(1000))
    claim_date = Column(Date, nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    approved_amount = Column(Numeric(10, 2))
    currency = Column(String(3), default="INR")
    status = Column(String(20), default="pending")
    rejection_reason = Column(String(500))
    submission_date = Column(DateTime, default=datetime.utcnow)
    approval_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="expense_claims")
    approver = relationship("User", foreign_keys=[approver_id], back_populates="approved_expense_claims")
    items = relationship("ExpenseItem", back_populates="claim", cascade="all, delete-orphan")
    documents = relationship("ExpenseDocument", back_populates="claim", cascade="all, delete-orphan")
    approvals = relationship("ExpenseApproval", back_populates="claim", cascade="all, delete-orphan")
    reimbursements = relationship("ExpenseReimbursement", back_populates="claim", uselist=False)

class ExpenseItem(Base):
    __tablename__ = "expense_items"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey('expense_claims.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('expense_categories.id'), nullable=False)
    item_description = Column(String(500), nullable=False)
    expense_date = Column(Date, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    approved_amount = Column(Numeric(10, 2))
    currency = Column(String(3), default="INR")
    vendor_name = Column(String(200))
    payment_method = Column(String(50))
    receipt_number = Column(String(100))
    business_purpose = Column(String(500))
    is_billable = Column(Boolean, default=False)
    client_name = Column(String(200))
    project_code = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    claim = relationship("ExpenseClaim", back_populates="items")
    category = relationship("ExpenseCategory", back_populates="items")
    documents = relationship("ExpenseDocument", back_populates="expense_item", cascade="all, delete-orphan")

class ExpenseDocument(Base):
    __tablename__ = "expense_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey('expense_claims.id'), nullable=True)
    expense_item_id = Column(Integer, ForeignKey('expense_items.id'), nullable=True)
    document_type = Column(String(50), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    mime_type = Column(String(100), nullable=False)
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String(500))
    
    # Relationships
    claim = relationship("ExpenseClaim", back_populates="documents")
    expense_item = relationship("ExpenseItem", back_populates="documents")

class ExpenseApproval(Base):
    __tablename__ = "expense_approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey('expense_claims.id'), nullable=False)
    approver_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    action = Column(String(20), nullable=False)  # approve, reject, pending
    remarks = Column(String(500))
    approved_amount = Column(Numeric(10, 2))
    approval_date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    claim = relationship("ExpenseClaim", back_populates="approvals")
    approver = relationship("User")

class ExpenseReimbursement(Base):
    __tablename__ = "expense_reimbursements"
    
    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey('expense_claims.id'), nullable=False, unique=True)
    reimbursement_amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String(50))
    payment_reference = Column(String(100))
    status = Column(String(20), default="pending")
    processed_by = Column(Integer, ForeignKey('users.id'))
    processed_date = Column(DateTime, default=datetime.utcnow)
    payment_date = Column(DateTime)
    notes = Column(String(500))
    
    # Relationships
    claim = relationship("ExpenseClaim", back_populates="reimbursements")
    processor = relationship("User", foreign_keys=[processed_by])

class SoftwareLicense(Base):
    __tablename__ = "software_licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    software_name = Column(String(200), nullable=False)
    vendor_name = Column(String(200), nullable=False)
    license_type = Column(String(50))  # perpetual, subscription, etc.
    purchase_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    cost = Column(Numeric(10, 2))
    is_recurring = Column(Boolean, default=False)
    recurring_cycle = Column(String(20))  # monthly, annual, etc.
    status = Column(String(20), default="active")  # active, expired, revoked
    notes = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(50), nullable=False)  # CREATE_CLAIM, APPROVE_CLAIM, etc.
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    user_name = Column(String(100))  # Store username at the time of action
    entity_type = Column(String(50), nullable=False)  # ExpenseClaim, ExpenseItem, etc.
    entity_id = Column(Integer)
    details = Column(String(500))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String(45))  # IPv4 or IPv6 address
    user_agent = Column(String(200))
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
