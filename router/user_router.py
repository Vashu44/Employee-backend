from fastapi import APIRouter, HTTPException, Depends,Response, UploadFile,Form, File
from sqlalchemy.orm import Session
from db.database import get_db
from model import usermodels
from model.userDetails_model import UserDetails
from service.user_service import NicknameRequest, BioRequest, NicknameResponse, BioResponse
import logging
from typing import Annotated

db_dependency = Annotated[Session, Depends(get_db)]
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users")

@router.get("/basic")
async def get_all_users_basic(db: Session = Depends(get_db)):
    """
    Get all users with basic info and details
    """
    try:
        # Query all users with their details using outerjoin to include users without UserDetails
        users = db.query(usermodels.User).outerjoin(
            UserDetails, usermodels.User.id == UserDetails.user_id
        ).all()
        
        if not users:
            raise HTTPException(
                status_code=404, 
                detail="No users found"
            )
        
        # Prepare response data with more details
        users_list = []
        for user in users:
            user_info = {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active if hasattr(user, 'is_active') and user.is_active is not None else True,
                "is_verified": user.is_verified if hasattr(user, 'is_verified') and user.is_verified is not None else False,
                "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,
                "updated_at": user.updated_at.isoformat() if hasattr(user, 'updated_at') and user.updated_at else None,
            }
            users_list.append(user_info)
        
        return {
            "total_users": len(users_list),
            "users": users_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching all users basic info: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Database query error"
        )

@router.get("/username/{username}")
async def get_user_by_username(username: str, db: Session = Depends(get_db)):
    """
    Get user's email and role by username
    """
    try:
        # Query user by username
        user = db.query(usermodels.User).filter(
            usermodels.User.username == username
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=404, 
                detail=f"User with username '{username}' not found"
            )
        
        # Prepare response data
        user_info = {
            "user_id": user.id,
            "username": user.username,
            "full_name": user.user_details.full_name,
            "email": user.email,
            "role": getattr(user, "role", "") if hasattr(user, "role") else ""
        }
        
        return {
            "message": "User found successfully",
            "user": user_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user by username {username}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Database query error"
        )


@router.put("/{user_id}/nickname", response_model=NicknameResponse)
async def update_user_nickname(user_id: int, nickname_request: NicknameRequest, db: db_dependency):
    """Update user nickname"""
    try:
        logger.info(f"Updating nickname for user_id: {user_id}")
        
        # Check if user details exist, create if not
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        
        if not user_details:
            logger.info(f"User details for user_id {user_id} not found, creating new record.")
            user_details = UserDetails(user_id=user_id, nickname=nickname_request.nickname)
            db.add(user_details)
        else:
            logger.info(f"Updating existing nickname for user_id {user_id}.")
            user_details.nickname = nickname_request.nickname
        
        db.commit()
        db.refresh(user_details)
        logger.info(f"Nickname updated successfully for user_id {user_id}.")
        
        return NicknameResponse(user_id=user_details.user_id, nickname=user_details.nickname)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during nickname update for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update nickname: {str(e)}")


@router.get("/{user_id}/nickname", response_model=NicknameResponse)
async def get_user_nickname(user_id: int, db: db_dependency):
    """Get user nickname"""
    try:
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        
        if not user_details:
            return NicknameResponse(user_id=user_id, nickname=None)
        
        return NicknameResponse(user_id=user_details.user_id, nickname=user_details.nickname)
        
    except Exception as e:
        logger.error(f"Error retrieving nickname for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve nickname: {str(e)}")


@router.put("/{user_id}/bio", response_model=BioResponse)
async def update_user_bio(user_id: int, bio_request: BioRequest, db: db_dependency):
    """Update user bio"""
    try:
        logger.info(f"Updating bio for user_id: {user_id}")
        
        # Check if user details exist, create if not
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        
        if not user_details:
            logger.info(f"User details for user_id {user_id} not found, creating new record.")
            user_details = UserDetails(user_id=user_id, bio=bio_request.bio)
            db.add(user_details)
        else:
            logger.info(f"Updating existing bio for user_id {user_id}.")
            user_details.bio = bio_request.bio
        
        db.commit()
        db.refresh(user_details)
        logger.info(f"Bio updated successfully for user_id {user_id}.")
        
        return BioResponse(user_id=user_details.user_id, bio=user_details.bio)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during bio update for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update bio: {str(e)}")


