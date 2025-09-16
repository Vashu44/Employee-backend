from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from sqlalchemy.orm import Session
from db.database import get_db
from Schema.thoughts_oftheday_schema import ThoughtCreate, ThoughtResponse
from model.thoughts_oftheday import ThoughtOfTheDay
from datetime import datetime,timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/thoughtoftheday")

@router.post("/thoughtoftheday", response_model=ThoughtResponse, status_code=status.HTTP_201_CREATED)
async def create_thought(thought_create: ThoughtCreate, db: Session = Depends(get_db)):
    """
    Create a new thought of the day - only one thought per day allowed
    """
    try:
        # Check if thought already exists for today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        existing_thought = db.query(ThoughtOfTheDay).filter(
            ThoughtOfTheDay.created_at >= today_start,
            ThoughtOfTheDay.created_at < today_end
        ).first()
        
        if existing_thought:
            # Update existing thought instead of creating new one
            existing_thought.thought = thought_create.thought
            existing_thought.author_id = thought_create.author_id
            existing_thought.author_name = thought_create.author_name
            existing_thought.created_at = datetime.now()
            db.commit()
            db.refresh(existing_thought)
            logger.info(f"Updated thought with ID: {existing_thought.id} by {existing_thought.author_name}")
            return existing_thought
        
        new_thought = ThoughtOfTheDay(
            thought=thought_create.thought,
            author_id=thought_create.author_id,
            author_name=thought_create.author_name
        )
        db.add(new_thought)
        db.commit()
        db.refresh(new_thought)
        logger.info(f"Created new thought with ID: {new_thought.id} by {new_thought.author_name}")
        return new_thought
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating thought: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create thought"
        )

@router.get("/thoughtoftheday/today", response_model=ThoughtResponse)
async def get_todays_thought(db: Session = Depends(get_db)):
    """
    Get today's thought of the day - returns thought only if it exists and is valid for current time
    """
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_9am = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        current_time = datetime.now()
        
        # Get today's thought
        todays_thought = db.query(ThoughtOfTheDay).filter(
            ThoughtOfTheDay.created_at >= today_start,
            ThoughtOfTheDay.created_at < today_start + timedelta(days=1)
        ).first()
        
        if not todays_thought:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No thought found for today"
            )
        
        # If current time is past 9 AM, check if thought should still be visible
        if current_time >= today_9am:
            # After 9 AM, only show thoughts that were created before 9 AM today
            if todays_thought.created_at >= today_9am:
                # Thought was created after 9 AM today, don't show it
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Thought not available after 9 AM"
                )
        
        return todays_thought
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching today's thought: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve today's thought"
        )

@router.get("/thoughtoftheday", response_model=List[ThoughtResponse])
async def get_all_thoughts(db: Session = Depends(get_db)):
    """
    Retrieve all thoughts of the day (ordered by newest first)
    """
    try:
        thoughts = db.query(ThoughtOfTheDay).order_by(
            ThoughtOfTheDay.created_at.desc()
        ).all()
        return thoughts
    except Exception as e:
        logger.error(f"Error fetching thoughts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve thoughts"
        )

@router.get("/thoughtoftheday/latest", response_model=ThoughtResponse)
async def get_latest_thought(db: Session = Depends(get_db)):
    """
    Get the most recent thought of the day (for admin/HR view)
    """
    try:
        latest_thought = db.query(ThoughtOfTheDay).order_by(
            ThoughtOfTheDay.created_at.desc()
        ).first()
        
        if not latest_thought:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No thoughts found"
            )
        
        return latest_thought
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest thought: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latest thought"
        )

@router.get("/thoughtoftheday/author/{author_id}", response_model=List[ThoughtResponse])
async def get_thoughts_by_author(author_id: int, db: Session = Depends(get_db)):
    """
    Get all thoughts by a specific author
    """
    try:
        thoughts = db.query(ThoughtOfTheDay).filter(
            ThoughtOfTheDay.author_id == author_id
        ).order_by(ThoughtOfTheDay.created_at.desc()).all()
        
        return thoughts
    except Exception as e:
        logger.error(f"Error fetching thoughts by author {author_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve thoughts"
        )

@router.put("/thoughtoftheday/{thought_id}", response_model=ThoughtResponse)
async def update_thought(thought_id: int, thought_update: ThoughtCreate, db: Session = Depends(get_db)):
    """
    Update a specific thought by ID
    """
    try:
        thought = db.query(ThoughtOfTheDay).filter(ThoughtOfTheDay.id == thought_id).first()
        
        if not thought:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thought not found"
            )
        
        # Update fields
        thought.thought = thought_update.thought
        thought.author_id = thought_update.author_id
        thought.author_name = thought_update.author_name
        
        db.commit()
        db.refresh(thought)
        logger.info(f"Updated thought with ID: {thought_id}")
        return thought
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating thought: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update thought"
        )

@router.delete("/thoughtoftheday/{thought_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thought(thought_id: int, db: Session = Depends(get_db)):
    """
    Delete a specific thought by ID
    """
    try:
        thought = db.query(ThoughtOfTheDay).filter(ThoughtOfTheDay.id == thought_id).first()
        
        if not thought:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thought not found"
            )
        
        db.delete(thought)
        db.commit()
        logger.info(f"Deleted thought with ID: {thought_id}")
        return
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting thought: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete thought"
        )

@router.post("/thoughtoftheday/cleanup", status_code=status.HTTP_200_OK)
async def manual_cleanup_thoughts(db: Session = Depends(get_db)):
    """
    Manually trigger cleanup of old thoughts (respects 9 AM rule)
    """
    try:
        today_9am = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        current_time = datetime.now()
        
        if current_time >= today_9am:
            # After 9 AM, delete thoughts from before today's 9 AM
            cutoff = today_9am
        else:
            # Before 9 AM, delete thoughts from before yesterday's 9 AM
            cutoff = today_9am - timedelta(days=1)
        
        deleted_count = db.query(ThoughtOfTheDay).filter(
            ThoughtOfTheDay.created_at < cutoff
        ).delete()
        db.commit()
        
        return {
            "message": f"Successfully cleaned up {deleted_count} old thoughts",
            "cutoff_time": cutoff.isoformat(),
            "cleanup_rule": "Thoughts are removed daily at 9 AM"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error in manual cleanup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup thoughts"
        )
