from sqlalchemy.orm import Session
from model.Project_model import Project
from model.userDetails_model import UserDetails  # Add this import
from Schema.project_schema import ProjectCreate, ProjectUpdate, ProjectResponse
from typing import List
from fastapi import HTTPException
from datetime import date

class ProjectService:
    @staticmethod
    async def create_project(db: Session, project: ProjectCreate) -> ProjectResponse:
        db_project = Project(
            project_name=project.project_name,
            description=project.description,
            start_date=project.start_date,
            end_date=project.end_date,
            client_name=project.client_name,
            project_code=project.project_code,
            status=project.status
        )
        try:
            db.add(db_project)
            db.commit()
            db.refresh(db_project)
            return db_project
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    async def get_project_names(db: Session) -> List[str]:
        """Get a list of all project names"""
        projects = db.query(Project.project_name).all()
        return [project[0] for project in projects]  # Extract names from result tuples

    @staticmethod
    async def get_all_projects(db: Session) -> List[Project]:
        return db.query(Project).all()

    @staticmethod
    async def get_project_by_id(db: Session, project_id: int) -> Project:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    @staticmethod
    async def update_project(db: Session, project_id: int, project_update: ProjectUpdate) -> Project:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        for var, value in vars(project_update).items():
            if value is not None:
                setattr(project, var, value)

        try:
            db.commit()
            db.refresh(project)
            return project
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    async def delete_project(db: Session, project_id: int):
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        try:
            db.delete(project)
            db.commit()
            return {"message": "Project deleted successfully"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        

    @staticmethod
    async def get_project_details_by_code(db: Session, project_code: str) -> List[Project]:
        projects = db.query(Project).filter(Project.project_code == project_code).all()

        if not projects:
            raise HTTPException(status_code=404, detail="No projects found with the given code")

        return projects
    
    @staticmethod
    async def get_project_details_by_user_id(db: Session, user_id: int) -> List[Project]:
        # First get user's project name from UserDetails
        user_project = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        
        if not user_project:
            raise HTTPException(status_code=404, detail="User not found")
            
        # Get the project name for this user
        project_name = user_project.project_name
        
        if not project_name:
            raise HTTPException(status_code=404, detail="No projects assigned to the user")
            
        # Now get full project details for the project name
        project = db.query(Project).filter(Project.project_name == project_name).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project details not found")
            
        return [project]  # Return as list to match the response model