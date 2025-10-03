from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(50), unique=True, index=True, nullable=False)
    asset_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    brand = Column(String(50))
    model = Column(String(50))
    serial_number = Column(String(100), unique=True)
    purchase_date = Column(DateTime)
    purchase_price = Column(Float)
    warranty_period = Column(Integer)  # in months
    description = Column(Text)
    status = Column(String(50), default="available")  # available, assigned, maintenance, retired
    location = Column(String(100))
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Asset approval workflow fields
    approval_status = Column(String(20), default="pending")  # pending, approved, rejected
    provided_to_employee = Column(String(5), default="no")   # yes, no
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_user = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_assets")
    approver = relationship("User", foreign_keys=[approved_by], back_populates="approved_assets")
    asset_claims = relationship("AssetClaim", back_populates="asset", cascade="all, delete-orphan")
    status_history = relationship("AssetStatusHistory", back_populates="asset", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_code": self.asset_code,
            "asset_name": self.asset_name,
            "category": self.category,
            "brand": self.brand,
            "model": self.model,
            "serial_number": self.serial_number,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "purchase_price": self.purchase_price,
            "warranty_period": self.warranty_period,
            "description": self.description,
            "status": self.status,
            "location": self.location,
            "assigned_to": self.assigned_to,
            "approval_status": self.approval_status,
            "provided_to_employee": self.provided_to_employee,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "assigned_user_name": self.assigned_user.username if self.assigned_user else None,
            "approver_name": self.approver.username if self.approver else None
        }

class AssetStatusHistory(Base):
    __tablename__ = "asset_status_history"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    
    # Status tracking
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=False)
    previous_approval_status = Column(String(20), nullable=True)
    new_approval_status = Column(String(20), nullable=False)
    
    # Action details
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    remarks = Column(Text)
    action_type = Column(String(50), nullable=False)  # approval, rejection, provision, status_change, creation, assignment

    # Relationships
    asset = relationship("Asset", back_populates="status_history")
    changed_by_user = relationship("User", foreign_keys=[changed_by])

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "previous_status": self.previous_status,
            "new_status": self.new_status,
            "previous_approval_status": self.previous_approval_status,
            "new_approval_status": self.new_approval_status,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "remarks": self.remarks,
            "action_type": self.action_type,
            "changed_by_name": self.changed_by_user.username if self.changed_by_user else None
        }

class AssetClaim(Base):
    __tablename__ = "asset_claims"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # Claim status
    status = Column(String(50), default="pending")  # pending, approved, rejected
    claimed_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    hr_remarks = Column(Text)
    
    # Return tracking
    expected_return_date = Column(DateTime)
    actual_return_date = Column(DateTime, nullable=True)

    # Relationships
    asset = relationship("Asset", back_populates="asset_claims")
    employee = relationship("User", foreign_keys=[employee_id], back_populates="asset_claims")
    processor = relationship("User", foreign_keys=[processed_by], back_populates="processed_claims")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "employee_id": self.employee_id,
            "reason": self.reason,
            "priority": self.priority,
            "status": self.status,
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processed_by": self.processed_by,
            "hr_remarks": self.hr_remarks,
            "expected_return_date": self.expected_return_date.isoformat() if self.expected_return_date else None,
            "actual_return_date": self.actual_return_date.isoformat() if self.actual_return_date else None,
            "asset_name": self.asset.asset_name if self.asset else None,
            "asset_code": self.asset.asset_code if self.asset else None,
            "employee_name": self.employee.username if self.employee else None,
            "processor_name": self.processor.username if self.processor else None
        }

class AssetCategory(Base):
    __tablename__ = "asset_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    category_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    is_active = Column(String(5), default="yes")  # yes, no
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "category_name": self.category_name,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class AssetMaintenance(Base):
    __tablename__ = "asset_maintenance"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    maintenance_type = Column(String(50), nullable=False)  # preventive, corrective, emergency
    description = Column(Text, nullable=False)
    cost = Column(Float, default=0.0)
    
    # Maintenance status
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled
    scheduled_date = Column(DateTime)
    started_date = Column(DateTime, nullable=True)
    completed_date = Column(DateTime, nullable=True)
    
    # Personnel
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    vendor_name = Column(String(100))
    vendor_contact = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    asset = relationship("Asset", foreign_keys=[asset_id])
    assigned_user = relationship("User", foreign_keys=[assigned_to])

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "maintenance_type": self.maintenance_type,
            "description": self.description,
            "cost": self.cost,
            "status": self.status,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "started_date": self.started_date.isoformat() if self.started_date else None,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
            "assigned_to": self.assigned_to,
            "vendor_name": self.vendor_name,
            "vendor_contact": self.vendor_contact,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "asset_name": self.asset.asset_name if self.asset else None,
            "asset_code": self.asset.asset_code if self.asset else None,
            "assigned_user_name": self.assigned_user.username if self.assigned_user else None
        }

class AssetTransfer(Base):
    __tablename__ = "asset_transfers"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    from_employee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    to_employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transfer_reason = Column(Text, nullable=False)
    
    # Transfer status
    status = Column(String(50), default="pending")  # pending, approved, completed, rejected
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Dates
    requested_date = Column(DateTime, default=datetime.utcnow)
    approved_date = Column(DateTime, nullable=True)
    transfer_date = Column(DateTime, nullable=True)
    
    # Additional details
    remarks = Column(Text)

    # Relationships
    asset = relationship("Asset", foreign_keys=[asset_id])
    from_employee = relationship("User", foreign_keys=[from_employee_id])
    to_employee = relationship("User", foreign_keys=[to_employee_id])
    requester = relationship("User", foreign_keys=[requested_by])
    approver = relationship("User", foreign_keys=[approved_by])

    def to_dict(self):
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "from_employee_id": self.from_employee_id,
            "to_employee_id": self.to_employee_id,
            "transfer_reason": self.transfer_reason,
            "status": self.status,
            "requested_by": self.requested_by,
            "approved_by": self.approved_by,
            "requested_date": self.requested_date.isoformat() if self.requested_date else None,
            "approved_date": self.approved_date.isoformat() if self.approved_date else None,
            "transfer_date": self.transfer_date.isoformat() if self.transfer_date else None,
            "remarks": self.remarks,
            "asset_name": self.asset.asset_name if self.asset else None,
            "asset_code": self.asset.asset_code if self.asset else None,
            "from_employee_name": self.from_employee.username if self.from_employee else None,
            "to_employee_name": self.to_employee.username if self.to_employee else None,
            "requester_name": self.requester.username if self.requester else None,
            "approver_name": self.approver.username if self.approver else None
        }
