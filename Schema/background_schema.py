from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Optional
from datetime import date, datetime

class VerificationChecks(BaseModel):
    address_verification: Optional[bool] = None
    education_verification: Optional[bool] = None
    employment_verification: Optional[bool] = None
    criminal_record_check: Optional[bool] = None

class EducationDetail(BaseModel):
    institution_name: str
    degree: str
    year_of_passing: int

class HRDetail(BaseModel):
    hr_name: str
    hr_contact_number: int
    hr_email_id: EmailStr

    @field_validator('hr_contact_number')
    @classmethod
    def validate_hr_contact_number_format(cls, v):
        if v is not None:
            # Convert to string for validation if it's an integer
            v_str = str(v) if isinstance(v, int) else v
            if not v_str.isdigit() or len(v_str) != 10:
                raise ValueError('HR contact number must be a 10-digit numeric value.')
        return v

class ReferenceDetail(BaseModel):
    ref_name: str
    ref_contact_number: int
    ref_email_id: EmailStr

    @field_validator('ref_contact_number')
    @classmethod
    def validate_ref_contact_number_format(cls, v):
        if v is not None:
            # Convert to string for validation if it's an integer
            v_str = str(v) if isinstance(v, int) else v
            if not v_str.isdigit() or len(v_str) != 10:
                raise ValueError('Reference contact number must be a 10-digit numeric value.')
        return v

# New schema for detailed approved form response
class ApprovedFormDetailResponse(BaseModel):
    """
    Detailed response schema for approved forms containing all form data
    """
    id: int
    # Personal Information
    candidate_name: Optional[str] = None
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    marital_status: Optional[str] = None
    email_id: Optional[EmailStr] = None
    contact_number: Optional[int] = None
    alternate_contact_number: Optional[int] = None
    aadhaar_card_number: Optional[int] = None
    pan_number: Optional[str] = None
    uan_number: Optional[str] = None

    # Current Address
    current_complete_address: Optional[str] = None
    current_landmark: Optional[str] = None
    current_city: Optional[str] = None
    current_state: Optional[str] = None
    current_pin_code: Optional[int] = None
    current_police_station: Optional[str] = None
    current_duration_from: Optional[str] = None
    current_duration_to: Optional[str] = None

    # Permanent Address
    permanent_complete_address: Optional[str] = None
    permanent_landmark: Optional[str] = None
    permanent_city: Optional[str] = None
    permanent_state: Optional[str] = None
    permanent_pin_code: Optional[int] = None
    permanent_police_station: Optional[str] = None
    permanent_duration_from: Optional[str] = None
    permanent_duration_to: Optional[str] = None

    # Employment Details
    organization_name: Optional[str] = None
    organization_address: Optional[str] = None
    designation: Optional[str] = None
    employee_code: Optional[str] = None
    date_of_joining: Optional[date] = None
    last_working_day: Optional[date] = None
    salary: Optional[int] = None
    reason_for_leaving: Optional[str] = None

    # Manager Details
    manager_name: Optional[str] = None
    manager_contact_number: Optional[int] = None
    manager_email_id: Optional[str] = None

    # JSON fields
    education_details: Optional[List[dict]] = None
    hr_details: Optional[List[dict]] = None
    reference_details: Optional[List[dict]] = None
    verification_checks: Optional[dict] = None

    # Authorization
    candidate_name_auth: Optional[str] = None
    signature: Optional[str] = None
    auth_date: Optional[str] = None
    acknowledgment: Optional[bool] = None

    # Status and timestamps
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    remarks: Optional[str] = None

    class Config:
        from_attributes = True

