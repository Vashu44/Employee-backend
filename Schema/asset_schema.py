
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum
# Asset Status Update Schema
class AssetStatusUpdate(BaseModel):
    approval_status: str  # 'pending', 'approved', 'rejected'
    provided_to_employee: Optional[str] = None  # 'yes' or 'no'
    remarks: Optional[str] = None
    changed_by: int

# Asset Status History Response
class AssetStatusHistoryResponse(BaseModel):
    id: int
    asset_id: int
    status: str
    changed_by: int
    changed_at: datetime
    remarks: Optional[str] = None
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class CaseInsensitiveEnum(str, Enum):
    """Base class for case-insensitive string enums"""
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive enum lookup"""
        if isinstance(value, str):
            value_lower = value.lower()
            for member in cls:
                if member.value.lower() == value_lower:
                    return member
        return None
    
class AssetCategoryEnum(CaseInsensitiveEnum):
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    MONITOR = "monitor"
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    HEADPHONE = "headphone"
    MOBILE = "mobile"
    TABLET = "tablet"
    SOFTWARE_LICENSE = "software_license"
    PRINTER = "printer"
    ROUTER = "router"
    SWITCH = "switch"
    UPS = "ups"
    OTHER = "other"

class AssetStatusEnum(CaseInsensitiveEnum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"

class ClaimStatusEnum(CaseInsensitiveEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class PriorityEnum(CaseInsensitiveEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

# Asset Schemas
class AssetCreate(BaseModel):
    asset_code: str
    asset_name: str
    category: AssetCategoryEnum
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    warranty_period: Optional[int] = None
    description: Optional[str] = None
    location: Optional[str] = None

class AssetUpdate(BaseModel):
    asset_code: Optional[str] = None
    asset_name: Optional[str] = None
    category: Optional[AssetCategoryEnum] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    warranty_period: Optional[int] = None
    description: Optional[str] = None
    location: Optional[str] = None

class AssetResponse(BaseModel):
    id: int
    asset_code: str
    asset_name: str
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    warranty_period: Optional[int] = None
    description: Optional[str] = None
    status: str
    location: Optional[str] = None
    assigned_to: Optional[int] = None
    assigned_user_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Asset Claim Schemas
class AssetClaimCreate(BaseModel):
    asset_id: int
    reason: str
    priority: Optional[PriorityEnum] = PriorityEnum.NORMAL
    expected_return_date: Optional[datetime] = None

class AssetClaimProcess(BaseModel):
    status: ClaimStatusEnum
    hr_remarks: Optional[str] = None

class AssetClaimResponse(BaseModel):
    id: int
    asset_id: int
    asset_name: Optional[str] = None
    asset_code: Optional[str] = None
    employee_id: int
    employee_name: Optional[str] = None
    reason: str
    priority: str
    status: str
    claimed_at: datetime
    processed_at: Optional[datetime] = None
    processed_by: Optional[int] = None
    processor_name: Optional[str] = None
    hr_remarks: Optional[str] = None
    expected_return_date: Optional[datetime] = None
    actual_return_date: Optional[datetime] = None

# Add these new enums
class ApprovalStatusEnum(CaseInsensitiveEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ProvisionStatusEnum(CaseInsensitiveEnum):
    YES = "yes"
    NO = "no"

class ActionTypeEnum(CaseInsensitiveEnum):
    APPROVAL = "approval"
    REJECTION = "rejection"
    PROVISION = "provision"
    STATUS_CHANGE = "status_change"

# Asset Status Update Schema
class AssetStatusUpdate(BaseModel):
    approval_status: ApprovalStatusEnum
    provided_to_employee: Optional[ProvisionStatusEnum] = None
    remarks: Optional[str] = None
    changed_by: int

# Asset Approval Schema
class AssetApprovalRequest(BaseModel):
    approval_status: ApprovalStatusEnum
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None

# Asset Provision Schema
class AssetProvisionRequest(BaseModel):
    provided_to_employee: ProvisionStatusEnum
    remarks: Optional[str] = None

# Asset Status History Response
class AssetStatusHistoryResponse(BaseModel):
    id: int
    asset_id: int
    previous_status: Optional[str] = None
    new_status: str
    previous_approval_status: Optional[str] = None
    new_approval_status: str
    changed_by: int
    changed_by_name: Optional[str] = None
    changed_at: datetime
    remarks: Optional[str] = None
    action_type: str

# Enhanced Asset Response
class AssetDetailedResponse(BaseModel):
    id: int
    asset_code: str
    asset_name: str
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    warranty_period: Optional[int] = None
    description: Optional[str] = None
    status: str
    location: Optional[str] = None
    assigned_to: Optional[int] = None
    assigned_user_name: Optional[str] = None
    approval_status: str
    provided_to_employee: str
    approved_by: Optional[int] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Keep your existing schemas and add these new ones
