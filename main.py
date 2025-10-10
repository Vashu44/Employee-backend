from __future__ import annotations
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, Depends, status, Request, Response, Body
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr, validator
from typing import Annotated
from datetime import datetime
import model.usermodels as usermodels
from db.database import Base, engine, get_db 
from sqlalchemy import func
from sqlalchemy.orm import Session
import os
import bcrypt
import logging
import traceback
from dotenv import load_dotenv
from utils import token as token_utils
from utils.token import validate_user_and_role, get_user_permissions
from utils.mail_config_utils import conf
from redis_client import RedisClient

from admin.admin_panel import admin_panel 

from router.user_router import router as user_router
from router.userDetails_router import router as userDetails_router
from router.upload_CSV_router import router as upload_CSV_router
from router.background_check_router import router as background_check_router
from router.holiday_router import router as holiday_router
from router.timesheet import router as timesheet_router
from router.mom_router import router as mom_router
from router.mom_decision_router import router as mom_decision_router
from router.mom_information_router import router as mom_information_router
from router.mom_actionitem_router import router as mom_actionitem_router
from router.mom_mail_router import router as mom_mail_router
from router.leave_management_router import router as leave_management_router
from router.policy_routes import router as policy_routes
from router.query_router import query_router
from router.thoughts_router import router as thoughts_router
from router.find_weather import router as find_weather
from router.appreciation_router import router as appreciation_router
from router.expense_router import router as expense_router
from router.asset_router import router as asset_router
from router.report_router import router as report_router


