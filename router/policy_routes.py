from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
import logging
import os
import shutil
import json
from pathlib import Path
 
from db.database import get_db
from model.policy_model import Policy
from pydantic import BaseModel, Field
from datetime import date

# Create uploads directory in BackAuthApi if it doesn't exist
UPLOAD_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uploads', 'policies')))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)
logger.info(f"Using uploads directory: {UPLOAD_DIR}")

# Pydantic models for request/response
class PolicyBase(BaseModel):
    name: str
    department: str
    description: str
    policy_category: Optional[str] = None
    effective_date: Optional[date] = None
    applicable_roles: Optional[List[str]] = None
 
class PolicyCreate(PolicyBase):
    pass
 
class PolicyUpdate(PolicyBase):
    pass
 
class PolicyResponse(PolicyBase):
    id: int
    pdf_filename: Optional[str] = None
    pdf_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
   
    class Config:
        from_attributes = True
 
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
router = APIRouter()
db_dependency = Depends(get_db)
 
 
@router.get("/policies", response_model=List[PolicyResponse])
async def get_policies(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = db_dependency
):
    """
    Get all policies with optional filtering and pagination
    """
    try:
        query = db.query(Policy)
 
        if search:
            query = query.filter(
                Policy.name.contains(search) | Policy.description.contains(search)
            )
 
        if department:
            query = query.filter(Policy.department == department)
 
        policies = query.offset(skip).limit(limit).all()
        return policies
    except Exception as e:
        logger.error(f"Error fetching policies: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
 
 
@router.get("/policies/{policy_id}", response_model=PolicyResponse)
async def get_policy(policy_id: int, db: Session = db_dependency):
    """
    Get a specific policy by ID
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
 
 
@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    name: str = Form(...),
    department: str = Form(...),
    description: str = Form(...),
    policy_category: str = Form(None),
    effective_date: Optional[str] = Form(None),
    applicable_roles: str = Form(None),  # JSON string of role arrays
    policy_pdf: UploadFile = File(None),
    db: Session = db_dependency
):
    """
    Create a new policy with optional PDF upload and role assignments
    """
    existing_policy = db.query(Policy).filter(Policy.name == name).first()
    if existing_policy:
        raise HTTPException(status_code=400, detail="Policy with this name already exists")
    
    # Parse applicable roles from JSON string
    roles_list = None
    if applicable_roles:
        try:
            roles_list = json.loads(applicable_roles)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid format for applicable_roles")
    
    # Create policy data dict
    policy_data = {
        "name": name,
        "department": department,
        "description": description,
        "policy_category": policy_category,
        "effective_date": datetime.strptime(effective_date, "%Y-%m-%d").date() if effective_date else None,
        "applicable_roles": roles_list,
    }
    
    # Handle PDF upload if provided
    if policy_pdf:
        # Validate file type
        if not policy_pdf.filename or not policy_pdf.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Create safe filename
        safe_filename = f"{name.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        file_path = UPLOAD_DIR / safe_filename
        
        try:
            # Save the uploaded file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(policy_pdf.file, buffer)
            
            # Verify file was saved
            if not os.path.isfile(file_path):
                raise HTTPException(status_code=500, detail="Failed to save PDF file")
            
            logger.info(f"✓ PDF saved successfully at: {file_path}")
            logger.info(f"✓ File size: {os.path.getsize(file_path)} bytes")
                
            policy_data["pdf_filename"] = policy_pdf.filename
            policy_data["pdf_path"] = str(file_path)
        except Exception as e:
            logger.error(f"Error saving PDF: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save PDF: {str(e)}")
    
    # Create the policy in DB
    db_policy = Policy(**policy_data)
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    logger.info(f"Policy created with ID {db_policy.id}")
    return db_policy


@router.put("/policies/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: int,
    name: str = Form(...),
    department: str = Form(...),
    description: str = Form(...),
    policy_category: str = Form(None),
    effective_date: Optional[str] = Form(None),
    applicable_roles: str = Form(None),  # JSON string of role arrays
    policy_pdf: UploadFile = File(None),
    db: Session = db_dependency
):
    """
    Update an existing policy with optional PDF replacement and role assignments
    """
    db_policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not db_policy:
        raise HTTPException(status_code=404, detail="Policy not found")
 
    # Check for duplicate name
    existing_policy = db.query(Policy).filter(
        Policy.name == name, Policy.id != policy_id
    ).first()
    if existing_policy:
        raise HTTPException(status_code=400, detail="Policy with this name already exists")
    
    # Parse applicable roles from JSON string
    roles_list = None
    if applicable_roles:
        try:
            roles_list = json.loads(applicable_roles)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid format for applicable_roles")
    
    # Update basic fields
    setattr(db_policy, "name", name)
    setattr(db_policy, "department", department)
    setattr(db_policy, "description", description)
    setattr(db_policy, "policy_category", policy_category)
    setattr(db_policy, "effective_date", datetime.strptime(effective_date, "%Y-%m-%d").date() if effective_date else None)
    setattr(db_policy, "applicable_roles", roles_list)
    
    # Handle PDF upload if provided
    if policy_pdf:
        # Validate file type
        if not policy_pdf.filename or not policy_pdf.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
        # Ensure upload directory exists
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        # Remove old PDF if exists
        pdf_path = getattr(db_policy, "pdf_path", None)
        if pdf_path and os.path.exists(str(pdf_path)):
            try:
                os.remove(str(pdf_path))
                logger.info(f"✓ Removed old PDF: {pdf_path}")
            except OSError as e:
                logger.error(f"Error removing old PDF: {str(e)}")
        
        # Create safe filename
        safe_filename = f"{name.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        file_path = UPLOAD_DIR / safe_filename
        
        try:
            # Save the uploaded file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(policy_pdf.file, buffer)
            
            # Verify file was saved
            if not os.path.isfile(file_path):
                raise HTTPException(status_code=500, detail="Failed to save PDF file")
            
            logger.info(f"✓ PDF updated successfully at: {file_path}")
            logger.info(f"✓ File size: {os.path.getsize(file_path)} bytes")
                
            setattr(db_policy, "pdf_filename", policy_pdf.filename)
            setattr(db_policy, "pdf_path", str(file_path))
        except Exception as e:
            logger.error(f"Error saving PDF: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save PDF: {str(e)}")
 
    setattr(db_policy, "updated_at", datetime.utcnow())
    db.commit()
    db.refresh(db_policy)
    logger.info(f"Policy updated with ID {policy_id}")
    return db_policy


@router.get("/policies/{policy_id}/download", status_code=status.HTTP_200_OK)
async def download_policy_pdf(policy_id: int, db: Session = db_dependency):
    """
    Download/View a policy's PDF file in browser
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Get the PDF path from the policy
    stored_path = getattr(policy, "pdf_path", None)
    pdf_filename = getattr(policy, "pdf_filename", None)
    
    if not stored_path:
        raise HTTPException(status_code=404, detail="Policy PDF not uploaded")
    
    # Convert SQLAlchemy property to string
    stored_path_str = str(stored_path)
    
    # Log for debugging
    logger.info(f"Attempting to serve PDF for policy {policy_id}")
    logger.info(f"Stored path in DB: {stored_path_str}")
    logger.info(f"Current upload directory: {UPLOAD_DIR}")
    
    file_path = None
    
    # First try the path directly (for new uploads)
    if os.path.isfile(stored_path_str):
        logger.info(f"✓ PDF found at stored path: {stored_path_str}")
        file_path = stored_path_str
    else:
        # If stored path doesn't exist, try to find file by filename in current upload directory
        # This handles cases where:
        # 1. File was uploaded on different server/environment (like /opt/render/...)
        # 2. Server was moved or directory structure changed
        
        if pdf_filename:
            # Try using the original filename in current upload directory
            current_path = UPLOAD_DIR / pdf_filename
            logger.info(f"Trying with original filename: {current_path}")
            
            if os.path.isfile(current_path):
                logger.info(f"✓ PDF found with original filename: {current_path}")
                file_path = current_path
        
        # If still not found, try extracting filename from stored path
        if not file_path:
            try:
                filename = os.path.basename(stored_path_str)
                alternative_path = UPLOAD_DIR / filename
                
                logger.info(f"Trying with extracted filename: {alternative_path}")
                
                if os.path.isfile(alternative_path):
                    logger.info(f"✓ PDF found at alternative path: {alternative_path}")
                    file_path = alternative_path
            except Exception as e:
                logger.error(f"Error extracting filename: {e}")
        
        # If still not found, list directory contents for debugging
        if not file_path:
            try:
                files_in_dir = os.listdir(str(UPLOAD_DIR))
                logger.error(f"❌ PDF not found anywhere!")
                logger.error(f"Files in upload directory ({UPLOAD_DIR}): {files_in_dir}")
                logger.error(f"Searched for: {stored_path_str}")
                if pdf_filename:
                    logger.error(f"Also searched for: {pdf_filename}")
            except Exception as e:
                logger.error(f"Could not list upload directory: {e}")
            
            raise HTTPException(
                status_code=404, 
                detail=f"PDF file not found. Please re-upload the policy PDF."
            )
    
    # Get display filename
    display_filename = pdf_filename or os.path.basename(file_path)
    
    # Return file with inline display for browser viewing
    return FileResponse(
        path=file_path,
        filename=str(display_filename),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{display_filename}"'  # inline = view in browser
        }
    )


