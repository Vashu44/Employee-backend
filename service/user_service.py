from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, Depends, status, Request, Response, UploadFile, Form, File, Body
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr, validator
from typing import Annotated, Optional, List
from datetime import datetime
import model.usermodels as usermodels
from model.userDetails_model import UserDetails
from db.database import engine, get_db, Base as DatabaseBase 
from sqlalchemy import func
from sqlalchemy.orm import Session

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