from fastapi import APIRouter, Depends, HTTPException,status
from fastapi.responses import StreamingResponse
from sqlalchemy import Date as SQLADate
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date
from model.background_model import BackgroundCheckForm
from fastapi.responses import StreamingResponse
from io import BytesIO
from xhtml2pdf import pisa
from Schema.background_schema import (
    BackgroundCheckFormCreate,
    BackgroundCheckFormResponse,
    EducationDetail, 
    HRDetail,
    ReferenceDetail,
    VerificationChecks
)
from db.database import get_db

router = APIRouter(
    prefix="/api/background-check",
)

# Pydantic model for approval request
class ApprovalRequest(BaseModel):
    action: str  # "approve" or "reject"
    remarks: str = None  # Optional remarks for approval/rejection

# Pydantic model for draft data (all fields optional)
class DraftRequest(BaseModel):
    # Personal Information
    candidateName: Optional[str] = None
    fatherName: Optional[str] = None
    motherName: Optional[str] = None
    dateOfBirth: Optional[date] = None
    maritalStatus: Optional[str] = None
    emailId: Optional[str] = None
    contactNumber: Optional[int] = None
    alternateContactNumber: Optional[int] = None
    aadhaarCardNumber: Optional[int] = None
    panNumber: Optional[str] = None
    uanNumber: Optional[str] = None

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
    salary: Optional[float] = None
    reasonForLeaving: Optional[str] = None

    # Manager Details
    managerName: Optional[str] = None
    managerContactNumber: Optional[int] = None
    managerEmailId: Optional[str] = None

    # JSON fields - Use actual Pydantic models for nested data
    educationDetails: Optional[List[EducationDetail]] = None
    hrDetails: Optional[List[HRDetail]] = None
    referenceDetails: Optional[List[ReferenceDetail]] = None
    verificationChecks: Optional[VerificationChecks] = None

    # Authorization
    candidateNameAuth: Optional[str] = None
    signature: Optional[str] = None
    authDate: Optional[str] = None
    acknowledgment: Optional[bool] = None

class DraftResponse(BaseModel):
    id: int
    candidate_name: Optional[str]
    email_id: Optional[str]
    contact_number: Optional[int]
    created_at: datetime
    updated_at: datetime
    status: str

# Helper function to safely convert Pydantic models or dicts to dict
def safe_model_dump(obj):
    """
    Safely convert Pydantic model or dict to dict
    """
    if obj is None:
        return None
    if hasattr(obj, 'model_dump'):
        return obj.model_dump()
    elif isinstance(obj, dict):
        return obj
    else:
        # If it's a list, process each item
        if isinstance(obj, list):
            return [safe_model_dump(item) for item in obj]
        return obj

# New Health Check API
@router.get("/health")
async def health_check():
    """
    Health check endpoint to verify backend connectivity.
    """
    return {"status": "ok", "message": "Backend is healthy"}

