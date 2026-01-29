from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from db.database import get_db
from model import usermodels
from model.userDetails_model import UserDetails
from Schema.userDetails_schema import UserBasicDetailsResponse, UserBasicDetailsUpdate,userProjectNameResponse
from service.user_details_service import ProjectService
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
            UserDetails.project_name == project_name
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
                "project_name": user_detail.project_name,
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
    

@router.put("/{user_id}/project-assign", status_code=status.HTTP_200_OK)
async def update_user_project_assignment(
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
        updated_fields = []

        user_details = user.user_details
        if not user_details:
            user_details = UserDetails(user_id=user_id)
            db.add(user_details)
            db.flush() 

        if user_update.project_name is not None:
            setattr(user_details, 'project_name', user_update.project_name)
            updated_fields.append("project_name")

        db.commit()
        db.refresh(user)
        db.refresh(user_details)
        
        # Prepare response data
        response_data = {
            "id": user.id,
            "project_name": user_details.project_name,
        }
        
        return UserBasicDetailsResponse(
            message="User project details updated successfully",
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
            UserDetails.project_name.isnot(None)
        ).order_by(UserDetails.date_of_joining.desc()).first()
        
        if not latest_project:
            raise HTTPException(status_code=404, detail="No projects found for this user")
        
        return {
            "user_id": latest_project.user_id,
            "full_name": latest_project.full_name,
            "personal_email": latest_project.personal_email,
            "current_role": latest_project.current_role,
            "current_department": latest_project.current_Department,
            "manager_name": latest_project.manager_name,
            "project_name": latest_project.project_name
        }
        
    except Exception as e:
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database query error")

#  this router for timesheet user list fetch excluding admin
@router.get("/", status_code=200)
async def get_all_users(db: Session = Depends(get_db)):
    users = db.query(usermodels.User).all()
    result = []
    for user in users:
        role = getattr(user, "role", "").lower()
        if role in ["admin"]:
            continue
        details = user.user_details
        if not details:
            # Create user_details record if missing
            details = UserDetails(user_id=user.id)
            db.add(details)
            db.flush()
            db.refresh(details)
        result.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": details.full_name if details and hasattr(details, "full_name") else "",
            "role": user.role if hasattr(user, "role") else ""
        })
    db.commit()
    return result


#  this router for assign project user list fetch excluding admin
@router.get("/all", status_code=200)
async def get_all_users_for_assign_project(db: Session = Depends(get_db)):
    users = db.query(usermodels.User).all()
    result = []
    for user in users:
        role = getattr(user, "role", "").lower()
        if role in ["admin"]:
            continue
        details = user.user_details
        if not details:
            # Create user_details record if missing
            details = UserDetails(user_id=user.id)
            db.add(details)
            db.flush()
            db.refresh(details)
        result.append({
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": details.full_name if details and hasattr(details, "full_name") else "",
            "role": user.role if hasattr(user, "role") else ""
        })
    db.commit()
    return result


@router.get("/user/{user_id}/project-name", response_model=userProjectNameResponse)
async def get_project_details_by_user_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all projects assigned to a specific user"""
    return await ProjectService.get_project_name_by_user_id(db, user_id)
