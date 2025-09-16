from sqlalchemy import Column, String, Enum, Date, Time, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.types import Integer
from enum import Enum as pyEnum
from datetime import datetime
from db.database import Base

class MeetingType(str, pyEnum):
    Online = "Online"
    Offline = "Offline"
    Hybrid = "Hybrid"

class MoMStatus(str, pyEnum):
    Open = "Open"
    Closed = "Closed"
    Pending = "Pending"

class ActionItemStatus(str, pyEnum):
    Pending = "Pending"
    InProgress = "In Progress"
    Completed = "Completed"
    Cancelled = "Cancelled"

class MoM(Base):
    __tablename__ = "mom"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    meeting_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    attendees = Column(JSON, nullable=False)
    absent = Column(JSON, default=[], nullable=True)
    outer_attendees = Column(JSON, default=[], nullable=False)
    project = Column(String(100), nullable=False, index=True)
    meeting_type = Column(Enum(MeetingType), nullable=False)
    location_link = Column(String(255), nullable=False)

    status = Column(Enum(MoMStatus), default=MoMStatus.Open, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    
        #  // Relationships with user table
    user = relationship("User", back_populates="moms_created")
    informations = relationship("MoMInformation", back_populates="mom")
    decisions = relationship("MoMDecision", back_populates="mom")
    action_items = relationship("MoMActionItem", back_populates="mom")


class MoMInformation(Base):
    __tablename__ = "mom_information"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    mom_id = Column(Integer, ForeignKey("mom.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    information = Column(String(255), nullable=False)

    mom = relationship("MoM", back_populates="informations")

class MoMDecision(Base):
    __tablename__ = "mom_decision"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    mom_id = Column(Integer, ForeignKey("mom.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    decision = Column(String(255), nullable=False)

    mom = relationship("MoM", back_populates="decisions")

class MoMActionItem(Base):
    __tablename__ = "mom_action_item"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    mom_id = Column(Integer, ForeignKey("mom.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    project = Column(String(100), nullable=False)
    action_item = Column(String(255), nullable=False)
    assigned_to = Column(String(255), nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(ActionItemStatus), default=ActionItemStatus.Pending, nullable=False)
    remark = Column(JSON, nullable=True, default=lambda: [])
    updated_at = Column(Date, nullable=True)
    re_assigned_to = Column(String(255), nullable=True)
    meeting_date = Column(Date, nullable=True)

    mom = relationship("MoM", back_populates="action_items")