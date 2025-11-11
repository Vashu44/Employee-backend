from sqlalchemy.orm import Session
from model.userDetails_model import UserDetails
from fastapi import HTTPException

class ProjectService:
    @staticmethod
    async def get_project_name_by_user_id(db: Session, user_id: int) -> dict:
        # First get user's project name from UserDetails
        user_project = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        
        if not user_project:
            raise HTTPException(status_code=404, detail="User not found")
            
        project_name = user_project.project_name
        
        if not project_name:
            raise HTTPException(status_code=404, detail="No projects assigned to the user")
            
        return {"project_name": project_name}  


