from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from db.database import get_db
from Schema.thoughts_schema import ThoughtCreate, ThoughtResponse, ThoughtUpdate
from service.thoughts_service import ThoughtService

router = APIRouter(prefix="/thoughts")

@router.post("/", response_model=ThoughtResponse, status_code=status.HTTP_201_CREATED)
async def create_thought(
    thought: ThoughtCreate,
    db: Session = Depends(get_db)
):
    """Create a new thought"""
    return ThoughtService.create_thought(db=db, thought=thought)

@router.post("/bulk-upload", status_code=status.HTTP_201_CREATED)
async def bulk_upload_thoughts(
    created_by: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Bulk upload thoughts from CSV file
    CSV format: thoughts,author,created_by
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )
    
    # Read file content
    content = await file.read()
    
    # Process the CSV
    result = ThoughtService.bulk_create_thoughts(
        db=db,
        csv_content=content,
        created_by=created_by
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return {
        "message": result["message"],
        "created_by": created_by,
        "created_count": result["created_count"],
        "failed_count": result["failed_count"],
        "failed_rows": result["failed_rows"] if result["failed_rows"] else None
    }

@router.get("/random", response_model=ThoughtResponse)
async def get_random_thought(
    db: Session = Depends(get_db)
):
    """Get a random thought from the database"""
    thought = ThoughtService.get_random_thought(db=db)
    if thought is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No thoughts found in database"
        )
    return thought

@router.get("/", response_model=List[ThoughtResponse])
async def get_all_thoughts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all thoughts with pagination"""
    thoughts = ThoughtService.get_all_thoughts(db=db, skip=skip, limit=limit)
    return thoughts

@router.get("/{thought_id}", response_model=ThoughtResponse)
async def get_thought(
    thought_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific thought by ID"""
    thought = ThoughtService.get_thought(db=db, thought_id=thought_id)
    if thought is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thought not found"
        )
    return thought

@router.get("/author/{author}", response_model=List[ThoughtResponse])
async def get_thoughts_by_author(
    author: str,
    db: Session = Depends(get_db)
):
    """Get all thoughts by a specific author"""
    thoughts = ThoughtService.get_thoughts_by_author(db=db, author=author)
    return thoughts

@router.put("/{thought_id}", response_model=ThoughtResponse)
async def update_thought(
    thought_id: int,
    thought_update: ThoughtUpdate,
    db: Session = Depends(get_db)
):
    """Update a thought"""
    thought = ThoughtService.update_thought(
        db=db, 
        thought_id=thought_id, 
        thought_update=thought_update
    )
    if thought is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thought not found"
        )
    return thought

@router.delete("/{thought_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thought(
    thought_id: int,
    db: Session = Depends(get_db)
):
    """Delete a thought"""
    success = ThoughtService.delete_thought(db=db, thought_id=thought_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thought not found"
        )