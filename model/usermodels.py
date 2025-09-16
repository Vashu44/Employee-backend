from sqlalchemy import Column, Integer, String, DateTime
from db.database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(50), unique=True, index=True)
    password = Column(String(100))
    is_verified = Column(Integer, default=0)
    role = Column(String(10), nullable=False)  # e.g., 'admin', 'user', 'manager'
    last_login = Column(DateTime, default=None)

    user_details = relationship("UserDetails", back_populates="user", uselist=False)
    timesheets = relationship("Timesheet", back_populates="user", cascade="all,save-update, delete")
    moms_created = relationship("MoM", back_populates="user", cascade="all, save-update, delete")
    queries = relationship("Query", back_populates="user", cascade="all, save-update, delete")
    appreciations_received = relationship("Appreciation", foreign_keys="[Appreciation.employee_id]", back_populates="employee", cascade="all, save-update, delete")
    appreciations_given = relationship("Appreciation", foreign_keys="[Appreciation.given_by_id]", back_populates="given_by", cascade="all, save-update, delete")
    
    # Expense management relationships
    expense_claims = relationship("ExpenseClaim", foreign_keys="[ExpenseClaim.employee_id]", back_populates="user")
    approved_claims = relationship("ExpenseClaim", foreign_keys="[ExpenseClaim.approver_id]", back_populates="approver")
    expense_approvals = relationship("ExpenseApproval", foreign_keys="[ExpenseApproval.approver_id]", back_populates="approver")
    expense_reimbursements = relationship("ExpenseReimbursement", foreign_keys="[ExpenseReimbursement.processed_by]", back_populates="processor")
    software_licenses = relationship("SoftwareLicense", back_populates="user")
