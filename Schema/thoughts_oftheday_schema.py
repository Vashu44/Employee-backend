from pydantic import BaseModel, Field
from datetime import datetime

class ThoughtCreate(BaseModel):
    thought: str = Field(..., description="The thought of the day text")
    author_id: int = Field(..., description="ID of the user creating the thought")
    author_name: str = Field(..., max_length=100, description="Name of the author")

class ThoughtResponse(BaseModel):
    id: int
    thought: str
    author_id: int
    author_name: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
