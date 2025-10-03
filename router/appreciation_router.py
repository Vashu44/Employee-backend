from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, case
from db.database import get_db
from model.appreciation_model import Appreciation, Like, Comment
from Schema.appreciation_schema import (
    AppreciationCreate, AppreciationUpdate, AppreciationResponse,
    EmployeeAppreciationSummary, DashboardAppreciation, MonthlyHighlightResponse,
    CommentCreate, CommentResponse
)
from pydantic import BaseModel 
import model.usermodels as usermodels
from typing import List, Optional
from datetime import datetime
import logging


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appreciation",)

class UserAction(BaseModel):
    user_id: int


@router.post("/", response_model=AppreciationResponse, status_code=status.HTTP_201_CREATED)
async def create_appreciation(
    appreciation: AppreciationCreate,
    db: Session = Depends(get_db)
):
    """Create new appreciation"""
    try:
        # Verify giver exists
        giver_user = db.query(usermodels.User).filter(
            usermodels.User.id == appreciation.given_by_id
        ).first()
        if not giver_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id={appreciation.given_by_id} not found"
            )

        # Verify employee exists
        employee = db.query(usermodels.User).filter(
            usermodels.User.id == appreciation.employee_id
        ).first()
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )

        # Use the month name directly from the request
        month_name = appreciation.month

        # Check if appreciation for same award type and month already exists
        existing = db.query(Appreciation).filter(
            and_(
                Appreciation.employee_id == appreciation.employee_id,
                Appreciation.award_type == appreciation.award_type.value,
                Appreciation.month == month_name,
                Appreciation.year == appreciation.year,
                Appreciation.is_active == True
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee already has an active {appreciation.award_type.value} award for {month_name} {appreciation.year}"
            )

        # Create new appreciation
        new_appreciation = Appreciation(
            employee_id=appreciation.employee_id,
            given_by_id=appreciation.given_by_id,
            award_type=appreciation.award_type.value,
            badge_level=appreciation.badge_level.value,
            appreciation_message=appreciation.appreciation_message,
            month=month_name,
            year=appreciation.year
        )

        db.add(new_appreciation)
        db.commit()
        db.refresh(new_appreciation)

        response = AppreciationResponse(
            id=new_appreciation.id,
            employee_id=new_appreciation.employee_id,
            employee_username=employee.username,
            employee_email=employee.email,
            given_by_id=new_appreciation.given_by_id,
            given_by_username=giver_user.username,
            award_type=new_appreciation.award_type,
            badge_level=new_appreciation.badge_level,
            appreciation_message=new_appreciation.appreciation_message,
            month=new_appreciation.month,
            year=new_appreciation.year,
            is_active=new_appreciation.is_active,
            created_at=new_appreciation.created_at
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating appreciation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create appreciation: {str(e)}"
        )

# Static routes first (no path parameters)
@router.get("/awards/types")
async def get_award_types():
    """Get all available award types"""
    return {
        "award_types": [
            {"value": "Employee of the Month", "label": "Employee of the Month"},
            {"value": "Best Performer", "label": "Best Performer"},
            {"value": "Innovation Champion", "label": "Innovation Champion"},
            {"value": "Team Player", "label": "Team Player"},
            {"value": "Customer Excellence", "label": "Customer Excellence"},
            {"value": "Leadership Excellence", "label": "Leadership Excellence"}
        ],
        "badge_levels": [
            {"value": "gold", "label": "Gold", "color": "#FFD700"},
            {"value": "silver", "label": "Silver", "color": "#C0C0C0"},
            {"value": "bronze", "label": "Bronze", "color": "#CD7F32"}
        ]
    }

@router.get("/stats")
async def get_appreciation_stats(db: Session = Depends(get_db)):
    """Get appreciation statistics"""
    try:
        total_appreciations = db.query(Appreciation).filter(
            Appreciation.is_active == True
        ).count()

        gold_count = db.query(Appreciation).filter(
            Appreciation.badge_level == "gold", 
            Appreciation.is_active == True
        ).count()

        silver_count = db.query(Appreciation).filter(
            Appreciation.badge_level == "silver", 
            Appreciation.is_active == True
        ).count()

        bronze_count = db.query(Appreciation).filter(
            Appreciation.badge_level == "bronze", 
            Appreciation.is_active == True
        ).count()

        award_types = [
            "Employee of the Month",
            "Best Performer", 
            "Innovation Champion",
            "Team Player",
            "Customer Excellence",
            "Leadership Excellence"
        ]

        award_type_stats = []
        for award_type in award_types:
            count = db.query(Appreciation).filter(
                Appreciation.award_type == award_type, 
                Appreciation.is_active == True
            ).count()
            award_type_stats.append({
                "award_type": award_type,
                "count": count
            })

        current_month = datetime.now().strftime("%B")
        current_month_count = db.query(Appreciation).filter(
            Appreciation.month == current_month,
            Appreciation.is_active == True
        ).count()

        return {
            "total_appreciations": total_appreciations,
            "badge_distribution": {
                "gold": gold_count,
                "silver": silver_count,
                "bronze": bronze_count
            },
            "award_type_distribution": award_type_stats,
            "current_month_appreciations": current_month_count
        }

    except Exception as e:
        logger.error(f"Error fetching appreciation stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch appreciation statistics: {str(e)}"
        )

@router.get("/summary", response_model=List[EmployeeAppreciationSummary])
async def get_appreciation_summary(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get appreciation summary for all employees"""

@router.get("/", response_model=List[dict])
async def get_all_appreciations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    active_only: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get all appreciations with pagination and engagement metrics"""
    try:
        query = db.query(Appreciation)
        
        if active_only:
            query = query.filter(Appreciation.is_active == True)
            
        appreciations = query.order_by(desc(Appreciation.created_at))\
            .offset(skip).limit(limit).all()

        response_list = []
        for app in appreciations:
            # Fetch employee and giver separately
            employee = db.query(usermodels.User).filter(usermodels.User.id == app.employee_id).first()
            giver = db.query(usermodels.User).filter(usermodels.User.id == app.given_by_id).first()
            
            employee_username = employee.username if employee else 'Unknown Employee'
            employee_email = employee.email if employee else ''
            given_by_username = giver.username if giver else 'Unknown Giver'

            # Get engagement metrics
            likes_count = db.query(Like).filter(Like.appreciation_id == app.id).count()
            comments_count = db.query(Comment).filter(Comment.appreciation_id == app.id).count()
            
            # Create base response
            appreciation_response = AppreciationResponse(
                id=app.id,
                employee_id=app.employee_id,
                employee_username=employee_username,
                employee_email=employee_email,
                given_by_id=app.given_by_id,
                given_by_username=given_by_username,
                award_type=app.award_type,
                badge_level=app.badge_level,
                appreciation_message=app.appreciation_message,
                month=app.month,
                year=app.year,
                is_active=app.is_active,
                created_at=app.created_at
            )
            
            # Convert to dict and add engagement counts
            appreciation_dict = appreciation_response.dict()
            appreciation_dict["likes_count"] = likes_count
            appreciation_dict["comments_count"] = comments_count
            
            response_list.append(appreciation_dict)

        return response_list

    except Exception as e:
        logger.error(f"Error fetching appreciations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch appreciations: {str(e)}"
        )

# Static routes continue
@router.get("/monthly-highlight/current", response_model=Optional[MonthlyHighlightResponse])
async def get_monthly_highlight(db: Session = Depends(get_db)):
    """Get the best appreciation for current month"""
    try:
        now = datetime.now()
        current_month_name = now.strftime("%B")
        current_year = now.year

        appreciations = db.query(Appreciation)\
            .filter(
                Appreciation.year == current_year,
                Appreciation.is_active == True,
                Appreciation.month == current_month_name
            )\
            .order_by(
                case(
                    (Appreciation.badge_level == 'gold', 1),
                    (Appreciation.badge_level == 'silver', 2),
                    (Appreciation.badge_level == 'bronze', 3),
                    else_=4
                ),
                desc(Appreciation.created_at)
            )\
            .all()

        latest_appreciation = appreciations[0] if appreciations else None
        if not latest_appreciation:
            return None

        employee = db.query(usermodels.User).filter(
            usermodels.User.id == latest_appreciation.employee_id
        ).first()

        employee_name = 'Unknown Employee'
        if employee:
            employee_name = getattr(employee, 'full_name', None) or getattr(employee, 'username', 'Unknown Employee')

        return MonthlyHighlightResponse(
            id=latest_appreciation.id,
            employee_name=employee_name,
            award_type=latest_appreciation.award_type,
            badge_level=latest_appreciation.badge_level,
            month=latest_appreciation.month,
            year=latest_appreciation.year,
            created_at=latest_appreciation.created_at
        )
    except Exception as e:
        logger.error(f"Error fetching monthly highlight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch monthly highlight: {str(e)}"
        )

@router.get("/monthly-highlight", response_model=Optional[MonthlyHighlightResponse])
async def get_monthly_highlight_legacy(db: Session = Depends(get_db)):
    """Legacy endpoint for monthly highlight"""
    return await get_monthly_highlight(db)

@router.get("/dashboard", response_model=List[DashboardAppreciation])
async def get_dashboard_appreciations(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get recent appreciations for dashboard display"""
    try:
        appreciations = db.query(Appreciation)\
            .filter(Appreciation.is_active == True)\
            .order_by(desc(Appreciation.created_at))\
            .limit(limit).all()

        dashboard_items = []
        for app in appreciations:
            employee = db.query(usermodels.User).filter(usermodels.User.id == app.employee_id).first()
            employee_username = employee.username if employee else 'Unknown Employee'
            # Ensure employee_id is included in the response
            dashboard_items.append({
                'id': app.id,
                'employee_id': app.employee_id,
                'employee_username': employee_username,
                'award_type': app.award_type,
                'badge_level': app.badge_level,
                'appreciation_message': app.appreciation_message,
                'month': app.month,
                'year': app.year,
                'created_at': app.created_at
            })

        return dashboard_items

    except Exception as e:
        logger.error(f"Error fetching dashboard appreciations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard appreciations: {str(e)}"
        )

@router.get("/{employee_id}", response_model=List[dict])
async def get_employee_appreciations(
    employee_id: int,
    active_only: bool = Query(True),
    badge_level: Optional[str] = Query(None, description="Filter by badge level (gold, silver, bronze)"),
    year: Optional[int] = Query(None, description="Filter by year"),
    month: Optional[str] = Query(None, description="Filter by month"),
    award_type: Optional[str] = Query(None, description="Filter by award type"),
    page: Optional[int] = Query(1, description="Page number"),
    db: Session = Depends(get_db)
):
    """Get all appreciations for a specific employee with optional filters"""
    try:
        query = db.query(Appreciation).filter(Appreciation.employee_id == employee_id)

        if active_only:
            query = query.filter(Appreciation.is_active == True)

        # Add filters
        if badge_level:
            query = query.filter(Appreciation.badge_level == badge_level.lower())
        
        if year:
            query = query.filter(Appreciation.year == year)
            
        if month:
            query = query.filter(Appreciation.month == month)
            
        if award_type:
            query = query.filter(Appreciation.award_type.ilike(f"%{award_type}%"))

        appreciations = query.order_by(desc(Appreciation.created_at)).all()

        logger.info(f"🔍 Filtering appreciations for employee {employee_id}: badge_level={badge_level}, year={year}, month={month}, award_type={award_type}")
        logger.info(f"📊 Found {len(appreciations)} appreciations after filtering")
        if active_only:
            query = query.filter(Appreciation.is_active == True)

        # Add filters
        if badge_level:
            query = query.filter(Appreciation.badge_level == badge_level.lower())
        
        if year:
            query = query.filter(Appreciation.year == year)
            
        if month:
            query = query.filter(Appreciation.month == month)
            
        if award_type:
            query = query.filter(Appreciation.award_type.ilike(f"%{award_type}%"))

        appreciations = query.order_by(desc(Appreciation.created_at)).all()

        logger.info(f"🔍 Filtering appreciations for employee {employee_id}: badge_level={badge_level}, year={year}, month={month}, award_type={award_type}")
        logger.info(f"📊 Found {len(appreciations)} appreciations after filtering")

        response_list = []
        for app in appreciations:
            employee = db.query(usermodels.User).filter(usermodels.User.id == app.employee_id).first()
            giver = db.query(usermodels.User).filter(usermodels.User.id == app.given_by_id).first()
            
            employee_username = employee.username if employee else 'Unknown Employee'
            employee_email = employee.email if employee else ''
            given_by_username = giver.username if giver else 'Unknown Giver'
            
            # Get likes and comments counts for this appreciation
            likes_count = db.query(Like).filter(Like.appreciation_id == app.id).count()
            comments_count = db.query(Comment).filter(Comment.appreciation_id == app.id).count()
            
            # Create base response
            appreciation_response = AppreciationResponse(
                id=app.id,
                employee_id=app.employee_id,
                employee_username=employee_username,
                employee_email=employee_email,
                given_by_id=app.given_by_id,
                given_by_username=given_by_username,
                award_type=app.award_type,
                badge_level=app.badge_level,
                appreciation_message=app.appreciation_message,
                month=app.month,
                year=app.year,
                is_active=app.is_active,
                created_at=app.created_at
            )
            
            # Convert to dict and add engagement counts
            appreciation_dict = appreciation_response.dict()
            appreciation_dict["likes_count"] = likes_count
            appreciation_dict["comments_count"] = comments_count
            
            response_list.append(appreciation_dict)

        return response_list

    except Exception as e:
        logger.error(f"Error fetching employee appreciations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch employee appreciations: {str(e)}"
        )

# Summary functionality is now part of /stats endpoint

@router.get("/awards/types")
async def get_award_types():
    """Get all available award types"""
    return {
        "award_types": [
            {"value": "Employee of the Month", "label": "Employee of the Month"},
            {"value": "Best Performer", "label": "Best Performer"},
            {"value": "Innovation Champion", "label": "Innovation Champion"},
            {"value": "Team Player", "label": "Team Player"},
            {"value": "Customer Excellence", "label": "Customer Excellence"},
            {"value": "Leadership Excellence", "label": "Leadership Excellence"}
        ],
        "badge_levels": [
            {"value": "gold", "label": "Gold", "color": "#FFD700"},
            {"value": "silver", "label": "Silver", "color": "#C0C0C0"},
            {"value": "bronze", "label": "Bronze", "color": "#CD7F32"}
        ]
    }

@router.get("/stats")
async def get_appreciation_stats(db: Session = Depends(get_db)):
    """Get appreciation statistics"""
    try:
        total_appreciations = db.query(Appreciation).filter(
            Appreciation.is_active == True
        ).count()

        gold_count = db.query(Appreciation).filter(
            Appreciation.badge_level == "gold", 
            Appreciation.is_active == True
        ).count()

        silver_count = db.query(Appreciation).filter(
            Appreciation.badge_level == "silver", 
            Appreciation.is_active == True
        ).count()

        bronze_count = db.query(Appreciation).filter(
            Appreciation.badge_level == "bronze", 
            Appreciation.is_active == True
        ).count()

        award_types = [
            "Employee of the Month",
            "Best Performer", 
            "Innovation Champion",
            "Team Player",
            "Customer Excellence",
            "Leadership Excellence"
        ]

        award_type_stats = []
        for award_type in award_types:
            count = db.query(Appreciation).filter(
                Appreciation.award_type == award_type, 
                Appreciation.is_active == True
            ).count()
            award_type_stats.append({
                "award_type": award_type,
                "count": count
            })

        current_month = datetime.now().strftime("%B")
        current_month_count = db.query(Appreciation).filter(
            Appreciation.month == current_month,
            Appreciation.is_active == True
        ).count()

        return {
            "total_appreciations": total_appreciations,
            "badge_distribution": {
                "gold": gold_count,
                "silver": silver_count,
                "bronze": bronze_count
            },
            "award_type_distribution": award_type_stats,
            "current_month_appreciations": current_month_count
        }

    except Exception as e:
        logger.error(f"Error fetching appreciation stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch appreciation statistics: {str(e)}"
        )

# CORRECT ORDER: Specific, static paths come first
@router.get("/monthly-highlight/current", response_model=Optional[MonthlyHighlightResponse])
async def get_monthly_highlight(db: Session = Depends(get_db)):
    """Get the best appreciation for current month (prioritized by badge level), handling both YYYY-MM and full month name storage."""
    try:
        now = datetime.now()
        current_month_name = now.strftime("%B")
        current_year = now.year

        # Match the month name
        appreciations = db.query(Appreciation)\
            .filter(
                Appreciation.year == current_year,
                Appreciation.is_active == True,
                Appreciation.month == current_month_name
            )\
            .order_by(
                case(
                    (Appreciation.badge_level == 'gold', 1),
                    (Appreciation.badge_level == 'silver', 2),
                    (Appreciation.badge_level == 'bronze', 3),
                    else_=4
                ),
                desc(Appreciation.created_at)
            )\
            .all()

        latest_appreciation = appreciations[0] if appreciations else None

        if not latest_appreciation:
            return None

        employee = db.query(usermodels.User).filter(
            usermodels.User.id == latest_appreciation.employee_id
        ).first()

        employee_name = 'Unknown Employee'
        if employee:
            employee_name = getattr(employee, 'full_name', None) or getattr(employee, 'username', 'Unknown Employee')

        return MonthlyHighlightResponse(
            id=latest_appreciation.id,
            employee_name=employee_name,
            award_type=latest_appreciation.award_type,
            badge_level=latest_appreciation.badge_level,
            month=latest_appreciation.month,
            year=latest_appreciation.year,
            created_at=latest_appreciation.created_at
        )
    except Exception as e:
        logger.error(f"Error fetching monthly highlight: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch monthly highlight: {str(e)}"
        )

@router.get("/monthly-highlight", response_model=Optional[MonthlyHighlightResponse])
async def get_monthly_highlight_legacy(db: Session = Depends(get_db)):
    """Legacy endpoint for monthly highlight"""
    return await get_monthly_highlight(db)

# DYNAMIC PATH: This path with a variable comes AFTER the specific ones
@router.get("/{appreciation_id}", response_model=dict)
async def get_appreciation_by_id(
    appreciation_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific appreciation by ID with engagement metrics"""
    try:
        appreciation = db.query(Appreciation).filter(Appreciation.id == appreciation_id).first()

        if not appreciation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appreciation not found"
            )

        employee = db.query(usermodels.User).filter(usermodels.User.id == appreciation.employee_id).first()
        giver = db.query(usermodels.User).filter(usermodels.User.id == appreciation.given_by_id).first()
        
        employee_username = employee.username if employee else 'Unknown Employee'
        employee_email = employee.email if employee else ''
        given_by_username = giver.username if giver else 'Unknown Giver'
        
        # Get engagement metrics
        likes_count = db.query(Like).filter(Like.appreciation_id == appreciation.id).count()
        comments_count = db.query(Comment).filter(Comment.appreciation_id == appreciation.id).count()

        # Create base response
        appreciation_response = AppreciationResponse(
            id=appreciation.id,
            employee_id=appreciation.employee_id,
            employee_username=employee_username,
            employee_email=employee_email,
            given_by_id=appreciation.given_by_id,
            given_by_username=given_by_username,
            award_type=appreciation.award_type,
            badge_level=appreciation.badge_level,
            appreciation_message=appreciation.appreciation_message,
            month=appreciation.month,
            year=appreciation.year,
            is_active=appreciation.is_active,
            created_at=appreciation.created_at
        )
        
        # Convert to dict and add engagement counts
        result = appreciation_response.dict()
        result["likes_count"] = likes_count
        result["comments_count"] = comments_count
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching appreciation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch appreciation: {str(e)}"
        )

@router.put("/{appreciation_id}", response_model=AppreciationResponse)
async def update_appreciation(
    appreciation_id: int,
    appreciation_update: AppreciationUpdate,
    db: Session = Depends(get_db)
):
    """Update appreciation"""
    try:
        appreciation = db.query(Appreciation).filter(Appreciation.id == appreciation_id).first()

        if not appreciation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appreciation not found"
            )

        if appreciation_update.appreciation_message is not None:
            appreciation.appreciation_message = appreciation_update.appreciation_message

        if appreciation_update.is_active is not None:
            appreciation.is_active = appreciation_update.is_active

        appreciation.updated_at = func.now()
        db.commit()
        db.refresh(appreciation)

        employee = db.query(usermodels.User).filter(usermodels.User.id == appreciation.employee_id).first()
        giver = db.query(usermodels.User).filter(usermodels.User.id == appreciation.given_by_id).first()
        
        employee_username = employee.username if employee else 'Unknown Employee'
        employee_email = employee.email if employee else ''
        given_by_username = giver.username if giver else 'Unknown Giver'

        response = AppreciationResponse(
            id=appreciation.id,
            employee_id=appreciation.employee_id,
            employee_username=employee_username,
            employee_email=employee_email,
            given_by_id=appreciation.given_by_id,
            given_by_username=given_by_username,
            award_type=appreciation.award_type,
            badge_level=appreciation.badge_level,
            appreciation_message=appreciation.appreciation_message,
            month=appreciation.month,
            year=appreciation.year,
            is_active=appreciation.is_active,
            created_at=appreciation.created_at
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating appreciation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update appreciation: {str(e)}"
        )

