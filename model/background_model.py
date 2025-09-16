from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text, Date
from db.database import Base
from datetime import datetime


class BackgroundCheckForm(Base):

    __tablename__ = "background_check_forms"

    id = Column(Integer, primary_key=True, index=True)
    
    # Personal Information
    candidate_name = Column(String(255))
    father_name = Column(String(255))
    mother_name = Column(String(255))
    date_of_birth = Column(Date)
    marital_status = Column(String(255))
    email_id = Column(String(255), index=True)
    contact_number = Column(Integer)
    alternate_contact_number = Column(Integer)
    aadhaar_card_number = Column(Integer)
    pan_number = Column(String(255), nullable=True)
    uan_number = Column(Integer)

    # Current Address
    current_complete_address = Column(Text)  
    current_landmark = Column(String(255))
    current_city = Column(String(255))
    current_state = Column(String(255))
    current_pin_code = Column(Integer)
    current_police_station = Column(String(255))
    current_duration_from = Column(Date)
    current_duration_to = Column(Date)

    # Permanent Address
    permanent_complete_address = Column(Text)  
    permanent_landmark = Column(String)
    permanent_city = Column(String(255))
    permanent_state = Column(String(255))
    permanent_pin_code = Column(Integer)
    permanent_police_station = Column(String(255))
    permanent_duration_from = Column(Date)
    permanent_duration_to = Column(Date)

    # Employment Details
    organization_name = Column(String(255))
    organization_address = Column(Text)  
    designation = Column(String(255))
    employee_code = Column(String(255))
    date_of_joining = Column(Date)
    last_working_day = Column(Date)
    salary = Column(Integer)
    reason_for_leaving = Column(Text)
    
    # Manager Details
    manager_name = Column(String(100), nullable=False)
    manager_contact_number = Column(String(100), nullable=False)
    manager_email_id = Column(String(100), nullable=False)
    
    # JSON fields
    education_details = Column(JSON, default=list)
    hr_details = Column(JSON, default=list)
    reference_details = Column(JSON, default=list)
    verification_checks = Column(JSON, default=dict)

    # Authorization
    candidate_name_auth = Column(String(255))
    signature = Column(String(255))
    auth_date = Column(Date)
    acknowledgment = Column(Boolean)
    
    # Status and tracking fields
    status = Column(String, default="draft", index=True)
    remarks = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime)
    
    def to_dict(self):
        """
        Convert the model instance to a dictionary for JSON serialization
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result
    
    def __repr__(self):
        return f"<BackgroundCheckForm(id={self.id}, candidate_name='{self.candidate_name}', status='{self.status}')>"

__all__ = ['BackgroundCheckForm', 'Base']