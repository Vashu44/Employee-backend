from pydantic import BaseModel, Field
from typing import List, Optional

class MoMInformationCreate(BaseModel):
    mom_id: int = Field(..., description="ID of the MoM this information belongs to")
    information: str = Field(..., max_length=255, description="Information content")

class MoMInformationUpdate(BaseModel):
    information: Optional[str] = Field(None, max_length=255, description="Information content")

class MoMInformationResponse(BaseModel):
    id: int
    mom_id: int
    information: str

    class Config:
        from_attributes = True

class MoMInformationListResponse(BaseModel):
    informations: List[MoMInformationResponse]
    total: int
    page: int
    per_page: int
    total_pages: int