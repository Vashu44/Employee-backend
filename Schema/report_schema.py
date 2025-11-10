# Schema/report_schema.py
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import re

class ReportQueryRequest(BaseModel):
    title: str
    description: Optional[str] = None
    sql_query: str
    require_approval: Optional[bool] = False
    
    @validator('sql_query')
    def validate_sql_query(cls, v):
        query_clean = v.strip().upper()
        
        # Define allowed query types
        allowed_starts = [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'REPLACE',
            'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE', 'TRUNCATE',
            'CREATE INDEX', 'DROP INDEX', 'GRANT', 'REVOKE',
            'COMMIT', 'ROLLBACK', 'SAVEPOINT'
        ]
        
        # Check if query starts with any allowed pattern
        is_valid = any(query_clean.startswith(start) for start in allowed_starts)
        
        if not is_valid:
            raise ValueError('Query type not supported or not allowed')
        
        # Security checks
        dangerous_keywords = [
            'INFORMATION_SCHEMA', 'MYSQL', 'PERFORMANCE_SCHEMA', 'SYS',
            '/*', '*/', '--', ';--', 'EXEC', 'EXECUTE', 'EVAL'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in query_clean:
                raise ValueError(f'Dangerous keyword "{keyword}" not allowed')
        
        return v
    
    @validator('title')
    def validate_title(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Title must be at least 3 characters long')
        return v.strip()

class QueryResultResponse(BaseModel):
    columns: List[str]
    data: List[List[Any]]
    total_rows: int
    affected_rows: Optional[int] = 0
    execution_time: Optional[float] = None
    message: Optional[str] = None
    query_category: Optional[str] = None
    query_type: Optional[str] = None

class ReportListResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    query_category: str
    query_type: str
    user_id: int
    created_at: datetime
    status: str
    is_approved: bool
    user_email: Optional[str] = None
    
    class Config:
        from_attributes = True

class ReportResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    query_category: str
    query_type: str
    sql_query: str
    result_data: Optional[str]
    affected_rows: int
    execution_time: Optional[str]
    user_id: int
    is_approved: bool
    approved_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    status: str
    user_email: Optional[str] = None
    approver_email: Optional[str] = None
    
    class Config:
        from_attributes = True

class ApprovalRequest(BaseModel):
    action: str  # "approve" or "reject"
    remarks: Optional[str] = None
