from pydantic import BaseModel, Field
from typing import List, Optional

class MoMDecisionCreate(BaseModel):
    mom_id: int = Field(..., description="ID of the MoM this decision belongs to")
    decision: str = Field(..., max_length=255, description="Decision content")

class MoMDecisionUpdate(BaseModel):
    decision: Optional[str] = Field(None, max_length=255, description="Decision content")

class MoMDecisionResponse(BaseModel):
    id: int
    mom_id: int
    decision: str

    class Config:
        from_attributes = True

class MoMDecisionListResponse(BaseModel):
    decisions: List[MoMDecisionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int