@router.post("/save-draft")
async def save_draft(
    draft_data: DraftRequest,
    user_id: Optional[int] = None,  # You can make this required based on your auth system
    db: Session = Depends(get_db)
):
    """
    Save draft data for a background check form.
    If a draft already exists for the user, it updates the existing draft.
    """
    try:
        # Check if a draft already exists for this user/email
        existing_draft = None
        if draft_data.emailId:
            existing_draft = db.query(BackgroundCheckForm).filter(
                BackgroundCheckForm.email_id == draft_data.emailId,
                BackgroundCheckForm.status == "draft"
            ).first()
        
        if existing_draft:
            # Update existing draft
            for field, value in draft_data.model_dump(exclude_unset=True).items():
                # Convert camelCase to snake_case for database fields
                db_field = ''.join(['_' + c.lower() if c.isupper() else c for c in field]).lstrip('_')
                if hasattr(existing_draft, db_field) and value is not None:
                    # Special handling for JSON fields that are Pydantic models
                    if db_field == "education_details" and value is not None:
                        setattr(existing_draft, db_field, [safe_model_dump(item) for item in value])
                    elif db_field == "hr_details" and value is not None:
                        setattr(existing_draft, db_field, [safe_model_dump(item) for item in value])
                    elif db_field == "reference_details" and value is not None:
                        setattr(existing_draft, db_field, [safe_model_dump(item) for item in value])
                    elif db_field == "verification_checks" and value is not None:
                        setattr(existing_draft, db_field, safe_model_dump(value))
                    else:
                        setattr(existing_draft, db_field, value)
            
            existing_draft.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_draft)
            
            return {
                "message": "Draft updated successfully",
                "draft_id": existing_draft.id,
                "status": "draft"
            }
        else:
            # Create new draft
            db_draft = BackgroundCheckForm(
                # Personal Information
                candidate_name=draft_data.candidateName,
                father_name=draft_data.fatherName,
                mother_name=draft_data.motherName,
                date_of_birth=draft_data.dateOfBirth,
                marital_status=draft_data.maritalStatus,
                email_id=draft_data.emailId,
                contact_number=draft_data.contactNumber,
                alternate_contact_number=draft_data.alternateContactNumber,
                aadhaar_card_number=draft_data.aadhaarCardNumber,
                pan_number=draft_data.panNumber,
                uan_number=draft_data.uanNumber,

                # Current Address
                current_complete_address=draft_data.currentCompleteAddress,
                current_landmark=draft_data.currentLandmark,
                current_city=draft_data.currentCity,
                current_state=draft_data.currentState,
                current_pin_code=draft_data.currentPinCode,
                current_police_station=draft_data.currentPoliceStation,
                current_duration_from=draft_data.currentDurationFrom,
                current_duration_to=draft_data.currentDurationTo,

                # Permanent Address
                permanent_complete_address=draft_data.permanentCompleteAddress,
                permanent_landmark=draft_data.permanentLandmark,
                permanent_city=draft_data.permanentCity,
                permanent_state=draft_data.permanentState,
                permanent_pin_code=draft_data.permanentPinCode,
                permanent_police_station=draft_data.permanentPoliceStation,
                permanent_duration_from=draft_data.permanentDurationFrom,
                permanent_duration_to=draft_data.permanentDurationTo,

                # Employment Details
                organization_name=draft_data.organizationName,
                organization_address=draft_data.organizationAddress,
                designation=draft_data.designation,
                employee_code=draft_data.employeeCode,
                date_of_joining=draft_data.dateOfJoining,
                last_working_day=draft_data.lastWorkingDay,
                salary=draft_data.salary,
                reason_for_leaving=draft_data.reasonForLeaving,

                # Manager Details
                manager_name=draft_data.managerName,
                manager_contact_number=draft_data.managerContactNumber,  # Fixed field reference
                manager_email_id=draft_data.managerEmailId,

                # JSON fields - Convert Pydantic models to dictionaries safely
                education_details=[safe_model_dump(ed) for ed in draft_data.educationDetails] if draft_data.educationDetails else [],
                hr_details=[safe_model_dump(hr) for hr in draft_data.hrDetails] if draft_data.hrDetails else [],
                reference_details=[safe_model_dump(ref) for ref in draft_data.referenceDetails] if draft_data.referenceDetails else [],
                verification_checks=safe_model_dump(draft_data.verificationChecks) if draft_data.verificationChecks else {},
                
                # Authorization
                candidate_name_auth=draft_data.candidateNameAuth,
                signature=draft_data.signature,
                auth_date=draft_data.authDate,
                acknowledgment=draft_data.acknowledgment,
                
                # Set status as draft
                status="draft"
            )
            db.add(db_draft)
            db.commit()
            db.refresh(db_draft)

            return {
                "message": "Draft saved successfully",
                "draft_id": db_draft.id,
                "status": "draft"
            }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving draft: {str(e)}")


