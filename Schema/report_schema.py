from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, date

class ReportTemplateBase(BaseModel):
    template_name: str
    template_type: str
    report_format: str
    template_config: Dict[str, Any]
    include_charts: bool = True
    chart_types: List[str] = []
    office_template_links: Dict[str, str] = {}

class ReportTemplateCreate(ReportTemplateBase):
    created_by: int

class ReportTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    template_config: Optional[Dict[str, Any]] = None
    include_charts: Optional[bool] = None
    chart_types: Optional[List[str]] = None
    office_template_links: Optional[Dict[str, str]] = None

class ReportTemplateInDB(ReportTemplateBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GeneratedReportBase(BaseModel):
    template_id: int
    template_name: str
    report_type: str
    generated_data: Dict[str, Any]
    charts_data: Dict[str, str] = {}
    pdf_path: Optional[str] = None

class GeneratedReportCreate(GeneratedReportBase):
    generated_by: int

class GeneratedReportInDB(GeneratedReportBase):
    id: int
    generated_by: int
    generated_at: datetime
    
    class Config:
        from_attributes = True

class ReportGenerationRequest(BaseModel):
    template_id: int
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    employee_ids: Optional[List[int]] = []
    department: Optional[str] = None
    additional_filters: Dict[str, Any] = {}

class EmailReportRequest(BaseModel):
    report_id: int
    recipient_email: EmailStr
    subject: str
    message: str
    sender_email: EmailStr

class ChartConfig(BaseModel):
    name: str
    type: str  # bar, line, pie, table
    title: str
    x_field: str
    y_field: str
    color: Optional[str] = None

class TemplateConfigSchema(BaseModel):
    title: str
    description: Optional[str] = None
    base_query: Optional[str] = None
    table: Optional[str] = None
    select_fields: str = "*"
    date_field: str = "created_at"
    employee_field: str = "user_id"
    order_by: str = " ORDER BY created_at DESC"
    limit: str = " LIMIT 1000"
    charts: List[ChartConfig] = []