@router.get("/roles", status_code=status.HTTP_200_OK)
async def get_available_roles():
    """
    Get all available roles/levels in the organization
    """
    roles = [
        {"level": "L0", "code": "INTERN", "name": "Intern", "description": "Student or fresher under training"},
        {"level": "L1", "code": "TRAINEE", "name": "Trainee Software Engineer / Graduate Engineer Trainee (GET)", "description": "Just joined after college/training"},
        {"level": "L2", "code": "SD1", "name": "SD1 / SDE1 / Associate Software Engineer", "description": "Entry-level, 0–2 years experience"},
        {"level": "L3", "code": "SD2", "name": "SD2 / SDE2 / Software Engineer", "description": "Mid-level dev, 2–5 years"},
        {"level": "L4", "code": "SD3", "name": "SD3 / SDE3 / Senior Software Engineer", "description": "Senior dev, owns modules, mentors"},
        {"level": "L5", "code": "LEAD", "name": "Lead Developer / Tech Lead", "description": "Leads team of developers, technical decisions"},
        {"level": "L6", "code": "PRINCIPAL", "name": "Principal Engineer / Staff Engineer", "description": "High-level architecture, deep expertise"},
        {"level": "L7", "code": "EM", "name": "Engineering Manager (EM)", "description": "Manages team and delivery"},
        {"level": "L8", "code": "SEM", "name": "Senior Engineering Manager (SEM)", "description": "Manages multiple teams/projects"},
        {"level": "L9", "code": "DIRECTOR", "name": "Director of Engineering", "description": "Strategic planning, multiple teams"},
        {"level": "L10", "code": "VP", "name": "VP of Engineering / CTO", "description": "Top-level technology decision maker"},
    ]
    return roles