@router.get("/forms/approved/{form_id}")
async def get_approved_form_by_id(form_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific approved background check form by its ID.
    Returns the full approved form data directly, or 404 if not found or not approved.
    """
    try:
        form = db.query(BackgroundCheckForm).filter(
            BackgroundCheckForm.id == form_id,
            BackgroundCheckForm.status == "approved"
        ).first()
        
        if not form:
            raise HTTPException(
                status_code=404, 
                detail="Approved form not found with the given ID"
            )
        
        # Return the dictionary representation for consistency with frontend
        return form.to_dict()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving approved form: {str(e)}")


@router.get("/get-draft/{email_id}")
async def get_draft_by_email(email_id: str, db: Session = Depends(get_db)):
    """
    Retrieve draft data by email ID.
    Returns the full draft data directly, or 404 if not found.
    """
    try:
        draft = db.query(BackgroundCheckForm).filter(
            BackgroundCheckForm.email_id == email_id,
            BackgroundCheckForm.status == "draft"
        ).first()
        
        if not draft:
            # Return 404 if no draft is found, as expected by the frontend
            raise HTTPException(status_code=404, detail="No draft found for this email.")
        
        # Return the dictionary representation of the draft directly
        return draft.to_dict()
    except HTTPException as e:
        raise e # Re-raise HTTPException directly
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving draft: {str(e)}")


@router.get("/drafts", response_model=List[DraftResponse])
async def get_all_drafts(db: Session = Depends(get_db)):
    """
    Get all draft forms
    """
    try:
        drafts = db.query(BackgroundCheckForm).filter(BackgroundCheckForm.status == "draft").all()
        return [
            DraftResponse(
                id=draft.id,
                candidate_name=draft.candidate_name,
                email_id=draft.email_id,
                contact_number=draft.contact_number,
                created_at=draft.created_at,
                updated_at=getattr(draft, 'updated_at', draft.created_at),
                status=draft.status
            ) for draft in drafts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving drafts: {str(e)}")


@router.delete("/draft/{draft_id}")
async def delete_draft(draft_id: int, db: Session = Depends(get_db)):
    """
    Delete a draft form
    """
    try:
        draft = db.query(BackgroundCheckForm).filter(
            BackgroundCheckForm.id == draft_id,
            BackgroundCheckForm.status == "draft"
        ).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")

        db.delete(draft)
        db.commit()
        return {"message": "Draft deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting draft: {str(e)}")


@router.post("/submit-from-draft/{draft_id}", response_model=BackgroundCheckFormResponse)
async def submit_from_draft(
    draft_id: int,
    form_data: BackgroundCheckFormCreate, # Changed to form_data to match submit endpoint
    db: Session = Depends(get_db)
):
    """
    Submit a draft as a complete form. This will change the status from 'draft' to 'pending'
    and clear any other drafts for the same email.
    """
    try:
        # Find the draft
        draft = db.query(BackgroundCheckForm).filter(
            BackgroundCheckForm.id == draft_id,
            BackgroundCheckForm.status == "draft"
        ).first()
        
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        # Update with new data from the form_data
        for field, value in form_data.model_dump(exclude_unset=True).items():
            # Convert camelCase to snake_case for database fields
            db_field = ''.join(['_' + c.lower() if c.isupper() else c for c in field]).lstrip('_')
            if hasattr(draft, db_field):
                # Special handling for JSON fields that are Pydantic models in schema
                if db_field == "education_details" and value is not None:
                    setattr(draft, db_field, [safe_model_dump(item) for item in value])
                elif db_field == "hr_details" and value is not None:
                    setattr(draft, db_field, [safe_model_dump(item) for item in value])
                elif db_field == "reference_details" and value is not None:
                    setattr(draft, db_field, [safe_model_dump(item) for item in value])
                elif db_field == "verification_checks" and value is not None:
                    setattr(draft, db_field, safe_model_dump(value))
                else:
                    setattr(draft, db_field, value)
        
        # Change status to pending
        draft.status = "pending"
        draft.updated_at = datetime.utcnow()
        
        # Delete any other drafts for the same email to keep it clean
        if draft.email_id:
            other_drafts = db.query(BackgroundCheckForm).filter(
                BackgroundCheckForm.email_id == draft.email_id,
                BackgroundCheckForm.status == "draft",
                BackgroundCheckForm.id != draft_id
            ).all()
            for other_draft in other_drafts:
                db.delete(other_draft)
        
        db.commit()
        db.refresh(draft)

        return BackgroundCheckFormResponse(
            id=draft.id,
            candidate_name=draft.candidate_name,
            email_id=draft.email_id,
            contact_number=draft.contact_number,
            created_at=draft.created_at,
            status=draft.status # Ensure status is returned
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting draft: {str(e)}")


# Modified /submit endpoint to handle upsert logic for submitted forms
@router.post("/submit", response_model=BackgroundCheckFormResponse)
async def submit_background_check(
    form_data: BackgroundCheckFormCreate,
    db: Session = Depends(get_db)
):
    try:
        # Check if a non-draft form already exists for this email
        existing_submitted_form = None
        if form_data.emailId:
            existing_submitted_form = db.query(BackgroundCheckForm).filter(
                BackgroundCheckForm.email_id == form_data.emailId,
                BackgroundCheckForm.status != "draft" # Look for any non-draft form
            ).first()

        if existing_submitted_form:
            # If a non-draft form exists, update it
            for field, value in form_data.model_dump(exclude_unset=True).items():
                db_field = ''.join(['_' + c.lower() if c.isupper() else c for c in field]).lstrip('_')
                if hasattr(existing_submitted_form, db_field):
                    # Special handling for JSON fields that are Pydantic models in schema
                    if db_field == "education_details" and value is not None:
                        setattr(existing_submitted_form, db_field, [safe_model_dump(item) for item in value])
                    elif db_field == "hr_details" and value is not None:
                        setattr(existing_submitted_form, db_field, [safe_model_dump(item) for item in value])
                    elif db_field == "reference_details" and value is not None:
                        setattr(existing_submitted_form, db_field, [safe_model_dump(item) for item in value])
                    elif db_field == "verification_checks" and value is not None:
                        setattr(existing_submitted_form, db_field, safe_model_dump(value))
                    else:
                        setattr(existing_submitted_form, db_field, value)
            
            # Set status to pending if it was previously rejected, or keep it if it was pending/approved
            if existing_submitted_form.status == "rejected":
                existing_submitted_form.status = "pending"
            
            existing_submitted_form.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_submitted_form)

            # Delete any existing drafts for this email after successful update
            if form_data.emailId:
                existing_drafts = db.query(BackgroundCheckForm).filter(
                    BackgroundCheckForm.email_id == form_data.emailId,
                    BackgroundCheckForm.status == "draft"
                ).all()
                for draft in existing_drafts:
                    db.delete(draft)
                db.commit() # Commit deletions

            return BackgroundCheckFormResponse(
                id=existing_submitted_form.id,
                candidate_name=existing_submitted_form.candidate_name,
                email_id=existing_submitted_form.email_id,
                contact_number=existing_submitted_form.contact_number,
                created_at=existing_submitted_form.created_at,
                status=existing_submitted_form.status
            )
        else:
            # No existing non-draft form, create a new one
            # Delete any existing drafts for this email before submitting new form
            if form_data.emailId:
                existing_drafts = db.query(BackgroundCheckForm).filter(
                    BackgroundCheckForm.email_id == form_data.emailId,
                    BackgroundCheckForm.status == "draft"
                ).all()
                for draft in existing_drafts:
                    db.delete(draft)
                db.commit() # Commit deletions

            db_form = BackgroundCheckForm(
                # Personal Information
                candidate_name=form_data.candidateName,
                father_name=form_data.fatherName,
                mother_name=form_data.motherName,
                date_of_birth=form_data.dateOfBirth,
                marital_status=form_data.maritalStatus,
                email_id=form_data.emailId,
                contact_number=form_data.contactNumber,
                alternate_contact_number=form_data.alternateContactNumber,
                aadhaar_card_number=form_data.aadhaarCardNumber,
                pan_number=form_data.panNumber,
                uan_number=form_data.uanNumber,

                # Current Address
                current_complete_address=form_data.currentCompleteAddress,
                current_landmark=form_data.currentLandmark,
                current_city=form_data.currentCity,
                current_state=form_data.currentState,
                current_pin_code=form_data.currentPinCode,
                current_police_station=form_data.currentPoliceStation,
                current_duration_from=form_data.currentDurationFrom,
                current_duration_to=form_data.currentDurationTo,

                # Permanent Address
                permanent_complete_address=form_data.permanentCompleteAddress,
                permanent_landmark=form_data.permanentLandmark,
                permanent_city=form_data.permanentCity,
                permanent_state=form_data.permanentState,
                permanent_pin_code=form_data.permanentPinCode,
                permanent_police_station=form_data.permanentPoliceStation,
                permanent_duration_from=form_data.permanentDurationFrom,
                permanent_duration_to=form_data.permanentDurationTo,

                # Employment Details
                organization_name=form_data.organizationName,
                organization_address=form_data.organizationAddress,
                designation=form_data.designation,
                employee_code=form_data.employeeCode,
                date_of_joining=form_data.dateOfJoining,
                last_working_day=form_data.lastWorkingDay,
                salary=form_data.salary,
                reason_for_leaving=form_data.reasonForLeaving,

                # Manager Details
                manager_name=form_data.managerName,
                manager_contact_number=form_data.managerContactNumber,
                manager_email_id=form_data.managerEmailId,

                # JSON fields - Convert Pydantic models to dictionaries safely
                education_details=[safe_model_dump(ed) for ed in form_data.educationDetails] if form_data.educationDetails else [],
                hr_details=[safe_model_dump(hr) for hr in form_data.hrDetails] if form_data.hrDetails else [],
                reference_details=[safe_model_dump(ref) for ref in form_data.referenceDetails] if form_data.referenceDetails else [],
                verification_checks=safe_model_dump(form_data.verificationChecks) if form_data.verificationChecks else {},

                # Authorization
                candidate_name_auth=form_data.candidateNameAuth,
                signature=form_data.signature,
                auth_date=form_data.authDate,
                acknowledgment=form_data.acknowledgment,
                
                # Set initial status as pending
                status="pending"
            )
            db.add(db_form)
            db.commit()
            db.refresh(db_form)

            return BackgroundCheckFormResponse(
                id=db_form.id,
                candidate_name=db_form.candidate_name,
                email_id=db_form.email_id,
                contact_number=db_form.contact_number,
                created_at=db_form.created_at,
                status=db_form.status # Ensure status is returned
            )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting form: {str(e)}")


@router.get("/forms", response_model=List[BackgroundCheckFormResponse])
async def get_all_forms(db: Session = Depends(get_db)):
    try:
        forms = db.query(BackgroundCheckForm).filter(BackgroundCheckForm.status != "draft").all()
        return [
            BackgroundCheckFormResponse(
                id=form.id,
                candidate_name=form.candidate_name,
                email_id=form.email_id,
                contact_number=form.contact_number,
                created_at=form.created_at,
                status=getattr(form, 'status', 'pending')
            ) for form in forms
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving forms: {str(e)}")


@router.get("/form/{form_id}")
async def get_form_by_id(form_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a background check form by its ID.
    Returns the full form data directly, or 404 if not found.
    """
    try:
        form = db.query(BackgroundCheckForm).filter(BackgroundCheckForm.id == form_id).first()
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")
        # Return the dictionary representation for consistency with frontend
        return form.to_dict()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving form: {str(e)}")


@router.get("/profile/{email_id}")
async def get_profile_by_email(email_id: str, db: Session = Depends(get_db)):
    """
    Retrieve user profile/form data by email ID.
    Returns the most recent form (draft or submitted) for the given email.
    """
    try:
        # First try to get the most recent non-draft form
        form = db.query(BackgroundCheckForm).filter(
            BackgroundCheckForm.email_id == email_id,
            BackgroundCheckForm.status != "draft"
        ).order_by(BackgroundCheckForm.updated_at.desc()).first()
        
        # If no submitted form found, try to get draft
        if not form:
            form = db.query(BackgroundCheckForm).filter(
                BackgroundCheckForm.email_id == email_id,
                BackgroundCheckForm.status == "draft"
            ).order_by(BackgroundCheckForm.updated_at.desc()).first()
        
        if not form:
            raise HTTPException(status_code=404, detail="Profile not found for this email.")
        
        # Return the dictionary representation of the form
        return form.to_dict()
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving profile: {str(e)}")


@router.get("/form/{form_id}/download/{format}")
async def download_form_document(form_id: int, format: str, db: Session = Depends(get_db)):
    """
    Generates and returns a complete, well-formatted PDF document for a given form ID.
    (Final version with all layouts and styles corrected)
    """
    if format.lower() != 'pdf':
        raise HTTPException(status_code=400, detail="Only 'pdf' is supported.")

    form = db.query(BackgroundCheckForm).filter(BackgroundCheckForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    # Helper functions
    def safe_str(value):
        return str(value) if value is not None else ""

    def format_date(value):
        if value is None: return ""
        if isinstance(value, (datetime, date)): return value.strftime('%d/%m/%Y')
        return str(value)

    def to_title_case(s):
        return s.title() if s else ""
        
    def get_check_char(check_value):
        if isinstance(check_value, str):
            check_value = check_value.lower() == 'true'
        return "&#10003;" if check_value else ""

    # Generating HTML "cards" for education details
    education_html = ""
    if isinstance(form.education_details, list) and form.education_details:
        for i, edu in enumerate(form.education_details):
            if isinstance(edu, dict):
                education_html += f"""
                <div class="entry-card">
                    <div class="section-subtitle">Education #{i+1}</div>
                    <table class="detail-table">
                        <tr><td class="detail-label">Institute Name</td><td class="detail-value">{safe_str(edu.get('institution_name'))}</td></tr>
                        <tr><td class="detail-label">Course/Degree</td><td class="detail-value">{safe_str(edu.get('degree'))}</td></tr>
                        <tr><td class="detail-label">Passing Year</td><td class="detail-value">{safe_str(edu.get('year_of_passing'))}</td></tr>
                        <tr><td class="detail-label">Reg. No./CGPA</td><td class="detail-value">{safe_str(edu.get('percentage_or_cgpa'))}</td></tr>
                        <tr><td class="detail-label">Mode</td><td class="detail-value">{safe_str(edu.get('mode'))}</td></tr>
                    </table>
                </div>
                """
    else:
        education_html = "<p>No education details provided.</p>"

    # Generating HTML "cards" for HR details
    hr_html = ""
    if isinstance(form.hr_details, list) and form.hr_details:
        for i, hr in enumerate(form.hr_details):
            if isinstance(hr, dict):
                hr_html += f"""
                <div class="entry-card">
                    <div class="section-subtitle">HR Contact #{i+1}</div>
                    <table class="detail-table">
                        <tr><td class="detail-label">Name</td><td class="detail-value">{safe_str(hr.get('hr_name'))}</td></tr>
                        <tr><td class="detail-label">Contact Number</td><td class="detail-value">{safe_str(hr.get('hr_contact_number'))}</td></tr>
                        <tr><td class="detail-label">Email ID</td><td class="detail-value">{safe_str(hr.get('hr_email_id'))}</td></tr>
                    </table>
                </div>
                """
    else:
        hr_html = "<p>No HR details provided.</p>"

    # Generating HTML "cards" for Reference details
    reference_html = ""
    if isinstance(form.reference_details, list) and form.reference_details:
        for i, ref in enumerate(form.reference_details):
            if isinstance(ref, dict):
                reference_html += f"""
                <div class="entry-card">
                    <div class="section-subtitle">Reference #{i+1}</div>
                    <table class="detail-table">
                        <tr><td class="detail-label">Referee Name</td><td class="detail-value">{safe_str(ref.get('ref_name'))}</td></tr>
                        <tr><td class="detail-label">Organization</td><td class="detail-value">{safe_str(ref.get('address'))}</td></tr>
                        <tr><td class="detail-label">Designation</td><td class="detail-value">{safe_str(ref.get('relationship'))}</td></tr>
                        <tr><td class="detail-label">Contact</td><td class="detail-value">{safe_str(ref.get('ref_contact_number'))}</td></tr>
                        <tr><td class="detail-label">Email</td><td class="detail-value">{safe_str(ref.get('ref_email_id'))}</td></tr>
                    </table>
                </div>
                """
    else:
        reference_html = "<p>No reference details provided.</p>"

    # Verification Checks
    checks = form.verification_checks or {}

    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica', sans-serif; margin: 0; padding: 25px; font-size: 10px; color: #333; }}
            .header {{ text-align: center; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #4A90E2; }}
            .header h1 {{ color: #4A90E2; margin: 0; font-size: 20px; font-weight: bold; }}
            .section {{ margin-bottom: 15px; page-break-inside: avoid; }}
            .section-title {{ background-color: #4A90E2; color: #fff; font-size: 12px; font-weight: bold; padding: 6px 12px; text-transform: uppercase; }}
            .section-subtitle {{ font-size: 11px; font-weight: bold; color: #555; margin-top: 10px; margin-bottom: 5px; border-bottom: 1px solid #eee; padding-bottom: 3px; }}
            .form-table {{ width: 100%; border-collapse: collapse; }}
            .form-table td {{ border: 1px solid #eee; padding: 6px 8px; vertical-align: top; }}
            .form-label {{ font-weight: bold; color: #444; background-color: #f8f8f8; width: 25%; white-space: nowrap; }}
            .page-break {{ page-break-before: always; }}
            .entry-card {{ border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px; overflow: hidden; }}
            
            .detail-table {{ width: 100%; border-collapse: collapse; table-layout: auto; }}
            .detail-table td {{ border: 1px solid #eee; padding: 6px 8px; }}
            .detail-label {{ width: 30%; font-weight: bold; background-color: #f8f8f8; white-space: nowrap; }}
            .detail-value {{ width: 70%; word-wrap: break-word; }}
            
            .auth-section {{ border: 2px solid #4A90E2; padding: 15px; background-color: #f9fcff; border-radius: 10px; }}
            .verification-table {{ width: 100%; border: none !important; margin-bottom: 10px; }}
            .verification-table td {{ border: none !important; padding: 4px 0; vertical-align: middle; }}
            .verification-table .text-cell {{ width: 95%; text-align: left; }}
            .verification-table .box-cell {{ width: 5%; text-align: right; }}
            .checkbox {{ display: inline-block; width: 14px; height: 14px; border: 1px solid #333; }}
            .acknowledgment-row {{ display: -pdf-flexbox; flex-direction: row; align-items: center; margin-top: 10px; }}
            .ack-checkbox {{ display: inline-block; width: 12px; height: 12px; border: 1px solid #333; text-align: center; line-height: 12px; font-family: sans-serif; }}
            .ack-label {{ margin-left: 8px; }}

        </style>
    </head>
    <body>
        <div class="header"><h1>BACKGROUND CHECK FORM</h1></div>

        <div class="section">
            <div class="section-title">PERSONAL INFORMATION</div>
            <table class="form-table">
                 <tr>
                    <td class="form-label">Candidate Name</td><td>{to_title_case(safe_str(form.candidate_name))}</td>
                    <td class="form-label">Father's Name</td><td>{to_title_case(safe_str(form.father_name))}</td>
                </tr>
                <tr>
                    <td class="form-label">Date of Birth</td><td>{format_date(form.date_of_birth)}</td>
                    <td class="form-label">Mother's Name</td><td>{to_title_case(safe_str(form.mother_name))}</td>
                </tr>
                <tr>
                    <td class="form-label">Marital Status</td><td>{safe_str(form.marital_status)}</td>
                    <td class="form-label">Email ID</td><td>{safe_str(form.email_id)}</td>
                </tr>
                <tr>
                    <td class="form-label">Contact Number</td><td>{safe_str(form.contact_number)}</td>
                    <td class="form-label">Alternate Contact</td><td>{safe_str(form.alternate_contact_number)}</td>
                </tr>
                <tr>
                    <td class="form-label">Aadhaar Number</td><td>{safe_str(form.aadhaar_card_number)}</td>
                    <td class="form-label">PAN Number</td><td>{safe_str(form.pan_number).upper()}</td>
                </tr>
                 <tr>
                    <td class="form-label">UAN Number</td><td colspan="3">{safe_str(form.uan_number)}</td>
                </tr>
            </table>
        </div>
        <div class="section">
            <div class="section-title">ADDRESS DETAILS</div>
            <div class="section-subtitle">Current Address</div>
            <table class="form-table">
                <tr><td class="form-label">Complete Address</td><td colspan="3">{safe_str(form.current_complete_address)}</td></tr>
                <tr>
                    <td class="form-label">Landmark</td><td>{safe_str(form.current_landmark)}</td>
                    <td class="form-label">City</td><td>{safe_str(form.current_city)}</td>
                </tr>
                <tr>
                    <td class="form-label">State</td><td>{safe_str(form.current_state)}</td>
                    <td class="form-label">PIN Code</td><td>{safe_str(form.current_pin_code)}</td>
                </tr>
                <tr>
                    <td class="form-label">Police Station</td><td>{safe_str(form.current_police_station)}</td>
                    <td class="form-label">Duration</td><td>{format_date(form.current_duration_from)} to {format_date(form.current_duration_to)}</td>
                </tr>
            </table>
            <div class="section-subtitle">Permanent Address</div>
            <table class="form-table">
                <tr><td class="form-label">Complete Address</td><td colspan="3">{safe_str(form.permanent_complete_address)}</td></tr>
                <tr>
                    <td class="form-label">Landmark</td><td>{safe_str(form.permanent_landmark)}</td>
                    <td class="form-label">City</td><td>{safe_str(form.permanent_city)}</td>
                </tr>
                <tr>
                    <td class="form-label">State</td><td>{safe_str(form.permanent_state)}</td>
                    <td class="form-label">PIN Code</td><td>{safe_str(form.permanent_pin_code)}</td>
                </tr>
                 <tr>
                    <td class="form-label">Police Station</td><td>{safe_str(form.permanent_police_station)}</td>
                    <td class="form-label">Duration</td><td>{format_date(form.permanent_duration_from)} to {format_date(form.permanent_duration_to)}</td>
                </tr>
            </table>
        </div>

        <div class="page-break"></div>

        <div class="section">
            <div class="section-title">EDUCATIONAL QUALIFICATIONS</div>
            {education_html}
        </div>
        <div class="section">
            <div class="section-title">EMPLOYMENT DETAILS</div>
            <div class="section-subtitle">Previous Organization Details</div>
            <table class="form-table">
                <tr><td class="form-label">Organization Name</td><td colspan="3">{safe_str(form.organization_name)}</td></tr>
                <tr><td class="form-label">Organization Address</td><td colspan="3">{safe_str(form.organization_address)}</td></tr>
                <tr>
                    <td class="form-label">Designation</td><td>{safe_str(form.designation)}</td>
                    <td class="form-label">Employee Code</td><td>{safe_str(form.employee_code)}</td>
                </tr>
                <tr>
                    <td class="form-label">Date of Joining</td><td>{format_date(form.date_of_joining)}</td>
                    <td class="form-label">Last Working Day</td><td>{format_date(form.last_working_day)}</td>
                </tr>
                 <tr>
                    <td class="form-label">Salary (CTC)</td><td>{safe_str(form.salary)}</td>
                    <td class="form-label">Reason for Leaving</td><td>{safe_str(form.reason_for_leaving)}</td>
                </tr>
            </table>
            <div class="section-subtitle">Reporting Manager Details</div>
            <table class="form-table">
                <tr>
                    <td class="form-label">Manager Name</td><td>{safe_str(form.manager_name)}</td>
                    <td class="form-label">Manager Contact</td><td>{safe_str(form.manager_contact_number)}</td>
                </tr>
                <tr><td class="form-label">Manager Email</td><td colspan="3">{safe_str(form.manager_email_id)}</td></tr>
            </table>
        </div>

        <div class="page-break"></div>

        <div class="section">
            <div class="section-title">HR DETAILS</div>
            {hr_html}
        </div>
        <div class="section">
            <div class="section-title">PROFESSIONAL REFERENCES</div>
            {reference_html}
        </div>
        
        <div class="page-break"></div>
        
        <div class="section">
            <div class="section-title">AUTHORIZATION & VERIFICATION CHECKS</div>
            <div class="auth-section">
                <p style="font-weight: bold;">Required Background Verification Checks:</p>
                <table class="verification-table">
                    <tr>
                        <td class="text-cell">Education Verification</td>
                        <td class="box-cell"><div class="checkbox">{get_check_char(checks.get('education_verification'))}</div></td>
                    </tr>
                    <tr>
                        <td class="text-cell">Employment Verification</td>
                        <td class="box-cell"><div class="checkbox">{get_check_char(checks.get('employment_verification'))}</div></td>
                    </tr>
                    <tr>
                        <td class="text-cell">Address & Criminal Verification</td>
                        <td class="box-cell"><div class="checkbox">{get_check_char(checks.get('address_verification'))}</div></td>
                    </tr>
                    <tr>
                        <td class="text-cell">Identity Verification</td>
                        <td class="box-cell"><div class="checkbox">{get_check_char(checks.get('identity_verification'))}</div></td>
                    </tr>
                    <tr>
                        <td class="text-cell">CIBIL Verification</td>
                        <td class="box-cell"><div class="checkbox">{get_check_char(checks.get('credit_check'))}</div></td>
                    </tr>
                </table>
                
                <div class="section-title" style="margin-top: 20px; text-transform: none; text-align: left;">Letter of Authorization</div>
                <p style="font-size: 8pt; text-align: justify; margin-top: 10px;">I hereby authorize (company name) and/or any of its subsidiaries or affiliates, and any person or organizations acting on its behalf to verify the information presented on this application form and to procure and investigate report for background verification purpose. I have read, understood and by my signature consent to above statement. I also understood if any misrepresentation found in details provided by me it may cause the repercussions, which may be lead to result as releasing from my duties with immediate effect.</p>
                <table class="form-table" style="margin-top: 15px;">
                    <tr><td class="form-label">NAME OF THE CANDIDATE (FOR AUTHORIZATION)</td><td>{to_title_case(safe_str(form.candidate_name_auth))}</td></tr>
                    <tr><td class="form-label">SIGNATURE (TYPE YOUR FULL NAME)</td><td>{to_title_case(safe_str(form.signature))}</td></tr>
                    <tr><td class="form-label">DATE</td><td>{format_date(form.auth_date)}</td></tr>
                </table>
                <div class="acknowledgment-row">
                    <span class="ack-checkbox">{get_check_char(form.acknowledgment)}</span><span class="ack-label">I acknowledge that all the information provided above is true and correct to the best of my knowledge.</span>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    result = BytesIO()
    pdf = pisa.CreatePDF(BytesIO(html_content.encode("UTF-8")), dest=result)

    if pdf.err:
        raise HTTPException(status_code=500, detail=f"Error generating PDF. Error code: {pdf.err}")

    result.seek(0)
    return StreamingResponse(
        result,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=background_check_{form_id}.pdf"}
    )