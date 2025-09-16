from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ThoughtBase(BaseModel):
    thoughts: str
    author: str

class ThoughtCreate(ThoughtBase):
    created_by: int

class ThoughtUpdate(BaseModel):
    thoughts: Optional[str] = None
    author: Optional[str] = None

class ThoughtResponse(ThoughtBase):
    id: int
    created_at: datetime
    created_by: int

    class Config:
        from_attributes = True