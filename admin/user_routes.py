from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from db.database import get_db
import model.usermodels as usermodels
from model.userDetails_model import UserDetails
import bcrypt
from .auth_utils import admin_required
import logging

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/user_details", response_class=HTMLResponse)
async def list_users(
    request: Request,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        # Get page from query parameters, default to 1
        page = int(request.query_params.get("page", 1))
        items_per_page = 10  # Number of users per page

        # Get total count and paginated users with proper ordering
        user_query = db.query(usermodels.User).order_by(usermodels.User.id)
        total_users = user_query.count()
        users = user_query.offset((page - 1) * items_per_page).limit(items_per_page).all()
        total_pages = (total_users + items_per_page - 1) // items_per_page

        logging.info(f"Users page: Found {total_users} users, showing page {page} of {total_pages}")
        
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "admin_name": admin_username,
                "users": users,
                "page": page,
                "total_pages": total_pages,
                "error": None
            }
        )
    except Exception as e:
        logging.error(f"Error fetching users: {str(e)}")
        return templates.TemplateResponse(
            "admin/users.html",
            {
                "request": request,
                "admin_name": admin_username,
                "users": [],
                "page": 1,
                "total_pages": 1,
                "error": str(e)
            }
        )

@router.get("/new", response_class=HTMLResponse)
async def create_user_form(
    request: Request,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse(
        "admin/user/create_user_form.html",
        {
            "request": request,
            "admin_name": admin_username,
            "roles": ["employee", "hr", "admin"],
            "error": None
        }
    )

@router.post("/new", response_class=HTMLResponse)
async def create_user(
    request: Request,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        form = await request.form()
        username = form.get("username")
        email = form.get("email")
        password = form.get("password")
        role = form.get("role")
        
        # Validate required fields
        if not all([username, email, password, role]):
            return templates.TemplateResponse(
                "admin/user/create_user_form.html",
                {
                    "request": request,
                    "admin_name": admin_username,
                    "roles": ["employee", "hr", "admin"],
                    "error": "All fields are required"
                }
            )

        # Check if user already exists
        existing_user = db.query(usermodels.User).filter(
            (usermodels.User.username == username) | (usermodels.User.email == email)
        ).first()

        if existing_user:
            return templates.TemplateResponse(
                "admin/user/create_user_form.html",
                {
                    "request": request,
                    "admin_name": admin_username,
                    "roles": ["employee", "hr", "admin"],
                    "error": "User with this username or email already exists"
                }
            )

        # Create new user
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        new_user = usermodels.User(
            username=username,
            email=email,
            password=hashed_password.decode('utf-8'),
            role=role,
            is_verified=1 if role == 'admin' else 0
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Create user details
        user_details = UserDetails(
            user_id=new_user.id,
            full_name="",
            personal_email=email
        )
        db.add(user_details)
        db.commit()

        return RedirectResponse(url="/admin/user/users", status_code=303)

    except Exception as e:
        logging.error(f"Error creating user: {str(e)}")
@router.get("/view/{user_id}", response_class=HTMLResponse)
async def view_user(
    request: Request,
    user_id: int,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        # Get user and their details
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        if not user:
            logging.error(f"User not found: {user_id}")
            return RedirectResponse(url="/admin/user/user_details", status_code=303)
        
        # Get user details
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
            
        logging.info(f"Viewing user details for user ID: {user_id}")
        return templates.TemplateResponse(
            "admin/user/user_detail.html",
            {
                "request": request,
                "admin_name": admin_username,
                "user": user,
                "user_details": user_details
            }
        )
    except Exception as e:
        logging.error(f"Error viewing user: {str(e)}")
        return RedirectResponse(url="/admin/user/user_details", status_code=303)

@router.get("/edit/{user_id}", response_class=HTMLResponse)
async def edit_user_form(
    request: Request,
    user_id: int,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        if not user:
            logging.error(f"User not found for editing: {user_id}")
            return RedirectResponse(url="/admin/user/user_details", status_code=303)
        
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
            
        return templates.TemplateResponse(
            "admin/user/edit_user.html",
            {
                "request": request,
                "admin_name": admin_username,
                "user": user,
                "user_details": user_details,
                "roles": ["employee", "hr", "admin"]
            }
        )
    except Exception as e:
        logging.error(f"Error loading edit user form: {str(e)}")
        return RedirectResponse(url="/admin/user/user_details", status_code=303)

@router.post("/edit/{user_id}", response_class=HTMLResponse)
async def edit_user(
    request: Request,
    user_id: int,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        form = await request.form()
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        if not user:
            return RedirectResponse(url="/admin/user/user_details", status_code=303)

        # Update user fields
        user.username = form.get("username", user.username)
        user.email = form.get("email", user.email)
        user.role = form.get("role", user.role)
        
        # Only update password if provided
        new_password = form.get("password")
        if new_password:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            user.password = hashed_password.decode('utf-8')

        # Update or create user details
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        if user_details:
            user_details.full_name = form.get("full_name", user_details.full_name)
            user_details.personal_email = form.get("personal_email", user_details.personal_email)
        else:
            user_details = UserDetails(
                user_id=user_id,
                full_name=form.get("full_name", ""),
                personal_email=form.get("personal_email", "")
            )
            db.add(user_details)

        db.commit()
        logging.info(f"Successfully updated user {user_id}")
        return RedirectResponse(url=f"/admin/user/view/{user_id}", status_code=303)
    except Exception as e:
        logging.error(f"Error updating user: {str(e)}")
        return RedirectResponse(url="/admin/user/user_details", status_code=303)

@router.get("/delete/{user_id}")
async def delete_user(
    request: Request,
    user_id: int,
    admin_username: str = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        # Delete user details first (if exists)
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        if user_details:
            db.delete(user_details)

        # Then delete the user
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        if user:
            db.delete(user)
            db.commit()
            logging.info(f"Successfully deleted user {user_id}")
        
        return RedirectResponse(url="/admin/user/user_details", status_code=303)
    except Exception as e:
        logging.error(f"Error deleting user: {str(e)}")
        return RedirectResponse(url="/admin/user/user_details", status_code=303)
        logging.error(f"Error viewing user: {str(e)}")
        return RedirectResponse(url="/admin/user/users", status_code=303)

        return templates.TemplateResponse(
            "admin/user/create_user_form.html",
            {
                "request": request,
                "admin_name": admin_username,
                "roles": ["employee", "hr", "admin"],
                "error": f"Error creating user: {str(e)}"
            }
        )