from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_REFRESH_SECRET_KEY = os.getenv("JWT_REFRESH_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRY_MINUTES = os.getenv("ACCESS_TOKEN_EXPIRY_MINUTES")
REFRESH_TOKEN_EXPIRE_DAYS = os.getenv("REFRESH_TOKEN_EXPIRE_DAYS")  

CACHE_DURATION = os.getenv("CACHE_DURATION")

# Read CORS origins from environment variables
REACT_APP_API_URL = os.getenv("REACT_APP_API_URL", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "")

# Parse comma-separated origins and create list
allowed_origins = []
for env_var in [REACT_APP_API_URL, FRONTEND_URL]:
    if env_var:
        origins = [origin.strip() for origin in env_var.split(",") if origin.strip()]
        allowed_origins.extend(origins)

# Remove duplicates while preserving order
allowed_origins = list(dict.fromkeys(allowed_origins))

# If no origins configured, allow localhost for development
if not allowed_origins:
    allowed_origins = ["http://localhost:3000", "http://localhost:8000"]

print("Allowed CORS Origins:", allowed_origins)

# Initialize Redis client
redis_client = RedisClient()


# initialize the database
app = FastAPI(
    title="Employee Management API",
    description="API for managing Employee`s details.",
    version="2.0.5",
)

app.mount("/static", StaticFiles(directory="./static"), name="static")
app.include_router(find_weather, tags=["Weather"])
app.mount("/admin", admin_panel)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

db_dependency = Annotated[Session, Depends(get_db)]


# Define the User model (Schema)
class UserBase(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str

class LoginRequest(BaseModel):
    username: str
    password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

# Pydantic Models for API request/response
class PolicyBase(BaseModel):
    name: str
    department: str
    description: str

class PolicyCreate(PolicyBase):
    pass

class PolicyUpdate(PolicyBase):
    pass

class PolicyResponse(PolicyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Routes
@app.get("/")
def read_root():
    return {"message": "Welcome to the API!"}


# Create a new user
@app.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserBase, db: db_dependency):
    try:
        # validate role
        valid_roles = ['hr', 'admin', 'employee']
        if user.role.lower() not in valid_roles:
            raise HTTPException(status_code=400, detail="Invalid role. Must be one of: hr, admin, employee")
        existing_user = db.query(usermodels.User).filter(
            (usermodels.User.username == user.username) | (usermodels.User.email == user.email)
        ).first()

        if existing_user:
            raise HTTPException(status_code=400, detail="User already exists")

        # hash the password
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
        # create a new user
        new_user = usermodels.User(
            username=user.username,
            email=user.email,
            password=hashed_password.decode('utf-8'),
            is_verified=0,
            role=user.role.lower()
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "User created successfully", "user": new_user.username}
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Employee Login endpoint
@app.post("/auth/employee/login", status_code=status.HTTP_200_OK)
async def employee_login(user: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        validated_user = validate_user_and_role(user.username, user.password, 'employee', db)

        # Convert SQLAlchemy model to dict
        user_data = {
            "id": str(validated_user.id),
            "username": str(validated_user.username),
            "email": str(validated_user.email),
            "role": str(validated_user.role)
        }

        payload = {
            "sub": user_data["username"],
            "user_id": user_data["id"],
            "role": user_data["role"],
            "email": user_data["email"]
        }

        access_token = token_utils.create_access_token(payload)
        refresh_token = token_utils.create_refresh_token(payload)

        token_utils.store_refresh_token(int(user_data["id"]), refresh_token)

        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)

        try:
            validated_user.last_login = func.now()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")

        return {
            "message": "EMPLOYEE logged in successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": int(user_data["id"]),
                "username": user_data["username"],
                "email": user_data["email"],
                "role": user_data["role"],
                "permissions": get_user_permissions(user_data["role"])
            }
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# HR Login endpoint
@app.post("/auth/hr/login", status_code=status.HTTP_200_OK)
async def hr_login(user: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        validated_user = validate_user_and_role(user.username, user.password, 'hr', db)

        # Convert SQLAlchemy model to dict
        user_data = {
            "id": str(validated_user.id),
            "username": str(validated_user.username),
            "email": str(validated_user.email),
            "role": str(validated_user.role)
        }

        payload = {
            "sub": user_data["username"],
            "user_id": user_data["id"],
            "role": user_data["role"],
            "email": user_data["email"]
        }

        access_token = token_utils.create_access_token(payload)
        refresh_token = token_utils.create_refresh_token(payload)

        token_utils.store_refresh_token(int(user_data["id"]), refresh_token)

        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)

        try:
            validated_user.last_login = func.now()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")

        return {
            "message": "HR logged in successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": int(user_data["id"]),
                "username": user_data["username"],
                "email": user_data["email"],
                "role": user_data["role"],
                "permissions": get_user_permissions(user_data["role"])
            }
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
# Manager Login endpoint
@app.post("/auth/admin/login", status_code=status.HTTP_200_OK)
async def admin_login(user: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        validated_user = validate_user_and_role(user.username, user.password, 'admin', db)

        # Convert SQLAlchemy model to dict
        user_data = {
            "id": str(validated_user.id),
            "username": str(validated_user.username),
            "email": str(validated_user.email),
            "role": str(validated_user.role)
        }

        payload = {
            "sub": user_data["username"],
            "user_id": user_data["id"],
            "role": user_data["role"],
            "email": user_data["email"]
        }

        access_token = token_utils.create_access_token(payload)
        refresh_token = token_utils.create_refresh_token(payload)

        token_utils.store_refresh_token(int(user_data["id"]), refresh_token)

        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)

        try:
            validated_user.last_login = func.now()
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")

        return {
            "message": "Admin logged in successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": int(user_data["id"]),
                "username": user_data["username"],
                "email": user_data["email"],
                "role": user_data["role"],
                "permissions": get_user_permissions(user_data["role"])
            }
        }
    except Exception as e:
        traceback.print_exc()  # 👈 This prints the full traceback in your terminal
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Route for User logout
@app.post("/logout")
async def logout(request: Request):
    access_token = request.headers.get("Authorization")
    refresh_token = request.cookies.get("refresh_token")

    if access_token and access_token.startswith("Bearer "):
        token = access_token.split(" ")[1]
        pass

    if refresh_token:
        payload = token_utils.verify_refresh_token(refresh_token)
        if payload:
            token_utils.delete_refresh_token(payload["user_id"])
    return {"message": "Logged out successfully"}


# 1. Forgot password - generate JWT token and store in Redis
@app.post("/forgot-password")
async def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    try:
        logger.info(f"Processing forgot password for email: {request.email}")

        # Check if user exists
        user = db.query(usermodels.User).filter(usermodels.User.email == request.email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Email not registered")

        # Generate JWT token
        jwt_token = token_utils.create_reset_token(request.email)
        logger.info(f"Generated JWT token for user: {user.username}")

        # Store JWT token in Redis with expiry (900 seconds = 15 minutes)
        try:
            redis_key = f"reset_token:{jwt_token}"
            redis_client.setex(redis_key, 900, request.email)
            logger.info(f"JWT token stored in Redis successfully")
        except Exception as redis_error:
            logger.error(f"Redis error: {str(redis_error)}")
            raise HTTPException(status_code=500, detail="Failed to store reset token")

        # Create reset link with JWT token
        reset_link = f"${REACT_APP_API_URL}/reset-password-form?token={jwt_token}"

        # Prepare email message
        message = MessageSchema(
            subject="Password Reset Request",
            recipients=[request.email],
            body=f"""
            Hello {user.username},

            You have requested to reset your password. Please click the link below to reset your password:

            {reset_link}

            This link will expire in 15 minutes for security reasons.

            If you didn't request this password reset, please ignore this email.

            Best regards,
            Your Hitesh~s App Team
            """,
            subtype=MessageType.plain
        )

        # Send email
        try:
            fm = FastMail(conf)
            await fm.send_message(message)
            logger.info("Password reset email sent successfully")
        except Exception as email_error:
            logger.error(f"Email sending error: {str(email_error)}")
            # Clean up the token from Redis if email fails
            redis_client.delete(f"reset_token:{jwt_token}")
            raise HTTPException(status_code=500, detail=f"Failed to send email: {str(email_error)}")
        return {"message": "Password reset link sent to your email.", "token_type": "JWT"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in forgot_password: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error occurred")


# 2. Reset password using JWT token
@app.post("/reset-password")
async def reset_password(request: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        logger.info(f"Processing password reset with JWT token")

        # Validate input
        if not request.token or not request.new_password:
            raise HTTPException(status_code=400, detail="Token and new password are required")

        if len(request.new_password) < 6:
            raise HTTPException(status_code=400, detail="New password must be at least 6 characters long")

        # First verify JWT token structure and expiry
        email_from_jwt = token_utils.verify_reset_token(request.token)
        if not email_from_jwt:
            raise HTTPException(status_code=400, detail="Invalid or expired JWT token")

        # Check if token exists in Redis (for additional security)
        try:
            redis_key = f"reset_token:{request.token}"
            email_from_redis = redis_client.get(redis_key)
            logger.info(f"Retrieved email from Redis: {email_from_redis}")
        except Exception as redis_error:
            logger.error(f"Redis error while retrieving token: {str(redis_error)}")
            raise HTTPException(status_code=500, detail="Failed to validate reset token")

        if not email_from_redis:
            raise HTTPException(status_code=400, detail="Token not found or already used")

        # Verify emails match (JWT vs Redis)
        if email_from_jwt != email_from_redis:
            logger.error(f"Email mismatch: JWT({email_from_jwt}) vs Redis({email_from_redis})")
            redis_client.delete(redis_key)
            raise HTTPException(status_code=400, detail="Token validation failed")

        # Find user by email
        user = db.query(usermodels.User).filter(usermodels.User.email == email_from_jwt).first()
        if not user:
            logger.error(f"User not found for email: {email_from_jwt}")
            # Clean up invalid token
            redis_client.delete(redis_key)
            raise HTTPException(status_code=400, detail="User not found")

        # Hash the new password
        try:
            hashed_password = bcrypt.hashpw(request.new_password.encode('utf-8'), bcrypt.gensalt())
            user.password = hashed_password.decode('utf-8') # Direct assignment
        except Exception as hash_error:
            logger.error(f"Password hashing error: {str(hash_error)}")
            raise HTTPException(status_code=500, detail="Failed to process new password")

        # Update password in database
        try:
            db.commit()
            logger.info(f"Password updated successfully for user: {user.username}")
        except Exception as db_error:
            logger.error(f"Database error while updating password: {str(db_error)}")
            db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update password")

        # Delete the used token from Redis
        try:
            redis_client.delete(redis_key)
            logger.info("JWT token deleted from Redis")
        except Exception as redis_error:
            logger.error(f"Error deleting token from Redis: {str(redis_error)}")
            # This is not critical, so we don't raise an exception

        return {"message": "Password reset successful", "user": user.username}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in reset_password: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error occurred")


@app.post("/reset-password/{token}")
async def reset_password_with_token(token: str, body: dict = Body(...), db: Session = Depends(get_db)):
    """
    Accepts token in path and password in body, matches frontend POST /reset-password/{token}
    """
    new_password = body.get("password")
    if not new_password:
        raise HTTPException(status_code=400, detail="Password is required")
    # Call the same logic as the main reset_password route
    req = PasswordResetConfirm(token=token, new_password=new_password)
    return await reset_password(req, db)

@app.post("/refresh-token")
async def refresh_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = token_utils.verify_refresh_token(refresh_token)
    if not payload or not token_utils.is_refresh_token_valid(payload["user_id"], refresh_token):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Issue new access token
    new_token = token_utils.create_access_token({
        "sub": payload["sub"],
        "user_id": payload["user_id"]
    })
    return {"access_token": new_token, "token_type": "bearer"}


# Update user role (admin only)
@app.put("/users/{user_id}/role")
async def update_user_role(user_id: int, role: str, db: db_dependency):
    """Update user role"""
    try:
        valid_roles = ['hr', 'admin', 'employee']
        if role.lower() not in valid_roles:
            raise HTTPException(status_code=400, detail="Invalid role. Must be one of: hr, admin, employee")
        
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.role = role.lower()
        db.commit()
        db.refresh(user)
        
        return {"message": f"User role updated to {role}", "user_id": user_id, "new_role": role}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user role for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user role: {str(e)}")

# Verify user email
@app.post("/users/{user_id}/verify")
async def verify_user(user_id: int, db: db_dependency):
    """Verify user email"""
    try:
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.is_verified = 1
        db.commit()
        db.refresh(user)
        
        return {"message": "User verified successfully", "user_id": user_id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error verifying user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify user: {str(e)}")
    

#  All Routes are Declared here 
app.include_router(user_router,tags=["Users"])
app.include_router(userDetails_router, tags=["User Details"])
app.include_router(background_check_router, tags=["Profile check"])
app.include_router(upload_CSV_router, tags=["CSV"])
app.include_router(holiday_router, tags=["Holidays"])
app.include_router(timesheet_router, tags=["Timesheets"])
app.include_router(mom_router, tags=["Minutes of Meeting"])
app.include_router(mom_decision_router, tags=["MoM Decisions"])
app.include_router(mom_information_router, tags=["MoM Information"])
app.include_router(mom_actionitem_router, tags=["MoM Action Items"])
app.include_router(mom_mail_router, tags=["MoM Mail"])
app.include_router(leave_management_router, tags=["Leave Management"])
app.include_router(policy_routes, tags=["Policies"])
app.include_router(query_router, tags=["Queries"])
app.include_router(thoughts_router, tags=["Thoughts"])
app.include_router(appreciation_router, tags=["Appreciation"])
app.include_router(expense_router, tags=["Expense Management"])
app.include_router(asset_router, tags=["Asset Management"])
app.include_router(report_router, tags=["Reports"])

