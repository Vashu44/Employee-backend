from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base
from datetime import datetime

class ReportTemplate(Base):
    __tablename__ = "report_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(200), nullable=False)
    template_type = Column(String(50), nullable=False)  # employee, expense, timesheet, etc.
    report_format = Column(String(20), nullable=False)  # monthly, yearly, custom
    template_config = Column(JSON, nullable=False)  # Flexible configuration
    include_charts = Column(Boolean, default=True)
    chart_types = Column(JSON, default=[])  # List of chart types
    office_template_links = Column(JSON, default={})  # Links to Word/Excel/PPT templates
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    generated_reports = relationship("GeneratedReport", back_populates="template", cascade="all, delete-orphan")

class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("report_templates.id"), nullable=False)
    template_name = Column(String(200), nullable=False)
    report_type = Column(String(50), nullable=False)
    generated_data = Column(JSON, nullable=False)  # Store the query results
    charts_data = Column(JSON, default={})  # Store base64 encoded charts
    pdf_path = Column(String(500))  # Path to generated PDF
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    template = relationship("ReportTemplate", back_populates="generated_reports")
    generator = relationship("User", foreign_keys=[generated_by])

class EmailLog(Base):
    __tablename__ = "email_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("generated_reports.id"), nullable=False)
    sender_email = Column(String(100), nullable=False)
    recipient_email = Column(String(100), nullable=False)
    subject = Column(String(300), nullable=False)
    message = Column(Text)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="sent")  # sent, failed, pending
    
    # Relationships
    report = relationship("GeneratedReport")
