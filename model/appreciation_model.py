from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db.database import Base 

class Appreciation(Base):
    __tablename__ = "appreciations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    given_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    award_type = Column(String(100), nullable=False)
    badge_level = Column(String(20), nullable=False)
    appreciation_message = Column(Text, nullable=True)
    month = Column(String(20), nullable=False) 
    year = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Define the relationships to the User model
    employee = relationship("User", foreign_keys=[employee_id], back_populates="appreciations_received")
    given_by = relationship("User", foreign_keys=[given_by_id], back_populates="appreciations_given")

    # Add relationships for likes and comments
    likes = relationship("Like", back_populates="appreciation", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="appreciation", cascade="all, delete-orphan")

class Like(Base):
    __tablename__ = "appreciation_likes"
    id = Column(Integer, primary_key=True, index=True)
    appreciation_id = Column(Integer, ForeignKey("appreciations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(Date,server_default=func.now())
    
    appreciation = relationship("Appreciation", back_populates="likes")
    user = relationship("User", foreign_keys=[user_id])

class Comment(Base):
    __tablename__ = "appreciation_comments"
    id = Column(Integer, primary_key=True, index=True)
    appreciation_id = Column(Integer, ForeignKey("appreciations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    appreciation = relationship("Appreciation", back_populates="comments")
    user = relationship("User", foreign_keys=[user_id])

