from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date
import logging

logger = logging.getLogger(__name__)

# Pydantic schema for updating basic user details
class UserBasicDetailsUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    personal_email: Optional[str] = Field(None, max_length=255, description="Personal email address")

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat() if v else None
        }
        json_schema_extra = {
            "example": {
                "full_name": "John Doe",
                "personal_email": "user@example.com", 
            }
        }


# Pydantic schema for response after updating user details
class UserBasicDetailsResponse(BaseModel):
    message: str
    updated_fields: list
    user_data: dict


# Pydantic models
class UserProjectsResponse(BaseModel):
    projects: List[str]

class UserSearchRequest(BaseModel):
    full_name: Optional[str] 
    personal_email: Optional[EmailStr]
    user_id: Optional[int]