class ProfileUpdateSchema(BaseModel):
    # Personal Information - all optional for updates
    candidateName: Optional[str] = None
    fatherName: Optional[str] = None
    motherName: Optional[str] = None
    dateOfBirth: Optional[date] = None
    maritalStatus: Optional[str] = None
    emailId: Optional[EmailStr] = None
    contactNumber: Optional[int] = None
    alternateContactNumber: Optional[int] = None
    aadhaarCardNumber: Optional[int] = None
    panNumber: Optional[str] = None
    uanNumber: Optional[int] = None

    # Current Address
    currentCompleteAddress: Optional[str] = None
    currentLandmark: Optional[str] = None
    currentCity: Optional[str] = None
    currentState: Optional[str] = None
    currentPinCode: Optional[int] = None
    currentPoliceStation: Optional[str] = None
    currentDurationFrom: Optional[date] = None
    currentDurationTo: Optional[date] = None

    # Permanent Address
    permanentCompleteAddress: Optional[str] = None
    permanentLandmark: Optional[str] = None
    permanentCity: Optional[str] = None
    permanentState: Optional[str] = None
    permanentPinCode: Optional[int] = None
    permanentPoliceStation: Optional[str] = None
    permanentDurationFrom: Optional[date] = None
    permanentDurationTo: Optional[date] = None

    # Employment Details
    organizationName: Optional[str] = None
    organizationAddress: Optional[str] = None
    designation: Optional[str] = None
    employeeCode: Optional[str] = None
    dateOfJoining: Optional[date] = None
    lastWorkingDay: Optional[date] = None
    salary: Optional[int] = None
    reasonForLeaving: Optional[str] = None

    # Manager Details
    managerName: Optional[str] = None
    managerContactNumber: Optional[int] = None
    managerEmailId: Optional[EmailStr] = None

    # JSON fields - make them Optional and default to None
    educationDetails: Optional[List[EducationDetail]] = None
    hrDetails: Optional[List[HRDetail]] = None
    referenceDetails: Optional[List[ReferenceDetail]] = None
    verificationChecks: Optional[VerificationChecks] = None

    # Authorization
    candidateNameAuth: Optional[str] = None
    signature: Optional[str] = None
    authDate: Optional[date] = None
    acknowledgment: Optional[bool] = None

    # Validators for ProfileUpdateSchema (similar to BackgroundCheckFormCreate, but all fields are optional)
    @field_validator('contactNumber', 'alternateContactNumber', 'managerContactNumber')
    @classmethod
    def validate_phone_numbers_format(cls, v):
        if v is not None:
            if not isinstance(v, str) or not v.isdigit() or len(v) != 10:
                raise ValueError(f'Phone number must be a 10-digit numeric string.')
        return v

    @field_validator('aadhaarCardNumber')
    @classmethod
    def validate_aadhaar(cls, v):
        if v is not None:
            if not isinstance(v, str) or not v.isdigit() or len(v) != 12:
                raise ValueError('Aadhaar card number must be a 12-digit numeric value.')
        return v

    @field_validator('panNumber')
    @classmethod
    def validate_pan(cls, v):
        if v is not None:
            if not isinstance(v, str) or not (len(v) == 10 and v[:5].isalpha() and v[5:9].isdigit() and v[9].isalpha()):
                raise ValueError('PAN number must be a 10-character alphanumeric value (e.g., ABCDE1234F).')
        return v

    @field_validator('currentPinCode', 'permanentPinCode')
    @classmethod
    def validate_pincode(cls, v):
        if v is not None:
            # Convert to string for validation if it's an integer
            v_str = str(v) if isinstance(v, int) else v
            if not v_str.isdigit() or len(v_str) != 6:
                raise ValueError('PIN code must be a 6-digit numeric value.')
        return v

