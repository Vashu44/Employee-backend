from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from db.database import get_db
from Schema.project_schema import ProjectCreate, ProjectResponse, ProjectUpdate
from service.project_service import ProjectService

router = APIRouter(
    prefix="/project",
)

@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db)
):
    return await ProjectService.create_project(db, project)

@router.get("/", response_model=List[ProjectResponse])
async def get_all_projects(
    db: Session = Depends(get_db)
):
    return await ProjectService.get_all_projects(db)

@router.get("/names", response_model=List[str])
async def get_project_names(
    db: Session = Depends(get_db)
):
    """Get a list of all project names"""
    return await ProjectService.get_project_names(db)

@router.get("/code/{project_code}", response_model=List[ProjectResponse])
async def get_project_details_by_code(
    project_code: str,
    db: Session = Depends(get_db)
):
    """Get projects by project code"""
    return await ProjectService.get_project_details_by_code(db, project_code)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_by_id(
    project_id: int,
    db: Session = Depends(get_db)
):
    return await ProjectService.get_project_by_id(db, project_id)

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project: ProjectUpdate,
    db: Session = Depends(get_db)
):
    return await ProjectService.update_project(db, project_id, project)

@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    return await ProjectService.delete_project(db, project_id)

@router.get("/user/{user_id}/projects", response_model=List[ProjectResponse])
async def get_project_details_by_user_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all projects assigned to a specific user"""
    return await ProjectService.get_project_details_by_user_id(db, user_id)