@router.delete("/policies/{policy_id}", status_code=status.HTTP_200_OK)
async def delete_policy(policy_id: int, db: Session = db_dependency):
    """
    Delete a policy
    """
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
 
    # Delete associated PDF file if exists
    stored_path = getattr(policy, "pdf_path", None)
    if stored_path:
        stored_path_str = str(stored_path)
        try:
            # Try stored path
            if os.path.isfile(stored_path_str):
                os.remove(stored_path_str)
                logger.info(f"Deleted PDF file from: {stored_path_str}")
            else:
                # Try alternative path in uploads directory
                filename = os.path.basename(stored_path_str)
                alternative_path = os.path.join(str(UPLOAD_DIR), filename)
                if os.path.isfile(alternative_path):
                    os.remove(alternative_path)
                    logger.info(f"Deleted PDF file from alternative path: {alternative_path}")
        except OSError as e:
            logger.error(f"Error removing PDF file: {str(e)}")
 
    db.delete(policy)
    db.commit()
    logger.info(f"Policy deleted with ID {policy_id}")
    return {"message": "Policy deleted successfully"}
 
 
@router.get("/departments", status_code=status.HTTP_200_OK)
async def get_departments(db: Session = db_dependency):
    """
    Get all unique departments
    """
    try:
        departments = db.query(Policy.department).distinct().all()
        return [dept[0] for dept in departments]
    except Exception as e:
        logger.error(f"Error fetching departments: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
 
 
@router.get("/policies-count", status_code=status.HTTP_200_OK)
async def get_policy_count(db: Session = db_dependency):
    """
    Get total count of policies
    """
    try:
        count = db.query(Policy).count()
        return {"count": count}
    except Exception as e:
        logger.error(f"Error fetching policy count: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
 
 
@router.get("/policies-stats", status_code=status.HTTP_200_OK)
async def get_policy_stats(db: Session = db_dependency):
    """
    Get policy statistics by department
    """
    try:
        # Use func directly instead of db.func
        stats = db.query(
            Policy.department,
            func.count(Policy.id).label('count')
        ).filter(Policy.department.isnot(None))\
         .group_by(Policy.department)\
         .order_by(Policy.department)\
         .all()
        
        # Add detailed logging
        logger.info(f"Retrieved policy stats: {stats}")
        
        # Handle empty results
        if not stats:
            return []
            
        # Convert to list of dictionaries with null check
        result = [
            {
                "department": dept or "Unassigned", 
                "count": count
            } 
            for dept, count in stats
        ]
        
        logger.info(f"Returning formatted stats: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching policy stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching policy statistics: {str(e)}"
        )