class BackgroundCheckFormCreate(BaseModel):
    # Personal Information
    candidateName: str
    fatherName: Optional[str] = None
    motherName: Optional[str] = None
    dateOfBirth: Optional[date] = None
    maritalStatus: Optional[str] = None
    emailId: EmailStr
    contactNumber: int
    alternateContactNumber: Optional[int] = None
    aadhaarCardNumber: Optional[int] = None
    panNumber: Optional[str] = None
    uanNumber: Optional[int] = None

    # Current Address
    currentCompleteAddress: Optional[str] = None
    currentLandmark: Optional[str] = None
    currentCity: Optional[str] = None
    currentState: Optional[str] = None
    currentPinCode: Optional[int] = None
    currentPoliceStation: Optional[str] = None
    currentDurationFrom: Optional[date] = None
    currentDurationTo: Optional[date] = None

    # Permanent Address
    permanentCompleteAddress: Optional[str] = None
    permanentLandmark: Optional[str] = None
    permanentCity: Optional[str] = None
    permanentState: Optional[str] = None
    permanentPinCode: Optional[int] = None
    permanentPoliceStation: Optional[str] = None
    permanentDurationFrom: Optional[date] = None
    permanentDurationTo: Optional[date] = None

    # Employment Details
    organizationName: Optional[str] = None
    organizationAddress: Optional[str] = None
    designation: Optional[str] = None
    employeeCode: Optional[str] = None
    dateOfJoining: Optional[date] = None
    lastWorkingDay: Optional[date] = None
    salary: Optional[int] = None
    reasonForLeaving: Optional[str] = None

    # Manager Details
    managerName: Optional[str] = None
    managerContactNumber: Optional[int] = None
    managerEmailId: Optional[EmailStr] = None

    # JSON fields - Make them Optional[List[...]] = None
    educationDetails: Optional[List[EducationDetail]] = None
    hrDetails: Optional[List[HRDetail]] = None
    referenceDetails: Optional[List[ReferenceDetail]] = None
    verificationChecks: Optional[VerificationChecks] = None

    # Authorization
    candidateNameAuth: Optional[str] = None
    signature: Optional[str] = None
    authDate: Optional[date] = None
    acknowledgment: Optional[bool] = None

    # Use @field_validator for Pydantic V2
    @field_validator('contactNumber', 'alternateContactNumber', 'managerContactNumber')
    @classmethod
    def validate_phone_numbers_format(cls, v):
        if v is not None:
            # Convert to string for validation if it's an integer
            v_str = str(v) if isinstance(v, int) else v
            if not v_str.isdigit() or len(v_str) != 10:
                raise ValueError(f'Phone number must be a 10-digit numeric value.')
        return v

    @field_validator('aadhaarCardNumber')
    @classmethod
    def validate_aadhaar(cls, v):
        if v is not None:
            # Convert to string for validation if it's an integer
            v_str = str(v) if isinstance(v, int) else v
            if not v_str.isdigit() or len(v_str) != 12:
                raise ValueError('Aadhaar card number must be a 12-digit numeric value.')
        return v

    @field_validator('panNumber')
    @classmethod
    def validate_pan(cls, v):
        if v is not None:
            if not isinstance(v, str) or not (len(v) == 10 and v[:5].isalpha() and v[5:9].isdigit() and v[9].isalpha()):
                raise ValueError('PAN number must be a 10-character alphanumeric value (e.g., ABCDE1234F).')
        return v

    @field_validator('currentPinCode', 'permanentPinCode')
    @classmethod
    def validate_pincode(cls, v):
        if v is not None:
            # Convert to string for validation if it's an integer
            v_str = str(v) if isinstance(v, int) else v
            if not v_str.isdigit() or len(v_str) != 6:
                raise ValueError('PIN code must be a 6-digit numeric value.')
        return v

class BackgroundCheckFormResponse(BaseModel):
    id: int
    candidate_name: str = Field(alias="candidateName")
    email_id: EmailStr = Field(alias="emailId")
    contact_number: int = Field(alias="contactNumber")
    created_at: datetime
    status: str

    class Config:
        from_attributes = True
        populate_by_name = True

__all__ = [
    'BackgroundCheckFormCreate',
    'BackgroundCheckFormResponse',
    'ApprovedFormDetailResponse',  # Added new schema
    'ProfileUpdateSchema',
    'VerificationChecks',
    'EducationDetail',
    'HRDetail',
    'ReferenceDetail'
]