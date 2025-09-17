from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy import Date as SQLADate
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date
from model.background_model import BackgroundCheckForm
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


@router.put("/form/{form_id}/approve")
async def approve_form(
    form_id: int, 
    approval_data: ApprovalRequest,
    db: Session = Depends(get_db)
):
    """
    Approve or reject a background check form
    """
    try:
        # Find the form
        form = db.query(BackgroundCheckForm).filter(BackgroundCheckForm.id == form_id).first()
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")
        
        # Validate action
        if approval_data.action not in ["approve", "reject"]:
            raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
        
        # Update the form status
        form.status = "approved" if approval_data.action == "approve" else "rejected"
        
        # Add remarks if provided
        if approval_data.remarks:
            form.remarks = approval_data.remarks
        
        # Set approval/rejection timestamp
        form.processed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(form)
        
        return {
            "message": f"Form {approval_data.action}d successfully",
            "form_id": form_id,
            "status": form.status,
            "processed_at": form.processed_at.isoformat() if form.processed_at else None # Ensure datetime is JSON serializable
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing form: {str(e)}")


@router.delete("/form/{form_id}")
async def delete_form(form_id: int, db: Session = Depends(get_db)):
    try:
        form = db.query(BackgroundCheckForm).filter(BackgroundCheckForm.id == form_id).first()
        if not form:
            raise HTTPException(status_code=404, detail="Form not found")

        db.delete(form)
        db.commit()
        return {"message": "Form deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting form: {str(e)}")


@router.get("/forms/pending")
async def get_pending_forms(db: Session = Depends(get_db)):
    """
    Get all pending background check forms
    """
    try:
        forms = db.query(BackgroundCheckForm).filter(BackgroundCheckForm.status == "pending").all()
        return [
            BackgroundCheckFormResponse(
                id=form.id,
                candidate_name=form.candidate_name,
                email_id=form.email_id,
                contact_number=form.contact_number,
                created_at=form.created_at,
                status=form.status
            ) for form in forms
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving pending forms: {str(e)}")


@router.get("/forms/approved")
async def get_approved_forms(db: Session = Depends(get_db)):
    """
    Get all approved background check forms
    """
    try:
        forms = db.query(BackgroundCheckForm).filter(BackgroundCheckForm.status == "approved").all()
        return [
            BackgroundCheckFormResponse(
                id=form.id,
                candidate_name=form.candidate_name,
                email_id=form.email_id,
                contact_number=form.contact_number,
                created_at=form.created_at,
                status=form.status
            ) for form in forms
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving approved forms: {str(e)}")


@router.get("/forms/rejected")
async def get_rejected_forms(db: Session = Depends(get_db)):
    """
    Get all rejected background check forms
    """
    try:
        forms = db.query(BackgroundCheckForm).filter(BackgroundCheckForm.status == "rejected").all()
        return [
            BackgroundCheckFormResponse(
                id=form.id,
                candidate_name=form.candidate_name,
                email_id=form.email_id,
                contact_number=form.contact_number,
                created_at=form.created_at,
                status=form.status
            ) for form in forms
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving rejected forms: {str(e)}")


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

@router.get("/birthdays/today")
async def get_todays_birthdays(db: Session = Depends(get_db)):
    """
    Get all users who have birthdays today
    """
    try:
        today = datetime.now()
        today_month = today.month
        today_day = today.day
        
        # Query users whose date_of_birth field is not null
        users_with_dob = db.query(BackgroundCheckForm).filter(
            BackgroundCheckForm.date_of_birth.isnot(None)
        ).all()
        
        # Filter for today's birthdays
        todays_birthdays = []
        for user in users_with_dob:
            if user.date_of_birth:
                birth_date = user.date_of_birth
                # Handle different date formats - could be string or datetime
                if isinstance(birth_date, str):
                    try:
                        birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
                    except ValueError:
                        # Try alternative date format if the first one fails
                        try:
                            birth_date = datetime.strptime(birth_date, '%d-%m-%Y').date()
                        except ValueError:
                            # Skip this record if date format is invalid
                            continue
                elif isinstance(birth_date, datetime):
                    birth_date = birth_date.date()
                
                # Check if today is the birthday
                if birth_date.month == today_month and birth_date.day == today_day:
                    todays_birthdays.append({
                        "id": user.id,
                        "candidate_name": user.candidate_name,
                        "email_id": user.email_id,
                        "date_of_birth": birth_date.isoformat(),
                        "age": today.year - birth_date.year
                    })
        
        return {
            "date": today.strftime('%Y-%m-%d'),
            "total_birthdays": len(todays_birthdays),
            "birthday_users": todays_birthdays
        }
        
    except Exception as e:
        # Use a simple print for logging if logger is not properly imported
        print(f"Error fetching today's birthdays: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve birthday data: {str(e)}"
        )