@router.get("/{user_id}/bio")
async def get_user_bio(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Handle missing bio attribute
        bio = getattr(user, 'bio', None)
        if bio is None:
            return {"bio": "No bio available"}
        
        return {"bio": bio}
    except AttributeError as e:
        raise HTTPException(status_code=500, detail=f"Bio field not available: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve bio: {str(e)}")


@router.post("/upload-profile-pic/")
async def upload_profile_pic(user_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    user = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.profile_pic is not None:
        message = "Profile picture updated successfully"
    else:
        message = "Profile picture uploaded successfully"
    
    user.profile_pic = contents 
    db.commit()
    db.refresh(user)
    return {"message": message}


@router.get("/{user_id}/profile-pic")
def get_profile_pic(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
    if user is not None and user.profile_pic is not None:
        return Response(content=user.profile_pic, media_type="image/png")
    else:
        raise HTTPException(status_code=404, detail="Image not found")

@router.delete("/{user_id}/profile-pic")
async def delete_profile_pic(user_id: int, db: db_dependency):
    """Delete user profile picture"""
    try:
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        
        if not user_details:
            raise HTTPException(status_code=404, detail="User details not found")
        
        if not user_details.profile_pic:
            raise HTTPException(status_code=404, detail="No profile picture found")
        
        user_details.profile_pic = None
        db.commit()
        
        return {"message": "Profile picture deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting profile picture for user {user_id}: {e}")
        # THIS WAS THE INCOMPLETE LINE:
        raise HTTPException(status_code=500, detail=f"Failed to delete profile picture: {str(e)}")

@router.get("/{user_id}/details", response_model=dict)
async def get_user_profile(user_id: int, db: db_dependency):
    """Get complete user profile including Full Name"""
    try:
        user = db.query(usermodels.User).filter(usermodels.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_details = db.query(UserDetails).filter(UserDetails.user_id == user_id).first()
        
        profile_data = {
            "user_id": user.id,
            "username": user.username,
            "full_name": user.user_details.full_name if user.user_details else None,
            "email": user.email,
            "role": user.role,
            "is_verified": user.is_verified,
            "last_login": user.last_login,
            "nickname": user_details.nickname if user_details else None,
            "bio": user_details.bio if user_details else None,
            "has_profile_pic": bool(user_details.profile_pic) if user_details else False
        }
        return profile_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving profile for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve profile: {str(e)}")

@router.get("/stats")
async def get_user_stats(db: db_dependency):
    """Get user statistics"""
    try:
        total_users = db.query(usermodels.User).count()
        verified_users = db.query(usermodels.User).filter(usermodels.User.is_verified == 1).count()
        hr_users = db.query(usermodels.User).filter(usermodels.User.role == 'hr').count()
        admin_users = db.query(usermodels.User).filter(usermodels.User.role == 'admin').count()
        employee_users = db.query(usermodels.User).filter(usermodels.User.role == 'employee').count()
        
        users_with_profiles = db.query(UserDetails).filter(UserDetails.profile_pic.isnot(None)).count()
        users_with_nicknames = db.query(UserDetails).filter(UserDetails.nickname.isnot(None)).count()
        users_with_bios = db.query(UserDetails).filter(UserDetails.bio.isnot(None)).count()
        
        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "unverified_users": total_users - verified_users,
            "users_by_role": {
                "hr": hr_users,
                "admin": admin_users,
                "employee": employee_users
            },
            "profile_stats": {
                "users_with_profile_pics": users_with_profiles,
                "users_with_nicknames": users_with_nicknames,
                "users_with_bios": users_with_bios
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving user stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user statistics: {str(e)}")