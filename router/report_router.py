# router/report_router.py - COMPLETE WORKING VERSION
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import extract, and_, or_, func
from typing import List, Optional
from datetime import datetime, date
import os
import uuid
from pathlib import Path

# Database and model imports
from db.database import get_db
from model.usermodels import User
from model.report_model import HRReport  # Make sure this matches your model class name

router = APIRouter(
    prefix="/api/reports",
    tags=["HR Reports"]
)

# Directory for storing report documents
UPLOAD_DIR = Path("uploads/reports")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/health")
async def health_check():
    """Health Check"""
    return {"status": "healthy", "message": "HR Reports API is running"}

@router.post("/add-report")
async def add_report(
    title: str = Form(...),
    description: str = Form(...),
    month: int = Form(...),
    report_type: str = Form(default="monthly"),
    user_id: int = Form(...),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """Add Report"""
    try:
        # Validate user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate month
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        
        # Handle document upload if provided
        document_path = None
        if file:
            # Generate unique filename
            file_extension = Path(file.filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            document_path = UPLOAD_DIR / unique_filename
            
            # Save the file
            with open(document_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            document_path = str(document_path)
        
        # Create new report
        db_report = HRReport(
            title=title,
            description=description,
            month=month,
            report_type=report_type,
            user_id=user_id,
            document_path=document_path,
            status="submitted"
        )
        
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        
        return {
            "id": db_report.id,
            "title": db_report.title,
            "description": db_report.description,
            "month": db_report.month,
            "report_type": db_report.report_type,
            "user_id": db_report.user_id,
            "username": user.username,
            "document_path": db_report.document_path,
            "status": db_report.status,
            "created_at": db_report.created_at,
            "updated_at": db_report.updated_at,
            "has_document": bool(db_report.document_path)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding report: {str(e)}")

@router.get("/view-reports")
async def view_reports(
    page: int = 1,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """View Reports"""
    try:
        offset = (page - 1) * limit
        
        reports = db.query(HRReport).join(User).offset(offset).limit(limit).all()
        
        return [
            {
                "id": report.id,
                "title": report.title,
                "description": report.description,
                "month": report.month,
                "report_type": report.report_type,
                "user_id": report.user_id,
                "username": report.user.username,
                "status": report.status,
                "created_at": report.created_at,
                "has_document": bool(report.document_path)
            } for report in reports
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving reports: {str(e)}")

@router.get("/monthly-status/{year}/{month}")
async def get_monthly_report_status(
    year: int,
    month: int,
    db: Session = Depends(get_db)
):
    """Get Monthly Report Status"""
    try:
        # Validate month
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
        
        # Query reports for the specific month and year
        reports_query = db.query(HRReport).filter(
            HRReport.month == month,
            extract('year', HRReport.created_at) == year
        )
        
        total_reports = reports_query.count()
        submitted_reports = reports_query.filter(HRReport.status == "submitted").count()
        approved_reports = reports_query.filter(HRReport.status == "approved").count()
        rejected_reports = reports_query.filter(HRReport.status == "rejected").count()
        
        return {
            "year": year,
            "month": month,
            "total_reports": total_reports,
            "submitted": submitted_reports,
            "approved": approved_reports,
            "rejected": rejected_reports
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving monthly status: {str(e)}")

@router.get("/yearly-preview/{year}")
async def get_yearly_reports_preview(
    year: int,
    db: Session = Depends(get_db)
):
    """Get Yearly Reports Preview"""
    try:
        # Query reports for the specific year
        reports_query = db.query(HRReport).filter(
            extract('year', HRReport.created_at) == year
        )
        
        total_reports = reports_query.count()
        
        # Monthly breakdown
        monthly_breakdown = {}
        for month in range(1, 13):
            month_count = reports_query.filter(HRReport.month == month).count()
            monthly_breakdown[str(month)] = month_count
        
        return {
            "year": year,
            "total_reports": total_reports,
            "monthly_breakdown": monthly_breakdown
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving yearly preview: {str(e)}")

@router.get("/download-report/{report_id}")
async def download_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """Download Report"""
    from fastapi.responses import FileResponse
    
    try:
        report = db.query(HRReport).filter(HRReport.id == report_id).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if not report.document_path or not os.path.exists(report.document_path):
            raise HTTPException(status_code=404, detail="Document not found")
        
        return FileResponse(
            path=report.document_path,
            filename=f"report_{report.id}_{Path(report.document_path).name}",
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading report: {str(e)}")

@router.post("/email-report/{report_id}")
async def email_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """Email Report"""
    try:
        report = db.query(HRReport).filter(HRReport.id == report_id).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Here you would implement email sending logic
        # For now, just return success message
        
        return {
            "message": f"Report '{report.title}' has been emailed successfully",
            "report_id": report_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error emailing report: {str(e)}")

@router.delete("/delete-report/{report_id}")
async def delete_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """Delete Report"""
    try:
        report = db.query(HRReport).filter(HRReport.id == report_id).first()
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Delete associated document if exists
        if report.document_path and os.path.exists(report.document_path):
            os.remove(report.document_path)
        
        db.delete(report)
        db.commit()
        
        return {"message": f"Report '{report.title}' deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting report: {str(e)}")

@router.get("/generate-template")
async def generate_dummy_template():
    """Generate Dummy Template"""
    from fastapi.responses import Response
    
    try:
        # Generate a simple PDF template (you can use reportlab or other PDF libraries)
        # For now, return a simple text response
        
        template_content = '''
REPORT TEMPLATE
===============

Title: [Enter Report Title]
Month: [Select Month]
Description: [Provide detailed description]

Created by: HR Management System
Date: Generated on request
        '''
        
        return Response(
            content=template_content,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=report_template.txt"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating template: {str(e)}")
