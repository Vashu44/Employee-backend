from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
from sqlalchemy.orm import Session
from db.database import get_db
from Schema.userDetails_schema import UserBasicDetailsResponse, UserBasicDetailsUpdate,UserProjectsResponse
from model import usermodels
import model.userDetails_model as userDetails_model
from model.userDetails_model import UserDetails
from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)

def safe_date_format(date_value):
    if date_value is None:
        return None
    if isinstance(date_value, (date, datetime)):
        return date_value.isoformat()
    if isinstance(date_value, str):
        return date_value
    return str(date_value)



# Create router
router = APIRouter(prefix="/user-details")

@router.get("/projects", response_model=List[UserProjectsResponse])
async def get_all_users_projects(db: Session = Depends(get_db)):
    
    """
    Find the Project Name Via user_details table
    """
    try:
        
        # Sabhi users ke unique projects fetch karna
        users_with_projects = db.query(UserDetails).filter(
            UserDetails.Project_name.isnot(None)
        ).all()
        
        # Group by user_id and get unique projects for each user
        user_projects_dict = {}

        for user_details in users_with_projects:
            user_id = user_details.user_id

            if user_id not in user_projects_dict:
                user_projects_dict[user_id] = {
                    'user_id': user_id,
                    'personal_email': user_details.personal_email or "",
                    'projects': set()
                }

            if user_details.Project_name: # type: ignore
                user_projects_dict[user_id]['projects'].add(user_details.Project_name)
        
        # Convert to response format
        response_list = []
        for user_data in user_projects_dict.values():
            response_list.append(UserProjectsResponse(
                projects=list(user_data['projects'])
            ))
        print("✅ Final response:", response_list)
        return response_list
    
        
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database query error")


@router.get("/project/{project_name}/")
async def get_users_by_project_name(project_name: str, db: Session = Depends(get_db)):
    """
    Find all users working on a specific project by project name
    Example: /user-details/project/Intranet Portal/
    """
    try:
        # Query users with the specific project name
        users_with_project = db.query(UserDetails).join(
            usermodels.User, UserDetails.user_id == usermodels.User.id
        ).filter(
            UserDetails.Project_name == project_name
        ).all()
        
        if not users_with_project:
            raise HTTPException(
                status_code=404, 
                detail=f"No users found working on project: {project_name}"
            )
        
        # Prepare response data
        users_list = []
        for user_detail in users_with_project:
            user_info = {
                "user_id": user_detail.user_id,
                "username": user_detail.user.username,
                "email": user_detail.user.email,
                "project_name": user_detail.Project_name,   
            }
            users_list.append(user_info)
        
        return {
            "project_name": project_name,
            "total_users": len(users_list),
            "users": users_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching users for project {project_name}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Database query error"
        )
    

@router.put("/{user_id}/basic-details", status_code=status.HTTP_200_OK)
async def update_user_basic_details(
    user_id: int,
    user_update: UserBasicDetailsUpdate,
    db: Session = Depends(get_db)  # Replace with your db dependency
):
    """
    Update basic user details (phone, email, full name, address, emergency contact, DOB)
    """
    try:
        # Find the user
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="User not found"
            )
        
        # Track which fields are being updated
        updated_fields = []
    

        # Get or create user_details record
        user_details = user.user_details
        if not user_details:
            # Create new user_details record if it doesn't exist
            user_details = userDetails_model.UserDetails(user_id=user_id)
            db.add(user_details)
            db.flush()  # To get the ID
        
        # Update user_details table fields

        if user_update.personal_email is not None:
            setattr(user_details, 'personal_email', user_update.personal_email)
            updated_fields.append("personal_email")
        
        # Commit changes to database
        db.commit()
        db.refresh(user)
        db.refresh(user_details)
        
        # Prepare response data
        response_data = {
            "id": user.id,
            "personal_email": user_details.personal_email,
        }
        
        return UserBasicDetailsResponse(
            message="User details updated successfully",
            updated_fields=updated_fields,
            user_data=response_data
        )
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Route 5: Specific user ke current project details
@router.get("/{user_id}/company-project-details")
async def get_user_company_details(user_id: int, db: Session = Depends(get_db)):
    """
    Find the Project details by their user_id
    """
    try:
        # Latest project entry fetch karna
        latest_project = db.query(UserDetails).filter(
            UserDetails.user_id == user_id,
            UserDetails.Project_name.isnot(None)
        ).order_by(UserDetails.project_Start_date.desc()).first()
        
        if not latest_project:
            raise HTTPException(status_code=404, detail="No projects found for this user")
        
        return {
            "user_id": latest_project.user_id,
            "full_name": latest_project.full_name,
            "personal_email": latest_project.personal_email,
            "project_name": latest_project.Project_name,
            "project_description": latest_project.project_description,
            "project_start_date": latest_project.project_Start_date,
            "project_end_date": latest_project.project_End_date,
            "current_role": latest_project.current_role,
            "current_department": latest_project.current_Department
        }
        
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database query error")


@router.get("/", status_code=200)
async def get_all_users(db: Session = Depends(get_db)):
    users = db.query(usermodels.User).all()
    result = []
    for user in users:
        role = getattr(user, "role", "").lower()
        if role in ["admin", "hr"]:
            continue
        details = user.user_details
        if not details:
            # Create user_details record if missing
            details = userDetails_model.UserDetails(user_id=user.id)
            db.add(details)
            db.flush()
            db.refresh(details)
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "Project_name": details.Project_name if details and hasattr(details, "Project_name") else "",
            "full_name": details.full_name if details and hasattr(details, "full_name") else "",
            "role": user.role if hasattr(user, "role") else ""
        })
    db.commit()
    return result