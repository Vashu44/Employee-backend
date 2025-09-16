from fastapi import APIRouter, Request, Depends,HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db.database import get_db
import model.usermodels as usermodels
from model.userDetails_model import UserDetails
from admin.auth_utils import admin_required
import logging
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/user_company_details", response_class=HTMLResponse)
async def list_company_details(
    request: Request,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        # Get all user details
        user_details = db.query(UserDetails).all()
        logging.info(f"Found {len(user_details)} user details")
        
        return templates.TemplateResponse(
            "admin/company details/user_company_details.html",
            {
                "request": request,
                "admin_name": admin_username,
                "user_details": user_details
            }
        )
    except Exception as e:
        logging.error(f"Error fetching company details: {str(e)}")
        return templates.TemplateResponse(
            "admin/company details/user_company_details.html",
            {
                "request": request,
                "admin_name": admin_username,
                "user_details": [],
                "error": str(e)
            }
        )

@router.get("/edit/{user_id}", response_class=HTMLResponse)
async def edit_company_details(
    request: Request,
    user_id: int,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        # Get user and user details
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        user_detail = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        
        if not user or not user_detail:
            return RedirectResponse(url="/admin/company details/user_company_details", status_code=303)
            
        return templates.TemplateResponse(
            "admin/company details/edit_company_details.html",
            {
                "request": request,
                "admin_name": admin_username,
                "user": user,
                "user_detail": user_detail,
                "error": None
            }
        )
    except Exception as e:
        logging.error(f"Error loading edit form: {str(e)}")
        return RedirectResponse(url="/admin/company details/user_company_details", status_code=303)

@router.get("/view/{user_id}", response_class=HTMLResponse)
async def view_company_details(
    request: Request,
    user_id: int,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        # Get user and user details
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        user_detail = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        
        if not user or not user_detail:
            return RedirectResponse(url="/admin/company details/user_company_details", status_code=303)
            
        return templates.TemplateResponse(
            "admin/company details/view_company_details.html",
            {
                "request": request,
                "admin_name": admin_username,
                "user": user,
                "user_detail": user_detail
            }
        )
    except Exception as e:
        logging.error(f"Error loading view page: {str(e)}")
        return RedirectResponse(url="/admin/company details/user_company_details", status_code=303)

@router.post("/edit/{user_id}", response_class=HTMLResponse)
async def update_company_details(
    request: Request,
    user_id: int,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        user_detail = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        if not user_detail:
            raise HTTPException(status_code=404, detail="User details not found")

        form = await request.form()
        
        # Update user details
        user_detail.full_name = form.get("full_name", user_detail.full_name)
        user_detail.personal_email = form.get("personal_email", user_detail.personal_email)
        user_detail.current_Department = form.get("department", user_detail.current_Department)
        user_detail.current_role = form.get("current_role", user_detail.current_role)
        user_detail.Project_name = form.get("project_name", user_detail.Project_name)
        
        # Handle dates
        join_date = form.get("date_of_joining")
        if join_date:
            user_detail.date_of_joining = datetime.strptime(join_date, "%Y-%m-%d")
            
        project_start = form.get("project_start_date")
        if project_start:
            user_detail.project_Start_date = datetime.strptime(project_start, "%Y-%m-%d")
            
        project_end = form.get("project_end_date")
        if project_end:
            user_detail.project_End_date = datetime.strptime(project_end, "%Y-%m-%d")
            
        user_detail.project_description = form.get("project_description", user_detail.project_description)
        
        db.commit()
        
        return RedirectResponse(
            url=f"/admin/company details/view/{user_id}",
            status_code=303
        )
        
    except Exception as e:
        logging.error(f"Error updating user details: {str(e)}")
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        return templates.TemplateResponse(
            "admin/company details/edit_company_details.html",
            {
                "request": request,
                "admin_name": admin_username,
                "user": user,
                "user_detail": user_detail,
                "error": f"Error updating details: {str(e)}"
            }
        )