@router.delete("/{appreciation_id}")
async def delete_appreciation(
    appreciation_id: int,
    db: Session = Depends(get_db)
):
    """Soft delete appreciation"""
    try:
        appreciation = db.query(Appreciation).filter(
            Appreciation.id == appreciation_id
        ).first()

        if not appreciation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appreciation not found"
            )

        appreciation.is_active = False
        appreciation.updated_at = func.now()
        db.commit()

        return {"message": "Appreciation deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting appreciation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete appreciation: {str(e)}"
        )
    
# --- START OF MODIFIED ENDPOINTS ---
@router.post("/{appreciation_id}/like", status_code=status.HTTP_200_OK)
async def toggle_like_appreciation(
    appreciation_id: int,
    action: UserAction,
    db: Session = Depends(get_db)
):
    """Toggle like on an appreciation (like Instagram) - SIMPLE DEBUG VERSION"""
    try:
        print("=== SIMPLE DEBUG INFO ===")
        print(f"Appreciation ID: {appreciation_id}")
        print(f"User ID: {action.user_id}")
        
        # Verify appreciation exists
        appreciation = db.query(Appreciation).filter(Appreciation.id == appreciation_id).first()
        if not appreciation:
            raise HTTPException(status_code=404, detail="Appreciation not found")
        print(f"Appreciation found: {appreciation.id}")
        
        # Verify user exists
        user = db.query(usermodels.User).filter(usermodels.User.id == action.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        print(f"User found: {user.username}")

        # Try to create a Like instance to test the model
        try:
            test_like = Like(appreciation_id=appreciation_id, user_id=action.user_id)
            print("SUCCESS: Like model accepts user_id")
            field_name = "user_id"
        except Exception as e1:
            print(f"user_id failed: {e1}")
            try:
                test_like = Like(appreciation_id=appreciation_id, likes_id=action.user_id)
                print("SUCCESS: Like model accepts likes_id")
                field_name = "likes_id"
            except Exception as e2:
                print(f"likes_id also failed: {e2}")
                # Let's see what fields the Like model actually accepts
                print(f"Like model __init__ signature issue")
                raise HTTPException(
                    status_code=500, 
                    detail=f"Like model field issue - user_id: {e1}, likes_id: {e2}"
                )

        # Check if user already liked this appreciation
        if field_name == "user_id":
            existing_like = db.query(Like).filter(
                Like.appreciation_id == appreciation_id,
                Like.user_id == action.user_id
            ).first()
        else:
            existing_like = db.query(Like).filter(
                Like.appreciation_id == appreciation_id,
                Like.likes_id == action.user_id
            ).first()
        
        print(f"Existing like found: {existing_like is not None}")

        if existing_like:
            # Unlike - remove the like
            db.delete(existing_like)
            db.commit()
            print("Like removed")
            
            # Get updated like count
            total_likes = db.query(Like).filter(Like.appreciation_id == appreciation_id).count()
            
            return {
                "message": "Like removed successfully",
                "is_liked": False,
                "total_likes": total_likes,
                "user_id": action.user_id,
                "username": user.username,
                "debug_field_used": field_name
            }
        else:
            # Like - add new like
            if field_name == "user_id":
                new_like = Like(appreciation_id=appreciation_id, user_id=action.user_id)
            else:
                new_like = Like(appreciation_id=appreciation_id, likes_id=action.user_id)
            
            db.add(new_like)
            db.commit()
            print("Like added")
            
            # Get updated like count
            total_likes = db.query(Like).filter(Like.appreciation_id == appreciation_id).count()
            
            return {
                "message": "Like added successfully",
                "is_liked": True,
                "total_likes": total_likes,
                "user_id": action.user_id,
                "username": user.username,
                "debug_field_used": field_name
            }
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error toggling like: {str(e)}")
        print(f"Full error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle like: {str(e)}"
        )
@router.get("/{appreciation_id}/likes", response_model=dict)
async def get_appreciation_likes(
    appreciation_id: int,
    user_id: Optional[int] = Query(None, description="User ID to check if they liked this appreciation"),
    db: Session = Depends(get_db)
):
    """Get all likes for an appreciation with user details"""
    try:
        # Verify appreciation exists
        appreciation = db.query(Appreciation).filter(Appreciation.id == appreciation_id).first()
        if not appreciation:
            raise HTTPException(status_code=404, detail="Appreciation not found")
        
        # Get all likes with user details
        likes_query = db.query(Like).filter(Like.appreciation_id == appreciation_id).all()
        
        total_likes = len(likes_query)
        liked_users = []
        
        for like in likes_query:
            user = db.query(usermodels.User).filter(usermodels.User.id == like.user_id).first()
            if user:
                liked_users.append({
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "liked_at": getattr(like, 'created_at', None)
                })
        
        # Check if specific user liked this appreciation
        is_liked_by_user = False
        if user_id:
            user_like = db.query(Like).filter(
                Like.appreciation_id == appreciation_id,
                Like.user_id == user_id
            ).first()
            is_liked_by_user = user_like is not None
        
        return {
            "appreciation_id": appreciation_id,
            "total_likes": total_likes,
            "is_liked_by_user": is_liked_by_user,
            "liked_users": liked_users
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching likes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch likes: {str(e)}"
        )

@router.post("/{appreciation_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    appreciation_id: int,
    comment: CommentCreate,
    db: Session = Depends(get_db)
):
    """Add a comment to an appreciation (like Instagram)"""
    try:
        # Verify appreciation exists
        appreciation = db.query(Appreciation).filter(Appreciation.id == appreciation_id).first()
        if not appreciation:
            raise HTTPException(status_code=404, detail="Appreciation not found")

        # Verify user exists
        commenting_user = db.query(usermodels.User).filter(usermodels.User.id == comment.user_id).first()
        if not commenting_user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create new comment
        new_comment = Comment(
            appreciation_id=appreciation_id,
            user_id=comment.user_id,
            text=comment.text
        )
        db.add(new_comment)
        db.commit()
        db.refresh(new_comment)
        
        return CommentResponse(
            id=new_comment.id,
            user_id=new_comment.user_id,
            username=commenting_user.username,
            text=new_comment.text,
            created_at=new_comment.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating comment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create comment: {str(e)}"
        )

@router.get("/{appreciation_id}/comments", response_model=List[CommentResponse])
async def get_appreciation_comments(
    appreciation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all comments for an appreciation with user details"""
    try:
        # Verify appreciation exists
        appreciation = db.query(Appreciation).filter(Appreciation.id == appreciation_id).first()
        if not appreciation:
            raise HTTPException(status_code=404, detail="Appreciation not found")
        
        # Get comments with pagination, ordered by newest first
        comments = db.query(Comment)\
            .filter(Comment.appreciation_id == appreciation_id)\
            .order_by(desc(Comment.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        response = []
        for comment in comments:
            user = db.query(usermodels.User).filter(usermodels.User.id == comment.user_id).first()
            response.append(CommentResponse(
                id=comment.id,
                user_id=comment.user_id,
                username=user.username if user else "Unknown User",
                text=comment.text,
                created_at=comment.created_at
            ))
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching comments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch comments: {str(e)}"
        )

@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    user_id: int = Query(..., description="User ID who wants to delete the comment"),
    db: Session = Depends(get_db)
):
    """Delete a comment (user can only delete their own comments)"""
    try:
        comment = db.query(Comment).filter(Comment.id == comment_id).first()
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Check if user is the author of the comment
        if comment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own comments"
            )
        
        db.delete(comment)
        db.commit()
        
        return {"message": "Comment deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting comment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete comment: {str(e)}"
        )

@router.get("/{appreciation_id}/engagement", response_model=dict)
async def get_appreciation_engagement(
    appreciation_id: int,
    user_id: Optional[int] = Query(None, description="User ID to check their engagement"),
    db: Session = Depends(get_db)
):
    """Get complete engagement data for an appreciation (likes + comments)"""
    try:
        # Verify appreciation exists
        appreciation = db.query(Appreciation).filter(Appreciation.id == appreciation_id).first()
        if not appreciation:
            raise HTTPException(status_code=404, detail="Appreciation not found")
        
        # Get like count and user's like status
        total_likes = db.query(Like).filter(Like.appreciation_id == appreciation_id).count()
        is_liked_by_user = False
        
        if user_id:
            user_like = db.query(Like).filter(
                Like.appreciation_id == appreciation_id,
                Like.user_id == user_id
            ).first()
            is_liked_by_user = user_like is not None
        
        # Get comment count
        total_comments = db.query(Comment).filter(Comment.appreciation_id == appreciation_id).count()
        
        # Get recent comments (last 3)
        recent_comments = db.query(Comment)\
            .filter(Comment.appreciation_id == appreciation_id)\
            .order_by(desc(Comment.created_at))\
            .limit(3)\
            .all()
        
        recent_comments_data = []
        for comment in recent_comments:
            user = db.query(usermodels.User).filter(usermodels.User.id == comment.user_id).first()
            recent_comments_data.append({
                "id": comment.id,
                "user_id": comment.user_id,
                "username": user.username if user else "Unknown User",
                "text": comment.text,
                "created_at": comment.created_at
            })
        
        return {
            "appreciation_id": appreciation_id,
            "engagement": {
                "likes": {
                    "total": total_likes,
                    "is_liked_by_user": is_liked_by_user
                },
                "comments": {
                    "total": total_comments,
                    "recent": recent_comments_data
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching engagement data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch engagement data: {str(e)}"
        )
