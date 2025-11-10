from pydantic import BaseModel, validator
from typing import Optional

class NicknameRequest(BaseModel):
    nickname: str
    
    @validator('nickname')
    def validate_nickname(cls, v):
        if v and len(v.strip()) == 0:
            raise ValueError('Nickname cannot be empty')
        if v and len(v) > 50:
            raise ValueError('Nickname cannot exceed 50 characters')
        return v.strip() if v else v

class BioRequest(BaseModel):
    bio: str
    
    @validator('bio')
    def validate_bio(cls, v):
        if v and len(v.strip()) == 0:
            raise ValueError('Bio cannot be empty')
        if v and len(v) > 500:
            raise ValueError('Bio cannot exceed 500 characters')
        return v.strip() if v else v

class NicknameResponse(BaseModel):
    user_id: int
    nickname: Optional[str] = None
    
    class Config:
        from_attributes = True

class BioResponse(BaseModel):
    user_id: int
    bio: Optional[str] = None
    
    class Config:
        from_attributes = True