from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from db.database import get_db
from model.query_model import Query
from model.usermodels import User

from Schema.query_schema import (
    QueryCreate,
    QueryResponse,
    QueryListResponse,
)


query_router = APIRouter(
    prefix="/api/queries",
    tags=["Queries"]
)

@query_router.get("/health")
async def health_check():
    """Health check endpoint to verify backend connectivity."""
    return {"status": "ok", "message": "Query service is healthy"}

# Create query
@query_router.post("/", response_model=QueryResponse)
async def create_query(
    query_data: QueryCreate,
    user_id: int,
    user_email: str,
    user_name: str,
    db: Session = Depends(get_db)
):
    """Create a new query"""
    try:
        # Verify user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Directly use string values from the request body
        db_query = Query(
            user_id=user_id,
            subject=query_data.subject,
            message=query_data.message,
            category=query_data.category.upper(),  # Convert to uppercase for consistency
            priority=query_data.priority.lower(),  # Convert to lowercase for consistency
            user_email=user_email,
            user_name=user_name,
            status="pending"  # Direct string entry
        )

        db.add(db_query)
        db.commit()
        db.refresh(db_query)

        # Return the response using the direct string values
        return QueryResponse(
            id=db_query.id,
            user_id=db_query.user_id,
            subject=db_query.subject,
            message=db_query.message,
            category=db_query.category,
            priority=db_query.priority,
            status=db_query.status,
            user_email=db_query.user_email,
            user_name=db_query.user_name,
            response=db_query.response,
            responded_by=db_query.responded_by,
            responded_at=db_query.responded_at,
            created_at=db_query.created_at,
            updated_at=db_query.updated_at
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating query: {str(e)}")

# Get all queries (for admin)
@query_router.get("/", response_model=List[QueryListResponse])
async def get_all_queries(
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all queries with optional filtering"""
    try:
        query = db.query(Query)

        if status:
            query = query.filter(Query.status == status)
        if category:
            query = query.filter(Query.category == category.upper())
        if priority:
            query = query.filter(Query.priority == priority.lower())

        queries = query.offset(skip).limit(limit).order_by(Query.created_at.desc()).all()

        return [
            QueryListResponse(
                id=q.id,
                subject=q.subject,
                category=q.category,
                priority=q.priority,
                status=q.status,
                user_name=q.user_name,
                user_email=q.user_email,
                created_at=q.created_at,
                has_response=bool(q.response or q.responses)
            ) for q in queries
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving queries: {str(e)}")

# Export the router
router = query_router